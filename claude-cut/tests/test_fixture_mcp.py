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
