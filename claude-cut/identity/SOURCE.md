# Where `frame.md` came from

`identity/frame.md` is Elliott Richmond's own derivative of a Broadside frame pack, adopted
2026-09-29 for claude-cut v0.6.

- **Original:** `/Volumes/Terrance/assets/broadside-frame-pack/FRAME.md`
- **sha256:** `fe8fa7e111c5` (first 12; the pack also sits at `~/Downloads/broadside-frame-pack/`)
- **Based on:** HyperFrames' `broadside` frame preset, recoloured to cyan on navy with Anton and DM Mono.

## What changed

**Names, not values.** Colour tokens were renamed to semantic names; every value is identical.

| Semantic (this file) | Broadside original | Value |
|---|---|---|
| `background` | `ink-black` | `#0D1F28` |
| `background-alt` | `ink-black-alt` | `#1A1A18` |
| `accent` | `fire-orange` | `#00C8E0` |
| `text` | `cream` | `#EFF9FC` |
| `text-muted` | `cream-muted` | `#888880` |
| `text-hint` | `cream-hint` | `#505048` |
| `border` | `border-dark` | `#5AACBD` |
| `on-accent-muted` | `ink-on-orange-muted` | `rgba(13,31,40,0.75)` |
| `on-accent-hint` | `ink-on-orange-hint` | `rgba(13,31,40,0.55)` |
| `on-accent-faint` | `ink-on-orange-faint` | `rgba(13,31,40,0.40)` |
| `on-accent-border` | `ink-on-orange-border` | `rgba(13,31,40,0.20)` |

Registers `dark` / `orange` became `dark` / `accent`; the `broadside-num` component became
`catalogue-num`. The name is "Elliott Richmond — Frame" and the prose uses the semantic names.

**Fonts.** A `fonts:` block names families by role (`display`, `body`, `mono`) and typography roles
reference a role (`font: display`) instead of a family. Anton ships in one weight (400), so every
Anton role is weight 400; the original's 600–900 would make the browser synthesise a fake bold.
DM Mono `label` keeps weight 500.

**Added:** "No em dashes in on-screen text; British spelling" to the Don'ts, and Known Gaps notes
on fonts shipping as files and the Anton body-text review.
