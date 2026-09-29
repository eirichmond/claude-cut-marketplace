---
name: paper-edit
description: Build a paper edit from a finished video script. Split it into beats with stable IDs (b01, b02...) and call the on-screen visuals, b-roll, screen recordings, motion graphics, lower thirds, transitions and sound for each one. Use when turning a script into an editor's blueprint, planning post-production, or as the first stage of the claude-cut pipeline (before the director). Writes <script>.paper-edit.json plus a readable .md.
---

# Paper edit: script to editor's blueprint

Turn a finished script into a paper edit: a beat-by-beat blueprint an editor
can follow without guessing. Every later stage of the claude-cut pipeline
(director, shoot, cut, conform, graphics, assemble) hangs off the beat IDs
you assign here, so they must be right.

**You never copy spoken text.** The script is split into numbered sentences
by code, and a beat is just a range of those numbers. Code fills the words
back in wherever they're shown. This is what guarantees the prompter, the
cut and the timeline all agree with the script word for word.

## Step 1. Number the script

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/number_sentences.py" <script.md>
```

This writes `<script>.script.json` next to the script. Spoken text is
everything under `## Script` up to the first `---`. Headings inside it are
sections (`sec01`...). Lines that are entirely `[bracketed]` and fenced code
blocks are **script cues**, not speech, and are listed in `script_cues` with
`after` = the sentence number they follow (0 = before the first).

If it fails with "no '## Script' heading", ask the user where the spoken
script starts rather than guessing. Read the whole `.script.json` before
planning: `sections`, `sentences` (n, section, para, text) and `script_cues`.
`preamble` is text before the first section heading (not spoken) and a
section's `level` is just its heading depth; neither matters for beats.

**Placing script cues.** A script cue's `after` and `section` only say
where it was written. Place each cue by meaning, on the beat it
illustrates. Writers often put a cue just after the line it belongs to, or
at the end of a section when it really opens the next one. (A cue at the
top of a section has `after` = the previous section's last sentence, but it
belongs to its own section's first beat.)

## Step 2. Plan the beats

A beat is a run of **whole sentences** (`"sentences": [first, last]`) with
**one primary picture**. Rules the validator enforces:

- Beats tile the script: b01 starts at sentence 1, each beat starts where
  the last one ended plus one, the last beat ends at the final sentence.
  No gaps, no overlaps.
- IDs run `b01`, `b02`, ... in order.
- A one-sentence beat is still a pair: `"sentences": [19, 19]`.
- A beat stays inside one section (`"section": "sec03"`).

How to cut the script into beats (editorial judgement, this is the craft):

- **Start a new beat when the picture changes.** A new screen, a cut back to
  camera, a new graphic that owns the frame. If the change happens
  mid-sentence, keep the sentence whole and put the change in a cue anchored
  to a phrase instead.
- Typically one to four sentences. A long paragraph over one continuous
  screen recording can be one beat; a punchy hook might be a beat per line.
- Short fragments ("Fine.", "Sweet huh!") belong in the beat around them.
- The director will later decide talking head vs voiceover per beat, and
  may split a beat at a sentence boundary. Where a paragraph obviously
  swings from face to screen, make that two beats yourself.

## Step 3. Call the visuals for every beat

For each beat set:

- `chapter` (only on the beat where one starts): the chapter title for the
  YouTube description and chapter markers. It runs until the next beat that
  sets one, so a chapter can start mid-section. A chapter card graphic is a
  separate cue; its words can differ from the chapter title.
- `visual`: the primary picture in plain words, a one-line summary for the
  reader (the bed cue's `brief` is the detailed build or shoot spec). "A, medium close-up",
  "SR: wp-admin Users > Add New", "BR: pizza coming out of the oven",
  "MG: kitchen illustration builds". Be specific. "B-roll: hands typing on a
  keyboard" beats "some b-roll".
- `transition_in`: how we arrive (hard cut, J-cut, L-cut, cross-dissolve,
  graphic wipe). Hard cut unless a different one serves the story. Don't add
  motion for the sake of it.
- `pace`: delivery and edit feel. Fast and punchy for a hook, slower for an
  explanation.
- `key_point: true` where the script lands its main idea. The beat needs
  something that reinforces the point on screen: a `callout`, `lt`, `zoom`,
  or an `mg` (a graphic bed that *is* the point counts). Don't add a
  caption just to satisfy the rule if the graphic already says it.
- `notes`: anything else the editor needs.
- `cues`: see below.

### Cues

Every graphic, screen, b-roll shot, zoom, blur, sound or marker is a cue:

```json
{ "id": "b05.lt1", "kind": "lt", "placement": "overlay", "layer": "overlay",
  "anchor": { "sentence": 21, "phrase": "application password" },
  "duration": { "seconds": 3 }, "brief": "'Application password: a separate login for software'",
  "script_cue": 9 }
```

- **id**: `<beat>.<kind><n>`, numbered per kind within the beat
  (`b05.sr1`, `b05.lt1`, `b05.lt2`). Never renumber an existing cue; graphic
  files are named after these IDs.
- **kind**: `mg` motion graphic, `lt` lower third, `chapter` chapter card,
  `callout` on-screen text/highlight, `sr` screen recording, `br` b-roll,
  `zoom` punch-in or zoom, `blur` blur/redaction, `sfx` sound effect,
  `music` music change, `marker` an editor note that isn't a visual.
- **placement**:
  - `bed`: the full-frame picture of the beat (`sr`, `br` or `mg` only).
    Give a beat **at most one bed**, anchored at its first sentence (omit
    `anchor`). If the picture changes for good, that's a new beat. There
    are two kinds, and the choice matters to the director:
    - **Full-length bed** (no `duration`): only for a **genuinely
      screen-led** beat, where the words narrate what's on screen (a
      walkthrough, a demo, code). It covers the whole beat, so it pushes
      the beat towards voiceover.
    - **Timed cutaway** (`duration` in seconds or `to_phrase`): the default
      for anything with the presenter's personality in it, above all
      **personal stories and key points**. The picture cuts to the screen
      or b-roll and comes back to the face, so the beat can stay on
      camera.
    When in doubt, make it a timed cutaway: the director can always move a
    bed into a voiceover part, but can only shorten one, never lengthen it.
    Don't end a timed bed just before a short button line ("Sweet huh!",
    "That's it."): under three words can't be its own talking-head segment,
    so the face can't come back for it. Let the bed run the beat, or end it
    on an earlier sentence.
    A bed always starts at the beat's first sentence, so a timed bed is
    "screen first, then face". If the beat **opens on the presenter and
    then cuts away** (a story, a key point, an aside), it has no bed: use a
    full-frame overlay cutaway (below) anchored where the cut happens.
  - `overlay`: on top of the picture, adds no time (lower thirds, callouts,
    zooms, blurs, sfx, overlay graphics). An `sr` or `br` overlay is a
    full-frame **cutaway that starts mid-beat**: anchor it where it starts,
    give it a duration, and the audio carries on underneath. An `mg` overlay
    with `layer: "full"` is the same thing for a graphic.
  - `insert_before` / `insert_after`: adds its own time to the timeline
    (a cold-open sting, a chapter card, "hold the finished file for four
    seconds"). Needs `duration: {"seconds": n}` and only `mg`, `chapter`,
    `sr` or `br`. The duration is exact: for "at least four seconds" use 4.
    Without a steer from the script, a chapter card is 1.5 to 2 seconds and
    a cold-open sting about 2.
    Chapter cards are usually `insert_before` on the first beat of their
    chapter; make one an `overlay` only if it plays over live picture.
- **layer**: required on `mg`, `lt`, `chapter` and `callout`, and not
  allowed on any other kind. `full` for a full-frame graphic, `overlay` when
  it sits over picture and needs transparency. An `mg` or `chapter` bed or
  insert is `layer: "full"`; `sr` and `br` never take a layer.
- **anchor**: where it starts. `{ "sentence": n }` or
  `{ "sentence": n, "phrase": "exact words" }` (the phrase must appear in
  sentence n, and n must be in this beat; matching ignores case,
  punctuation and backticks, so `mcp-adapter.zip` matches
  `` `mcp-adapter.zip` ``), or `{ "cue": "<id>" }` to start with another
  cue. Omit for the start of the beat.
- **duration**: `"segment"`, `"to_beat_end"`, `{ "seconds": n }`,
  `{ "to_phrase": "words later in this beat" }` (ends when that phrase has
  been said), or `"until_next_cue"` (the next cue of the same kind). A *segment* is the recorded unit the cue lands
  on: the whole beat, or, if the director later splits the beat into a
  talking-head part and a voiceover part, the part it's in. `"segment"` is
  the default for beds. `sfx` plays for its natural length and `music` and
  `marker` are points in time, so all three can omit `duration`.
- **brief**: what it is, precisely enough to build or shoot it. For
  graphics, include the on-screen words.
- **script_cue** (optional): the index into `script_cues` this came from,
  or a list of indexes. Several cues can come from one script cue (the
  kitchen illustration that builds across four beats), and one cue can
  cover several.

A sound that goes with a graphic is its own `sfx` cue anchored to it:
`"anchor": { "cue": "b01.mg1" }`.

Turn every script cue into cues, and record it in `script_cue`:

- `[Talking head ...]` is a mode note. It shapes the beat's `visual` and
  `pace` and needs no cue (a delivery note like "serious for a second"
  goes in `pace`).
- `[Screen: ...]` usually becomes the beat's `sr` bed.
- `[MG: ...]` becomes an `mg`, `lt` or `chapter` cue.
- `[Zoom: ...]` becomes a `zoom`; `[Blur ...]` a `blur`.
- A hold instruction becomes an `insert_after`.
- A code block shown on screen goes in the brief of the `sr` (or `mg`) that
  shows it, usually the beat's bed, with any hold as an `insert_after`.
- Instructions with no single moment ("highlight each key as it's
  mentioned") go in the briefs of the cues they govern, or in `notes`.
- Edit instructions with no picture of their own ("[Cut to building the
  ability]") go in `transition_in` of the beat they lead into, with a
  `marker` cue carrying the `script_cue` index. Markers are
  `"placement": "overlay"`, anchored where they apply.
- A short flash that illustrates a spoken line ("quick flash of the
  terminal, hold for two seconds") is a timed full-frame overlay anchored
  on that line. Use `insert_before`/`insert_after` only when the moment
  needs time of its own with no speech over it.
- Things tied to the end of the video (end screen elements) are a
  `marker` cue on the last beat plus a line in `notes`. If the end screen
  needs a minimum length, set the last beat's `est_seconds` and say so in
  `notes`; the edit will hold the picture if speech runs short.

Where the script has no cue but the story needs a visual, add one: that's
the job. `write_handoff.py` lists any bracketed script cue you didn't use
(other than talking-head notes), so you can check nothing was dropped.

## Step 4. Section and whole-video notes

Finalise the beats before writing these: notes that mention beat IDs go
stale silently if you merge or split beats afterwards. If the script has
its own chapter list (often in its metadata), follow it for the beats'
`chapter` titles unless the beats make a better case.

- `sections`: for each script section worth a note,
  `{ "id": "sec02", "purpose": "..." }`: what the section is for and how it
  should feel.
- `notes`:
  - `tone` (text): overall feel, music, captions, recurring graphics,
    style rules.
  - `before_timeline` (text): anything to fix or check before editing,
    such as script claims that need verifying.
  - `blur_list` (a **list** of strings): everything that must be blurred,
    one item each.
  - Add other keys if useful; each is a paragraph of text.
- `assets`: lists of things to capture or build, keyed by cue kind (`"sr"`,
  `"br"`, `"mg"`, `"sfx"`...), one plain line per item.
- `title`: the video title from the script.

## Step 5. Write, validate, render

Write the body (no `schema`, `created` or `inputs`) to a draft file in your
scratchpad, shaped like:

```json
{ "title": "...", "notes": {...}, "sections": [...],
  "beats": [ { "id": "b01", "section": "sec01", "sentences": [1, 2],
               "visual": "...", "transition_in": "...", "pace": "...",
               "key_point": false, "notes": "...", "cues": [...] } ],
  "assets": {...} }
```

Then:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/write_handoff.py" paper-edit <draft.json> \
  --input script=<script>.script.json \
  -o <script folder>/<script stem>.paper-edit.json --render
```

It adds the header, validates, and writes the `.json` and a `.md` render.
If it lists problems, nothing is written: fix the draft and run it again
until it's clean. Never hand-edit the `.md`; it's regenerated from the JSON.

When it succeeds it prints a summary (beats, chapters, cues by kind) and
any **notes**: unused script cues and key points with no reinforcing cue.
Notes don't block the file, but deal with each one or be ready to say why
not.

The runtime estimate is words at 150 a minute plus inserts. For beats with
long silent screen time (typing, loading, holds) set `est_seconds` on the
beat to your own estimate. It **replaces** that beat's word-count estimate
and excludes its inserts, which are always added on top.

## Step 6. Report back

Tell the user: the summary line from `write_handoff.py`, the estimated
runtime (from the top of the render), any notes you left unresolved and
why, anything in `before_timeline`, and where the files are. Suggest the
director stage next.

## Principles

- Every visual earns its place by supporting the message. Cut anything
  decorative.
- Match cuts to the rhythm of speech, not to a metronome.
- Keep b-roll honest to the point being made. Don't illustrate a claim you
  can't back up.
- Never rewrite, reorder or drop the script's words. If something in the
  script looks wrong, say so in `before_timeline`; don't fix it here.
