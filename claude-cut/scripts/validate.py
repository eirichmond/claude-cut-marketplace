#!/usr/bin/env python3
"""Validate claude-cut handoff files: structure (JSON Schema) and meaning.

Usage:
    python validate.py FILE [FILE ...]

The kind is read from each file's "schema" field. Upstream files named in
the header are loaded and hash-checked, so a stale input is an error. Every
problem found is listed; the exit code is 1 if there were any.

Legacy markdown paper edits and director files (no segment IDs) are rejected
with a message saying which stage to re-run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from handoff import (CUE_RE, SCHEMA_DIR, HandoffError, load, phrase_in,
                     resolve_input, schema_kind)
from model import (WPM, Script, all_cues, anchor_index, covered_words,
                   cue_anchor_sentence, load_director, load_paper_edit,
                   segment_parts, segment_ranges, segment_words,
                   sentence_owner)

BED_KINDS = {"sr", "br", "mg"}
INSERT_KINDS = {"mg", "chapter", "sr", "br"}
LAYERED_KINDS = {"mg", "lt", "chapter", "callout"}


# --- structure ------------------------------------------------------------

def _schema_errors(doc: dict, kind: str) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError:
        sys.exit("jsonschema is not installed. Run: pip install jsonschema")
    schema_path = SCHEMA_DIR / f"{kind}.schema.json"
    if not schema_path.exists():
        return [f"no schema for kind '{kind}'"]
    resources = []
    for p in SCHEMA_DIR.glob("*.schema.json"):
        s = json.loads(p.read_text())
        resources.append((s["$id"], Resource.from_contents(s)))
    registry = Registry().with_resources(resources)
    validator = Draft202012Validator(json.loads(schema_path.read_text()),
                                     registry=registry)
    out = []
    for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in e.path) or "(top level)"
        out.append(f"{where}: {e.message}")
    return out


# --- meaning --------------------------------------------------------------

def check_script(doc: dict) -> list[str]:
    errs = []
    ns = [s["n"] for s in doc["sentences"]]
    if ns != list(range(1, len(ns) + 1)):
        errs.append("sentences are not numbered 1..N in order")
    sec_ids = {s["id"] for s in doc["sections"]}
    for s in doc["sentences"]:
        if s["section"] not in sec_ids:
            errs.append(f"sentence {s['n']}: unknown section {s['section']}")
    return errs


GRAPHIC_KINDS = {"mg", "lt", "chapter", "callout"}


def check_graphics_spec(path: Path, doc: dict) -> list[str]:
    """Every graphic and sfx cue of the plan covered exactly once, template
    vars valid, custom compositions present and on-identity, SFX in the
    index."""
    import identity
    import templates
    errs: list[str] = []
    plan_path = resolve_input(path, doc, "plan")
    frame_path = resolve_input(path, doc, "frame")
    k, plan_errs = validate_file(plan_path)
    if plan_errs:
        return [f"[{plan_path.name}] {e}" for e in plan_errs]
    plan = load(plan_path)
    cues = {c["id"]: c for c in plan["cues"]}
    wanted = {cid for cid, c in cues.items()
              if c["kind"] in GRAPHIC_KINDS or c["kind"] == "sfx"}

    seen: dict[str, str] = {}
    def claim(cid, where):
        if cid in seen:
            errs.append(f"{cid}: listed in {seen[cid]} and {where}")
        seen[cid] = where
        if cid not in cues:
            errs.append(f"{cid}: not a cue in the plan (or outside its scope)")
            return None
        return cues[cid]

    base = Path(path).parent
    try:
        tok = identity.tokens(frame_path, base / "fonts") \
            if (base / "fonts").exists() else identity.tokens(frame_path)
    except ValueError as e:
        errs.append(str(e))
        tok = None
    for g in doc["graphics"]:
        c = claim(g["cue"], "graphics")
        if c and c["kind"] not in GRAPHIC_KINDS:
            errs.append(f"{g['cue']}: a {c['kind']} cue isn't a graphic")
        if g["template"] == "custom":
            comp = base / g["composition"]
            if not comp.exists():
                errs.append(f"{g['cue']}: {g['composition']} doesn't exist")
            elif tok:
                errs += [f"{g['cue']}: {i}"
                         for i in identity.check(comp.read_text(), tok)]
        else:
            try:
                errs += [f"{g['cue']} ({g['template']}): {e}"
                         for e in templates.check_vars(g["template"], g["vars"])]
            except RuntimeError as e:
                errs.append(str(e))

    index = None
    if doc["sfx"]:
        if "sfx_index" not in doc["inputs"]:
            errs.append("sfx picks need the sfx index in inputs (sfx_index)")
        else:
            index = load(resolve_input(path, doc, "sfx_index"))
    have = {(f["library"], f["path"]) for f in index["files"]} if index else set()
    for s in doc["sfx"]:
        c = claim(s["cue"], "sfx")
        if c and c["kind"] != "sfx":
            errs.append(f"{s['cue']}: a {c['kind']} cue can't have a sound effect")
        if index is not None:
            for f in [s["file"]] + s.get("alternatives", []):
                if (s["library"], f) not in have:
                    errs.append(f"{s['cue']}: '{f}' isn't in the '{s['library']}' "
                                f"library index")

    for s in doc["skip"]:
        c = claim(s["cue"], "skip")
        if c and c["id"] not in wanted:
            errs.append(f"{s['cue']}: {c['kind']} cues aren't listed; they stay "
                        f"markers anyway")

    for cid in sorted(wanted - set(seen)):
        errs.append(f"{cid} ({cues[cid]['kind']}): not in graphics, sfx or skip")
    return errs


def check_prompter_map(path: Path, doc: dict) -> list[str]:
    from handoff import sha256
    errs = []
    for mode, p in doc["prompters"].items():
        f = Path(path).parent / p["path"]
        if not f.exists():
            errs.append(f"{mode}: prompter {p['path']} not found")
        elif sha256(f) != p["sha256"]:
            errs.append(f"{mode}: {p['path']} has been edited since the map "
                        f"was built. Re-run build_prompters.py; never edit a "
                        f"prompter by hand.")
        ss = [e["s"] for e in p["sentences"]]
        if ss != list(range(1, len(ss) + 1)):
            errs.append(f"{mode}: sentences are not s1..sN in order")
    return errs


def check_sentences(doc: dict) -> list[str]:
    errs = []
    ss = [s["s"] for s in doc["sentences"]]
    if ss != list(range(1, len(ss) + 1)):
        errs.append("sentences are not numbered s1..sN in order")
    for s in doc["sentences"]:
        if "start" in s and s["start"] > s["end"]:
            errs.append(f"s{s['s']}: starts after it ends")
    return errs


def check_paper_edit(doc: dict, script: Script) -> list[str]:
    errs: list[str] = []
    n_total = script.count
    script_secs = {s["id"] for s in script.doc["sections"]}

    seen_secs = set()
    for s in doc.get("sections", []):
        if s["id"] not in script_secs:
            errs.append(f"sections: {s['id']} is not a section of the script")
        if s["id"] in seen_secs:
            errs.append(f"sections: {s['id']} listed twice")
        seen_secs.add(s["id"])

    # beats: sequential IDs, sentence ranges tile 1..N
    expect_next = 1
    beat_ids = set()
    for i, beat in enumerate(doc["beats"]):
        bid = beat["id"]
        if bid in beat_ids:
            errs.append(f"{bid}: duplicate beat ID")
        beat_ids.add(bid)
        if int(bid[1:]) != i + 1:
            errs.append(f"{bid}: beat IDs must run b01, b02... in order "
                        f"(expected b{i + 1:02d})")
        a, b = beat["sentences"]
        if a > b:
            errs.append(f"{bid}: sentences [{a}, {b}] run backwards")
        if a != expect_next:
            if a > expect_next:
                errs.append(f"{bid}: sentences {expect_next}-{a - 1} are not "
                            f"in any beat")
            else:
                errs.append(f"{bid}: starts at sentence {a}, overlapping the "
                            f"previous beat (expected {expect_next})")
        expect_next = max(expect_next, b + 1)
        if b > n_total:
            errs.append(f"{bid}: sentence {b} does not exist "
                        f"(script has {n_total})")
        secs = {script.by_n[n]["section"] for n in range(a, min(b, n_total) + 1)
                if n in script.by_n}
        if secs and secs != {beat["section"]}:
            errs.append(f"{bid}: section is {beat['section']} but its sentences "
                        f"are in {', '.join(sorted(secs))}")
    if expect_next <= n_total:
        errs.append(f"sentences {expect_next}-{n_total} are not in any beat")

    errs += check_cues(all_cues(doc), {b["id"]: b for b in doc["beats"]},
                       script, doc)
    return errs


def check_cues(cues: list[dict], beats: dict, script: Script,
               paper_edit: dict) -> list[str]:
    errs: list[str] = []
    by_id: dict = {}
    for c in cues:
        cid = c["id"]
        if cid in by_id:
            errs.append(f"{cid}: duplicate cue ID")
        by_id[cid] = c
    n_script_cues = len(script.doc.get("script_cues", []))

    for c in cues:
        cid, kind, place = c["id"], c["kind"], c["placement"]
        m = CUE_RE.match(cid)
        beat = beats.get(c["_beat"])
        if m and m.group(1) != c["_beat"] and c["_from"] == "paper-edit":
            errs.append(f"{cid}: cue is under beat {c['_beat']} but its ID "
                        f"names {m.group(1)}")
        if c["_from"] == "director" and not beat:
            errs.append(f"{cid}: no beat {c['_beat']} in the paper edit")
            continue
        if m and m.group(2) != kind:
            errs.append(f"{cid}: ID says '{m.group(2)}' but kind is '{kind}'")

        # placement rules
        if place == "bed" and kind not in BED_KINDS:
            errs.append(f"{cid}: a bed must be sr, br or mg (got {kind})")
        if place.startswith("insert"):
            if kind not in INSERT_KINDS:
                errs.append(f"{cid}: only mg, chapter, sr or br can be "
                            f"inserted (got {kind})")
            if not isinstance(c.get("duration"), dict) or \
                    "seconds" not in c["duration"]:
                errs.append(f"{cid}: {place} needs duration {{\"seconds\": n}}")
        if kind in LAYERED_KINDS and "layer" not in c:
            errs.append(f"{cid}: {kind} cues need a layer (full or overlay)")
        if kind not in LAYERED_KINDS and "layer" in c:
            errs.append(f"{cid}: layer only applies to mg, lt, chapter, callout")
        if place in ("bed", "insert_before", "insert_after") and \
                c.get("layer") == "overlay":
            errs.append(f"{cid}: a {place} is full frame; layer must be full")

        # anchors
        anchor = c.get("anchor") or {}
        if "sentence" in anchor and beat:
            n = anchor["sentence"]
            a, b = beat["sentences"]
            if not a <= n <= b:
                errs.append(f"{cid}: anchor sentence {n} is outside beat "
                            f"{beat['id']} ({a}-{b})")
            elif "phrase" in anchor and not phrase_in(anchor["phrase"],
                                                      script.by_n[n]["text"]):
                errs.append(f"{cid}: phrase \"{anchor['phrase']}\" is not in "
                            f"sentence {n}")
        if "cue" in anchor:
            if anchor["cue"] not in by_id:
                errs.append(f"{cid}: anchored to unknown cue {anchor['cue']}")
            elif cue_anchor_sentence(c, beats, by_id) is None:
                errs.append(f"{cid}: cue anchors form a loop")
        dur = c.get("duration")
        if isinstance(dur, dict) and "to_phrase" in dur and beat:
            if not phrase_in(dur["to_phrase"], script.text(*beat["sentences"])):
                errs.append(f"{cid}: to_phrase \"{dur['to_phrase']}\" is not "
                            f"in beat {beat['id']}")
        for sc in script_cue_list(c):
            if sc >= n_script_cues:
                errs.append(f"{cid}: script_cue {sc} does not exist")
    return errs


def script_cue_list(cue: dict) -> list[int]:
    sc = cue.get("script_cue")
    return [] if sc is None else ([sc] if isinstance(sc, int) else list(sc))


REINFORCING = {"callout", "lt", "zoom", "mg", "chapter"}


def lint_paper_edit(pe: dict, script: Script) -> list[str]:
    """Editorial notes that don't block the handoff but deserve a look."""
    notes = []
    used = {i for c in all_cues(pe) for i in script_cue_list(c)}
    for i, sc in enumerate(script.doc.get("script_cues", [])):
        if i in used or sc["kind"] != "bracket":
            continue
        if sc["text"].lower().startswith("talking head"):
            continue  # a mode note; it belongs in the beat's visual
        notes.append(f"script cue {i} (after sentence {sc['after']}) isn't "
                     f"used by any cue: [{sc['text'][:70]}]")
    for beat in pe["beats"]:
        if beat.get("key_point") and not any(
                c["kind"] in REINFORCING and
                (c["placement"] != "bed" or c["kind"] == "mg")
                for c in beat.get("cues", [])):
            notes.append(f"{beat['id']}: key point with no reinforcing cue "
                         f"(callout, lower third, zoom or graphic)")
    return notes


def check_director(doc: dict, pe: dict, script: Script) -> list[str]:
    errs: list[str] = []
    beats = {b["id"]: b for b in pe["beats"]}
    beat_order = [b["id"] for b in pe["beats"]]

    # group segments by beat, in order
    groups: list[tuple[str, list[dict]]] = []
    seg_ids = set()
    for seg in doc["segments"]:
        sid = seg["id"]
        base, letter = segment_parts(sid)
        if sid in seg_ids:
            errs.append(f"{sid}: duplicate segment ID")
        seg_ids.add(sid)
        if base != seg["beat"]:
            errs.append(f"{sid}: beat is {seg['beat']} but the ID traces to "
                        f"{base}")
        if seg["beat"] not in beats:
            errs.append(f"{sid}: no beat {seg['beat']} in the paper edit")
            continue
        if groups and groups[-1][0] == seg["beat"]:
            groups[-1][1].append(seg)
        else:
            groups.append((seg["beat"], [seg]))

    order = [g[0] for g in groups]
    if len(order) != len(set(order)):
        errs.append("segments of a beat must be consecutive; beats appear "
                    "more than once in the running order")
    known = [b for b in order if b in beats]
    if known != [b for b in beat_order if b in known]:
        errs.append("segments are not in paper-edit beat order")
    missing = [b for b in beat_order if b not in order]
    for b in missing:
        errs.append(f"{b}: beat has no segment in the director file")

    for bid, segs in groups:
        beat = beats[bid]
        ba, bb = beat["sentences"]
        letters = [segment_parts(s["id"])[1] for s in segs]
        if len(segs) == 1 and not letters[0]:
            rng = segs[0].get("sentences")
            if rng and list(rng) != [ba, bb]:
                errs.append(f"{bid}: unsplit segment must cover the whole beat "
                            f"({ba}-{bb}), got {rng[0]}-{rng[1]}")
            continue
        if any(not l for l in letters):
            errs.append(f"{bid}: mixes the unsplit ID with sub-beats "
                        f"({', '.join(s['id'] for s in segs)})")
            continue
        if len(segs) == 1:
            errs.append(f"{segs[0]['id']}: a beat split into one piece should "
                        f"just be {bid}")
            continue
        expect = [chr(ord("a") + i) for i in range(len(segs))]
        if letters != expect:
            errs.append(f"{bid}: sub-beats must be lettered "
                        f"{', '.join(bid + e for e in expect)} in order")
        nxt = ba
        for s in segs:
            rng = s.get("sentences")
            if not rng:
                errs.append(f"{s['id']}: sub-beats need a sentences range")
                continue
            if rng[0] != nxt or rng[0] > rng[1]:
                errs.append(f"{s['id']}: sentences {rng[0]}-{rng[1]} don't "
                            f"follow on from sentence {nxt - 1} of {bid}")
            nxt = rng[1] + 1
        if nxt != bb + 1:
            errs.append(f"{bid}: sub-beats cover up to sentence {nxt - 1}, "
                        f"beat ends at {bb}")

    if errs:
        return errs  # cue checks need a sound segment map

    segments = segment_ranges(doc, pe)
    owner = sentence_owner(segments)
    seg_by_id = {s["id"]: s for s in segments}

    # director cues: beds only, IDed off the parent, in a VO sub-beat
    pe_ids = {c["id"] for c in all_cues(pe)}
    for c in doc.get("cues", []):
        cid = c["id"]
        m = CUE_RE.match(cid)
        parent, kind, num = m.group(1), m.group(2), int(m.group(3))
        if c["placement"] != "bed":
            errs.append(f"{cid}: the director may only add bed cues")
        if cid in pe_ids:
            errs.append(f"{cid}: collides with a paper-edit cue")
        elif parent in beats:
            used = [int(CUE_RE.match(x["id"]).group(3))
                    for x in beats[parent].get("cues", [])
                    if CUE_RE.match(x["id"]).group(2) == kind]
            if used and num <= max(used):
                errs.append(f"{cid}: use the next free number after the "
                            f"paper edit's {parent}.{kind}{max(used)}")
        anchor = c.get("anchor") or {}
        if "sentence" not in anchor:
            errs.append(f"{cid}: director cues need a sentence anchor inside "
                        f"a VO sub-beat of {parent}")
            continue
        seg = seg_by_id.get(owner.get(anchor["sentence"], ""))
        if not seg or seg["beat"] != parent or \
                not segment_parts(seg["id"])[1] or seg["mode"] != "vo":
            where = seg["id"] if seg else "no segment"
            errs.append(f"{cid}: anchor sentence {anchor['sentence']} lands on "
                        f"{where}, not a VO sub-beat of {parent}")

    errs += check_reanchors(doc, pe, beats)

    # Re-check cues with reanchors applied. Paper-edit cues were checked on
    # their own already, so only report the ones whose anchor moved.
    cues = all_cues(pe, doc)
    unchanged = tuple(c["id"] + ":" for c in cues
                      if c["_from"] == "paper-edit" and "_reanchor" not in c)
    errs += [e for e in check_cues(cues, beats, script, pe)
             if not e.startswith(unchanged)]

    # beds per segment
    by_id = {c["id"]: c for c in cues}
    beds: dict[str, list[str]] = {s["id"]: [] for s in segments}
    for c in cues:
        if c["placement"] != "bed":
            continue
        n = cue_anchor_sentence(c, beats, by_id)
        sid = owner.get(n)
        if not sid:
            continue
        beds[sid].append(c["id"])
        seg = seg_by_id[sid]
        dur = c.get("duration", "segment")
        if seg["mode"] == "th" and dur == "segment":
            errs.append(f"{c['id']}: bed lands on talking-head segment {sid}; "
                        f"a TH cutaway needs an explicit duration")
        if seg["mode"] == "vo" and dur != "segment":
            errs.append(f"{c['id']}: bed on VO segment {sid} must run the "
                        f"whole segment (duration \"segment\" or none), got "
                        f"{json.dumps(dur)}. VO length isn't known until it's "
                        f"recorded; two pictures under one VO means two VO "
                        f"sub-beats.")
        retime = (c.get("_reanchor") or {}).get("retime")
        if retime:
            errs += _check_retime(c, seg, script)
    for seg in segments:
        if seg["mode"] != "vo":
            continue
        got = beds[seg["id"]]
        if len(got) == 0:
            errs.append(f"{seg['id']}: VO segment has no bed (add one in the "
                        f"director cues, anchored inside it)")
        elif len(got) > 1:
            errs.append(f"{seg['id']}: VO segment has {len(got)} beds "
                        f"({', '.join(got)}); it needs exactly one")

    for jc in doc.get("judgement_calls", []):
        if jc["segment"] not in seg_by_id:
            errs.append(f"judgement_calls: unknown segment {jc['segment']}")

    # Would the prompters build? Checked here so nothing half-written is
    # left behind when a segment can't be matched.
    from build_prompters import check_prompters
    errs += check_prompters(doc, pe, script)
    return errs


def _check_retime(cue: dict, seg: dict, script: Script) -> list[str]:
    """A retimed bed must end inside the segment it lands on."""
    to = cue["_reanchor"]["retime"]["to"]
    if to == "segment":
        return []
    words = segment_words(script, seg)
    span = covered_words(words, cue.get("anchor"), to)
    if span is None:
        return [f"reanchor {cue['id']}: retime to_phrase \"{to['to_phrase']}\" "
                f"isn't in {seg['id']} after the bed's anchor"]
    if "seconds" in to:
        start = anchor_index(words, cue.get("anchor"))
        room = (len(words) - start) * 60 / WPM
        if to["seconds"] > room:
            return [f"reanchor {cue['id']}: retime to {to['seconds']}s runs "
                    f"past the end of {seg['id']} (about {room:.0f}s of "
                    f"speech from the anchor at {WPM} words a minute)"]
    return []


def check_reanchors(doc: dict, pe: dict, beats: dict) -> list[str]:
    """Reanchor may only move a paper-edit bed within its own parent beat,
    and must record the anchor it replaces exactly."""
    errs: list[str] = []
    pe_cues = {c["id"]: c for c in all_cues(pe)}
    director_ids = {c["id"] for c in doc.get("cues", [])}
    seen = set()
    for r in doc.get("reanchor", []):
        cid = r["cue"]
        if cid in seen:
            errs.append(f"reanchor {cid}: listed more than once")
            continue
        seen.add(cid)
        cue = pe_cues.get(cid)
        if not cue:
            if cid in director_ids:
                errs.append(f"reanchor {cid}: only paper-edit cues can be "
                            f"reanchored; change the director cue's anchor")
            else:
                errs.append(f"reanchor {cid}: no such cue in the paper edit")
            continue
        if cue["placement"] != "bed":
            errs.append(f"reanchor {cid}: only bed cues can be reanchored "
                        f"(this is {cue['placement']})")
        current = cue.get("anchor")
        if current != r["from"]:
            errs.append(f"reanchor {cid}: 'from' is {json.dumps(r['from'])} "
                        f"but the paper edit's anchor is "
                        f"{json.dumps(current)}")
        a, b = beats[cue["_beat"]]["sentences"]
        n = r["to"]["sentence"]
        if not a <= n <= b:
            errs.append(f"reanchor {cid}: new anchor sentence {n} is outside "
                        f"its parent beat {cue['_beat']} ({a}-{b})")
        if "retime" in r and r["retime"]["from"] != cue.get("duration"):
            errs.append(f"reanchor {cid}: retime 'from' is "
                        f"{json.dumps(r['retime']['from'])} but the paper "
                        f"edit's duration is {json.dumps(cue.get('duration'))}")
    return errs


# --- entry points ---------------------------------------------------------

def validate_file(path: Path) -> tuple[str | None, list[str]]:
    """Return (kind, errors). Upstream files are validated too."""
    path = Path(path)
    try:
        doc = load(path)
        kind = schema_kind(doc)
    except HandoffError as e:
        return None, [str(e)]

    errs = _schema_errors(doc, kind)
    if errs:
        return kind, errs
    try:
        if kind == "script":
            return kind, check_script(doc)
        if kind == "paper-edit":
            pe, script = load_paper_edit(path)
            return kind, (_prefixed("script", _schema_errors(script.doc, "script"))
                          or check_paper_edit(pe, script))
        if kind == "graphics-spec":
            return kind, check_graphics_spec(path, doc)
        if kind == "sfx-index":
            return kind, []
        if kind == "plan-resolved":
            for role in doc["inputs"]:
                resolve_input(path, doc, role)
            return kind, []
        if kind == "prompter-map":
            resolve_input(path, doc, "director")
            return kind, check_prompter_map(path, doc)
        if kind == "sentences":
            resolve_input(path, doc, "script")
            resolve_input(path, doc, "transcript")
            return kind, check_sentences(doc)
        if kind == "director":
            d, pe, pe_path, script = load_director(path)
            up = _prefixed(pe_path.name, _schema_errors(pe, "paper-edit")
                           or check_paper_edit(pe, script))
            return kind, up or check_director(d, pe, script)
    except HandoffError as e:
        return kind, [str(e)]
    return kind, []


def _prefixed(name: str, errs: list[str]) -> list[str]:
    return [f"[{name}] {e}" for e in errs]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", type=Path, nargs="+")
    args = ap.parse_args()
    failed = False
    for f in args.files:
        kind, errs = validate_file(f)
        if errs:
            failed = True
            print(f"FAIL {f} ({kind or 'unknown'}): {len(errs)} problem(s)")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"OK   {f} ({kind})")
            for n in lint_file(f):
                print(f"  note: {n}")
    sys.exit(1 if failed else 0)


def lint_director(d: dict, pe: dict, script: Script) -> list[str]:
    """A talking-head cutaway that covers most of its segment is really a
    voiceover recorded in the wrong session."""
    notes = []
    segments = segment_ranges(d, pe)
    owner = sentence_owner(segments)
    seg_by_id = {s["id"]: s for s in segments}
    beats = {b["id"]: b for b in pe["beats"]}
    cues = all_cues(pe, d)
    by_id = {c["id"]: c for c in cues}
    for c in cues:
        full_frame_overlay = c["placement"] == "overlay" and (
            c["kind"] in ("sr", "br") or
            (c["kind"] == "mg" and c.get("layer") == "full"))
        if c["placement"] != "bed" and not full_frame_overlay:
            continue
        seg = seg_by_id.get(owner.get(cue_anchor_sentence(c, beats, by_id)))
        if not seg or seg["mode"] != "th":
            continue
        words = segment_words(script, seg)
        span = covered_words(words, c.get("anchor"), c.get("duration"))
        if span and words and (span[1] - span[0]) / len(words) > 0.8:
            pct = 100 * (span[1] - span[0]) / len(words)
            notes.append(f"{c['id']}: cutaway covers about {pct:.0f}% of "
                         f"talking-head segment {seg['id']}; should it be VO?")
    return notes


def lint_file(path: Path) -> list[str]:
    """Non-blocking notes for a file that already validates."""
    try:
        doc = load(path)
        if schema_kind(doc) == "director":
            d, pe, _, script = load_director(path)
            return lint_director(d, pe, script)
        if schema_kind(doc) == "paper-edit":
            pe, script = load_paper_edit(path)
            return lint_paper_edit(pe, script)
    except HandoffError:
        pass
    return []


if __name__ == "__main__":
    main()
