#!/usr/bin/env python3
"""Assemble: build the full Resolve timeline from the conformed plan.

Usage:
    python assemble.py --plan plan.resolved.json --shoot shoot.json \\
        -o <video>_assembled.fcpxml

Starts from the edit-takes timeline conform read (the TH clips, same
approach as the B-roll graft) and writes:

  <video>_assembled.fcpxml   spine: TH clips split at segment boundaries,
                             gaps for VO segments and inserts
                             lane 1   the B-roll angle (build_xml's graft)
                             lane 2   screen-recording / b-roll beds
                             lane -1  VO audio, from the original recording
  <video>_markers.edl        chapters (blue), CHECK points and missing
                             assets (red), graphic cues (yellow): import
                             with Media Pool > right-click the timeline >
                             Timelines > Import > Timeline Markers from EDL
  assemble-report.md         what was placed, what's missing, how to import

A stereo VO recording is downmixed to <name>_mono.wav beside it (the
original is untouched), so Resolve puts it on its own track next to the
stereo camera audio. Graphics and sound effects are markers until the
graphics stage renders them (v0.6).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote

from build_xml import graft_broll, parse_rt, probe, rt
from handoff import HandoffError, load, resolve_input
from validate import validate_file

GAP_START = Fraction(3600)
BED_LANE = "2"
VO_LANE = "-1"
MARKER_KINDS = {"mg", "lt", "chapter", "callout", "zoom", "blur", "sfx",
                "music", "marker"}
COLOURS = {"check": "ResolveColorRed", "missing": "ResolveColorRed",
           "chapter": "ResolveColorBlue", "cue": "ResolveColorYellow",
           "note": "ResolveColorCyan"}
PRIORITY = ["check", "missing", "chapter", "note", "cue"]


class AssembleError(Exception):
    pass


def probe_audio(path: Path) -> dict:
    res = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                          "-show_streams", "-show_format", str(path)],
                         capture_output=True, text=True)
    if res.returncode:
        raise AssembleError(f"ffprobe failed on {path}")
    info = json.loads(res.stdout)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if not a:
        raise AssembleError(f"{path.name} has no audio stream")
    return {"channels": int(a.get("channels", 1)),
            "rate": int(a.get("sample_rate", 48000)),
            "duration": Fraction(info["format"]["duration"]).limit_denominator(10**6)}


def mono_vo(path: Path, report: list) -> Path:
    """The VO file as mono: itself if it already is, else a downmix beside it."""
    info = probe_audio(path)
    if info["channels"] == 1:
        return path
    out = path.with_name(f"{path.stem}_mono.wav")
    if out.exists() and out.stat().st_mtime >= path.stat().st_mtime:
        report.append(f"VO is {info['channels']}-channel; reused the mono "
                      f"copy {out.name}")
        return out
    gains = "+".join(f"{1 / info['channels']:.6f}*c{i}"
                     for i in range(info["channels"]))
    res = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path),
                          "-af", f"pan=mono|c0={gains}", "-c:a", "pcm_s24le",
                          "-ar", str(info["rate"]), str(out)],
                         capture_output=True, text=True)
    if res.returncode:
        raise AssembleError(f"couldn't make a mono copy of {path.name}:\n"
                            f"{res.stderr[-1000:]}")
    report.append(f"VO is {info['channels']}-channel; made a mono copy "
                  f"{out.name} so it lands on its own track (original untouched)")
    return out


def media_rep(el, path: Path) -> None:
    ET.SubElement(el, "media-rep", {"kind": "original-media",
                                    "src": "file://" + quote(str(path.resolve()))})


class Timeline:
    """The edit-takes FCPXML, rebuilt around the conformed plan."""

    def __init__(self, fcpxml: Path, fps: Fraction):
        self.tree = ET.parse(fcpxml)
        self.root = self.tree.getroot()
        self.fps = fps
        self.resources = self.root.find("resources")
        self.spine = self.root.find("./library/event/project/sequence/spine")
        self.placed = []  # (tl start, tl end, element, element start time)
        self.ids = 0
        # Drop an earlier B-roll graft: the angle is regrafted onto the split
        # clips, and its resource IDs would clash.
        for el in list(self.resources):
            if el.get("id") in ("r90", "r91"):
                self.resources.remove(el)
        self.clips = []
        for c in self.spine.findall("asset-clip"):
            self.clips.append((parse_rt(c.get("offset")), parse_rt(c.get("start")),
                               parse_rt(c.get("duration")), dict(c.attrib)))
        for c in list(self.spine):
            self.spine.remove(c)

    def T(self, frames: int) -> Fraction:
        return Fraction(frames) / self.fps

    def frames(self, t) -> int:
        return round(Fraction(t).limit_denominator(10**6) * self.fps)

    def new_id(self, prefix: str) -> str:
        self.ids += 1
        return f"cc{prefix}{self.ids}"

    def add_th(self, seg: dict) -> None:
        """The part of the TH timeline this segment covers, as spine clips."""
        (ta, tb), cursor = seg["th_tl"], seg["tl"][0]
        for off, start, dur, attrs in self.clips:
            oa, ob = self.frames(off), self.frames(off + dur)
            lo, hi = max(ta, oa), min(tb, ob)
            if hi <= lo:
                continue
            src = start + self.T(lo - oa)
            el = ET.SubElement(self.spine, "asset-clip", {
                **{k: v for k, v in attrs.items()
                   if k not in ("offset", "start", "duration", "name")},
                "name": f"{seg['id']} {attrs.get('name', '')}".strip(),
                "offset": rt(self.T(cursor)), "start": rt(src),
                "duration": rt(self.T(hi - lo))})
            self.placed.append((cursor, cursor + hi - lo, el, src))
            cursor += hi - lo
        if cursor != seg["tl"][1]:
            raise AssembleError(f"{seg['id']}: the TH timeline gives "
                                f"{cursor - seg['tl'][0]} frames, the plan "
                                f"{seg['tl'][1] - seg['tl'][0]}. Was the "
                                f"edit-takes timeline rebuilt after conform?")

    def add_gap(self, name: str, tl: list) -> None:
        el = ET.SubElement(self.spine, "gap", {
            "name": name, "offset": rt(self.T(tl[0])), "start": rt(GAP_START),
            "duration": rt(self.T(tl[1] - tl[0]))})
        self.placed.append((tl[0], tl[1], el, GAP_START))

    def reindex(self) -> None:
        """Re-find the spine elements after build_xml's graft rewrote the file."""
        self.resources = self.root.find("resources")
        self.spine = self.root.find("./library/event/project/sequence/spine")
        self.placed = []
        for el in self.spine:
            off = self.frames(parse_rt(el.get("offset")))
            dur = self.frames(parse_rt(el.get("duration")))
            self.placed.append((off, off + dur, el, parse_rt(el.get("start"))))

    def connect(self, tl_start: int, length: int, attrs: dict):
        for a, b, el, start in self.placed:
            if a <= tl_start < b:
                break
        else:
            a, b, el, start = self.placed[-1]
        attrs["offset"] = rt(start + self.T(tl_start - a))
        attrs["duration"] = rt(self.T(max(1, length)))
        clip = ET.SubElement(el, "asset-clip", attrs)
        # FCPXML wants connected clips before markers and other children
        kids = list(el)
        for k in kids:
            el.remove(k)
        for k in [k for k in kids if k.tag == "asset-clip"] + \
                [k for k in kids if k.tag != "asset-clip"]:
            el.append(k)
        return clip

    def add_video_asset(self, path: Path) -> tuple[str, Fraction, Fraction]:
        info = probe(path)
        fid, aid = self.new_id("f"), self.new_id("a")
        ET.SubElement(self.resources, "format", {
            "id": fid, "width": str(info["width"]), "height": str(info["height"]),
            "frameDuration": rt(info["frame"]), "colorSpace": "1-1-1 (Rec. 709)",
            "name": "FFVideoFormatRateUndefined"})
        a = ET.SubElement(self.resources, "asset", {
            "id": aid, "name": path.stem, "format": fid, "start": rt(info["tc"]),
            "duration": rt(info["duration"]), "hasVideo": "1"})
        media_rep(a, path)
        return aid, info["tc"], info["duration"]

    def add_audio_asset(self, path: Path) -> tuple[str, Fraction]:
        info = probe_audio(path)
        aid = self.new_id("a")
        a = ET.SubElement(self.resources, "asset", {
            "id": aid, "name": path.stem, "start": "0s",
            "duration": rt(info["duration"]), "hasVideo": "0", "hasAudio": "1",
            "audioSources": "1", "audioChannels": str(info["channels"]),
            "audioRate": str(info["rate"])})
        media_rep(a, path)
        return aid, info["duration"]

    def write(self, path: Path) -> None:
        ET.indent(self.tree)
        self.tree.write(path, encoding="utf-8", xml_declaration=True)


# --- markers ------------------------------------------------------------------

def edl_name(text: str, limit: int = 160) -> str:
    return " ".join(text.replace("|", "/").split())[:limit]


def write_markers_edl(path: Path, markers: list, fps: Fraction,
                      title: str) -> int:
    """markers: (frame, kind, name, duration frames). Resolve keeps one
    marker per frame, so markers on the same frame are merged."""
    by_frame: dict[int, list] = {}
    for f, kind, name, dur in markers:
        by_frame.setdefault(f, []).append((kind, name, dur))
    base = round(fps)

    def tc(f: int) -> str:
        s, fr = divmod(f, base)
        return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{fr:02d}"

    lines = [f"TITLE: {edl_name(title)}", "FCM: NON-DROP FRAME", ""]
    for i, f in enumerate(sorted(by_frame), 1):
        group = by_frame[f]
        kind = min((k for k, _, _ in group), key=PRIORITY.index)
        # '|' separates EDL fields, so clean each name before joining
        name = " + ".join(edl_name(n) for _, n, _ in group)
        dur = max(1, max(d for _, _, d in group))
        lines += [f"{i:03d}  001      V     C        {tc(f)} {tc(f + 1)} "
                  f"{tc(f)} {tc(f + 1)}  ",
                  f" |C:{COLOURS[kind]} |M:{edl_name(name, 480)} |D:{dur}", ""]
    path.write_text("\n".join(lines))
    return len(by_frame)


# --- assemble -------------------------------------------------------------------

def rel(base: Path, p: str | None) -> Path | None:
    if not p:
        return None
    q = Path(p)
    return q if q.is_absolute() else (base / q).resolve()


def assemble(args) -> dict:
    kind, errs = validate_file(args.plan)
    if errs:
        raise AssembleError(f"{args.plan.name} doesn't validate:\n  - " +
                            "\n  - ".join(errs))
    plan = load(args.plan)
    shoot_path = args.shoot
    shoot = load(shoot_path) if shoot_path else {"th": {}, "assets": {}}
    if shoot_path:
        k, errs = validate_file(shoot_path)
        if errs:
            raise AssembleError(f"{shoot_path.name}: " + "; ".join(errs))
    base = shoot_path.parent if shoot_path else Path.cwd()
    report: list[str] = []
    fps = Fraction(plan["timeline"]["fps"])

    fcp_in = resolve_input(args.plan, plan, "th_fcpxml") \
        if "th_fcpxml" in plan["inputs"] else None
    if not fcp_in:
        raise AssembleError("the plan has no TH timeline (th_fcpxml); a "
                            "voiceover-only video isn't supported yet")
    if args.output.resolve() == fcp_in.resolve():
        raise AssembleError("refusing to overwrite the edit-takes timeline; "
                            "write the assembled timeline to a new file")
    tl = Timeline(fcp_in, fps)

    # --- spine ------------------------------------------------------------------
    items = [("seg", s) for s in plan["segments"]] + \
        [("ins", c) for c in plan["cues"] if c["placement"].startswith("insert")]
    items.sort(key=lambda it: it[1]["tl"][0])
    for kind, it in items:
        if kind == "seg" and it["mode"] == "th":
            tl.add_th(it)
        elif kind == "seg":
            tl.add_gap(f"VO {it['id']}", it["tl"])
        else:
            tl.add_gap(f"{it['id']} ({it['kind']})", it["tl"])
    if tl.placed[-1][1] != plan["timeline"]["frames"]:
        raise AssembleError("spine length doesn't match the plan")

    # --- lane 1: the B-roll angle, grafted by build_xml onto the split clips --
    out = args.output
    broll = rel(base, args.broll or shoot["th"].get("broll"))
    offsets = rel(base, args.offsets or shoot["th"].get("offsets"))
    tl.write(out)
    if broll:
        if not offsets:
            raise AssembleError("the B-roll angle needs --offsets (sync.py output)")
        b = probe(broll)
        off = Fraction(json.loads(offsets.read_text())["offset_seconds"]) \
            .limit_denominator(10**6)
        n = graft_broll(out, b, off)
        report.append(f"B-roll angle {broll.name}: {n} clips on lane 1")
        tl.tree = ET.parse(out)
        tl.root = tl.tree.getroot()
    tl.reindex()

    # --- lane -1: the VO, from the original recording --------------------------
    vo_segs = [s for s in plan["segments"] if s["mode"] == "vo"]
    vo_clips = 0
    if vo_segs:
        vo = rel(base, args.vo or shoot.get("vo", {}).get("audio"))
        if not vo or not vo.exists():
            raise AssembleError("there are VO segments but no VO recording "
                                "(--vo, or vo.audio in shoot.json)")
        vo = mono_vo(vo, report) if not args.keep_stereo_vo else vo
        vid, vdur = tl.add_audio_asset(vo)
        last = max(r[1] for s in vo_segs for r in s["source"]["ranges"])
        if Fraction(last).limit_denominator(10**6) > vdur + tl.T(1):
            raise AssembleError(f"{vo.name} is {float(vdur):.1f}s long but the "
                                f"plan uses it up to {last:.1f}s: wrong file?")
        for s in vo_segs:
            f = s["tl"][0]
            for a, b in s["source"]["ranges"]:
                fa, fb = tl.frames(a), tl.frames(b)
                tl.connect(f, fb - fa, {"ref": vid, "lane": VO_LANE,
                                        "name": f"VO {s['id']}",
                                        "start": rt(tl.T(fa))})
                f += fb - fa
                vo_clips += 1
            if f != s["tl"][1]:
                raise AssembleError(f"{s['id']}: VO ranges give {f - s['tl'][0]} "
                                    f"frames, the plan {s['tl'][1] - s['tl'][0]}")

    # --- lane 2: beds and cutaways, markers for everything else ---------------
    assets = shoot.get("assets", {})
    markers, placed_beds, missing, short = [], 0, [], []
    asset_ids: dict[Path, tuple] = {}
    for c in plan["cues"]:
        a, b = c["tl"]
        if c["kind"] in ("sr", "br"):
            path = rel(base, assets.get(c["id"]))
            if not path or not path.exists():
                missing.append(c)
                why = "not captured" if c["id"] not in assets or \
                    assets.get(c["id"]) is None else f"file not found ({path})"
                markers.append((a, "missing", f"MISSING {c['id']} ({why}): "
                                f"{c['brief']}", b - a))
                continue
            if path not in asset_ids:
                asset_ids[path] = tl.add_video_asset(path)
            aid, tc0, dur = asset_ids[path]
            length = b - a
            if tl.frames(dur) < length:
                short.append((c, tl.frames(dur), length))
                length = tl.frames(dur)
            tl.connect(a, length, {"ref": aid, "lane": BED_LANE,
                                   "name": c["id"], "start": rt(tc0),
                                   "srcEnable": "video"})
            placed_beds += 1
        elif c["kind"] in MARKER_KINDS and not c["placement"].startswith("insert"):
            markers.append((a, "cue", f"{c['id']} {c['kind'].upper()}: "
                            f"{c['brief']}", b - a))
        elif c["placement"].startswith("insert"):
            markers.append((a, "cue", f"{c['id']} {c['kind'].upper()} "
                            f"(insert, {b - a} frames): {c['brief']}", b - a))
    for m in plan["markers"]:
        markers.append((m["tl"], m["kind"], m["name"], 1))

    tl.write(out)
    edl = out.with_name(out.name.replace("_assembled.fcpxml", "") +
                        "_markers.edl") if out.name.endswith("_assembled.fcpxml") \
        else out.with_suffix(".markers.edl")
    n_markers = write_markers_edl(edl, markers, fps,
                                  f"{out.stem} markers")
    return {"fcpxml": out, "edl": edl, "report": report, "missing": missing,
            "short": short, "beds": placed_beds, "vo_clips": vo_clips,
            "markers": n_markers, "plan": plan}


def write_report(path: Path, r: dict) -> None:
    plan = r["plan"]
    fps = Fraction(plan["timeline"]["fps"])
    secs = plan["timeline"]["frames"] / fps
    th = sum(1 for s in plan["segments"] if s["mode"] == "th")
    vo = len(plan["segments"]) - th
    lines = ["# Assemble report", "",
             f"- Timeline: `{r['fcpxml'].name}`, {int(secs // 60)}:"
             f"{int(secs % 60):02d} at {plan['timeline']['fps']} fps, "
             f"{th} talking-head and {vo} voiceover segments",
             f"- Voiceover: {r['vo_clips']} clips on its own audio track",
             f"- Screen recordings and b-roll placed: {r['beds']}",
             f"- Markers: {r['markers']} in `{r['edl'].name}`"]
    lines += [f"- {x}" for x in r["report"]]
    lines += ["", "## Import into Resolve", "",
              f"1. File > Import > Timeline, pick `{r['fcpxml'].name}`, into a "
              f"fresh project with 'Automatically import source clips into "
              f"media pool' ticked.",
              f"2. In the Media Pool, right-click the new timeline > Timelines > "
              f"Import > Timeline Markers from EDL..., pick `{r['edl'].name}`.",
              "", "Markers: blue = chapters, red = check this / missing "
              "asset, yellow = graphics, lower thirds, zooms, blurs and "
              "sound effects still to add."]
    if r["missing"]:
        lines += ["", f"## Not captured yet ({len(r['missing'])})", "",
                  "The picture is black there; each has a red marker. Add the "
                  "file to `assets` in shoot.json and assemble again.", ""]
        lines += [f"- `{c['id']}` ({c['placement']}): {c['brief']}"
                  for c in r["missing"]]
    if r["short"]:
        lines += ["", "## Shorter than needed", ""]
        lines += [f"- `{c['id']}`: the file is {have} frames, the cue needs "
                  f"{need}. Extend or freeze the last frame in Resolve."
                  for c, have, need in r["short"]]
    if plan["warnings"]:
        lines += ["", "## Conform warnings", ""] + \
            [f"- {w}" for w in plan["warnings"]]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--shoot", type=Path)
    ap.add_argument("--vo", type=Path, help="overrides vo.audio in shoot.json")
    ap.add_argument("--broll", type=Path, help="overrides th.broll")
    ap.add_argument("--offsets", type=Path, help="overrides th.offsets")
    ap.add_argument("--keep-stereo-vo", action="store_true",
                    help="use a stereo VO file as-is (it may share A1)")
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.suffix != ".fcpxml":
        sys.exit("Output must end .fcpxml")
    try:
        r = assemble(args)
    except (AssembleError, HandoffError) as e:
        sys.exit(f"Assemble failed: {e}")
    rpath = args.output.with_name("assemble-report.md")
    write_report(rpath, r)
    print(f"Wrote {r['fcpxml']} ({r['beds']} beds, {r['vo_clips']} VO clips, "
          f"{len(r['missing'])} assets missing)")
    print(f"Wrote {r['edl']} ({r['markers']} markers)")
    print(f"Wrote {rpath}")


if __name__ == "__main__":
    main()
