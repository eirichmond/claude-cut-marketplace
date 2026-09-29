---
name: conform
description: Merge the paper edit, the director's TH/VO split and the real cut timings into one resolved plan (plan.resolved.json) with every segment, graphic, b-roll and marker placed in timeline frames. Use after both edit-takes cuts (talking heads and --vo voiceover) have run in the claude-cut pipeline, or when the user asks to conform, line up the graphics with the cut, or check the cut against the paper edit.
---

# Conform: from plans to real timings

The paper edit and director say *what* happens and in what order; the cuts
say *when*, in the real recordings. Conform joins them through the stable
segment IDs and writes `plan.resolved.json`: every segment, cue and marker
at an exact frame on the final timeline, ready for graphics and assembly.

It's pure code. Your job is to find the inputs, run it, and explain the
result, above all any failure.

Run scripts with the Python that has the plugin's dependencies (the same
one edit-takes uses).

## Inputs

From the video's folder (ask if anything is ambiguous):

- `<video>.director.json` and the `prompter.map.json` next to it (from the
  director stage).
- The talking-head cut folder, usually `.claude-cut/th/` in the footage
  folder, holding `cuts.json` and `sentences.json`, plus the edit-takes
  timeline `<project>_cut.fcpxml` for those talking heads.
- The voiceover cut folder, usually `.claude-cut/vo/`, holding `cuts.json`
  and `sentences.json`.

Both cuts must have been run against the generated prompters with
`--sentences-out` (see the edit-takes skill's pipeline section). If
`sentences.json` is missing, run that cut's step 3 again with the flag.

## Run it

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/conform.py" \
  --director <video>.director.json --map prompter.map.json \
  --th .claude-cut/th --th-fcpxml <project>_cut.fcpxml \
  --vo .claude-cut/vo \
  -o plan.resolved.json
```

- If only part of the script was recorded (a test pass, or a video shot in
  chunks), add `--segments b01-b08`: segments outside that range are left
  out, and anything *recorded* outside it is still an error.
- `--allow-missing` turns "sentence not found in the recording" into a
  warning. Only use it when the user confirms a line was cut on purpose; a
  segment with nothing recorded at all still fails.

## When it fails

Conform refuses to guess. It lists every problem and writes nothing. Explain
each one in plain words and say which stage fixes it:

- **"has been edited since the map was built"** or **"was cut against a
  different ... prompter"**: the prompter changed after recording, or the cut
  used an old one. Re-run the director's `build_prompters.py` if the
  director file changed, then re-run that cut against the current prompter.
  Never edit a prompter or the map by hand.
- **"wasn't found in the recording"**: a line on the prompter isn't in the
  kept takes. Check the edit-takes report: often a retake binned good lines
  said in the same breath as a fluff, or the line was skipped. Re-record,
  or confirm it's dropped and use `--allow-missing`.
- **"nothing kept for this segment"**: a whole segment is missing from the
  recording.
- **"map segment ... isn't in the director file"** / **"the cut has N
  sentences, the map M"**: the director, map and cut are from different
  runs. Rebuild from the director stage forward.
- **"is outside --segments"**: the recording holds more than the range you
  gave; widen it.
- **"VO bed covers ... but segment ... is"** or **"retimed cutaway ... runs
  past the end"**: a picture doesn't fit the real timing. Fix the bed in the
  director stage (reanchor/retime) and conform again.

## Warnings

On success it prints warnings, which are also stored in the plan. Pass each
one on:

- **"absorbed Ns of kept off-script material"**: an intro ad-lib or tail was
  kept (edit-takes never bins off-script speech). It's now part of the first
  or last segment; trim it in Resolve if it's not wanted.
- **"runs across b28 and b29: split at ..."**: a line ending in a quoted
  question or exclamation (`...over MCP?"`) was matched together with the
  next one, so conform split it at the pause. There's a **CHECK** marker at
  that point on the timeline: check the cut sounds right in Resolve.
- **"anchor sentence N ... is untimed"**: a cue was anchored to a fragment
  too short to time ("Fine."), so it was placed at the next timed word.
- **"phrase ... not heard"**: a cue's anchor phrase wasn't found in what was
  said (a mis-hearing or a paraphrase), so it used the sentence start or
  end.

## Report back

Give the user the summary line (segments, cues, markers, running time), the
warnings in plain words, and where `plan.resolved.json` is. Next comes the
assemble stage (and, from v0.6, graphics).
