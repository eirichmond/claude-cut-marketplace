"""In-memory view of the script / paper-edit / director handoffs.

Loads the chain of files through their headers (checking hashes, so a stale
upstream is caught) and answers the questions every later stage asks:
what text is in a beat, which segment owns a sentence, which segment a cue
lands on.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from handoff import SEGMENT_RE, HandoffError, load, resolve_input, schema_kind


@dataclass
class Script:
    path: Path
    doc: dict
    by_n: dict = field(init=False)

    def __post_init__(self):
        self.by_n = {s["n"]: s for s in self.doc["sentences"]}

    @property
    def count(self) -> int:
        return len(self.doc["sentences"])

    def text(self, first: int, last: int) -> str:
        return " ".join(self.by_n[n]["text"]
                        for n in range(first, last + 1) if n in self.by_n)

    def paragraphs(self, first: int, last: int) -> list[str]:
        """Text grouped by script paragraph, for readable renders."""
        out, cur, para = [], [], None
        for n in range(first, last + 1):
            s = self.by_n.get(n)
            if not s:
                continue
            if para is not None and s["para"] != para:
                out.append(" ".join(cur))
                cur = []
            para = s["para"]
            cur.append(s["text"])
        if cur:
            out.append(" ".join(cur))
        return out


def expect_kind(path: Path, doc: dict, kind: str) -> None:
    got = schema_kind(doc)
    if got != kind:
        raise HandoffError(f"{Path(path).name}: expected a {kind} file, got {got}")


def load_script(path: Path) -> Script:
    doc = load(path)
    expect_kind(path, doc, "script")
    return Script(Path(path), doc)


def load_paper_edit(path: Path, check_hash: bool = True):
    """Return (paper_edit_doc, Script)."""
    doc = load(path)
    expect_kind(path, doc, "paper-edit")
    script = load_script(resolve_input(Path(path), doc, "script", check_hash))
    return doc, script


def load_director(path: Path, check_hash: bool = True):
    """Return (director_doc, paper_edit_doc, paper_edit_path, Script)."""
    doc = load(path)
    expect_kind(path, doc, "director")
    pe_path = resolve_input(Path(path), doc, "paper_edit", check_hash)
    pe, script = load_paper_edit(pe_path, check_hash)
    return doc, pe, pe_path, script


def segment_parts(seg_id: str):
    m = SEGMENT_RE.match(seg_id)
    return (m.group(1), m.group(2)) if m else (None, None)


def segment_ranges(director: dict, paper_edit: dict) -> list[dict]:
    """Segments in running order with their sentence range filled in.

    Unsplit segments inherit the beat's range. Assumes a valid director.
    """
    beats = {b["id"]: b for b in paper_edit["beats"]}
    out = []
    for seg in director["segments"]:
        rng = seg.get("sentences") or beats[seg["beat"]]["sentences"]
        out.append({**seg, "sentences": list(rng)})
    return out


def sentence_owner(segments: list[dict]) -> dict:
    """Map sentence number -> segment id."""
    owner = {}
    for seg in segments:
        a, b = seg["sentences"]
        for n in range(a, b + 1):
            owner.setdefault(n, seg["id"])
    return owner


def all_cues(paper_edit: dict, director: dict | None = None) -> list[dict]:
    """Every cue with its parent beat id, paper-edit first then director.

    With a director, its reanchor entries are applied: the paper-edit cue
    keeps its ID and brief, only the anchor changes, and '_reanchor' holds
    the entry so renders can show it.
    """
    moves = {}
    if director:
        for r in director.get("reanchor", []):
            moves.setdefault(r["cue"], r)
    cues = []
    for beat in paper_edit["beats"]:
        for c in beat.get("cues", []):
            cue = {**c, "_beat": beat["id"], "_from": "paper-edit"}
            if c["id"] in moves:
                move = moves[c["id"]]
                cue["anchor"] = dict(move["to"])
                if "retime" in move:
                    cue["duration"] = move["retime"]["to"]
                cue["_reanchor"] = move
            cues.append(cue)
    if director:
        for c in director.get("cues", []):
            cues.append({**c, "_beat": c["id"].split(".")[0], "_from": "director"})
    return cues


def cue_anchor_sentence(cue: dict, beats: dict, cues_by_id: dict,
                        _seen=None) -> int | None:
    """Sentence number a cue is anchored to (following cue->cue anchors)."""
    _seen = _seen or set()
    if cue["id"] in _seen:
        return None
    _seen.add(cue["id"])
    anchor = cue.get("anchor")
    if not anchor:
        beat = beats.get(cue["_beat"])
        return beat["sentences"][0] if beat else None
    if "sentence" in anchor:
        return anchor["sentence"]
    target = cues_by_id.get(anchor["cue"])
    if not target:
        return None
    return cue_anchor_sentence(target, beats, cues_by_id, _seen)


# --- word positions (for checking cue timing before anything is recorded) --

WPM = 150


def segment_words(script: Script, seg: dict) -> list[tuple[int, str]]:
    """(sentence number, normalised word) for every word in a segment."""
    from handoff import norm_words
    a, b = seg["sentences"]
    return [(n, w) for n in range(a, b + 1)
            for w in norm_words(script.by_n[n]["text"])]


def find_phrase(words: list[tuple[int, str]], phrase: str,
                start: int = 0, sentence: int | None = None) -> int | None:
    """Index of the first word of `phrase` at or after `start` (optionally
    only inside `sentence`), or None."""
    from handoff import norm_words
    p = norm_words(phrase)
    toks = [w for _, w in words]
    for i in range(start, len(toks) - len(p) + 1):
        if toks[i:i + len(p)] == p and \
                (sentence is None or words[i][0] == sentence):
            return i
    return None


def anchor_index(words: list[tuple[int, str]], anchor: dict | None) -> int:
    """Word index a sentence anchor points at within a segment (0 if the
    anchor isn't in it)."""
    if not anchor or "sentence" not in anchor:
        return 0
    first = next((i for i, (n, _) in enumerate(words)
                  if n == anchor["sentence"]), 0)
    if "phrase" in anchor:
        at = find_phrase(words, anchor["phrase"], first, anchor["sentence"])
        return first if at is None else at
    return first


def covered_words(words: list[tuple[int, str]], anchor: dict | None,
                  duration) -> tuple[int, int] | None:
    """Estimated [start, end) word span a cue covers inside its segment,
    before any recording exists. None if the duration can't be placed."""
    from handoff import norm_words
    start = anchor_index(words, anchor)
    if duration in (None, "segment", "to_beat_end"):
        return start, len(words)
    if isinstance(duration, dict) and "seconds" in duration:
        return start, min(len(words),
                          start + round(duration["seconds"] * WPM / 60))
    if isinstance(duration, dict) and "to_phrase" in duration:
        at = find_phrase(words, duration["to_phrase"], start)
        if at is None:
            return None
        return start, at + len(norm_words(duration["to_phrase"]))
    return None
