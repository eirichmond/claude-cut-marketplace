"""render_graphics.py: exact frames at the timeline rate, incremental
re-renders that keep review decisions, review proxies in context, the SFX
stem. Uses the ffmpeg stand-in for HyperFrames (CLAUDE_CUT_FAKE_RENDER);
the real renderer is in the slow test at the bottom."""
import json
import shutil
import subprocess

import pytest

from conftest import graphics_body, graphics_world, run_script, write_graphics_spec
from render_graphics import count_frames
from validate import validate_file

pytestmark = pytest.mark.skipif(not (shutil.which("node") and shutil.which("ffmpeg")),
                                reason="needs node and ffmpeg")


def render(world, *extra, fake=True, env=None):
    import os
    e = {**os.environ, **(env or {})}
    if fake:
        e["CLAUDE_CUT_FAKE_RENDER"] = "1"
    else:
        e.pop("CLAUDE_CUT_FAKE_RENDER", None)
    from conftest import SCRIPTS
    import sys
    return subprocess.run([sys.executable, str(SCRIPTS / "render_graphics.py"),
                           str(world["gfx"]), "--shoot", str(world["shoot"]), *extra],
                          capture_output=True, text=True, env=e)


def manifest(world):
    return json.loads((world["gfx"] / "renders" / "manifest.json").read_text())


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    w = graphics_world(tmp_path_factory.mktemp("render"))
    write_graphics_spec(w, graphics_body(w))
    r = render(w)
    assert r.returncode == 0, r.stderr + r.stdout
    w["first"] = r.stdout
    return w


def cue(world, cid):
    return next(c for c in world["plan"]["cues"] if c["id"] == cid)


def test_every_graphic_renders_to_its_exact_frame_count(world):
    m = manifest(world)
    assert validate_file(world["gfx"] / "renders" / "manifest.json") == ("graphics", [])
    graphic = [c for c in world["plan"]["cues"]
               if c["kind"] in ("mg", "lt", "chapter", "callout")]
    assert {r["cue"] for r in m["renders"]} == {c["id"] for c in graphic}
    for r in m["renders"]:
        c = cue(world, r["cue"])
        assert r["frames"] == c["tl"][1] - c["tl"][0]
        assert count_frames(world["gfx"] / r["file"]) == r["frames"], r["cue"]
        assert r["fps"] == "25/1" and r["rendered_at_fps"] == 60
        assert r["review"] == {"status": "pending", "note": ""}


def test_overlays_keep_alpha_and_full_frames_do_not(world):
    for r in manifest(world)["renders"]:
        codec = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=profile,pix_fmt", "-of", "csv=p=0", world["gfx"] / r["file"]],
            capture_output=True, text=True).stdout.strip()
        if r["layer"] == "overlay":
            assert "4444" in codec and "yuva" in codec, r["cue"]
            assert r["transparent"] > 0.5
        else:
            assert "HQ" in codec and "yuva" not in codec, r["cue"]


def test_review_proxies_show_the_picture_underneath(world):
    m = manifest(world)
    for r in m["renders"]:
        p = world["gfx"] / r["proxy"]
        info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                               "-show_entries", "stream=codec_name,width,height",
                               "-of", "csv=p=0", p], capture_output=True,
                              text=True).stdout.strip()
        assert info == "h264,1280,720", r["cue"]
        seg = cue(world, r["cue"])["segment"]
        mode = next(s["mode"] for s in world["plan"]["segments"] if s["id"] == seg)
        f = sum(cue(world, r["cue"])["tl"]) // 2
        in_th = any(s["mode"] == "th" and s["tl"][0] <= f < s["tl"][1]
                    for s in world["plan"]["segments"])
        if r["layer"] == "overlay":
            assert r["proxy_context"] == ("picture" if in_th else "plate"), r["cue"]


def test_unchanged_rerun_reuses_everything_and_keeps_review(world):
    mp = world["gfx"] / "renders" / "manifest.json"
    m = manifest(world)
    m["renders"][0]["review"] = {"status": "approved", "note": ""}
    mp.write_text(json.dumps(m))
    r = render(world)
    assert r.returncode == 0, r.stderr
    assert "rendered" not in r.stdout and r.stdout.count("reused") >= len(m["renders"])
    assert manifest(world)["renders"][0]["review"]["status"] == "approved"


def test_a_changed_cue_rerenders_alone_and_returns_to_review(world):
    body = graphics_body(world)
    lt = next(g for g in body["graphics"] if g["template"] == "lowerThird")
    lt["vars"]["head"] = "*mcp* changed"
    write_graphics_spec(world, body)
    mp = world["gfx"] / "renders" / "manifest.json"
    m = manifest(world)
    for x in m["renders"]:
        x["review"] = {"status": "approved", "note": ""}
    mp.write_text(json.dumps(m))
    r = render(world)
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("rendered ") == 1 and f"rendered {lt['cue']}" in r.stdout
    after = {x["cue"]: x["review"]["status"] for x in manifest(world)["renders"]}
    assert after[lt["cue"]] == "pending"
    assert all(s == "approved" for c, s in after.items() if c != lt["cue"])


def test_only_rerenders_what_it_names(world):
    target = manifest(world)["renders"][-1]["cue"]
    r = render(world, "--only", target)
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("rendered ") == 1 and f"rendered {target}" in r.stdout


def test_custom_composition_must_last_as_long_as_its_cue(world):
    custom = next(g for g in graphics_body(world)["graphics"]
                  if g["template"] == "custom")
    comp = world["gfx"] / custom["composition"]
    original = comp.read_text()
    try:
        comp.write_text(original.replace('data-duration="', 'data-duration="9', 1))
        r = render(world, "--only", custom["cue"])
    finally:
        comp.write_text(original)
    assert r.returncode == 1
    assert f"{custom['cue']}: {custom['composition']} lasts 9" in r.stderr
    assert "the cue needs" in r.stderr


def test_sfx_stem_is_full_length_stereo_with_effects_at_their_frames(world):
    m = manifest(world)
    stem = world["gfx"] / m["sfx"]["file"]
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=channels,sample_rate:format=duration", "-of", "json", stem],
        capture_output=True, text=True).stdout)
    assert info["streams"][0]["channels"] == 2
    assert info["streams"][0]["sample_rate"] == "48000"
    assert float(info["format"]["duration"]) == pytest.approx(
        world["plan"]["timeline"]["frames"] / 25, abs=0.01)
    for it in m["sfx"]["items"]:
        t = it["frame"] / 25
        def peak(at):
            out = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{at:.3f}", "-t",
                                  "0.3", "-i", str(stem), "-af", "volumedetect",
                                  "-f", "null", "-"], capture_output=True, text=True)
            return float(out.stderr.split("max_volume:")[1].split("dB")[0])
        assert peak(t + 0.05) > -40              # the effect is there...
        assert peak(max(0, t - 0.6)) < -80       # ...and silence before it
        assert (world["gfx"] / "sfx" / f"{it['cue']} Impact - Deep - Snap.wav").exists()


def test_sfx_changes_remix_and_reset_that_effect(world):
    body = graphics_body(world)
    body["sfx"][0]["gain_db"] = -12
    write_graphics_spec(world, body)
    before = manifest(world)["sfx"]["sha256"]
    r = render(world)
    assert r.returncode == 0 and "mixed    sfx stem" in r.stdout
    m = manifest(world)
    assert m["sfx"]["sha256"] != before
    assert m["sfx"]["items"][0]["review"]["status"] == "pending"


def test_native_timeline_rate_renders_without_conversion(tmp_path):
    w = graphics_world(tmp_path, fps=30)
    body = graphics_body(w)
    keep = next(g for g in body["graphics"] if g["template"] == "lowerThird")
    body = {"graphics": [keep], "sfx": [],
            "skip": [{"cue": g["cue"], "reason": "test"} for g in body["graphics"]
                     if g is not keep] +
                    [{"cue": s["cue"], "reason": "test"} for s in body["sfx"]]}
    write_graphics_spec(w, body)
    r = render(w)
    assert r.returncode == 0, r.stderr + r.stdout
    (only,) = manifest(w)["renders"]
    assert only["fps"] == "30/1" and only["rendered_at_fps"] == 30
    assert count_frames(w["gfx"] / only["file"]) == only["frames"]


@pytest.mark.slow
def test_real_hyperframes_render_of_one_template(world):
    """The real renderer: one lower third at 60fps converted to 25."""
    lt = next(g["cue"] for g in graphics_body(world)["graphics"]
              if g["template"] == "lowerThird")
    r = render(world, "--only", lt, "--quality", "draft", fake=False)
    assert r.returncode == 0, r.stderr + r.stdout
    got = next(x for x in manifest(world)["renders"] if x["cue"] == lt)
    assert count_frames(world["gfx"] / got["file"]) == got["frames"]
    assert 0.5 < got["transparent"] < 1.0      # a panel, and alpha around it
