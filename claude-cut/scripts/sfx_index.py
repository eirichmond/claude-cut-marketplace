#!/usr/bin/env python3
"""Local sound-effects libraries: register, index, search, suggest.

Usage:
    python sfx_index.py add-library NAME PATH     register a folder of SFX
    python sfx_index.py build                     (re)index every library
    python sfx_index.py search "heavy thud" [--category Impacts] [--limit 8]
    python sfx_index.py suggest PLAN.json [--limit 3] [-o candidates.json]
    python sfx_index.py snapshot GRAPHICS_DIR     copy the index into a project

Libraries live in ~/.claude-cut/config.json ({"sfx_libraries": [{"name",
"path"}]}); the index in ~/.claude-cut/sfx-index.json (claude-cut/sfx-index@1).
Set CLAUDE_CUT_HOME to use another folder. A file's category is its first
folder inside the library ("Whooshes"); `build` only re-probes files whose
size or modification time changed.

search/suggest rank by the words a brief shares with file and folder names
(plus a few sound synonyms). They make a shortlist; the graphics skill
judges the fit, and you hear it in the review page.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from handoff import header

AUDIO = {".wav", ".aif", ".aiff", ".mp3", ".m4a", ".flac", ".caf"}
# brief word -> words that name the same kind of sound in file names
SYNONYMS = {
    "thud": ["impact", "hit", "boom", "slam", "deep"],
    "hit": ["impact", "thud", "punch", "snap"],
    "stamp": ["impact", "slam", "thud", "hit"],
    "slam": ["impact", "hit", "stamp"],
    "boom": ["impact", "subdrop", "sub", "deep"],
    "swoosh": ["whoosh", "swish", "swipe"],
    "whoosh": ["swoosh", "swish", "pan", "air"],
    "swipe": ["whoosh", "swoosh", "transition"],
    "wipe": ["whoosh", "transition", "swipe"],
    "transition": ["whoosh", "transition", "swipe"],
    "reveal": ["riser", "whoosh", "shimmer"],
    "build": ["riser", "rise", "tension"],
    "tension": ["riser", "sub", "drone"],
    "click": ["click", "tap", "mechanism", "keyboard", "cam"],
    "typing": ["keyboard", "click", "typing"],
    "keyboard": ["keyboard", "typing", "click"],
    "pop": ["pop", "bubble", "blip"],
    "ding": ["bell", "chime", "ding", "twinkle"],
    "notification": ["bell", "ding", "chime", "pop"],
    "camera": ["cam", "shutter", "click"],
    "shutter": ["cam", "click", "shutter"],
    "paper": ["paper", "page", "book", "flutter"],
    "page": ["page", "paper", "book", "flutter"],
    "magic": ["twinkle", "bells", "shimmer"],
    "sparkle": ["twinkle", "bells", "shimmer"],
    "glitch": ["glitch", "static", "digital"],
}
STOP = {"a", "an", "the", "of", "on", "in", "as", "at", "to", "and", "with",
        "for", "it", "its", "is", "sound", "sfx", "effect", "small", "quick",
        "short", "single", "one", "then", "when", "over", "into", "lands",
        "landing", "plays"}


def home() -> Path:
    return Path(os.environ.get("CLAUDE_CUT_HOME", Path.home() / ".claude-cut"))


def config() -> dict:
    p = home() / "config.json"
    return json.loads(p.read_text()) if p.exists() else {"sfx_libraries": []}


def save_config(cfg: dict) -> None:
    home().mkdir(parents=True, exist_ok=True)
    (home() / "config.json").write_text(json.dumps(cfg, indent=1) + "\n")


def index_path() -> Path:
    return home() / "sfx-index.json"


def probe(path: Path) -> dict | None:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                        "-show_entries", "stream=channels,sample_rate:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    try:
        info = json.loads(r.stdout)
        s = info["streams"][0]
        return {"duration": round(float(info["format"]["duration"]), 3),
                "channels": int(s["channels"]), "rate": int(s["sample_rate"])}
    except (KeyError, IndexError, ValueError, json.JSONDecodeError):
        return None


def build(log=print) -> dict:
    libs = {l["name"]: l["path"] for l in config()["sfx_libraries"]}
    if not libs:
        raise SystemExit("No SFX libraries registered. Add one with: "
                         "sfx_index.py add-library NAME PATH")
    old = {}
    if index_path().exists():
        for f in json.loads(index_path().read_text()).get("files", []):
            old[(f["library"], f["path"])] = f
    files, probed, skipped = [], 0, []
    for name, root in libs.items():
        root = Path(root)
        if not root.is_dir():
            log(f"warning: library '{name}' not found at {root} (drive unplugged?); "
                f"keeping its previous entries")
            files += [f for (lib, _), f in old.items() if lib == name]
            continue
        for p in sorted(root.rglob("*")):
            if p.suffix.lower() not in AUDIO or not p.is_file() or p.name.startswith("."):
                continue
            rel = p.relative_to(root).as_posix()
            st = p.stat()
            prev = old.get((name, rel))
            if prev and prev.get("size") == st.st_size and prev.get("mtime") == st.st_mtime:
                files.append(prev)
                continue
            info = probe(p)
            if not info:
                skipped.append(rel)
                continue
            probed += 1
            parts = Path(rel).parts
            files.append({"library": name, "path": rel,
                          "category": parts[0] if len(parts) > 1 else "",
                          "name": p.stem, **info, "size": st.st_size,
                          "mtime": st.st_mtime})
    doc = header("sfx-index", {})
    doc.update({"libraries": libs, "files": files})
    home().mkdir(parents=True, exist_ok=True)
    index_path().write_text(json.dumps(doc, indent=1) + "\n")
    log(f"{len(files)} sounds in {len(libs)} librar{'y' if len(libs) == 1 else 'ies'} "
        f"({probed} probed, {len(files) - probed} unchanged) -> {index_path()}")
    for s in skipped:
        log(f"  skipped (not readable audio): {s}")
    return doc


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP]


def search(index: dict, brief: str, category: str | None = None,
           limit: int = 8) -> list[dict]:
    want = words(brief)
    expanded = {w: 1.0 for w in want}
    for w in want:
        for s in SYNONYMS.get(w, []):
            expanded.setdefault(s, 0.6)
    out = []
    for f in index["files"]:
        if category and f["category"].lower() != category.lower():
            continue
        name = set(words(f["name"]))
        cat = set(words(f["category"]))
        score = sum(wt * (1.0 if w in name else 0.7 if w in cat else 0)
                    for w, wt in expanded.items())
        # prefix matches: "whooshes" folder vs "whoosh"
        score += sum(0.4 * wt for w, wt in expanded.items()
                     if any(n.startswith(w) or w.startswith(n)
                            for n in name | cat if len(n) > 3 and n != w))
        if score > 0:
            out.append({**f, "score": round(score, 2)})
    out.sort(key=lambda f: (-f["score"], f["duration"], f["path"]))
    return out[:limit]


def suggest(index: dict, plan: dict, limit: int = 3) -> list[dict]:
    """Candidates for every sfx cue in a plan, for the graphics skill."""
    return [{"cue": c["id"], "brief": c["brief"],
             "candidates": [{"library": f["library"], "file": f["path"],
                             "duration": f["duration"], "score": f["score"]}
                            for f in search(index, c["brief"], limit=limit)]}
            for c in plan["cues"] if c["kind"] == "sfx"]


def load_index() -> dict:
    if not index_path().exists():
        raise SystemExit(f"No SFX index yet at {index_path()}: run sfx_index.py build")
    return json.loads(index_path().read_text())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add-library")
    a.add_argument("name")
    a.add_argument("path", type=Path)
    sub.add_parser("build")
    s = sub.add_parser("search")
    s.add_argument("brief")
    s.add_argument("--category")
    s.add_argument("--limit", type=int, default=8)
    g = sub.add_parser("suggest")
    g.add_argument("plan", type=Path)
    g.add_argument("--limit", type=int, default=3)
    g.add_argument("-o", "--output", type=Path)
    n = sub.add_parser("snapshot")
    n.add_argument("project", type=Path)
    args = ap.parse_args()

    if args.cmd == "add-library":
        if not args.path.is_dir():
            sys.exit(f"{args.path} is not a folder")
        cfg = config()
        cfg["sfx_libraries"] = [l for l in cfg["sfx_libraries"] if l["name"] != args.name]
        cfg["sfx_libraries"].append({"name": args.name, "path": str(args.path.resolve())})
        save_config(cfg)
        print(f"Library '{args.name}' -> {args.path.resolve()}. Now run: sfx_index.py build")
    elif args.cmd == "build":
        build()
    elif args.cmd == "search":
        for f in search(load_index(), args.brief, args.category, args.limit):
            print(f"{f['score']:>5}  {f['library']}:{f['path']}  ({f['duration']}s)")
    elif args.cmd == "suggest":
        out = suggest(load_index(), json.loads(args.plan.read_text()), args.limit)
        text = json.dumps(out, indent=1)
        if args.output:
            args.output.write_text(text + "\n")
            print(f"{len(out)} sfx cues -> {args.output}")
        else:
            print(text)
    elif args.cmd == "snapshot":
        args.project.mkdir(parents=True, exist_ok=True)
        dest = args.project / "sfx-index.json"
        shutil.copyfile(load_index_path_checked(), dest)
        print(f"Copied the SFX index to {dest}")


def load_index_path_checked() -> Path:
    load_index()
    return index_path()


if __name__ == "__main__":
    main()
