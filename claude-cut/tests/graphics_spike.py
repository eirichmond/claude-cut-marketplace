#!/usr/bin/env python3
"""v0.6 spike: do HyperFrames graphics and local SFX land in Resolve?

Usage:
    python tests/graphics_spike.py CUT_DIR [--recordings DIR] [--out DIR]

CUT_DIR is a real-recordings run's folder (pytest -m real leaves one with
th/, vo/ and offsets.json). The recordings default to /Volumes/Terrance/spiketest.

Builds, in OUT (default <recordings>/out/spike-graphics):
  - the v0.5 assembled timeline for the real b01-b08 recording
  - b04.lt1 rendered from the ported lowerThird template in identity/frame.md,
    at 60fps -> converted to the 25fps timeline, exact frame count, alpha kept
  - a fast horizontal slide, the same way, to judge judder
  - SFX from The Story Sound Pack on lane -2 (b01.sfx1 at 0dB, a whoosh on the
    slide at -6dB) with a silent full-length stereo spacer on the same lane
  - spike_graphics.fcpxml, stills at 1080p, and SPIKE-GRAPHICS.md
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "scripts"
sys.path[:0] = [str(SCRIPTS)]

import identity  # noqa: E402
from assemble import Timeline  # noqa: E402
from build_xml import rt  # noqa: E402

PY = sys.executable
MCP = HERE / "fixtures" / "mcp-setup"
HF = ["npx", "--yes", "hyperframes@0.8.71"]
SFX_LIB = Path("/Volumes/Terrance/assets/The Story Sound Pack")


def run(*cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd))}\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r.stdout


def probe_frames(path: Path) -> dict:
    out = run("ffprobe", "-v", "error", "-count_frames", "-show_entries",
              "stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,nb_read_frames",
              "-of", "json", path)
    return json.loads(out)["streams"][0]


def alpha_fraction(path: Path, at: float) -> float:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(at), "-i", str(path),
                          "-frames:v", "1", "-vf", "scale=480:270,format=rgba",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    a = raw[3::4]
    return sum(1 for x in a if x == 0) / max(1, len(a))


def tc(f: int, fps: int = 25) -> str:
    s, fr = divmod(f, fps)
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{fr:02d}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cut", type=Path)
    ap.add_argument("--recordings", type=Path, default=Path("/Volumes/Terrance/spiketest"))
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    rec = args.recordings
    out = (args.out or rec / "out" / "spike-graphics").resolve()
    work = out / "work"
    if out.exists():
        shutil.rmtree(out)
    work.mkdir(parents=True)

    # --- 1. the v0.5 timeline, rebuilt here so its paths stay valid --------------
    for d in ("th", "vo"):
        shutil.copytree(args.cut / d, work / d)
    shutil.copy(args.cut / "offsets.json", work / "offsets.json")
    # the TH timeline's source path is absolute, so the copy still points at it
    run(PY, SCRIPTS / "conform.py", "--director", MCP / "mcp-setup.director.json",
        "--map", MCP / "prompter.map.json", "--th", work / "th",
        "--th-fcpxml", work / "th" / "cut.fcpxml", "--vo", work / "vo",
        "-o", work / "plan.resolved.json", "--segments", "b01-b08")
    plan = json.loads((work / "plan.resolved.json").read_text())
    fps = Fraction(plan["timeline"]["fps"])
    aroll = next(p for p in rec.iterdir() if p.stem.lower().replace("-", "") == "aroll")
    broll = next((p for p in rec.iterdir()
                  if p.stem.lower().replace("-", "") == "broll"), None)
    vo = next(p for p in rec.iterdir() if p.stem.lower() == "vo")
    shoot = {"schema": "claude-cut/shoot@1",
             "th": {"aroll": str(aroll), "offsets": str(work / "offsets.json"),
                    "broll": str(broll) if broll else None},
             "vo": {"audio": str(vo)}, "assets": {}}
    (work / "shoot.json").write_text(json.dumps(shoot, indent=1))
    assembled = work / "spike_assembled.fcpxml"
    run(PY, SCRIPTS / "assemble.py", "--plan", work / "plan.resolved.json",
        "--shoot", work / "shoot.json", "-o", assembled)

    # --- 2. graphics: identity, compositions, 60fps renders, 25fps conversion ----
    gfx = out / "graphics"
    tok = identity.install(gfx)
    (gfx / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions"}}))
    lt = next(c for c in plan["cues"] if c["id"] == "b04.lt1")
    slide_seg = next(s for s in plan["segments"] if s["id"] == "b02")
    slide_at, slide_len = slide_seg["tl"][0] + 100, 38
    rows = [
        {"cue": "b04.lt1", "template": "lowerThird", "frames": lt["tl"][1] - lt["tl"][0],
         "fps": plan["timeline"]["fps"],
         "vars": {"kicker": "For those who don't know",
                  "head": "*mcp* = model context protocol",
                  "line": "A standard way for an AI agent to talk to a piece of software."}},
        {"cue": "spike.slide1", "template": "slideAcross", "frames": slide_len,
         "fps": plan["timeline"]["fps"], "vars": {"text": "fast slide test"}},
    ]
    (gfx / "rows.json").write_text(json.dumps(rows, indent=1))
    print(run("node", ROOT / "graphics" / "build.mjs", gfx, gfx / "rows.json"), end="")
    (gfx / "raw").mkdir()
    (gfx / "renders").mkdir()
    size = "landscape-4k" if plan["timeline"]["width"] >= 3840 else "landscape"
    results = {}
    for row in rows:
        cue, frames = row["cue"], row["frames"]
        raw = gfx / "raw" / f"{cue}.mov"
        run(*HF, "render", "-c", f"compositions/{cue}.html", "--fps", "60",
            "--format", "mov", "--resolution", size, "--quality", "delivery",
            "-o", f"raw/{cue}.mov", cwd=gfx)
        final = gfx / "renders" / f"{cue}.mov"
        run("ffmpeg", "-v", "error", "-y", "-i", raw, "-vf",
            f"fps={fps.numerator}/{fps.denominator}", "-frames:v", str(frames),
            "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le",
            "-vendor", "apl0", final)
        info = probe_frames(final)
        mid = frames / 2 / float(fps)
        results[cue] = {"frames": int(info["nb_read_frames"]), "want": frames,
                        "size": f"{info['width']}x{info['height']}",
                        "pix_fmt": info["pix_fmt"],
                        "transparent": round(alpha_fraction(final, mid), 2)}
        raw.unlink()
        if results[cue]["frames"] != frames:
            sys.exit(f"{cue}: {results[cue]['frames']} frames, wanted {frames}")

    # --- 3. a 1080p still of the lower third, fully revealed, over the A-roll ----
    seg = next(s for s in plan["segments"] if s["id"] == lt["segment"])
    reveal = 2.4                                   # seconds into the cue
    f = lt["tl"][0] + round(reveal * fps)
    src_t = seg["source"]["ranges"][0][0] + float((f - seg["tl"][0]) / fps)
    still = out / "still_lower_third_1080p.png"
    run("ffmpeg", "-v", "error", "-y", "-ss", f"{src_t:.3f}", "-i", aroll,
        "-ss", f"{reveal}", "-i", gfx / "renders" / "b04.lt1.mov", "-filter_complex",
        "[0:v]scale=1920:1080[a];[1:v]scale=1920:1080[o];[a][o]overlay=format=auto",
        "-frames:v", "1", still)
    crop = out / "still_lower_third_1080p_crop.png"
    run("ffmpeg", "-v", "error", "-y", "-i", still, "-vf", "crop=1280:420:60:640", crop)

    # --- 4. SFX + graft everything onto the assembled timeline -------------------
    whoosh = SFX_LIB / "Whooshes" / "Whoosh - Pan - Heavy.wav"
    impact = SFX_LIB / "Impacts" / "Impact - Deep - Snap.wav"
    total = plan["timeline"]["frames"]
    spacer = out / "sfx_spacer_silent.wav"
    run("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
        f"anullsrc=r=48000:cl=stereo:d={total / float(fps) + 1:.3f}",
        "-c:a", "pcm_s24le", spacer)

    t = Timeline.__new__(Timeline)
    t.tree = ET.parse(assembled)
    t.root = t.tree.getroot()
    t.fps, t.ids = fps, 500
    t.reindex()
    lt_id, _, _ = t.add_video_asset(gfx / "renders" / "b04.lt1.mov")
    sl_id, _, _ = t.add_video_asset(gfx / "renders" / "spike.slide1.mov")
    t.connect(lt["tl"][0], lt["tl"][1] - lt["tl"][0],
              {"ref": lt_id, "lane": "4", "name": "b04.lt1", "start": "0s"})
    t.connect(slide_at, slide_len,
              {"ref": sl_id, "lane": "4", "name": "spike.slide1", "start": "0s"})
    sp_id, _ = t.add_audio_asset(spacer)
    t.connect(0, total, {"ref": sp_id, "lane": "-2", "name": "SFX spacer (silent)",
                         "start": "0s"})
    wh_id, wh_dur = t.add_audio_asset(whoosh)
    clip = t.connect(slide_at, t.frames(wh_dur),
                     {"ref": wh_id, "lane": "-2", "name": "SFX whoosh (-6dB)",
                      "start": "0s"})
    ET.SubElement(clip, "adjust-volume", {"amount": "-6dB"})
    sfx_cue = next(c for c in plan["cues"] if c["id"] == "b01.sfx1")
    im_id, im_dur = t.add_audio_asset(impact)
    t.connect(sfx_cue["tl"][0], t.frames(im_dur),
              {"ref": im_id, "lane": "-2", "name": "b01.sfx1 impact (0dB)",
               "start": "0s"})
    final_fcp = out / "spike_graphics.fcpxml"
    t.write(final_fcp)
    shutil.copy(work / "spike_markers.edl", out / "spike_graphics_markers.edl")

    # --- 5. what to check -----------------------------------------------------------
    lt_tc, sl_tc = tc(lt["tl"][0]), tc(slide_at)
    rl = results["b04.lt1"]
    rs = results["spike.slide1"]
    lines = [
        "# v0.6 graphics spike: what to check", "",
        f"Import `{final_fcp}` (File > Import > Timeline, fresh project, auto-import on), "
        f"then its markers: Media Pool > right-click the timeline > Timelines > Import > "
        f"Timeline Markers from EDL > `spike_graphics_markers.edl`.", "",
        "Identity: `claude-cut/identity/frame.md` "
        f"({tok['name']}), fonts {', '.join(tok['font_files'])} from files.", "",
        "## Renders (checked here)", "",
        f"- `b04.lt1` lower third: {rl['frames']}/{rl['want']} frames at 25fps, "
        f"{rl['size']}, {rl['pix_fmt']}, {int(rl['transparent'] * 100)}% transparent mid-cue",
        f"- `spike.slide1` fast slide: {rs['frames']}/{rs['want']} frames, "
        f"{int(rs['transparent'] * 100)}% transparent mid-cue", "",
        "## In Resolve", "",
        f"1. **Transparency**: at **{lt_tc}** the lower third sits over your A-roll, "
        f"with you visible around the panel (not on black).",
        f"2. **Length and animation**: it builds on, holds and wipes off within "
        f"{rl['want']} frames ({lt_tc} to {tc(lt['tl'][1])}), with no jump or freeze.",
        f"3. **Judder**: at **{sl_tc}** the accent bar crosses the frame in about 0.6s. "
        f"Play it at full speed a few times: is the motion acceptable at 25fps?",
        "4. **Fonts**: the headline and body are Anton (tall, condensed); the eyebrow "
        "is DM Mono (monospaced, spaced capitals). Anything else means a font didn't load.",
        f"5. **Anton for body text**: read the line \"A standard way for an AI agent to "
        f"talk to a piece of software.\" in the viewer at 1080p (and in "
        f"`still_lower_third_1080p.png` / `_crop.png`). Comfortable to read, or not? "
        f"If not, body text switches to a readable face (Inter is ready locally).",
        f"6. **SFX on their own track**: the impact at **{tc(sfx_cue['tl'][0])}** and the "
        f"whoosh at **{sl_tc}** should share an audio track with a long silent clip "
        f"(\"SFX spacer\"), separate from the camera audio and the voiceover.",
        "7. **Gain**: the whoosh clip should show a volume of -6dB (Inspector > Audio), "
        "the impact 0dB.",
        "", "## Please report", "",
        "Pass/fail for 1-7, and which audio track numbers the camera, voiceover and SFX got.",
    ]
    (out / "SPIKE-GRAPHICS.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {final_fcp}\nChecklist: {out / 'SPIKE-GRAPHICS.md'}")
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
