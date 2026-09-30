"""The channel identity: identity/frame.md, its fonts, install and check."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import identity
from conftest import ROOT, run_script

GRAPHICS = ROOT / "graphics"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node")


def test_tokens_from_the_plugin_frame():
    tok = identity.tokens()
    assert tok["name"].startswith("Elliott Richmond")
    assert tok["colors"]["accent"] == "#00C8E0"
    assert tok["colors"]["background"] == "#0D1F28"
    assert tok["fonts"] == {"display": "Anton", "body": "Anton", "mono": "DM Mono"}
    assert tok["font_files"]["Anton"] == {400: "anton-latin-400-normal.woff2"}
    assert set(tok["font_files"]["DM Mono"]) == {400, 500}
    assert tok["typography"]["label"]["family"] == "DM Mono"
    assert tok["typography"]["display"]["family"] == "Anton"
    assert len(tok["frame_sha256"]) == 64


def test_frame_keeps_the_original_values_under_semantic_names():
    """SOURCE.md's mapping: every original colour value, renamed."""
    src = (ROOT / "identity" / "SOURCE.md").read_text()
    mapping = re.findall(r"^\| `([a-z-]+)` \| `([a-z-]+)` \| `([^`]+)` \|$", src, re.M)
    assert len(mapping) == 11
    colors = identity.tokens()["colors"]
    for new, old, value in mapping:
        assert colors[new] == value, new


def test_frame_uses_no_broadside_names():
    text = (ROOT / "identity" / "frame.md").read_text()
    assert not identity.LEGACY.search(text)


def test_anton_roles_use_its_only_weight():
    typo = identity.tokens()["typography"]
    assert all(r["weight"] == 400 for r in typo.values() if r["family"] == "Anton")


def frame_variant(tmp_path, change):
    text = (ROOT / "identity" / "frame.md").read_text()
    p = tmp_path / "frame.md"
    p.write_text(change(text))
    return p


def test_missing_colour_and_font_role_are_refused(tmp_path):
    p = frame_variant(tmp_path, lambda t: t.replace('  accent: "#00C8E0"\n', "")
                      .replace('  mono: "DM Mono"\n', ""))
    with pytest.raises(ValueError) as e:
        identity.tokens(p)
    msg = str(e.value)
    assert "colors.accent is missing" in msg
    assert "fonts.mono is missing" in msg
    assert "typography.label uses font role 'mono'" in msg


def test_missing_font_file_is_refused(tmp_path):
    p = frame_variant(tmp_path, lambda t: t.replace('mono: "DM Mono"',
                                                    'mono: "JetBrains Mono"'))
    with pytest.raises(ValueError, match="no font file for JetBrains Mono"):
        identity.tokens(p)


def test_install_puts_frame_md_at_the_project_root(tmp_path):
    """HyperFrames' skills read lowercase frame.md from the project root."""
    tok = identity.install(tmp_path / "gfx")
    root = tmp_path / "gfx"
    assert (root / "frame.md").read_bytes() == \
        (ROOT / "identity" / "frame.md").read_bytes()
    for fam in tok["font_files"].values():
        for f in fam.values():
            assert (root / "fonts" / f).exists()
    assert (root / "fonts" / "OFL-Anton.txt").exists()
    assert json.loads((root / "identity.json").read_text())["colors"]["accent"] \
        == "#00C8E0"


def test_cli_install_and_tokens(tmp_path):
    r = run_script("identity.py", "install", tmp_path / "gfx")
    assert r.returncode == 0 and "Elliott Richmond" in r.stdout
    r = run_script("identity.py", "tokens")
    assert json.loads(r.stdout)["fonts"]["mono"] == "DM Mono"


# --- check ------------------------------------------------------------------

BAD = """<style>
  .a { color: #F8635F; background: var(--fire-orange); border-color: var(--nope); }
  .b { font-family: "Barlow", sans-serif; }
  .c { color: rgba(1,2,3,0.5); font-family: "Anton"; background: #0d1f28; }
</style>"""


def test_check_flags_everything_off_identity():
    issues = identity.check(BAD, identity.tokens())
    text = "\n".join(issues)
    assert "colour #F8635F isn't in frame.md's palette" in text
    assert "colour rgba(1,2,3,0.5) isn't in frame.md's palette" in text
    assert "font 'Barlow' has no file" in text
    assert "var(--nope) isn't a colour" in text
    assert "var(--fire-orange) isn't a colour" in text
    assert "'fire-orange' is a Broadside name" in text
    assert "'Barlow' is a Broadside name" in text
    # palette colours (any case) and real fonts pass
    assert "#0d1f28" not in text and "'Anton'" not in text


def test_check_cli_exit_codes(tmp_path):
    bad = tmp_path / "bad.html"
    bad.write_text(BAD)
    good = tmp_path / "good.html"
    good.write_text('<p style="color: var(--accent); font-family: \'DM Mono\'">x</p>')
    r = run_script("identity.py", "check", good)
    assert r.returncode == 0 and r.stdout.startswith("OK")
    r = run_script("identity.py", "check", good, bad)
    assert r.returncode == 1 and "FAIL" in r.stdout


def test_templates_use_semantic_names_only():
    for f in list(GRAPHICS.rglob("*.mjs")):
        text = f.read_text()
        assert not identity.LEGACY.search(text), f
        assert not re.search(r"#[0-9a-fA-F]{6}\b", text), f"hex colour in {f}"


@needs_node
def test_built_compositions_pass_the_check(tmp_path):
    identity.install(tmp_path)
    rows = [{"cue": "b01.lt1", "template": "lowerThird", "frames": 125,
             "fps": "25/1", "vars": {"kicker": "Key term", "head": "*mcp* = x",
                                     "line": "A line of body text."}},
            {"cue": "b01.sl1", "template": "slideAcross", "frames": 38,
             "fps": "25/1", "vars": {"text": "slide"}}]
    (tmp_path / "rows.json").write_text(json.dumps(rows))
    r = subprocess.run(["node", str(GRAPHICS / "build.mjs"), str(tmp_path),
                        str(tmp_path / "rows.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    tok = json.loads((tmp_path / "identity.json").read_text())
    for row in rows:
        html = (tmp_path / "compositions" / f"{row['cue']}.html").read_text()
        assert identity.check(html, tok) == [], row["cue"]
        assert 'data-duration="5"' in html or row["frames"] != 125
        assert "../fonts/anton-latin-400-normal.woff2" in html
