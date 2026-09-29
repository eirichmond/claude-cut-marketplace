"""--marker-scope sentence: a retake marker bins only what the retake repeats.

v0.4.0 (the default, --marker-scope chunk) bins the whole pause-chunk before
"retake cut". A fluff delivered mid-flow shares its chunk with the good
sentences said just before it, so when the presenter restarts from the
fluffed sentence (not the paragraph), those good sentences are lost.

Here, for each marker:
  1. the restart point is the first script sentence matched after the
     marker (before the next one);
  2. the words since the previous marker are aligned to the script;
  3. everything from where that sentence began in the fluffed attempt up to
     the marker is binned; words of earlier sentences stay.

Restarting from the start of the paragraph restarts at its first sentence,
so the whole attempt is binned, as before. If nothing after a marker matches
the script (an off-script restart), or nothing before it can be aligned,
that marker falls back to the v0.4.0 behaviour.
"""
from __future__ import annotations

from sentence_timings import align

REASON = "before marker (retaken)"


def _chunk_scope(chunks: list, i: int) -> None:
    """v0.4.0's rule for the one marker at chunks[i] (see apply_markers)."""
    anchor = -2
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


def _restart(chunks: list, i: int) -> int | None:
    """Script sentence the retake after chunks[i] starts with."""
    for ch in chunks[i + 1:]:
        if ch.is_marker:
            return None
        if ch.match_idx >= 0:
            return ch.match_idx
    return None


def apply_markers_sentence(chunks: list, sentences: list[str],
                           make_chunk, match_chunks) -> list:
    """Returns the new chunk list (chunks may be split at the restart point).
    make_chunk(words) builds a Chunk; match_chunks re-matches split parts."""
    out: list = []
    attempt: list = []   # chunks since the previous marker, not yet decided

    for i, ch in enumerate(chunks):
        if not ch.is_marker:
            attempt.append(ch)
            continue
        ch.binned, ch.bin_reason = True, "marker"
        k = _restart(chunks, i)
        live = [c for c in attempt if not c.binned]
        words = [w for c in live for w in c.words]
        labels = align(words, sentences) if (k is not None and words) else []
        if k is None or not any(l is not None for l in labels):
            # can't tell what was retaken: v0.4.0 behaviour for this marker
            seg = attempt + [ch]
            _chunk_scope(seg, len(seg) - 1)
            out += seg
            attempt = []
            continue

        # "retake cut" always means what was just being said is bad, even
        # when the retake moves on instead of repeating it: start from the
        # earlier of the restart and the sentence the marker interrupted.
        k = min(k, next(l for l in reversed(labels) if l is not None))
        # Keep through the last word of an earlier sentence said before the
        # retaken one began; bin from there. Filler between them ("Okay.",
        # "Now") goes with the fluff: left as a stub it could be matched as a
        # later take of some other sentence and bin the real one.
        # Only within the breath the fluff started in, though: a fragment
        # after a pause ("Sweet huh!", too short to match) is a line of its own.
        first_retaken = next((n for n, l in enumerate(labels)
                              if l is not None and l >= k), len(labels))
        earlier = [n for n, l in enumerate(labels[:first_retaken])
                   if l is not None and l < k]
        starts, n = [], 0
        for c in live:
            starts.append(n)
            n += len(c.words)
        breath = max(s for s in starts if s <= min(first_retaken, n - 1))
        cut = max(earlier[-1] + 1 if earlier else 0, breath)

        n = 0
        for c in attempt:
            if c.binned:
                out.append(c)
                continue
            lo, hi = n, n + len(c.words)
            n = hi
            if hi <= cut:
                out.append(c)                                # all kept
            elif lo >= cut:
                c.binned, c.bin_reason = True, REASON        # all retaken
                out.append(c)
            else:                                            # split it
                keep = make_chunk(c.words[:cut - lo])
                drop = make_chunk(c.words[cut - lo:])
                match_chunks([keep], sentences)
                drop.binned, drop.bin_reason = True, REASON
                out += [keep, drop]
        out.append(ch)
        attempt = []
    return out + attempt
