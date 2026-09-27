#!/usr/bin/env python3
"""Build a Resolve-importable FCPXML by piping the cut list through
auto-editor (whose output Resolve demonstrably accepts), then grafting the
B-roll in as connected clips.

Usage:
    python build_xml.py cuts.json --aroll aroll.mov \
        [--broll broll.mov --offsets offsets.json] -o project_cut

Requires auto-editor on PATH (pip install auto-editor).
"""
import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote


def probe(src: Path) -> dict:
    res = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams",
         "-show_format", str(src)],
        capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"ffprobe failed on {src}")
    info = json.loads(res.stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    rate = Fraction(v.get("r_frame_rate", "25/1"))
    tc = (v.get("tags", {}).get("timecode")
          or info["format"].get("tags", {}).get("timecode"))
    if not tc:
        # Some cameras (e.g. Sony XAVC) only carry start timecode on a
        # separate timed-metadata/data stream (tmcd/rtmd), not on the
        # video stream or in the format tags. Fall back to scanning all
        # streams so we don't silently default to 0 and desync from what
        # Resolve links against when it auto-imports the source clip.
        for s in info["streams"]:
            t = s.get("tags", {}).get("timecode")
            if t:
                tc = t
                break
    tc_seconds = Fraction(0)
    if tc:
        try:
            h, m, s, f = re.split(r"[:;]", tc)
            tb = round(float(rate))
            frames = (int(h) * 3600 + int(m) * 60 + int(s)) * tb + int(f)
            tc_seconds = frames / rate
        except (ValueError, ZeroDivisionError):
            pass
    return {
        "path": src.resolve(),
        "rate": rate,
        "frame": Fraction(1) / rate,
        "tc": tc_seconds,
        "width": int(v["width"]),
        "height": int(v["height"]),
        "duration": Fraction(info["format"]["duration"]).limit_denominator(10**6),
    }


def rt(t: Fraction) -> str:
    f = Fraction(t)
    return "0s" if f == 0 else f"{f.numerator}/{f.denominator}s"


def parse_rt(s: str) -> Fraction:
    s = s.rstrip("s")
    return Fraction(s) if "/" in s or s not in ("0", "") else Fraction(int(s or 0))


def snap(seconds, frame: Fraction) -> Fraction:
    return round(Fraction(seconds) / frame) * frame


def run_auto_editor(aroll: Path, ranges: list[dict], rate: Fraction,
                    workdir: Path, out_base: Path) -> Path:
    chunks = []
    for r in ranges:
        s = round(Fraction(r["start"]).limit_denominator(10**6) * rate)
        e = round(Fraction(r["end"]).limit_denominator(10**6) * rate)
        if e > s:
            chunks.append([int(s), int(e), 1])
    v1 = workdir / "claude-cut.v1.json"
    v1.write_text(json.dumps(
        {"version": "1", "source": str(aroll.resolve()), "chunks": chunks}))
    res = subprocess.run(
        ["auto-editor", str(v1), "--export", "resolve",
         "-o", str(out_base)],
        capture_output=True, text=True)
    fcp = out_base.with_suffix(".fcpxml")
    if res.returncode != 0 or not fcp.exists():
        sys.exit("auto-editor failed:\n" + (res.stderr or res.stdout)[-2000:]
                 + "\nIs auto-editor installed? (pip install auto-editor)")
    return fcp


def graft_broll(fcp: Path, b: dict, b_offset: Fraction) -> int:
    tree = ET.parse(fcp)
    root = tree.getroot()
    resources = root.find("resources")
    a_asset = resources.find("asset")
    a_tc = parse_rt(a_asset.get("start", "0s"))

    ET.SubElement(resources, "format", {
        "id": "r90", "width": str(b["width"]), "height": str(b["height"]),
        "frameDuration": rt(b["frame"]),
        "colorSpace": "1-1-1 (Rec. 709)",
        "name": "FFVideoFormatRateUndefined",
    })
    b_asset = ET.SubElement(resources, "asset", {
        "id": "r91", "format": "r90", "start": rt(b["tc"]),
        "duration": rt(snap(b["duration"], b["frame"])),
        "hasVideo": "1", "name": b["path"].stem,
    })
    ET.SubElement(b_asset, "media-rep", {
        "kind": "original-media",
        "src": "file://" + quote(str(b["path"])),
    })

    grafted = 0
    spine = root.find("./library/event/project/sequence/spine")
    for clip in spine.findall("asset-clip"):
        c_start = parse_rt(clip.get("start"))
        c_dur = parse_rt(clip.get("duration"))
        # master (zero-based) range this cut covers
        m_start = c_start - a_tc
        bs = snap(m_start - b_offset, b["frame"])
        be = snap(m_start + c_dur - b_offset, b["frame"])
        bs_c, be_c = max(Fraction(0), bs), min(b["duration"], be)
        if be_c <= bs_c:
            continue
        shift = snap(bs_c - bs, b["frame"]) if bs_c > bs else Fraction(0)
        b_dur = min(be_c - bs_c, c_dur - shift)
        if b_dur <= 0:
            continue
        ET.SubElement(clip, "asset-clip", {
            "ref": "r91", "lane": "1",
            "offset": rt(c_start + shift),
            "start": rt(b["tc"] + bs_c),
            "duration": rt(b_dur),
            "srcEnable": "video",
            "name": b["path"].stem,
        })
        grafted += 1
    tree.write(fcp, encoding="utf-8", xml_declaration=True)
    return grafted


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cuts", type=Path)
    ap.add_argument("--aroll", type=Path, required=True)
    ap.add_argument("--broll", type=Path)
    ap.add_argument("--offsets", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()

    if args.broll and not args.offsets:
        sys.exit("--broll needs --offsets from sync.py")

    ranges = json.loads(args.cuts.read_text())["ranges"]
    a = probe(args.aroll)
    out_base = args.output.with_suffix("")
    workdir = args.cuts.parent
    fcp = run_auto_editor(args.aroll, ranges, a["rate"], workdir, out_base)

    msg = f"Wrote {fcp} ({len(ranges)} cuts via auto-editor"
    if args.broll:
        b = probe(args.broll)
        b_offset = Fraction(
            json.loads(args.offsets.read_text())["offset_seconds"]
        ).limit_denominator(10**6)
        n = graft_broll(fcp, b, b_offset)
        msg += f", {n} B-roll clips grafted on lane 1"
    print(msg + ")")
    print("Import in Resolve: File > Import > Timeline "
          "(fresh project, auto-import source clips ON).")


if __name__ == "__main__":
    main()
