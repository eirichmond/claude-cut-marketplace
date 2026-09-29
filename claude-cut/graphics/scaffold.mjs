#!/usr/bin/env node
// A starting point for a one-off (custom) composition: the house shell from
// lib.mjs at the cue's exact length, with a placeholder headline that builds
// on and off. The graphics skill replaces the placeholder with the real
// design (see skills/graphics/references/custom-compositions.md); the
// scaffold marker makes `custom.py check` fail until it has.
//
// Usage:
//   node scaffold.mjs <project dir> <cue> <frames> <fps> <overlay|full> [headline]
// Prints the path written. The caller (scripts/custom.py new) decides
// whether an existing file may be replaced.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { page, esc, role, timing } from "./lib.mjs";

const MARKER = "<!-- claude-cut:scaffold (delete this line once the design is authored) -->";

function scaffold({ identity: id, cue, dur, overlay, headline }) {
  const css = overlay ? `
  .block { position: absolute; left: 5.5cqw; bottom: 5.5cqw; width: 60cqw; }
  .panel { background: var(--background); padding: 2.2cqw 2.6cqw; }
  .rule { margin-bottom: 1.2cqw; }
  .kicker { ${role(id, "label", { cqw: 1.15 })} color: var(--accent); margin-bottom: 0.8cqw; }
  .head { ${role(id, "h2")} }
  ` : `
  .block { position: absolute; inset: 0; padding: 0 5.5cqw; display: flex; flex-direction: column; justify-content: center; }
  .rule { margin-bottom: 1.6cqw; }
  .kicker { ${role(id, "label", { cqw: 1.25 })} color: var(--accent); margin-bottom: 1.2cqw; }
  .head { ${role(id, "h1")} }
  `;
  const html = `
      <div class="block">
        <div class="${overlay ? "panel" : "plain"}">
          <span class="rule"></span>
          <div class="mask"><div class="kicker">${esc(cue)}</div></div>
          <div class="mask"><h2 class="head">${esc(headline)}</h2></div>
        </div>
      </div>`;
  const { k, out } = timing(dur, 0.7, 0.5);
  const js = `
        tl.fromTo(q(".block"), { opacity: 0 }, { opacity: 1, duration: ${0.2 * k}, ease: "none" }, 0);
        tl.fromTo(q(".rule"), { scaleX: 0 }, { scaleX: 1, duration: ${0.4 * k}, ease: "power3.out" }, ${0.05 * k});
        tl.fromTo(q(".kicker"), { yPercent: 110 }, { yPercent: 0, duration: ${0.45 * k}, ease: "expo.out" }, ${0.1 * k});
        tl.fromTo(q(".head"), { yPercent: 105 }, { yPercent: 0, duration: ${0.6 * k}, ease: "expo.out" }, ${0.15 * k});
        tl.to(q(".block"), { opacity: 0, y: -24, duration: ${0.4 * k}, ease: "power2.in" }, ${out});`;
  const body = page({ identity: id, id: cue.replace(/\./g, "-"), dur, overlay, css, html, js,
                      title: `Custom ${cue}` });
  return body.replace("<!doctype html>", `<!doctype html>\n${MARKER}`);
}

const [project, cue, frames, fpsArg, layer, ...rest] = process.argv.slice(2);
if (!project || !cue || !frames || !fpsArg || !["overlay", "full"].includes(layer)) {
  console.error("usage: node scaffold.mjs <project> <cue> <frames> <fps> <overlay|full> [headline]");
  process.exit(2);
}
const identity = JSON.parse(readFileSync(join(project, "identity.json"), "utf8"));
const [n, d] = fpsArg.split("/").map(Number);
const dur = +(Number(frames) / (n / (d || 1))).toFixed(6);
mkdirSync(join(project, "compositions"), { recursive: true });
const out = join(project, "compositions", `${cue}.html`);
writeFileSync(out, scaffold({ identity, cue, dur, overlay: layer === "overlay",
                              headline: rest.join(" ") || "headline goes here" }));
console.log(out);
