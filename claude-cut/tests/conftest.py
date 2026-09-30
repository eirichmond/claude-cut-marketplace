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
                       "--marker-scope", "sentence",
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


# --- a graphics project on the synthetic MCP plan -------------------------------

SFX_FILES = [("Impacts/Impact - Deep - Snap.wav", "Impacts", 1),
             ("Whooshes/Whoosh - Pan - Heavy.wav", "Whooshes", 2),
             ("Clicks/Click - Keyboard 02.wav", "Clicks", 2)]
TEMPLATE_FOR = {
    "chapter": ("chapterCard", lambda c: {"num": "01", "kicker": "Chapter",
                                          "title": c["brief"][:30]}),
    "lt": ("lowerThird", lambda c: {"kicker": "Key term", "head": c["brief"][:40]}),
    "callout": ("callout", lambda c: {"kicker": "Key point", "text": c["brief"][:40]}),
}


def graphics_world(d: Path, fps: int = 25) -> dict:
    """Synthetic MCP cut -> conform -> a graphics project with the identity,
    custom compositions for the one-off mg cues, a small SFX library (real
    tone files) and its index. Returns paths and the plan."""
    import subprocess as sp
    import identity
    from handoff import header
    synthetic_cut(FIXTURES / "mcp-setup", d / "cut", fps=fps)
    mcp = FIXTURES / "mcp-setup"
    r = run_conform(mcp / "mcp-setup.director.json", mcp / "prompter.map.json",
                    d / "cut", d / "plan.resolved.json")
    assert r.returncode == 0, r.stdout
    gfx = d / "graphics"
    identity.install(gfx)
    lib = d / "sfxlib"
    for path, _, ch in SFX_FILES:
        (lib / path).parent.mkdir(parents=True, exist_ok=True)
        sp.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                "sine=frequency=660:duration=0.5:sample_rate=48000",
                "-ac", str(ch), str(lib / path)], check=True)
    index = header("sfx-index", {})
    index.update({"libraries": {"story": str(lib)},
                  "files": [{"library": "story", "path": p, "category": cat,
                             "name": Path(p).stem, "duration": 0.5, "channels": ch,
                             "rate": 48000} for p, cat, ch in SFX_FILES]})
    (gfx / "sfx-index.json").write_text(json.dumps(index))
    plan = json.loads((d / "plan.resolved.json").read_text())
    mg = [c for c in plan["cues"] if c["kind"] == "mg"]
    rows = [{"cue": c["id"], "template": "tag", "frames": c["tl"][1] - c["tl"][0],
             "fps": plan["timeline"]["fps"], "vars": {"text": "one-off"}} for c in mg]
    (gfx / "rows.json").write_text(json.dumps(rows))
    sp.run(["node", str(ROOT / "graphics" / "build.mjs"), str(gfx),
            str(gfx / "rows.json")], check=True, capture_output=True)
    (d / "shoot.json").write_text(json.dumps({
        "schema": "claude-cut/shoot@1", "th": {"aroll": "cut/aroll.mp4"},
        "vo": {"audio": "vo.wav"}, "assets": {}}))
    return {"dir": d, "gfx": gfx, "plan": plan, "shoot": d / "shoot.json"}


def graphics_body(world: dict) -> dict:
    """A complete graphics.json body for the world's plan."""
    g, sfx = [], []
    for c in world["plan"]["cues"]:
        if c["kind"] in TEMPLATE_FOR:
            name, make = TEMPLATE_FOR[c["kind"]]
            g.append({"cue": c["id"], "template": name, "vars": make(c)})
        elif c["kind"] == "mg":
            g.append({"cue": c["id"], "template": "custom",
                      "composition": f"compositions/{c['id']}.html"})
        elif c["kind"] == "sfx":
            sfx.append({"cue": c["id"], "library": "story", "file": SFX_FILES[0][0],
                        "gain_db": -6, "alternatives": [SFX_FILES[1][0]]})
    return {"graphics": g, "sfx": sfx, "skip": []}


def write_graphics_spec(world: dict, body: dict, sfx_index=True,
                        name="graphics.json") -> Path:
    from handoff import header, input_ref
    gfx = world["gfx"]
    doc = header("graphics-spec", {
        "plan": input_ref(world["dir"] / "plan.resolved.json", gfx),
        "frame": input_ref(gfx / "frame.md", gfx),
        **({"sfx_index": input_ref(gfx / "sfx-index.json", gfx)} if sfx_index else {})})
    doc.update(body)
    p = gfx / name
    p.write_text(json.dumps(doc, indent=1))
    return p
