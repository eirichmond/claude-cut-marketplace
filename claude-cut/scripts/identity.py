#!/usr/bin/env python3
"""The channel's visual identity: identity/frame.md and its fonts.

Usage:
    python identity.py tokens [--frame FRAME.md]        print the tokens as JSON
    python identity.py install PROJECT_DIR [--frame ..] set up a graphics project

`frame.md` is the one source of truth for colours, fonts and the type ramp.
HyperFrames' skills read `frame.md` from a project's root, so `install`
copies it there (with the font files and an identity.json the claude-cut
templates read), and every render - templated or custom - uses the same
identity. Templates only ever use the semantic names (accent, background,
text ...), never hex values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

IDENTITY = Path(__file__).resolve().parent.parent / "identity"
FRAME = IDENTITY / "frame.md"
FONTS = IDENTITY / "fonts"
FONT_FILE = re.compile(r"^(?P<family>.+?)-latin-(?P<weight>\d{3})-normal\.woff2$")


def front_matter(path: Path) -> dict:
    import yaml
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError(f"{path}: no YAML front matter")
    return yaml.safe_load(m.group(1))


def font_files(font_dir: Path = FONTS) -> dict:
    """{family name: {weight: filename}} from fontsource-style file names."""
    out: dict = {}
    for f in sorted(font_dir.glob("*.woff2")):
        m = FONT_FILE.match(f.name)
        if not m:
            continue
        family = " ".join(w.capitalize() if w != "dm" else "DM"
                          for w in m.group("family").split("-"))
        out.setdefault(family, {})[int(m.group("weight"))] = f.name
    return out


def tokens(frame: Path = FRAME, font_dir: Path = FONTS) -> dict:
    fm = front_matter(frame)
    fonts = fm.get("fonts", {})
    files = font_files(font_dir)
    missing = [fam for fam in set(fonts.values()) if fam not in files]
    if missing:
        raise ValueError(f"no font files for {', '.join(sorted(missing))} in "
                         f"{font_dir}")
    typo = {}
    for role, spec in fm.get("typography", {}).items():
        family = fonts.get(spec.get("font"), spec.get("font"))
        typo[role] = {**spec, "family": family}
    return {
        "name": fm.get("name", ""),
        "frame_sha256": hashlib.sha256(frame.read_bytes()).hexdigest(),
        "colors": fm.get("colors", {}),
        "fonts": fonts,
        "font_files": files,
        "typography": typo,
        "spacing": fm.get("spacing", {}),
    }


def install(project: Path, frame: Path = FRAME, font_dir: Path = FONTS) -> dict:
    """frame.md at the project root (where HyperFrames' skills look), the
    font files under fonts/, and identity.json for the templates."""
    project.mkdir(parents=True, exist_ok=True)
    tok = tokens(frame, font_dir)
    shutil.copyfile(frame, project / "frame.md")
    dest = project / "fonts"
    dest.mkdir(exist_ok=True)
    for family in tok["font_files"].values():
        for fname in family.values():
            shutil.copyfile(font_dir / fname, dest / fname)
    for lic in font_dir.glob("OFL-*.txt"):
        shutil.copyfile(lic, dest / lic.name)
    (project / "identity.json").write_text(json.dumps(tok, indent=1) + "\n")
    return tok


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tokens")
    t.add_argument("--frame", type=Path, default=FRAME)
    i = sub.add_parser("install")
    i.add_argument("project", type=Path)
    i.add_argument("--frame", type=Path, default=FRAME)
    args = ap.parse_args()
    try:
        if args.cmd == "tokens":
            print(json.dumps(tokens(args.frame), indent=1))
        else:
            tok = install(args.project, args.frame)
            print(f"Installed '{tok['name']}' into {args.project}")
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
