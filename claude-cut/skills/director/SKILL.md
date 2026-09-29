---
name: director
description: Decide, beat by beat, what gets recorded as a talking head (face to camera) and what as a voiceover (audio only over screen or b-roll), from a claude-cut paper edit. Writes <video>.director.json plus a readable .md, and generates the TH and VO prompter scripts and the sentence map the cut and conform stages need. Use after the paper-edit stage, or when the user wants to split a script into talking-head and voiceover recording sessions.
---

# Director: the talking head / voiceover split

Read the paper edit and decide, for every beat, whether it's recorded as a
**talking head** (TH, face to camera) or a **voiceover** (VO, audio only,
laid over screen recordings, b-roll or graphics). The point is to let the
presenter record all the talking heads in one sitting and all the
voiceovers in another, from two prompter scripts, without hunting through
the script.

You don't change the paper edit and you never write spoken text. Segments
reference the paper edit's beat IDs; code fills the words in.

Run every script with the Python that has the plugin's dependencies
installed (the same one edit-takes uses). The full file format is in
`${CLAUDE_PLUGIN_ROOT}/schemas/director.schema.json`; the examples below
cover everything you normally need.

## Step 1. Read the paper edit

The input is `<video>.paper-edit.json`. Check it first:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/validate.py" <video>.paper-edit.json
```

If it fails, stop and tell the user (a markdown paper edit with no beat IDs
is a legacy file: the paper-edit stage has to be run first). Then read the
`.paper-edit.md` render for the words and the visuals, and the JSON for the
beat IDs, sentence ranges and cues. Sentence numbers refer to the
`.script.json` named in the paper edit's header.

## Step 2. Decide TH or VO for every beat

Talking head when the line is:

- The hook or the opening.
- An opinion, a judgement or a bit of personality.
- Spoken directly to the viewer ("you", "I", "let me show you").
- A transition between sections, or the sign-off.
- An interstitial (like, subscribe, sponsor).

Voiceover when the line is:

- Narrating a screen recording, a demo, or anything happening on screen.
- Walking through code, settings or a step-by-step process.
- Sitting over b-roll, a diagram or a motion graphic.
- A list of facts, figures or specifications where the face adds nothing.

The paper edit's `visual` and bed cues are strong evidence: a beat whose
picture is a screen recording is usually VO; one whose visual is "A" is
usually TH. If a beat genuinely could go either way, make it TH and add a
judgement call.

## Step 3. Split beats only where they switch

Most beats get one segment with the **same ID** as the beat:

```json
{ "id": "b07", "beat": "b07", "mode": "vo", "on_screen": "..." }
```

If a beat genuinely switches between face and screen partway through, split
it at a sentence boundary into sub-beats lettered in order, each with its
sentence range. Together they must cover the beat's range exactly:

```json
{ "id": "b12a", "beat": "b12", "sentences": [40, 41], "mode": "th", "delivery": "..." },
{ "id": "b12b", "beat": "b12", "sentences": [42, 44], "mode": "vo", "on_screen": "..." }
```

Never mix `b12` with `b12a`, and never split into a single sub-beat. A
sentence is never split. Every segment needs at least one sentence of three
or more words (take matching can't find "Fine." on its own), so keep short
fragments with a neighbour.

For each segment add:

- `delivery` (TH and VO): pace, tone, where to pause, what to land.
- `on_screen` (VO): what's on screen while it plays, so the presenter knows
  what they're talking over.

Both are printed on the prompters as `###` lines under the segment's
heading, so keep them short: one line each.

Watch the rhythm: switching between face and screen more often than every
10 to 15 seconds feels choppy unless it's deliberate. Prefer fewer, longer
segments, and say so in a judgement call when a stretch has to cut fast.

After a split, check the beat's other cues still make sense on their side.
A zoom or callout on a screen element that has landed on a talking-head
sub-beat is a problem for the paper edit: note it in a judgement call.

## Step 4. Every VO segment needs exactly one bed

A **bed** is the full-frame picture under a voiceover: a paper-edit cue
with `"placement": "bed"`. The validator checks that each VO segment ends
up with exactly one, after your splits. A bed lands on the segment
containing its anchor sentence (a bed with no anchor is at its beat's
first sentence).

When a split leaves a VO segment without a bed, or with the wrong one:

- **Add a bed** in your `cues`, only for a VO sub-beat. ID it off the
  parent beat with the next free number for that kind (if the paper edit
  has `b12.sr1`, yours is `b12.sr2`), anchor it inside the sub-beat, and
  write a brief like any paper-edit cue:
  `{ "id": "b12.sr2", "kind": "sr", "placement": "bed", "anchor": { "sentence": 42 }, "duration": "segment", "brief": "..." }`.
  Only `sr`, `br` or `mg` (with `"layer": "full"`).
- **Reanchor a paper-edit bed** when a split put it on the wrong side, for
  example a beat whose bed sits at its first sentence, which you've made a
  talking head. Record it in `reanchor`, copying the paper edit's current
  anchor exactly into `from` (`null` if it had none):
  `{ "cue": "b12.sr1", "from": null, "to": { "sentence": 42 }, "reason": "b12a went to camera; the screen starts at b12b" }`.
  `to` can also carry a `phrase` inside that sentence. Only paper-edit
  beds, only within the same beat. The ID and brief stay.

A paper-edit bed on a talking-head segment is a **cutaway**: fine if it
has a `duration` (seconds or `to_phrase`), because the face comes back. A
bed with no duration would cover the face for the whole segment; the
validator rejects that.

A **VO segment's bed must run the whole segment**: `duration` `"segment"`
or none. Its length isn't known until it's recorded, so a bed timed in
seconds or to a phrase could leave the end of the voiceover with no
picture. Two pictures under one voiceover means two VO sub-beats, each
with its own bed.

**Retime** a paper-edit bed by adding `retime` to its reanchor entry
(copy the paper edit's duration exactly into `from`, `null` if none):

- To keep a screen-led beat **on camera** (a personal story, the key
  insight), shorten its full-length bed into a timed cutaway so the face
  comes back:
  `"retime": { "from": null, "to": { "to_phrase": "went looking for another way in" } }`.
  The new end must fall inside the segment the bed lands on: a
  `to_phrase` after the anchor, or seconds that fit the segment's spoken
  length. You can only shorten a bed this way, never lengthen it.
- When a timed paper-edit bed lands on a **VO** segment, retime it to
  `"segment"` so it covers the whole voiceover.

If the anchor doesn't move, `to` is just the current anchor (for a bed
with no anchor, `{ "sentence": <beat's first sentence> }`). After a
retime, `write_handoff.py` notes any talking-head cutaway that still
covers more than about 80% of its segment: that beat probably wants to be
VO after all. The same note covers full-frame overlay cutaways (`sr`, `br`
or full-frame `mg` overlays) on a talking-head segment. A cutaway overlay
inside a VO segment is fine: it's a second picture over the bed.

A paper-edit bed that runs up to a short "button" line ("Sweet huh!",
"That's it.") can't hand that line to camera: two words can't be a segment
of their own. Keep the beat VO, and say in a judgement call that the bed's
brief (which may say "back to face") is now out of date.

If an **unsplit** beat you've made VO has no bed, you can't add one (the
director only adds beds to sub-beats). Either keep the beat TH with a
judgement call, or stop and tell the user the paper edit needs a bed on
that beat.

The paper edit's picture is evidence, not a verdict. The "if in doubt,
talking head" rule and the talking-head list above still apply to a beat
with a bed: keep it on camera and retime the bed into a cutaway.

## Step 5. Write, validate, build the prompters

Write the body (no `schema`, `created` or `inputs`) to a draft file in your
scratchpad:

```json
{ "segments": [ ... every beat, in paper-edit order ... ],
  "cues": [ ... your bed cues; leave out if none ... ],
  "reanchor": [ ... leave out if none ... ],
  "judgement_calls": [ { "segment": "b03", "note": "one or two sentences on why" } ] }
```

Then:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/write_handoff.py" director <draft.json> \
  --input paper_edit=<video>.paper-edit.json \
  -o <folder>/<video>.director.json --render

python "${CLAUDE_PLUGIN_ROOT}/scripts/build_prompters.py" <folder>/<video>.director.json
```

`write_handoff.py` validates everything (every beat covered, sub-beats
tiling their beat, beds, reanchors, and that the prompters can be built:
every segment has a sentence of three or more words) and only writes when
it's clean; fix the draft and rerun until it is. `build_prompters.py` then writes
`th.prompter.md`, `vo.prompter.md` and `prompter.map.json` next to the
director file. It reports "untimed fragments": sentences under three words
("Fine.", "Sweet huh!") that take matching can't find on their own. That's
fine: they're still on the prompter and still recorded, and the cut keeps
them inside their segment. Just make sure no segment is *only* fragments.
It may note that a cut sentence "runs across" two segments: a
segment ending in a quoted question or exclamation (`...over MCP?"`) isn't
a sentence break to take matching. That's handled at conform; pass the
note on to the user. Never edit a prompter by hand; regenerate it.

## Step 6. Report back

Give the user the top line of the `.director.md` render (how many TH and VO
segments, words and rough spoken duration of each), the prompter file
names, the summary line from `write_handoff.py` (splits, director beds,
reanchors), and the judgement calls. Remind them:

- Record the talking heads from `th.prompter.md` in one sitting and the
  voiceovers from `vo.prompter.md` as **one continuous audio file**, reading
  straight through in order.
- Say "retake cut" before going again, as usual, and then restart from the
  start of the paragraph (or, for a short segment, from its heading), not
  just the fluffed sentence. Until the opt-in retake fix lands, a retake
  can bin good lines said in the same breath as the fluff.
- The `## b05` headings are for them to keep their place; they're not read
  out.
