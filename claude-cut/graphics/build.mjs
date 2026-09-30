#!/usr/bin/env node
// Generate one standalone composition per templated cue.
//
// Usage:
//   node build.mjs <graphics project dir> <rows.json>
//     rows.json: [{ "cue": "b04.lt1", "template": "lowerThird",
//                   "frames": 150, "fps": "25/1", "vars": { ... } }]
//     Writes <project>/compositions/<cue>.html, one line per file; exits 1
//     (after reporting every row) if any row is invalid.
//   node build.mjs --list
//     Every template's variables and default layer, as JSON.
// The project must have identity.json (scripts/identity.py install).
import { readFileSync, writeFileSync, mkdirSync, readdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const templatesDir = join(here, "templates");

async function load(name) {
  const file = join(templatesDir, `${name}.mjs`);
  return existsSync(file) ? import(pathToFileURL(file)) : null;
}

export function checkVars(t, vars = {}) {
  const errs = [];
  for (const [k, spec] of Object.entries(t.variables)) {
    const v = vars[k];
    if (v === undefined || v === null || v === "") {
      if (spec.required) errs.push(`missing ${k}`);
      continue;
    }
    const ok = spec.type === "string" ? typeof v === "string"
      : spec.type === "number" ? typeof v === "number" && Number.isFinite(v)
      : spec.type === "boolean" ? typeof v === "boolean"
      : spec.type === "enum" ? spec.values.includes(v) : false;
    if (!ok) errs.push(spec.type === "enum"
      ? `${k} must be one of ${spec.values.join(", ")}` : `${k} must be a ${spec.type}`);
  }
  for (const k of Object.keys(vars)) if (!(k in t.variables)) errs.push(`unknown ${k}`);
  return errs;
}

const args = process.argv.slice(2);
if (args[0] === "--list") {
  const out = {};
  for (const f of readdirSync(templatesDir).filter((f) => f.endsWith(".mjs")).sort()) {
    const name = f.replace(/\.mjs$/, "");
    const t = await load(name);
    out[name] = { layer: t.layer, variables: t.variables };
  }
  console.log(JSON.stringify(out, null, 1));
  process.exit(0);
}
const [project, rowsPath] = args;
if (!project || !rowsPath) {
  console.error("usage: node build.mjs <project dir> <rows.json> | --list");
  process.exit(2);
}
const identity = JSON.parse(readFileSync(join(project, "identity.json"), "utf8"));
const rows = JSON.parse(readFileSync(rowsPath, "utf8"));
mkdirSync(join(project, "compositions"), { recursive: true });

const fps = (s) => { const [n, d] = String(s).split("/").map(Number); return n / (d || 1); };
let failed = 0;
for (const row of rows) {
  const t = await load(row.template);
  if (!t) { console.error(`${row.cue}: no template ${row.template}`); failed++; continue; }
  const errs = checkVars(t, row.vars);
  if (!Number.isInteger(row.frames) || row.frames < 1) errs.push("frames must be a positive integer");
  if (errs.length) { console.error(`${row.cue} (${row.template}): ${errs.join("; ")}`); failed++; continue; }
  const dur = +(row.frames / fps(row.fps)).toFixed(6);
  const html = t.render({ identity, cue: row.cue, dur, ...row.vars });
  const out = join(project, "compositions", `${row.cue}.html`);
  writeFileSync(out, html);
  console.log(`${row.cue}\t${row.template}\t${dur}s\t${out}`);
}
process.exit(failed ? 1 : 0);
