"""Assemble on the synthetic MCP read: the timeline matches the plan, lanes
and assets land where the spike showed Resolve expects them, markers go to
an EDL, and bad inputs are refused."""
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from fractions import Fraction

import pytest

from conftest import FIXTURES, run_conform, run_script, synthetic_cut

MCP = FIXTURES / "mcp-setup"
FPS = 25


def rt(s):
    return Fraction(s.rstrip("s") or 0)


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("asm")
    synthetic_cut(MCP, d / "cut")
    r = run_conform(MCP / "mcp-setup.director.json", MCP / "prompter.map.json",
                    d / "cut", d / "plan.resolved.json")
    assert r.returncode == 0, r.stdout
    plan = json.loads((d / "plan.resolved.json").read_text())
    vo_len = json.loads((d / "cut" / "vo" / "transcript.json").read_text())["duration"]
    ffmpeg("-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={vo_len}",
           "-c:a", "pcm_s16le", d / "vo.wav")
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=40", "-c:v",
           "libx264", "-preset", "ultrafast", d / "sr.mp4")
    ffmpeg("-f", "lavfi", "-i", "color=c=0x663322:s=1080x1920:r=24:d=620",
           "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
           d / "broll.mov")
    (d / "offsets.json").write_text(json.dumps({"offset_seconds": 1.5}))
    beds = [c["id"] for c in plan["cues"] if c["kind"] in ("sr", "br")]
    assets = {cid: "sr.mp4" for cid in beds[:20]}
    assets.update({cid: None for cid in beds[20:25]})
    (d / "shoot.json").write_text(json.dumps({
        "schema": "claude-cut/shoot@1",
        "th": {"aroll": "cut/aroll.mp4", "broll": "broll.mov",
               "offsets": "offsets.json"},
        "vo": {"audio": "vo.wav"}, "assets": assets}))
    out = d / "mcp_assembled.fcpxml"
    r = run_script("assemble.py", "--plan", d / "plan.resolved.json",
                   "--shoot", d / "shoot.json", "-o", out)
    assert r.returncode == 0, r.stderr + r.stdout
    root = ET.parse(out).getroot()
    return {"dir": d, "plan": plan, "root": root, "out": out, "beds": beds,
            "assets": assets, "stdout": r.stdout,
            "spine": list(root.find("./library/event/project/sequence/spine"))}


def test_spine_is_contiguous_and_the_plans_length(built):
    cur = Fraction(0)
    for el in built["spine"]:
        assert rt(el.get("offset")) == cur, el.get("name")
        cur += rt(el.get("duration"))
    assert cur * FPS == built["plan"]["timeline"]["frames"]


def test_gaps_for_vo_and_inserts_clips_for_talking_heads(built):
    plan, spine = built["plan"], built["spine"]
    gaps = [e for e in spine if e.tag == "gap"]
    vo = [s for s in plan["segments"] if s["mode"] == "vo"]
    inserts = [c for c in plan["cues"] if c["placement"].startswith("insert")]
    assert len(gaps) == len(vo) + len(inserts)
    th_frames = sum(rt(e.get("duration")) * FPS for e in spine
                    if e.tag == "asset-clip")
    assert th_frames == sum(s["tl"][1] - s["tl"][0] for s in plan["segments"]
                            if s["mode"] == "th")


def test_th_clips_only_use_kept_source(built):
    """Every spine clip's source range sits inside a clip of the edit-takes
    timeline conform read."""
    src = ET.parse(built["dir"] / "cut" / "th" / "cut.fcpxml").getroot()
    kept = [(rt(c.get("start")), rt(c.get("start")) + rt(c.get("duration")))
            for c in src.iter("asset-clip")]
    for el in built["spine"]:
        if el.tag == "asset-clip":
            a = rt(el.get("start"))
            b = a + rt(el.get("duration"))
            assert any(ka <= a and b <= kb for ka, kb in kept), el.get("name")


def lane_clips(built, lane):
    return [(p, c) for p in built["spine"] for c in p
            if c.tag == "asset-clip" and c.get("lane") == lane]


def test_broll_angle_regrafted_on_the_split_clips(built):
    lane1 = lane_clips(built, "1")
    assert lane1 and all(p.tag == "asset-clip" for p, _ in lane1)
    assert "B-roll angle broll.mov" in (built["dir"] / "assemble-report.md").read_text()


def test_vo_on_lane_minus_one_from_a_mono_copy(built):
    plan = built["plan"]
    vo_clips = lane_clips(built, "-1")
    ranges = sum(len(s["source"]["ranges"]) for s in plan["segments"]
                 if s["mode"] == "vo")
    assert len(vo_clips) == ranges
    assert all(p.tag == "gap" for p, _ in vo_clips)
    ref = {c.get("ref") for _, c in vo_clips}
    asset = next(a for a in built["root"].iter("asset") if a.get("id") in ref)
    assert asset.get("name") == "vo_mono" and asset.get("audioChannels") == "1"
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=channels", "-of", "csv=p=0",
                          built["dir"] / "vo_mono.wav"],
                         capture_output=True, text=True).stdout.strip()
    assert out == "1"
    assert (built["dir"] / "vo.wav").exists()


def test_beds_with_assets_are_placed_video_only(built):
    lane2 = lane_clips(built, "2")
    assert sorted(c.get("name") for _, c in lane2) == \
        sorted(k for k, v in built["assets"].items() if v)
    assert all(c.get("srcEnable") == "video" for _, c in lane2)


def edl_markers(built):
    text = (built["dir"] / "mcp_markers.edl").read_text()
    return re.findall(r"^\d{3}  001 .*? (\d\d:\d\d:\d\d:\d\d) \d\d.*\n"
                      r" \|C:(\w+) \|M:(.*) \|D:(\d+)$", text, re.M)


def test_markers_edl_one_per_frame(built):
    marks = edl_markers(built)
    frames = [m[0] for m in marks]
    assert len(frames) == len(set(frames))


def test_markers_for_chapters_checks_missing_and_graphics(built):
    marks = edl_markers(built)
    by_colour = {}
    for tc, colour, name, dur in marks:
        by_colour.setdefault(colour, []).append(name)
    pe = json.loads((MCP / "mcp-setup.paper-edit.json").read_text())
    chapters = [b["chapter"] for b in pe["beats"] if b.get("chapter")]
    blue = " ".join(by_colour["ResolveColorBlue"])
    assert all(c in blue for c in chapters)
    red = " ".join(by_colour["ResolveColorRed"])
    assert "CHECK split b28/b29" in red
    missing = [c for c in built["beds"] if not built["assets"].get(c)]
    assert all(f"MISSING {c}" in red for c in missing)
    yellow = " ".join(by_colour["ResolveColorYellow"])
    graphic = [c["id"] for c in built["plan"]["cues"]
               if c["kind"] in ("mg", "lt", "callout", "zoom", "blur")]
    assert all(g in yellow + red + blue for g in graphic)


def test_markers_on_the_same_frame_are_merged(tmp_path):
    """Resolve keeps one marker per frame, so same-frame markers become one,
    coloured by the most urgent kind, as long as the longest."""
    from assemble import write_markers_edl
    p = tmp_path / "m.edl"
    n = write_markers_edl(p, [(0, "cue", "b01.mg1 MG: sting", 50),
                              (0, "cue", "b01.sfx1 SFX: low hit", 1),
                              (0, "missing", "MISSING b01.sr1", 10),
                              (30, "chapter", "Intro | part 1", 1)],
                          Fraction(25), "t")
    text = p.read_text()
    assert n == 2
    assert (" |C:ResolveColorRed |M:b01.mg1 MG: sting + b01.sfx1 SFX: low hit"
            " + MISSING b01.sr1 |D:50") in text
    assert "|M:Intro / part 1 |D:1" in text   # a | in a name would break the EDL
    assert "00:00:01:05 00:00:01:06" in text


def test_report_lists_missing_assets_and_import_steps(built):
    rep = (built["dir"] / "assemble-report.md").read_text()
    missing = [c for c in built["beds"] if not built["assets"].get(c)]
    assert f"## Not captured yet ({len(missing)})" in rep
    assert "Timelines > Import > Timeline Markers from EDL" in rep
    assert "made a mono copy vo_mono.wav" in rep


def test_short_asset_is_trimmed_and_reported(built):
    rep = (built["dir"] / "assemble-report.md").read_text()
    long_beds = [c for c in built["plan"]["cues"]
                 if built["assets"].get(c["id"]) and
                 c["tl"][1] - c["tl"][0] > 40 * FPS]
    for c in long_beds:
        assert f"`{c['id']}`: the file is 1000 frames" in rep
    for _, clip in lane_clips(built, "2"):
        assert rt(clip.get("duration")) <= 40


def test_assemble_is_deterministic(built, tmp_path):
    again = built["dir"] / "again_assembled.fcpxml"
    r = run_script("assemble.py", "--plan", built["dir"] / "plan.resolved.json",
                   "--shoot", built["dir"] / "shoot.json", "-o", again)
    assert r.returncode == 0, r.stderr
    assert again.read_bytes() == built["out"].read_bytes()
    assert "reused the mono copy" in \
        (built["dir"] / "assemble-report.md").read_text()


# --- refusals --------------------------------------------------------------------

def test_stale_plan_is_refused(built, tmp_path):
    """The edit-takes timeline was rebuilt after conform: refuse."""
    fcp = built["dir"] / "cut" / "th" / "cut.fcpxml"
    original = fcp.read_text()
    try:
        fcp.write_text(original.replace("aroll", "aroll2", 1))
        r = run_script("assemble.py", "--plan", built["dir"] / "plan.resolved.json",
                       "--shoot", built["dir"] / "shoot.json",
                       "-o", tmp_path / "x_assembled.fcpxml")
    finally:
        fcp.write_text(original)
    assert r.returncode == 1
    assert "has changed since this file was written" in r.stderr


def test_wrong_vo_file_is_refused(built, tmp_path):
    short = tmp_path / "short.wav"
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono:d=5", short)
    r = run_script("assemble.py", "--plan", built["dir"] / "plan.resolved.json",
                   "--shoot", built["dir"] / "shoot.json", "--vo", short,
                   "-o", tmp_path / "x_assembled.fcpxml")
    assert r.returncode == 1 and "wrong file?" in r.stderr


def test_wont_overwrite_the_edit_takes_timeline(built):
    r = run_script("assemble.py", "--plan", built["dir"] / "plan.resolved.json",
                   "--shoot", built["dir"] / "shoot.json",
                   "-o", built["dir"] / "cut" / "th" / "cut.fcpxml")
    assert r.returncode == 1 and "refusing to overwrite" in r.stderr
