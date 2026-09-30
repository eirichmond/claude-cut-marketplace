// Fast horizontal slide: an accent panel with a label crossing the frame.
// Made for the v0.6 spike, to judge judder of fast motion rendered at 60fps
// and converted to a 25fps timeline; also usable as a wipe.
import { page, esc, role } from "../lib.mjs";

export const variables = {
  text: { type: "string", required: true, label: "Label on the panel" },
  cross: { type: "number", required: false, label: "Seconds to cross the frame (default 0.6)" },
};
export const layer = "overlay";

export function render({ identity: id, cue, dur, text, cross = 0.6 }) {
  const css = `
  .bar { position: absolute; top: 38cqh; left: 0; height: 24cqh; width: 46cqw;
         background: var(--accent); display: flex; align-items: center; padding: 0 3cqw; }
  .bar span { ${role(id, "h1", { cqw: 6.5 })} color: var(--background); white-space: nowrap; }
  .stripe { position: absolute; top: 64cqh; left: 0; height: 1cqh; width: 30cqw; background: var(--text); }
  `;
  const html = `
      <div class="bar"><span>${esc(text)}</span></div>
      <div class="stripe"></div>`;
  const start = Math.max(0, (dur - cross) / 2);
  const js = `
        tl.fromTo(q(".bar"), { x: -900 }, { x: 1920, duration: ${cross}, ease: "none" }, ${start});
        tl.fromTo(q(".stripe"), { x: 1920 }, { x: -600, duration: ${cross}, ease: "none" }, ${start});`;
  return page({ identity: id, id: cue.replace(/\./g, "-"), dur, overlay: true, css, html, js,
                title: `Slide ${cue}` });
}
