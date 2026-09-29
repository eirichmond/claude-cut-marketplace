// The composition shell every claude-cut graphic is built on.
//
// Ported from the MCP video's hand-built motion-graphics project
// (build/lib.mjs), with the identity taken from the project's identity.json
// (written by scripts/identity.py from identity/frame.md) instead of
// constants. Templates use semantic names only: var(--accent), role("h1")...
//
// Compositions are authored at 1920x1080 in cqw units and supersampled to
// the timeline's size at render time.

export const W = 1920;
export const H = 1080;

// Escape text for HTML. `*word*` marks an accented clause in headlines.
export const esc = (s) =>
  String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
export const accented = (s) => esc(s).replace(/\*(.+?)\*/g, "<em>$1</em>");

function fontFaces(id) {
  const faces = [];
  for (const [family, weights] of Object.entries(id.font_files)) {
    for (const [weight, file] of Object.entries(weights)) {
      faces.push(`@font-face { font-family: "${family}"; font-weight: ${weight}; ` +
                 `font-style: normal; font-display: block; src: url("../fonts/${file}") format("woff2"); }`);
    }
  }
  return faces.join("\n");
}

function colorVars(id) {
  return Object.entries(id.colors).map(([k, v]) => `--${k}: ${v};`).join(" ");
}

// CSS declarations for a type role from frame.md, with optional overrides
// (e.g. role(id, "lead", { cqw: 1.75 })).
export function role(id, name, over = {}) {
  const r = { ...id.typography[name], ...over };
  if (!r.family) throw new Error(`frame.md has no typography role "${name}"`);
  const out = [`font-family: "${r.family}"`, `font-weight: ${r.weight ?? 400}`];
  if (r.cqw) out.push(`font-size: ${r.cqw}cqw`);
  if (r.lineHeight) out.push(`line-height: ${r.lineHeight}`);
  if (r.tracking) out.push(`letter-spacing: ${r.tracking}`);
  if (r.upper) out.push("text-transform: uppercase");
  if (r.lower) out.push("text-transform: lowercase");
  return out.join("; ") + ";";
}

/**
 * page({ identity, id, dur, overlay, css, html, js, title })
 * js runs inside an IIFE with: R (root), q/qa (scoped query), tl (paused timeline).
 * dur is seconds: the cue's exact frame count / timeline fps.
 */
export function page({ identity, id, dur, overlay = false, css = "", html, js, title }) {
  const base = `
    position: absolute; inset: 0; width: 100%; height: 100%; overflow: hidden;
    container-type: size;
    ${colorVars(identity)}
    ${role(identity, "body")}
    color: var(--text);
    ${overlay ? "background: transparent;" : "background: var(--background);"}
    -webkit-font-smoothing: antialiased;
    * { box-sizing: border-box; margin: 0; padding: 0; }
    .mono { ${role(identity, "label")} }
    .mask { overflow: hidden; display: block; }
    /* tight display line-heights let descenders hang below the line box,
       where the reveal mask would clip them: pad the masked line */
    .mask > * { display: block; padding-top: 0.06em; padding-bottom: 0.2em; }
    .rule { display: block; width: 72px; height: 4px; background: var(--accent); transform-origin: left center; }
    em { font-style: normal; color: var(--accent); }
  `;
  const GSAP = `<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>`;
  return `<!doctype html>
<html lang="en-GB">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=${W}, height=${H}" />
    <title>${esc(title || id)}</title>
    ${GSAP}
    <style>
      ${fontFaces(identity)}
      html, body { margin: 0; width: ${W}px; height: ${H}px; overflow: hidden;
        background: ${overlay ? "transparent" : identity.colors.background}; }
      #r-${id} {${base}
        ${css}
      }
    </style>
  </head>
  <body>
    <div id="r-${id}" data-composition-id="${id}" data-start="0"
         data-width="${W}" data-height="${H}" data-duration="${dur}">
${html}
    </div>
    <script>
      (function () {
        const R = document.getElementById("r-${id}");
        const q = (s) => R.querySelector(s);
        const qa = (s) => R.querySelectorAll(s);
        const tl = gsap.timeline({ paused: true });
${js}
        window.__timelines["${id}"] = tl;
      })();
    </script>
  </body>
</html>
`;
}

// In/out timing that shrinks for short cues, so nothing is cut mid-move.
export function timing(dur, inFor = 0.7, outFor = 0.6) {
  const scale = Math.min(1, dur / (inFor + outFor + 0.8));
  return { k: scale, out: Math.max(dur - outFor * scale, (inFor * scale) + 0.1) };
}
