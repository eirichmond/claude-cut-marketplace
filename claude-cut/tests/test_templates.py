"""The graphics templates: schemas, validation, markup, timing and identity."""
import json
import re
import shutil
import subprocess

import pytest

import identity
from conftest import ROOT

GRAPHICS = ROOT / "graphics"
pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="needs node")

PRODUCTION = {"chapterCard", "lowerThird", "callout", "tag", "keyTerm", "warningStrip"}
MINIMAL = {
    "chapterCard": {"num": "01", "kicker": "Step one", "title": "the user"},
    "lowerThird": {"kicker": "Key term", "head": "mcp"},
    "callout": {"kicker": "Key point", "text": "lowest role"},
    "tag": {"text": "Later in the video"},
    "keyTerm": {"term": "MCP"},
    "warningStrip": {"kicker": "Warning", "head": "never commit passwords"},
    "slideAcross": {"text": "slide"},
}


def listing():
    r = subprocess.run(["node", str(GRAPHICS / "build.mjs"), "--list"],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


@pytest.fixture
def project(tmp_path):
    identity.install(tmp_path)
    return tmp_path


def build(project, rows):
    (project / "rows.json").write_text(json.dumps(rows))
    return subprocess.run(["node", str(GRAPHICS / "build.mjs"), str(project),
                           str(project / "rows.json")], capture_output=True, text=True)


def row(template, frames=100, **vars_):
    return {"cue": f"b01.{template.lower()}1", "template": template,
            "frames": frames, "fps": "25/1", "vars": vars_ or MINIMAL[template]}


def test_list_has_every_production_template_with_schemas():
    tpl = listing()
    assert PRODUCTION <= set(tpl)
    for name in PRODUCTION:
        assert tpl[name]["layer"] == "overlay"
        assert any(v["required"] for v in tpl[name]["variables"].values())
        for spec in tpl[name]["variables"].values():
            assert spec["type"] in ("string", "number", "boolean", "enum")
            assert spec["label"]


def test_minimal_vars_build_and_pass_the_identity_check(project):
    r = build(project, [row(t) for t in MINIMAL])
    assert r.returncode == 0, r.stderr
    tok = json.loads((project / "identity.json").read_text())
    for t in MINIMAL:
        html = (project / "compositions" / f"b01.{t.lower()}1.html").read_text()
        assert identity.check(html, tok) == [], t
        assert '<script src="../vendor/gsap.min.js">' in html
        assert "cdn." not in html and "googleapis" not in html   # nothing remote


def test_invalid_vars_are_all_reported(project):
    rows = [row("lowerThird", head="x"),                        # missing kicker
            row("callout", kicker="k", text="t", pos="middle"),  # bad enum
            row("keyTerm", term="MCP", code="yes"),              # wrong type
            row("tag", text="t", colour="red"),                  # unknown var
            {**row("tag"), "frames": 0},
            {**row("tag"), "template": "nope"}]
    r = build(project, rows)
    assert r.returncode == 1
    for want in ["missing kicker", "pos must be one of bl, br, tl, tr",
                 "code must be a boolean", "unknown colour",
                 "frames must be a positive integer", "no template nope"]:
        assert want in r.stderr, want


def test_text_is_escaped_and_markup_is_inline_only(project):
    r = build(project, [row("lowerThird", kicker="<b>k</b>",
                            head="*mcp* = `x` <script>alert(1)</script>",
                            line="a & b")])
    assert r.returncode == 0, r.stderr
    html = (project / "compositions" / "b01.lowerthird1.html").read_text()
    assert "&lt;b&gt;k&lt;/b&gt;" in html
    assert "<em>mcp</em> = <code>x</code> &lt;script&gt;" in html
    assert "a &amp; b" in html
    assert "<script>alert" not in html


@pytest.mark.parametrize("frames", [20, 50, 150])
def test_every_move_finishes_inside_the_cue(project, frames):
    """In/out timings shrink for short cues: no tween may run past the end."""
    r = build(project, [row(t, frames) for t in PRODUCTION])
    assert r.returncode == 0, r.stderr
    dur = frames / 25
    for t in PRODUCTION:
        html = (project / "compositions" / f"b01.{t.lower()}1.html").read_text()
        assert f'data-duration="{dur:g}"' in html, t
        for d, at in re.findall(r"duration: ([\d.]+)[^}]*\}, ([\d.]+)\);", html):
            assert float(at) + float(d) <= dur + 1e-6, (t, d, at)
            assert float(at) >= 0


def test_chapter_card_picks_display_size_by_title_length(project):
    r = build(project, [{**row("chapterCard"), "cue": "b01.a"},
                        {**row("chapterCard", num="02", kicker="k",
                               title="the application password"), "cue": "b01.b"}])
    assert r.returncode == 0, r.stderr
    short = (project / "compositions" / "b01.a.html").read_text()
    long_ = (project / "compositions" / "b01.b.html").read_text()
    assert "font-size: 13cqw" in short and "font-size: 7.5cqw" in long_
