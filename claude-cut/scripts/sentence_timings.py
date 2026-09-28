"""Per-sentence timings for a finished take selection.

Called by match_takes.py when --sentences-out is given, after the ranges
are built. It never changes a decision; it only labels what survived.

Why alignment rather than reading chunk labels: a kept pause-chunk often
runs two sentences together and carries a single match_idx. So the kept
words (words inside the kept ranges, minus retake-marker words) are aligned
to the script's sentence token stream with difflib, giving every kept word
a sentence number. Sentence numbers are match_takes' own (s1 = first entry
of split_sentences), so they line up with the report.

Output: see schemas/sentences.schema.json.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from handoff import header, input_ref


def kept_words(words: list[dict], ranges: list[dict],
               marker_ids: set[int]) -> list[dict]:
    """Transcript words whose midpoint falls in a kept range."""
    out, i = [], 0
    spans = sorted((r["start"], r["end"]) for r in ranges)
    for w in words:
        if id(w) in marker_ids:
            continue
        mid = (w["start"] + w["end"]) / 2
        while i < len(spans) and spans[i][1] < mid:
            i += 1
        if i < len(spans) and spans[i][0] <= mid <= spans[i][1]:
            out.append(w)
    return out


def word_key(token: str) -> str:
    """One comparison key per whitespace word, with every non-alphanumeric
    dropped. match_takes strips '_' and '`' from the script but turns them
    into spaces in speech, so `WP_API_URL` only lines up as 'wpapiurl'."""
    return re.sub(r"[^a-z0-9]", "", token.lower())


def align(kept: list[dict], sentences: list[str]) -> list[int | None]:
    """Sentence index (0-based) for each kept word, or None if off-script."""
    ref, ref_sent = [], []
    for idx, s in enumerate(sentences):
        for tok in s.split():
            key = word_key(tok)
            if key:
                ref.append(key)
                ref_sent.append(idx)
    hyp, hyp_word = [], []
    for wi, w in enumerate(kept):
        key = word_key(w["word"])
        if key:
            hyp.append(key)
            hyp_word.append(wi)

    label: list[int | None] = [None] * len(kept)
    sm = difflib.SequenceMatcher(None, hyp, ref, autojunk=False)
    for a, b, size in sm.get_matching_blocks():
        # A lone matching word is as likely to be a coincidence (the same
        # word further down the script) as a real match. Trust runs of two
        # or more; the gap fill below picks up singles inside a sentence.
        if size < 2:
            continue
        for k in range(size):
            label[hyp_word[a + k]] = ref_sent[b + k]

    # A word the aligner skipped (a mis-heard token) belongs to the sentence
    # on both sides of it, if those agree. Otherwise it stays off-script.
    prev = [None] * len(kept)
    last = None
    for i, lab in enumerate(label):
        if lab is not None:
            last = lab
        prev[i] = last
    nxt = None
    for i in range(len(kept) - 1, -1, -1):
        if label[i] is not None:
            nxt = label[i]
        elif prev[i] is not None and prev[i] == nxt:
            label[i] = nxt
    return label


def sentence_timings(words: list[dict], chunks: list, ranges: list[dict],
                     sentences: list[str]) -> dict:
    marker_ids = {id(w) for c in chunks if c.is_marker for w in c.words}
    kept = kept_words(words, ranges, marker_ids)
    labels = align(kept, sentences)

    by_sent: dict[int, list[dict]] = {}
    unaligned: list[list[dict]] = []
    prev_off = False
    for w, lab in zip(kept, labels):
        if lab is None:
            # one span per run of off-script words, split across cuts
            if prev_off and w["start"] - unaligned[-1][-1]["end"] <= 1.0:
                unaligned[-1].append(w)
            else:
                unaligned.append([w])
        else:
            by_sent.setdefault(lab, []).append(w)
        prev_off = lab is None

    survivors = [c for c in chunks
                 if not c.is_marker and not c.binned and c.match_idx >= 0]
    out = []
    for idx in range(len(sentences)):
        ws = by_sent.get(idx)
        entry = {"s": idx + 1}
        if not ws:
            entry["status"] = "missing"
            out.append(entry)
            continue
        own = [c for c in survivors if c.match_idx == idx]
        entry["status"] = "rescued" if any(c.rescued for c in own) else "kept"
        entry["start"] = round(min(w["start"] for w in ws), 3)
        entry["end"] = round(max(w["end"] for w in ws), 3)
        if own:
            entry["score"] = round(max(c.match_score for c in own))
        entry["words"] = [{"w": w["word"], "start": w["start"],
                           "end": w["end"]} for w in ws]
        out.append(entry)

    return {
        "sentences": out,
        "unaligned": [{"start": g[0]["start"], "end": g[-1]["end"],
                       "text": " ".join(w["word"] for w in g)}
                      for g in unaligned],
    }


def write_sentence_timings(out: Path, transcript_path: Path, script_path: Path,
                           data: dict, chunks: list, ranges: list[dict],
                           sentences: list[str]) -> dict:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = header("sentences", {
        "script": input_ref(script_path, out.parent),
        "transcript": input_ref(transcript_path, out.parent),
    })
    doc["source"] = data.get("source", "")
    doc.update(sentence_timings(data["words"], chunks, ranges, sentences))
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    return doc
