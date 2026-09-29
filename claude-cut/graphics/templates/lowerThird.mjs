// Lower third: background panel, accent kicker, headline, optional line.
// Ported from the MCP video's overlays.mjs, on semantic tokens.
import { page, esc, inline, role, timing } from "../lib.mjs";

export const variables = {
  kicker: { type: "string", required: true, label: "Eyebrow, uppercase mono" },
  head: { type: "string", required: true, label: "Headline; *accent*, `code`" },
  line: { type: "string", required: false, label: "Supporting line (body text); *accent*, `code`" },
};
export const layer = "overlay";

export function render({ identity: id, cue, dur, kicker, head, line }) {
  const css = `
  .lt { position: absolute; left: 5.5cqw; bottom: 5.5cqw; max-width: 62cqw; }
  .panel { position: absolute; inset: 0; background: var(--background); transform-origin: left center; }
  .inner { position: relative; padding: 2.1cqw 2.9cqw 2.3cqw 2.5cqw; }
  .rule { margin-bottom: 1.15cqw; }
  .kicker { ${role(id, "label", { cqw: 1.15 })} color: var(--accent); margin-bottom: 0.85cqw; }
  .head { ${role(id, "h3", { cqw: 3.1, lineHeight: 1.05, tracking: "-0.02em" })} color: var(--text); }
  .line { ${role(id, "lead", { cqw: 1.75, lineHeight: 1.35 })} color: var(--text); margin-top: 0.75cqw; }
  .hair { position: absolute; left: 0; right: 0; top: 0; height: 2px; background: var(--border); transform-origin: left center; }
  `;
  const html = `
      <div class="lt">
        <div class="panel"></div>
        <div class="hair"></div>
        <div class="inner">
          <span class="rule"></span>
          <div class="mask"><div class="kicker">${esc(kicker)}</div></div>
          <div class="mask"><div class="head">${inline(head)}</div></div>
          ${line ? `<div class="mask"><p class="line">${inline(line)}</p></div>` : ""}
        </div>
      </div>`;
  const { k, out } = timing(dur);
  const js = `
        tl.fromTo(q(".panel"), { scaleX: 0 }, { scaleX: 1, duration: ${0.5 * k}, ease: "power4.out" }, 0);
        tl.fromTo(q(".hair"), { scaleX: 0 }, { scaleX: 1, duration: ${0.7 * k}, ease: "power3.out" }, ${0.1 * k});
        tl.fromTo(q(".rule"), { scaleX: 0 }, { scaleX: 1, duration: ${0.4 * k}, ease: "power3.out" }, ${0.2 * k});
        tl.fromTo(q(".kicker"), { yPercent: 110 }, { yPercent: 0, duration: ${0.45 * k}, ease: "expo.out" }, ${0.2 * k});
        tl.fromTo(q(".head"), { yPercent: 105 }, { yPercent: 0, duration: ${0.6 * k}, ease: "expo.out" }, ${0.28 * k});
        if (q(".line")) tl.fromTo(q(".line"), { yPercent: 110 }, { yPercent: 0, duration: ${0.5 * k}, ease: "power3.out" }, ${0.42 * k});
        tl.to(q(".inner"), { opacity: 0, duration: ${0.2 * k}, ease: "none" }, ${out});
        tl.to(q(".hair"), { opacity: 0, duration: ${0.2 * k}, ease: "none" }, ${out});
        tl.set(q(".panel"), { transformOrigin: "right center" }, ${out + 0.1 * k});
        tl.to(q(".panel"), { scaleX: 0, duration: ${0.4 * k}, ease: "power4.in" }, ${out + 0.1 * k});`;
  return page({ identity: id, id: cue.replace(/\./g, "-"), dur, overlay: true, css, html, js,
                title: `Lower third ${cue}` });
}
