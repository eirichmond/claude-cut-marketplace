# claude-cut

Automated take selection for prompter-scripted videos. Shoot continuously,
fluff your lines, say **"retake cut"**, go again. This plugin transcribes the
master audio, keeps the last take of each script section, syncs your B-roll
(even at a different frame rate and start time), and hands DaVinci Resolve a
clean timeline XML. You do the final polish.

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
brew install ffmpeg          # if not already on the machine
pip install faster-whisper numpy scipy rapidfuzz auto-editor jsonschema
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

## The full pipeline (v0.5)

edit-takes still works on its own, exactly as above. It's also one stage of
a pipeline that goes from a finished script to an assembled Resolve
timeline, one skill per stage, each handing a file to the next:

| Stage | Skill | Writes |
|---|---|---|
| Paper edit | `/claude-cut:paper-edit` | `<script>.script.json` (numbered sentences), `<script>.paper-edit.json` + `.md`: beats `b01`, `b02`... with visuals and cues |
| Director | `/claude-cut:director` | `.director.json` + `.md` (talking head or voiceover per beat), `th.prompter.md`, `vo.prompter.md`, `prompter.map.json` |
| Shoot | (you) | record the talking heads from `th.prompter.md` and the voiceover as one continuous file from `vo.prompter.md`, saying "retake cut" as usual; list the files in `shoot.json` |
| Cut | `/claude-cut:edit-takes` | run twice: talking heads (with `--sentences-out`) and `--vo` |
| Conform | `/claude-cut:conform` | `plan.resolved.json`: everything placed in timeline frames; fails loudly on any mismatch |
| Assemble | `/claude-cut:assemble` | `<video>_assembled.fcpxml`, `<video>_markers.edl`, `assemble-report.md` |

Import the assembled timeline with File > Import > Timeline (fresh project,
auto-import source clips on), then its markers with Media Pool > right-click
the timeline > Timelines > Import > Timeline Markers from EDL.

Every handoff carries the hashes of what it was made from, so a stage run
against stale inputs says so instead of producing a quietly wrong edit.
Motion graphics (HyperFrames) and a single command that runs the whole
pipeline come in v0.6; until then graphics and sound effects are markers.

### Tests

```bash
cd claude-cut && venv/bin/python -m pytest              # everything
venv/bin/python -m pytest -m "not slow"                  # skip whisper runs
CLAUDE_CUT_REAL_FIXTURE=/path/to/recordings venv/bin/python -m pytest -m real
```
