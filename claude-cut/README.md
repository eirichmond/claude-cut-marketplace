# claude-cut

From a finished script to an assembled DaVinci Resolve timeline for
prompter-scripted YouTube videos. You shoot continuously, fluff your lines,
say **"retake cut"** and go again. Claude plans the edit, picks the last good
take of every line, builds the graphics and sound effects in your style, and
hands Resolve a timeline to polish. You sign off each step along the way.

There are two ways to use it:

- **The whole pipeline:** one command, `claude-produce`, run from the
  video's footage folder. This is the one to learn.
- **Just the take picking:** `claude-cut` on a recording and its script
  gives a cut timeline, nothing else.

## Quick start

### 1. Install (once)

In a terminal:

```bash
brew install ffmpeg node
pip install faster-whisper numpy scipy rapidfuzz auto-editor jsonschema pyyaml
```

In Claude Code:

```
/plugin marketplace add ~/.claude/plugins/claude-cut-marketplace
/plugin install claude-cut@elliott-local
```

Add these two shortcuts to `~/.zshrc`, then open a new terminal:

```bash
claude-produce() { claude "/claude-cut:produce $*"; }
claude-cut() { claude "/claude-cut:edit-takes $*"; }
```

**Updating to a new version** later:

```bash
claude plugin marketplace update elliott-local
claude plugin update claude-cut@elliott-local
```

### 2. Make a video

**Write the script** as markdown. The spoken words go under a `## Script`
heading. A line that's entirely `[in brackets]` is a note about what's on
screen, not something you say.

**Make a folder for the footage**, go into it and start:

```bash
mkdir ~/Footage/my-video && cd ~/Footage/my-video
claude-produce ~/vault/videos/my-video.md
```

Produce works through the stages and **stops whenever it needs you**. At
each stop, do what it asks, then run `claude-produce` again (no script
needed now) from the same folder to carry on:

| Stop | What you do |
|---|---|
| 1. Paper edit | Read `my-video.paper-edit.md` (next to your script): the beats, graphics and chapters. Say "approve", or say what to change. |
| 2. Director | Read `my-video.director.md` and the two prompters (`th.prompter.md` for the talking heads, `vo.prompter.md` for the voiceover). Approve or change. |
| 3. Shoot | Open `shoot-pack.md` in the footage folder and record from it (details below). Put the files in the footage folder, then `claude-produce` and tell it you're done. |
| 4. Files | It lists what it found. Answer any questions about files it couldn't place, then approve. |
| 5. Cut | Read the two cut reports it points you to, and listen to the voiceover cut. Approve. |
| 6. Graphics | A review page opens. Watch each graphic and listen to each sound effect, then Approve, or Redo with a note. Tell Claude when you've been through them all; it fixes the redos and you look again. |
| 7. Done | Import into Resolve (below). |

**Recording** (the shoot pack says all this too):

- Talking head: read `th.prompter.md` to camera and save the file as
  `aroll` (e.g. `aroll.MP4`). A second angle, if you have one, is `broll`.
- Voiceover: read `vo.prompter.md` in one go and save it as `vo.wav`.
- Fluffed a line? Say **"retake cut"**, pause, and start again from the
  beginning of that sentence. The last take always wins.
- Screen recordings and b-roll: record each one on the shoot pack's list
  and put its ID in the file name, e.g. `b05.sr1.mov`. Anything you don't
  record gets a red MISSING marker to fill in later.

**Into Resolve:**

1. File > Import > Timeline, and pick `my-video_assembled.fcpxml`, into a
   **fresh project** with **Automatically import source clips into media
   pool** ticked.
2. In the Media Pool, right-click the new timeline > Timelines > Import >
   Timeline Markers from EDL..., and pick `my-video_markers.edl`.

Blue markers are chapters, red ones need a look (missing footage,
something to check), and yellow ones are sound effects and anything left to
do by hand, like zooms and blurs.

**Handy anytime**, from the footage folder:

```bash
claude-produce --status   # where is this video up to?
claude-produce            # carry on from where it stopped
```

The first time you reach the graphics, Claude asks where your sound
effects are (e.g. `/Volumes/Terrance/assets/The Story Sound Pack`) and
remembers the folder.

### Just picking takes

From a folder with your recording and its script:

```bash
claude-cut aroll.MP4 broll.mov script.md    # or just: claude-cut aroll.MP4 script.md
```

You get `<project>_cut.fcpxml` to import into Resolve (File > Import >
Timeline, fresh project, auto-import on) and `.claude-cut/report.md`
explaining every keep and bin.

---

## Advanced

### Produce options

```bash
claude-produce ~/vault/videos/my-video.md --segments b01-b08  # only part of the script was recorded
claude-produce --from graphics   # redo a stage and everything after it
claude-produce --to cut          # stop after a stage
claude-produce --status          # show every stage
```

`pipeline.json` in the footage folder remembers the script and where each
stage is. Produce never approves anything for you, and it resumes wherever
it stopped. If you edit a file a stage was made from, that stage and the
ones after it show as stale and run again. If an approved file changes,
that stage asks for your approval again.

### The stages

| Stage | Skill | Writes | Gate |
|---|---|---|---|
| Paper edit | `paper-edit` | `<script>.script.json`, `<script>.paper-edit.json` + `.md`: beats `b01`, `b02`... with visuals and cues | you approve it |
| Director | `director` | `.director.json` + `.md` (talking head or voiceover per beat), `th.prompter.md`, `vo.prompter.md`, `prompter.map.json` | you approve it |
| Shoot | `shoot` | `shoot-pack.md`; after you record, `shoot.json` (the files, matched by name) | you record, then confirm the files |
| Cut | `edit-takes` | talking heads and voiceover cut, with per-sentence timings, in `.claude-cut/` | you read both reports |
| Conform | `conform` | `plan.resolved.json`: everything placed in timeline frames; fails loudly on any mismatch | - |
| Graphics | `graphics` | HyperFrames renders per cue in your identity, one SFX stem, in `graphics/` | the review page: approve each one |
| Assemble | `assemble` | `<video>_assembled.fcpxml`, `<video>_markers.edl`, `assemble-report.md` | - |

The text files (the script, paper edit, director and prompters) live next
to the script, so they sit in your vault. Everything else lives in the
footage folder.

Each stage is also a skill you can run on its own, e.g.
`/claude-cut:paper-edit` on a script, or `/claude-cut:shoot` for a shoot pack.
Every file carries the hashes of what it was made from, so a stage run
against stale inputs says so instead of producing a quietly wrong edit.

### The timeline

- **Video:** talking heads on the main track, black gaps where the
  voiceover and chapter cards go, the second angle above, then screen
  recordings and b-roll, then full-frame graphics, then overlays with
  alpha (lower thirds, callouts) on top. Resolve drops empty tracks, so the
  numbers shift, but the order holds.
- **Audio:** camera audio, the voiceover on its own track (a mono copy is
  made from a stereo recording so Resolve keeps it separate), and the sound
  effects as one full-length stem on another.

### Graphics

- **Identity:** `identity/frame.md` (cyan on navy, Anton and DM Mono, fonts
  in `identity/fonts/`). Every template and one-off composition takes its
  colours and type from it; changing it re-renders everything.
- **Templates first** (chapter card, lower third, callout, tag, key term,
  warning strip), with one-off HyperFrames compositions for the rest.
- Rendered at 60fps (or natively at 24/30/60) and converted to the
  timeline's rate at each cue's exact frame count: overlays are ProRes 4444
  with alpha, full-frame graphics ProRes 422 HQ.
- **Sound effects** come from your own library folders. Claude registers
  them when asked, or you can run it yourself (`<plugin>` is the
  `claude-cut` folder of this repo):

  ```bash
  python <plugin>/scripts/sfx_index.py add-library story "/Volumes/Terrance/assets/The Story Sound Pack"
  python <plugin>/scripts/sfx_index.py build
  ```

  A sound is picked per cue, with two alternatives, and can be placed
  inside its cue (`offset_s`) so a hit lands on its moment, like a stamp
  slamming down half a second into its graphic.
- **Review page:** every render (over the picture it sits on) and every
  sound effect, in timeline order, with Approve, or Redo and a note, and a
  one-click swap to an alternative sound. Only what you send back is
  re-rendered, and assemble won't place anything you haven't approved.
- Needs `node` and `ffmpeg`. HyperFrames (`hyperframes@0.8.71`) is fetched
  by `npx` on first use and brings its own headless Chrome.

### Take picking in detail (edit-takes)

What it replaces:

- Driving auto-editor by hand (it's still used under the bonnet to write
  the final timeline, fed with take-selection decisions instead of silence
  detection)
- The manual backwards pass through the footage hunting for the last good take
- Manually syncing and cutting the B-roll to match

A voiceover recorded as one continuous audio file, against its own prompter
script, with the same "retake cut" marker:

```bash
claude-cut --vo vo.wav vo.prompter.md
```

That gives `<project>_vo_cut.wav` (the kept takes, joined) and the usual
report, instead of a Resolve timeline.

**Shooting conventions:**

- One master audio source (the A-roll clip by default)
- Prompter script provided as markdown or plain text
- Say "retake cut" before repeating a section (fuzzy matching catches
  unmarked repeats too, but the keyword makes it bulletproof)
- Clap early on when running two devices (helps the waveform sync, and helps
  you if you ever need to check it by eye)
- Off-script ad-libs are kept and flagged in the report, never silently binned

**Outputs:**

- `<project>_cut.fcpxml`: import via File > Import > Timeline in Resolve.
  A-roll (with audio) on the spine, B-roll connected above it, cut identically.
- `.claude-cut/report.md`: every keep/bin decision with timestamps.
  Read it before trusting the cut, especially in the first few sessions.

**Tuning knobs** (ask for them when running the skill):

- `--keyword`: retake marker phrase (default: "retake cut")
- `--handles`: seconds of breathing room either side of a kept range (0.25)
- `--merge-gap`: kept ranges closer than this get merged (1.0s)
- `--min-take-coverage`: a final take must cover this fraction of its script
  sentence or it's flagged as partial (0.8)
- `--marker-scope sentence`: "retake cut" bins only from where the retaken
  sentence began, instead of everything since the last pause (the default,
  `chunk`). Use it if you restart from the fluffed line rather than the
  paragraph; the full pipeline always does.

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
