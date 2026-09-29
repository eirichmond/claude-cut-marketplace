import json
import re
import subprocess
import sys

from conftest import SCRIPTS, run_script
from speech import transcript
from validate import validate_file


def build(chain, **kw):
    chain.build(**kw)
    return run_script("build_prompters.py", chain.director)


def load_map(chain):
    return json.loads((chain.dir / "prompter.map.json").read_text())


def test_prompters_and_map(chain):
    r = build(chain)
    assert r.returncode == 0, r.stdout
    th = (chain.dir / "th.prompter.md").read_text()
    vo = (chain.dir / "vo.prompter.md").read_text()
    assert re.findall(r"^## (\S+)$", th, re.M) == ["b01", "b02", "b04"]
    assert re.findall(r"^## (\S+)$", vo, re.M) == ["b03a", "b03b"]
    # every non-spoken line is a heading, including the director's notes
    for text in (th, vo):
        for line in text.splitlines():
            assert not line or line.startswith("#") or line[0].isupper()
    assert "## b01\n\n### Delivery: warm\n\nWelcome back" in th
    assert "## b03a\n\n### On screen: settings panel\n\nOpen the" in vo
    m = load_map(chain)["prompters"]
    assert [(e["s"], e["n"], e["segment"]) for e in m["th"]["sentences"]] == [
        (1, 1, "b01"), (2, 2, "b01"), (3, 4, "b02"), (4, 9, "b04")]
    assert m["th"]["untimed"] == [{"n": 3, "segment": "b01", "text": "Fine."}]
    assert [e["segment"] for e in m["vo"]["sentences"]] == \
        ["b03a", "b03a", "b03b", "b03b"]
    assert validate_file(chain.dir / "prompter.map.json") == ("prompter-map", [])


def test_prompters_are_byte_stable(chain):
    build(chain)
    first = [(chain.dir / f).read_bytes() for f in ("th.prompter.md",
                                                     "vo.prompter.md")]
    assert run_script("build_prompters.py", chain.director).returncode == 0
    assert first == [(chain.dir / f).read_bytes() for f in ("th.prompter.md",
                                                             "vo.prompter.md")]


def test_hand_edited_prompter_is_caught(chain):
    build(chain)
    p = chain.dir / "vo.prompter.md"
    p.write_text(p.read_text().replace("left", "right"))
    kind, errs = validate_file(chain.dir / "prompter.map.json")
    assert any("vo.prompter.md has been edited since the map was built" in e
               for e in errs)


def test_segment_without_matchable_sentence(chain):
    def split_fine(d):
        d["segments"][0:1] = [
            {"id": "b01a", "beat": "b01", "sentences": [1, 2], "mode": "th"},
            {"id": "b01b", "beat": "b01", "sentences": [3, 3], "mode": "th"}]
    r = build(chain, d_mutate=split_fine)
    assert r.returncode == 1
    assert "b01b: no sentence long enough for take matching" in r.stdout
    assert not (chain.dir / "th.prompter.md").exists()


def test_quoted_question_straddle_is_mapped_not_refused(chain):
    """A segment ending ?" isn't a boundary to split_sentences, so one cut
    sentence covers the end of b02 and the start of b04 on the TH prompter.
    It's recorded against both segments for conform to split."""
    chain.script_md.write_text(chain.script_md.read_text().replace(
        "This line is personal and goes to camera.",
        'Then I ask it, "is this personal enough?"'))
    r = build(chain)
    assert r.returncode == 0, r.stdout
    th = load_map(chain)["prompters"]["th"]["sentences"]
    assert th[2] == {"s": 3, "n": [4, 9], "segment": ["b02", "b04"]}
    assert validate_file(chain.dir / "prompter.map.json") == ("prompter-map", [])


def test_zero_sentence_segment_is_caught_by_director_validation(chain):
    def split_fine(d):
        d["segments"][0:1] = [
            {"id": "b01a", "beat": "b01", "sentences": [1, 2], "mode": "th"},
            {"id": "b01b", "beat": "b01", "sentences": [3, 3], "mode": "th"}]
    chain.build(d_mutate=split_fine)
    kind, errs = validate_file(chain.director)
    assert any("b01b: no sentence long enough for take matching" in e
               for e in errs)


def test_invalid_director_is_refused(chain):
    r = build(chain, d_mutate=lambda d: d.update(cues=[]))
    assert r.returncode == 1 and "doesn't validate" in r.stdout


def test_map_s_numbers_are_what_the_cut_reports(chain, tmp_path):
    """Read each prompter aloud (synthetically), cut it, and check every
    s the cut times lands in the segment the map says, word for word."""
    build(chain)
    m = load_map(chain)["prompters"]
    script = json.loads(chain.script_json.read_text())
    by_n = {s["n"]: s["text"] for s in script["sentences"]}
    for mode in ("th", "vo"):
        prompter = chain.dir / f"{mode}.prompter.md"
        spoken = [l for l in prompter.read_text().splitlines()
                  if l and not l.startswith("#")]
        tr = tmp_path / f"{mode}.transcript.json"
        tr.write_text(json.dumps(transcript([(1.2, p) for p in spoken])))
        out = tmp_path / f"{mode}.sentences.json"
        r = subprocess.run([sys.executable, str(SCRIPTS / "match_takes.py"),
                            tr, prompter, "-o", tmp_path / f"{mode}.cuts.json",
                            "--sentences-out", out],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        timed = {s["s"]: s for s in json.loads(out.read_text())["sentences"]}
        for e in m[mode]["sentences"]:
            got = " ".join(w["w"] for w in timed[e["s"]]["words"])
            ns = e["n"] if isinstance(e["n"], list) else [e["n"]]
            assert got == " ".join(by_n[n] for n in ns), (mode, e)
