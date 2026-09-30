#!/usr/bin/env python3
"""The shoot stage: a shoot pack before recording, shoot.json after.

Usage:
    python shoot.py pack  --director D.director.json [-o shoot-pack.md]
    python shoot.py scan  FOLDER --director D.director.json [-o shoot.draft.json]
    python shoot.py write DRAFT --director D.director.json [-o FOLDER/shoot.json]

pack   what to record, from the director and paper edit: which prompter to
       read for the talking-head and voiceover sessions, the retake habit,
       every screen recording and b-roll cue (ID, brief, the words it plays
       under, roughly how long it's on screen, a file name to save it as),
       and the blur list.

scan   looks through the footage folder and proposes a shoot.json body:
         aroll.* / broll.* / vo.* (case, '-', '_' and spaces ignored:
           A-Roll.MP4 is the A-roll; 'voiceover' counts as vo), plus the
           B-roll sync offsets if the cut has made .claude-cut/offsets.json;
         a screen recording or b-roll file whose name contains its cue ID
           (b05.sr1.mov, B05-SR1 wp admin.mp4, b05_sr1_take2.mov).
       Every sr/br cue in the plan gets an entry: the file, or null (not
       captured). Anything it can't place is listed under "questions"
       (in the draft and on screen): ask the user, fix the draft, then
       `write`.

write  checks the draft (schema; every file exists; aroll, and vo if there
       are voiceover segments; asset IDs are sr/br cues of this director)
       and writes shoot.json with a header naming the director it was
       made for. Paths are stored relative to shoot.json where they can be.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from handoff import HandoffError, header, input_ref, load
from model import (WPM, all_cues, covered_words, cue_anchor_sentence, load_director,
                   segment_ranges, segment_words, sentence_owner)

VIDEO = {".mp4", ".mov", ".mxf", ".m4v", ".mkv", ".avi", ".mts"}
AUDIO = {".wav", ".aif", ".aiff", ".m4a", ".mp3", ".flac", ".caf"}
SKIP_DIRS = {".claude-cut", "graphics", "renders", "review", "node_modules"}
CUE_IN_NAME = re.compile(r"(?<![a-z0-9])(b\d{2}[a-z]?)[\s._-]?(sr|br)[\s._-]?(\d+)(?!\d)",
                         re.I)
ROLES = {"aroll": ("aroll",), "broll": ("broll",), "vo": ("vo", "voiceover")}


class ShootError(Exception):
    pass


# --- what the plan asks for ----------------------------------------------------------

def captures(director_path: Path) -> dict:
    """Segments, sr/br cues (with the words they play under and an estimate
    of their length), the prompters and the blur list."""
    d, pe, pe_path, script = load_director(director_path, check_hash=False)
    segments = segment_ranges(d, pe)
    owner = sentence_owner(segments)
    beats = {b["id"]: b for b in pe["beats"]}
    cues = all_cues(pe, d)
    by_id = {c["id"]: c for c in cues}
    segs = {s["id"]: s for s in segments}
    out = []
    for c in cues:
        if c["kind"] not in ("sr", "br"):
            continue
        sid = owner.get(cue_anchor_sentence(c, beats, by_id))
        seg = segs.get(sid)
        under, seconds = "", None
        if seg:
            words = segment_words(script, seg)
            dur = c.get("duration", "segment" if c["placement"] == "bed" else None)
            span = covered_words(words, c.get("anchor"), dur)
            if isinstance(dur, dict) and "seconds" in dur:
                seconds = dur["seconds"]
            elif span:
                seconds = (span[1] - span[0]) * 60 / WPM
            raw = script.text(*seg["sentences"]).split()
            a = span[0] if span else 0
            under = " ".join(raw[a:a + 14]) + (" …" if len(raw) > a + 14 else "")
        out.append({"id": c["id"], "kind": c["kind"], "placement": c["placement"],
                    "segment": sid, "mode": seg["mode"] if seg else None,
                    "brief": c["brief"], "under": under, "seconds": seconds})
    order = {s["id"]: i for i, s in enumerate(segments)}
    out.sort(key=lambda c: (order.get(c["segment"], 10**6), c["id"]))
    here = Path(director_path).parent
    prompters = {}
    mp = here / "prompter.map.json"
    if mp.exists():
        for mode, p in load(mp)["prompters"].items():
            prompters[mode] = p["path"]
    words = {m: sum(len(script.text(*s["sentences"]).split())
                    for s in segments if s["mode"] == m) for m in ("th", "vo")}
    return {"title": pe.get("title", ""), "segments": segments, "captures": out,
            "prompters": prompters, "words": words,
            "blur": pe.get("notes", {}).get("blur_list", []),
            "sr_br_ids": {c["id"] for c in out}}


def mmss(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


def suggested_name(c: dict) -> str:
    return f"{c['id']}.{'mov' if c['kind'] == 'sr' else 'mp4'}"


# --- pack ------------------------------------------------------------------------

def pack(director_path: Path) -> str:
    info = captures(director_path)
    th = [s for s in info["segments"] if s["mode"] == "th"]
    vo = [s for s in info["segments"] if s["mode"] == "vo"]
    out = [f"# Shoot pack: {info['title']}", "",
           f"_Made from `{Path(director_path).name}`. Tick things off as you go._", ""]

    n = 1
    if th:
        out += [f"## {n}. Talking head", "",
                f"Read **`{info['prompters'].get('th', 'th.prompter.md')}`** top to "
                f"bottom: {len(th)} segments, about {info['words']['th']} words "
                f"(roughly {mmss(info['words']['th'] * 60 / WPM)} spoken).", "",
                "- [ ] Save the camera file as **`aroll`** (e.g. `aroll.MP4`), and a "
                "second angle, if you shoot one, as **`broll`**.", ""]
        n += 1
    if vo:
        out += [f"## {n}. Voiceover", "",
                f"Read **`{info['prompters'].get('vo', 'vo.prompter.md')}`**: "
                f"{len(vo)} segments, about {info['words']['vo']} words (roughly "
                f"{mmss(info['words']['vo'] * 60 / WPM)}).", "",
                "- [ ] Save it as **`vo.wav`**.", ""]
        n += 1
    out += [f"## {n}. The retake habit", "",
            "- Fluffed a line? Say **\"retake cut\"** clearly, pause, then go again "
            "from the **start of the sentence** you fluffed. The last take is the "
            "keeper.",
            "- Don't go back further than that sentence: the lines before it are "
            "kept.",
            "- Leave a breath between segments (the `## b05` headings on the "
            "prompter).",
            "- Ad-libs are kept (nothing off-script is thrown away), so trim them "
            "in Resolve, or don't say them.", ""]
    n += 1
    caps = info["captures"]
    if caps:
        total = sum(c["seconds"] or 0 for c in caps)
        out += [f"## {n}. Screen recordings and b-roll ({len(caps)})", "",
                f"About {mmss(total)} on screen in all. Record each with a few "
                f"seconds spare at both ends, and **save it with its cue ID in the "
                f"name** (the suggested name is fine; `b05.sr1 users page.mov` works "
                f"too).", ""]
        for c in caps:
            length = f"~{c['seconds']:.0f}s on screen" if c["seconds"] else "length: see brief"
            where = f"{c['segment']}, {c['mode'].upper()}" if c["segment"] else "?"
            out += [f"- [ ] **`{c['id']}`** ({'screen recording' if c['kind'] == 'sr' else 'b-roll'}, "
                    f"{length}, {where}) → `{suggested_name(c)}`",
                    f"  - {c['brief']}"]
            if c["under"]:
                out.append(f"  - Plays under: \"{c['under']}\"")
        out.append("")
        n += 1
    if info["blur"]:
        out += [f"## {n}. Keep off screen, or blur later", ""] + \
            [f"- {b}" for b in info["blur"]] + [""]
        n += 1
    out += [f"## {n}. After recording", "",
            "Put everything in the footage folder, then run the shoot stage again "
            "to register the files (it matches names and asks about anything it "
            "can't place).", ""]
    return "\n".join(out)


# --- scan ------------------------------------------------------------------------

def key(p: Path) -> str:
    return re.sub(r"[\s_-]", "", p.stem.lower())


def media(folder: Path) -> list[Path]:
    out = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
        for f in files:
            p = Path(root) / f
            if f.startswith(".") or p.suffix.lower() not in VIDEO | AUDIO:
                continue
            if p.stem.lower().endswith(("_mono", "_vo_cut", "_cut")):
                continue                 # made by the pipeline
            out.append(p)
    return sorted(out)


def rel_to(p: Path, base: Path) -> str:
    try:
        return os.path.relpath(p.resolve(), base.resolve())
    except ValueError:
        return str(p.resolve())


def scan(folder: Path, director_path: Path) -> dict:
    info = captures(director_path)
    has_vo = any(s["mode"] == "vo" for s in info["segments"])
    files = media(folder)
    questions, found = [], {r: [] for r in ROLES}
    by_cue: dict[str, list[Path]] = {}
    leftovers = []
    for p in files:
        k = key(p)
        role = next((r for r, names in ROLES.items() if k in names), None)
        m = CUE_IN_NAME.search(p.stem)
        if role:
            found[role].append(p)
        elif m:
            cid = f"{m.group(1).lower()}.{m.group(2).lower()}{int(m.group(3))}"
            if cid in info["sr_br_ids"]:
                by_cue.setdefault(cid, []).append(p)
            else:
                questions.append(f"{rel_to(p, folder)} names {cid}, which isn't a "
                                 f"screen recording or b-roll cue in the plan")
        else:
            leftovers.append(p)
    body: dict = {"th": {}, "assets": {}}
    for role, want in (("aroll", True), ("broll", False), ("vo", has_vo)):
        got = found[role]
        if len(got) == 1:
            if role == "vo":
                body["vo"] = {"audio": rel_to(got[0], folder)}
            else:
                body["th"][role] = rel_to(got[0], folder)
        elif len(got) > 1:
            questions.append(f"more than one {role}: " +
                             ", ".join(rel_to(p, folder) for p in got))
        elif want:
            questions.append(f"no {role} file found (name it {role}.* or say which "
                             f"file it is)")
    offsets = folder / ".claude-cut" / "offsets.json"
    if body["th"].get("broll") and offsets.exists():    # the cut's sync step ran
        body["th"]["offsets"] = rel_to(offsets, folder)
    for c in info["captures"]:
        got = by_cue.get(c["id"], [])
        if len(got) == 1:
            body["assets"][c["id"]] = rel_to(got[0], folder)
        else:
            body["assets"][c["id"]] = None
            if len(got) > 1:
                questions.append(f"more than one file for {c['id']}: " +
                                 ", ".join(rel_to(p, folder) for p in got))
    for p in leftovers:
        questions.append(f"{rel_to(p, folder)}: not matched to anything (the "
                         f"A-roll, B-roll or voiceover under another name, or a "
                         f"capture without its cue ID?)")
    return {"body": body, "questions": questions, "captures": info["captures"]}


# --- write -----------------------------------------------------------------------

def check_draft(body: dict, base: Path, director_path: Path) -> list[str]:
    info = captures(director_path)
    has_vo = any(s["mode"] == "vo" for s in info["segments"])
    errs = []

    def exists(label, p):
        if p is None:
            return
        q = Path(p) if Path(p).is_absolute() else base / p
        if not q.exists():
            errs.append(f"{label}: {p} doesn't exist")

    th = body.get("th") or {}
    if not th.get("aroll"):
        errs.append("th.aroll is required (the talking-head recording)")
    exists("th.aroll", th.get("aroll"))
    exists("th.broll", th.get("broll"))
    exists("th.offsets", th.get("offsets"))
    if has_vo and not (body.get("vo") or {}).get("audio"):
        errs.append("the plan has voiceover segments: vo.audio is required")
    exists("vo.audio", (body.get("vo") or {}).get("audio"))
    for cid, p in (body.get("assets") or {}).items():
        if cid not in info["sr_br_ids"]:
            errs.append(f"assets.{cid}: not a screen recording or b-roll cue of "
                        f"this director")
        exists(f"assets.{cid}", p)
    return errs


def write(draft: Path, director_path: Path, out: Path) -> dict:
    from validate import validate_file
    body = json.loads(draft.read_text())
    body = {k: v for k, v in body.items() if k in ("th", "vo", "assets", "workdir")}
    info = captures(director_path)
    assets = body.setdefault("assets", {})
    for cid in info["sr_br_ids"]:
        assets.setdefault(cid, None)           # not captured: say so explicitly
    errs = check_draft(body, out.parent, director_path)
    if errs:
        raise ShootError("the draft isn't ready:\n  - " + "\n  - ".join(errs))
    doc = header("shoot", {"director": input_ref(director_path, out.parent)})
    doc.update(body)
    doc["assets"] = dict(sorted(assets.items()))
    pending = out.with_name(out.stem + ".pending.json")
    pending.write_text(json.dumps(doc, indent=1) + "\n")
    try:
        _, schema_errs = validate_file(pending)
    finally:
        text = pending.read_text()
        pending.unlink()
    if schema_errs:
        raise ShootError("shoot.json doesn't validate:\n  - " + "\n  - ".join(schema_errs))
    out.write_text(text)
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--director", type=Path, required=True)
    p.add_argument("-o", "--output", type=Path)
    s = sub.add_parser("scan")
    s.add_argument("folder", type=Path)
    s.add_argument("--director", type=Path, required=True)
    s.add_argument("-o", "--output", type=Path)
    w = sub.add_parser("write")
    w.add_argument("draft", type=Path)
    w.add_argument("--director", type=Path, required=True)
    w.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    try:
        if args.cmd == "pack":
            text = pack(args.director)
            if args.output:
                args.output.write_text(text)
                print(f"Wrote {args.output}")
            else:
                print(text)
        elif args.cmd == "scan":
            r = scan(args.folder, args.director)
            out = args.output or args.folder / "shoot.draft.json"
            out.write_text(json.dumps({**r["body"], "questions": r["questions"]},
                                      indent=1) + "\n")
            a = r["body"]["assets"]
            got = sum(1 for v in a.values() if v)
            th = r["body"]["th"]
            print(f"A-roll: {th.get('aroll', '-')}   B-roll: {th.get('broll', '-')}   "
                  f"VO: {(r['body'].get('vo') or {}).get('audio', '-')}")
            print(f"Captures: {got} of {len(a)} found")
            for cid, v in a.items():
                if not v:
                    print(f"  not captured: {cid}")
            for q in r["questions"]:
                print(f"  question: {q}")
            print(f"Draft -> {out}" + ("" if not r["questions"] else
                                       " (answer the questions, then write)"))
        else:
            out = args.output or args.draft.parent / "shoot.json"
            doc = write(args.draft, args.director, out)
            a = doc["assets"]
            print(f"Wrote {out}: {sum(1 for v in a.values() if v)} of {len(a)} "
                  f"captures, {sum(1 for v in a.values() if not v)} not captured")
    except (ShootError, HandoffError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
