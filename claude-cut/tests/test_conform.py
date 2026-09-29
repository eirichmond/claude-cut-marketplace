"""Conform on synthetic recordings of the real MCP prompters (and the mini
chain), through the real cut and edit-takes timeline."""
import json
import re
import shutil
from fractions import Fraction

import pytest

from conftest import FIXTURES, run_conform, run_script, synthetic_cut
from validate import validate_file

MCP = FIXTURES / "mcp-setup"
FPS = 25


def frames(t):
    return round(Fraction(t).limit_denominator(10**6) * FPS)


@pytest.fixture(scope="module")
def mcp(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("mcp")
    expected = synthetic_cut(MCP, tmp / "cut")
    out = tmp / "plan.resolved.json"
    r = run_conform(MCP / "mcp-setup.director.json", MCP / "prompter.map.json",
                    tmp / "cut", out)
    assert r.returncode == 0, r.stdout
    return {"plan": json.loads(out.read_text()), "path": out,
            "expected": expected, "cut": tmp / "cut", "stdout": r.stdout}


def test_plan_validates(mcp):
    assert validate_file(mcp["path"]) == ("plan-resolved", [])


def test_only_the_expected_warnings(mcp):
    w = mcp["plan"]["warnings"]
    assert len(w) == 2, w
    assert w[0].startswith("b01: absorbed 2.5s of kept off-script material")
    assert w[1].startswith("s38 (vo) runs across b28 and b29: split at")


def test_every_take_lands_in_its_segment_and_no_fluff_survives(mcp):
    segs = {s["id"]: s for s in mcp["plan"]["segments"]}
    all_ranges = [(r, s["mode"]) for s in segs.values()
                  for r in s["source"]["ranges"]]
    for mode, utts in mcp["expected"].items():
        for u in utts:
            if u["role"] == "take":
                rs = segs[u["segment"]]["source"]["ranges"]
                assert rs[0][0] <= u["start"] and u["end"] <= rs[-1][1], u
            if u["role"] in ("fluff", "marker"):
                assert not any(m == mode and a < u["end"] and u["start"] < b
                               for (a, b), m in all_ranges), u


def test_timeline_tiles_with_no_gaps_or_overlaps(mcp):
    p = mcp["plan"]
    spans = [s["tl"] for s in p["segments"]] + \
        [c["tl"] for c in p["cues"] if c["placement"].startswith("insert")]
    spans.sort()
    assert spans[0][0] == 0
    for a, b in zip(spans, spans[1:]):
        assert a[1] == b[0], (a, b)
    assert spans[-1][1] == p["timeline"]["frames"]


def test_th_segments_tile_the_edit_takes_timeline(mcp):
    th = [s for s in mcp["plan"]["segments"] if s["mode"] == "th"]
    assert th[0]["th_tl"][0] == 0
    for a, b in zip(th, th[1:]):
        assert a["th_tl"][1] == b["th_tl"][0]
    for s in th:
        assert s["tl"][1] - s["tl"][0] == s["th_tl"][1] - s["th_tl"][0]
    ranges = json.loads((mcp["cut"] / "th" / "cuts.json").read_text())["ranges"]
    assert th[-1]["th_tl"][1] == sum(frames(r["end"]) - frames(r["start"])
                                     for r in ranges)


def test_vo_lengths_come_from_the_vo_cut(mcp):
    vo = [s for s in mcp["plan"]["segments"] if s["mode"] == "vo"]
    for s in vo:
        assert s["tl"][1] - s["tl"][0] == sum(frames(e) - frames(a)
                                              for a, e in s["source"]["ranges"])
    cut = json.loads((mcp["cut"] / "vo" / "cuts.json").read_text())["ranges"]
    assert sum(len(s["source"]["ranges"]) for s in vo) == len(cut)


def test_every_vo_segment_has_one_bed_covering_it(mcp):
    p = mcp["plan"]
    for s in p["segments"]:
        if s["mode"] != "vo":
            continue
        beds = [c for c in p["cues"]
                if c["placement"] == "bed" and c["segment"] == s["id"]]
        assert len(beds) == 1 and beds[0]["tl"] == s["tl"], s["id"]


def test_straddle_split_at_the_pause_midpoint(mcp):
    p = mcp["plan"]
    s38 = next(s for s in json.loads(
        (mcp["cut"] / "vo" / "sentences.json").read_text())["sentences"]
        if s["s"] == 38)
    words = s38["words"]
    # the quoted question ends sentence 75 (b28); b29 starts after it
    i = next(i for i, w in enumerate(words) if w["w"].endswith('?"'))
    midpoint = round((words[i]["end"] + words[i + 1]["start"]) / 2, 3)
    b28, b29 = (next(s for s in p["segments"] if s["id"] == sid)
                for sid in ("b28", "b29"))
    # the pause between them was cut, so the split sits in the gap
    assert b28["source"]["ranges"][-1][1] <= midpoint \
        <= b29["source"]["ranges"][0][0]
    assert f"split at {midpoint:.2f}s" in p["warnings"][1]
    assert {"tl": b29["tl"][0], "kind": "check",
            "name": "CHECK split b28/b29"} in p["markers"]


def test_chapter_markers(mcp):
    pe = json.loads((MCP / "mcp-setup.paper-edit.json").read_text())
    names = [b["chapter"] for b in pe["beats"] if b.get("chapter")]
    got = [m["name"] for m in mcp["plan"]["markers"] if m["kind"] == "chapter"]
    assert got == names
    assert mcp["plan"]["markers"][0] == {"tl": 0, "kind": "chapter",
                                         "name": names[0]}


# --- fails loudly ----------------------------------------------------------------

@pytest.fixture
def mcp_copy(tmp_path, mcp):
    """A writable copy of the MCP fixture chain and its synthetic cut."""
    shutil.copytree(MCP, tmp_path / "fx")
    shutil.copytree(mcp["cut"], tmp_path / "cut")
    return tmp_path


def conform_copy(root, *extra):
    fx = root / "fx"
    return run_conform(fx / "mcp-setup.director.json", fx / "prompter.map.json",
                       root / "cut", root / "plan.json", *extra)


def test_hand_edited_prompter_fails(mcp_copy):
    p = mcp_copy / "fx" / "vo.prompter.md"
    p.write_text(p.read_text().replace("Subscriber", "Contributor", 1))
    r = conform_copy(mcp_copy)
    assert r.returncode == 1
    assert "vo.prompter.md has been edited since the map was built" in r.stdout
    assert not (mcp_copy / "plan.json").exists()


def test_cut_against_another_prompter_fails(mcp_copy):
    s = mcp_copy / "cut" / "th" / "sentences.json"
    doc = json.loads(s.read_text())
    doc["inputs"]["script"]["sha256"] = "0" * 64
    s.write_text(json.dumps(doc))
    r = conform_copy(mcp_copy)
    assert r.returncode == 1
    assert "th: sentences.json was cut against a different th.prompter.md" \
        in r.stdout


def test_every_mismatch_is_listed(mcp_copy):
    """A renamed sub-ID and a deleted map entry, reported together."""
    m = mcp_copy / "fx" / "prompter.map.json"
    doc = json.loads(m.read_text())
    vo = doc["prompters"]["vo"]["sentences"]
    renamed = next(e for e in vo if e["segment"] == "b06a")
    renamed["segment"] = "b06x"
    th = doc["prompters"]["th"]["sentences"]
    th.pop()
    m.write_text(json.dumps(doc))
    r = conform_copy(mcp_copy)
    assert r.returncode == 1
    assert "Conform failed: 2 problem(s)" in r.stdout, r.stdout
    assert "vo: map segment b06x isn't in the director file" in r.stdout
    assert "th: the cut has 82 sentences, the map 81" in r.stdout


def missing_paragraph(expected):
    """(mode, segment, text) of a take that wasn't retaken, in a segment
    with more than one paragraph."""
    for mode, utts in expected.items():
        by_seg = {}
        for prev, u in zip([None] + utts, utts):
            if u["role"] == "take":
                by_seg.setdefault(u["segment"], []).append(
                    (u, prev and prev["role"] == "marker"))
        for seg, takes in by_seg.items():
            for u, retaken in takes[1:]:
                if not retaken:
                    return mode, seg, u["text"]
    raise AssertionError("no suitable paragraph")


def test_missing_sentence_fails_unless_allowed(mcp, tmp_path):
    mode, seg, text = missing_paragraph(mcp["expected"])
    synthetic_cut(MCP, tmp_path / "cut",
                  keep=lambda m, u: not (m == mode and u["text"] == text))
    r = run_conform(MCP / "mcp-setup.director.json", MCP / "prompter.map.json",
                    tmp_path / "cut", tmp_path / "plan.json")
    assert r.returncode == 1
    assert f"({seg}) wasn't found in the recording" in r.stdout

    r = run_conform(MCP / "mcp-setup.director.json", MCP / "prompter.map.json",
                    tmp_path / "cut", tmp_path / "plan.json", "--allow-missing")
    assert r.returncode == 0, r.stdout
    assert f"({seg}) wasn't found in the recording" in r.stdout


def test_whole_segment_missing_fails_even_when_allowed(mcp, tmp_path):
    synthetic_cut(MCP, tmp_path / "cut",
                  keep=lambda mode, u: u["segment"] != "b07")
    r = run_conform(MCP / "mcp-setup.director.json", MCP / "prompter.map.json",
                    tmp_path / "cut", tmp_path / "plan.json", "--allow-missing")
    assert r.returncode == 1
    assert "b07: nothing kept for this segment in the VO recording" in r.stdout


# --- partial recordings (--segments) ----------------------------------------------

def test_segments_scope_conforms_a_partial_recording(tmp_path):
    first = {"b01", "b02", "b03", "b04", "b05"}
    synthetic_cut(MCP, tmp_path / "cut",
                  keep=lambda mode, u: u["segment"] in first or
                  u["role"] == "off-script")
    out = tmp_path / "plan.json"
    r = run_conform(MCP / "mcp-setup.director.json", MCP / "prompter.map.json",
                    tmp_path / "cut", out, "--segments", "b01-b05")
    assert r.returncode == 0, r.stdout
    plan = json.loads(out.read_text())
    assert [s["id"] for s in plan["segments"]] == ["b01", "b02", "b03", "b04",
                                                    "b05"]
    assert plan["scope"] == "b01-b05"


def test_kept_material_outside_the_scope_fails(mcp):
    r = run_conform(MCP / "mcp-setup.director.json", MCP / "prompter.map.json",
                    mcp["cut"], mcp["cut"].parent / "scoped.json",
                    "--segments", "b01-b05")
    assert r.returncode == 1
    assert "th: s13 was kept but its segment b06b is outside --segments" \
        in r.stdout
    assert re.search(r"vo: s\d+ was kept but its segment b06a is outside "
                     r"--segments", r.stdout)


# --- untimed anchors (the mini chain's b01.lt1 is anchored to "Fine.") --------------

def test_untimed_anchor_is_placed_at_the_next_timed_word(chain, tmp_path):
    chain.build()
    assert run_script("build_prompters.py", chain.director).returncode == 0
    synthetic_cut(chain.dir, tmp_path / "cut")
    out = tmp_path / "plan.json"
    r = run_conform(chain.director, chain.dir / "prompter.map.json",
                    tmp_path / "cut", out)
    assert r.returncode == 0, r.stdout
    plan = json.loads(out.read_text())
    assert any(w.startswith('b01.lt1: anchor sentence 3 "Fine." is untimed; '
                            'placed at the next timed word')
               for w in plan["warnings"])
    # the next timed word after sentence 2 is sentence 4's first, in b02
    th = json.loads((tmp_path / "cut" / "th" / "sentences.json").read_text())
    word = th["sentences"][2]["words"][0]           # s3 on the TH prompter = n4
    assert word["w"] == "This"
    b02 = next(s for s in plan["segments"] if s["id"] == "b02")
    expect = b02["tl"][0] + frames(word["start"]) - \
        frames(b02["source"]["ranges"][0][0])
    lt1 = next(c for c in plan["cues"] if c["id"] == "b01.lt1")
    assert lt1["segment"] == "b01"
    assert lt1["tl"][0] == expect


def test_straddle_inside_one_kept_range_splits_at_the_midpoint(chain, tmp_path):
    """b02 ends with a quoted question and b04 follows straight on (0.3s),
    so both sentences sit in one kept range: the split has to land exactly
    halfway through the pause between them."""
    chain.script_md.write_text(chain.script_md.read_text().replace(
        "This line is personal and goes to camera.",
        'Then I ask it, "is this personal enough?"'))
    chain.build()
    assert run_script("build_prompters.py", chain.director).returncode == 0
    synthetic_cut(chain.dir, tmp_path / "cut", segment_pause=0.3)
    out = tmp_path / "plan.json"
    r = run_conform(chain.director, chain.dir / "prompter.map.json",
                    tmp_path / "cut", out)
    assert r.returncode == 0, r.stdout
    plan = json.loads(out.read_text())
    th = json.loads((tmp_path / "cut" / "th" / "sentences.json").read_text())
    words = th["sentences"][2]["words"]            # s3 = n4 + n9
    i = next(i for i, w in enumerate(words) if w["w"].endswith('?"'))
    midpoint = round((words[i]["end"] + words[i + 1]["start"]) / 2, 3)
    b02, b04 = (next(s for s in plan["segments"] if s["id"] == sid)
                for sid in ("b02", "b04"))
    assert b02["source"]["ranges"][-1][1] == midpoint
    assert b04["source"]["ranges"][0][0] == midpoint
    assert any("s3 (th) runs across b02 and b04" in w for w in plan["warnings"])


@pytest.mark.slow
def test_real_audio_through_whisper_conforms(chain, tmp_path):
    """The mini prompters spoken by macOS say (with a fluff and 'retake cut'),
    TH muxed onto a timecoded dummy A-roll, all through real whisper
    transcription, take matching, the edit-takes timeline and conform."""
    import shutil
    from test_vo import whisper_ready
    if not whisper_ready():
        pytest.skip("needs macOS say, ffmpeg and faster-whisper")
    chain.build()
    assert run_script("build_prompters.py", chain.director).returncode == 0
    media = tmp_path / "media"
    r = run_script("../tests/make_synthetic_fixture.py", chain.dir, "-o", media,
                   "--audio", "--fluff-every", "2")
    assert r.returncode == 0, r.stderr
    cut = tmp_path / "cut"
    for mode, src in (("th", media / "aroll.mp4"), ("vo", media / "vo.wav")):
        d = cut / mode
        d.mkdir(parents=True)
        assert run_script("transcribe.py", src, "-o",
                          d / "transcript.json").returncode == 0
        r = run_script("match_takes.py", d / "transcript.json",
                       chain.dir / f"{mode}.prompter.md", "-o", d / "cuts.json",
                       "--report", d / "report.md",
                       "--sentences-out", d / "sentences.json")
        assert r.returncode == 0, r.stderr
    r = run_script("build_xml.py", cut / "th" / "cuts.json", "--aroll",
                   media / "aroll.mp4", "-o", cut / "th" / "cut.fcpxml")
    assert r.returncode == 0, r.stderr
    out = tmp_path / "plan.json"
    r = run_conform(chain.director, chain.dir / "prompter.map.json", cut, out)
    assert r.returncode == 0, r.stdout
    plan = json.loads(out.read_text())
    assert [s["id"] for s in plan["segments"]] == ["b01", "b02", "b03a",
                                                    "b03b", "b04"]
    # every fluff said before a 'retake cut' is outside the conformed plan
    expected = json.loads((media / "expected.json").read_text())["recordings"]
    for mode, utts in expected.items():
        ranges = [r for s in plan["segments"] if s["mode"] == mode
                  for r in s["source"]["ranges"]]
        for u in utts:
            if u["role"] == "fluff":
                assert not any(a < u["end"] - 0.3 and u["start"] + 0.3 < b
                               for a, b in ranges), (mode, u)
