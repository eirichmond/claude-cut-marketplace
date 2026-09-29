import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
MCP_LEGACY = FIXTURES / "mcp-setup" / "legacy"
MCP_SCRIPT = MCP_LEGACY / "claude-code-wordpress-mcp-setup-script-v2.md"
MINI_SCRIPT = FIXTURES / "mini" / "mini-script.md"

sys.path.insert(0, str(SCRIPTS))

from handoff import header, input_ref  # noqa: E402
from number_sentences import number_script  # noqa: E402


def run_script(name: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                          capture_output=True, text=True)


# A valid mini chain. Sentences in mini-script.md:
#  1 Welcome back to the channel.   2 Today we fix the edit.   3 Fine.
#  4 This line is personal and goes to camera.
#  5 Open the settings panel on the left.   6 Click the export button at the bottom.
#  7 Wait for the progress bar to finish.   8 That is the whole demo in three steps.
#  9 Thanks for watching and see you next time.
MINI_PAPER_EDIT = {
    "title": "Mini test video",
    "notes": {"tone": "Light.", "blur_list": ["nothing"]},
    "sections": [{"id": "sec02", "purpose": "Show the export."}],
    "beats": [
        {"id": "b01", "section": "sec01", "sentences": [1, 3],
         "visual": "A, medium", "transition_in": "hard_cut", "cues": [
             {"id": "b01.mg1", "kind": "mg", "placement": "insert_before",
              "duration": {"seconds": 2.0}, "layer": "full",
              "brief": "Cold open sting"},
             {"id": "b01.sfx1", "kind": "sfx", "placement": "overlay",
              "anchor": {"cue": "b01.mg1"}, "brief": "low hit"},
             {"id": "b01.lt1", "kind": "lt", "placement": "overlay",
              "layer": "overlay", "anchor": {"sentence": 3},
              "duration": {"seconds": 1.5}, "brief": "anchored to a fragment"}]},
        {"id": "b02", "section": "sec01", "sentences": [4, 4],
         "visual": "A, punch in", "cues": []},
        {"id": "b03", "section": "sec02", "sentences": [5, 8],
         "chapter": "1. Demo",
         "visual": "SR: settings panel", "cues": [
             {"id": "b03.chapter1", "kind": "chapter",
              "placement": "insert_before", "layer": "full",
              "duration": {"seconds": 1.5}, "brief": "1. Demo"},
             {"id": "b03.sr1", "kind": "sr", "placement": "bed",
              "anchor": {"sentence": 5}, "brief": "settings panel"},
             {"id": "b03.lt1", "kind": "lt", "placement": "overlay",
              "layer": "overlay",
              "anchor": {"sentence": 6, "phrase": "export button"},
              "duration": {"to_phrase": "progress bar"},
              "brief": "Export"}]},
        {"id": "b04", "section": "sec03", "sentences": [9, 9],
         "visual": "A", "cues": []},
    ],
}

MINI_DIRECTOR = {
    "segments": [
        {"id": "b01", "beat": "b01", "mode": "th", "delivery": "warm"},
        {"id": "b02", "beat": "b02", "mode": "th"},
        {"id": "b03a", "beat": "b03", "sentences": [5, 6], "mode": "vo",
         "on_screen": "settings panel"},
        {"id": "b03b", "beat": "b03", "sentences": [7, 8], "mode": "vo",
         "on_screen": "progress bar"},
        {"id": "b04", "beat": "b04", "mode": "th"},
    ],
    "cues": [
        {"id": "b03.sr2", "kind": "sr", "placement": "bed",
         "anchor": {"sentence": 7}, "duration": "segment",
         "brief": "progress bar filling"},
    ],
    "judgement_calls": [{"segment": "b03b", "note": "could be TH"}],
}


class Chain:
    """Writes a script -> paper-edit -> director chain into a folder."""

    def __init__(self, folder: Path, script_md: Path = MINI_SCRIPT):
        self.dir = folder
        self.script_md = folder / script_md.name
        shutil.copy(script_md, self.script_md)
        self.script_json = folder / "mini.script.json"
        self.paper_edit = folder / "mini.paper-edit.json"
        self.director = folder / "mini.director.json"

    def write_script(self):
        doc = header("script", {"script": input_ref(self.script_md, self.dir)})
        doc.update(number_script(self.script_md.read_text()))
        self.script_json.write_text(json.dumps(doc, indent=1))
        return self

    def write_paper_edit(self, mutate=None):
        body = copy.deepcopy(MINI_PAPER_EDIT)
        if mutate:
            mutate(body)
        doc = header("paper-edit",
                     {"script": input_ref(self.script_json, self.dir)})
        doc.update(body)
        self.paper_edit.write_text(json.dumps(doc, indent=1))
        return self

    def write_director(self, mutate=None):
        body = copy.deepcopy(MINI_DIRECTOR)
        if mutate:
            mutate(body)
        doc = header("director",
                     {"paper_edit": input_ref(self.paper_edit, self.dir)})
        doc.update(body)
        self.director.write_text(json.dumps(doc, indent=1))
        return self

    def build(self, pe_mutate=None, d_mutate=None):
        return self.write_script().write_paper_edit(pe_mutate) \
                   .write_director(d_mutate)


@pytest.fixture
def chain(tmp_path):
    return Chain(tmp_path)


# --- synthetic cut: recordings -> match_takes -> edit-takes timeline -------------

def synthetic_cut(prompters: Path, out: Path, fluff_every: int = 6,
                  keep=None, fps: int = 25, segment_pause: float = 1.6) -> dict:
    """Synthesise TH/VO recordings of the prompters in `prompters`, cut them
    with the real match_takes (--sentences-out) and build the TH timeline
    with the real build_xml/auto-editor. Returns the utterance plan per
    mode. `keep(u)` can drop utterances to simulate things not recorded."""
    from make_synthetic_fixture import dummy_aroll, plan, transcript_mode
    expected = {}
    for mode in ("th", "vo"):
        prompter = prompters / f"{mode}.prompter.md"
        if not prompter.exists():
            continue
        utts = plan(mode, prompter.read_text(), fluff_every, segment_pause)
        if keep:
            utts = [u for u in utts if keep(mode, u)]
        if not utts:
            continue
        secs = transcript_mode(mode, utts, out)
        d = out / mode
        r = run_script("match_takes.py", d / "transcript.json", prompter,
                       "-o", d / "cuts.json", "--report", d / "report.md",
                       "--sentences-out", d / "sentences.json")
        assert r.returncode == 0, r.stderr
        if mode == "th":
            aroll = dummy_aroll(out, secs, fps, None)
            r = run_script("build_xml.py", d / "cuts.json", "--aroll", aroll,
                           "-o", d / "cut.fcpxml")
            assert r.returncode == 0, r.stderr + r.stdout
        expected[mode] = utts
    return expected


def run_conform(director: Path, pmap: Path, cut: Path, out: Path, *extra):
    args = ["--director", director, "--map", pmap, "-o", out]
    if (cut / "th").exists():
        args += ["--th", cut / "th", "--th-fcpxml", cut / "th" / "cut.fcpxml"]
    if (cut / "vo").exists():
        args += ["--vo", cut / "vo"]
    return run_script("conform.py", *args, *extra)
