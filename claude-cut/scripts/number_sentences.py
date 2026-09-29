#!/usr/bin/env python3
"""Split a prompter script into numbered sentences: the ground truth every
later stage refers to by number.

Usage:
    python number_sentences.py script.md [-o script.script.json]

Script conventions:
  - Spoken text lives under a '## Script' heading, up to the first '---'
    rule (or end of file). Headings inside it ('##' to '######') start
    sections; anything before the first section heading is preamble.
  - A line that is entirely [bracketed] is an on-screen cue, not speech.
  - Fenced code blocks are cues too (kind 'code').
  - Sentences split per paragraph on the same rule match_takes.py uses
    ((?<=[.!?])\\s+), but short fragments like "Fine." are KEPT here so
    every spoken word has a number.

Output: see schemas/script.schema.json.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from handoff import header, input_ref

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
CUE_LINE = re.compile(r"^\s*\[(.*)\]\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")


def number_script(text: str, start_heading: str = "Script") -> dict:
    lines = text.splitlines()
    title = next((HEADING.match(l).group(2) for l in lines
                  if HEADING.match(l) and HEADING.match(l).group(1) == "#"), "")

    start = None
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if m and len(m.group(1)) == 2 and \
                m.group(2).strip().lower() == start_heading.lower():
            start = i + 1
            break
    if start is None:
        raise ValueError(f"no '## {start_heading}' heading found")

    sections, sentences, cues, preamble = [], [], [], []
    section = None
    para_no = 0
    para: list[str] = []
    in_code, code_buf = False, []

    def last_n() -> int:
        return sentences[-1]["n"] if sentences else 0

    def flush_para() -> None:
        nonlocal para, para_no
        if not para:
            return
        joined = " ".join(l.strip() for l in para).strip()
        para = []
        if not joined:
            return
        if section is None:
            preamble.append(joined)
            return
        para_no += 1
        for part in SENTENCE_SPLIT.split(joined):
            part = part.strip()
            if part:
                sentences.append({"n": last_n() + 1, "section": section["id"],
                                  "para": para_no, "text": part})

    def add_cue(kind: str, body: str) -> None:
        cues.append({"after": last_n(),
                     "section": section["id"] if section else None,
                     "kind": kind, "text": body})

    for line in lines[start:]:
        if in_code:
            if FENCE.match(line):
                in_code = False
                add_cue("code", "\n".join(code_buf))
                code_buf = []
            else:
                code_buf.append(line)
            continue
        if FENCE.match(line):
            flush_para()
            in_code = True
            continue
        if RULE.match(line):
            break
        m = HEADING.match(line)
        if m:
            flush_para()
            section = {"id": f"sec{len(sections) + 1:02d}",
                       "title": m.group(2).strip(), "level": len(m.group(1))}
            sections.append(section)
            continue
        if not line.strip():
            flush_para()
            continue
        c = CUE_LINE.match(line)
        if c:
            flush_para()
            add_cue("bracket", c.group(1).strip())
            continue
        para.append(line)
    flush_para()
    if in_code:
        raise ValueError("unterminated code fence in script body")
    if not sentences:
        raise ValueError("no spoken sentences found under the script heading")

    for s in sections:
        ns = [x["n"] for x in sentences if x["section"] == s["id"]]
        s["first"], s["last"] = (ns[0], ns[-1]) if ns else (None, None)

    return {"title": title, "preamble": preamble, "sections": sections,
            "sentences": sentences, "script_cues": cues}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", type=Path)
    ap.add_argument("-o", "--output", type=Path,
                    help="default: <script stem>.script.json next to the script")
    ap.add_argument("--start-heading", default="Script")
    args = ap.parse_args()

    if not args.script.exists():
        sys.exit(f"Script not found: {args.script}")
    out = args.output or args.script.with_name(args.script.stem + ".script.json")
    try:
        body = number_script(args.script.read_text(), args.start_heading)
    except ValueError as e:
        sys.exit(f"{args.script.name}: {e}")

    doc = header("script", {"script": input_ref(args.script, out.parent)})
    doc.update(body)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(body['sentences'])} sentences in {len(body['sections'])} "
          f"sections, {len(body['script_cues'])} cues -> {out}")


if __name__ == "__main__":
    main()
