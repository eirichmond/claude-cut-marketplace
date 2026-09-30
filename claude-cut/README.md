# claude-cut

Automated take selection for prompter-scripted videos. Shoot continuously,
fluff your lines, say **"retake cut"**, go again. This plugin transcribes the
master audio, keeps the last take of each script section, syncs your B-roll
(even at a different frame rate and start time), and hands DaVinci Resolve a
clean timeline XML. You do the final polish.

It's also a whole pipeline: `/claude-cut:produce` takes a finished script
to an assembled Resolve timeline with graphics and sound effects, stopping
for your sign-off at each stage (see [The full pipeline](#the-full-pipeline-v06)).

## What it replaces

- Driving auto-editor by hand (it's still used under the bonnet to write
  the final timeline, fed with take-selection decisions instead of silence
  detection)
- The manual backwards pass through the footage hunting for the last good take
- Manually syncing and cutting the B-roll to match

## Install

```bash
# One-off setup
/plugin marketplace add ~/path/to/claude-cut-marketplace
/plugin install claude-cut@elliott-local
```

Dependencies (the skill will offer to install the Python ones on first run):

```bash
brew install ffmpeg node     # if not already on the machine
pip install faster-whisper numpy scipy rapidfuzz auto-editor jsonschema pyyaml
```

## Shell alias

Add to `.zshrc`:

```bash
claude-cut() {
  claude "/claude-cut:edit-takes $*"
}
```

Then from any footage folder:

```bash
claude-cut aroll.mov broll.mov script.md
```

A-roll only works too:

```bash
claude-cut aroll.mov script.md
```

A voiceover recorded as one continuous audio file, against its own prompter
script, same "retake cut" marker:

```bash
claude-cut --vo vo.wav vo.prompter.md
```

That gives `<project>_vo_cut.wav` (the kept takes, joined) and the usual
report, instead of a Resolve timeline.

## Shooting conventions the pipeline relies on

- One master audio source (the A-roll clip by default)
- Prompter script provided as markdown or plain text
- Say "retake cut" before repeating a section (fuzzy matching catches
  unmarked repeats too, but the keyword makes it bulletproof)
- Clap early on when running two devices (helps the waveform sync, and helps
  you if you ever need to check it by eye)
- Off-script ad-libs are kept and flagged in the report, never silently binned

## Outputs

- `<project>_cut.fcpxml` — import via File > Import > Timeline in Resolve.
  A-roll (with audio) on the spine, B-roll connected above it, cut identically.
- `.claude-cut/report.md` — every keep/bin decision with timestamps.
  Read it before trusting the cut, especially in the first few sessions.

## Tuning knobs (pass through the skill)

- `--keyword` — retake marker phrase (default: "retake cut")
- `--handles` — seconds of breathing room either side of a kept range (0.25)
- `--merge-gap` — kept ranges closer than this get merged (1.0s)
- `--min-take-coverage` — a final take must cover this fraction of its script
  sentence or it's flagged as partial (0.8)
- `--marker-scope sentence` — "retake cut" bins only from where the retaken
  sentence began, instead of everything since the last pause (the default,
  `chunk`). Use it if you restart from the fluffed line rather than the
  paragraph; the full pipeline always does.

## The full pipeline (v0.6)

edit-takes still works on its own, exactly as above. It's also one stage of
a pipeline that goes from a finished script to an assembled Resolve
timeline with its graphics and sound effects, one skill per stage, each
handing a file to the next.

### One command: produce

```bash
claude-produce() {
  claude "/claude-cut:produce $*"
}
```

Then, from the video's footage folder:

```bash
claude-produce ~/vault/videos/my-video.md   # the first time: which script
claude-produce                              # after that: carry on
claude-produce --status                     # where is it?
claude-produce --from graphics              # redo a stage (and what follows)
claude-produce --to cut                     # stop after a stage
```

`pipeline.json` in the footage folder remembers the script and where each
stage is. Produce runs the next stage and stops at every gate for you: it
never approves anything itself, and it resumes where it stopped. If you
edit a file a stage was made from, that stage (and what follows) shows as
stale and runs again.

| Stage | Skill | Writes | Gate |
|---|---|---|---|
| Paper edit | `paper-edit` | `<script>.script.json`, `<script>.paper-edit.json` + `.md`: beats `b01`, `b02`... with visuals and cues | you approve it |
| Director | `director` | `.director.json` + `.md` (talking head or voiceover per beat), `th.prompter.md`, `vo.prompter.md`, `prompter.map.json` | you approve it |
| Shoot | `shoot` | `shoot-pack.md` (what to record and what to name it); after you record, `shoot.json` (the files, matched by name) | you record, then confirm the files |
| Cut | `edit-takes` | talking heads and voiceover cut, per-sentence timings | you read both reports |
| Conform | `conform` | `plan.resolved.json`: everything placed in timeline frames; fails loudly on any mismatch | - |
| Graphics | `graphics` | HyperFrames renders per cue in your identity, one SFX stem | the review page: approve each one |
| Assemble | `assemble` | `<video>_assembled.fcpxml`, `<video>_markers.edl`, `assemble-report.md` | - |

Text handoffs live next to the script (your vault); everything else lives
in the footage folder.

Import the assembled timeline with File > Import > Timeline (fresh project,
auto-import source clips on), then its markers with Media Pool > right-click
the timeline > Timelines > Import > Timeline Markers from EDL. Graphics sit
on their own tracks above the screen recordings (overlays with alpha on
top), and the sound effects are one stem on their own audio track.

### Graphics

- **Identity:** `identity/frame.md` (cyan on navy, Anton and DM Mono, fonts
  in `identity/fonts/`). Every template and one-off composition takes its
  colours and type from it; changing it re-renders everything.
- **Templates first** (chapter card, lower third, callout, tag, key term,
  warning strip), one-off HyperFrames compositions for the rest.
- Rendered at 60fps (or natively at 24/30/60) and converted to the
  timeline's rate at each cue's exact frame count: overlays ProRes 4444
  with alpha, full-frame ProRes 422 HQ.
- **Sound effects** from your own library folders:

  ```bash
  python scripts/sfx_index.py add-library story "/Volumes/Terrance/assets/The Story Sound Pack"
  python scripts/sfx_index.py build
  ```

  The graphics stage picks a sound per cue, with two alternatives, and
  can place it inside its cue (`offset_s`) so a hit lands on the moment it
  belongs to, like a stamp slamming down half a second into its graphic.
  Everything is mixed into one full-length stem, which Resolve gives its own
  track.
- **Review page:** every render (over the picture it sits on) and every
  sound effect, in timeline order, with Approve or Redo and a note, and a
  one-click swap to an alternative sound. Only what you send back is
  re-rendered, and assemble won't place anything you haven't approved.
- Needs `node` and `ffmpeg`; HyperFrames (`hyperframes@0.8.71`) is fetched
  by `npx` on first use and brings its own headless Chrome.

Every handoff carries the hashes of what it was made from, so a stage run
against stale inputs says so instead of producing a quietly wrong edit.

### What's new in 0.6

- **Graphics stage:** HyperFrames renders in your identity, template-first,
  with one-off compositions checked against house rules, a review page,
  and per-cue re-renders.
- **Sound effects** from local libraries, indexed and searchable, mixed into
  one stem.
- **Shoot stage:** a shoot pack before recording, and footage registered by
  file name afterwards.
- **Assemble** places the approved graphics and the stem, and refuses stale
  or unapproved renders.
- **`/claude-cut:produce`** runs the pipeline from the footage folder, with
  human gates, `--from`, `--to` and `--status`.

### Tests

```bash
cd claude-cut && venv/bin/python -m pytest              # everything
venv/bin/python -m pytest -m "not slow"                  # skip whisper and real HyperFrames renders
CLAUDE_CUT_REAL_FIXTURE=/path/to/recordings venv/bin/python -m pytest -m real
```
