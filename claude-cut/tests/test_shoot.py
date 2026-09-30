"""shoot.py: the shoot pack from the director, scanning a footage folder
into a shoot.json draft (with questions for what it can't place), and
writing a checked shoot.json."""
import json

import pytest

from conftest import FIXTURES, run_script
from validate import validate_file

MCP = FIXTURES / "mcp-setup"
DIRECTOR = MCP / "mcp-setup.director.json"


def shoot(*args):
    return run_script("shoot.py", *args)


def touch(folder, *names):
    for n in names:
        p = folder / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")


def sr_br_ids():
    from shoot import captures
    return [c["id"] for c in captures(DIRECTOR)["captures"]]


def test_pack_lists_sessions_habit_captures_and_blur_list(tmp_path):
    r = shoot("pack", "--director", DIRECTOR, "-o", tmp_path / "pack.md")
    assert r.returncode == 0, r.stderr
    text = (tmp_path / "pack.md").read_text()
    assert "Read **`th.prompter.md`**" in text and "Read **`vo.prompter.md`**" in text
    assert '"retake cut"' in text
    ids = sr_br_ids()
    assert f"Screen recordings and b-roll ({len(ids)})" in text
    for cid in ids:                                     # every capture, with a name
        assert f"**`{cid}`**" in text and f"`{cid}." in text
    pe = json.loads((MCP / "mcp-setup.paper-edit.json").read_text())
    for b in pe["notes"]["blur_list"]:
        assert f"- {b}" in text
    # timeline order: b02's capture before b57's
    assert text.index("`b02.sr1`") < text.index("`b57.sr1`")


def test_pack_estimates_on_screen_time_and_the_words_under_it():
    from shoot import captures
    caps = {c["id"]: c for c in captures(DIRECTOR)["captures"]}
    c = caps["b02.sr1"]                                 # "Studio app" .. to a phrase
    assert c["mode"] == "th" and 2 <= c["seconds"] <= 8
    assert c["under"].startswith("Studio app")
    bed = next(c for c in caps.values() if c["mode"] == "vo")
    assert bed["seconds"] > 5                           # a whole VO segment


@pytest.fixture
def footage(tmp_path):
    ids = sr_br_ids()
    touch(tmp_path, "A-Roll.MP4", "B_roll.mov", "Voiceover.wav",
          f"screens/{ids[0].upper().replace('.', '-')} users page.mov",   # B02-SR1 …
          f"{ids[1].replace('.', '_')}.mov",
          f"{ids[2]}.mov", f"{ids[2]} take2.mov",                        # ambiguous
          "b99.sr1.mov",                                                 # no such cue
          "C0099.MP4",                                                   # unmatched
          "aroll_mono.wav", ".claude-cut/th/cut.wav", "notes.txt")       # ignored
    return tmp_path, ids


def test_scan_matches_names_and_asks_about_the_rest(footage):
    folder, ids = footage
    r = shoot("scan", folder, "--director", DIRECTOR)
    assert r.returncode == 0, r.stderr
    draft = json.loads((folder / "shoot.draft.json").read_text())
    assert draft["th"] == {"aroll": "A-Roll.MP4", "broll": "B_roll.mov"}
    (folder / ".claude-cut" / "offsets.json").write_text('{"offset_seconds": 1.5}')
    shoot("scan", folder, "--director", DIRECTOR)
    draft = json.loads((folder / "shoot.draft.json").read_text())
    assert draft["th"]["offsets"] == ".claude-cut/offsets.json"
    assert draft["vo"] == {"audio": "Voiceover.wav"}
    a = draft["assets"]
    assert set(a) == set(ids)
    assert a[ids[0]] == f"screens/{ids[0].upper().replace('.', '-')} users page.mov"
    assert a[ids[1]] == f"{ids[1].replace('.', '_')}.mov"
    assert a[ids[2]] is None and all(a[i] is None for i in ids[3:])
    q = " | ".join(draft["questions"])
    assert f"more than one file for {ids[2]}" in q
    assert "b99.sr1.mov names b99.sr1, which isn't" in q
    assert "C0099.MP4: not matched" in q
    assert "mono" not in q and "cut.wav" not in q and "notes" not in q
    assert f"Captures: 2 of {len(ids)} found" in r.stdout


def test_scan_asks_when_the_recordings_are_camera_named(tmp_path):
    touch(tmp_path, "C0012.MP4", "ZOOM0001.WAV")
    shoot("scan", tmp_path, "--director", DIRECTOR)
    q = json.loads((tmp_path / "shoot.draft.json").read_text())["questions"]
    assert any(x.startswith("no aroll file found") for x in q)
    assert any(x.startswith("no vo file found") for x in q)
    assert not any("no broll" in x for x in q)          # a second angle is optional


def test_write_checks_the_draft_and_stamps_shoot_json(footage):
    folder, ids = footage
    shoot("scan", folder, "--director", DIRECTOR)
    draft_path = folder / "shoot.draft.json"
    draft = json.loads(draft_path.read_text())
    draft["assets"][ids[2]] = f"{ids[2]} take2.mov"     # the user's answer
    draft["assets"]["b99.sr1"] = "b99.sr1.mov"
    draft["assets"][ids[3]] = "nowhere.mov"
    draft_path.write_text(json.dumps(draft))
    r = shoot("write", draft_path, "--director", DIRECTOR)
    assert r.returncode == 1
    assert "assets.b99.sr1: not a screen recording or b-roll cue" in r.stderr
    assert f"assets.{ids[3]}: nowhere.mov doesn't exist" in r.stderr
    assert not (folder / "shoot.json").exists()

    del draft["assets"]["b99.sr1"]
    draft["assets"][ids[3]] = None
    draft_path.write_text(json.dumps(draft))
    r = shoot("write", draft_path, "--director", DIRECTOR)
    assert r.returncode == 0, r.stderr
    doc = json.loads((folder / "shoot.json").read_text())
    assert validate_file(folder / "shoot.json") == ("shoot", [])
    assert doc["inputs"]["director"]["sha256"]
    assert "questions" not in doc
    assert doc["assets"][ids[2]] == f"{ids[2]} take2.mov"
    assert f"3 of {len(ids)} captures" in r.stdout


def test_write_needs_the_recordings(tmp_path):
    (tmp_path / "d.json").write_text(json.dumps({"th": {}, "assets": {}}))
    r = shoot("write", tmp_path / "d.json", "--director", DIRECTOR)
    assert r.returncode == 1
    assert "th.aroll is required" in r.stderr and "vo.audio is required" in r.stderr
