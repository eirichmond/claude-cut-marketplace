// Key-term caption: an accent chip, top centre, naming the term being said.
// Ported from the MCP video.
import { page, esc, role, timing } from "../lib.mjs";

export const variables = {
  term: { type: "string", required: true, label: "The term, e.g. MCP or .mcp.json" },
  note: { type: "string", required: false, label: "Small mono note above, e.g. Key term" },
  code: { type: "boolean", required: false, label: "Set the term as code (mono, case kept)" },
};
export const layer = "overlay";

export function render({ identity: id, cue, dur, term, note, code = false }) {
  const css = `
  .kt { position: absolute; left: 0; right: 0; top: 5.5cqw; display: flex; justify-content: center; }
  .chip { position: relative; background: var(--accent); color: var(--background);
          padding: 1.15cqw 2.3cqw 1.35cqw; display: flex; flex-direction: column; align-items: center; }
  .note { ${role(id, "label", { cqw: 1.05 })} color: var(--on-accent-muted); margin-bottom: 0.4cqw; }
  .term { ${role(id, "h2", { cqw: 4.2, lineHeight: 1, tracking: "-0.03em", lower: false })} }
  .term.code { ${role(id, "label", { cqw: 3.4, upper: false, tracking: "-0.01em", weight: 500 })} }
  `;
  const html = `
      <div class="kt"><div class="mask"><div class="chip">
        ${note ? `<div class="note">${esc(note)}</div>` : ""}
        <div class="term${code ? " code" : ""}">${esc(term)}</div>
      </div></div></div>`;
  const { k } = timing(dur, 0.45, 0.35);
  const js = `
        tl.fromTo(q(".chip"), { yPercent: 105 }, { yPercent: 0, duration: ${0.45 * k}, ease: "expo.out" }, 0);
        tl.to(q(".chip"), { yPercent: 105, duration: ${0.3 * k}, ease: "power3.in" }, ${Math.max(dur - 0.35 * k, 0.55 * k)});`;
  return page({ identity: id, id: cue.replace(/\./g, "-"), dur, overlay: true, css, html, js,
                title: `Key term ${cue}` });
}
