"""Shared helpers for the pipeline handoff files.

Every handoff JSON carries a header:
    {"schema": "claude-cut/<kind>@<n>", "created": "...",
     "inputs": {"<role>": {"path": "...", "sha256": "..."}}}

Input paths are stored relative to the directory of the file that records
them, so a project folder can move without breaking its handoffs.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
SCHEMA_RE = re.compile(r"^claude-cut/([a-z-]+)@(\d+)$")


class HandoffError(Exception):
    """A handoff file is missing, malformed, stale or legacy."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def input_ref(path: Path, relative_to: Path) -> dict:
    """Header entry for an input file, path relative to the output's dir."""
    rel = os.path.relpath(Path(path).resolve(), Path(relative_to).resolve())
    return {"path": rel, "sha256": sha256(path)}


def header(kind: str, inputs: dict, version: int = 1) -> dict:
    return {
        "schema": f"claude-cut/{kind}@{version}",
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
    }


def schema_kind(doc: dict) -> str:
    m = SCHEMA_RE.match(str(doc.get("schema", "")))
    if not m:
        raise HandoffError("not a claude-cut handoff file (no 'schema' field)")
    return m.group(1)


def load(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise HandoffError(f"{path}: file not found")
    if path.suffix.lower() != ".json":
        raise HandoffError(legacy_message(path))
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise HandoffError(f"{path}: invalid JSON ({e})")


def resolve_input(doc_path: Path, doc: dict, role: str,
                  check_hash: bool = True) -> Path:
    """Locate an input named in a file's header and check it isn't stale."""
    ref = doc.get("inputs", {}).get(role)
    if not ref:
        raise HandoffError(f"{doc_path.name}: header has no '{role}' input")
    p = (Path(doc_path).parent / ref["path"]).resolve()
    if not p.exists():
        raise HandoffError(f"{doc_path.name}: input '{role}' not found at {p}")
    if check_hash and sha256(p) != ref.get("sha256"):
        raise HandoffError(
            f"{doc_path.name}: input '{role}' ({p.name}) has changed since this "
            f"file was written. It's stale: re-run the stage that made it.")
    return p


def legacy_message(path: Path) -> str:
    name = Path(path).name.lower()
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        text = ""
    if re.search(r"^\s*#+\s*b\d{2,3}[a-z]?\b", text, re.M) or \
            re.search(r"\bb\d{2,3}\.[a-z]+\d+\b", text):
        return (f"{Path(path).name}: this is a rendered markdown view. "
                f"Validate the .json it was rendered from.")
    if "director" in name or re.search(r"^#\s*Director\b", text, re.M):
        stage = "director"
    elif "paper-edit" in name or "paper edit" in name or \
            re.search(r"^#\s*Paper Edit\b", text, re.M):
        stage = "paper-edit"
    else:
        return (f"{Path(path).name}: not a claude-cut handoff file "
                f"(expected .json with a 'schema' field)")
    label, source = (("paper edit", "the script") if stage == "paper-edit"
                     else ("director file", "the new paper edit"))
    return (f"{Path(path).name}: legacy {label} (no segment IDs): "
            f"re-run /claude-cut:{stage} on {source}")


# --- text helpers shared by validation, rendering and prompters ----------

def norm_words(text: str) -> list[str]:
    """Lowercase word tokens with markdown furniture stripped."""
    text = re.sub(r"[*_`>\[\]()\"“”]", " ", text.lower())
    text = text.replace("’", "'")
    return re.findall(r"[a-z0-9']+", text)


def phrase_in(phrase: str, text: str) -> bool:
    p, t = norm_words(phrase), norm_words(text)
    if not p:
        return False
    return any(t[i:i + len(p)] == p for i in range(len(t) - len(p) + 1))


BEAT_RE = re.compile(r"^b\d{2,3}$")
SEGMENT_RE = re.compile(r"^(b\d{2,3})([a-z]?)$")
CUE_KINDS = ("mg", "lt", "chapter", "callout", "sr", "br", "zoom", "blur",
             "sfx", "music", "marker")
CUE_RE = re.compile(r"^(b\d{2,3})\.(" + "|".join(CUE_KINDS) + r")(\d+)$")
