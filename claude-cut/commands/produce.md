---
description: Run the claude-cut pipeline for one video, from the footage folder. It goes paper edit, director, shoot, cut, conform, graphics, assemble, stopping at each human gate and resuming where it left off.
argument-hint: "[script.md] [--from STAGE] [--to STAGE] [--status] [--segments b01-b08]"
---

# Produce: the whole pipeline, one gate at a time

Arguments: `$ARGUMENTS`

The **current folder is the working (footage) folder**. It holds
`pipeline.json`, which records where this video is. Text handoffs (script,
paper edit, director, prompters) live next to the script, usually in the
Obsidian vault; everything else lives here.

Run scripts with the Python that has the plugin's dependencies. Below, `$S`
is `${CLAUDE_PLUGIN_ROOT}/scripts`, and `P` is `python $S/pipeline.py`.

## 1. Where are we?

- **If there's no `pipeline.json` here:** the first argument must be the
  script (`.md`). If it's missing, ask for it. Then run:
  `P init --script <script.md> [--segments b01-b08]`.
  - `--segments` is only for a partial recording, such as a test pass or a
    video shot in chunks.
  - Tell the user the working folder and the script it's tied to.
- **If there is one:** `P status`. A `--segments` argument updates the
  setting (`P init --script <same script> --segments …`).
- **`--status`:** show `P status` in plain words and stop.
- **`--from STAGE`:** `P reset --from STAGE`. That stage runs again and
  every later stage is marked stale. Files aren't deleted. Tell the user
  which stages that touched.

`P paths` gives every file's fixed location. Use those paths and nothing
else, so the stages find each other's files.

## 2. The loop

Repeat: `P next --json` (add `--to STAGE` if given), then act on `action`:

| `action` | What to do |
|---|---|
| `run` | Run the stage (section 3): `P start STAGE`, do the work, then `P done STAGE`. `done` refuses, listing what's missing or invalid, until the outputs are really there. Fix it, don't force it. |
| `gate` | Stop and hand over (section 4). |
| `wait` | Only the shoot uses this: the user is recording. Ask whether the recording is finished. If it is, `P start shoot` and register the files (the `register` step). If not, stop. |
| `stop` | Reached `--to`. Report and stop. |
| `finished` | Everything is complete. Report and stop. |

`reasons` explains a `stale` or `failed` stage. Say what changed ("the
director file changed, so the shoot pack is out of date") before re-running.

If a stage hits something only the user can resolve (a question, a missing
file, a conform failure), run `P fail STAGE --reason "<short reason>"`,
explain it, and stop. A later `/claude-cut:produce` picks it up again.

## 3. Running each stage

Follow the stage's skill for the judgement and details; the paths come
from `P paths`.

- **paper-edit** follows the `paper-edit` skill:
  - `number_sentences.py <script>`, then write `paper_edit` with `--render`.
- **director** follows the `director` skill:
  - write `director` with `--render`, then `build_prompters.py` (the prompters
    and map land next to it).
- **shoot** follows the `shoot` skill. `next` gives the `step`:
  - `pack`: `shoot.py pack --director <director> -o <shoot_pack>`. Summarise
    it for the user, then run `P wait shoot --reason "recording from the
    shoot pack"` and **stop**: they go and record.
  - `register`: `shoot.py scan <workdir> --director <director>`. Resolve the
    questions with the user, then `shoot.py write`, then `P done shoot`.
- **cut** follows the `edit-takes` skill's pipeline use, with its files in
  `th_dir` and `vo_dir`:
  - **Talking heads:** transcribe the A-roll into `th_dir`. With a B-roll,
    run `sync.py` to `offsets`. Then `match_takes.py` against `th_prompter`
    with `--marker-scope sentence --sentences-out <th_sentences>`, and
    `build_xml.py` to `th_fcpxml`.
  - **Voiceover** (if the director has VO segments): transcribe into
    `vo_dir`, `match_takes.py` against `vo_prompter` (same flags), and
    `render_audio_cut.py` to `vo_cut_wav`.
  - Transcription is slow, so run it in the background.
  - Don't write the offsets into `shoot.json`. Assemble is given them
    directly.
- **conform** follows the `conform` skill:
  - `conform.py --director <director> --map <map> --th <th_dir> --th-fcpxml <th_fcpxml> --vo <vo_dir> -o <plan>`;
  - add `--segments` from the settings if set;
  - add `--allow-missing` only if the user confirms a line was dropped on purpose.
- **graphics** follows the `graphics` skill, with the working folder as `$W`:
  - run its steps 1 to 6 (set-up to render);
  - then `P done graphics`. Its gate is the review (section 4).
- **assemble** follows the `assemble` skill:
  - `assemble.py --plan <plan> --shoot <shoot> -o <assembled>`;
  - add `--offsets <offsets>` if that file exists. The graphics are picked
    up from `graphics/`.
  - Never pass `--allow-unreviewed` from produce. The graphics gate has
    already passed.

## 4. Gates: the user decides

Show `next`'s `message` (what to look at), plus a short summary of the
stage's result, and ask the user to **approve, or say what to change**.
Then stop and wait for their answer.

- **Approve** only on the user's explicit yes in this conversation:
  `P approve STAGE`. Never approve on their behalf, and never skip a gate,
  even when resuming.
- **Changes:** make them with the stage's skill (which rewrites its files
  through its own validation), run `P done STAGE` again, and ask again.
- **The graphics gate is the review page.** Start `review.py serve
  <graphics>` in the background, open it, and run the graphics skill's
  review loop until `review.py status` passes. Then `P approve graphics`,
  which checks the review itself.
- A gate can come back. If an approved stage's files change later, `next`
  asks for it again ("changed since you approved it").

## 5. Report

At every stop, give the user:
- where the video is: `P status`, in words;
- what just happened;
- what they need to do: read something, record, or answer a question;
- how to continue: `/claude-cut:produce` from this folder, or `claude-produce`
  from a terminal.

On `finished`, give the assemble import steps and point to `assemble-report.md`.
