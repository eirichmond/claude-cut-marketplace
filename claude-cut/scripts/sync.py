#!/usr/bin/env python3
"""Find the time offset between two clips by cross-correlating their audio.

Usage:
    python sync.py <master_clip> <other_clip> -o offsets.json

Output JSON:
    {
      "master": "aroll.mov",
      "other": "broll.mov",
      "offset_seconds": 12.84,   # other started 12.84s AFTER master
      "confidence": 0.91
    }

offset_seconds is how far into the master timeline the other clip's t=0 sits.
Negative means the other clip started rolling first.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import signal

SR = 8000  # plenty for waveform alignment, keeps memory sane


def load_audio(src: Path, max_seconds: int | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "quiet", "-i", str(src)]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0 or not res.stdout:
        sys.exit(f"ffmpeg failed reading audio from {src}")
    audio = np.frombuffer(res.stdout, dtype=np.int16).astype(np.float32)
    audio /= max(np.abs(audio).max(), 1.0)
    return audio


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("master", type=Path)
    ap.add_argument("other", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--window", type=int, default=300,
                    help="Seconds of audio to correlate (default 300; the "
                         "clap should land inside this window on both clips)")
    args = ap.parse_args()

    for p in (args.master, args.other):
        if not p.exists():
            sys.exit(f"Not found: {p}")

    print("Loading audio...", flush=True)
    a = load_audio(args.master, args.window)
    b = load_audio(args.other, args.window)

    print("Cross-correlating...", flush=True)
    corr = signal.correlate(a, b, mode="full", method="fft")
    lags = signal.correlation_lags(len(a), len(b), mode="full")
    peak = int(np.argmax(np.abs(corr)))
    offset = lags[peak] / SR

    # Confidence: peak prominence vs the rest of the correlation curve
    ac = np.abs(corr)
    peak_val = ac[peak]
    noise = np.median(ac) + 1e-9
    confidence = float(min(1.0, (peak_val / noise) / 50.0))

    payload = {
        "master": str(args.master),
        "other": str(args.other),
        "offset_seconds": round(float(offset), 3),
        "confidence": round(confidence, 2),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=1))

    direction = "after" if offset >= 0 else "before"
    print(f"{args.other.name} started {abs(offset):.2f}s {direction} "
          f"{args.master.name} (confidence {confidence:.2f})")
    if confidence < 0.5:
        print("WARNING: low confidence. Check both clips actually share "
              "the same scene audio and the clap is inside the window.")


if __name__ == "__main__":
    main()
