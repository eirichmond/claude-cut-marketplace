---
name: graphics
description: Make every graphic and sound effect in a conformed claude-cut plan. Chapter cards, lower thirds, callouts and one-off motion graphics are rendered with HyperFrames in the user's visual identity, at each cue's exact length. Sound effects are picked from their local libraries and mixed into one stem. Then everything goes through a review page until the user approves it. Use after the conform stage, or when the user asks to make, render, redo or review the graphics, lower thirds or sound effects for a claude-cut video.
---

# Graphics: renders and sound effects, reviewed

Conform placed every cue at an exact frame. This stage turns the plan's
graphic cues (`mg`, `lt`, `chapter`, `callout`) into rendered clips and
its `sfx` cues into one sound-effects stem. The user signs each one off on
a review page, and assemble then places them on the timeline.

**Your job is the design judgement.** You choose a template and its words
for each cue, author the one-offs, and pick the sounds. Code does the
rest: validation, rendering, frame counts and the review state.

Run scripts with the Python that has the plugin's dependencies. Below,
`$S` is `${CLAUDE_PLUGIN_ROOT}/scripts`, `$W` is the video's working folder
(it holds `plan.resolved.json` and `shoot.json`), and `$G` is `$W/graphics`,
the graphics project.

Rendering needs `node`, `ffmpeg` and HyperFrames, which is fetched once
with `npx` as `hyperframes@0.8.71` and uses its own headless Chrome. If a
render fails before it starts, run `npx --yes hyperframes@0.8.71 doctor`.

## 1. Set up the graphics project

```bash
python $S/identity.py install $G       # frame.md, fonts, GSAP, identity.json
python $S/sfx_index.py build           # incremental; seconds after the first run
python $S/sfx_index.py snapshot $G     # the index this video's picks are checked against
```

- **The identity** is the plugin's `identity/frame.md` (the user's own:
  cyan accent on navy, Anton and DM Mono). Every template and composition
  takes its colours and type from it. Re-running `install` is safe;
  changing `frame.md` makes every render stale, so they all re-render.
- **If no SFX library is registered** (`sfx_index.py build` says so), ask
  the user where their sound effects are, then run
  `sfx_index.py add-library NAME PATH` and build again. If a library's
  drive is unplugged, the build keeps its old entries, but rendering needs
  the files, so ask for the drive.

## 2. Read every cue

```bash
python $S/custom.py brief $G --all               # every graphic cue, in timeline order
node ${CLAUDE_PLUGIN_ROOT}/graphics/build.mjs --list   # the templates and their variables
python $S/sfx_index.py suggest $W/plan.resolved.json -o $G/sfx-candidates.json
```

For each cue, `brief` gives:
- the brief;
- the words spoken over it;
- its exact length;
- whether it's an overlay (alpha, over the picture) or full frame
  (replaces the picture);
- what's underneath it.

The length is fixed by the plan. Design to it, never around it.

## 3. Decide each graphic: a template first

Use a template whenever one carries the brief:

| Cue | Template | Variables |
|---|---|---|
| `chapter` | `chapterCard` | `num` ("01"), `kicker` ("Chapter one"), `title` (lowercase display, 1–4 words), optional `lead`, `meta` |
| `lt` naming or explaining something | `lowerThird` | `kicker` (short, uppercase mono), `head` (≤ 6 words), optional `line` (≤ 12 words) |
| `lt` defining a single term | `keyTerm` | `term`, optional `note`, `code: true` for a file or command name |
| a short label ("Later in the video") | `tag` | `text` (≤ 4 words), `pos` corner |
| `callout` | `callout` | `kicker`, `text` (one line), `code` for code, `pos` corner |
| `callout` or `lt` that is a warning ("never…", "don't…") | `warningStrip` | `kicker` ("Warning"), `head` (lowercase display), optional `line` |

**How to write the text:**
- When the brief quotes the words (`'MCP = Model Context Protocol'`), use
  them as quoted. Split them across `head` and `line` if they're long.
  Otherwise, write from the spoken words, in the speaker's terms, as short
  as it can be.
- `*one clause*` in a headline sets it in the accent. Use it once, on the
  word that matters.
- `` `code` `` sets file names, commands, flags and code in mono, keeping
  their case. Headlines and chapter titles are displayed lowercase anyway.
- **Placement:** keep overlays clear of the speaker's face. Lower thirds
  sit bottom left. Put callouts and tags in the corner the brief asks for,
  otherwise `bl` (callout) or `tr` (tag). If the brief says where the
  speaker is ("beside Elliott"), use the opposite side.

Ignore `slideAcross`: it's the spike's wipe test.

**A one-off (`custom`)** is for a cue no template can carry: usually an
`mg` (a terminal moment, a stamp, a diagram, a stat), or a callout that
needs a picture rather than words. Author those **after** the templated
cues, following `references/custom-compositions.md`
(`custom.py new`, then design, then `custom.py check`, then look at the stills).

**Skip** a graphic only for a real reason, such as "the screen recording
already shows it" or "the user will build this in Resolve". Skipped cues
stay yellow markers on the timeline.

## 4. Pick the sound effects

For each `sfx` cue, `sfx-candidates.json` has a shortlist ranked on file
and folder names. Judge the brief against them yourself. `sfx_index.py
search "…" [--category Whooshes]` finds more.

- `file` is your pick, as its path inside the library.
- `alternatives` holds up to two other good fits. The review page plays
  them, so the user can swap with one click.
- `gain_db` usually sits between −6 (an impact under a stamp or a whoosh
  on a wipe) and −12 (a click or tick under speech). Leave it at 0 only
  for a hit meant to punch.
- `offset_s` puts the effect that many seconds after its cue's start. An
  effect anchored to a graphic starts with it, but the moment it belongs
  to is often inside it: a stamp that lands 0.58s in, or a card that snaps
  shut at the end. Take the time from the composition's timeline (or the
  template's in-animation), minus how long the sound takes to peak. A
  negative value leads in, for a whoosh that starts before a wipe.
- **If nothing fits, skip it with a reason.** It stays a marker for the
  user to fill by hand. Never pick a file that isn't in the index.

The effects are mixed into **one** full-length stereo stem,
`sfx/sfx_stem.wav`. Resolve gives a single full-length clip its own track,
where individual clips would displace the camera audio. The chosen files
are also copied to `sfx/` by cue, for anyone replacing one by hand.

## 5. Write graphics.json

Write the body as a draft, `$G/graphics.draft.json`:

```json
{ "graphics": [
    { "cue": "b04.lt1", "template": "lowerThird",
      "vars": { "kicker": "For those who don't know", "head": "*mcp* = model context protocol",
                "line": "A standard way for AI to talk to software." } },
    { "cue": "b01.mg1", "template": "custom", "composition": "compositions/b01.mg1.html" } ],
  "sfx": [ { "cue": "b01.sfx1", "library": "story", "file": "Impacts/Impact - Deep - Snap.wav",
             "alternatives": ["Impacts/Impact - Subdrop.wav"], "offset_s": 0.52,
             "gain_db": -6 } ],
  "skip": [ { "cue": "b20.mg1", "reason": "the screen recording already shows the file" } ] }
```

Then stamp and validate it:

```bash
python $S/write_handoff.py graphics-spec $G/graphics.draft.json \
  --input plan=$W/plan.resolved.json --input frame=$G/frame.md \
  --input sfx_index=$G/sfx-index.json -o $G/graphics.json
```

(Leave out `--input sfx_index=…` if there are no `sfx` picks.)

Every graphic and `sfx` cue must appear exactly once, in `graphics`, `sfx`
or `skip`. Zooms, blurs and markers aren't listed; they stay markers
anyway. Validation checks:
- every template's variables;
- every custom composition, against the house rules;
- that every sound is in the index.

It prints every problem and writes nothing until they're fixed. Keep the
draft: redo changes are made to it, and it's re-stamped each time.

## 6. Render

```bash
python $S/render_graphics.py $G --shoot $W/shoot.json
```

- Run it in the background. A graphic takes a few seconds to render, and
  unchanged cues are reused, so later runs only render what changed.
- For each cue it renders at 60fps (or natively at 24, 30 or 60fps),
  converts to the timeline rate at exactly the cue's frame count, and
  checks that count. Overlays come out as ProRes 4444 with alpha;
  full-frame graphics as 422 HQ.
- It also makes a 720p review proxy over the picture underneath, and
  mixes the SFX stem.
- Everything is recorded in `renders/manifest.json`.
- Don't use `--quality draft` for the review pass. Quality is part of each
  render's identity, so switching back to delivery quality re-renders
  everything and resets its review.

## 7. The review gate

```bash
python $S/review.py serve $G          # in the background; http://127.0.0.1:8765
```

Open the page (in the built-in browser pane if there is one) and hand it
to the user. It lists everything in timeline order. Each graphic shows its
proxy in context, with its brief and the words spoken. Each sound effect
has players for the pick and its alternatives. The user can:
- approve a cue, or send it back with a note;
- choose an alternative sound, which asks for a swap;
- filter to only what still needs a decision;
- approve everything still pending at once.

Wait until the user says they're done, then:

```bash
python $S/review.py status $G        # exit 0 only when everything is approved
python $S/review.py todo $G          # the redo list, with notes and swaps
```

**For each redo, change only that cue:**

| Redo | What to change |
|---|---|
| a templated cue | its `vars` in the draft (or its template, if the note says it's the wrong kind of graphic) |
| a custom cue | edit its composition, then run `custom.py check` again and look at the stills |
| a sound swap (`swap`) | set `file` to the swap, and move the old file into `alternatives` |
| a sound note ("too loud", "later") | adjust `gain_db`. A timing note can't be fixed here, because the frame comes from the plan: say so |

A note asking for a different length or position is also a plan change:
- For a small adjustment, it's easier to nudge the clip in Resolve.
- Otherwise it's the paper edit or director stage, then conform, then here again.

Tell the user which it is. Don't fake a fix.

Then re-stamp (`write_handoff.py`, as in step 5) and render again. Only the
changed cues re-render and go back to pending; approvals on everything else
are kept. Ask the user to reload the page. Repeat until `review.py status`
exits 0.

**Never edit `renders/manifest.json` or `graphics.json` by hand.** Review
decisions are made on the page; spec changes go through the draft and
`write_handoff.py`.

Stop the review server when the gate is passed.

## 8. Report back

Give the user:
- how many graphics were rendered (templated and custom) and how many
  sound effects were mixed;
- what was skipped, and why;
- that everything is approved;
- where the files are: `$G/renders/`, `$G/sfx/sfx_stem.wav`, and the
  manifest.

Next is **assemble**, which places the renders and the stem and refuses to
run while anything is unapproved.
