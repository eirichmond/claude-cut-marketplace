#!/usr/bin/env python3
"""The graphics review gate: a local page to approve or send back each render.

Usage:
    python review.py serve GRAPHICS_DIR [--port 8765]   the review page
    python review.py todo GRAPHICS_DIR                  redo list, as JSON
    python review.py status GRAPHICS_DIR                summary; exit 0 only
                                                        when everything is approved

The page lists every graphic in timeline order: its review proxy (the
render over the picture underneath it), the brief, and the words spoken
around it, with Approve / Redo and a note. Each sound effect has players
for the pick and its alternatives; choosing an alternative is a redo that
asks for a swap. Decisions are written straight into renders/manifest.json,
which render_graphics.py keeps (and resets to pending when a cue changes)
and assemble checks. The graphics skill reads `todo`, makes the changes,
and re-renders only those cues.

The server listens on 127.0.0.1 only and serves nothing outside the
graphics project and the indexed SFX libraries.
"""
from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import sys
import tempfile
import threading
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from handoff import load, resolve_input

STATUSES = ("approved", "redo", "pending")


# --- the manifest as review state ---------------------------------------------------

def manifest_path(project: Path) -> Path:
    return project / "renders" / "manifest.json"


def read_manifest(project: Path) -> dict:
    p = manifest_path(project)
    if not p.exists():
        raise SystemExit(f"No renders yet in {project}: run render_graphics.py first")
    return json.loads(p.read_text())


def write_manifest(project: Path, doc: dict) -> None:
    p = manifest_path(project)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(doc, indent=1) + "\n")
    os.replace(tmp, p)


def items(doc: dict):
    """(kind, entry) for every reviewable thing, graphics then effects."""
    for r in doc.get("renders", []):
        yield "graphic", r
    for s in (doc.get("sfx") or {}).get("items", []):
        yield "sfx", s


LOCK = threading.Lock()


def set_review(project: Path, cue: str, kind: str, status: str, note: str = "",
               swap: str | None = None) -> dict:
    if status not in ("approved", "redo"):
        raise ValueError("status must be approved or redo")
    with LOCK:
        doc = read_manifest(project)
        for k, entry in items(doc):
            if k == kind and entry["cue"] == cue:
                if swap and kind != "sfx":
                    raise ValueError("only sound effects can be swapped")
                if swap and swap == entry["file"]:
                    swap = None
                if swap:
                    status = "redo"
                review = {"status": status, "note": note.strip()}
                if swap:
                    review["swap"] = swap
                entry["review"] = review
                write_manifest(project, doc)
                return review
    raise KeyError(f"no {kind} {cue} in the manifest")


def summary(doc: dict) -> dict:
    out = {s: 0 for s in STATUSES}
    for _, e in items(doc):
        out[e.get("review", {}).get("status", "pending")] += 1
    out["total"] = sum(out[s] for s in STATUSES)
    return out


def todo(doc: dict) -> list[dict]:
    return [{"cue": e["cue"], "kind": k, "note": e["review"].get("note", ""),
             **({"swap": e["review"]["swap"]} if "swap" in e["review"] else {})}
            for k, e in items(doc) if e.get("review", {}).get("status") == "redo"]


# --- context for the page ----------------------------------------------------------

def context(project: Path, doc: dict) -> dict:
    spec_path = project / "graphics.json"
    spec = load(spec_path)
    plan_path = resolve_input(spec_path, spec, "plan", check_hash=False)
    plan = load(plan_path)
    cues = {c["id"]: c for c in plan["cues"]}
    words = {}
    try:
        from model import load_director
        director = resolve_input(plan_path, plan, "director", check_hash=False)
        _, _, _, script = load_director(director, check_hash=False)
        for s in plan["segments"]:
            words[s["id"]] = script.text(*s["sentences"])
    except Exception:      # the words are a courtesy; the page works without them
        pass
    alts = {s["cue"]: s for s in spec.get("sfx", [])}
    libraries = {}
    if spec.get("sfx") and "sfx_index" in spec["inputs"]:
        libraries = load(resolve_input(spec_path, spec, "sfx_index",
                                       check_hash=False))["libraries"]
    return {"plan": plan, "cues": cues, "words": words, "alts": alts,
            "libraries": libraries,
            "templates": {g["cue"]: g["template"] for g in spec["graphics"]}}


def proxy_note(e: dict) -> str:
    if e.get("layer") == "full":
        return "Full frame: replaces the picture for its length."
    if e.get("proxy_context") == "picture":
        return "Shown over the picture underneath."
    return "Shown over a plain background (nothing supplied underneath yet)."


def tc(frame: int, fps: Fraction) -> str:
    base = round(fps)
    s, f = divmod(frame, base)
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{f:02d}"


PAGE_CSS = """
:root { --bg: #f4f5f6; --card: #fff; --ink: #1b1f23; --muted: #626a73; --line: #d9dde1;
        --ok: #1f7a4d; --redo: #b3261e; --pending: #8a6d00; --accent: #0b7285; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #111417; --card: #1a1e22; --ink: #e8eaed; --muted: #9aa3ad; --line: #2c3238;
          --ok: #5cc28f; --redo: #f28b82; --pending: #e6c34a; --accent: #4fc3d9; } }
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.45 system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--ink); }
header { position: sticky; top: 0; z-index: 2; background: var(--bg); border-bottom: 1px solid var(--line);
         padding: 12px 16px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
header h1 { font-size: 17px; margin: 0 12px 0 0; }
.counts span { margin-right: 10px; } .counts b { font-variant-numeric: tabular-nums; }
main { max-width: 1100px; margin: 0 auto; padding: 16px; display: grid; gap: 16px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 14px;
        display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 16px; }
@media (max-width: 760px) { .card { grid-template-columns: minmax(0, 1fr); } }
.card > div { min-width: 0; }
.brief, .said, .note { overflow-wrap: anywhere; }
.card.hidden { display: none; }
video { width: 100%; border-radius: 4px; background: #000; aspect-ratio: 16/9; }
.meta { display: flex; flex-wrap: wrap; gap: 6px 12px; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
.meta .id { color: var(--ink); font-weight: 600; font-family: ui-monospace, monospace; }
.brief { margin: 4px 0 8px; }
.said { font-size: 13px; color: var(--muted); border-left: 3px solid var(--line); padding-left: 8px; margin: 0 0 10px; }
.badge { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 99px; border: 1px solid currentColor; }
.badge.approved { color: var(--ok); } .badge.redo { color: var(--redo); } .badge.pending { color: var(--pending); }
textarea { width: 100%; min-height: 56px; font: inherit; padding: 6px 8px; border-radius: 6px;
           border: 1px solid var(--line); background: var(--bg); color: var(--ink); }
.actions { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
button { font: inherit; padding: 6px 14px; border-radius: 6px; border: 1px solid var(--line);
         background: var(--card); color: var(--ink); cursor: pointer; }
button.approve { border-color: var(--ok); color: var(--ok); }
button.redo { border-color: var(--redo); color: var(--redo); }
.sfx label { display: flex; gap: 8px; align-items: center; margin: 6px 0; font-size: 13px; }
.sfx audio { height: 32px; flex: 1; min-width: 0; }
.note { font-size: 12px; color: var(--muted); }
"""


def page(project: Path) -> str:
    doc = read_manifest(project)
    ctx = context(project, doc)
    fps = Fraction(doc["timeline"]["fps"])
    esc = html.escape
    cards = []

    def at(pair):
        kind, e = pair
        c = ctx["cues"].get(e["cue"], {})
        start = e["frame"] if kind == "sfx" else c.get("tl", [0])[0]
        return (start, kind != "graphic", e["cue"])

    for kind, e in sorted(items(doc), key=at):     # timeline order, effects included
        cue = ctx["cues"].get(e["cue"], {})
        rv = e.get("review", {"status": "pending", "note": ""})
        start = e["frame"] if kind == "sfx" else cue.get("tl", [0])[0]
        said = ctx["words"].get(cue.get("segment"), "")
        head = (f'<div class="meta"><span class="id">{esc(e["cue"])}</span>'
                f'<span>{tc(start, fps)}</span><span>{esc(cue.get("kind", kind))}</span>'
                + (f'<span>{esc(ctx["templates"].get(e["cue"], ""))}</span>' if kind == "graphic" else "")
                + f'<span class="badge {rv["status"]}">{rv["status"]}</span></div>')
        body = (f'<p class="brief">{esc(cue.get("brief", ""))}</p>'
                + (f'<p class="said">{esc(said[:400])}</p>' if said else ""))
        if kind == "graphic":
            media = (f'<video controls loop muted playsinline preload="metadata" '
                     f'src="/files/{quote(e.get("proxy", ""))}?v={e["sha256"][:12]}#t=0.5"></video>'
                     f'<p class="note">{proxy_note(e)}</p>')
        else:
            alt = ctx["alts"].get(e["cue"], {})
            options = [e["file"]] + [a for a in alt.get("alternatives", []) if a != e["file"]]
            want = rv.get("swap", e["file"])
            rows = "".join(
                f'<label><input type="radio" name="sfx-{esc(e["cue"])}" value="{esc(f)}"'
                f'{" checked" if f == want else ""}> <span>{esc(Path(f).stem)}'
                f'{" (current)" if f == e["file"] else ""}</span>'
                f'<audio controls preload="none" src="/sfx/{quote(e["library"])}/{quote(f)}"></audio></label>'
                for f in options)
            media = (f'<div class="sfx">{rows}</div>'
                     f'<p class="note">Gain {e.get("gain_db", 0)} dB. Choosing another sound '
                     f'sends this back with a swap request.</p>')
        form = (f'<textarea placeholder="What should change? (for Redo)">{esc(rv.get("note", ""))}</textarea>'
                f'<div class="actions"><button class="approve">Approve</button>'
                f'<button class="redo">Redo</button></div>')
        cards.append(f'<section class="card" data-cue="{esc(e["cue"])}" data-kind="{kind}" '
                     f'data-status="{rv["status"]}"><div>{media}</div>'
                     f'<div>{head}{body}{form}</div></section>')
    s = summary(doc)
    return f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Graphics review</title><style>{PAGE_CSS}</style></head>
<body><header><h1>Graphics review</h1>
<div class="counts"><span>Approved <b id="n-approved">{s['approved']}</b></span>
<span>Redo <b id="n-redo">{s['redo']}</b></span>
<span>Pending <b id="n-pending">{s['pending']}</b></span>
<span>of <b>{s['total']}</b></span></div>
<label><input type="checkbox" id="open-only"> Only what still needs a decision</label>
<button id="approve-rest">Approve all pending</button></header>
<main>{''.join(cards)}</main>
<script>
async function send(card, status) {{
  const radio = card.querySelector('input[type=radio]:checked');
  const body = {{ cue: card.dataset.cue, kind: card.dataset.kind, status,
                 note: card.querySelector('textarea').value,
                 swap: radio ? radio.value : null }};
  const r = await fetch('/api/review', {{ method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(body) }});
  if (!r.ok) {{ alert(await r.text()); return; }}
  const rv = await r.json();
  card.dataset.status = rv.status;
  const b = card.querySelector('.badge');
  b.className = 'badge ' + rv.status; b.textContent = rv.status;
  counts(); filter();
}}
function counts() {{
  for (const s of ['approved', 'redo', 'pending'])
    document.getElementById('n-' + s).textContent =
      document.querySelectorAll('.card[data-status="' + s + '"]').length;
}}
function filter() {{
  const only = document.getElementById('open-only').checked;
  for (const c of document.querySelectorAll('.card'))
    c.classList.toggle('hidden', only && c.dataset.status === 'approved');
}}
document.querySelectorAll('.card').forEach(card => {{
  card.querySelector('.approve').onclick = () => send(card, 'approved');
  card.querySelector('.redo').onclick = () => send(card, 'redo');
}});
document.getElementById('open-only').onchange = filter;
document.getElementById('approve-rest').onclick = async () => {{
  for (const c of document.querySelectorAll('.card[data-status="pending"]'))
    await send(c, 'approved');
}};
</script></body></html>"""


# --- the server ------------------------------------------------------------------------

def make_server(project: Path, port: int = 8765) -> ThreadingHTTPServer:
    project = project.resolve()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, code, body: bytes, ctype="text/plain; charset=utf-8", extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def send_file(self, path: Path):
            size = path.stat().st_size
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            rng = self.headers.get("Range", "")
            start, end = 0, size - 1
            code = 200
            if rng.startswith("bytes="):
                a, _, b = rng[6:].partition("-")
                start = int(a) if a else max(0, size - int(b))
                end = int(b) if a and b else size - 1
                end = min(end, size - 1)
                code = 206
            with open(path, "rb") as f:
                f.seek(start)
                data = f.read(end - start + 1)
            extra = {"Accept-Ranges": "bytes"}
            if code == 206:
                extra["Content-Range"] = f"bytes {start}-{end}/{size}"
            self.reply(code, data, ctype, extra)

        def do_GET(self):
            url = urlparse(self.path)
            p = unquote(url.path)
            try:
                if p == "/":
                    return self.reply(200, page(project).encode(), "text/html; charset=utf-8")
                if p == "/api/state":
                    doc = read_manifest(project)
                    return self.reply(200, json.dumps({"summary": summary(doc),
                                                       "todo": todo(doc)}).encode(),
                                      "application/json")
                if p.startswith("/files/"):
                    f = (project / p[len("/files/"):]).resolve()
                    if project not in f.parents or not f.is_file():
                        return self.reply(404, b"not found")
                    return self.send_file(f)
                if p.startswith("/sfx/"):
                    lib, _, rel = p[len("/sfx/"):].partition("/")
                    ctx = context(project, read_manifest(project))
                    allowed = {a for s in ctx["alts"].values() if s["library"] == lib
                               for a in [s["file"], *s.get("alternatives", [])]}
                    root = Path(ctx["libraries"].get(lib, "/nonexistent")).resolve()
                    f = (root / rel).resolve()
                    if rel not in allowed or root not in f.parents or not f.is_file():
                        return self.reply(404, b"not found")
                    return self.send_file(f)
            except SystemExit as e:
                return self.reply(500, str(e).encode())
            self.reply(404, b"not found")

        do_HEAD = do_GET

        def do_POST(self):
            if urlparse(self.path).path != "/api/review":
                return self.reply(404, b"not found")
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
                rv = set_review(project, body["cue"], body["kind"], body["status"],
                                body.get("note", ""), body.get("swap"))
            except (KeyError, ValueError, TypeError) as e:
                return self.reply(400, str(e).strip("'").encode())
            self.reply(200, json.dumps(rv).encode(), "application/json")

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("project", type=Path)
    s.add_argument("--port", type=int, default=8765)
    for name in ("todo", "status"):
        sub.add_parser(name).add_argument("project", type=Path)
    args = ap.parse_args()
    if args.cmd == "serve":
        srv = make_server(args.project, args.port)
        print(f"Review page: http://127.0.0.1:{srv.server_address[1]}/  (Ctrl-C to stop)",
              flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
    elif args.cmd == "todo":
        print(json.dumps(todo(read_manifest(args.project)), indent=1))
    else:
        s = summary(read_manifest(args.project))
        print(f"{s['approved']} approved, {s['redo']} to redo, {s['pending']} pending, "
              f"of {s['total']}")
        sys.exit(0 if s["approved"] == s["total"] else 1)


if __name__ == "__main__":
    main()
