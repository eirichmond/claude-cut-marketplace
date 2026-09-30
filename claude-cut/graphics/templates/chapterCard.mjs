// Chapter card: the accent register as a full-frame "cover" that wipes on
// over whatever is underneath and off again. Ported from the MCP video.
import { page, esc, inline, role, timing } from "../lib.mjs";

export const variables = {
  num: { type: "string", required: true, label: "Chapter number, e.g. 01" },
  kicker: { type: "string", required: true, label: "Eyebrow, e.g. Step one" },
  title: { type: "string", required: true, label: "Chapter title (lowercase display)" },
  lead: { type: "string", required: false, label: "One supporting line" },
  meta: { type: "string", required: false, label: "Top-right mono meta, e.g. Step 01 / 05" },
};
export const layer = "overlay";

export function render({ identity: id, cue, dur, num, kicker, title, lead, meta }) {
  const big = title.trim().split(/\s+/).length <= 2;
  const css = `
  .ground { position: absolute; inset: 0; background: var(--accent); transform-origin: left center; }
  .num, .meta { position: absolute; top: 5.5cqw; color: var(--background); ${role(id, "label", { cqw: 1.15 })} }
  .num { left: 5.5cqw; } .meta { right: 5.5cqw; }
  .block { position: absolute; left: 5.5cqw; bottom: 5.5cqw; width: 78cqw; color: var(--background); }
  .rule { background: var(--background); margin-bottom: 1.45cqw; }
  .kicker { ${role(id, "label", { cqw: 1.25 })} color: var(--background); margin-bottom: 1.15cqw; }
  .title { ${role(id, big ? "display" : "h1")} color: var(--background); }
  .lead { ${role(id, "lead", { cqw: 1.9, lineHeight: 1.4 })} color: var(--on-accent-muted); margin-top: 1.75cqw; }
  .lead em { color: var(--background); }
  .content { position: absolute; inset: 0; }
  `;
  const html = `
      <div class="ground"></div>
      <div class="content">
        <div class="num">No. ${esc(num)}</div>
        ${meta ? `<div class="meta">${esc(meta)}</div>` : ""}
        <div class="block">
          <span class="rule"></span>
          <div class="mask"><div class="kicker">${esc(kicker)}</div></div>
          <div class="mask"><h1 class="title">${esc(title)}</h1></div>
          ${lead ? `<div class="mask"><p class="lead">${inline(lead)}</p></div>` : ""}
        </div>
      </div>`;
  const { k } = timing(dur, 0.9, 0.55);
  const out = Math.max(dur - 0.55 * k, 0.9 * k + 0.1);
  const js = `
        tl.fromTo(q(".ground"), { scaleX: 0 }, { scaleX: 1, duration: ${0.45 * k}, ease: "power4.inOut" }, 0);
        tl.fromTo(q(".rule"), { scaleX: 0 }, { scaleX: 1, duration: ${0.4 * k}, ease: "power3.out" }, ${0.3 * k});
        tl.fromTo(q(".kicker"), { yPercent: 110 }, { yPercent: 0, duration: ${0.45 * k}, ease: "expo.out" }, ${0.32 * k});
        tl.fromTo(q(".title"), { yPercent: 105 }, { yPercent: 0, duration: ${0.7 * k}, ease: "expo.out" }, ${0.36 * k});
        if (q(".lead")) tl.fromTo(q(".lead"), { yPercent: 110 }, { yPercent: 0, duration: ${0.5 * k}, ease: "power3.out" }, ${0.5 * k});
        tl.fromTo(qa(".num, .meta"), { opacity: 0 }, { opacity: 1, duration: ${0.3 * k}, ease: "none" }, ${0.4 * k});
        tl.to(q(".content"), { y: -40, opacity: 0, duration: ${0.25 * k}, ease: "power2.in" }, ${out});
        tl.set(q(".ground"), { transformOrigin: "right center" }, ${out + 0.1 * k});
        tl.to(q(".ground"), { scaleX: 0, duration: ${0.45 * k}, ease: "power4.inOut" }, ${out + 0.1 * k});`;
  return page({ identity: id, id: cue.replace(/\./g, "-"), dur, overlay: true, css, html, js,
                title: `Chapter ${num}` });
}
