# One-off (custom) compositions

Templates come first: a chapter card, lower third, callout, tag, key term or
warning strip is always a template entry in `graphics.json`. A cue gets its
own composition only when no template can carry its brief. That's usually
an `mg` cue (a terminal moment, a diagram, a stat, a stamp), and sometimes a
callout whose brief needs a picture rather than words.

A custom composition is one HTML file, `compositions/<cue>.html`, inside the
graphics project, listed in `graphics.json` as:

```json
{ "cue": "b01.mg1", "template": "custom", "composition": "compositions/b01.mg1.html" }
```

It renders through the same path as a template: HyperFrames at 60fps (or
the timeline rate if that's 24/30/60), converted to the cue's exact frame
count, ProRes 4444 with alpha for overlays, 422 HQ for full-frame. It then
goes through the same review gate.

## The loop, per cue

`$S` is the plugin's `scripts/` folder and `$G` is the graphics project.

1. **Read the brief:** `python $S/custom.py brief $G <cue>`. It gives the
   brief, the words spoken over it, the exact length (frames, fps,
   seconds), overlay or full frame, what's underneath, and the identity's
   colour and type names.
2. **Scaffold:** `python $S/custom.py new $G <cue>`. It writes the house shell
   at the exact length with a placeholder design. It won't replace an
   existing file without `--force`.
3. **Author the design** in that file, using the HyperFrames skills in the
   graphics project:
   - `hyperframes-core`: the composition contract (read its "agent
     pitfalls" and "first-pass lint gotchas" first);
   - `hyperframes-animation`: GSAP motion and scene blueprints;
   - `motion-graphics`: design craft for a short, motion-led graphic;
   - `hyperframes-creative`: reads `frame.md`, which `identity.py
     install` put at the project root, so it sees the same identity.

   Keep the shell (see the house rules below) and replace the placeholder
   CSS, HTML and timeline. **Delete the `claude-cut:scaffold` line** when
   the design is real.
4. **Check:** `python $S/custom.py check $G <cue>`. This runs the house
   rules, then HyperFrames' own `check` (lint, runtime, layout, contrast)
   on the composition by itself, then writes stills at 25%, 50% and 80% of
   its length (or `--at 0.4,1.2`) to `review/stills/<cue>/`. Overlays are
   composited over the picture underneath them.
5. **Look at the stills** (Read the PNGs). Fix and re-check until it
   passes and looks right: readable at 1080p, on-identity, nothing clipped,
   and the timing lands on the words.
6. List it in `graphics.json` and render with `render_graphics.py`. The
   review page is where the user judges it in motion.

**A redo note on a custom cue:** edit its composition (steps 3 to 5 only),
then `render_graphics.py --only <cue>`. Nothing else re-renders.

## House rules

`custom.py check` and `validate.py` both enforce these, so `graphics.json`
won't validate while any composition breaks one.

- **The scaffold marker is gone.**
- **One composition root**, with `data-composition-id`,
  `data-width="1920" data-height="1080"`, and a `data-duration` that is
  **exactly** the cue's length, in seconds, to six places. The plan fixed
  the length; the design fits the length, never the other way round.
- **One paused GSAP timeline, registered** as
  `window.__timelines["<composition id>"]`.
- **Overlays are transparent:** `html, body { background: transparent }`,
  with no full-frame fill, so the picture shows through. Full-frame
  graphics fill with `var(--background)` (or another identity colour).
- **Nothing is fetched from the network.** GSAP is `../vendor/gsap.min.js`
  and fonts are `../fonts/…`. Put any image, SVG or clip the design needs
  in `graphics/assets/` and use it as `../assets/<file>`. Every local file
  referenced must exist.
- **The identity only.** Colours are `var(--name)` from frame.md
  (`background`, `accent`, `text`…), and literal values are allowed only
  if they're in its palette. Type comes from frame.md's roles and font
  families (Anton, DM Mono). Don't define new CSS custom properties.
  - **A brief that names a colour** ("a red stamp") gets the identity's
    equivalent (the accent) in place of the literal colour. The identity
    wins.

## HyperFrames layout checks and deliberate layering

HyperFrames' layout pass treats text overlapping text as an error. When the
overlap is the design (a stamp over a terminal, a label over a chart), mark
the specific elements, never a wrapper:

- `data-layout-ignore` goes on decorative text that's never meant to be read,
  such as blurred terminal lines;
- `data-layout-allow-occlusion` goes on an element that is meant to cover text;
- `data-layout-allow-overlap` goes on a text block deliberately layered on another;
- `data-layout-allow-overflow` is for entrance or exit travel outside a clipping box.

Only mark something after a still shows the layering is intended.

## Design notes for this channel

- Compositions are authored at 1920×1080 in `cqw` units and supersampled
  to 4K. Size type with the frame.md roles, e.g. `h1` is 7.5cqw.
- A full-frame `mg` cue replaces the talking head for its length. Get in
  fast (under 0.5s), hold what matters, and clear in the last 0.2 to 0.4s.
- An overlay sits on the talking head or a screen recording. Keep it to a
  corner or a band, and keep faces and the centre of the frame clear (the
  brief says what's underneath).
- Motion should be deterministic. There's no `Math.random` without a seed,
  no clocks, and no infinite repeats.
- **Example:** `graphics/examples/access-stamp.html` is a 2s full-frame cold
  open: a blurred SSH terminal with an ACCESS stamp slamming on. It shows the
  shell, identity-only colours, the layering markers, and a timeline that
  ends inside its length.
