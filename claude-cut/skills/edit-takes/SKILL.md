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
   `--min-take-coverage` (default 0.8), `--marker-scope` (default `chunk`), `--pad` etc.

If you cannot unambiguously identify which file is which, ASK. Do not guess which
clip holds the master audio.

If the user passes `--vo <audio file>` (a voiceover recorded as one continuous
audio file), it's a voiceover run: there's no A-roll or B-roll. Follow
"Voiceover runs (--vo)" below instead of steps 2 and 4.

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

## Retake scope (--marker-scope)

By default (`chunk`, as in v0.4.0) "retake cut" bins everything said since
the last pause. If the user fluffs a line mid-flow and restarts from that
line, good sentences said in the same breath before it are lost; the report
shows them as `BINNED (before marker)` with nothing kept for their sentence.

`--marker-scope sentence` bins only from where the retaken sentence began,
keeping the earlier lines (report reason: `before marker (retaken)`). Pass
it to match_takes when the user asks for it, and suggest it when a report
shows good lines lost that way. Standalone runs keep the default unless
asked.

## Voiceover runs (--vo)

`--vo vo.wav` (any audio ffmpeg reads: .wav, .m4a, .mp3, or a video file's
audio) means the voiceover was recorded separately, as one continuous file,
against its own prompter script, with the same "retake cut" marker. Take
selection is exactly the same; there's just no picture:

1. Transcribe the VO file (step 1 as usual, with the VO file as the source).
2. Skip sync: there's one source.
3. Match takes (step 3 as usual, with the VO prompter as the script).
4. Instead of the Resolve XML, render the kept audio so the user can listen
   to the cut straight away:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/render_audio_cut.py" .claude-cut/cuts.json \
     --source <vo file> -o <projectname>_vo_cut.wav
   ```

5. Report back as in step 5, but point them at the `_vo_cut.wav` rather than
   an fcpxml. There's nothing to import into Resolve from a VO run on its
   own; in the full pipeline the assemble stage places the voiceover.

Keep a voiceover run's working files separate from a talking-head run's in
the same folder: use `.claude-cut/vo/` instead of `.claude-cut/` for its
transcript, cuts, report and sentences.

## Pipeline use (only when asked)

When edit-takes runs as the cut stage of the full pipeline it runs twice:
once for the talking heads (A-roll, optional B-roll, `th.prompter.md`,
working files in `.claude-cut/th/`) and once with `--vo` (the voiceover
file, `vo.prompter.md`, working files in `.claude-cut/vo/`). In both, step 3
also writes per-sentence timings for the conform stage:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/match_takes.py" .claude-cut/transcript.json <prompter> \
  -o .claude-cut/cuts.json --report .claude-cut/report.md \
  --marker-scope sentence --sentences-out .claude-cut/sentences.json
```

`--sentences-out` only adds a file. The pipeline always uses
`--marker-scope sentence` (see above), so conform isn't handed lines lost to
a mid-flow retake.

## Judgement calls

- **Off-script speech** (intros, ad-libs) with no script match and no retake
  marker after it: KEEP it and flag it in the summary. Never silently delete
  something that might be an intentional ad-lib.
- **Low match confidence** across the board usually means the wrong script file
  or heavy paraphrasing. Stop and ask rather than producing a garbage cut.
- If any script errors out, read the traceback, fix the issue if it is
  environmental (missing dep, wrong path), and only patch script logic if the
  fix is obvious and safe. Report what you changed.
