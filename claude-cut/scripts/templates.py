"""The graphics templates' variable schemas, read from graphics/build.mjs
--list so there is one definition (in each template's .mjs file)."""
from __future__ import annotations

import functools
import json
import shutil
import subprocess
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent / "graphics" / "build.mjs"


@functools.lru_cache(maxsize=1)
def schemas() -> dict:
    if not shutil.which("node"):
        raise RuntimeError("the graphics templates need node on the PATH")
    r = subprocess.run(["node", str(BUILD), "--list"], capture_output=True,
                       text=True)
    if r.returncode:
        raise RuntimeError(f"build.mjs --list failed: {r.stderr[-500:]}")
    return json.loads(r.stdout)


def check_vars(template: str, vars_: dict) -> list[str]:
    """The same rules as build.mjs's checkVars."""
    spec = schemas().get(template)
    if spec is None:
        return [f"no template '{template}' (have: {', '.join(sorted(schemas()))})"]
    errs = []
    for k, s in spec["variables"].items():
        v = vars_.get(k)
        if v is None or v == "":
            if s["required"]:
                errs.append(f"missing {k}")
            continue
        ok = {"string": isinstance(v, str),
              "number": isinstance(v, (int, float)) and not isinstance(v, bool),
              "boolean": isinstance(v, bool),
              "enum": v in s.get("values", [])}.get(s["type"], False)
        if not ok:
            errs.append(f"{k} must be one of {', '.join(s['values'])}"
                        if s["type"] == "enum" else f"{k} must be a {s['type']}")
    errs += [f"unknown {k}" for k in vars_ if k not in spec["variables"]]
    return errs
