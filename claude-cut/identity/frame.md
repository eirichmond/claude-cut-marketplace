---
version: alpha
name: Elliott Richmond — Frame (video / frame layer)
description: >
  Elliott Richmond's visual identity for video frames. The unit is the frame (1920×1080). Atoms are
  fixed: the two-register surface system (dark background / accent), massive Anton in lowercase
  treated as graphic primitive, DM Mono chrome (uppercase, 0.14em), the single accent colour, the
  flat plane, and 1px hairline dividers. Composition is free. Motion is defined by the templates,
  not here.
unit: the frame — 1920×1080 primary; 9:16 and 1:1 documented
principle: atoms are fixed · composition is free · numbers come from the script

colors:
  background: "#0D1F28"
  background-alt: "#1A1A18"
  accent: "#00C8E0"
  text: "#EFF9FC"
  text-muted: "#888880"
  text-hint: "#505048"
  border: "#5AACBD"
  on-accent-muted: "rgba(13,31,40,0.75)"
  on-accent-hint: "rgba(13,31,40,0.55)"
  on-accent-faint: "rgba(13,31,40,0.40)"
  on-accent-border: "rgba(13,31,40,0.20)"

fonts:
  display: "Anton"
  body: "Anton"
  mono: "DM Mono"

typography:
  # — reading ramp —
  body:    { font: body, cqw: 1.2, weight: 400, lineHeight: 1.6 }
  lead:    { font: body, cqw: 1.6, weight: 400, lineHeight: 1.5 }
  caption: { font: body, cqw: 0.9, weight: 400, lineHeight: 1.5 }
  label:   { font: mono, cqw: 0.72, weight: 500, tracking: "0.14em", upper: true }
  # — display / hero ramp (Anton, lowercase, negative tracking) —
  h3:      { font: display, cqw: 2.8, weight: 400, lineHeight: 1.2, lower: true }
  quote-text: { font: display, cqw: 3.8, weight: 400, lineHeight: 1.15, tracking: "-0.02em", lower: true }
  h2:      { font: display, cqw: 4.5, weight: 400, lineHeight: 1.1, tracking: "-0.02em", lower: true }
  stat-value: { font: display, cqw: 5.5, weight: 400, lineHeight: 1.0, tracking: "-0.04em" }
  h1:      { font: display, cqw: 7.5, weight: 400, lineHeight: 0.9, tracking: "-0.03em", lower: true }
  fadelist-item: { font: display, cqw: 7.5, weight: 400, lineHeight: 1.0, tracking: "-0.03em", lower: true }
  quote-mark: { font: display, cqw: 10.0, weight: 400, lineHeight: 0.6 }
  fadelist-title: { font: display, cqw: 10.5, weight: 400, lineHeight: 0.9, tracking: "-0.04em", lower: true }
  display: { font: display, cqw: 13.0, weight: 400, lineHeight: 0.88, tracking: "-0.04em", lower: true }

spacing:
  pad-x: "5.5cqw"
  pad-y: "5.5cqw"
  gap-lg: "3.5cqw"
  gap-md: "2cqw"
  gap-sm: "1cqw"

components:
  registers:
    dark: "ground {colors.background}, text {colors.text}, accent {colors.accent}"
    accent: "ground {colors.accent}, text {colors.background}"
    description: "Two surfaces only — no light/paper register. One register per frame."
  slide-chrome:
    rule: "1px solid {colors.border} (dark) / {colors.on-accent-border} (accent)"
    placement: "top + bottom bars (label left, number right)"
    description: "SUPPRESSED on cover/chapter/statement/quote/end — declarative frames let type fill the field."
  kicker:
    typography: "{typography.label}"
    color: "{colors.accent} (dark) / {colors.on-accent-hint} (accent)"
    description: "Uppercase mono eyebrow."
  rule:
    backgroundColor: "{colors.accent} (dark) / {colors.background} (accent)"
    size: "36×2px"
    description: "Stub accent bar — the system's only ornament."
  catalogue-num:
    typography: "{typography.label}"
    placement: "top-left of accent cover/chapter, low opacity"
    description: "Mono catalogue numeral."
  stat-card:
    borderTop: "1px solid {colors.border}"
    typography: "{typography.stat-value} (accent on dark / background on accent) + {typography.body} + {typography.label}"
    description: "Top-border-only block, no other borders."
  bullet:
    marker: "accent `/` mono via ::before"
    typography: "{typography.lead}"
    description: "Capped at THREE items."
  bar-track:
    borderLeft: "1px solid {colors.border}"
    bars: "{colors.text-hint}, one .accent {colors.accent}"
    typography: "{typography.label} axis"
    description: "Vertical bar chart, left axis only."
  compare-panel:
    layout: "two equal panels split by a 1px vertical rule"
    payoff: "right panel may fill {colors.accent}"
    description: "Before/after."
  fadelist:
    typography: "{typography.fadelist-item} ×3 at opacity 1.0/0.5/0.22 + {typography.fadelist-title}"
    description: "Three stacked words + one oversized title opposite."
---

# Elliott Richmond — Frame (video / frame layer)

## Overview

At frame scale this is a **poster system where type is so large it stops reading as text and
becomes graphic primitive.** Anton `display` at 13cqw puts a single lowercase word nearly across the
frame. The system runs in **two registers**: a dark `background` ground with `text` for
documentation, and an `accent` ground with `background`-coloured ink for declaration. The accent is
the *only* colour: accent on dark, environment on the accent register. The plane is flat; hierarchy
is size, case and 1px hairlines.

**Anton** carries every text role from display to body. It has a single weight, so range comes from
size, case and colour, not weight. **DM Mono** is chrome only (numbers, kickers, tags, axis labels,
the `/` bullet marker), always uppercase and tracked. Display is **lowercase**, the system's most
distinctive single decision.

**Key characteristics at frame scale:**
- **Two registers**: dark (`text` on `background`) / accent (`background` on `accent`). No light/paper register.
- **Massive lowercase Anton**, negative-tracked, as graphic primitive (display 13cqw).
- **The accent is the only colour**: accent on dark, full environment on the accent register.
- **DM Mono chrome**: uppercase, 0.14em; the `/` bullet marker; mono catalogue numbers.
- **Flat plane**: no shadow, no radius (save nav dots), no gradient; 1px hairlines carry structure.
- **Low density**: one statement per frame, bullets capped at three, chrome suppressed on declarative frames.

## The Frame

### Frame Craft Bar
Eyeball tests gate every frame before any structural check:
- **Squint**: exactly **one display moment dominates** at 3–6× everything else; nothing competes.
- **Silence**: declarative frames read **45–55% empty**; the **stat grid is the one dense exception**.
- **Restraint**: **one register per frame**; **the accent is the only colour**; one display moment; bullets capped at three.
- **Reference**: aim at **broadside printing / a SPACE10 report / a Wim Crouwel grid with one loud colour**; failure looks like a **multi-accent corporate slide deck**.

- **Primary:** 1920×1080 (16:9). Type authored in **`cqw`** (`px ÷ 1920 × 100 = cqw`).
- **Vertical:** 1080×1920 (9:16). **Square:** 1080×1080 (1:1).
- **Safe area:** `pad-x`/`pad-y` 5.5cqw, deliberately tight so the massive type crowds the frame edge.

**The container law (load-bearing).** Every frame ground sets `container-type: size`; ALL
frame-relative units are `cqw`/`cqh` against it, never `vw` (a `vw`-sized frame inflates when not
full-screen). 1px hairlines stay 1px.

## Colors

Two registers. **Dark:** `{colors.background}` ground, `{colors.text}` text, `{colors.accent}`
accent (kickers, accent stat, bullet `/`, lead bar, quote mark, rule stub). **Accent:**
`{colors.accent}` ground, `{colors.background}` headlines and body, with the `on-accent`
overlays (75/55/40/20%) as the muted tones. Choose one register per frame and commit. **No second
accent colour**: on the accent register, emphasis is size or opacity on the ink, never a new hue.
`text` on `accent` does not exist (background-on-accent is absolute).

## Typography

Two ramps. The **reading ramp** (`body` 1.2cqw, mono `label` 0.72cqw) carries copy and chrome; the
**display ramp** (`h2` 4.5cqw → `display` 13cqw) carries every statement. Roles name a font by
role (`display`, `body`, `mono`) from the `fonts` block, never by family.

- **Legibility floor:** any load-bearing line ≥ **1.4cqw**; mono labels are chrome only.
- **Fit-to-measure:** size the headline to its length. Cap the block at **≤ 78cqw**; ≤2 words → `display`; 3–4 → `h1`; 5+ → `h2`. Only ONE display moment per frame.
- **Display is lowercase and negative-tracked** (−0.04em largest, −0.02em h2). **Mono chrome is uppercase, 0.1em+.** No italic, no underline, no uppercase display.

## Depth & Surface

Flat plane, the only technique. Hierarchy from:
- **Size and case contrast**: the dominant signal (massive lowercase display).
- **1px hairlines**: chrome bars, stat-card top, compare divider, bar-track left, chart baseline.
- **Colour shift**: accent on background, background on accent, muted text on text.
- **Negative space**: generous, intentional empty regions.

**Ceiling:** no box-shadow, no elevation, no rounded surface (save nav dots), no gradient ground.

## Shapes

- **0 radius everywhere** except nav dots (50%). Cards, panels, tags, stat blocks, bars: sharp rectangles.

## Components

- **registers**: the two-surface system. **slide-chrome**: optional hairline bars, suppressed on declarative frames.
- **kicker** (mono eyebrow) / **rule** (36×2 stub) / **catalogue-num** (catalogue mark): the chrome ornament set.
- **stat-card** (top-border only) / **bullet** (accent `/`, max 3) / **bar-track** (one accent bar) / **compare-panel** (accent payoff) / **fadelist** (1.0/0.5/0.22 stack).

## Frame Treatments

> Recipe: ground · register · composes · focal · chrome · accent · silence · Fixed/Free · density.
> One statement per frame; chrome suppressed on declarative frames.

### 1 · Cover  (identity · move: massive type · ACCENT register · left)
**Ground** accent. **Composes** catalogue-num, rule, kicker, display, lead. **Focal** a 1–2 word
`display` (13cqw) lowercase in background ink, left-anchored, over a small rule stub and mono kicker;
a lead line beneath in `on-accent-muted`. **Chrome** mono catalogue number top-left, mono meta
top-right (no chrome bars). **Accent** the ink itself is the pop on the accent. **Silence** ~45%.
**Fixed** background-on-accent, lowercase, flat. **Free** the word, kicker, lead. **Density** low.

### 2 · Statement  (declarative · move: type IS composition · DARK register · left)
**Ground** background. **Composes** kicker, display. **Focal** a 2–4 word `display`/`h1` lowercase in
`text`, with ONE clause in `{colors.accent}`. **Chrome** mono kicker; no bars. **Accent** the accent
clause. **Silence** ~55%. **Fixed** lowercase, one accent clause, flat. **Free** the statement, which
clause is accented. **Density** low.

### 3 · Stat Grid  (data · move: top-border cards · DARK · the dense frame)
**Ground** background, chrome bars present. **Composes** slide-chrome, kicker, 3× stat-card. **Focal**
a row of three top-border-only stat-cards: big numeral in `{colors.accent}`, body label, mono note.
**Chrome** top + bottom hairline bars (label + number). **Accent** the accent numerals. **Silence**
moderate, the density exception. **Fixed** top-border-only cards, accent numerals, 1px hairlines.
**Free** figures (from script), labels. **Density** dense-exception.

### 4 · Fadelist  (narrative · move: opacity stack · DARK)
**Ground** background. **Composes** fadelist (3 stacked words at 1.0/0.5/0.22), fadelist-title.
**Focal** the three-stage word stack opposite an oversized display title in `{colors.accent}`
(before/during/after). **Accent** the accent title. **Silence** moderate. **Fixed** the opacity
ladder, lowercase. **Free** the three words, the title. **Density** low-moderate.

### 5 · Pull Quote  (quote · move: oversized mark · DARK · left)
**Ground** background, chrome suppressed. **Composes** quote-mark, quote-text, attribution. **Focal**
a `quote-text` (lowercase) at ≤78cqw under an oversized accent `quote-mark` (10cqw, line-height
0.6). **Chrome** mono attribution (name + role). **Accent** the accent quote mark. **Silence** ~50%.
**Fixed** accent mark, lowercase quote. **Free** quote, attribution. **Density** low.

### 6 · Compare  (argument · move: split + accent payoff · DARK→ACCENT)
**Ground** background left panel + accent right (payoff) panel, 1px divider. **Composes**
compare-panel pair, kicker, h3. **Focal** two panels: left documents (text on background), right
declares (background on accent). **Chrome** mono panel labels. **Accent** the accent payoff panel.
**Silence** moderate. **Fixed** background-on-accent right panel, 1px divider, flat. **Free** the
before/after content. **Density** standard.

## Composition Rules

### Do
- Set every display line in **lowercase Anton**, negative-tracked: the system's signature.
- Use **the accent as full environment** on declarative frames, the **lone accent** on dark.
- Keep chrome in **DM Mono uppercase, 0.14em**; use the `/` mono bullet marker.
- **Cap bullets at three; one statement per frame**; build hierarchy from size, case and 1px hairlines.
- Suppress chrome bars on cover/chapter/statement/quote/end; let type fill the field.
- Lean left on most frames; the type IS the composition.

### Don't
- Never uppercase display; never add a second accent colour.
- Never put `text` on `accent` (background-on-accent is absolute); never a light/paper register.
- No drop shadow, no rounded surface (save nav dots), no gradient ground.
- No serif companion; chrome is never Anton.
- Don't pack two display moments into one frame; don't blow a long line edge-to-edge: step down.
- No em dashes in on-screen text; British spelling.

## Aspect-Ratio Behavior

| Treatment | 16:9 | 9:16 | 1:1 |
|---|---|---|---|
| Cover | word left, lead below | word top, lead below | centered word |
| Statement | display left | display stacked taller | display centered |
| Stat Grid | 3 across | 3 stacked | 2+1 |
| Fadelist | stack + title side-by-side | stack over title | stack over title |
| Pull Quote | mark + quote left | mark top, quote below | centered |
| Compare | side-by-side panels | stacked (dark over accent) | stacked |

`pad-x` holds tight on the short edge; re-step display so the one big line stays ≤78cqw and above the
1.4cqw floor. Mono chrome stays Latin/digit-only.

## Approved Entities

No real customers, logos, or vendors are defined here: render any such mark as a placeholder (the
dashed `img-placeholder` at 55cqh). The system supplies type and one colour, not brands.

## Numerals & Claims (hard rule)

Never invent figures, percentages, dates, or counts at frame scale. Render slots as `— figure —`,
`{metric}`, `NN%`. Stat-card numerals and bar heights carry placeholders until the script supplies
them. Catalogue numbers (No. 01) are decorative chrome and may be sequential.

## Pre-Render Self-Audit

- **Squint**: exactly one display moment dominates; nothing competes.
- **Silence**: declarative frames ~45–55% empty; only the stat grid runs dense.
- **Register**: one register per frame; background-on-accent on the accent register, text on dark; no second hue.
- **Type**: Anton lowercase negative-tracked, fit-to-measure; mono chrome uppercase 0.14em; ≥1.4cqw floor.
- **Depth**: 0 shadow, 0 radius (save nav dots); 1px hairlines only.
- **Bullets**: capped at three, accent `/` marker.
- **Fabrication**: every numeral traces to the script, else placeholder.

## Known Gaps

- **Motion is defined by the claude-cut templates**, not by this file.
- **Fonts ship as files** in `identity/fonts/` (Anton, DM Mono); nothing is fetched at render time.
- **Anton as body text is under review** (v0.6 spike): if it isn't readable at body sizes, `fonts.body` switches to a readable face defined here.
- **9:16 / 1:1 are guidance**; verify the one big line stays ≤78cqw and above the floor per ratio.
