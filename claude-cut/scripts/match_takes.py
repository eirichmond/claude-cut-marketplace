#!/usr/bin/env python3
"""Decide which time ranges to keep, based on the script and retake markers.

Usage:
    python match_takes.py transcript.json script.md -o cuts.json --report report.md

Logic:
  1. Chunk the word stream on pauses.
  2. Detect the spoken retake keyword ("retake cut" by default). A marker bins
     the chunks immediately before it that belong to the same attempt.
  3. Fuzzy-match remaining chunks against script sentences. Where a sentence
     was attempted more than once, keep only the LAST occurrence.
  4. Unmatched, un-binned speech (intros, ad-libs) is KEPT and flagged.
  5. Merge kept chunks into ranges, add handles.

Output cuts.json:
    {"ranges": [{"start": 1.0, "end": 9.4, "label": "s1-s3"}, ...],
     "timeline_duration": ...}
"""
import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from rapidfuzz import fuzz
except ImportError:
    sys.exit("rapidfuzz is not installed. Run: pip install rapidfuzz")

PAUSE_SPLIT = 0.8       # seconds of silence that starts a new chunk
MATCH_THRESHOLD = 70    # fuzz score (0-100) to accept a script match
TAKE_SPLIT = 2.5        # gap above which same-sentence chunks are separate takes


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9' ]+", " ", text.lower()).strip()


def split_sentences(script_text: str) -> list[str]:
    # Strip markdown furniture, then split on sentence enders.
    text = re.sub(r"^#{1,6} .*$", "", script_text, flags=re.M)
    text = re.sub(r"[*_`>\[\]()]", "", text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(norm(p).split()) >= 3]


@dataclass
class Chunk:
    words: list[dict] = field(default_factory=list)
    is_marker: bool = False
    match_idx: int = -1       # index into script sentences, -1 = off-script
    match_score: float = 0.0
    binned: bool = False
    bin_reason: str = ""
    rescued: bool = False

    @property
    def start(self) -> float:
        return self.words[0]["start"]

    @property
    def end(self) -> float:
        return self.words[-1]["end"]

    @property
    def text(self) -> str:
        return " ".join(w["word"] for w in self.words)


def chunk_words(words: list[dict]) -> list[Chunk]:
    chunks: list[Chunk] = []
    cur = Chunk()
    for w in words:
        if cur.words and w["start"] - cur.words[-1]["end"] > PAUSE_SPLIT:
            chunks.append(cur)
            cur = Chunk()
        cur.words.append(w)
    if cur.words:
        chunks.append(cur)
    return chunks


def mark_keyword(chunks: list[Chunk], keyword: str) -> list[Chunk]:
    """Find the keyword; split it out into its own marker chunk if embedded."""
    kw_words = norm(keyword).split()
    n = len(kw_words)
    out: list[Chunk] = []
    for ch in chunks:
        toks = [norm(w["word"]) for w in ch.words]
        i, last = 0, 0
        hits = []
        while i <= len(toks) - n:
            if toks[i:i + n] == kw_words:
                hits.append(i)
                i += n
            else:
                i += 1
        if not hits:
            out.append(ch)
            continue
        for h in hits:
            if h > last:
                out.append(Chunk(words=ch.words[last:h]))
            out.append(Chunk(words=ch.words[h:h + n], is_marker=True))
            last = h + n
        if last < len(ch.words):
            out.append(Chunk(words=ch.words[last:]))
    return [c for c in out if c.words]


def apply_markers(chunks: list[Chunk]) -> None:
    """A marker bins the preceding chunks that belong to the same attempt:
    walk backwards binning unmatched chunks and chunks matching the same
    sentence as the one directly before the marker."""
    for i, ch in enumerate(chunks):
        if not ch.is_marker:
            continue
        ch.binned, ch.bin_reason = True, "marker"
        anchor = -2  # sentinel: not yet established
        for j in range(i - 1, -1, -1):
            prev = chunks[j]
            if prev.is_marker:
                break
            if prev.binned:
                continue
            if anchor == -2:
                anchor = prev.match_idx
            if prev.match_idx == anchor or prev.match_idx == -1:
                prev.binned, prev.bin_reason = True, "before marker"
                if prev.match_idx != -1:
                    anchor = prev.match_idx
            else:
                break


def match_chunks(chunks: list[Chunk], sentences: list[str]) -> None:
    normed = [norm(s) for s in sentences]
    for ch in chunks:
        if ch.is_marker:
            continue
        best, best_score = -1, 0.0
        t = norm(ch.text)
        for idx, s in enumerate(normed):
            score = fuzz.token_sort_ratio(t, s)
            if score > best_score:
                best, best_score = idx, score
        if best_score >= MATCH_THRESHOLD:
            ch.match_idx, ch.match_score = best, best_score
        else:
            # try partial match for chunks that are fragments of a sentence
            for idx, s in enumerate(normed):
                score = fuzz.partial_ratio(t, s)
                if score > best_score:
                    best, best_score = idx, score
            if best_score >= MATCH_THRESHOLD + 15:
                ch.match_idx, ch.match_score = best, best_score


def last_take_wins(chunks: list[Chunk], coverage: float,
                   sentences: list[str]) -> None:
    """Pick the last DELIVERY of each sentence, not the last fragment.

    A single delivery is often split across several pause-separated chunks.
    Those are one take, not competing takes, so group adjacent chunks (no
    marker between them, small gap) before applying last-take-wins and
    measure coverage on the whole take. A matched sentence must never end
    up with nothing kept unless a marker explicitly binned it.
    """
    pos = {id(c): i for i, c in enumerate(chunks)}

    def marker_between(a: Chunk, b: Chunk) -> bool:
        return any(chunks[k].is_marker
                   for k in range(pos[id(a)] + 1, pos[id(b)]))

    by_sentence: dict[int, list[Chunk]] = {}
    for ch in chunks:
        if ch.is_marker or ch.binned or ch.match_idx < 0:
            continue
        by_sentence.setdefault(ch.match_idx, []).append(ch)

    for idx, group in by_sentence.items():
        sent_len = len(norm(sentences[idx]).split())
        takes: list[list[Chunk]] = [[group[0]]]
        for prev, cur in zip(group, group[1:]):
            if marker_between(prev, cur) or cur.start - prev.end > TAKE_SPLIT:
                takes.append([cur])
            else:
                takes[-1].append(cur)
        for take in takes[:-1]:
            for ch in take:
                ch.binned, ch.bin_reason = True, "earlier take"
        winner = takes[-1]
        n = sum(len(c.words) for c in winner)
        if n / max(sent_len, 1) < coverage:
            for ch in winner:
                ch.binned = True
                ch.bin_reason = f"partial take ({n}/{sent_len} words)"

    # Safety net: never let a sentence vanish because of the coverage test.
    # Marker decisions stay authoritative; only coverage kills are reversed.
    for idx, group in by_sentence.items():
        if any(not c.binned for c in group):
            continue
        rescue = [c for c in group if c.bin_reason.startswith("partial take")]
        if not rescue:
            continue
        for ch in rescue:
            ch.binned = False
            ch.bin_reason = ""
            ch.rescued = True


def build_ranges(chunks: list[Chunk], handles: float,
                 merge_gap: float) -> list[dict]:
    kept = [c for c in chunks if not c.binned and not c.is_marker]
    kept.sort(key=lambda c: c.start)
    ranges: list[dict] = []
    for ch in kept:
        s, e = max(0.0, ch.start - handles), ch.end + handles
        label = f"s{ch.match_idx + 1}" if ch.match_idx >= 0 else "off-script"
        if ranges and s - ranges[-1]["end"] <= merge_gap:
            ranges[-1]["end"] = e
            if label not in ranges[-1]["label"]:
                ranges[-1]["label"] += f",{label}"
        else:
            ranges.append({"start": round(s, 3), "end": round(e, 3),
                           "label": label})
    for r in ranges:
        r["start"], r["end"] = round(r["start"], 3), round(r["end"], 3)
    return ranges


def write_report(path: Path, chunks: list[Chunk], ranges: list[dict],
                 sentences: list[str], duration: float) -> None:
    lines = ["# claude-cut report", ""]
    kept_dur = sum(r["end"] - r["start"] for r in ranges)
    lines += [f"Source duration: {duration:.1f}s",
              f"Kept: {kept_dur:.1f}s across {len(ranges)} ranges",
              f"Script sentences: {len(sentences)}", "", "## Decisions", ""]
    for ch in chunks:
        t = f"{ch.start:7.1f}-{ch.end:7.1f}"
        if ch.is_marker:
            lines.append(f"- {t}  MARKER")
        elif ch.binned:
            lines.append(f"- {t}  BINNED ({ch.bin_reason}): {ch.text[:70]}")
        else:
            tag = (f"s{ch.match_idx + 1} @{ch.match_score:.0f}"
                   if ch.match_idx >= 0 else "OFF-SCRIPT (kept, check me)")
            if ch.rescued:
                tag += " RESCUED (low coverage, only take - check me)"
            lines.append(f"- {t}  KEEP [{tag}]: {ch.text[:70]}")
    lines += ["", "## Final ranges", ""]
    for r in ranges:
        lines.append(f"- {r['start']:.2f} -> {r['end']:.2f}  ({r['label']})")
    path.write_text("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("transcript", type=Path)
    ap.add_argument("script", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--keyword", default="retake cut")
    ap.add_argument("--handles", type=float, default=0.25)
    ap.add_argument("--merge-gap", type=float, default=1.0,
                    help="Merge kept ranges closer than this many seconds")
    ap.add_argument("--min-take-coverage", type=float, default=0.8)
    ap.add_argument("--marker-scope", choices=["chunk", "sentence"],
                    default="chunk",
                    help="What 'retake cut' bins. chunk (default, v0.4.0): "
                         "everything since the last pause. sentence: only "
                         "from where the retaken sentence began, keeping good "
                         "lines said in the same breath before it.")
    ap.add_argument("--sentences-out", type=Path,
                    help="Also write per-sentence timings (s1, s2...) for the "
                         "pipeline's conform stage. Doesn't change the cut.")
    args = ap.parse_args()

    data = json.loads(args.transcript.read_text())
    words = data["words"]
    if not words:
        sys.exit("Transcript contains no words. Wrong audio track?")
    sentences = split_sentences(args.script.read_text())
    if not sentences:
        sys.exit("No usable sentences found in the script file.")

    chunks = chunk_words(words)
    chunks = mark_keyword(chunks, args.keyword)
    match_chunks(chunks, sentences)
    if args.marker_scope == "sentence":
        from retake_scope import apply_markers_sentence
        chunks = apply_markers_sentence(chunks, sentences,
                                        lambda ws: Chunk(words=ws), match_chunks)
    else:
        apply_markers(chunks)
    last_take_wins(chunks, args.min_take_coverage, sentences)
    ranges = build_ranges(chunks, args.handles, args.merge_gap)

    if not ranges:
        sys.exit("Nothing survived the cut. Check the script matches the "
                 "footage and the match threshold isn't too strict.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        {"ranges": ranges, "source_duration": data.get("duration", 0)},
        indent=1))
    if args.report:
        write_report(args.report, chunks, ranges, sentences,
                     data.get("duration", 0))
    if args.sentences_out:
        from sentence_timings import write_sentence_timings
        write_sentence_timings(args.sentences_out, args.transcript, args.script,
                               data, chunks, ranges, sentences)
    kept = sum(r["end"] - r["start"] for r in ranges)
    print(f"Kept {kept:.1f}s of {data.get('duration', 0):.1f}s "
          f"in {len(ranges)} ranges -> {args.output}")


if __name__ == "__main__":
    main()
