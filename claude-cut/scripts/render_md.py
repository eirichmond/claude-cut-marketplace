#!/usr/bin/env python3
"""Render a paper-edit or director JSON as markdown for humans.

Usage:
    python render_md.py FILE.json [-o FILE.md]

The JSON is authoritative; the markdown is regenerated from it and should
never be edited by hand. Spoken text is filled in from the numbered script,
so what you read is exactly what will be on the prompter. The file must
validate first.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


from model import (Script, all_cues, cue_anchor_sentence, load_director,
                   load_paper_edit, segment_ranges, sentence_owner)
from validate import validate_file

WPM = 150


def words(text: str) -> int:
    return len(text.split())


def mmss(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def describe_cue(c: dict) -> str:
    bits = [c["kind"].upper()]
    if c["placement"] != "overlay":
        bits.append(c["placement"].replace("_", " "))
    dur = c.get("duration")
    if isinstance(dur, dict):
        bits.append(f"{dur['seconds']}s" if "seconds" in dur
                    else f"to \"{dur['to_phrase']}\"")
    elif dur:
        bits.append(dur.replace("_", " "))
    anchor = c.get("anchor") or {}
    at = ""
    if "phrase" in anchor:
        at = f" at \"{anchor['phrase']}\""
    elif "cue" in anchor:
        at = f" with {anchor['cue']}"
    return f"`{c['id']}` {', '.join(bits)}{at}: {c['brief']}"


def beat_seconds(beat: dict, script: Script) -> float:
    if "est_seconds" in beat:
        return beat["est_seconds"]
    return words(script.text(*beat["sentences"])) * 60 / WPM


def render_paper_edit(pe: dict, script: Script, src: Path) -> str:
    sec_titles = {s["id"]: s["title"] for s in script.doc["sections"]}
    sec_meta = {s["id"]: s for s in pe.get("sections", [])}
    total = sum(beat_seconds(b, script) for b in pe["beats"]) + sum(
        c["duration"]["seconds"] for c in all_cues(pe)
        if c["placement"].startswith("insert"))
    out = [f"# Paper edit: {pe['title']}", "",
           f"_Rendered from `{src.name}`. Don't edit this file; edit the JSON "
           f"and re-render._", "",
           f"**Beats:** {len(pe['beats'])} · **Sentences:** {script.count} · "
           f"**Estimated runtime:** {mmss(total)} (about {WPM} words a minute)",
           ""]
    notes = pe.get("notes", {})
    if notes.get("before_timeline"):
        out += ["## Before anyone opens the timeline", "",
                notes["before_timeline"], ""]
    if notes.get("tone"):
        out += ["## Tone and style", "", notes["tone"], ""]
    if notes.get("blur_list"):
        out += ["**Blur list:** " + "; ".join(notes["blur_list"]), ""]
    for k, v in notes.items():
        if k not in ("before_timeline", "tone", "blur_list"):
            out += [f"## {k.replace('_', ' ').capitalize()}", "", v, ""]

    out += ["## Beat-by-beat", ""]
    t, section = 0.0, None
    for beat in pe["beats"]:
        if beat["section"] != section:
            section = beat["section"]
            meta = sec_meta.get(section, {})
            out += ["", f"### {sec_titles.get(section, section)}", ""]
            if meta.get("purpose"):
                out += [meta["purpose"], ""]
            out += ["| ID | Est. TC | Spoken | On screen | Transition | Notes |",
                    "|---|---|---|---|---|---|"]
        cues = beat.get("cues", [])
        t += sum(c["duration"]["seconds"] for c in cues
                 if c["placement"] == "insert_before")
        spoken = "<br><br>".join(cell(p) for p in
                                 script.paragraphs(*beat["sentences"]))
        a, b = beat["sentences"]
        screen = [cell(beat["visual"])] + [cell(describe_cue(c)) for c in cues]
        notes_cell = []
        if beat.get("chapter"):
            notes_cell.append(f"**Chapter: {cell(beat['chapter'])}**")
        if beat.get("key_point"):
            notes_cell.append("**Key point.**")
        for k in ("pace", "notes"):
            if beat.get(k):
                notes_cell.append(cell(beat[k]))
        out.append(f"| **{beat['id']}**<br>s{a}–{b} | {mmss(t)} | {spoken} | "
                   f"{'<br>'.join(screen)} | "
                   f"{cell(beat.get('transition_in', ''))} | "
                   f"{' '.join(notes_cell)} |")
        t += beat_seconds(beat, script) + sum(
            c["duration"]["seconds"] for c in cues
            if c["placement"] == "insert_after")

    assets = pe.get("assets") or {}
    if assets:
        out += ["", "## Asset list", ""]
        for kind, items in assets.items():
            out += [f"**{kind.upper()}**", ""] + [f"- {i}" for i in items] + [""]
    return "\n".join(out).rstrip() + "\n"


def render_director(d: dict, pe: dict, script: Script, src: Path) -> str:
    segments = segment_ranges(d, pe)
    owner = sentence_owner(segments)
    beats = {b["id"]: b for b in pe["beats"]}
    cues = all_cues(pe, d)
    by_id = {c["id"]: c for c in cues}
    seg_cues: dict[str, list[dict]] = {s["id"]: [] for s in segments}
    for c in cues:
        sid = owner.get(cue_anchor_sentence(c, beats, by_id))
        if sid:
            seg_cues[sid].append(c)
    sec_titles = {s["id"]: s["title"] for s in script.doc["sections"]}
    judgement = {}
    for jc in d.get("judgement_calls", []):
        judgement.setdefault(jc["segment"], []).append(jc["note"])

    def text(seg):
        return script.text(*seg["sentences"])

    counts = {}
    for mode in ("th", "vo"):
        segs = [s for s in segments if s["mode"] == mode]
        w = sum(words(text(s)) for s in segs)
        counts[mode] = (len(segs), w, mmss(w * 60 / WPM))

    out = [f"# Director: {pe['title']}", "",
           f"_Rendered from `{src.name}`. Don't edit this file; edit the JSON "
           f"and re-render._", "",
           f"**{counts['th'][0]} talking head segments (about {counts['th'][1]} "
           f"words, roughly {counts['th'][2]} spoken) and {counts['vo'][0]} "
           f"voiceover segments (about {counts['vo'][1]} words, roughly "
           f"{counts['vo'][2]} spoken).**", ""]

    for num, mode, label in ((1, "th", "Talking head shot list"),
                             (2, "vo", "Voiceover shot list")):
        out += ["---", "", f"## {num}. {label}", ""]
        section = None
        for seg in segments:
            if seg["mode"] != mode:
                continue
            sec = beats[seg["beat"]]["section"]
            if sec != section:
                section = sec
                out += [f"### {sec_titles.get(sec, sec)}", ""]
            out += [f"**{seg['id']}**", ""]
            out += [f"> {p}" for p in script.paragraphs(*seg["sentences"])]
            out.append("")
            if seg.get("delivery"):
                out += [f"*Delivery:* {seg['delivery']}", ""]
            if seg.get("on_screen"):
                out += [f"*On screen:* {seg['on_screen']}", ""]
            for c in seg_cues[seg["id"]]:
                if c["placement"] == "bed":
                    moved = " *(reanchored, see below)*" \
                        if "_reanchor" in c else ""
                    out += [f"*Bed:* {describe_cue(c)}{moved}", ""]

    out += ["---", "", "## 3. Running order", "",
            "| # | Segment | Mode | Section | Words |", "|---|---|---|---|---|"]
    for i, seg in enumerate(segments, 1):
        sec = beats[seg["beat"]]["section"]
        out.append(f"| {i} | {seg['id']} | {seg['mode'].upper()} | "
                   f"{cell(sec_titles.get(sec, sec))} | {words(text(seg))} |")

    section_no = 4
    if judgement:
        out += ["", "---", "", f"## {section_no}. Judgement calls", ""]
        section_no += 1
        for sid, notes in judgement.items():
            for n in notes:
                out.append(f"- **{sid}.** {n}")

    moves = d.get("reanchor", [])
    if moves:
        out += ["", "---", "", f"## {section_no}. Reanchored beds", "",
                "Paper-edit bed cues the director moved within their beat. "
                "The ID and brief are unchanged.", "",
                "| Cue | Was | Now | Lands on | Reason |",
                "|---|---|---|---|---|"]
        for r in moves:
            lands = owner.get(r["to"]["sentence"], "?")
            out.append(f"| `{r['cue']}` | {describe_anchor(r['from'])} | "
                       f"{describe_anchor(r['to'])} | {lands} | "
                       f"{cell(r['reason'])} |")
    return "\n".join(out).rstrip() + "\n"


def describe_anchor(anchor: dict | None) -> str:
    if not anchor:
        return "start of beat"
    if "cue" in anchor:
        return f"with {anchor['cue']}"
    text = f"sentence {anchor['sentence']}"
    if "phrase" in anchor:
        text += f" at \"{cell(anchor['phrase'])}\""
    return text


def render(path: Path) -> str:
    kind, errs = validate_file(path)
    if errs:
        raise SystemExit(f"{path.name} does not validate; fix it before "
                         f"rendering:\n  - " + "\n  - ".join(errs))
    if kind == "paper-edit":
        pe, script = load_paper_edit(path)
        return render_paper_edit(pe, script, path)
    if kind == "director":
        d, pe, _, script = load_director(path)
        return render_director(d, pe, script, path)
    raise SystemExit(f"{path.name}: nothing to render for kind '{kind}'")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    out = args.output or args.file.with_suffix(".md")
    out.write_text(render(args.file))
    print(f"Rendered {out}")


if __name__ == "__main__":
    main()
