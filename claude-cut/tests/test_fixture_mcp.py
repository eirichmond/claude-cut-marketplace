"""The MCP video, run through the new skills, as a regression fixture."""
import json

from conftest import FIXTURES
from validate import lint_file, validate_file

MCP = FIXTURES / "mcp-setup"


def test_script_json_is_current():
    assert validate_file(MCP / "mcp-setup.script.json") == ("script", [])


def test_paper_edit_validates_with_no_notes():
    path = MCP / "mcp-setup.paper-edit.json"
    assert validate_file(path) == ("paper-edit", [])
    assert lint_file(path) == []


def test_paper_edit_covers_every_sentence():
    pe = json.loads((MCP / "mcp-setup.paper-edit.json").read_text())
    ranges = [b["sentences"] for b in pe["beats"]]
    assert ranges[0][0] == 1 and ranges[-1][1] == 168
    assert all(b[0] == a[1] + 1 for a, b in zip(ranges, ranges[1:]))


def test_paper_edit_render_is_current():
    from render_md import render
    md = (MCP / "mcp-setup.paper-edit.md").read_text()
    assert md == render(MCP / "mcp-setup.paper-edit.json")


def test_director_and_map_validate():
    assert validate_file(MCP / "mcp-setup.director.json") == ("director", [])
    assert validate_file(MCP / "prompter.map.json") == ("prompter-map", [])


def test_director_render_is_current():
    from render_md import render
    md = (MCP / "mcp-setup.director.md").read_text()
    assert md == render(MCP / "mcp-setup.director.json")


def test_prompters_rebuild_byte_identical(tmp_path):
    from conftest import run_script
    r = run_script("build_prompters.py", MCP / "mcp-setup.director.json",
                   "--out-dir", tmp_path)
    assert r.returncode == 0, r.stdout
    for f in ("th.prompter.md", "vo.prompter.md"):
        assert (tmp_path / f).read_bytes() == (MCP / f).read_bytes()


def test_parity_with_legacy_director_is_reported_not_enforced():
    """The legacy director is a reference: differences are printed, never
    a failure. Word-level agreement is only sanity-checked."""
    from conftest import MCP_LEGACY, run_script
    r = run_script("director_parity.py", MCP / "mcp-setup.director.json",
                   MCP_LEGACY / "claude-code-wordpress-mcp-setup-script-v2-director.md",
                   "--th", MCP_LEGACY / "th.md", "--vo", MCP_LEGACY / "vo.md")
    assert r.returncode == 0, r.stderr
    assert "Mode parity with" in r.stdout
    assert "th.prompter.md vs th.md" in r.stdout
    assert "Information only" in r.stdout
    assert "Script sentences not found in the legacy file" not in r.stdout


def test_real_prompters_round_trip_through_the_cut(tmp_path):
    """Read the MCP prompters aloud (synthetically) and cut them: every s in
    the map, including the ?" straddle, gets exactly its script words."""
    import subprocess
    import sys
    from conftest import SCRIPTS
    from speech import transcript
    m = json.loads((MCP / "prompter.map.json").read_text())["prompters"]
    script = json.loads((MCP / "mcp-setup.script.json").read_text())
    by_n = {s["n"]: s["text"] for s in script["sentences"]}
    straddles = 0
    for mode in ("th", "vo"):
        prompter = MCP / f"{mode}.prompter.md"
        spoken = [l for l in prompter.read_text().splitlines()
                  if l and not l.startswith("#")]
        tr = tmp_path / f"{mode}.json"
        tr.write_text(json.dumps(transcript([(1.2, p) for p in spoken])))
        out = tmp_path / f"{mode}.sentences.json"
        r = subprocess.run([sys.executable, str(SCRIPTS / "match_takes.py"),
                            tr, prompter, "-o", tmp_path / f"{mode}.cuts.json",
                            "--sentences-out", out],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        timed = {s["s"]: s for s in json.loads(out.read_text())["sentences"]}
        for e in m[mode]["sentences"]:
            ns = e["n"] if isinstance(e["n"], list) else [e["n"]]
            straddles += isinstance(e["segment"], list)
            got = " ".join(w["w"] for w in timed[e["s"]]["words"])
            assert got == " ".join(by_n[n] for n in ns), (mode, e)
    assert straddles == 1
