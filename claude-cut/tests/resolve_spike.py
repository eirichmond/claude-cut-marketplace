#!/usr/bin/env python3
"""Resolve import spike: does Resolve accept the timeline structure the
assemble stage will write?

Usage:
    python tests/resolve_spike.py OUT

Builds the mini video end to end with real speech (macOS say -> whisper ->
match_takes -> edit-takes timeline -> conform), then writes OUT/spike.fcpxml:

  spine     the talking-head clips from the edit-takes timeline, split at
            segment boundaries, with <gap>s opened for VO segments and inserts
  lane -1   VO audio (from the continuous vo.wav) under the VO gaps
  lane -2   a sound effect
  lane 2    screen-recording beds (placeholder: moving test pattern)
  lane 3    full-frame graphics (placeholder: SMPTE bars)
  lane 4    transparent overlays (ProRes 4444 with alpha: a coloured box)
  markers   chapter markers, and a note marker per cue

and OUT/SPIKE.md: what you should see in Resolve.
"""
from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path[:0] = [str(HERE), str(SCRIPTS)]

from build_xml import parse_rt, rt  # noqa: E402
from conftest import Chain  # noqa: E402

PY = sys.executable
W, H, FPS = 640, 360, 25


def run(*cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd))}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def ffmpeg(*args):
    run("ffmpeg", "-v", "error", "-y", *args)


def make_media(out: Path, seconds: int) -> dict:
    """Placeholder assets, long enough for any cue in the spike."""
    m = out / "media"
    m.mkdir(exist_ok=True)
    sr = m / "sr_placeholder.mp4"
    ffmpeg("-f", "lavfi", "-i", f"testsrc2=s={W}x{H}:r={FPS}:d={seconds}",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", sr)
    mg = m / "mg_full_placeholder.mov"
    ffmpeg("-f", "lavfi", "-i", f"smptebars=s={W}x{H}:r={FPS}:d={seconds}",
           "-c:v", "prores_ks", "-profile:v", "3", mg)
    lt = m / "overlay_lower_third.mov"
    ffmpeg("-f", "lavfi", "-i",
           f"color=c=black@0.0:s={W}x{H}:r={FPS}:d={seconds},format=rgba,"
           f"drawbox=x=30:y={H - 90}:w=320:h=56:color=yellow@1:t=fill:replace=1",
           "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
           lt)
    callout = m / "overlay_callout.mov"
    ffmpeg("-f", "lavfi", "-i",
           f"color=c=black@0.0:s={W}x{H}:r={FPS}:d={seconds},format=rgba,"
           f"drawbox=x={W - 230}:y=30:w=200:h=80:color=cyan@1:t=fill:replace=1",
           "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
           callout)
    sfx = m / "sfx_beep.wav"
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=880:duration=0.4:sample_rate=48000",
           "-af", "afade=t=out:st=0.3:d=0.1", sfx)
    return {"sr": sr, "mg": mg, "lt": lt, "callout": callout, "sfx": sfx}


def build_plan(out: Path) -> tuple[dict, Path, Path, Path]:
    (out / "chain").mkdir(parents=True, exist_ok=True)
    chain = Chain(out / "chain")
    chain.build()
    run(PY, SCRIPTS / "build_prompters.py", chain.director)
    media = out / "recordings"
    run(PY, HERE / "make_synthetic_fixture.py", chain.dir, "-o", media,
        "--audio", "--fluff-every", "2")
    cut = out / "cut"
    for mode, src in (("th", media / "aroll.mp4"), ("vo", media / "vo.wav")):
        d = cut / mode
        d.mkdir(parents=True, exist_ok=True)
        run(PY, SCRIPTS / "transcribe.py", src, "-o", d / "transcript.json")
        run(PY, SCRIPTS / "match_takes.py", d / "transcript.json",
            chain.dir / f"{mode}.prompter.md", "-o", d / "cuts.json",
            "--report", d / "report.md", "--sentences-out", d / "sentences.json")
    run(PY, SCRIPTS / "build_xml.py", cut / "th" / "cuts.json", "--aroll",
        media / "aroll.mp4", "-o", cut / "th" / "cut.fcpxml")
    plan = out / "plan.resolved.json"
    print(run(PY, SCRIPTS / "conform.py", "--director", chain.director,
              "--map", chain.dir / "prompter.map.json", "--th", cut / "th",
              "--th-fcpxml", cut / "th" / "cut.fcpxml", "--vo", cut / "vo",
              "-o", plan))
    return (json.loads(plan.read_text()), cut / "th" / "cut.fcpxml",
            media / "vo.wav", media / "aroll.mp4")


def asset(resources, aid, path: Path, fmt: str | None, dur: Fraction,
          video: bool, audio: bool, start: Fraction = Fraction(0)):
    a = ET.SubElement(resources, "asset", {
        "id": aid, "name": path.stem, "start": rt(start), "duration": rt(dur),
        "hasVideo": "1" if video else "0", "hasAudio": "1" if audio else "0"})
    if fmt:
        a.set("format", fmt)
    if audio:
        a.set("audioSources", "1")
        a.set("audioChannels", "1")
        a.set("audioRate", "48000")
    ET.SubElement(a, "media-rep", {"kind": "original-media",
                                   "src": "file://" + quote(str(path.resolve()))})
    return a


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    plan, fcp, vo_wav, aroll = build_plan(out)
    # The ZV-E10 records stereo; the synthetic A-roll is mono. Make it
    # stereo in place so Resolve sees the real A-roll/VO channel mix.
    stereo = aroll.with_name("aroll_stereo.mp4")
    ffmpeg("-i", aroll, "-map", "0:v", "-map", "0:a", "-c:v", "copy",
           "-ac", "2", "-c:a", "aac", "-timecode", "01:00:00:00", stereo)
    stereo.replace(aroll)
    fps = Fraction(plan["timeline"]["fps"])
    frame = 1 / fps

    def T(frames: int) -> Fraction:
        return frames * frame

    total_s = int(plan["timeline"]["frames"] / fps) + 2
    media = make_media(out, total_s)

    tree = ET.parse(fcp)
    root = tree.getroot()
    resources = root.find("resources")
    fmt_id = resources.find("format").get("id")
    for a in resources.findall("asset"):
        if a.get("hasAudio") == "1" and a.get("hasVideo") == "1":
            a.set("audioChannels", "2")   # the A-roll was made stereo above
    spine = root.find("./library/event/project/sequence/spine")
    project = root.find("./library/event/project")
    project.set("name", "claude-cut assemble spike")
    old = [(parse_rt(c.get("offset")), parse_rt(c.get("start")),
            parse_rt(c.get("duration")), c.get("ref"), c.get("name"))
           for c in spine.findall("asset-clip")]
    for c in list(spine):
        spine.remove(c)

    long = Fraction(total_s)
    asset(resources, "vo1", vo_wav, None, long, False, True)
    asset(resources, "sr1", media["sr"], fmt_id, long, True, False)
    asset(resources, "mg1", media["mg"], fmt_id, long, True, False)
    asset(resources, "lt1", media["lt"], fmt_id, long, True, False)
    asset(resources, "co1", media["callout"], fmt_id, long, True, False)
    asset(resources, "sfx1", media["sfx"], None, Fraction(2, 5), False, True)

    # --- spine: TH pieces and gaps, in final timeline order --------------------
    items = [("seg", s) for s in plan["segments"]] + \
        [("ins", c) for c in plan["cues"] if c["placement"].startswith("insert")]
    items.sort(key=lambda it: it[1]["tl"][0])
    placed = []  # (tl start frame, tl end frame, element, element start time)
    GAP_START = Fraction(3600)
    for kind, it in items:
        a, b = it["tl"]
        if kind == "seg" and it["mode"] == "th":
            ta, tb = it["th_tl"]
            cursor = a
            for off, start, dur, ref, name in old:
                oa, ob = round(off * fps), round((off + dur) * fps)
                lo, hi = max(ta, oa), min(tb, ob)
                if hi <= lo:
                    continue
                src = start + T(lo - oa)
                el = ET.SubElement(spine, "asset-clip", {
                    "ref": ref, "name": f"{it['id']} {name}", "offset": rt(T(cursor)),
                    "start": rt(src), "duration": rt(T(hi - lo)), "tcFormat": "NDF",
                    "audioRole": "dialogue"})
                placed.append((cursor, cursor + hi - lo, el, src))
                cursor += hi - lo
        else:
            label = it["id"] if kind == "seg" else f"{it['id']} ({it['placement']})"
            el = ET.SubElement(spine, "gap", {
                "name": f"GAP {label}", "offset": rt(T(a)),
                "start": rt(GAP_START), "duration": rt(T(b - a))})
            placed.append((a, b, el, GAP_START))

    def parent_at(f: int):
        for a, b, el, start in placed:
            if a <= f < b:
                return a, el, start
        a, b, el, start = placed[-1]
        return a, el, start

    def connect(tl_start: int, length: int, attrs: dict):
        a, el, start = parent_at(tl_start)
        attrs["offset"] = rt(start + T(tl_start - a))
        attrs["duration"] = rt(T(max(1, length)))
        return ET.SubElement(el, "asset-clip", attrs)

    # --- VO audio under the VO gaps ------------------------------------------
    for s in plan["segments"]:
        if s["mode"] != "vo":
            continue
        f = s["tl"][0]
        for ra, rb in s["source"]["ranges"]:
            fa, fb = round(Fraction(ra).limit_denominator(10**6) * fps), \
                round(Fraction(rb).limit_denominator(10**6) * fps)
            connect(f, fb - fa, {"ref": "vo1", "lane": "-1",
                                 "name": f"VO {s['id']}", "start": rt(T(fa)),
                                 "audioRole": "dialogue.VO"})
            f += fb - fa

    # --- cues --------------------------------------------------------------------
    lanes = {"bed": "2", "full": "3", "overlay": "4"}
    for c in plan["cues"]:
        a, b = c["tl"]
        if c["kind"] in ("sr", "br"):
            connect(a, b - a, {"ref": "sr1", "lane": lanes["bed"],
                               "name": c["id"], "start": "0s"})
        elif c["kind"] in ("mg", "chapter") and c.get("layer") == "full":
            connect(a, b - a, {"ref": "mg1", "lane": lanes["full"],
                               "name": c["id"], "start": "0s"})
        elif c["kind"] in ("lt", "callout", "mg") and c.get("layer") == "overlay":
            ref = "lt1" if c["kind"] == "lt" else "co1"
            connect(a, b - a, {"ref": ref, "lane": lanes["overlay"],
                               "name": c["id"], "start": "0s"})
        elif c["kind"] == "sfx":
            connect(a, 10, {"ref": "sfx1", "lane": "-2", "name": c["id"],
                            "start": "0s", "audioRole": "effects"})
        # a note marker for every cue, so each one can be found by name
        pa, el, start = parent_at(a)
        ET.SubElement(el, "marker", {"start": rt(start + T(a - pa)),
                                     "duration": rt(frame),
                                     "value": f"{c['id']}: {c['brief'][:60]}"})

    for m in plan["markers"]:
        pa, el, start = parent_at(m["tl"])
        tag = "chapter-marker" if m["kind"] == "chapter" else "marker"
        attrs = {"start": rt(start + T(m["tl"] - pa)), "duration": rt(frame),
                 "value": m["name"]}
        if tag == "chapter-marker":
            attrs["posterOffset"] = "0s"
        ET.SubElement(el, tag, attrs)

    # --- experiments: which marker placements survive, and does an effect
    # that overlaps talking-head speech get its own track? --------------------
    def first(pred):
        return next((a, b, el, s) for a, b, el, s in placed if pred(el))

    def seconds(n):
        return round(n * fps)

    a, b, el, s = first(lambda e: e.tag == "asset-clip")
    ET.SubElement(el, "marker", {"start": rt(s + T(seconds(1))),
                                 "duration": rt(T(seconds(1))),
                                 "value": "TEST A: marker on a spine clip"})
    connect(a + seconds(2), 10, {"ref": "sfx1", "lane": "-2",
                                 "name": "TEST beep over speech",
                                 "start": "0s", "audioRole": "effects"})
    a, b, el, s = first(lambda e: e.tag == "gap" and "b03a" in e.get("name"))
    ET.SubElement(el, "marker", {"start": rt(s + T(seconds(1))),
                                 "duration": rt(T(seconds(1))),
                                 "value": "TEST B: marker on a gap"})
    bed = next(k for k in el if k.tag == "asset-clip" and k.get("lane") == "2")
    ET.SubElement(bed, "marker", {"start": rt(parse_rt(bed.get("start")) +
                                              T(seconds(2))),
                                  "duration": rt(T(seconds(1))),
                                  "value": "TEST C: marker on a connected clip"})
    a, b, el, s = [x for x in placed if x[2].tag == "asset-clip"][1]
    ET.SubElement(el, "chapter-marker", {"start": rt(s + T(seconds(1))),
                                         "duration": rt(T(seconds(1))),
                                         "value": "TEST D: chapter-marker on a spine clip",
                                         "posterOffset": "0s"})

    # Connected clips and markers must come before any nested items' order
    # Resolve cares about? FCPXML wants markers after clip children; keep
    # element order: asset-clips first, then markers.
    for _, _, el, _ in placed:
        kids = list(el)
        for k in kids:
            el.remove(k)
        for k in [k for k in kids if k.tag == "asset-clip"] + \
                [k for k in kids if k.tag != "asset-clip"]:
            el.append(k)

    ET.indent(tree)
    spike = out / "spike.fcpxml"
    tree.write(spike, encoding="utf-8", xml_declaration=True)

    # --- the same markers as an EDL, for Timeline > Import > Timeline
    # Markers from EDL (Resolve's own marker format) --------------------------
    def tcode(f: int) -> str:
        s, fr = divmod(f, int(fps))
        return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{fr:02d}"

    edl = ["TITLE: claude-cut assemble spike", "FCM: NON-DROP FRAME", ""]
    marks = [(m["tl"], "ResolveColorBlue", f"EDL {m['kind']}: {m['name']}")
             for m in plan["markers"]] + \
        [(c["tl"][0], "ResolveColorYellow", f"EDL cue {c['id']}")
         for c in plan["cues"]]
    for i, (f, colour, name) in enumerate(sorted(marks), 1):
        edl += [f"{i:03d}  001      V     C        {tcode(f)} {tcode(f + 1)} "
                f"{tcode(f)} {tcode(f + 1)}  ",
                f" |C:{colour} |M:{name} |D:1", ""]
    (out / "spike_markers.edl").write_text("\n".join(edl))

    # --- and as a script for Resolve's own console (Workspace > Console >
    # Py3), which works in the free version --------------------------------
    colours = {"ResolveColorBlue": "Blue", "ResolveColorYellow": "Yellow"}
    py = ["# Paste into DaVinci Resolve: Workspace > Console > Py3, with the",
          "# spike timeline open. Adds the spike's markers to it.",
          "tl = resolve.GetProjectManager().GetCurrentProject()"
          ".GetCurrentTimeline()",
          "added = 0",
          "for frame, colour, name in ["]
    py += [f"    ({f}, {colours[c]!r}, {n.replace('EDL', 'PY')!r}),"
           for f, c, n in sorted(marks)]
    py += ["]:",
           "    added += bool(tl.AddMarker(frame, colour, name, '', 1))",
           "print(f'added {added} markers to {tl.GetName()}')"]
    (out / "spike_markers_console.py").write_text("\n".join(py) + "\n")

    # --- what to look for --------------------------------------------------------
    def tc(f: int) -> str:
        s, fr = divmod(f, int(fps))
        return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{fr:02d}"

    lines = ["# Resolve import spike: what to check", "",
             f"Import `{spike}` via File > Import > Timeline into a **fresh "
             f"project**, with 'Automatically import source clips into media "
             f"pool' ticked.", "",
             f"Timeline length should be **{tc(plan['timeline']['frames'])}** "
             f"({plan['timeline']['frames']} frames at {plan['timeline']['fps']}).",
             "", "## Track by track", "",
             "Lanes are written as 2 (beds), 3 (full-frame graphics) and 4 "
             "(overlays); lane 1 is kept for the B-roll angle and is empty "
             "here, so Resolve may or may not leave an empty V2. What matters "
             "is the order, bottom to top:", "",
             "- **V1**: dark blue A-roll pieces with black gaps between.",
             "- **(V2, maybe)**: empty (the B-roll angle's lane).",
             "- **Next up**: moving test pattern (screen-recording beds).",
             "- **Next**: SMPTE bars (full-frame graphics and chapter cards).",
             "- **Top**: yellow and cyan boxes, with the picture below visible "
             "around them (alpha).",
             "- **A1**: the talking-head audio (speech) on the A-roll pieces.",
             "- **Below that**: the voiceover speech under the gaps, then a "
             "short beep at the very start.", "",
             "## Timeline items", "", "| Starts | Item | What |", "|---|---|---|"]
    for kind, it in items:
        what = (f"{it['mode'].upper()} segment" if kind == "seg"
                else f"{it['kind']} {it['placement'].replace('_', ' ')}")
        lines.append(f"| {tc(it['tl'][0])} | {it['id']} | {what} |")
    lines += ["", "## Cues", "", "| Starts | Ends | Cue | Lane |", "|---|---|---|---|"]
    for c in plan["cues"]:
        lane = {"sr": "beds", "br": "beds", "sfx": "beep"}.get(c["kind"]) or \
            ("bars" if c.get("layer") == "full" else
             "boxes" if c.get("layer") == "overlay" else "marker only")
        lines.append(f"| {tc(c['tl'][0])} | {tc(c['tl'][1])} | {c['id']} | {lane} |")
    lines += ["", "## Markers", ""] + \
        [f"- {tc(m['tl'])} {m['kind']}: {m['name']}" for m in plan["markers"]] + \
        ["- plus a marker named after every cue", "",
         "## Round 3", "",
         "- The overlay boxes now really have alpha (round 2's were fully "
         "transparent: a bug in the spike, not Resolve).",
         "- The A-roll audio is now stereo, like the ZV-E10; the voiceover is "
         "mono.",
         "- Markers, two more routes: **(a)** in the Media Pool, right-click "
         "the *claude-cut assemble spike* timeline > **Timelines > Import > "
         "Timeline Markers from EDL...** and pick `spike_markers.edl` (don't "
         "use File > Import > Timeline, which makes a new timeline of clips); "
         "**(b)** with the spike timeline open, **Workspace > Console**, "
         "choose **Py3**, paste the contents of `spike_markers_console.py` "
         "and press Enter; markers named \"PY ...\" should appear.", "",
         "## Round 2 experiments (still to check)", "",
         "**Markers.** Open the Index (top left of the Edit page) and pick the "
         "Markers tab. Which of these are listed?", "",
         "- TEST A: marker on a spine clip (about 00:00:03:00)",
         "- TEST B: marker on a gap (about 00:00:15:18)",
         "- TEST C: marker on a connected clip (about 00:00:16:18, on the "
         "test pattern)",
         "- TEST D: chapter-marker on a spine clip (about 00:00:10:04)",
         "- any of the cue markers (b01.mg1, b03.sr1 ...)", "",
         "Then try Resolve's own route: with the timeline open, **Timeline > "
         "Import > Timeline Markers from EDL...** and pick "
         f"`{out / 'spike_markers.edl'}`. Do markers named \"EDL ...\" appear "
         "at the times in the tables above?", "",
         "**Audio tracks.** Every clip now carries an audio role (dialogue, "
         "dialogue.VO, effects), and there's a second beep, \"TEST beep over "
         "speech\", at about 00:00:04:00 on top of the talking head. "
         "Which audio track did the voiceover, the first beep (0:00) and the "
         "second beep land on?", "",
         "## Please report", "",
         "1. Did it import without errors or offline media?",
         "2. Is the length right, and are the gaps where the table says?",
         "3. Did the lanes stack in that order, and which track numbers "
         "did they get?",
         "4. Are the V5 boxes transparent around the edges?",
         "5. Is the voiceover audible under the gaps, in sync with the "
         "timeline items?",
         "6. Do the A-roll clips show source timecode starting 01:00:...?",
         "7. Did chapter markers and cue markers come through, with names?"]
    (out / "SPIKE.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {spike}\nChecklist: {out / 'SPIKE.md'}")


if __name__ == "__main__":
    main()
