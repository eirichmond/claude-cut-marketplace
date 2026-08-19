#!/usr/bin/env python3
"""Transcribe the master audio track with word-level timestamps.

Usage:
    python transcribe.py <video_or_audio_file> -o transcript.json [--model small]

Output JSON:
    {
      "source": "aroll.mov",
      "duration": 512.3,
      "words": [{"word": "hello", "start": 1.02, "end": 1.31}, ...]
    }
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_audio(src: Path, out_wav: Path) -> None:
    """Pull mono 16kHz wav out of any container ffmpeg understands."""
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vn", "-ac", "1", "-ar", "16000",
        "-acodec", "pcm_s16le", str(out_wav),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"ffmpeg failed extracting audio:\n{res.stderr[-2000:]}")


def probe_duration(src: Path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", str(src)],
        capture_output=True, text=True,
    )
    try:
        return float(json.loads(res.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--model", default="small",
                    help="faster-whisper model size (tiny/base/small/medium)")
    ap.add_argument("--language", default="en")
    args = ap.parse_args()

    if not args.source.exists():
        sys.exit(f"Source not found: {args.source}")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed. Run: pip install faster-whisper")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "audio.wav"
        print(f"Extracting audio from {args.source.name}...", flush=True)
        extract_audio(args.source, wav)

        print(f"Loading whisper model '{args.model}' "
              "(first run downloads it)...", flush=True)
        model = WhisperModel(args.model, device="cpu", compute_type="int8")

        print("Transcribing (this can take a while on long footage)...",
              flush=True)
        segments, _info = model.transcribe(
            str(wav),
            language=args.language,
            word_timestamps=True,
            vad_filter=True,
        )

        words = []
        for seg in segments:
            for w in seg.words or []:
                words.append({
                    "word": w.word.strip(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                })

    payload = {
        "source": str(args.source),
        "duration": probe_duration(args.source),
        "words": words,
    }
    args.output.write_text(json.dumps(payload, indent=1))
    print(f"Wrote {len(words)} words -> {args.output}")


if __name__ == "__main__":
    main()
