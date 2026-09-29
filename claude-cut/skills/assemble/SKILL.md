---
name: assemble
description: Build the full DaVinci Resolve timeline from a conformed claude-cut plan: talking heads and voiceover interleaved in running order, the B-roll angle, screen recordings and b-roll on their own track, and a markers file for chapters, graphics and anything still missing. Use after the conform stage, or when the user asks to assemble the edit, build the Resolve timeline, or drop the screen recordings in.
---

# Assemble: the Resolve timeline

Take `plan.resolved.json` from conform and build the timeline the user
imports into Resolve. It's code; your job is to gather the inputs, run it,
and walk the user through importing and what's still to do.

Run scripts with the Python that has the plugin's dependencies.

## Inputs

- `plan.resolved.json` from the conform stage. It names the edit-takes
  timeline it was built from; assemble starts from that same file (and
  refuses if it has changed since conform).
- `shoot.json` in the video's working folder, saying where things are
  (paths absolute or relative to the file):

  ```json
  { "schema": "claude-cut/shoot@1",
    "th": { "aroll": "C0012.MP4", "broll": "IMG_4411.MOV",
            "offsets": ".claude-cut/th/offsets.json" },
    "vo": { "audio": "vo.wav" },
    "assets": { "b05.sr1": "screens/wp-admin-add-user.mov", "b06.br1": null } }
  ```

  `assets` maps screen-recording and b-roll cue IDs (from the paper edit)
  to their files; `null`, or leaving a cue out, means not captured yet. If
  there's no `shoot.json`, build one with the user: list the plan's `sr`
  and `br` cues with their briefs and ask which files they've got.
  `broll`/`offsets` are only needed for a second camera angle (offsets come
  from edit-takes' sync step).

## Run it

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.py" \
  --plan plan.resolved.json --shoot shoot.json \
  -o <video>_assembled.fcpxml
```

It writes three files next to the output:

- `<video>_assembled.fcpxml`: talking-head clips split at segment
  boundaries, black gaps where the voiceover and inserts (chapter cards,
  stings, holds) go. The B-roll angle sits on the track above the A-roll,
  screen recordings and b-roll above that (video only), and the voiceover
  on its own audio track, from the original recording.
- `<video>_markers.edl`: chapter markers (blue), things to check or still
  missing (red), and every graphic, lower third, zoom, blur and sound
  effect still to add (yellow), each named after its cue.
- `assemble-report.md`: what was placed, what's missing, how to import.

If the voiceover recording is stereo, a mono copy (`<name>_mono.wav`) is
made beside it and used instead: Resolve only gives the voiceover its own
track if its channel format differs from the camera's. The original is
never changed.

## When it fails

- **"has changed since this file was written"**: the edit-takes timeline
  or a cut changed after conform. Conform again, then assemble.
- **"the TH timeline gives N frames, the plan M"**: the same, caught later.
- **"... is Ns long but the plan uses it up to ...: wrong file?"**: the VO
  file isn't the one that was cut. Check `vo.audio`.
- **"refusing to overwrite the edit-takes timeline"**: pick a new output
  name (`<video>_assembled.fcpxml`).

## Report back

Summarise `assemble-report.md`, then give the import steps exactly:

1. **File > Import > Timeline**, pick `<video>_assembled.fcpxml`, into a
   **fresh project** with **Automatically import source clips into media
   pool** ticked (pre-loading clips into the pool makes Resolve's timecode
   matching stricter and imports can fail).
2. In the **Media Pool**, right-click the new timeline > **Timelines >
   Import > Timeline Markers from EDL...** and pick `<video>_markers.edl`.
   Not File > Import > Timeline: that makes a new timeline out of the
   markers.

Then list the missing assets (red markers) so the user knows what to
capture, and mention the yellow markers are graphics and sound still to
add. Re-running assemble after adding files to `shoot.json` is safe: it
always starts from the edit-takes timeline, never from a previous
assembled one.
