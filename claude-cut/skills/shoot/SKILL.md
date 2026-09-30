---
name: shoot
description: The recording stage of the claude-cut pipeline. Before recording, it writes a shoot pack from the director and paper edit (which prompter to read, the retake habit, every screen recording and b-roll to capture with a file name, the blur list). After recording, it scans the footage folder and registers the files in shoot.json, asking about anything it can't place. Use after the director stage, when the user asks what to record or for a shot list, or when they've finished recording and want the footage registered.
---

# Shoot: what to record, then what was recorded

This stage sits between the director (prompters written) and the cut
(takes selected). It has two halves, with the user's recording session in
between. You write the pack, and after the recording you register the
files. Code does the matching and the checks.

Run scripts with the Python that has the plugin's dependencies. `$S` is
`${CLAUDE_PLUGIN_ROOT}/scripts`.

**Inputs:**
- `<video>.director.json`, with `prompter.map.json` and the prompters beside it;
- the footage folder, where recordings go.

The footage folder is the working folder: `shoot.json` and everything from
the cut onwards lives there, away from the Obsidian vault.

## Before recording: the shoot pack

```bash
python $S/shoot.py pack --director <video>.director.json -o <footage>/shoot-pack.md
```

The pack covers:
- **Talking head:** read `th.prompter.md` and save the camera file as
  `aroll.*`. A second angle, if there is one, is saved as `broll.*`.
- **Voiceover:** read `vo.prompter.md` and save it as `vo.wav`.
- **The retake habit:** say "retake cut", pause, and restart from the start
  of the fluffed sentence. The last take is the keeper.
- **Every screen recording and b-roll cue**, in running order. Each shows:
  - its ID and brief;
  - the words it plays under;
  - roughly how long it's on screen;
  - a file name to save it as (`b05.sr1.mov`).
- **The blur list**, the things to keep off screen.

Give the user a short summary (how much talking head and voiceover to
record, how many captures and roughly how long) and the pack's path. The
checklist form is meant for the recording session.

Stop here until the user says the recording is done.

## After recording: register the files

```bash
python $S/shoot.py scan <footage> --director <video>.director.json
```

It writes `<footage>/shoot.draft.json` and prints what it found. It matches:
- `aroll.*`, `broll.*` and `vo.*` or `voiceover.*`, ignoring case, `-`, `_`
  and spaces;
- each capture by the cue ID in its file name (`b05.sr1.mov`,
  `B05-SR1 users page.mov` and `b05_sr1_take2.mov` all count).

Every capture cue gets an entry, either its file or `null` for not captured.

**Resolve every question** in the draft by asking the user. Don't guess:

| Question | What to ask |
|---|---|
| "no aroll file found" / "no vo file found" | which file it is (cameras name files like `C0012.MP4`) |
| "more than one …" | which take to use |
| "names bNN.srN, which isn't … in the plan" | which cue it's for (a typo in the name?), or leave it out |
| "not matched to anything" | what it is: often the A-roll or voiceover under a camera name, or a capture saved without its ID |

Put the answers in the draft: paths relative to the footage folder, and
`null` for anything not captured. Then:

```bash
python $S/shoot.py write <footage>/shoot.draft.json --director <video>.director.json
```

It checks the draft and writes `<footage>/shoot.json`, stamped with the
director it was made for. It refuses, listing everything, when:
- a file doesn't exist;
- the A-roll is missing;
- the voiceover is missing while the plan has voiceover segments;
- an asset isn't a capture cue of this director.

Uncaptured cues are fine. Assemble leaves black with a red **MISSING**
marker there, and the user can add the file to `shoot.json` later and
assemble again.

A B-roll angle needs its sync offsets. The edit-takes cut makes them
(`sync.py` → `.claude-cut/offsets.json`). A scan after that picks them up
as `th.offsets`.

## Report back

Tell the user:
- what was registered: the A-roll, B-roll and voiceover, and N of M captures;
- which captures are still missing, by ID and brief;
- where `shoot.json` is.

Next is the **cut** (edit-takes, run once for the talking heads and once
with `--vo` for the voiceover).
