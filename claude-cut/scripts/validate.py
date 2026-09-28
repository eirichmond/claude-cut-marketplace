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
from model import (Script, all_cues, cue_anchor_sentence, load_director,
                   load_paper_edit, segment_parts, segment_ranges,
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
        if "sfx" in c:
            target = by_id.get(c["sfx"])
            if not target or target["kind"] != "sfx":
                errs.append(f"{cid}: sfx {c['sfx']} is not an sfx cue")
        if "script_cue" in c and c["script_cue"] >= n_script_cues:
            errs.append(f"{cid}: script_cue {c['script_cue']} does not exist")
    return errs


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
        if seg_by_id[sid]["mode"] == "th" and \
                c.get("duration", "segment") == "segment":
            errs.append(f"{c['id']}: bed lands on talking-head segment {sid}; "
                        f"a TH cutaway needs an explicit duration")
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
    return errs


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
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
