"""sfx_index.py: libraries, incremental indexing, search, suggest, snapshot."""
import json
import os
import shutil
import subprocess
import time

import pytest

from conftest import run_script
from validate import validate_file

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")

SOUNDS = ["Impacts/Impact - Deep - Snap.wav", "Impacts/Impact - Subdrop.wav",
          "Whooshes/Whoosh - Pan - Heavy.wav", "Whooshes/Whoosh - Swipe Screen - Fast.wav",
          "Clicks/Click - Keyboard 02.wav", "Extras/Bells Twinkle.wav", "Root Pop.wav"]


def tone(path, seconds=0.3, channels=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"sine=frequency=440:duration={seconds}:sample_rate=48000",
                    "-ac", str(channels), str(path)], check=True)


@pytest.fixture
def lib(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CUT_HOME", str(tmp_path / "home"))
    root = tmp_path / "Story Pack"
    for i, s in enumerate(SOUNDS):
        tone(root / s, 0.2 + i * 0.1, 1 if "Pop" in s else 2)
    (root / "Impacts" / "readme.txt").write_text("not audio")
    (root / "Impacts" / "broken.wav").write_text("not really a wav")
    return root


def sfx(*args):
    return run_script("sfx_index.py", *args)


def index(tmp_path):
    return json.loads((tmp_path / "home" / "sfx-index.json").read_text())


def test_register_build_and_validate(lib, tmp_path):
    assert sfx("add-library", "story", lib).returncode == 0
    r = sfx("build")
    assert r.returncode == 0, r.stderr
    assert "7 sounds in 1 library (7 probed, 0 unchanged)" in r.stdout
    assert "skipped (not readable audio): Impacts/broken.wav" in r.stdout
    doc = index(tmp_path)
    assert validate_file(tmp_path / "home" / "sfx-index.json") == ("sfx-index", [])
    by = {f["path"]: f for f in doc["files"]}
    assert by["Impacts/Impact - Deep - Snap.wav"]["category"] == "Impacts"
    assert by["Root Pop.wav"]["category"] == "" and by["Root Pop.wav"]["channels"] == 1
    assert by["Whooshes/Whoosh - Pan - Heavy.wav"]["duration"] == pytest.approx(0.4, abs=0.02)
    assert doc["libraries"] == {"story": str(lib.resolve())}


def test_rebuild_only_probes_changed_files(lib):
    sfx("add-library", "story", lib)
    sfx("build")
    assert "0 probed, 7 unchanged" in sfx("build").stdout
    time.sleep(0.01)
    tone(lib / "Impacts" / "Impact - Subdrop.wav", 1.5)
    assert "1 probed, 6 unchanged" in sfx("build").stdout


def test_an_unplugged_library_keeps_its_entries(lib, tmp_path):
    sfx("add-library", "story", lib)
    sfx("build")
    moved = tmp_path / "unplugged"
    lib.rename(moved)
    r = sfx("build")
    assert "library 'story' not found" in r.stdout
    assert len(index(tmp_path)["files"]) == 7


def test_search_ranks_by_brief_words_and_synonyms(lib):
    sfx("add-library", "story", lib)
    sfx("build")
    r = sfx("search", "Heavy rubber-stamp thud as the ACCESS stamp lands", "--limit", "3")
    first = r.stdout.splitlines()[0]
    assert "Impacts/" in first                        # thud/stamp -> impact
    r = sfx("search", "a quick swoosh as the panel slides", "--limit", "2")
    assert all("Whooshes/" in l for l in r.stdout.splitlines())
    r = sfx("search", "whoosh", "--category", "Impacts")
    assert "Whooshes/" not in r.stdout
    r = sfx("search", "keyboard typing")
    assert r.stdout.splitlines()[0].endswith("Click - Keyboard 02.wav  (0.6s)")


def test_suggest_gives_candidates_for_every_sfx_cue(lib, tmp_path):
    sfx("add-library", "story", lib)
    sfx("build")
    plan = {"cues": [
        {"id": "b01.sfx1", "kind": "sfx", "brief": "Heavy thud as the stamp lands"},
        {"id": "b05.sfx1", "kind": "sfx", "brief": "whoosh on the chapter wipe"},
        {"id": "b05.lt1", "kind": "lt", "brief": "not a sound"}]}
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    r = sfx("suggest", tmp_path / "plan.json", "-o", tmp_path / "c.json")
    assert r.returncode == 0 and "2 sfx cues" in r.stdout
    out = json.loads((tmp_path / "c.json").read_text())
    assert [c["cue"] for c in out] == ["b01.sfx1", "b05.sfx1"]
    assert out[0]["candidates"][0]["file"].startswith("Impacts/")
    assert out[1]["candidates"][0]["file"].startswith("Whooshes/")
    assert len(out[0]["candidates"]) <= 3


def test_snapshot_copies_the_index_into_a_project(lib, tmp_path):
    sfx("add-library", "story", lib)
    sfx("build")
    r = sfx("snapshot", tmp_path / "graphics")
    assert r.returncode == 0
    assert (tmp_path / "graphics" / "sfx-index.json").read_bytes() == \
        (tmp_path / "home" / "sfx-index.json").read_bytes()


def test_no_library_or_index_is_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CUT_HOME", str(tmp_path / "empty"))
    assert "No SFX libraries registered" in sfx("build").stderr
    assert "No SFX index yet" in sfx("search", "thud").stderr
