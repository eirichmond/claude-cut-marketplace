"""Assemble v0.6: approved renders on lanes 3 (full frame) and 4 (overlays)
at their cues' exact frames, the SFX stem as one clip from 0:00 on lane -2
with a marker per effect, markers only for what isn't placed, and the gate:
stale renders, wrong frame counts and unapproved cues are refused.
Renders use the ffmpeg stand-in (CLAUDE_CUT_FAKE_RENDER)."""
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction

import pytest

from conftest import (SCRIPTS, graphics_body, graphics_world, run_script,
                      write_graphics_spec)
from review import items, read_manifest, write_manifest

pytestmark = pytest.mark.skipif(not (shutil.which("node") and shutil.which("ffmpeg")),
                                reason="needs node and ffmpeg")
FPS = 25


def rt(s):
    return Fraction(s.rstrip("s") or 0)


def render(world, *extra):
    return subprocess.run([sys.executable, str(SCRIPTS / "render_graphics.py"),
                           str(world["gfx"]), "--shoot", str(world["shoot"]), *extra],
                          capture_output=True, text=True,
                          env={**os.environ, "CLAUDE_CUT_FAKE_RENDER": "1"})


def assemble(world, *extra, out="mcp_assembled.fcpxml"):
    return run_script("assemble.py", "--plan", world["dir"] / "plan.resolved.json",
                      "--shoot", world["shoot"], "-o", world["dir"] / out, *extra)


def approve_all(world):
    doc = read_manifest(world["gfx"])
    for _, e in items(doc):
        e["review"] = {"status": "approved", "note": ""}
    write_manifest(world["gfx"], doc)


def placed(root):
    """(lane, name, timeline start frame, frames, ref) for every connected clip."""
    out = []
    spine = root.find("./library/event/project/sequence/spine")
    for parent in spine:
        p_off, p_start = rt(parent.get("offset")), rt(parent.get("start"))
        for c in parent.findall("asset-clip"):
            if c.get("lane"):
                at = (p_off + rt(c.get("offset")) - p_start) * FPS
                out.append((c.get("lane"), c.get("name"), int(at),
                            int(rt(c.get("duration")) * FPS), c.get("ref"),
                            c.get("srcEnable")))
    return out


def edl_names(world, name="mcp_markers.edl"):
    text = (world["dir"] / name).read_text()
    return [l.split("|M:")[1].split(" |D:")[0] for l in text.splitlines() if "|M:" in l]


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    w = graphics_world(tmp_path_factory.mktemp("asm6"))
    d = w["dir"]
    vo_len = json.loads((d / "cut" / "vo" / "transcript.json").read_text())["duration"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"anullsrc=r=48000:cl=mono:d={vo_len}", str(d / "vo.wav")], check=True)
    body = graphics_body(w)
    skipped = next(g for g in body["graphics"] if g["template"] == "lowerThird")
    body["graphics"].remove(skipped)
    body["skip"].append({"cue": skipped["cue"], "reason": "the screen shows it"})
    write_graphics_spec(w, body)
    r = render(w)
    assert r.returncode == 0, r.stderr + r.stdout
    w["skipped"] = skipped["cue"]
    w["manifest"] = read_manifest(w["gfx"])
    return w


def test_unapproved_graphics_are_refused(world):
    r = assemble(world, out="pending_assembled.fcpxml")
    assert r.returncode == 1
    assert "not approved yet" in r.stderr and "--allow-unreviewed" in r.stderr
    assert not (world["dir"] / "pending_assembled.fcpxml").exists()


def test_allow_unreviewed_places_them_with_red_markers(world):
    r = assemble(world, "--allow-unreviewed", out="unrev_assembled.fcpxml")
    assert r.returncode == 0, r.stderr
    names = edl_names(world, "unrev_markers.edl")
    n = len(world["manifest"]["renders"])
    assert sum(x.startswith("UNREVIEWED") or " + UNREVIEWED" in x for x in names) >= 1
    assert sum(x.count("UNREVIEWED") for x in names) == \
        n + len(world["manifest"]["sfx"]["items"])
    report = (world["dir"] / "assemble-report.md").read_text()
    assert "Placed without approval" in report


@pytest.fixture(scope="module")
def approved(world):
    approve_all(world)
    r = assemble(world)
    assert r.returncode == 0, r.stderr + r.stdout
    root = ET.parse(world["dir"] / "mcp_assembled.fcpxml").getroot()
    return {"root": root, "clips": placed(root), "stdout": r.stdout}


def test_renders_land_on_their_lanes_at_their_cues_frames(world, approved):
    cues = {c["id"]: c for c in world["plan"]["cues"]}
    got = {name: (lane, at, n, src) for lane, name, at, n, _, src in approved["clips"]
           if lane in ("3", "4")}
    renders = world["manifest"]["renders"]
    assert set(got) == {r["cue"] for r in renders}
    for r in renders:
        lane, at, n, src = got[r["cue"]]
        assert lane == ("3" if r["layer"] == "full" else "4"), r["cue"]
        assert (at, at + n) == tuple(cues[r["cue"]]["tl"]), r["cue"]
        assert src == "video"
    assert any(l == "3" for l, *_ in got.values()) and any(l == "4" for l, *_ in got.values())


def test_render_assets_point_at_the_renders(world, approved):
    res = approved["root"].find("resources")
    srcs = [a.find("media-rep").get("src") for a in res.findall("asset")
            if a.find("media-rep") is not None]
    for r in world["manifest"]["renders"]:
        assert any(s.endswith(f"/renders/{r['cue']}.mov") for s in srcs), r["cue"]


def test_sfx_stem_is_one_full_length_clip_from_the_start(world, approved):
    stems = [c for c in approved["clips"] if c[0] == "-2"]
    assert len(stems) == 1
    lane, name, at, n, _, _ = stems[0]
    assert (name, at, n) == ("SFX stem", 0, world["plan"]["timeline"]["frames"])


def test_markers_only_for_what_isnt_placed(world, approved):
    names = edl_names(world)
    joined = " + ".join(names)
    for r in world["manifest"]["renders"]:
        assert f"{r['cue']} " not in joined, r["cue"]          # placed: no marker
    for it in world["manifest"]["sfx"]["items"]:
        assert f"SFX {it['cue']}: Impact - Deep - Snap" in joined
    assert f"{world['skipped']} LT (skipped: the screen shows it)" in joined
    zoom = next(c["id"] for c in world["plan"]["cues"] if c["kind"] == "zoom")
    assert f"{zoom} ZOOM" in joined                            # never rendered
    report = (world["dir"] / "assemble-report.md").read_text()
    assert "full-frame" in report and "Skipped in the graphics stage (1)" in report
    assert "graphics, SFX stem" in approved["stdout"]


def test_no_graphics_keeps_every_cue_a_marker(world, approved):
    r = assemble(world, "--no-graphics", out="plain_assembled.fcpxml")
    assert r.returncode == 0, r.stderr
    root = ET.parse(world["dir"] / "plain_assembled.fcpxml").getroot()
    assert not [c for c in placed(root) if c[0] in ("3", "4", "-2")]
    joined = " + ".join(edl_names(world, "plain_markers.edl"))
    assert all(f"{r['cue']} " in joined for r in world["manifest"]["renders"])


def test_a_render_with_the_wrong_length_is_refused(world, approved):
    r0 = world["manifest"]["renders"][0]
    f = world["gfx"] / r0["file"]
    keep = f.read_bytes()
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "color=c=black:s=320x180:r=25:d=0.4", "-c:v", "prores_ks",
                        str(f)], check=True)
        r = assemble(world, out="bad_assembled.fcpxml")
        assert r.returncode == 1
        assert f"{r0['cue']}: the render is 10 frames" in r.stderr
    finally:
        f.write_bytes(keep)


def test_stale_renders_are_refused(world, approved):
    spec = world["gfx"] / "graphics.json"
    keep = spec.read_text()
    try:
        doc = json.loads(keep)
        doc["sfx"][0]["gain_db"] = -3
        spec.write_text(json.dumps(doc))
        r = assemble(world, out="stale_assembled.fcpxml")
        assert r.returncode == 1 and "graphics.json has changed" in r.stderr
    finally:
        spec.write_text(keep)
    plan = world["dir"] / "plan.resolved.json"
    keep = plan.read_text()
    try:
        plan.write_text(keep.replace('"warnings": [', '"warnings": ["edited", ', 1))
        r = assemble(world, out="stale_assembled.fcpxml")
        assert r.returncode == 1 and "plan has changed" in r.stderr
    finally:
        plan.write_text(keep)
