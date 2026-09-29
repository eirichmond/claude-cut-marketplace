#!/usr/bin/env python3
"""Conform: merge the paper edit, the TH/VO split and the real cut timings
into one resolved plan, in timeline frames.

Usage:
    python conform.py --director V.director.json --map prompter.map.json \\
        --th .claude-cut/th --th-fcpxml V_cut.fcpxml [--vo .claude-cut/vo] \\
        -o plan.resolved.json [--segments b01-b08] [--allow-missing]

--th / --vo are the cut folders holding cuts.json and sentences.json (from
match_takes --sentences-out). --th-fcpxml is the edit-takes timeline for the
talking heads; it's the ground truth for where each kept moment sits.

Fails loudly: every mismatch between the director, the map and the cut is
listed and nothing is written. Warnings (absorbed off-script lead-ins, split
cut sentences, untimed anchors) are printed and kept in the plan.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from handoff import HandoffError, header, input_ref, load, norm_words
from model import (all_cues, cue_anchor_sentence, load_director,
                   segment_parts, segment_ranges, sentence_owner)
from sentence_timings import align
from validate import validate_file

LEAD_WARN = 2.0          # seconds of absorbed off-script material worth a warning
GRAPHIC_KINDS = {"mg", "lt", "chapter", "callout"}
POINT_KINDS = {"sfx", "music", "marker"}


class ConformError(Exception):
    pass


# --- the TH timeline from edit-takes -----------------------------------------

def parse_rt(s: str) -> Fraction:
    s = s.rstrip("s") or "0"
    return Fraction(s)


@dataclass
class ThTimeline:
    fps: Fraction
    width: int
    height: int
    clips: list  # (timeline offset, source start, duration) in seconds

    @classmethod
    def read(cls, path: Path) -> "ThTimeline":
        root = ET.parse(path).getroot()
        fmt = root.find("resources/format")
        asset = root.find("resources/asset")
        tc = parse_rt(asset.get("start", "0s"))
        clips = []
        for c in root.findall("./library/event/project/sequence/spine/asset-clip"):
            clips.append((parse_rt(c.get("offset")),
                          parse_rt(c.get("start")) - tc,
                          parse_rt(c.get("duration"))))
        if not clips:
            raise ConformError(f"{path.name}: no clips on the spine")
        return cls(1 / parse_rt(fmt.get("frameDuration")),
                   int(fmt.get("width")), int(fmt.get("height")), clips)

    def at(self, t: float) -> Fraction:
        """Timeline seconds for source time t. Inside a cut, the next kept
        moment; after the last clip, the end of the timeline."""
        t = Fraction(t).limit_denominator(10**6)
        for off, src, dur in self.clips:
            if t < src:
                return off
            if t < src + dur:
                return off + (t - src)
        off, src, dur = self.clips[-1]
        return off + dur

    def frame(self, t: float) -> int:
        return round(self.at(t) * self.fps)

    @property
    def frames(self) -> int:
        off, _, dur = self.clips[-1]
        return round((off + dur) * self.fps)


# --- one recording (TH or VO) ------------------------------------------------

@dataclass
class Recording:
    mode: str
    segments: list           # director segments of this mode, running order
    ranges: list             # kept source ranges [(start, end)]
    n_words: dict = field(default_factory=dict)   # script n -> [word]
    boundaries: dict = field(default_factory=dict)  # seg id -> window start
    windows: dict = field(default_factory=dict)   # seg id -> [start, end)
    untimed: dict = field(default_factory=dict)   # n -> segment


def assign_words(rec: Recording, map_entries: list, sentences: dict,
                 script, owner: dict, warnings: list, errors: list,
                 expected: set, allow_missing: bool) -> None:
    """Give every timed word a script sentence n (splitting straddles)."""
    for e in map_entries:
        segs = e["segment"] if isinstance(e["segment"], list) else [e["segment"]]
        ns = e["n"] if isinstance(e["n"], list) else [e["n"]]
        s = sentences.get(e["s"])
        in_scope = [g for g in segs if g in expected]
        if s is None:
            errors.append(f"{rec.mode}: s{e['s']} is in the map but not in "
                          f"sentences.json (cut against a different prompter?)")
            continue
        if s["status"] == "missing":
            if in_scope:
                msg = (f"{rec.mode}: s{e['s']} ({', '.join(segs)}) wasn't "
                       f"found in the recording: \"{script.by_n[ns[0]]['text'][:60]}\"")
                (warnings if allow_missing else errors).append(msg)
            continue
        if not in_scope:
            errors.append(f"{rec.mode}: s{e['s']} was kept but its segment "
                          f"{', '.join(segs)} is outside --segments")
            continue
        words = s["words"]
        if len(ns) == 1:
            rec.n_words.setdefault(ns[0], []).extend(words)
            continue
        labels = align([{"word": w["w"]} for w in words],
                       [script.by_n[n]["text"] for n in ns])
        last = 0
        for w, lab in zip(words, labels):
            last = lab if lab is not None else last
            rec.n_words.setdefault(ns[last], []).append(w)
    for n in rec.n_words:
        rec.n_words[n].sort(key=lambda w: w["start"])


def build_windows(rec: Recording, owner: dict, straddles: dict,
                  warnings: list, errors: list) -> None:
    """Segment windows: [first timed word, next segment's first timed word),
    within this recording; first/last stretched to the kept material."""
    firsts, lasts = {}, {}
    for n, ws in rec.n_words.items():
        sid = owner[n]
        firsts[sid] = min(firsts.get(sid, ws[0]["start"]), ws[0]["start"])
        lasts[sid] = max(lasts.get(sid, ws[-1]["end"]), ws[-1]["end"])
    order = [s["id"] for s in rec.segments]
    for sid in order:
        if sid not in firsts:
            errors.append(f"{sid}: nothing kept for this segment in the "
                          f"{rec.mode.upper()} recording")
    if errors:
        return
    kept_start = rec.ranges[0][0]
    kept_end = rec.ranges[-1][1]
    for i, sid in enumerate(order):
        start = firsts[sid]
        if i:
            # The handle leading into a segment's first word belongs to it,
            # when that kept range starts after the previous segment stopped
            # talking. In one continuous range, split at the first word.
            lead = next((s for s, e in rec.ranges if s <= start < e), start)
            if lead >= lasts[order[i - 1]]:
                start = lead
        if i and (order[i - 1], sid) in straddles:
            # a cut sentence ran across the boundary: split at the pause
            start = (lasts[order[i - 1]] + firsts[sid]) / 2
            s = straddles[(order[i - 1], sid)]
            warnings.append(f"s{s} ({rec.mode}) runs across {order[i - 1]} "
                            f"and {sid}: split at {start:.2f}s in the "
                            f"recording; check this boundary in Resolve")
        rec.boundaries[sid] = round(start, 3)
    first = order[0]
    if rec.boundaries[first] - kept_start > LEAD_WARN:
        warnings.append(f"{first}: absorbed {rec.boundaries[first] - kept_start:.1f}s "
                        f"of kept off-script material before it "
                        f"({rec.mode.upper()} recording)")
    rec.boundaries[first] = kept_start
    tail = kept_end - lasts[order[-1]]
    if tail > LEAD_WARN:
        warnings.append(f"{order[-1]}: absorbed {tail:.1f}s of kept material "
                        f"after its last word ({rec.mode.upper()} recording)")
    for i, sid in enumerate(order):
        end = rec.boundaries[order[i + 1]] if i + 1 < len(order) else kept_end
        rec.windows[sid] = (rec.boundaries[sid], end)


def clip_ranges(window: tuple, ranges: list) -> list:
    a, b = window
    out = []
    for s, e in ranges:
        s2, e2 = max(s, a), min(e, b)
        if e2 > s2:
            out.append([round(s2, 3), round(e2, 3)])
    return out


# --- conform ----------------------------------------------------------------

def parse_scope(spec: str | None, beat_order: list) -> set | None:
    if not spec:
        return None
    m = re.match(r"^(b\d{2,3})(?:-(b\d{2,3}))?$", spec)
    if not m:
        raise ConformError(f"--segments {spec}: expected e.g. b01-b08")
    a, b = m.group(1), m.group(2) or m.group(1)
    if a not in beat_order or b not in beat_order:
        raise ConformError(f"--segments {spec}: unknown beat")
    i, j = beat_order.index(a), beat_order.index(b)
    return set(beat_order[i:j + 1])


def conform(args) -> tuple[dict, list, list]:
    errors, warnings = [], []
    for f in (args.director, args.map):
        _, errs = validate_file(f)
        errors += [f"[{Path(f).name}] {e}" for e in errs]
    if errors:
        return {}, errors, warnings

    d, pe, pe_path, script = load_director(args.director)
    pmap = load(args.map)
    segments = segment_ranges(d, pe)
    owner = sentence_owner(segments)
    mode_of = {s["id"]: s["mode"] for s in segments}
    beats = {b["id"]: b for b in pe["beats"]}
    scope = parse_scope(args.segments, [b["id"] for b in pe["beats"]])
    if scope is not None:
        segments = [s for s in segments if s["beat"] in scope]
    expected = {s["id"] for s in segments}
    seg_by_id = {s["id"]: s for s in segments}

    th_tl = ThTimeline.read(args.th_fcpxml) if args.th_fcpxml else None
    fps = th_tl.fps if th_tl else Fraction(args.fps)
    recordings, inputs = {}, {"director": input_ref(args.director, args.out.parent),
                              "map": input_ref(args.map, args.out.parent)}
    if th_tl:
        inputs["th_fcpxml"] = input_ref(args.th_fcpxml, args.out.parent)

    for mode, folder in (("th", args.th), ("vo", args.vo)):
        segs = [s for s in segments if s["mode"] == mode]
        if not segs:
            continue
        if folder is None:
            errors.append(f"{len(segs)} {mode.upper()} segments but no --{mode} "
                          f"cut folder")
            continue
        if mode not in pmap["prompters"]:
            errors.append(f"the map has no {mode} prompter")
            continue
        sent_path, cuts_path = folder / "sentences.json", folder / "cuts.json"
        absent = [p for p in (sent_path, cuts_path) if not p.exists()]
        if absent:
            errors += [f"{mode}: {p} not found" for p in absent]
            continue
        sdoc = load(sent_path)
        if sdoc["inputs"]["script"]["sha256"] != pmap["prompters"][mode]["sha256"]:
            errors.append(f"{mode}: {sent_path.name} was cut against a "
                          f"different {mode}.prompter.md than the map "
                          f"describes. Re-run the {mode.upper()} cut against "
                          f"the current prompter.")
            continue
        inputs[f"{mode}_sentences"] = input_ref(sent_path, args.out.parent)
        inputs[f"{mode}_cuts"] = input_ref(cuts_path, args.out.parent)
        entries = pmap["prompters"][mode]["sentences"]
        if len(sdoc["sentences"]) != len(entries):
            errors.append(f"{mode}: the cut has {len(sdoc['sentences'])} "
                          f"sentences, the map {len(entries)}")
            continue
        before = len(errors)
        for e in entries:
            for g in (e["segment"] if isinstance(e["segment"], list)
                      else [e["segment"]]):
                if g not in mode_of:
                    errors.append(f"{mode}: map segment {g} isn't in the "
                                  f"director file")
                elif mode_of[g] != mode:
                    errors.append(f"{mode}: map puts {g} on the {mode} "
                                  f"prompter but the director makes it "
                                  f"{mode_of[g].upper()}")
        if len(errors) > before:
            continue  # the map disagrees with the director; timings would mislead
        ranges = [(r["start"], r["end"])
                  for r in json.loads(cuts_path.read_text())["ranges"]]
        rec = Recording(mode, segs, sorted(ranges))
        assign_words(rec, entries, {s["s"]: s for s in sdoc["sentences"]},
                     script, owner, warnings, errors, expected,
                     args.allow_missing)
        rec.untimed = {u["n"]: u["segment"]
                       for u in pmap["prompters"][mode]["untimed"]}
        straddles = {}
        for e in entries:
            if isinstance(e["segment"], list):
                for a, b in zip(e["segment"], e["segment"][1:]):
                    straddles[(a, b)] = e["s"]
        build_windows(rec, owner, straddles, warnings, errors)
        recordings[mode] = rec
    if errors:
        return {}, errors, warnings

    # --- lay the timeline out in running order --------------------------------
    cues = [c for c in all_cues(pe, d)]
    by_id = {c["id"]: c for c in cues}

    def cue_segment(c):
        if c["placement"] == "insert_after" and not c.get("anchor"):
            beat_segs = [s for s in segments if s["beat"] == c["_beat"]]
            return beat_segs[-1]["id"] if beat_segs else None
        n = cue_anchor_sentence(c, beats, by_id)
        sid = owner.get(n) if n else None
        return sid if sid in expected else None

    cue_seg = {c["id"]: cue_segment(c) for c in cues}
    inserts = {"insert_before": {}, "insert_after": {}}
    for c in cues:
        if c["placement"] in inserts and cue_seg[c["id"]]:
            inserts[c["placement"]].setdefault(cue_seg[c["id"]], []).append(c)

    def frames(seconds: float) -> int:
        return round(Fraction(seconds).limit_denominator(10**6) * fps)

    out_segments, cue_tl, seg_tl, cursor = [], {}, {}, 0
    for seg in segments:
        for c in inserts["insert_before"].get(seg["id"], []):
            n = frames(c["duration"]["seconds"])
            cue_tl[c["id"]] = [cursor, cursor + n]
            cursor += n
        rec = recordings[seg["mode"]]
        window = rec.windows[seg["id"]]
        src = clip_ranges(window, rec.ranges)
        entry = {"id": seg["id"], "beat": seg["beat"], "mode": seg["mode"],
                 "sentences": seg["sentences"],
                 "source": {"file": seg["mode"], "ranges": src}}
        if seg["mode"] == "th":
            a = th_tl.frame(window[0])
            b = th_tl.frame(window[1]) if window[1] < rec.ranges[-1][1] \
                else th_tl.frames
            entry["th_tl"] = [a, b]
            length = b - a
        else:
            length = sum(frames(e) - frames(s) for s, e in src)
        entry["tl"] = [cursor, cursor + length]
        seg_tl[seg["id"]] = entry["tl"]
        cursor += length
        out_segments.append(entry)
        for c in inserts["insert_after"].get(seg["id"], []):
            n = frames(c["duration"]["seconds"])
            cue_tl[c["id"]] = [cursor, cursor + n]
            cursor += n
    total = cursor
    entry_by_id = {e["id"]: e for e in out_segments}

    # --- source time -> timeline frame within a segment -------------------------
    def to_frame(sid: str, t: float) -> int:
        e = entry_by_id[sid]
        a, b = e["tl"]
        if e["mode"] == "th":
            f = a + th_tl.frame(t) - e["th_tl"][0]
        else:
            pos = sum(frames(min(max(t, s), en)) - frames(s)
                      for s, en in e["source"]["ranges"])
            f = a + pos
        return max(a, min(b, f))

    def frame_at(mode: str, t: float, fallback: str) -> int:
        """Timeline frame of source time t, through whichever segment's
        window holds it (an untimed anchor can land in the next one)."""
        for sid, (a, b) in recordings[mode].windows.items():
            if a <= t < b and sid in entry_by_id:
                return to_frame(sid, t)
        return to_frame(fallback, t)

    def n_time(mode: str, n: int, cid: str, phrase: str | None,
               end: bool = False) -> float | None:
        rec = recordings[mode]
        ws = rec.n_words.get(n)
        if not ws:
            # untimed (a fragment take matching can't see): first timed word
            # after the previous timed sentence ends
            prev = [m for m in rec.n_words if m < n]
            after = rec.n_words[max(prev)][-1]["end"] if prev else -1
            nxt = [w for m, wl in rec.n_words.items() for w in wl
                   if w["start"] >= after]
            if not nxt:
                return None
            warnings.append(f"{cid}: anchor sentence {n} "
                            f"\"{script.by_n[n]['text']}\" is untimed; placed "
                            f"at the next timed word"
                            + ("; phrase ignored" if phrase else ""))
            return min(w["start"] for w in nxt)
        if not phrase:
            return ws[-1]["end"] if end else ws[0]["start"]
        # match on the same tokens the validator uses: one word can hold
        # several ("mcp-adapter.zip", "built-in")
        p = norm_words(phrase)
        toks, owner_w = [], []
        for wi, w in enumerate(ws):
            for tok in norm_words(w["w"]):
                toks.append(tok)
                owner_w.append(wi)
        for i in range(len(toks) - len(p) + 1):
            if toks[i:i + len(p)] == p:
                return ws[owner_w[i + len(p) - 1]]["end"] if end \
                    else ws[owner_w[i]]["start"]
        warnings.append(f"{cid}: phrase \"{phrase}\" not heard in sentence "
                        f"{n}; used the sentence {'end' if end else 'start'}")
        return ws[-1]["end"] if end else ws[0]["start"]

    def phrase_end(sid: str, beat: str, start_n: int, phrase: str,
                   cid: str) -> int | None:
        seg = seg_by_id[sid]
        mode = seg["mode"]
        a, b = beats[beat]["sentences"]
        for n in range(start_n, b + 1):
            if phrase_in_n(n, phrase):
                t = n_time(mode, n, cid, phrase, end=True)
                s2 = owner[n]
                if t is not None and s2 in entry_by_id:
                    return to_frame(s2, t)
        return None

    def phrase_in_n(n, phrase):
        from handoff import phrase_in
        return phrase_in(phrase, script.by_n[n]["text"])

    out_cues = []

    def resolve(c, stack=()):
        cid = c["id"]
        if cid in cue_tl or cid in stack:
            return cue_tl.get(cid)
        sid = cue_seg[cid]
        if not sid:
            return None
        e = entry_by_id[sid]
        anchor = c.get("anchor") or {}
        if "cue" in anchor:
            target = resolve(by_id[anchor["cue"]], stack + (cid,))
            start = target[0] if target else e["tl"][0]
        else:
            n = anchor.get("sentence") or beats[c["_beat"]]["sentences"][0]
            if owner.get(n) != sid or (n == seg_by_id[sid]["sentences"][0]
                                       and not anchor.get("phrase")):
                # the start of a segment's first sentence is the start of
                # the segment, handles and all
                start = e["tl"][0]
            else:
                t = n_time(e["mode"], n, cid, anchor.get("phrase"))
                start = frame_at(e["mode"], t, sid) if t is not None \
                    else e["tl"][0]
        dur = c.get("duration")
        if dur is None:
            dur = None if c["kind"] in POINT_KINDS else "segment"
        if dur is None:
            end = start
        elif dur == "segment":
            end = e["tl"][1]
        elif dur == "to_beat_end":
            end = max(seg_tl[s["id"]][1] for s in segments
                      if s["beat"] == c["_beat"])
        elif dur == "until_next_cue":
            end = None  # filled in below
        elif "seconds" in dur:
            end = start + frames(dur["seconds"])
        else:
            n0 = anchor.get("sentence") or beats[c["_beat"]]["sentences"][0]
            end = phrase_end(sid, c["_beat"], n0, dur["to_phrase"], cid)
            if end is None:
                warnings.append(f"{cid}: to_phrase \"{dur['to_phrase']}\" "
                                f"wasn't heard; ran it to the segment end")
                end = e["tl"][1]
        tl = [start, end]
        cue_tl[cid] = tl
        return tl

    for c in cues:
        if cue_seg[c["id"]]:
            resolve(c)
    # until_next_cue: the next cue of the same kind on the timeline
    placed = sorted((cue_tl[c["id"]][0], c["id"]) for c in cues
                    if c["id"] in cue_tl)
    for c in cues:
        tl = cue_tl.get(c["id"])
        if tl and tl[1] is None:
            later = [s for s, cid in placed
                     if s > tl[0] and by_id[cid]["kind"] == c["kind"]]
            tl[1] = min(later) if later else total

    for c in cues:
        tl = cue_tl.get(c["id"])
        if not tl:
            continue
        tl[1] = max(tl[0], min(tl[1], total))
        sid = cue_seg[c["id"]]
        seg = entry_by_id[sid]
        retime = (c.get("_reanchor") or {}).get("retime")
        if c["placement"] == "bed" and seg["mode"] == "vo" and \
                tl != seg["tl"]:
            errors.append(f"{c['id']}: VO bed covers {tl} but segment {sid} "
                          f"is {seg['tl']}")
        if retime and isinstance(retime["to"], dict) and \
                "seconds" in retime["to"] and tl[1] > seg["tl"][1]:
            errors.append(f"{c['id']}: retimed cutaway ({retime['to']['seconds']}s) "
                          f"runs {tl[1] - seg['tl'][1]} frames past the end "
                          f"of {sid}")
        out = {"id": c["id"], "kind": c["kind"], "placement": c["placement"],
               "segment": sid, "beat": c["_beat"], "tl": tl,
               "brief": c["brief"]}
        if "layer" in c:
            out["layer"] = c["layer"]
        if c["kind"] in GRAPHIC_KINDS:
            out["render"] = f"mg/{c['id']}.mov"
        if c["kind"] in ("sr", "br"):
            out["asset"] = c["id"]
        if "_reanchor" in c:
            out["reanchored"] = True
        out_cues.append(out)
    out_cues.sort(key=lambda c: (c["tl"][0], c["id"]))

    markers = []
    seen_beats = set()
    for seg in segments:
        b = beats[seg["beat"]]
        if b.get("chapter") and b["id"] not in seen_beats:
            first = seg_tl[seg["id"]][0]
            before = [cue_tl[c["id"]][0]
                      for c in inserts["insert_before"].get(seg["id"], [])]
            markers.append({"tl": min([first] + before), "kind": "chapter",
                            "name": b["chapter"]})
        seen_beats.add(seg["beat"])
    for w in warnings:
        m = re.match(r"s\d+ \((th|vo)\) runs across (\S+) and (\S+):", w)
        if m:
            markers.append({"tl": seg_tl[m.group(3)][0], "kind": "check",
                            "name": f"CHECK split {m.group(2)}/{m.group(3)}"})
    markers.sort(key=lambda m: m["tl"])

    if errors:
        return {}, errors, warnings

    doc = header("plan-resolved", inputs)
    doc["timeline"] = {
        "fps": f"{fps.numerator}/{fps.denominator}",
        "width": th_tl.width if th_tl else 1920,
        "height": th_tl.height if th_tl else 1080,
        "frames": total,
    }
    if scope is not None:
        doc["scope"] = args.segments
    doc["segments"] = out_segments
    doc["cues"] = out_cues
    doc["markers"] = markers
    doc["warnings"] = warnings
    return doc, errors, warnings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--director", type=Path, required=True)
    ap.add_argument("--map", type=Path, required=True)
    ap.add_argument("--th", type=Path, help="TH cut folder")
    ap.add_argument("--th-fcpxml", type=Path)
    ap.add_argument("--vo", type=Path, help="VO cut folder")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--segments", help="only these beats, e.g. b01-b08")
    ap.add_argument("--allow-missing", action="store_true",
                    help="warn instead of failing when a sentence wasn't found")
    ap.add_argument("--fps", type=int, default=25,
                    help="timeline rate when there are no talking heads")
    args = ap.parse_args()
    if args.th and not args.th_fcpxml:
        sys.exit("--th needs --th-fcpxml (the edit-takes timeline)")

    try:
        doc, errors, warnings = conform(args)
    except (HandoffError, ConformError) as e:
        doc, errors, warnings = {}, [str(e)], []
    if errors:
        print(f"Conform failed: {len(errors)} problem(s). Nothing written.")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    tl = doc["timeline"]
    fps = Fraction(tl["fps"])
    secs = tl["frames"] / fps
    print(f"Wrote {args.out}: {len(doc['segments'])} segments, "
          f"{len(doc['cues'])} cues, {len(doc['markers'])} markers, "
          f"{int(secs // 60)}:{int(secs % 60):02d} at {tl['fps']} fps")
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")


if __name__ == "__main__":
    main()
