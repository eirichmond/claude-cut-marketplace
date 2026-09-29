#!/usr/bin/env python3
"""Stamp, validate and write a handoff file drafted by a skill.

Usage:
    python write_handoff.py KIND DRAFT.json --input ROLE=PATH [...] -o OUT.json [--render]

The skill writes only the body (no schema/created/inputs). This adds the
header with input hashes, validates the result, and only then writes OUT
(and OUT.md with --render). If validation fails, every problem is printed,
nothing is written, and the exit code is 1: fix the draft and run it again.

Examples:
    python write_handoff.py paper-edit draft.json \\
        --input script=video.script.json -o video.paper-edit.json --render
    python write_handoff.py director draft.json \\
        --input paper_edit=video.paper-edit.json -o video.director.json --render
"""
import argparse
import json
import sys
from pathlib import Path

from handoff import header, input_ref

HEADER_KEYS = ("schema", "created", "inputs")


def summary(doc: dict) -> str:
    from collections import Counter
    if "beats" in doc:
        cues = [c for b in doc["beats"] for c in b.get("cues", [])]
        kinds = Counter(c["kind"] for c in cues)
        chapters = sum(1 for b in doc["beats"] if b.get("chapter"))
        full = sum(1 for c in cues if c["placement"] == "bed"
                   and c.get("duration", "segment") == "segment")
        timed = sum(1 for c in cues if c["placement"] == "bed") - full
        cutaways = sum(1 for c in cues if c["placement"] == "overlay"
                       and (c["kind"] in ("sr", "br") or
                            (c["kind"] == "mg" and c.get("layer") == "full")))
        return (f"{len(doc['beats'])} beats, {chapters} chapters, {len(cues)} "
                f"cues ({', '.join(f'{k} {n}' for k, n in kinds.most_common())})\n"
                f"Pictures: {full} full-length beds, {timed} timed beds, "
                f"{cutaways} mid-beat cutaways")
    segs = doc.get("segments", [])
    modes = Counter(s["mode"] for s in segs)
    split = len({s["beat"] for s in segs if s["id"] != s["beat"]})
    return (f"{len(segs)} segments ({modes['th']} TH, {modes['vo']} VO), "
            f"{split} beats split, {len(doc.get('cues', []))} director beds, "
            f"{len(doc.get('reanchor', []))} reanchors")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["paper-edit", "director"])
    ap.add_argument("draft", type=Path)
    ap.add_argument("--input", action="append", default=[], metavar="ROLE=PATH",
                    required=True)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--render", action="store_true",
                    help="also write the markdown render next to OUT")
    args = ap.parse_args()

    try:
        body = json.loads(args.draft.read_text())
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"Can't read draft {args.draft}: {e}")
    if not isinstance(body, dict):
        sys.exit("The draft must be a JSON object")

    out = args.output.resolve()
    inputs = {}
    for spec in args.input:
        role, _, path = spec.partition("=")
        if not path or not Path(path).exists():
            sys.exit(f"--input {spec}: expected ROLE=PATH to an existing file")
        inputs[role] = input_ref(Path(path), out.parent)

    doc = header(args.kind, inputs)
    doc.update({k: v for k, v in body.items() if k not in HEADER_KEYS})

    # Validate a pending copy beside OUT so relative input paths resolve the
    # same way, and never clobber a good file with a bad one.
    pending = out.with_name(out.stem + ".pending.json")
    pending.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    try:
        from validate import validate_file
        _, errs = validate_file(pending)
    finally:
        text = pending.read_text()
        pending.unlink()
    if errs:
        print(f"Not written: the draft has {len(errs)} problem(s). Fix them in "
              f"{args.draft} and run this again.")
        for e in errs:
            print(f"  - {e}")
        sys.exit(1)

    out.write_text(text)
    print(f"Wrote {out}")
    print(summary(doc))
    from validate import lint_file
    notes = lint_file(out)
    if notes:
        print(f"{len(notes)} note(s) worth a look (not errors):")
        for n in notes:
            print(f"  - {n}")
    if args.render:
        from render_md import render
        md = out.with_suffix(".md")
        md.write_text(render(out))
        print(f"Rendered {md}")


if __name__ == "__main__":
    main()
