// Callout: a compact background block in a corner with a kicker and a short
// statement, or a code snippet (mono, case kept). Ported from the MCP video.
import { page, esc, inline, role, timing, CORNERS } from "../lib.mjs";

export const variables = {
  kicker: { type: "string", required: true, label: "Eyebrow, e.g. Key point" },
  text: { type: "string", required: true, label: "The callout; *accent*, `code`" },
  code: { type: "boolean", required: false, label: "Set the text as code (mono, case kept)" },
  pos: { type: "enum", values: ["bl", "br", "tl", "tr"], required: false, label: "Corner (default bl)" },
};
export const layer = "overlay";

export function render({ identity: id, cue, dur, kicker, text, code = false, pos = "bl" }) {
  const origin = pos.endsWith("r") ? "right" : "left";
  const css = `
  .co { position: absolute; ${CORNERS[pos]} max-width: 70cqw; }
  .panel { position: absolute; inset: 0; background: var(--background); transform-origin: ${origin} center; }
  .inner { position: relative; padding: 1.55cqw 2.3cqw 1.75cqw 2.1cqw; }
  .kicker { ${role(id, "label", { cqw: 1.05 })} color: var(--accent); margin-bottom: 0.65cqw; display: flex; align-items: center; gap: 0.85cqw; }
  .kicker .rule { width: 2.1cqw; height: 4px; }
  .text { ${role(id, "h3", { cqw: 2.6, lineHeight: 1.1, tracking: "-0.02em" })} color: var(--text); }
  .code { ${role(id, "label", { cqw: 2.1, upper: false, tracking: "0", weight: 500 })} color: var(--text); }
  `;
  const body = code ? `<div class="code">${inline(text)}</div>`
                    : `<div class="text">${inline(text)}</div>`;
  const html = `
      <div class="co">
        <div class="panel"></div>
        <div class="inner">
          <div class="mask"><div class="kicker"><span class="rule"></span><span>${esc(kicker)}</span></div></div>
          <div class="mask">${body}</div>
        </div>
      </div>`;
  const { k } = timing(dur, 0.8, 0.45);
  const out = Math.max(dur - 0.45 * k, 0.8 * k + 0.1);
  const back = origin === "left" ? "right" : "left";
  const js = `
        tl.fromTo(q(".panel"), { scaleX: 0 }, { scaleX: 1, duration: ${0.45 * k}, ease: "power4.out" }, 0);
        tl.fromTo(q(".kicker"), { yPercent: 110 }, { yPercent: 0, duration: ${0.4 * k}, ease: "expo.out" }, ${0.15 * k});
        tl.fromTo(q(".rule"), { scaleX: 0 }, { scaleX: 1, duration: ${0.35 * k}, ease: "power3.out" }, ${0.2 * k});
        tl.fromTo(q(".text, .code"), { yPercent: 105 }, { yPercent: 0, duration: ${0.55 * k}, ease: "expo.out" }, ${0.22 * k});
        tl.to(q(".inner"), { opacity: 0, duration: ${0.18 * k}, ease: "none" }, ${out});
        tl.set(q(".panel"), { transformOrigin: "${back} center" }, ${out + 0.08 * k});
        tl.to(q(".panel"), { scaleX: 0, duration: ${0.35 * k}, ease: "power4.in" }, ${out + 0.08 * k});`;
  return page({ identity: id, id: cue.replace(/\./g, "-"), dur, overlay: true, css, html, js,
                title: `Callout ${cue}` });
}
