---
name: edit-takes
description: Automated video take selection and A/B roll sync for prompter-scripted footage. Use this skill whenever the user wants to cut a video, select takes, remove fluffed lines or retakes, sync a second camera angle, prepare footage for DaVinci Resolve, or mentions editing A-roll/B-roll, 'retake cut', or running claude-cut on a footage folder. Also trigger when the user points at video files plus a script and asks for a rough cut or clean edit.
---

# Edit Takes: automated take selection pipeline

You are running Elliott's video editing pipeline. He shoots continuously against a
prompter script, fluffs lines, and repeats until happy. The LAST take of each script
section is the keeper. He says the spoken marker **"retake cut"** before going again.
He shoots A-roll (Sony ZV-E10, 25 or 30fps) and sometimes B-roll (iPhone, 24fps),
started at different times, with ONE master audio source (the A-roll audio unless
told otherwise). He claps near the start as a sync aid.

Your job: produce a DaVinci Resolve-importable XML containing only the winning
takes, both angles cut identically, plus a report he can sanity-check.

## Inputs to identify

From the user's message or the current directory, find:

1. **A-roll file** (master audio source) — .mov/.mp4 from the ZV-E10
2. **B-roll file** (optional) — iPhone footage, may start at a different time
3. **Script file** — markdown or plain text, the prompter script
4. Optional overrides: `--keyword` (default "retake cut"), `--handles` (default 0.25s),
   `--min-take-coverage` (default 0.8), `--pad` etc.

If you cannot unambiguously identify which file is which, ASK. Do not guess which
clip holds the master audio.

## Dependencies

Check these are installed before starting; install what's missing (prefer pipx/pip
with --user, or a venv in the plugin data dir):

- `ffmpeg` / `ffprobe` (system)
- Python: `faster-whisper`, `numpy`, `scipy`, `rapidfuzz`, `auto-editor`
  (auto-editor generates the final timeline; its output format is what
  Resolve reliably imports)

## Pipeline (run the bundled scripts in this order)

All scripts live in `${CLAUDE_PLUGIN_ROOT}/scripts/` and write intermediates to a
`.claude-cut/` working folder inside the footage directory.

### 1. Transcribe the master audio

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/transcribe.py" <aroll> -o .claude-cut/transcript.json
```

Word-level timestamps via faster-whisper. First run downloads the model; warn the
user it takes a minute.

### 2. Sync angles (only if B-roll provided)

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/sync.py" <aroll> <broll> -o .claude-cut/offsets.json
```

Cross-correlates the two audio tracks and reports the B-roll offset in seconds
relative to the A-roll. Sanity-check the reported confidence; if it is low, tell
the user and suggest confirming the clap timestamps manually.

### 3. Match takes against the script

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/match_takes.py" .claude-cut/transcript.json <script> \
  -o .claude-cut/cuts.json --report .claude-cut/report.md
```

This does the actual editing decision:
- Splits the script into sentences (ground truth).
- Detects every spoken "retake cut" marker: everything between the previous
  keeper boundary and the marker is binned.
- Fuzzy-matches remaining speech to script sentences; where a sentence was
  attempted more than once, keeps the LAST occurrence.
- Discards partial takes below the coverage threshold.
- Trims leading/trailing dead air inside each kept range, adds handles.

### 4. Build the Resolve XML

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/build_xml.py" .claude-cut/cuts.json \
  --aroll <aroll> [--broll <broll> --offsets .claude-cut/offsets.json] \
  -o <projectname>_cut.fcpxml
```

Writes an FCPXML 1.11 file that Resolve imports directly. A-roll on the spine,
B-roll (if present) as a video-only connected clip on lane 1, both cut to the
same time ranges with offset and per-clip frame rate applied. Timeline format follows the A-roll. Output file must end .fcpxml.

### 5. Report back

Read `.claude-cut/report.md` and give the user a short summary in plain English:
how many takes were found, how many kept, total runtime before/after, and
anything suspicious (unmatched speech, low-confidence matches, off-script
sections that were kept by default). Tell them the fcpxml filename and to
import it via File > Import > Timeline in Resolve, into a FRESH project with
'Automatically import source clips into media pool' ticked (pre-loading clips
into the pool triggers Resolve's stricter timecode matcher and can fail).

## Judgement calls

- **Off-script speech** (intros, ad-libs) with no script match and no retake
  marker after it: KEEP it and flag it in the summary. Never silently delete
  something that might be an intentional ad-lib.
- **Low match confidence** across the board usually means the wrong script file
  or heavy paraphrasing. Stop and ask rather than producing a garbage cut.
- If any script errors out, read the traceback, fix the issue if it is
  environmental (missing dep, wrong path), and only patch script logic if the
  fix is obvious and safe. Report what you changed.
