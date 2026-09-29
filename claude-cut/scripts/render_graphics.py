#!/usr/bin/env python3
"""Render every graphic in graphics.json, mix the SFX stem, make review proxies.

Usage:
    python render_graphics.py GRAPHICS_DIR [--shoot shoot.json] [--only CUE,..]
                              [--quality delivery|draft] [--force] [--no-proxies]

GRAPHICS_DIR is the graphics project (identity installed, graphics.json
validated). For each graphic cue:

  1. templated cues are built from their template (graphics/build.mjs);
     custom compositions are used as authored, and must last exactly as
     long as the cue;
  2. a spec hash (composition, frames, fps, size, frame.md) decides whether
     it needs rendering; unchanged cues are reused, changed ones go back to
     review 'pending';
  3. HyperFrames renders at the timeline rate if it's 24/30/60, else at 60,
     and ffmpeg converts to the timeline rate with the cue's exact frame
     count: overlays as ProRes 4444 with alpha, full-frame as ProRes 422 HQ;
     the frame count is checked;
  4. a 720p h264 review proxy is made, overlays composited over the picture
     underneath them (A-roll, a supplied bed, or a plain plate).

Sound effects are mixed, with their gains, into one full-length stereo
sfx/sfx_stem.wav (Resolve gives a full-length clip its own track), and the
chosen files are copied to sfx/ by cue.

Everything is recorded in renders/manifest.json (claude-cut/graphics@1),
which assemble and the review page read.

CLAUDE_CUT_FAKE_RENDER=1 swaps HyperFrames for a quick ffmpeg stand-in with
the right timing (for tests).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from handoff import HandoffError, header, input_ref, load, resolve_input, sha256
from validate import validate_file

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "graphics" / "build.mjs"
HF = ["npx", "--yes", "hyperframes@0.8.71"]
NATIVE_FPS = (24, 30, 60)
RENDER_VERSION = "1"        # bump to force re-renders when the pipeline changes
PROXY = (1280, 720)


class RenderError(Exception):
    pass


def run(cmd, cwd=None) -> str:
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise RenderError(f"{' '.join(map(str, cmd[:4]))}... failed:\n"
                          f"{(r.stderr or r.stdout)[-2000:]}")
    return r.stdout


def count_frames(path: Path) -> int:
    out = run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
               "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path])
    return int(out.strip())


def transparent_share(path: Path, at: float) -> float:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{at:.3f}", "-i", str(path),
                          "-frames:v", "1", "-vf", "scale=320:180,format=rgba",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    a = raw[3::4]
    return round(sum(1 for x in a if x == 0) / max(1, len(a)), 3)


def comp_duration(html: str) -> float | None:
    m = re.search(r'data-composition-id="[^"]+"[^>]*data-duration="([\d.]+)"', html) \
        or re.search(r'data-duration="([\d.]+)"', html)
    return float(m.group(1)) if m else None


def local_files_hash(html: str, comp_dir: Path) -> str:
    """Hash of the local files a composition uses (assets/, fonts, GSAP), so
    replacing an image re-renders the cues that show it."""
    from custom import LOCAL
    h = hashlib.sha256()
    for ref in sorted({(m.group(1) or m.group(2) or "").strip()
                       for m in LOCAL.finditer(html)}):
        f = comp_dir / ref
        if ref and f.is_file():
            h.update(ref.encode() + sha256(f).encode())
    return h.hexdigest()


# --- rendering ---------------------------------------------------------------

def hyperframes(project: Path, comp: str, out: Path, fps: int, size: str,
                quality: str, seconds: float) -> None:
    if os.environ.get("CLAUDE_CUT_FAKE_RENDER"):
        # a transparent frame with a moving box: right length, right rate
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
             f"color=c=black@0.0:s=640x360:r={fps}:d={seconds:.6f},format=rgba,"
             f"drawbox=x='t*100':y=200:w=200:h=80:color=0x00C8E0@1:t=fill:replace=1",
             "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", out])
        return
    run([*HF, "render", "-c", comp, "--fps", str(fps), "--format", "mov",
         "--resolution", size, "--quality", quality, "-o",
         os.path.relpath(out, project)], cwd=project)


def convert(raw: Path, out: Path, fps: Fraction, frames: int, overlay: bool) -> None:
    codec = (["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le"]
             if overlay else
             ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"])
    run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vf",
         f"fps={fps.numerator}/{fps.denominator}", "-frames:v", str(frames),
         *codec, "-vendor", "apl0", out])


# --- the picture under a cue, for review proxies ----------------------------------

def context_still(plan: dict, cue: dict, shoot: dict | None, shoot_dir: Path | None,
                  out: Path) -> bool:
    """A still of what's under the cue at its midpoint. False = none known."""
    fps = Fraction(plan["timeline"]["fps"])
    f = (cue["tl"][0] + cue["tl"][1]) // 2
    seg = next((s for s in plan["segments"] if s["tl"][0] <= f < s["tl"][1]), None)
    if not seg or not shoot:
        return False

    def where(p):
        q = Path(p)
        return q if q.is_absolute() or not shoot_dir else shoot_dir / q

    src, t = None, None
    if seg["mode"] == "th":
        src = where(shoot["th"]["aroll"])
        pos = Fraction(f - seg["tl"][0]) / fps
        for a, b in seg["source"]["ranges"]:
            if pos <= Fraction(b - a).limit_denominator(10**6):
                t = a + float(pos)
                break
            pos -= Fraction(b - a).limit_denominator(10**6)
    else:
        bed = next((c for c in plan["cues"] if c["placement"] == "bed"
                    and c["segment"] == seg["id"]), None)
        path = (shoot.get("assets") or {}).get(bed["id"]) if bed else None
        if path:
            src = where(path)
            t = float(Fraction(f - bed["tl"][0]) / fps)
    if not src or t is None or not src.exists():
        return False
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(src),
                        "-frames:v", "1", "-vf", f"scale={PROXY[0]}:{PROXY[1]}", str(out)],
                       capture_output=True)
    return r.returncode == 0 and out.exists()


def make_proxy(render: Path, out: Path, overlay: bool, still: Path | None) -> None:
    w, h = PROXY
    if overlay:
        under = (["-loop", "1", "-i", str(still)] if still else
                 ["-f", "lavfi", "-i", f"color=c=0x3a4a55:s={w}x{h}"])
        run(["ffmpeg", "-v", "error", "-y", *under, "-i", render, "-filter_complex",
             f"[1:v]scale={w}:{h}[o];[0:v]scale={w}:{h}[b];[b][o]overlay=format=auto:shortest=1",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-preset", "veryfast",
             out])
    else:
        run(["ffmpeg", "-v", "error", "-y", "-i", render, "-vf", f"scale={w}:{h}",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-preset",
             "veryfast", out])


# --- SFX stem ------------------------------------------------------------------

def sfx_stem(project: Path, spec: dict, spec_path: Path, plan: dict,
             previous: dict | None, force: bool) -> dict | None:
    if not spec["sfx"]:
        return None
    index = load(resolve_input(spec_path, spec, "sfx_index"))
    libs = index["libraries"]
    fps = Fraction(plan["timeline"]["fps"])
    cues = {c["id"]: c for c in plan["cues"]}
    total = Fraction(plan["timeline"]["frames"]) / fps
    items = []
    for s in spec["sfx"]:
        src = Path(libs[s["library"]]) / s["file"]
        if not src.exists():
            raise RenderError(f"{s['cue']}: {src} not found (library moved?)")
        st = src.stat()
        items.append({"cue": s["cue"], "library": s["library"], "file": s["file"],
                      "src": str(src), "frame": cues[s["cue"]]["tl"][0],
                      "gain_db": s.get("gain_db", 0), "size": st.st_size,
                      "mtime": st.st_mtime})
    h = hashlib.sha256(json.dumps([items, plan["timeline"]], sort_keys=True)
                       .encode()).hexdigest()
    sfx_dir = project / "sfx"
    stem = sfx_dir / "sfx_stem.wav"
    reviews = {x["cue"]: x.get("review") for x in (previous or {}).get("items", [])}
    same = {x["cue"]: x for x in (previous or {}).get("items", [])}
    for it in items:
        old = same.get(it["cue"])
        unchanged = old and all(old.get(k) == it[k] for k in
                                ("library", "file", "frame", "gain_db", "size"))
        it["review"] = (reviews.get(it["cue"]) if unchanged and reviews.get(it["cue"])
                        else {"status": "pending", "note": ""})
    if previous and previous.get("hash") == h and stem.exists() and not force:
        return {**previous, "items": items, "reused": True}
    sfx_dir.mkdir(exist_ok=True)
    for f in sfx_dir.glob("b*.wav"):
        f.unlink()
    for it in items:
        shutil.copyfile(it["src"], sfx_dir / f"{it['cue']} {Path(it['file']).name}")
    ins, chains = [], []
    for i, it in enumerate(items):
        ins += ["-i", it["src"]]
        ms = int(round(float(Fraction(it["frame"]) / fps) * 1000))
        chains.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                      f"volume={it['gain_db']}dB,adelay={ms}:all=1[s{i}]")
    mix = "".join(f"[s{i}]" for i in range(len(items)))
    graph = ";".join(chains) + (f";{mix}amix=inputs={len(items)}:normalize=0:"
                                f"duration=longest,apad=whole_dur={float(total):.6f},"
                                f"atrim=0:{float(total):.6f}[out]")
    run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", graph, "-map", "[out]",
         "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le", stem])
    return {"file": "sfx/sfx_stem.wav", "sha256": sha256(stem), "hash": h,
            "seconds": float(total), "items": items, "reused": False}


# --- the whole run -------------------------------------------------------------------

def render_all(project: Path, shoot_path: Path | None, only: set | None,
               quality: str, force: bool, proxies: bool, log=print) -> dict:
    spec_path = project / "graphics.json"
    kind, errs = validate_file(spec_path)
    if errs:
        raise RenderError("graphics.json doesn't validate:\n  - " + "\n  - ".join(errs))
    spec = load(spec_path)
    plan_path = resolve_input(spec_path, spec, "plan")
    plan = load(plan_path)
    fps = Fraction(plan["timeline"]["fps"])
    render_fps = int(fps) if fps.denominator == 1 and int(fps) in NATIVE_FPS else 60
    size = "landscape-4k" if plan["timeline"]["width"] >= 3840 else "landscape"
    frame_sha = sha256(project / "frame.md")
    cues = {c["id"]: c for c in plan["cues"]}
    shoot = load(shoot_path) if shoot_path else None

    renders, raw, review = project / "renders", project / "raw", project / "review"
    for d in (renders, raw, review):
        d.mkdir(exist_ok=True)
    manifest_path = renders / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    old_renders = {r["cue"]: r for r in old.get("renders", [])}

    # 1. build the templated compositions
    rows = [{"cue": g["cue"], "template": g["template"], "vars": g["vars"],
             "frames": cues[g["cue"]]["tl"][1] - cues[g["cue"]]["tl"][0],
             "fps": plan["timeline"]["fps"]}
            for g in spec["graphics"] if g["template"] != "custom"]
    if rows:
        (project / ".rows.json").write_text(json.dumps(rows))
        run(["node", BUILD, project, project / ".rows.json"])

    out, problems = [], []
    for g in spec["graphics"]:
        cue = cues[g["cue"]]
        frames = cue["tl"][1] - cue["tl"][0]
        overlay = cue.get("layer", "overlay") != "full"
        comp_rel = g.get("composition") or f"compositions/{g['cue']}.html"
        html = (project / comp_rel).read_text()
        want = float(Fraction(frames) / fps)
        got = comp_duration(html)
        if got is None or abs(got - want) > 0.0005:
            problems.append(f"{g['cue']}: {comp_rel} lasts {got}s; the cue needs "
                            f"{want:.6f}s ({frames} frames at {plan['timeline']['fps']})")
            continue
        spec_hash = hashlib.sha256("|".join(map(str, (
            RENDER_VERSION, hashlib.sha256(html.encode()).hexdigest(),
            local_files_hash(html, (project / comp_rel).parent), frames,
            plan["timeline"]["fps"], render_fps, size, overlay, frame_sha, quality)))
            .encode()).hexdigest()
        final = renders / f"{g['cue']}.mov"
        prev = old_renders.get(g["cue"])
        if only is not None and g["cue"] not in only:
            if prev:                       # not asked for: leave it as it was
                out.append(prev)
            continue
        # --only always re-renders what it names; otherwise reuse unchanged
        reuse = (only is None and not force and prev and
                 prev["spec_hash"] == spec_hash and final.exists() and
                 sha256(final) == prev["sha256"])
        if reuse:
            out.append(prev)
            log(f"reused   {g['cue']}")
            continue
        raw_file = raw / f"{g['cue']}.mov"
        hyperframes(project, comp_rel, raw_file, render_fps, size, quality,
                    float(Fraction(frames) / fps))
        convert(raw_file, final, fps, frames, overlay)
        raw_file.unlink(missing_ok=True)
        n = count_frames(final)
        if n != frames:
            problems.append(f"{g['cue']}: rendered {n} frames, the cue needs {frames}")
            continue
        entry = {"cue": g["cue"], "file": f"renders/{g['cue']}.mov",
                 "template": g["template"], "layer": "overlay" if overlay else "full",
                 "frames": frames, "fps": plan["timeline"]["fps"],
                 "rendered_at_fps": render_fps, "size": size,
                 "sha256": sha256(final), "spec_hash": spec_hash,
                 "review": {"status": "pending", "note": ""}}
        if overlay:
            entry["transparent"] = transparent_share(final, want / 2)
        if proxies:
            still = review / f"{g['cue']}.under.png"
            has = context_still(plan, cue, shoot,
                                shoot_path.parent if shoot_path else None, still)
            make_proxy(final, review / f"{g['cue']}.mp4", overlay, still if has else None)
            entry["proxy"] = f"review/{g['cue']}.mp4"
            entry["proxy_context"] = "picture" if has else "plate"
        out.append(entry)
        log(f"rendered {g['cue']} ({frames} frames)")

    stem = sfx_stem(project, spec, spec_path, plan, old.get("sfx"), force)
    if stem:
        log(("reused   " if stem.pop("reused") else "mixed    ") +
            f"sfx stem ({len(stem['items'])} effects)")

    doc = header("graphics", {"spec": input_ref(spec_path, renders),
                              "plan": input_ref(plan_path, renders)})
    doc.update({"timeline": plan["timeline"], "renders":
                sorted(out, key=lambda r: cues[r["cue"]]["tl"][0])})
    if stem:
        doc["sfx"] = stem
    manifest_path.write_text(json.dumps(doc, indent=1) + "\n")
    if problems:
        raise RenderError("\n  - ".join(["some graphics failed:"] + problems))
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", type=Path)
    ap.add_argument("--shoot", type=Path)
    ap.add_argument("--only", help="comma-separated cue IDs to (re)render")
    ap.add_argument("--quality", default="delivery", choices=["delivery", "draft"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-proxies", action="store_true")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None
    try:
        doc = render_all(args.project, args.shoot, only, args.quality, args.force,
                         not args.no_proxies)
    except (RenderError, HandoffError) as e:
        sys.exit(f"Render failed: {e}")
    pending = sum(r["review"]["status"] != "approved" for r in doc["renders"])
    print(f"{len(doc['renders'])} graphics in renders/manifest.json, "
          f"{pending} waiting for review")


if __name__ == "__main__":
    main()
