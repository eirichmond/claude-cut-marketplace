#!/usr/bin/env python3
"""Render the kept ranges of an audio-only recording to one audio file.

Usage:
    python render_audio_cut.py cuts.json --source vo.wav -o vo_cut.wav

Used for voiceover (--vo) runs, which have no picture and so no Resolve
timeline: this gives a listenable cut straight away. Each range gets a 5ms
fade in and out so the joins don't click. The pipeline's assemble stage
doesn't use this file; it places the VO from the original recording.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

FADE = 0.005


def probe_audio(src: Path) -> dict:
    res = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams",
         "-show_format", str(src)], capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"ffprobe failed on {src}")
    info = json.loads(res.stdout)
    audio = [s for s in info["streams"] if s["codec_type"] == "audio"]
    if not audio:
        sys.exit(f"{src} has no audio stream")
    return {"rate": int(audio[0].get("sample_rate", 48000)),
            "channels": int(audio[0].get("channels", 1)),
            "duration": float(info["format"].get("duration", 0))}


def filter_graph(ranges: list[dict], duration: float) -> tuple[str, int]:
    parts, labels = [], []
    for i, r in enumerate(ranges):
        s, e = max(0.0, r["start"]), min(r["end"], duration or r["end"])
        if e <= s:
            continue
        d = e - s
        fade = min(FADE, d / 2)
        parts.append(
            f"[0:a]atrim=start={s:.6f}:end={e:.6f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:d={fade:.6f},"
            f"afade=t=out:st={d - fade:.6f}:d={fade:.6f}[a{i}]")
        labels.append(f"[a{i}]")
    if not labels:
        return "", 0
    parts.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[out]")
    return ";".join(parts), len(labels)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cuts", type=Path)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()

    ranges = json.loads(args.cuts.read_text())["ranges"]
    info = probe_audio(args.source)
    graph, n = filter_graph(ranges, info["duration"])
    if not n:
        sys.exit("No ranges to render.")
    # The graph can be long; pass it as a file rather than on the command line.
    script = args.output.with_suffix(".filter.txt")
    script.write_text(graph)
    try:
        res = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(args.source),
             "-filter_complex_script", str(script), "-map", "[out]",
             "-c:a", "pcm_s24le", "-ar", str(info["rate"]), str(args.output)],
            capture_output=True, text=True)
    finally:
        script.unlink(missing_ok=True)
    if res.returncode != 0:
        sys.exit("ffmpeg failed rendering the cut:\n" + res.stderr[-2000:])
    kept = sum(max(0.0, min(r["end"], info["duration"]) - max(0.0, r["start"]))
               for r in ranges)
    print(f"Wrote {args.output} ({n} ranges, {kept:.1f}s of "
          f"{info['duration']:.1f}s)")


if __name__ == "__main__":
    main()
