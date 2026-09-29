#!/usr/bin/env node
// Generate one standalone composition per templated cue.
//
// Usage: node build.mjs <graphics project dir> <rows.json>
//   rows.json: [{ "cue": "b04.lt1", "template": "lowerThird",
//                 "frames": 150, "fps": "25/1", "vars": { ... } }]
// Writes <project>/compositions/<cue>.html and prints one line per file.
// The project must have identity.json (scripts/identity.py install).
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const [project, rowsPath] = process.argv.slice(2);
if (!project || !rowsPath) {
  console.error("usage: node build.mjs <project dir> <rows.json>");
  process.exit(2);
}
const identity = JSON.parse(readFileSync(join(project, "identity.json"), "utf8"));
const rows = JSON.parse(readFileSync(rowsPath, "utf8"));
mkdirSync(join(project, "compositions"), { recursive: true });

const fps = (s) => { const [n, d] = String(s).split("/").map(Number); return n / (d || 1); };
let failed = 0;
for (const row of rows) {
  const file = join(here, "templates", `${row.template}.mjs`);
  if (!existsSync(file)) { console.error(`${row.cue}: no template ${row.template}`); failed++; continue; }
  const t = await import(pathToFileURL(file));
  const missing = Object.entries(t.variables)
    .filter(([k, v]) => v.required && (row.vars?.[k] ?? "") === "").map(([k]) => k);
  const unknown = Object.keys(row.vars ?? {}).filter((k) => !(k in t.variables));
  if (missing.length || unknown.length) {
    console.error(`${row.cue}: ${missing.length ? "missing " + missing.join(", ") : ""}` +
                  `${unknown.length ? " unknown " + unknown.join(", ") : ""}`);
    failed++; continue;
  }
  const dur = +(row.frames / fps(row.fps)).toFixed(6);
  const html = t.render({ identity, cue: row.cue, dur, ...row.vars });
  const out = join(project, "compositions", `${row.cue}.html`);
  writeFileSync(out, html);
  console.log(`${row.cue}\t${row.template}\t${dur}s\t${out}`);
}
process.exit(failed ? 1 : 0);
