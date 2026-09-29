#!/usr/bin/env python3
"""Compare a new director file with a legacy (pre-pipeline) one. Info only.

Usage:
    python director_parity.py NEW.director.json LEGACY-director.md \\
        [--th th.md] [--vo vo.md] [--prompters DIR]

Reports, per legacy TH-xx / VO-xx line, whether the new director gave the
same words the same mode, and (with --th/--vo) how the generated prompters
differ from hand-made ones. Always exits 0 unless the inputs can't be read:
the legacy files are a reference, not a spec.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from handoff import HandoffError, norm_words
from model import load_director, segment_ranges, sentence_owner

LEGACY_ID = re.compile(r"^\*\*((TH|VO)-\d+)\*\*\s*$")


def legacy_lines(md: str) -> list[tuple[str, str, str]]:
    """(id, mode, text) for each quoted line in a legacy director file."""
    md = md.split("## 3. Running order")[0]
    out, cur = [], None
    for line in md.splitlines():
        m = LEGACY_ID.match(line.strip())
        if m:
            cur = [m.group(1), m.group(2).lower(), []]
            out.append(cur)
        elif cur and line.startswith("> "):
            cur[2].append(line[2:])
    return [(i, mode, " ".join(t)) for i, mode, t in out]


def locate(words: list[str], sentences: list[tuple[int, list[str]]]) -> list[int]:
    """Script sentence numbers whose words appear, in order, inside words."""
    hay = " " + " ".join(words) + " "
    return [n for n, sw in sentences if sw and " " + " ".join(sw) + " " in hay]


def mode_parity(director: Path, legacy_md: Path) -> list[str]:
    d, pe, _, script = load_director(director)
    segments = segment_ranges(d, pe)
    owner = sentence_owner(segments)
    mode_of = {s["id"]: s["mode"] for s in segments}
    sents = [(s["n"], norm_words(s["text"])) for s in script.doc["sentences"]]

    lines = legacy_lines(legacy_md.read_text())
    report, same_words, total_words, placed = [], 0, 0, set()
    diffs = []
    for lid, lmode, text in lines:
        ns = locate(norm_words(text), sents)
        placed.update(ns)
        for n in ns:
            w = len(script.by_n[n]["text"].split())
            total_words += w
            if mode_of[owner[n]] == lmode:
                same_words += w
        new_modes = {(owner[n], mode_of[owner[n]]) for n in ns}
        if any(m != lmode for _, m in new_modes):
            segs = ", ".join(f"{sid} ({m.upper()})"
                             for sid, m in sorted(new_modes))
            diffs.append(f"- {lid} was {lmode.upper()}; now {segs}")
    unplaced = [n for n, _ in sents if n not in placed]
    pct = 100 * same_words / max(total_words, 1)
    report.append(f"Mode parity with {legacy_md.name}: {pct:.0f}% of words "
                  f"have the same mode ({len(lines)} legacy lines, "
                  f"{len(segments)} new segments).")
    if diffs:
        report.append(f"{len(diffs)} legacy line(s) where the mode changed:")
        report += diffs
    if unplaced:
        report.append(f"Script sentences not found in the legacy file: "
                      f"{', '.join(map(str, unplaced))}")
    return report


def prompter_sentences(text: str) -> list[str]:
    body = "\n".join(l for l in text.splitlines()
                     if not l.startswith("#") and not LEGACY_ID.match(l.strip()))
    parts = re.split(r"(?<=[.!?])\s+", body)
    return [" ".join(norm_words(p)) for p in parts if norm_words(p)]


def prompter_diff(label: str, generated: Path, legacy: Path) -> list[str]:
    new = prompter_sentences(generated.read_text())
    old = prompter_sentences(legacy.read_text())
    only_new = [s for s in new if s not in old]
    only_old = [s for s in old if s not in new]
    out = [f"{label}: {generated.name} vs {legacy.name}: {len(new)} vs "
           f"{len(old)} sentences, {len(only_new)} only in generated, "
           f"{len(only_old)} only in legacy."]
    for s in only_new[:10]:
        out.append(f"  + {s[:90]}")
    for s in only_old[:10]:
        out.append(f"  - {s[:90]}")
    if len(only_new) > 10 or len(only_old) > 10:
        out.append("  (first 10 of each shown)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("director", type=Path)
    ap.add_argument("legacy", type=Path)
    ap.add_argument("--th", type=Path)
    ap.add_argument("--vo", type=Path)
    ap.add_argument("--prompters", type=Path,
                    help="folder with th/vo.prompter.md (default: next to "
                         "the director file)")
    args = ap.parse_args()
    try:
        lines = mode_parity(args.director, args.legacy)
    except (HandoffError, OSError, KeyError) as e:
        sys.exit(f"Can't compare: {e}")
    folder = args.prompters or args.director.parent
    for label, legacy in (("TH", args.th), ("VO", args.vo)):
        if legacy:
            gen = folder / f"{label.lower()}.prompter.md"
            if gen.exists():
                lines += [""] + prompter_diff(label, gen, legacy)
            else:
                lines += ["", f"{label}: no {gen.name} to compare"]
    print("\n".join(lines))
    print("\n(Information only: the legacy files are a reference, not a spec.)")


if __name__ == "__main__":
    main()
