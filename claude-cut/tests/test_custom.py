"""custom.py: one-off compositions for mg cues -- brief, scaffold, the house
rules (also enforced by validate.py), and HyperFrames' own check with stills
(slow)."""
import json
import shutil
import subprocess

import pytest

from conftest import (ROOT, graphics_body, graphics_world, run_script,
                      write_graphics_spec)
from custom import house_rules
from validate import validate_file

pytestmark = pytest.mark.skipif(not (shutil.which("node") and shutil.which("ffmpeg")),
                                reason="needs node and ffmpeg")
EXAMPLE = ROOT / "graphics" / "examples" / "access-stamp.html"


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return graphics_world(tmp_path_factory.mktemp("custom"))


def cue(world, kind="mg", layer="full"):
    return next(c for c in world["plan"]["cues"]
                if c["kind"] == kind and c.get("layer", "overlay") == layer)


def custom(*args):
    return run_script("custom.py", *args)


def tok(world):
    return json.loads((world["gfx"] / "identity.json").read_text())


def rules(world, html, seconds=2.0, overlay=False):
    return house_rules(html, seconds=seconds, overlay=overlay, tok=tok(world),
                       comp_dir=world["gfx"] / "compositions")


def test_brief_has_what_the_author_needs(world):
    c = cue(world)
    r = custom("brief", world["gfx"], c["id"], "--json")
    assert r.returncode == 0, r.stderr
    b = json.loads(r.stdout)
    assert b["frames"] == c["tl"][1] - c["tl"][0] and b["fps"] == "25/1"
    assert b["seconds"] == pytest.approx(b["frames"] / 25)
    assert b["layer"] == "full" and "replaces the picture" in b["underneath"]
    assert b["brief"] == c["brief"]
    assert "Claude Code" in b["spoken"]                 # the words over the cue
    assert "accent" in b["colors"] and "h1" in b["type_roles"]
    text = custom("brief", world["gfx"], c["id"]).stdout
    assert f"{b['frames']} frames at 25/1" in text and "var(--accent)" in text


def test_brief_all_lists_every_graphic_in_timeline_order(world):
    r = custom("brief", world["gfx"], "--all", "--json")
    assert r.returncode == 0, r.stderr
    got = [b["cue"] for b in json.loads(r.stdout)]
    want = [c["id"] for c in sorted(world["plan"]["cues"], key=lambda c: c["tl"][0])
            if c["kind"] in ("mg", "lt", "chapter", "callout")]
    assert got == want
    text = custom("brief", world["gfx"], "--all").stdout
    assert text.count("identity (frame.md):") == 1
    assert "brief takes a CUE or --all" in custom("brief", world["gfx"]).stderr


def test_brief_says_what_an_overlay_sits_on(world):
    b = json.loads(custom("brief", world["gfx"], cue(world, layer="overlay")["id"],
                          "--json").stdout)
    assert b["layer"] == "overlay"
    assert b["underneath"].startswith(("the talking head", "the sr bed", "the br bed",
                                       "voiceover", "an insert"))


def test_only_graphic_cues(world):
    sfx = next(c for c in world["plan"]["cues"] if c["kind"] == "sfx")
    r = custom("new", world["gfx"], sfx["id"])
    assert r.returncode == 1 and "isn't a graphic" in r.stderr
    assert "not a cue" in custom("brief", world["gfx"], "b99.mg9").stderr


@pytest.mark.parametrize("layer", ["full", "overlay"])
def test_scaffold_is_the_house_shell_and_must_be_authored(world, layer):
    c = cue(world, layer=layer)
    path = world["gfx"] / "compositions" / f"{c['id']}.html"
    before = path.read_text()                           # graphics_world wrote one
    r = custom("new", world["gfx"], c["id"])
    assert r.returncode == 1 and "already exists" in r.stderr
    assert path.read_text() == before
    assert custom("new", world["gfx"], c["id"], "--force").returncode == 0
    html = path.read_text()
    seconds = (c["tl"][1] - c["tl"][0]) / 25
    assert rules(world, html, seconds, layer == "overlay") == [
        "still the scaffold: author the design, then delete the claude-cut:scaffold line"]
    authored = "\n".join(l for l in html.splitlines() if "claude-cut:scaffold" not in l)
    assert rules(world, authored, seconds, layer == "overlay") == []
    r = custom("check", world["gfx"], c["id"], "--no-hf")
    assert r.returncode == 1 and "still the scaffold" in r.stdout
    path.write_text(authored)
    assert custom("check", world["gfx"], c["id"], "--no-hf").returncode == 0
    path.write_text(before)


def test_house_rules_catch_what_breaks_a_render(world):
    good = EXAMPLE.read_text()
    assert rules(world, good) == []
    broken = {
        "data-duration is 3": good.replace('data-duration="2"', 'data-duration="3"'),
        "window.__timelines": good.replace('window.__timelines["b01-mg1"] = tl;', ""),
        'data-width="1920"': good.replace('data-width="1920"', 'data-width="1280"'),
        "exactly one element": good.replace(
            "</body>", '<div data-composition-id="x" data-duration="2"></div></body>'),
        "fetches something": good.replace(
            '<script src="../vendor/gsap.min.js">',
            '<script src="https://cdn.example.com/gsap.min.js">'),
        "uses ../assets/terminal.png": good.replace(
            '<div class="bar">', '<img src="../assets/terminal.png"><div class="bar">'),
        "colour #ff0000": good.replace("var(--accent); padding: 0.4cqw",
                                       "#ff0000; padding: 0.4cqw"),
    }
    for want, html in broken.items():
        errs = rules(world, html)
        assert any(want in e for e in errs), (want, errs)


def test_an_overlay_must_be_transparent(world):
    opaque = EXAMPLE.read_text()                      # a full-frame design
    errs = rules(world, opaque, overlay=True)
    assert any("background: transparent" in e for e in errs)


def test_validation_rejects_a_scaffolded_custom_entry(world):
    c = cue(world)
    path = world["gfx"] / "compositions" / f"{c['id']}.html"
    before = path.read_text()
    try:
        custom("new", world["gfx"], c["id"], "--force")
        spec = write_graphics_spec(world, graphics_body(world))
        _, errs = validate_file(spec)
        assert f"{c['id']}: still the scaffold: author the design, then delete " \
               f"the claude-cut:scaffold line" in errs
    finally:
        path.write_text(before)


@pytest.mark.slow
def test_hyperframes_check_and_stills(world):
    """The real gate: the example passes HyperFrames' check and gives stills;
    unmarked deliberate layering is caught."""
    c = next(x for x in world["plan"]["cues"] if x["id"] == "b01.mg1")
    assert c["tl"][1] - c["tl"][0] == 50                # the example's 2.0s
    path = world["gfx"] / "compositions" / "b01.mg1.html"
    before = path.read_text()
    try:
        shutil.copyfile(EXAMPLE, path)
        r = custom("check", world["gfx"], "b01.mg1", "--at", "0.3,1.2")
        assert r.returncode == 0, r.stdout + r.stderr
        stills = [l.split("still: ")[1] for l in r.stdout.splitlines() if "still: " in l]
        assert len(stills) == 2
        size = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                               "stream=width,height", "-of", "csv=p=0", stills[1]],
                              capture_output=True, text=True).stdout.strip()
        assert size == "1920,1080"
        assert not (world["gfx"] / ".check" / "b01.mg1").exists()
        path.write_text(EXAMPLE.read_text().replace(" data-layout-allow-occlusion", "")
                        .replace(" data-layout-ignore", ""))
        r = custom("check", world["gfx"], "b01.mg1")
        assert r.returncode == 1 and "layout:" in r.stdout
    finally:
        path.write_text(before)
