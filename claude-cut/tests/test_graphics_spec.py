"""graphics.json: every graphic and sfx cue covered once, valid template
vars, custom compositions on-identity, SFX picks in the index."""
import copy
import json
import shutil
import subprocess

import pytest

import identity
from conftest import FIXTURES, ROOT, run_conform, run_script, synthetic_cut
from handoff import header, input_ref
from validate import validate_file

MCP = FIXTURES / "mcp-setup"
pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="needs node")

TEMPLATE_FOR = {
    "chapter": ("chapterCard", lambda c: {"num": "01", "kicker": "Chapter",
                                          "title": c["brief"][:30]}),
    "lt": ("lowerThird", lambda c: {"kicker": "Key term", "head": c["brief"][:40]}),
    "callout": ("callout", lambda c: {"kicker": "Key point", "text": c["brief"][:40]}),
}
SFX_FILES = [("Impacts/Impact - Deep - Snap.wav", "Impacts"),
             ("Whooshes/Whoosh - Pan - Heavy.wav", "Whooshes"),
             ("Clicks/Click - Keyboard 02.wav", "Clicks")]


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    d = tmp_path_factory.mktemp("gspec")
    synthetic_cut(MCP, d / "cut")
    r = run_conform(MCP / "mcp-setup.director.json", MCP / "prompter.map.json",
                    d / "cut", d / "plan.resolved.json")
    assert r.returncode == 0, r.stdout
    gfx = d / "graphics"
    identity.install(gfx)
    index = header("sfx-index", {})
    index.update({"libraries": {"story": "/Volumes/Terrance/assets/The Story Sound Pack"},
                  "files": [{"library": "story", "path": p, "category": cat,
                             "name": p.split("/")[1][:-4], "duration": 0.8,
                             "channels": 2, "rate": 48000} for p, cat in SFX_FILES]})
    (gfx / "sfx-index.json").write_text(json.dumps(index))
    plan = json.loads((d / "plan.resolved.json").read_text())
    # one-off graphics: a real composition, built from a template, used as custom
    mg = [c for c in plan["cues"] if c["kind"] == "mg"]
    rows = [{"cue": c["id"], "template": "tag", "frames": c["tl"][1] - c["tl"][0] or 25,
             "fps": "25/1", "vars": {"text": "one-off"}} for c in mg]
    (gfx / "rows.json").write_text(json.dumps(rows))
    subprocess.run(["node", str(ROOT / "graphics" / "build.mjs"), str(gfx),
                    str(gfx / "rows.json")], check=True, capture_output=True)
    return {"dir": d, "gfx": gfx, "plan": plan}


def body(world):
    g, sfx, skip = [], [], []
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
    return {"graphics": g, "sfx": sfx, "skip": skip}


def write(world, b, sfx_index=True, name="graphics.json"):
    gfx = world["gfx"]
    doc = header("graphics-spec", {
        "plan": input_ref(world["dir"] / "plan.resolved.json", gfx),
        "frame": input_ref(gfx / "frame.md", gfx),
        **({"sfx_index": input_ref(gfx / "sfx-index.json", gfx)} if sfx_index else {})})
    doc.update(b)
    p = gfx / name
    p.write_text(json.dumps(doc, indent=1))
    return p


def errors(world, mutate=None, **kw):
    b = body(world)
    if mutate:
        mutate(b)
    return validate_file(write(world, b, **kw))[1]


def test_complete_spec_validates(world):
    b = body(world)
    kinds = {c["kind"] for c in world["plan"]["cues"]}
    assert {"chapter", "lt", "callout", "mg", "sfx"} <= kinds   # the MCP plan has all
    assert errors(world) == []


def test_write_handoff_stamps_and_summarises(world, tmp_path):
    draft = tmp_path / "draft.json"
    draft.write_text(json.dumps(body(world)))
    out = world["gfx"] / "graphics.cli.json"
    r = run_script("write_handoff.py", "graphics-spec", draft,
                   "--input", f"plan={world['dir'] / 'plan.resolved.json'}",
                   "--input", f"frame={world['gfx'] / 'frame.md'}",
                   "--input", f"sfx_index={world['gfx'] / 'sfx-index.json'}",
                   "-o", out)
    assert r.returncode == 0, r.stdout
    assert "graphics (" in r.stdout and "sound effects" in r.stdout
    assert json.loads(out.read_text())["schema"] == "claude-cut/graphics-spec@1"


def test_every_graphic_and_sfx_cue_must_be_covered(world):
    def m(b):
        b["graphics"].pop(0)
        b["sfx"].pop(0)
    errs = errors(world, m)
    missing = [e for e in errs if "not in graphics, sfx or skip" in e]
    assert len(missing) == 2


def test_skipping_is_explicit_and_counts_as_covered(world):
    def m(b):
        g = b["graphics"].pop(0)
        b["skip"].append({"cue": g["cue"], "reason": "done by hand in Resolve"})
    assert errors(world, m) == []


def test_duplicates_unknown_cues_and_wrong_kinds(world):
    plan = world["plan"]
    blur = next(c["id"] for c in plan["cues"] if c["kind"] == "blur")
    lt = next(c["id"] for c in plan["cues"] if c["kind"] == "lt")
    def m(b):
        b["skip"].append({"cue": b["graphics"][0]["cue"], "reason": "twice"})
        b["skip"].append({"cue": "b99.mg1", "reason": "no such cue"})
        b["skip"].append({"cue": blur, "reason": "zoom/blur are Resolve's job"})
        b["sfx"].append({"cue": lt, "library": "story", "file": SFX_FILES[0][0]})
    errs = "\n".join(errors(world, m))
    assert "listed in graphics and skip" in errs
    assert "b99.mg1: not a cue in the plan" in errs
    assert f"{blur}: blur cues aren't listed; they stay markers" in errs
    assert f"{lt}: a lt cue can't have a sound effect" in errs


def test_template_vars_are_checked_against_the_template(world):
    def pick(b, name, n=0):
        return [g for g in b["graphics"] if g["template"] == name][n]
    def m(b):
        pick(b, "chapterCard")["vars"] = {"num": "01"}
        pick(b, "lowerThird")["template"] = "spinner"
        pick(b, "callout")["vars"]["pos"] = "centre"
    errs = "\n".join(errors(world, m))
    assert "(chapterCard): missing kicker" in errs
    assert "no template 'spinner'" in errs
    assert "(callout): pos must be one of bl, br, tl, tr" in errs


def test_custom_compositions_must_exist_and_follow_the_identity(world):
    mg = [g for g in body(world)["graphics"] if g["template"] == "custom"]
    comp = world["gfx"] / mg[0]["composition"]
    original = comp.read_text()
    try:
        comp.write_text(original.replace("var(--accent)", "#FF00FF", 1))
        def m(b):
            b["graphics"].append({"cue": "b99.mg1", "template": "custom",
                                  "composition": "compositions/nope.html"})
        errs = "\n".join(errors(world, m))
    finally:
        comp.write_text(original)
    assert f"{mg[0]['cue']}: colour #FF00FF isn't in frame.md's palette" in errs
    assert "compositions/nope.html doesn't exist" in errs


def test_sfx_picks_must_be_in_the_index(world):
    def m(b):
        b["sfx"][0]["file"] = "Whooshes/Not A Real File.wav"
        b["sfx"][0]["alternatives"] = ["Impacts/Also Missing.wav"]
    errs = "\n".join(errors(world, m))
    assert "'Whooshes/Not A Real File.wav' isn't in the 'story' library index" in errs
    assert "'Impacts/Also Missing.wav' isn't in" in errs
    assert "sfx picks need the sfx index" in "\n".join(errors(world, sfx_index=False))


def test_stale_plan_is_refused(world):
    p = write(world, body(world), name="stale.json")
    doc = json.loads(p.read_text())
    doc["inputs"]["plan"]["sha256"] = "0" * 64
    p.write_text(json.dumps(doc))
    errs = validate_file(p)[1]
    assert len(errs) == 1 and "has changed since this file was written" in errs[0]
