#!/usr/bin/env python3
"""Write the TH and VO prompter scripts and the sentence-to-segment map.

Usage:
    python build_prompters.py <video>.director.json [--out-dir DIR]

Writes, next to the director file by default:
  th.prompter.md     talking-head segments, in running order, each under a
  vo.prompter.md     '## <segment id>' heading (headings are never spoken)
  prompter.map.json  for each prompter: s1..sN (the sentence numbers
                     edit-takes will report for it) -> segment and script
                     sentence(s), plus 'untimed' script sentences too short
                     for take matching.

The prompters are generated from the numbered script, so they are
byte-stable and verbatim. The map is computed with match_takes'
own split_sentences, so its s numbers are, by construction, the ones the
cut reports. Fails (listing every problem) if a segment would have no
matchable sentence. A cut sentence that runs across two segments (a
segment ending in ?" or !") is recorded with both segments, and conform
splits it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from handoff import HandoffError, header, input_ref, sha256
from match_takes import norm, split_sentences
from model import load_director, segment_ranges
from validate import validate_file

# split_sentences removes these characters before splitting (match_takes.py
# line 44); script sentences go through the same step so tokens line up.
STRIPPED = re.compile(r"[*_`>\[\]()]")


def tokens(text: str) -> list[str]:
    return norm(STRIPPED.sub("", text)).split()


def prompter_text(mode: str, title: str, source: str, segments: list[dict],
                  script) -> str:
    label = "Talking head" if mode == "th" else "Voiceover"
    # Every non-spoken line must be a heading: split_sentences treats any
    # other line as speech.
    out = [f"# {label} prompter: {title}",
           f"# Generated from {source}. Read in order; the ## IDs are not spoken.",
           ""]
    for seg in segments:
        out += [f"## {seg['id']}", ""]
        # Director notes ride along as headings, which take matching ignores.
        for key, label in (("on_screen", "On screen"), ("delivery", "Delivery")):
            if seg.get(key):
                out += [f"### {label}: {' '.join(seg[key].split())}", ""]
        for para in script.paragraphs(*seg["sentences"]):
            out += [para, ""]
    return "\n".join(out).rstrip() + "\n"


def build_map(text: str, segments: list[dict], script) -> tuple[dict, list]:
    """Map split_sentences' s numbers back to segments and script sentences."""
    errs = []
    cut_sents = split_sentences(text)

    # Token stream of the script sentences in prompter order, each token
    # tagged with (segment, n).
    stream = []
    for seg in segments:
        a, b = seg["sentences"]
        for n in range(a, b + 1):
            for tok in tokens(script.by_n[n]["text"]):
                stream.append((tok, seg["id"], n))

    pos = 0
    entries, used_n = [], set()
    for s, sent in enumerate(cut_sents, 1):
        toks = norm(sent).split()
        owners = []
        for tok in toks:
            # skip script tokens split_sentences dropped (short fragments)
            while pos < len(stream) and stream[pos][0] != tok:
                pos += 1
            if pos == len(stream):
                errs.append(f"internal: couldn't place cut sentence s{s} "
                            f"(\"{sent[:60]}\") in the prompter")
                return {}, errs
            owners.append(stream[pos][1:])
            pos += 1
        segs = list(dict.fromkeys(o[0] for o in owners))
        ns = sorted({o[1] for o in owners})
        used_n.update(ns)
        # A script sentence ending in ?" or !" (quote after the mark) isn't
        # a boundary to split_sentences, so one cut sentence can run across
        # two segments. That's recorded, not refused: conform splits its
        # words at the pause between the script sentences, and warns.
        entries.append({"s": s, "n": ns[0] if len(ns) == 1 else ns,
                        "segment": segs[0] if len(segs) == 1 else segs})

    timed_segments = {g for e in entries
                      for g in ([e["segment"]] if isinstance(e["segment"], str)
                                else e["segment"])}
    untimed = []
    for seg in segments:
        a, b = seg["sentences"]
        if seg["id"] not in timed_segments:
            errs.append(f"{seg['id']}: no sentence long enough for take "
                        f"matching (3+ words); merge it with a neighbour")
        for n in range(a, b + 1):
            if n not in used_n:
                untimed.append({"n": n, "segment": seg["id"],
                                "text": script.by_n[n]["text"]})
    return {"sentences": entries, "untimed": untimed}, errs


def check_prompters(d: dict, pe: dict, script) -> list[str]:
    """The prompter problems a director can fix, for director validation."""
    segments = segment_ranges(d, pe)
    problems = []
    for mode in ("th", "vo"):
        segs = [s for s in segments if s["mode"] == mode]
        if segs:
            _, errs = build_map(prompter_text(mode, "", "", segs, script),
                                segs, script)
            problems += errs
    return problems


def build(director_path: Path, out_dir: Path) -> list[str]:
    kind, errs = validate_file(director_path)
    if errs:
        return [f"{director_path.name} doesn't validate:"] + errs
    d, pe, _, script = load_director(director_path)
    segments = segment_ranges(d, pe)

    problems, texts, maps = [], {}, {}
    for mode in ("th", "vo"):
        segs = [s for s in segments if s["mode"] == mode]
        if not segs:
            continue
        text = prompter_text(mode, pe["title"], director_path.name, segs,
                             script)
        m, errs = build_map(text, segs, script)
        problems += [f"[{mode}] {e}" for e in errs]
        texts[mode], maps[mode] = text, m
    if problems:
        return problems

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = header("prompter-map",
                 {"director": input_ref(director_path, out_dir)})
    doc["prompters"] = {}
    for mode, text in texts.items():
        p = out_dir / f"{mode}.prompter.md"
        p.write_text(text)
        doc["prompters"][mode] = {"path": p.name, "sha256": sha256(p),
                                  **maps[mode]}
    (out_dir / "prompter.map.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    for mode, m in doc["prompters"].items():
        straddles = [e for e in m["sentences"] if isinstance(e["segment"], list)]
        segs = {g for e in m["sentences"]
                for g in (e["segment"] if isinstance(e["segment"], list)
                          else [e["segment"]])}
        print(f"{mode}.prompter.md: {len(segs)} segments, "
              f"{len(m['sentences'])} matchable sentences, "
              f"{len(m['untimed'])} untimed fragments")
        for e in straddles:
            print(f"  note: cut sentence s{e['s']} runs across "
                  f"{' and '.join(e['segment'])} (a quote closes after the "
                  f"? or !); conform will split it at the pause")
    print(f"Wrote {out_dir / 'prompter.map.json'}")
    return []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("director", type=Path)
    ap.add_argument("--out-dir", type=Path)
    args = ap.parse_args()
    try:
        problems = build(args.director,
                         args.out_dir or args.director.parent)
    except HandoffError as e:
        problems = [str(e)]
    if problems:
        print("Prompters not written:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)


if __name__ == "__main__":
    main()
