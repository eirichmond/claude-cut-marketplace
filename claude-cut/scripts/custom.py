#!/usr/bin/env python3
"""One-off (custom) compositions for mg cues: brief, scaffold, check.

Usage:
    python custom.py brief GRAPHICS_DIR (CUE | --all) [--plan P] [--json]
    python custom.py new   GRAPHICS_DIR CUE [--plan P] [--headline TEXT] [--force]
    python custom.py check GRAPHICS_DIR CUE [CUE..] [--plan P] [--shoot S]
                           [--no-hf] [--at 0.5,1.2]

A cue that no template fits gets its own composition,
GRAPHICS_DIR/compositions/<cue>.html, authored with the HyperFrames skills
in the graphics project (so they read the same frame.md) and listed in
graphics.json as {"cue", "template": "custom", "composition"}.

  brief   (any graphic cue, or --all of them in timeline order) everything
          the author needs: the brief, the words spoken, exact
          length, overlay or full frame, what's underneath, the identity's
          colour and type names, and the house rules.
  new     writes the house shell at the cue's exact length with a
          placeholder design (graphics/scaffold.mjs). It refuses to replace
          an existing composition without --force.
  check   the house rules (below), then HyperFrames' own `check` (lint,
          runtime, layout, contrast) on the composition staged by itself,
          then stills at a few moments into review/stills/<cue>/ (overlays
          composited over the picture underneath) for the author to look
          at. Exit 1 on any error; warnings are printed but pass.

The house rules (also run by validate.py on every custom entry):
  - the scaffold marker is gone (the design has actually been authored);
  - one composition root, 1920x1080, data-duration exactly the cue's length;
  - the timeline is registered on window.__timelines;
  - an overlay's html/body background is transparent;
  - nothing is fetched from the network, and every local file it uses exists;
  - colours, fonts and var(--names) are frame.md's (identity.py check).

--plan defaults to graphics.json's plan input, else ../plan.resolved.json;
--shoot to ../shoot.json. --no-hf runs only the house rules.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from handoff import HandoffError, load, resolve_input

ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = ROOT / "graphics" / "scaffold.mjs"
HF = ["npx", "--yes", "hyperframes@0.8.71"]
MARKER = "claude-cut:scaffold"
W, H = 1920, 1080
CUSTOM_KINDS = ("mg", "lt", "chapter", "callout")


class CustomError(Exception):
    pass


# --- where things are -------------------------------------------------------------

def find_plan(project: Path, plan: Path | None) -> Path:
    if plan:
        return plan
    spec = project / "graphics.json"
    if spec.exists():
        try:
            return resolve_input(spec, load(spec), "plan", check_hash=False)
        except HandoffError:
            pass
    return project.parent / "plan.resolved.json"


def cue_info(project: Path, cue_id: str, plan_path: Path | None = None) -> dict:
    plan_path = find_plan(project, plan_path)
    plan = load(plan_path)
    cue = next((c for c in plan["cues"] if c["id"] == cue_id), None)
    if not cue:
        raise CustomError(f"{cue_id}: not a cue in {plan_path.name}")
    if cue["kind"] not in CUSTOM_KINDS:
        raise CustomError(f"{cue_id}: a {cue['kind']} cue isn't a graphic")
    fps = Fraction(plan["timeline"]["fps"])
    frames = cue["tl"][1] - cue["tl"][0]
    return {"plan": plan, "plan_path": plan_path, "cue": cue, "fps": fps,
            "frames": frames, "seconds": float(Fraction(frames) / fps),
            "overlay": cue.get("layer", "overlay") != "full",
            "file": project / "compositions" / f"{cue_id}.html"}


def spoken(plan: dict, plan_path: Path, segment: str) -> str:
    try:
        from model import load_director
        director = resolve_input(plan_path, plan, "director", check_hash=False)
        _, _, _, script = load_director(director, check_hash=False)
        seg = next(s for s in plan["segments"] if s["id"] == segment)
        return script.text(*seg["sentences"])
    except Exception:          # a courtesy: the brief works without it
        return ""


def underneath(plan: dict, cue: dict) -> str:
    if cue.get("layer") == "full":
        return "nothing: a full-frame graphic replaces the picture"
    mid = sum(cue["tl"]) // 2
    seg = next((s for s in plan["segments"] if s["tl"][0] <= mid < s["tl"][1]), None)
    if not seg:
        return "an insert gap (no picture): the overlay is shown over black"
    if seg["mode"] == "th":
        return f"the talking head ({seg['id']}): keep faces and the centre clear"
    bed = next((c for c in plan["cues"] if c.get("placement") == "bed"
                and c["segment"] == seg["id"]), None)
    return (f"the {bed['kind']} bed {bed['id']} ({bed.get('brief', '')})" if bed
            else f"voiceover segment {seg['id']} with no bed")


# --- brief --------------------------------------------------------------------------

def brief(project: Path, cue_id: str, plan_path: Path | None = None) -> dict:
    info = cue_info(project, cue_id, plan_path)
    tok = json.loads((project / "identity.json").read_text())
    c = info["cue"]
    return {
        "cue": cue_id, "kind": c["kind"], "brief": c.get("brief", ""),
        "layer": "overlay" if info["overlay"] else "full",
        "frames": info["frames"], "fps": info["plan"]["timeline"]["fps"],
        "seconds": round(info["seconds"], 6),
        "spoken": spoken(info["plan"], info["plan_path"], c["segment"]),
        "underneath": underneath(info["plan"], c),
        "file": str(info["file"].relative_to(project)),
        "exists": info["file"].exists(),
        "colors": list(tok["colors"]),
        "type_roles": list(tok["typography"]),
        "fonts": {k: v for k, v in tok["fonts"].items()},
    }


def brief_text(b: dict, identity: bool = True) -> str:
    lines = [
        f"{b['cue']} ({b['kind']}, {b['layer']}): {b['brief']}",
        f"  length    {b['frames']} frames at {b['fps']} = {b['seconds']}s",
        f"  spoken    {b['spoken'] or '(not available)'}",
        f"  under it  {b['underneath']}",
        f"  custom    {b['file']}{' (exists)' if b['exists'] else ' (none)'}",
    ]
    return "\n".join(lines + ([identity_text(b)] if identity else []))


def identity_text(b: dict) -> str:
    return "\n".join([
        "identity (frame.md):",
        f"  colours   var(--{'), var(--'.join(b['colors'])})",
        f"  type      {', '.join(b['type_roles'])}",
        f"  fonts     {', '.join(f'{k}: {v}' for k, v in b['fonts'].items())}",
    ])


# --- new --------------------------------------------------------------------------

def new(project: Path, cue_id: str, plan_path: Path | None = None,
        headline: str | None = None, force: bool = False) -> Path:
    info = cue_info(project, cue_id, plan_path)
    if info["file"].exists() and not force:
        raise CustomError(f"{info['file'].relative_to(project)} already exists "
                          f"(--force replaces it)")
    if not (project / "identity.json").exists():
        raise CustomError(f"{project} has no identity (identity.py install)")
    r = subprocess.run(["node", str(SCAFFOLD), str(project), cue_id,
                        str(info["frames"]), info["plan"]["timeline"]["fps"],
                        "overlay" if info["overlay"] else "full",
                        headline or info["cue"].get("brief", "")[:48]],
                       capture_output=True, text=True)
    if r.returncode:
        raise CustomError(r.stderr.strip())
    return info["file"]


# --- check ------------------------------------------------------------------------

REMOTE = re.compile(r"""(?:src|href)\s*=\s*["']\s*(?:https?:)?//|url\(\s*["']?\s*(?:https?:)?//|@import""",
                    re.I)
LOCAL = re.compile(r"""(?:src|href)\s*=\s*["']([^"'#:]+)["']|url\(\s*["']?([^"')#:]+)["']?\s*\)""",
                   re.I)


def house_rules(html: str, *, seconds: float, overlay: bool, tok: dict,
                comp_dir: Path) -> list[str]:
    """The static rules every custom composition follows. [] = clean."""
    import identity
    errs = []
    if MARKER in html:
        errs.append("still the scaffold: author the design, then delete the "
                    "claude-cut:scaffold line")
    roots = re.findall(r"<[^>]*data-composition-id=[\"'][^\"']+[\"'][^>]*>", html)
    if len(roots) != 1:
        errs.append(f"needs exactly one element with data-composition-id "
                    f"(found {len(roots)})")
    else:
        root = roots[0]
        dur = re.search(r"data-duration=[\"']([\d.]+)[\"']", root)
        if not dur:
            errs.append("the composition root has no data-duration")
        elif abs(float(dur.group(1)) - seconds) > 0.0005:
            errs.append(f"data-duration is {dur.group(1)}s; the cue needs "
                        f"{seconds:.6f}s")
        for attr, want in (("data-width", W), ("data-height", H)):
            m = re.search(attr + r"=[\"'](\d+)[\"']", root)
            if not m or int(m.group(1)) != want:
                errs.append(f"the composition root needs {attr}=\"{want}\"")
    if not re.search(r"window\.__timelines\s*\[", html):
        errs.append("the GSAP timeline isn't registered on window.__timelines")
    if overlay:
        hb = re.search(r"html\s*,\s*body\s*\{([^}]*)\}", html)
        if not hb or not re.search(r"background(?:-color)?\s*:\s*transparent", hb.group(1)):
            errs.append("an overlay needs `html, body { background: transparent }` "
                        "so the picture shows through")
    if REMOTE.search(html):
        errs.append("fetches something from the network: vendor it into the "
                    "graphics project instead")
    for m in LOCAL.finditer(html):
        ref = (m.group(1) or m.group(2) or "").strip()
        if ref and not ref.startswith("data") and not (comp_dir / ref).exists():
            errs.append(f"uses {ref}, which doesn't exist")
    errs += identity.check(html, tok)
    return errs


def stage(project: Path, comp: Path, dest: Path) -> None:
    """The composition alone as a HyperFrames project (check/snapshot take a
    project directory), with the fonts, vendor and frame.md beside it."""
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for d in ("fonts", "vendor", "assets"):
        if (project / d).is_dir():
            shutil.copytree(project / d, dest / d)
    shutil.copyfile(project / "frame.md", dest / "frame.md")
    html = comp.read_text().replace("../fonts/", "fonts/").replace(
        "../vendor/", "vendor/").replace("../assets/", "assets/")
    (dest / "index.html").write_text(html)


def hf_check(staged: Path) -> tuple[list[str], list[str]]:
    r = subprocess.run([*HF, "check", ".", "--json"], cwd=staged,
                       capture_output=True, text=True)
    try:
        doc = json.loads(r.stdout[r.stdout.index("{"):])
    except ValueError:
        return [f"hyperframes check didn't run: {(r.stderr or r.stdout).strip()[-400:]}"], []
    errs, warns = [], []
    for part in ("lint", "runtime", "layout", "motion", "contrast"):
        for f in (doc.get(part) or {}).get("findings") or []:
            where = f" at {f['time']}s" if f.get("time") is not None else ""
            sel = f" ({f['selector']})" if f.get("selector") else ""
            line = f"{part}: {f.get('message', f.get('code'))}{sel}{where}"
            if f.get("severity") == "error":
                errs.append(line)
            elif f.get("severity") == "warning":
                warns.append(line)
    if not doc.get("ok") and not errs:
        errs.append("hyperframes check failed (run it with --json in "
                    f"{staged} for details)")
    return errs, warns


def stills(project: Path, info: dict, staged: Path, at: list[float],
           shoot: Path | None) -> list[Path]:
    out = project / "review" / "stills" / info["cue"]["id"]
    shutil.rmtree(out, ignore_errors=True)
    r = subprocess.run([*HF, "snapshot", ".", "--at", ",".join(f"{t:.3f}" for t in at),
                        "--no-end", "--describe", "false", "-o", str(out / "raw")],
                       cwd=staged, capture_output=True, text=True)
    shots = sorted((out / "raw").glob("frame-*.png"))
    if r.returncode or not shots:
        raise CustomError(f"hyperframes snapshot failed: {(r.stderr or r.stdout).strip()[-400:]}")
    under = None
    if info["overlay"]:
        from render_graphics import context_still
        under = out / "under.png"
        shoot_doc = load(shoot) if shoot and shoot.exists() else None
        if not context_still(info["plan"], info["cue"], shoot_doc,
                             shoot.parent if shoot else None, under):
            under = None
    made = []
    for shot, t in zip(shots, at):
        dest = out / f"{info['cue']['id']} at {t:.2f}s.png"
        if info["overlay"]:
            src = (["-i", str(under)] if under else
                   ["-f", "lavfi", "-i", f"color=c=0x3a4a55:s={W}x{H}"])
            subprocess.run(["ffmpeg", "-v", "error", "-y", *src, "-i", str(shot),
                            "-filter_complex", f"[0:v]scale={W}:{H}[b];[b][1:v]overlay",
                            "-frames:v", "1", str(dest)], check=True)
        else:
            shutil.copyfile(shot, dest)
        made.append(dest)
    return made


def check(project: Path, cue_id: str, plan_path: Path | None = None,
          shoot: Path | None = None, hf: bool = True,
          at: list[float] | None = None) -> dict:
    info = cue_info(project, cue_id, plan_path)
    comp = info["file"]
    if not comp.exists():
        return {"cue": cue_id, "errors": [f"{comp.relative_to(project)} doesn't exist "
                                          f"(custom.py new {cue_id})"],
                "warnings": [], "stills": []}
    tok = json.loads((project / "identity.json").read_text())
    errs = house_rules(comp.read_text(), seconds=info["seconds"],
                       overlay=info["overlay"], tok=tok, comp_dir=comp.parent)
    warns, shots = [], []
    if hf and not errs:
        staged = project / ".check" / cue_id
        stage(project, comp, staged)
        e, warns = hf_check(staged)
        errs += e
        if not e:
            s = info["seconds"]
            at = at or [round(s * f, 3) for f in (0.25, 0.5, 0.8)]
            shots = stills(project, info, staged, at, shoot)
        shutil.rmtree(staged, ignore_errors=True)
    return {"cue": cue_id, "errors": errs, "warnings": warns,
            "stills": [str(p) for p in shots]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("brief", "new", "check"):
        p = sub.add_parser(name)
        p.add_argument("project", type=Path)
        p.add_argument("cues" if name == "check" else "cue",
                       nargs="+" if name == "check" else "?" if name == "brief" else None)
        p.add_argument("--plan", type=Path)
        if name == "brief":
            p.add_argument("--all", action="store_true",
                           help="every graphic cue in the plan, in timeline order")
            p.add_argument("--json", action="store_true")
        if name == "new":
            p.add_argument("--headline")
            p.add_argument("--force", action="store_true")
        if name == "check":
            p.add_argument("--shoot", type=Path)
            p.add_argument("--no-hf", action="store_true")
            p.add_argument("--at", help="seconds, comma-separated, for the stills")
    args = ap.parse_args()
    project = args.project.resolve()
    try:
        if args.cmd == "brief":
            if args.all == bool(args.cue):
                sys.exit("brief takes a CUE or --all")
            ids = [args.cue] if args.cue else [
                c["id"] for c in sorted(load(find_plan(project, args.plan))["cues"],
                                        key=lambda c: c["tl"][0])
                if c["kind"] in CUSTOM_KINDS]
            out = [brief(project, i, args.plan) for i in ids]
            if args.json:
                print(json.dumps(out if args.all else out[0], indent=1))
            else:
                print("\n\n".join([brief_text(b, identity=False) for b in out] +
                                    [identity_text(out[0])] if out else []))
        elif args.cmd == "new":
            path = new(project, args.cue, args.plan, args.headline, args.force)
            print(f"Wrote {path.relative_to(project)}: replace the placeholder design, "
                  f"then delete the claude-cut:scaffold line and run custom.py check")
        else:
            shoot = args.shoot or (project.parent / "shoot.json")
            at = [float(x) for x in args.at.split(",")] if args.at else None
            bad = 0
            for cue in args.cues:
                r = check(project, cue, args.plan, shoot if shoot.exists() else None,
                          hf=not args.no_hf, at=at)
                print(f"{'OK  ' if not r['errors'] else 'FAIL'} {cue}")
                for e in r["errors"]:
                    print(f"  error: {e}")
                for w in r["warnings"]:
                    print(f"  warning: {w}")
                for s in r["stills"]:
                    print(f"  still: {s}")
                bad += bool(r["errors"])
            sys.exit(1 if bad else 0)
    except (CustomError, HandoffError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
