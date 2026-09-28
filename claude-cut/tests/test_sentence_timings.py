import json
import subprocess
import sys

import pytest

from conftest import FIXTURES, MCP_SCRIPT, ROOT, SCRIPTS, run_script
from number_sentences import number_script
from speech import SESSION, transcript
from validate import validate_file

PROMPTER = FIXTURES / "timings" / "prompter.md"
V040 = "7e8619d"  # main at v0.4.0


def cut(tmp_path, data, script=PROMPTER, timings=True, runner=None, tag="new"):
    """Run match_takes on a transcript dict; return the output paths."""
    d = tmp_path / tag
    d.mkdir(exist_ok=True)
    tr = d / "transcript.json"
    tr.write_text(json.dumps(data, indent=1))
    args = [tr, script, "-o", d / "cuts.json", "--report", d / "report.md"]
    if timings:
        args += ["--sentences-out", d / "sentences.json"]
    r = subprocess.run([sys.executable, str(runner or SCRIPTS / "match_takes.py"),
                        *map(str, args)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return d


@pytest.fixture
def session(tmp_path):
    d = cut(tmp_path, transcript(SESSION))
    return (json.loads((d / "sentences.json").read_text()),
            json.loads((d / "cuts.json").read_text()), d)


def by_s(doc):
    return {s["s"]: s for s in doc["sentences"]}


def test_sentences_run_together_get_their_own_timings(session):
    doc, _, _ = session
    s = by_s(doc)
    # s1 and s2 were one pause-chunk labelled s1; alignment splits them.
    assert (s[1]["status"], s[1]["start"], s[1]["end"]) == ("kept", 3.7, 5.75)
    assert (s[2]["status"], s[2]["start"], s[2]["end"]) == ("kept", 5.8, 8.55)
    assert " ".join(w["w"] for w in s[2]["words"]) == \
        "Today we are going to fix the edit."
    assert s[1]["score"] == 100 and "score" not in s[2]


def test_retake_rescue_and_missing(session):
    doc, _, _ = session
    s = by_s(doc)
    # only the clean second take of s3 is timed, not the fluff before the marker
    assert (s[3]["start"], s[3]["end"]) == (15.1, 17.85)
    assert s[4]["status"] == "rescued"
    assert s[5] == {"s": 5, "status": "missing"}


def test_off_script_and_fragments_are_unaligned(session):
    doc, _, _ = session
    assert [u["text"] for u in doc["unaligned"]] == [
        "hi folks quick one today", "Fine.", "okay that's a wrap"]


def test_timed_words_are_inside_kept_ranges_and_never_markers(session):
    doc, cuts, _ = session
    spans = [(r["start"], r["end"]) for r in cuts["ranges"]]
    for s in doc["sentences"]:
        for w in s.get("words", []):
            assert w["w"].lower().strip(".") not in ("retake", "cut")
            mid = (w["start"] + w["end"]) / 2
            assert any(a <= mid <= b for a, b in spans)


def test_misheard_word_stays_in_its_sentence(tmp_path):
    data = transcript(SESSION)
    for w in data["words"]:
        if w["word"] == "left":
            w["word"] = "lift"
    d = cut(tmp_path, data)
    s3 = by_s(json.loads((d / "sentences.json").read_text()))[3]
    assert "lift" in [w["w"] for w in s3["words"]]


def test_output_validates(session):
    _, _, d = session
    kind, errs = validate_file(d / "sentences.json")
    assert (kind, errs) == ("sentences", [])


# --- edit-takes standalone: byte-identical to v0.4.0 ----------------------------

def long_session():
    """The MCP script read end to end, with a fluffed take and a spoken
    'retake cut' before every seventh sentence, and pauses like a real
    prompter read."""
    doc = number_script(MCP_SCRIPT.read_text())
    utts, para = [], None
    for s in doc["sentences"]:
        pause = 1.2 if s["para"] != para else 0.4
        para = s["para"]
        if s["n"] % 7 == 0 and len(s["text"].split()) > 4:
            utts.append((pause, " ".join(s["text"].split()[:4])))
            utts.append((1.0, "retake cut"))
            pause = 1.0
        utts.append((pause, s["text"]))
    return transcript(utts)


@pytest.fixture(scope="module")
def v040_match_takes(tmp_path_factory):
    src = subprocess.run(
        ["git", "show", f"{V040}:claude-cut/scripts/match_takes.py"],
        cwd=ROOT, capture_output=True, text=True)
    if src.returncode != 0:
        pytest.skip(f"can't read v0.4.0 match_takes.py from git ({V040})")
    p = tmp_path_factory.mktemp("v040") / "match_takes.py"
    p.write_text(src.stdout)
    return p


@pytest.mark.parametrize("name,data,script", [
    ("session", transcript(SESSION), PROMPTER),
    ("mcp", long_session(), MCP_SCRIPT),
])
def test_cut_outputs_identical_to_v040(tmp_path, v040_match_takes, name, data,
                                       script):
    old = cut(tmp_path, data, script, timings=False, runner=v040_match_takes,
              tag="old")
    plain = cut(tmp_path, data, script, timings=False, tag="plain")
    flagged = cut(tmp_path, data, script, timings=True, tag="flagged")
    for f in ("cuts.json", "report.md"):
        ref = (old / f).read_bytes()
        assert (plain / f).read_bytes() == ref, f"{name}: {f} differs (no flag)"
        assert (flagged / f).read_bytes() == ref, f"{name}: {f} differs (flag)"
    assert not (plain / "sentences.json").exists()
    assert (flagged / "sentences.json").exists()


def test_mcp_session_every_kept_spoken_word_is_timed(tmp_path):
    """Only the short fragments split_sentences drops ("Fine.", "Sweet huh!")
    may come back unaligned. Missing sentences are ones the cut binned or
    script-file furniture (titles, metadata) that's never spoken."""
    d = cut(tmp_path, long_session(), MCP_SCRIPT)
    doc = json.loads((d / "sentences.json").read_text())
    fragments = {s["text"] for s in number_script(MCP_SCRIPT.read_text())
                 ["sentences"] if len(s["text"].split()) < 3}
    assert {u["text"] for u in doc["unaligned"]} <= fragments
    spoken = [s for s in doc["sentences"] if s["status"] != "missing"]
    starts = [s["start"] for s in spoken]
    assert starts == sorted(starts)
    assert all(s["start"] < s["end"] for s in spoken)


def test_underscored_identifiers_align(session):
    """`WP_API_URL` is 'WPAPIURL' to match_takes' script side but
    'wp api url' to its speech side; the alignment key must agree."""
    from sentence_timings import align
    words = [{"word": "`WP_API_URL`", "start": 0, "end": 1},
             {"word": "is", "start": 1, "end": 2},
             {"word": "your", "start": 2, "end": 3},
             {"word": "site.", "start": 3, "end": 4}]
    assert align(words, ["WPAPIURL is your site."]) == [0, 0, 0, 0]


def test_lone_word_matches_elsewhere_are_ignored():
    from sentence_timings import align
    words = [{"word": w, "start": i, "end": i + 1}
             for i, w in enumerate("happy building".split())]
    # 'building' also appears in a later, never-spoken sentence
    assert align(words, ["Nothing to see here.",
                         "We are building a thing."]) == [None, None]
