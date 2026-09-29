"""Real recordings: cut -> conform on footage recorded for the MCP video.

Skipped unless CLAUDE_CUT_REAL_FIXTURE points at a folder (kept out of git,
e.g. on an external drive) holding:
    aroll.*        the talking-head recording (ZV-E10, with timecode)
    broll.*        optional second angle
    vo.wav         the voiceover, one continuous file (any audio format)
    segments.txt   the beats covered, e.g. "b01-b08"
recorded from tests/fixtures/mcp-setup/th.prompter.md and vo.prompter.md.

    CLAUDE_CUT_REAL_FIXTURE=/Volumes/Footage/mcp-real pytest -m real
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
    found = sorted(p for p in folder.glob(f"{stem}.*") if p.suffix != ".txt")
    return found[0] if found else None


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    src = Path(REAL)
    aroll, broll, vo = one(src, "aroll"), one(src, "broll"), one(src, "vo")
    scope = (src / "segments.txt").read_text().strip()
    assert aroll and vo, f"{src} needs aroll.* and vo.*"
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
                    out, plan, "--segments", scope)
    return {"out": out, "scope": scope, "conform": r, "plan": plan}


def test_real_recordings_conform(real):
    r = real["conform"]
    print(r.stdout)
    assert r.returncode == 0, r.stdout
    plan = json.loads(real["plan"].read_text())
    assert plan["scope"] == real["scope"]
    assert plan["segments"], "nothing conformed"
