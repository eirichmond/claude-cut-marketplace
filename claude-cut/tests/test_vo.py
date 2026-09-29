"""--vo: audio-only take selection and the rendered audio cut."""
import json
import shutil
import subprocess
import sys

import pytest

from conftest import SCRIPTS, run_script


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=sample_rate,codec_name",
                          "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    return (float(info["format"]["duration"]), info["streams"][0])


needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"),
                                  reason="ffmpeg not installed")


@needs_ffmpeg
def test_render_audio_cut_keeps_exactly_the_ranges(tmp_path):
    src = tmp_path / "tone.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=10:sample_rate=44100",
                    str(src)], check=True)
    cuts = tmp_path / "cuts.json"
    cuts.write_text(json.dumps({"ranges": [
        {"start": 1.0, "end": 3.0, "label": "s1"},
        {"start": 5.0, "end": 6.5, "label": "s2"},
        {"start": 9.5, "end": 12.0, "label": "past the end"}]}))
    out = tmp_path / "cut.wav"
    r = run_script("render_audio_cut.py", cuts, "--source", src, "-o", out)
    assert r.returncode == 0, r.stderr
    dur, stream = duration(out)
    assert dur == pytest.approx(2.0 + 1.5 + 0.5, abs=0.01)
    assert stream["sample_rate"] == "44100"
    assert stream["codec_name"] == "pcm_s24le"
    assert not list(tmp_path.glob("*.filter.txt"))


@needs_ffmpeg
def test_render_audio_cut_rejects_video_without_audio(tmp_path):
    src = tmp_path / "silent.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                    "color=c=black:s=64x64:d=1", str(src)], check=True)
    cuts = tmp_path / "cuts.json"
    cuts.write_text(json.dumps({"ranges": [{"start": 0, "end": 1}]}))
    r = run_script("render_audio_cut.py", cuts, "--source", src,
                   "-o", tmp_path / "x.wav")
    assert r.returncode != 0 and "has no audio stream" in r.stderr


def whisper_ready():
    try:
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError:
        return False
    return bool(shutil.which("say") and shutil.which("ffmpeg"))


@pytest.mark.slow
@pytest.mark.skipif(not whisper_ready(),
                    reason="needs macOS say, ffmpeg and faster-whisper")
def test_vo_recording_end_to_end(chain, tmp_path):
    """A synthetic VO read of the mini chain's vo.prompter.md with a fluff
    and a spoken 'retake cut', through the real transcribe -> match_takes
    (--sentences-out) -> render_audio_cut path that --vo runs."""
    chain.build()
    assert run_script("build_prompters.py", chain.director).returncode == 0
    prompter = chain.dir / "vo.prompter.md"
    aiff, wav = tmp_path / "vo.aiff", tmp_path / "vo.wav"
    subprocess.run(["say", "-v", "Samantha", "-r", "165", "-o", str(aiff),
                    "[[slnc 600]] Open the settings panel on the. "
                    "[[slnc 1500]] Retake, cut. [[slnc 1500]] "
                    "Open the settings panel on the left. Click the export "
                    "button at the bottom. [[slnc 1500]] Wait for the "
                    "progress bar to finish. [[slnc 1000]] That is the whole "
                    "demo in three steps. [[slnc 600]]"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff),
                    "-ar", "48000", str(wav)], check=True)

    t = tmp_path / "transcript.json"
    r = run_script("transcribe.py", wav, "-o", t)
    assert r.returncode == 0, r.stderr
    r = run_script("match_takes.py", t, prompter, "-o", tmp_path / "cuts.json",
                   "--report", tmp_path / "report.md",
                   "--sentences-out", tmp_path / "sentences.json")
    assert r.returncode == 0, r.stderr

    report = (tmp_path / "report.md").read_text()
    assert "MARKER" in report and "BINNED (before marker)" in report
    doc = json.loads((tmp_path / "sentences.json").read_text())
    assert [s["status"] for s in doc["sentences"]] == ["kept"] * 4
    marker_end = max(w["end"] for w in json.loads(t.read_text())["words"]
                     if w["word"].lower().strip(",.") == "cut")
    assert doc["sentences"][0]["start"] > marker_end

    out = tmp_path / "vo_cut.wav"
    r = run_script("render_audio_cut.py", tmp_path / "cuts.json",
                   "--source", wav, "-o", out)
    assert r.returncode == 0, r.stderr
    ranges = json.loads((tmp_path / "cuts.json").read_text())["ranges"]
    assert duration(out)[0] == pytest.approx(
        sum(r["end"] - r["start"] for r in ranges), abs=0.02)
