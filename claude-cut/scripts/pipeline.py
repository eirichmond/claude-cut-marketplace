#!/usr/bin/env python3
"""The produce command's state engine: pipeline.json in the working folder.

Usage (every command takes --dir WORKDIR, default the current folder):
    python pipeline.py init --script SCRIPT.md [--segments b01-b08]
    python pipeline.py status [--json]
    python pipeline.py next [--to STAGE] [--json]
    python pipeline.py paths
    python pipeline.py start STAGE
    python pipeline.py done STAGE
    python pipeline.py wait STAGE --reason TEXT
    python pipeline.py approve STAGE
    python pipeline.py fail STAGE --reason TEXT
    python pipeline.py reset --from STAGE

The stages, in order, and their gates (a gate is a human sign-off):

    paper-edit  the paper edit                 gate: approve
    director    TH/VO split and prompters      gate: approve
    shoot       shoot pack, then (after the
                recording) shoot.json          gate: approve shoot.json
    cut         edit-takes, TH and VO          gate: approve both reports
    conform     plan.resolved.json             -
    graphics    renders and SFX stem           gate: the review page (every
                                                     render and effect approved)
    assemble    the Resolve timeline           -

Every file has a fixed place (`paths`): text handoffs next to the script,
everything else in the working folder. `done` checks a stage's outputs
exist and validate, then records fingerprints of what it was made from and
what it made. `status` recomputes staleness from the files on disk: a done
stage whose inputs have changed is stale, and a gated stage whose outputs
changed after approval needs approving again. Large media is fingerprinted
by size and modification time rather than hashed.

`next` names the first stage that isn't complete and what to do there:
run it, wait for the recording, or ask for the gate. `reset --from X`
sends X back to pending and marks every later done stage stale.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from handoff import HandoffError, header, load

STAGES = ["paper-edit", "director", "shoot", "cut", "conform", "graphics", "assemble"]
GATES = {"paper-edit": "approve", "director": "approve", "shoot": "approve",
         "cut": "approve", "graphics": "review"}
BIG = 64 * 1024 * 1024
STATE = "pipeline.json"


class PipelineError(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fingerprint(path: Path) -> str | None:
    if not path.is_file():
        return None
    st = path.stat()
    if st.st_size > BIG:
        return f"size:{st.st_size}:mtime:{st.st_mtime_ns}"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


# --- where everything lives ---------------------------------------------------------

def layout(state: dict) -> dict[str, Path]:
    script = Path(state["script"])
    v, stem, w = script.parent, script.stem, Path(state["workdir"])
    c = w / ".claude-cut"
    g = w / "graphics"
    return {
        "script": script,
        "script_json": v / f"{stem}.script.json",
        "paper_edit": v / f"{stem}.paper-edit.json",
        "paper_edit_md": v / f"{stem}.paper-edit.md",
        "director": v / f"{stem}.director.json",
        "director_md": v / f"{stem}.director.md",
        "map": v / "prompter.map.json",
        "th_prompter": v / "th.prompter.md",
        "vo_prompter": v / "vo.prompter.md",
        "workdir": w,
        "shoot_pack": w / "shoot-pack.md",
        "shoot_draft": w / "shoot.draft.json",
        "shoot": w / "shoot.json",
        "th_dir": c / "th",
        "th_cuts": c / "th" / "cuts.json",
        "th_sentences": c / "th" / "sentences.json",
        "th_report": c / "th" / "report.md",
        "th_fcpxml": w / f"{stem}_cut.fcpxml",
        "offsets": c / "offsets.json",
        "vo_dir": c / "vo",
        "vo_cuts": c / "vo" / "cuts.json",
        "vo_sentences": c / "vo" / "sentences.json",
        "vo_report": c / "vo" / "report.md",
        "vo_cut_wav": w / f"{stem}_vo_cut.wav",
        "plan": w / "plan.resolved.json",
        "graphics": g,
        "graphics_spec": g / "graphics.json",
        "graphics_manifest": g / "renders" / "manifest.json",
        "sfx_stem": g / "sfx" / "sfx_stem.wav",
        "assembled": w / f"{stem}_assembled.fcpxml",
        "markers": w / f"{stem}_markers.edl",
        "assemble_report": w / "assemble-report.md",
    }


def modes(p: dict) -> set:
    """'th' and/or 'vo': which recordings the director asks for."""
    if not p["director"].exists():
        return {"th", "vo"}
    try:
        return {s["mode"] for s in load(p["director"])["segments"]}
    except (HandoffError, KeyError):
        return {"th", "vo"}


def media(p: dict) -> list[Path]:
    """The recordings shoot.json names (inputs of the cut)."""
    if not p["shoot"].exists():
        return []
    try:
        s = load(p["shoot"])
    except HandoffError:
        return []
    base = p["shoot"].parent
    out = []
    for v in [s.get("th", {}).get("aroll"), s.get("th", {}).get("broll"),
              (s.get("vo") or {}).get("audio")]:
        if v:
            q = Path(v)
            out.append(q if q.is_absolute() else base / q)
    return out


def spec(stage: str, p: dict) -> dict:
    """inputs (fingerprinted if present), required and optional outputs, and
    the handoff files to validate at `done`."""
    m = modes(p)
    if stage == "paper-edit":
        return {"inputs": [p["script"]],
                "required": [p["script_json"], p["paper_edit"]],
                "optional": [p["paper_edit_md"]],
                "validate": [p["script_json"], p["paper_edit"]]}
    if stage == "director":
        return {"inputs": [p["paper_edit"]],
                "required": [p["director"], p["map"]] +
                            [p[f"{x}_prompter"] for x in sorted(m)],
                "optional": [p["director_md"]],
                "validate": [p["director"], p["map"]]}
    if stage == "shoot":
        return {"inputs": [p["director"]],
                "required": [p["shoot_pack"], p["shoot"]], "optional": [],
                "validate": [p["shoot"]]}
    if stage == "cut":
        req, val = [], []
        if "th" in m:
            req += [p["th_cuts"], p["th_sentences"], p["th_fcpxml"]]
            val += [p["th_sentences"]]
        if "vo" in m:
            req += [p["vo_cuts"], p["vo_sentences"]]
            val += [p["vo_sentences"]]
        return {"inputs": [p["shoot"], p["th_prompter"], p["vo_prompter"]] + media(p),
                "required": req,
                "optional": [p["th_report"], p["vo_report"], p["vo_cut_wav"], p["offsets"]],
                "validate": val}
    if stage == "conform":
        return {"inputs": [p["director"], p["map"], p["th_cuts"], p["th_sentences"],
                           p["th_fcpxml"], p["vo_cuts"], p["vo_sentences"]],
                "required": [p["plan"]], "optional": [], "validate": [p["plan"]]}
    if stage == "graphics":
        return {"inputs": [p["plan"], p["shoot"]],
                "required": [p["graphics_spec"], p["graphics_manifest"]],
                "optional": [p["sfx_stem"]],
                "validate": [p["graphics_spec"], p["graphics_manifest"]]}
    if stage == "assemble":
        return {"inputs": [p["plan"], p["shoot"], p["graphics_manifest"], p["offsets"]],
                "required": [p["assembled"], p["markers"], p["assemble_report"]],
                "optional": [], "validate": []}
    raise PipelineError(f"no stage {stage!r}; the stages are {', '.join(STAGES)}")


# --- state -------------------------------------------------------------------------

def state_path(workdir: Path) -> Path:
    return workdir / STATE


def read(workdir: Path) -> dict:
    sp = state_path(workdir)
    if not sp.exists():
        raise PipelineError(f"no {STATE} in {workdir}: start with "
                            f"`pipeline.py init --script <script.md>`")
    return json.loads(sp.read_text())


def save(workdir: Path, state: dict) -> None:
    sp = state_path(workdir)
    tmp = sp.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1) + "\n")
    tmp.replace(sp)


def fresh(stage: str) -> dict:
    return {"status": "pending", "gate": "n/a"}


def init(workdir: Path, script: Path, segments: str | None) -> dict:
    script = script.resolve()
    if not script.is_file():
        raise PipelineError(f"{script} doesn't exist")
    workdir = workdir.resolve()
    if state_path(workdir).exists():
        state = read(workdir)
        if Path(state["script"]) != script:
            raise PipelineError(f"{STATE} here is for {state['script']}; a working "
                                f"folder holds one video")
        if segments is not None:
            state["settings"]["segments"] = segments
        save(workdir, state)
        return state
    state = header("pipeline", {})
    del state["inputs"]
    state.update({"script": str(script), "workdir": str(workdir),
                  "settings": {"marker_scope": "sentence", "segments": segments},
                  "stages": {s: fresh(s) for s in STAGES}})
    save(workdir, state)
    return state


def prints(paths) -> dict:
    out = {}
    for p in paths:
        fp = fingerprint(Path(p))
        if fp:
            out[str(p)] = fp
    return out


def evaluate(state: dict) -> list[dict]:
    """Each stage's effective status, gate and reasons, from the files."""
    rows = []
    for name in STAGES:
        st = state["stages"][name]
        status, gate, reasons = st["status"], st["gate"], []
        if st.get("reason") and status in ("waiting", "failed", "stale"):
            reasons.append(st["reason"])
        if status == "waiting":         # paused for the recording
            changed = [Path(path).name for path, fp in st.get("inputs", {}).items()
                       if fingerprint(Path(path)) != fp]
            if changed:
                status = "stale"
                reasons.append(f"{', '.join(changed)} changed while waiting")
        if status == "done":
            for path, fp in st.get("inputs", {}).items():
                cur = fingerprint(Path(path))
                if cur is None:
                    reasons.append(f"{Path(path).name} is gone")
                elif cur != fp:
                    reasons.append(f"{Path(path).name} has changed")
            for path in st.get("outputs", {}):
                if not Path(path).exists():
                    reasons.append(f"output {Path(path).name} is missing")
            if reasons:
                status = "stale"
            elif gate == "approved" and GATES.get(name):
                changed = [Path(path).name for path, fp in st.get("outputs", {}).items()
                           if fingerprint(Path(path)) != fp]
                if changed:
                    gate = "waiting"
                    reasons.append(f"{', '.join(changed)} changed since you approved it")
        complete = status == "done" and gate in ("n/a", "approved")
        rows.append({"stage": name, "status": status, "gate": gate,
                     "reasons": reasons, "complete": complete,
                     "finished_at": st.get("finished_at")})
    return rows


GATE_TEXT = {
    "paper-edit": "Read the paper edit ({paper_edit_md}): beats, cues and chapters.",
    "director": "Read the director file ({director_md}) and the prompters "
                "({th_prompter}, {vo_prompter}).",
    "shoot": "Check what was registered in {shoot}: the recordings, and which "
             "captures are still missing.",
    "cut": "Read the cut reports ({th_report}, {vo_report}); listen to "
           "{vo_cut_wav}; import {th_fcpxml} into Resolve if you want to watch it.",
    "graphics": "Approve every graphic and sound effect on the review page "
                "(review.py serve {graphics}).",
}


def next_step(state: dict, to: str | None = None) -> dict:
    p = layout(state)
    rows = evaluate(state)
    for r in rows:
        if r["complete"]:
            if to and r["stage"] == to:
                return {"action": "stop", "stage": to,
                        "message": f"stopped after {to} (--to)"}
            continue
        name = r["stage"]
        if r["status"] == "waiting":
            action = "wait"
        elif r["status"] == "done":
            action = "gate"
        else:
            action = "run"
        out = {"action": action, "stage": name, "status": r["status"],
               "gate": r["gate"], "reasons": r["reasons"]}
        if action == "gate":
            out["message"] = GATE_TEXT[name].format(**{k: str(v) for k, v in p.items()})
            if name == "graphics":
                out["message"] += f" {review_summary(p)}"
        if name == "shoot" and action == "run":
            pack_ok = p["shoot_pack"].exists() and \
                state["stages"]["shoot"].get("inputs", {}).get(str(p["director"])) \
                == fingerprint(p["director"])
            out["step"] = "register" if pack_ok else "pack"
        return out
    return {"action": "finished", "stage": None,
            "message": f"every stage is complete: {p['assembled']}"}


def review_summary(p: dict) -> str:
    try:
        from review import read_manifest, summary
        s = summary(read_manifest(p["graphics"]))
        return (f"({s['approved']} approved, {s['redo']} sent back, "
                f"{s['pending']} pending)")
    except Exception:
        return ""


# --- transitions ---------------------------------------------------------------------

def stage_entry(state: dict, stage: str) -> dict:
    if stage not in STAGES:
        raise PipelineError(f"no stage {stage!r}; the stages are {', '.join(STAGES)}")
    return state["stages"][stage]


def start(state: dict, stage: str) -> None:
    st = stage_entry(state, stage)
    before = STAGES[:STAGES.index(stage)]
    rows = {r["stage"]: r for r in evaluate(state)}
    blocked = [s for s in before if not rows[s]["complete"]]
    if blocked:
        raise PipelineError(f"{stage} can't start: {', '.join(blocked)} "
                            f"{'is' if len(blocked) == 1 else 'are'} not complete")
    keep = {k: st[k] for k in ("inputs",) if k in st and st.get("status") == "waiting"}
    st.clear()
    st.update({"status": "running", "gate": "n/a", "started_at": now(), **keep})


def done(state: dict, stage: str) -> dict:
    from validate import validate_file
    st = stage_entry(state, stage)
    p = layout(state)
    sp = spec(stage, p)
    missing = [str(x) for x in sp["required"] if not x.exists()]
    if missing:
        raise PipelineError(f"{stage} isn't finished; missing:\n  - " +
                            "\n  - ".join(missing))
    errs = []
    for f in sp["validate"]:
        _, e = validate_file(f)
        errs += [f"{f.name}: {x}" for x in e]
    if errs:
        raise PipelineError(f"{stage}'s outputs don't validate:\n  - " + "\n  - ".join(errs))
    st.update({"status": "done", "gate": "waiting" if stage in GATES else "n/a",
               "inputs": prints(sp["inputs"]),
               "outputs": prints(sp["required"] + sp["optional"]),
               "finished_at": now()})
    st.pop("reason", None)
    st.pop("approved_at", None)
    return st


def wait(state: dict, stage: str, reason: str) -> None:
    st = stage_entry(state, stage)
    p = layout(state)
    st.update({"status": "waiting", "reason": reason,
               "inputs": prints(spec(stage, p)["inputs"])})


def approve(state: dict, stage: str) -> None:
    st = stage_entry(state, stage)
    if stage not in GATES:
        raise PipelineError(f"{stage} has no gate")
    row = next(r for r in evaluate(state) if r["stage"] == stage)
    if row["status"] != "done":
        raise PipelineError(f"{stage} is {row['status']}"
                            + (f" ({'; '.join(row['reasons'])})" if row["reasons"] else "")
                            + ": finish it before approving")
    p = layout(state)
    if GATES[stage] == "review":
        from review import read_manifest, summary
        s = summary(read_manifest(p["graphics"]))
        if s["redo"] or s["pending"]:
            raise PipelineError(f"the review isn't finished: {s['approved']} approved, "
                                f"{s['redo']} sent back, {s['pending']} pending")
    sp = spec(stage, p)
    st.update({"gate": "approved", "approved_at": now(),
               "outputs": prints(sp["required"] + sp["optional"])})


def fail(state: dict, stage: str, reason: str) -> None:
    st = stage_entry(state, stage)
    st.update({"status": "failed", "reason": reason})


def reset_from(state: dict, stage: str) -> list[str]:
    stage_entry(state, stage)
    i = STAGES.index(stage)
    state["stages"][stage] = fresh(stage)
    touched = [stage]
    for later in STAGES[i + 1:]:
        st = state["stages"][later]
        if st["status"] in ("done", "waiting", "running", "failed"):
            st.update({"status": "stale", "gate": "n/a",
                       "reason": f"{stage} is being redone"})
            touched.append(later)
    return touched


# --- CLI -----------------------------------------------------------------------------

MARK = {"pending": "·", "running": "…", "waiting": "⏸", "done": "✓",
        "failed": "✗", "stale": "↻"}


def status_text(state: dict) -> str:
    lines = [f"{Path(state['script']).name} -> {state['workdir']}"]
    if state["settings"].get("segments"):
        lines[0] += f"  (segments {state['settings']['segments']})"
    for r in evaluate(state):
        gate = "" if r["gate"] == "n/a" else f"  gate: {r['gate']}"
        why = f"  - {'; '.join(r['reasons'])}" if r["reasons"] else ""
        lines.append(f"  {MARK[r['status']]} {r['stage']:<11} {r['status']:<8}{gate}{why}")
    n = next_step(state)
    lines.append(f"next: {n['action']}" + (f" {n['stage']}" if n["stage"] else "")
                 + (f" ({n['step']})" if n.get("step") else ""))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, default=Path.cwd(), help="the working folder")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--script", type=Path, required=True)
    i.add_argument("--segments")
    s = sub.add_parser("status")
    s.add_argument("--json", action="store_true")
    n = sub.add_parser("next")
    n.add_argument("--to", choices=STAGES)
    n.add_argument("--json", action="store_true")
    sub.add_parser("paths")
    for name in ("start", "done", "approve"):
        sub.add_parser(name).add_argument("stage", choices=STAGES)
    for name in ("wait", "fail"):
        x = sub.add_parser(name)
        x.add_argument("stage", choices=STAGES)
        x.add_argument("--reason", required=True)
    r = sub.add_parser("reset")
    r.add_argument("--from", dest="from_", required=True, choices=STAGES)
    args = ap.parse_args()
    w = args.dir.resolve()
    try:
        if args.cmd == "init":
            state = init(w, args.script, args.segments)
            print(status_text(state))
            return
        state = read(w)
        if args.cmd == "status":
            print(json.dumps(evaluate(state), indent=1) if args.json
                  else status_text(state))
        elif args.cmd == "next":
            nx = next_step(state, args.to)
            if args.json:
                print(json.dumps(nx, indent=1))
            else:
                print(f"{nx['action']} {nx['stage'] or ''}".strip() +
                      (f" ({nx['step']})" if nx.get("step") else ""))
                for x in nx.get("reasons", []):
                    print(f"  - {x}")
                if nx.get("message"):
                    print(f"  {nx['message']}")
        elif args.cmd == "paths":
            print(json.dumps({k: str(v) for k, v in layout(state).items()}, indent=1))
        else:
            if args.cmd == "start":
                start(state, args.stage)
            elif args.cmd == "done":
                done(state, args.stage)
            elif args.cmd == "wait":
                wait(state, args.stage, args.reason)
            elif args.cmd == "approve":
                approve(state, args.stage)
            elif args.cmd == "fail":
                fail(state, args.stage, args.reason)
            elif args.cmd == "reset":
                touched = reset_from(state, args.from_)
                print(f"reset: {', '.join(touched)}")
            save(w, state)
            print(status_text(state))
    except (PipelineError, HandoffError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
