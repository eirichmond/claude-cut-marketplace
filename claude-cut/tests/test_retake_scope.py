"""--marker-scope sentence: 'retake cut' bins only what the retake repeats."""
import json

import pytest

from conftest import FIXTURES, MCP_SCRIPT, run_script
from speech import transcript

PROMPTER = FIXTURES / "timings" / "prompter.md"
# s1 Welcome back to the channel everyone.  s2 Today we are going to fix the edit.
# s3 Open the settings panel on the left side.
# s4 Click the big export button at the bottom.
# s5 Thanks for watching and see you next time.


def cut(tmp_path, utts, scope, script=PROMPTER, tag=None):
    d = tmp_path / (tag or scope)
    d.mkdir(exist_ok=True)
    (d / "t.json").write_text(json.dumps(transcript(utts)))
    r = run_script("match_takes.py", d / "t.json", script, "-o", d / "cuts.json",
                   "--report", d / "report.md", "--marker-scope", scope,
                   "--sentences-out", d / "sentences.json")
    assert r.returncode == 0, r.stderr
    doc = json.loads((d / "sentences.json").read_text())
    return ({s["s"]: s for s in doc["sentences"]},
            (d / "report.md").read_text())


MID_FLOW_FLUFF = [
    # s1 and s2 said well, s3 fluffed in the same breath, restart at s3
    (0.5, "Welcome back to the channel everyone. Today we are going to fix "
          "the edit. Open the settings panel on the"),
    (1.2, "retake cut"),
    (1.2, "Open the settings panel on the left side. Click the big export "
          "button at the bottom."),
    (1.5, "Thanks for watching and see you next time."),
]


def test_default_loses_good_lines_said_before_a_mid_flow_fluff(tmp_path):
    """The v0.4.0 behaviour this fix exists for, kept as the default."""
    s, _ = cut(tmp_path, MID_FLOW_FLUFF, "chunk")
    assert s[1]["status"] == s[2]["status"] == "missing"


def test_sentence_scope_keeps_them(tmp_path):
    s, report = cut(tmp_path, MID_FLOW_FLUFF, "sentence")
    assert [s[n]["status"] for n in (1, 2, 3, 4, 5)] == ["kept"] * 5
    assert s[1]["start"] < 1 and s[2]["end"] < 6       # the first-breath take
    assert s[3]["start"] > 8                           # the retake, not the fluff
    assert "BINNED (before marker (retaken)): Open the settings panel on the" \
        in report


def test_paragraph_restart_still_bins_the_whole_attempt(tmp_path):
    utts = [(0.5, "Welcome back to the channel everyone. Today we are going "
                  "to fix the"),
            (1.2, "retake cut"),
            (1.2, "Welcome back to the channel everyone. Today we are going "
                  "to fix the edit."),
            (1.5, "Open the settings panel on the left side. Click the big "
                  "export button at the bottom. Thanks for watching and see "
                  "you next time.")]
    s, _ = cut(tmp_path, utts, "sentence")
    assert s[1]["start"] > 3 and s[2]["start"] > 3     # only the retake


def test_filler_before_the_retaken_sentence_goes_with_the_fluff(tmp_path):
    """'Okay. Open the settings...' fluffed: the 'Okay.' stub must not be
    kept (it could match some other sentence and bin its real take)."""
    utts = [(0.5, "Welcome back to the channel everyone. Today we are going "
                  "to fix the edit. Okay. Open the settings panel on the"),
            (1.2, "retake cut"),
            (1.2, "Open the settings panel on the left side. Click the big "
                  "export button at the bottom."),
            (1.5, "Thanks for watching and see you next time.")]
    s, report = cut(tmp_path, utts, "sentence")
    assert "BINNED (before marker (retaken)): Okay. Open the settings" in report
    assert all(s[n]["status"] == "kept" for n in range(1, 6))


def test_off_script_restart_falls_back_to_chunk_scope(tmp_path):
    utts = [(0.5, "Welcome back to the channel everyone. Today we are going "
                  "to fix the"),
            (1.2, "retake cut"),
            (1.2, "sorry about that folks"),
            (1.5, "hang on a moment")]
    chunk, _ = cut(tmp_path, utts, "chunk")
    sentence, _ = cut(tmp_path, utts, "sentence")
    assert chunk == sentence


def test_a_line_never_delivered_cleanly_stays_missing(tmp_path):
    utts = [(0.5, "Welcome back to the channel everyone."),
            (1.2, "Today we are going to"), (1.2, "retake cut"),
            (1.2, "Today we are going to fix"), (1.2, "retake cut"),
            (1.2, "Open the settings panel on the left side.")]
    s, _ = cut(tmp_path, utts, "sentence")
    assert s[1]["status"] == "kept" and s[2]["status"] == "missing"


def test_no_markers_means_no_difference(tmp_path):
    utts = [(0.5, "Welcome back to the channel everyone. Today we are going "
                  "to fix the edit."),
            (1.5, "Open the settings panel on the left side.")]
    a = cut(tmp_path, utts, "chunk")
    b = cut(tmp_path, utts, "sentence")
    assert a[0] == b[0]


def test_long_read_restarting_at_the_fluff_loses_nothing(tmp_path):
    """Step 2's MCP read (a fluff + 'retake cut' before every seventh
    sentence, restarting at the fluffed sentence) lost good lines under
    chunk scope; sentence scope keeps every spoken sentence."""
    from match_takes import norm, split_sentences
    from number_sentences import number_script
    from test_sentence_timings import long_session
    utts = long_session()
    tr = tmp_path / "t.json"
    tr.write_text(json.dumps(utts))
    spoken = {norm(s["text"]) for s in number_script(MCP_SCRIPT.read_text())
              ["sentences"]}
    cut_sents = split_sentences(MCP_SCRIPT.read_text())
    want = {i + 1 for i, s in enumerate(cut_sents) if norm(s) in spoken}
    missing = {}
    for scope in ("chunk", "sentence"):
        out = tmp_path / f"{scope}.json"
        r = run_script("match_takes.py", tr, MCP_SCRIPT, "-o",
                       tmp_path / f"{scope}.cuts.json", "--marker-scope", scope,
                       "--sentences-out", out)
        assert r.returncode == 0, r.stderr
        doc = json.loads(out.read_text())
        missing[scope] = {s["s"] for s in doc["sentences"]
                          if s["status"] == "missing"} & want
    assert len(missing["chunk"]) >= 10          # the problem, reproduced
    assert missing["sentence"] == set()          # and fixed


def test_a_fragment_after_a_pause_is_not_filler(tmp_path):
    """'Sweet huh!' ends one paragraph; after a pause the next is fluffed.
    The fragment is too short to match but it's its own line: keep it."""
    utts = [(0.5, "Welcome back to the channel everyone. Today we are going "
                  "to fix the edit. Fine."),
            (1.5, "Open the settings panel on the"),
            (1.2, "retake cut"),
            (1.2, "Open the settings panel on the left side. Click the big "
                  "export button at the bottom.")]
    s, _ = cut(tmp_path, utts, "sentence")
    assert s[1]["status"] == s[2]["status"] == "kept"
    words = transcript(utts)["words"]
    fine = next(w for w in words if w["word"] == "Fine.")
    ranges = json.loads((tmp_path / "sentence" / "cuts.json").read_text())["ranges"]
    assert any(r["start"] <= fine["start"] and fine["end"] <= r["end"]
               for r in ranges)
