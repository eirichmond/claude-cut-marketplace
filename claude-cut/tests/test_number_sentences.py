import json
import re
from collections import Counter

from conftest import MCP_LEGACY, MCP_SCRIPT, MINI_SCRIPT, run_script
from handoff import norm_words
from number_sentences import number_script


def test_mini_sentences_sections_and_cues():
    doc = number_script(MINI_SCRIPT.read_text())
    texts = [s["text"] for s in doc["sentences"]]
    assert texts == [
        "Welcome back to the channel.", "Today we fix the edit.", "Fine.",
        "This line is personal and goes to camera.",
        "Open the settings panel on the left.",
        "Click the export button at the bottom.",
        "Wait for the progress bar to finish.",
        "That is the whole demo in three steps.",
        "Thanks for watching and see you next time.",
    ]
    assert [s["n"] for s in doc["sentences"]] == list(range(1, 10))
    assert [(s["id"], s["title"], s["first"], s["last"])
            for s in doc["sections"]] == [
        ("sec01", "Hook", 1, 4), ("sec02", "Demo", 5, 8),
        ("sec03", "Outro", 9, 9)]
    assert doc["preamble"] == ["Bracketed lines are cues, not narration."]
    assert doc["title"] == "Mini test video"
    kinds = [(c["kind"], c["after"]) for c in doc["script_cues"]]
    assert kinds == [("bracket", 0), ("bracket", 4), ("code", 7)]
    # paragraphs survive for rendering
    assert [s["para"] for s in doc["sentences"]] == [1, 1, 1, 2, 3, 3, 3, 4, 5]


def test_body_stops_at_rule():
    doc = number_script(MINI_SCRIPT.read_text())
    assert not any("Metadata" in s["text"] or "Not spoken" in s["text"]
                   for s in doc["sentences"])


def test_missing_script_heading_is_an_error(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("# Title\n\nJust some words here.\n")
    r = run_script("number_sentences.py", p)
    assert r.returncode != 0
    assert "no '## Script' heading" in r.stderr


def test_cli_writes_header(tmp_path):
    out = tmp_path / "mini.script.json"
    r = run_script("number_sentences.py", MINI_SCRIPT, "-o", out)
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text())
    assert doc["schema"] == "claude-cut/script@1"
    assert len(doc["inputs"]["script"]["sha256"]) == 64


def test_mcp_fixture_numbering():
    doc = number_script(MCP_SCRIPT.read_text())
    assert len(doc["sentences"]) == 168
    assert len(doc["sections"]) == 13
    # level-2 headings inside the script body are sections, not the end
    assert doc["sections"][10]["title"].startswith("Confession time")
    assert doc["sections"][10]["level"] == 2
    # short fragments keep their own number
    short = {s["n"]: s["text"] for s in doc["sentences"]
             if len(s["text"].split()) < 3}
    assert short[6] == "Fine."
    assert "Sweet huh!" in short.values()
    # the .mcp.json code block is a cue, not speech
    code = [c for c in doc["script_cues"] if c["kind"] == "code"]
    assert len(code) == 1 and '"mcpServers"' in code[0]["text"]
    assert not any("mcpServers\":" in s["text"] for s in doc["sentences"])


def test_mcp_fixture_matches_legacy_director_words():
    """Every quoted line in the legacy director file is verbatim script, so
    the numbered sentences must hold exactly the same words."""
    doc = number_script(MCP_SCRIPT.read_text())
    ours = Counter(w for s in doc["sentences"] for w in norm_words(s["text"]))
    legacy = (MCP_LEGACY /
              "claude-code-wordpress-mcp-setup-script-v2-director.md").read_text()
    legacy = legacy.split("## 3. Running order")[0]
    quotes = re.findall(r"^> (.*)$", legacy, flags=re.M)
    theirs = Counter(w for q in quotes for w in norm_words(q))
    assert ours == theirs
