"""Real recordings: cut -> conform -> assemble on footage recorded for the
MCP video.

Skipped unless CLAUDE_CUT_REAL_FIXTURE points at a folder (kept out of git,
e.g. on an external drive) holding:
    aroll.*        the talking-head recording (ZV-E10, with timecode)
    broll.*        optional second angle
    vo.*           the voiceover, one continuous file (any audio format)
    segments.txt   the beats covered, e.g. "b01-b08" (or set
                   CLAUDE_CUT_REAL_SEGMENTS=b01-b08 instead)
(names are matched ignoring case and hyphens: a-roll.MP4, VO.m4a are fine)
recorded from tests/fixtures/mcp-setup/th.prompter.md and vo.prompter.md.

    CLAUDE_CUT_REAL_FIXTURE=/Volumes/Footage/mcp-real pytest -m real

The assembled timeline, markers and report are written to
$CLAUDE_CUT_REAL_FIXTURE/out/ so they can be imported into Resolve.
"""
import json
import os
from pathlib import Path

import pytest

from conftest import FIXTURES, run_conform, run_script

REAL = os.environ.get("CLAUDE_CUT_REAL_FIXTURE")
MCP = FIXTURES / "mcp-setup"

pytestmark = [pytest.mark.real,
              pytest.mark.skipif(not REAL, reason="CLAUDE_CUT_REAL_FIXTURE not set")]


def one(folder: Path, stem: str) -> Path | None:
    """aroll.mp4, a-roll.MP4, A_Roll.mov ... all count as 'aroll'."""
    found = sorted(p for p in folder.iterdir()
                   if p.is_file() and p.suffix.lower() not in (".txt", ".md")
                   and p.stem.lower().replace("-", "").replace("_", "") == stem
                   and not p.stem.lower().endswith("_mono"))
    return found[0] if found else None


def scope(folder: Path) -> str:
    import re
    spec = os.environ.get("CLAUDE_CUT_REAL_SEGMENTS")
    if not spec and (folder / "segments.txt").exists():
        m = re.search(r"\bb\d{2,3}-b\d{2,3}\b",
                      (folder / "segments.txt").read_text(errors="replace"))
        spec = m.group(0) if m else None
    assert spec, ("say which beats were recorded: put e.g. b01-b08 in "
                  "segments.txt (plain text) or set CLAUDE_CUT_REAL_SEGMENTS")
    return spec


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    src = Path(REAL)
    aroll, broll, vo = one(src, "aroll"), one(src, "broll"), one(src, "vo")
    assert aroll and vo, f"{src} needs aroll.* and vo.*"
    scope_spec = scope(src)
    out = tmp_path_factory.mktemp("real")
    for mode, media in (("th", aroll), ("vo", vo)):
        d = out / mode
        d.mkdir()
        r = run_script("transcribe.py", media, "-o", d / "transcript.json")
        assert r.returncode == 0, r.stderr
        r = run_script("match_takes.py", d / "transcript.json",
                       MCP / f"{mode}.prompter.md", "-o", d / "cuts.json",
                       "--report", d / "report.md",
                       "--sentences-out", d / "sentences.json")
        assert r.returncode == 0, r.stderr
    args = [out / "th" / "cuts.json", "--aroll", aroll, "-o",
            out / "th" / "cut.fcpxml"]
    if broll:
        r = run_script("sync.py", aroll, broll, "-o", out / "offsets.json")
        assert r.returncode == 0, r.stderr
        args += ["--broll", broll, "--offsets", out / "offsets.json"]
    r = run_script("build_xml.py", *args)
    assert r.returncode == 0, r.stderr + r.stdout
    plan = out / "plan.resolved.json"
    r = run_conform(MCP / "mcp-setup.director.json", MCP / "prompter.map.json",
                    out, plan, "--segments", scope_spec)
    return {"out": out, "scope": scope_spec, "conform": r, "plan": plan,
            "aroll": aroll, "broll": broll, "vo": vo}


def test_real_recordings_conform(real):
    r = real["conform"]
    print(r.stdout)
    assert r.returncode == 0, r.stdout
    plan = json.loads(real["plan"].read_text())
    assert plan["scope"] == real["scope"]
    assert plan["segments"], "nothing conformed"


def test_real_recordings_assemble(real):
    assert real["conform"].returncode == 0, real["conform"].stdout
    dest = Path(REAL) / "out"
    dest.mkdir(exist_ok=True)
    shoot = real["out"] / "shoot.json"
    th = {"aroll": str(real["aroll"])}
    if real["broll"]:
        th.update(broll=str(real["broll"]),
                  offsets=str(real["out"] / "offsets.json"))
    shoot.write_text(json.dumps({"schema": "claude-cut/shoot@1", "th": th,
                                 "vo": {"audio": str(real["vo"])},
                                 "assets": {}}))
    out = dest / "mcp-real_assembled.fcpxml"
    r = run_script("assemble.py", "--plan", real["plan"], "--shoot", shoot,
                   "-o", out)
    print(r.stdout, r.stderr)
    assert r.returncode == 0, r.stderr
    assert (dest / "mcp-real_markers.edl").exists()
    assert (dest / "assemble-report.md").exists()
