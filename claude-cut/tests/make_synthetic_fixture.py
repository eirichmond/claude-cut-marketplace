#!/usr/bin/env python3
"""Synthetic recordings of a video's prompters, for testing cut -> conform
-> assemble without real footage.

Usage:
    python tests/make_synthetic_fixture.py <folder with th/vo.prompter.md> \\
        -o OUT [--audio] [--fluff-every 6] [--fps 25]

It reads each prompter the way a presenter would: paragraph by paragraph,
with an off-script "okay, rolling" at the start of the talking heads, and
every Nth paragraph fluffed partway, followed by "retake cut" and a clean
restart of that paragraph (restarting the paragraph, as the director skill
advises).

Default (transcript mode, fast and deterministic):
  OUT/th/transcript.json, OUT/vo/transcript.json  word timings, as
                                                   transcribe.py writes them
  OUT/aroll.mp4    a flat-colour dummy A-roll the length of the TH read,
                   silent, with embedded start timecode 01:00:00:00 (the
                   same tmcd path the ZV-E10 files take)
  OUT/expected.json  every utterance with its role (take, fluff, marker,
                   off-script), segment and time span

--audio renders real speech with macOS `say` instead: OUT/aroll.mp4 carries
the TH read, OUT/vo.wav the VO read, and expected.json the true spans.
Transcribe them with transcribe.py (whisper) as for real footage.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from speech import timed_transcript  # noqa: E402

PAUSE_SENTENCE = 0.4
PAUSE_PARAGRAPH = 1.2
PAUSE_SEGMENT = 1.6
PAUSE_MARKER = 1.5
MARKER = "retake cut"
INTRO = "okay, rolling"
VOICE = "Samantha"
RATE = 48000


def paragraphs(prompter: str) -> list[tuple[str, str]]:
    """(segment id, paragraph text) in reading order."""
    out, seg = [], None
    for line in prompter.splitlines():
        m = re.match(r"^## (\S+)\s*$", line)
        if m:
            seg = m.group(1)
            continue
        if not line.strip() or line.startswith("#"):
            continue
        # a presenter reads words, not markdown
        out.append((seg, line.replace("`", "").strip()))
    return out


def plan(mode: str, prompter: str, fluff_every: int,
         segment_pause: float = PAUSE_SEGMENT) -> list[dict]:
    """The utterances of one recording session, in order. A marker belongs
    to the segment it retakes."""
    utts, prev_seg = [], None
    if mode == "th":
        utts.append({"role": "off-script", "segment": None, "text": INTRO,
                     "pause": 0.8})
    for i, (seg, para) in enumerate(paragraphs(prompter), 1):
        pause = (segment_pause if seg != prev_seg else PAUSE_PARAGRAPH) \
            if prev_seg is not None or utts else 0.8
        words = para.split()
        if fluff_every and i % fluff_every == 0 and len(words) >= 6:
            first = re.split(r"(?<=[.!?])\s+", para)[0].split()
            fluff = " ".join(first[:max(3, len(first) // 2)])
            utts += [{"role": "fluff", "segment": seg, "text": fluff,
                      "pause": pause},
                     {"role": "marker", "segment": seg, "text": MARKER,
                      "pause": PAUSE_MARKER}]
            pause = PAUSE_MARKER
        utts.append({"role": "take", "segment": seg, "text": para,
                     "pause": pause})
        prev_seg = seg
    return utts


def transcript_mode(mode: str, utts: list[dict], out: Path) -> float:
    data, spans = timed_transcript([(u["pause"], u["text"]) for u in utts],
                                   source=f"{mode}-synthetic")
    for u, (s, e) in zip(utts, spans):
        u["start"], u["end"] = s, e
    d = out / mode
    d.mkdir(parents=True, exist_ok=True)
    (d / "transcript.json").write_text(json.dumps(data, indent=1))
    return data["duration"]


def say_mode(mode: str, utts: list[dict], out: Path) -> Path:
    """Render each utterance with say, join with exact silences, record spans."""
    if not shutil.which("say"):
        sys.exit("--audio needs macOS 'say'")
    wav = out / f"{mode}.wav"
    with tempfile.TemporaryDirectory() as td, wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        t = 0.0
        for i, u in enumerate(utts):
            silence = int(u["pause"] * RATE)
            w.writeframes(b"\x00\x00" * silence)
            t += silence / RATE
            aiff, part = Path(td) / f"{i}.aiff", Path(td) / f"{i}.wav"
            subprocess.run(["say", "-v", VOICE, "-r", "165", "-o", str(aiff),
                            u["text"]], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff),
                            "-ac", "1", "-ar", str(RATE), "-c:a", "pcm_s16le",
                            str(part)], check=True)
            with wave.open(str(part)) as p:
                frames = p.readframes(p.getnframes())
            u["start"] = round(t, 3)
            t += len(frames) / 2 / RATE
            u["end"] = round(t, 3)
            w.writeframes(frames)
        w.writeframes(b"\x00\x00" * RATE)
    return wav


def dummy_aroll(out: Path, seconds: float, fps: int, audio: Path | None) -> Path:
    mp4 = out / "aroll.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
           f"color=c=0x224466:s=640x360:r={fps}:d={seconds:.3f}"]
    if audio:
        cmd += ["-i", str(audio)]
    else:
        cmd += ["-f", "lavfi", "-i",
                f"anullsrc=r={RATE}:cl=mono:d={seconds:.3f}"]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
            "-c:a", "aac", "-shortest", "-timecode", "01:00:00:00", str(mp4)]
    subprocess.run(cmd, check=True)
    return mp4


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompters", type=Path,
                    help="folder holding th.prompter.md and vo.prompter.md")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--fluff-every", type=int, default=6)
    ap.add_argument("--fps", type=int, default=25)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    expected = {"fluff_every": args.fluff_every, "audio": args.audio,
                "recordings": {}}
    for mode in ("th", "vo"):
        p = args.prompters / f"{mode}.prompter.md"
        if not p.exists():
            continue
        utts = plan(mode, p.read_text(), args.fluff_every)
        if args.audio:
            wav = say_mode(mode, utts, args.out)
            if mode == "th":
                with wave.open(str(wav)) as w:
                    secs = w.getnframes() / RATE
                dummy_aroll(args.out, secs, args.fps, wav)
                wav.unlink()
        else:
            secs = transcript_mode(mode, utts, args.out)
            if mode == "th":
                dummy_aroll(args.out, secs, args.fps, None)
        expected["recordings"][mode] = utts
        takes = sum(u["role"] == "take" for u in utts)
        fluffs = sum(u["role"] == "fluff" for u in utts)
        print(f"{mode}: {takes} paragraphs, {fluffs} fluffed and retaken")
    (args.out / "expected.json").write_text(json.dumps(expected, indent=1))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
