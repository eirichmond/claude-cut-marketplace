// Warning strip: a full-width accent band that slides over the picture.
// Ported from the MCP video.
import { page, esc, inline, role, timing } from "../lib.mjs";

export const variables = {
  kicker: { type: "string", required: true, label: "Eyebrow, e.g. Warning" },
  head: { type: "string", required: true, label: "The warning (lowercase display)" },
  line: { type: "string", required: false, label: "Detail; `code` allowed" },
};
export const layer = "overlay";

export function render({ identity: id, cue, dur, kicker, head, line }) {
  const css = `
  .strip { position: absolute; left: 0; right: 0; bottom: 8cqw; background: var(--accent); color: var(--background);
           padding: 2.3cqw 5.5cqw 2.5cqw; }
  .kicker { ${role(id, "label", { cqw: 1.15 })} color: var(--background); margin-bottom: 0.85cqw; display: flex; gap: 0.85cqw; align-items: center; }
  .kicker .rule { background: var(--background); width: 2.1cqw; }
  .head { ${role(id, "h1", { cqw: 5.2, lineHeight: 0.95 })} }
  .line { ${role(id, "lead", { cqw: 1.9, lineHeight: 1.35 })} margin-top: 0.85cqw; color: var(--background); }
  .line em, .head em { color: var(--background); text-decoration: underline; }
  .inner { position: relative; }
  `;
  const html = `
      <div class="strip">
        <div class="inner">
          <div class="mask"><div class="kicker"><span class="rule"></span><span>${esc(kicker)}</span></div></div>
          <div class="mask"><div class="head">${esc(head)}</div></div>
          ${line ? `<div class="mask"><p class="line">${inline(line)}</p></div>` : ""}
        </div>
      </div>`;
  const { k } = timing(dur, 0.95, 0.55);
  const js = `
        tl.fromTo(q(".strip"), { xPercent: -101 }, { xPercent: 0, duration: ${0.5 * k}, ease: "power4.out" }, 0);
        tl.fromTo(q(".kicker"), { yPercent: 110 }, { yPercent: 0, duration: ${0.4 * k}, ease: "expo.out" }, ${0.25 * k});
        tl.fromTo(q(".head"), { yPercent: 105 }, { yPercent: 0, duration: ${0.6 * k}, ease: "expo.out" }, ${0.3 * k});
        if (q(".line")) tl.fromTo(q(".line"), { yPercent: 110 }, { yPercent: 0, duration: ${0.5 * k}, ease: "power3.out" }, ${0.45 * k});
        tl.to(q(".inner"), { opacity: 0, duration: ${0.2 * k}, ease: "none" }, ${Math.max(dur - 0.55 * k, 1.0 * k)});
        tl.to(q(".strip"), { xPercent: 101, duration: ${0.45 * k}, ease: "power4.in" }, ${Math.max(dur - 0.45 * k, 1.1 * k)});`;
  return page({ identity: id, id: cue.replace(/\./g, "-"), dur, overlay: true, css, html, js,
                title: `Warning ${cue}` });
}
