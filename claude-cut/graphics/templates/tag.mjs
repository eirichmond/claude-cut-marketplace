// Tag: a small accent chip with mono text, e.g. "Later in the video".
// Ported from the MCP video.
import { page, esc, role, timing, CORNERS } from "../lib.mjs";

export const variables = {
  text: { type: "string", required: true, label: "Short label" },
  pos: { type: "enum", values: ["bl", "br", "tl", "tr"], required: false, label: "Corner (default tr)" },
};
export const layer = "overlay";

export function render({ identity: id, cue, dur, text, pos = "tr" }) {
  const css = `
  .tag { position: absolute; ${CORNERS[pos]} }
  .chip { ${role(id, "label", { cqw: 1.35, weight: 500 })} background: var(--accent); color: var(--background);
          padding: 0.95cqw 1.45cqw 0.95cqw 1.35cqw; display: flex; align-items: center; gap: 0.95cqw; }
  `;
  const html = `
      <div class="tag"><div class="mask"><div class="chip"><span>/</span><span>${esc(text)}</span></div></div></div>`;
  const { k } = timing(dur, 0.45, 0.4);
  const js = `
        tl.fromTo(q(".chip"), { yPercent: 110 }, { yPercent: 0, duration: ${0.45 * k}, ease: "expo.out" }, 0);
        tl.to(q(".chip"), { yPercent: -110, duration: ${0.35 * k}, ease: "power3.in" }, ${Math.max(dur - 0.4 * k, 0.55 * k)});`;
  return page({ identity: id, id: cue.replace(/\./g, "-"), dur, overlay: true, css, html, js,
                title: `Tag ${cue}` });
}
