#!/usr/bin/env python3
"""The channel's visual identity: identity/frame.md and its fonts.

Usage:
    python identity.py tokens [--frame FRAME.md]        print the tokens as JSON
    python identity.py install PROJECT_DIR [--frame ..] set up a graphics project
    python identity.py check FILE... [--project DIR]    lint compositions against it

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

# What every identity must define: templates rely on these names.
REQUIRED_COLORS = ("background", "accent", "text", "text-muted", "border")
REQUIRED_FONTS = ("display", "body", "mono")
REQUIRED_ROLES = ("body", "lead", "label", "h3", "h1", "display")
# Names from the Broadside pack the identity was derived from. Compositions
# must use the semantic names instead.
# (The brand is capitalised; "broadside printing" is a generic design term.)
LEGACY = re.compile(r"fire-orange|ink-black|ink-on-orange|border-dark|"
                    r"--cream|colors\.cream|\bBarlow\b|IBM Plex Mono|"
                    r"broadside-num|(?-i:\bBroadside\b)", re.I)


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
    colors = fm.get("colors") or {}
    fonts = fm.get("fonts") or {}
    typography = fm.get("typography") or {}
    problems = []
    problems += [f"colors.{c} is missing" for c in REQUIRED_COLORS
                 if c not in colors]
    problems += [f"fonts.{f} is missing" for f in REQUIRED_FONTS
                 if f not in fonts]
    problems += [f"typography.{r} is missing" for r in REQUIRED_ROLES
                 if r not in typography]
    for role, spec in typography.items():
        if spec.get("font") not in fonts:
            problems.append(f"typography.{role} uses font role "
                            f"'{spec.get('font')}', which fonts doesn't define")
    files = font_files(font_dir)
    problems += [f"no font file for {fam} in {font_dir}"
                 for fam in sorted(set(fonts.values())) if fam not in files]
    if problems:
        raise ValueError(f"{frame.name}: " + "; ".join(problems))
    typo = {role: {**spec, "family": fonts[spec["font"]]}
            for role, spec in typography.items()}
    return {
        "name": fm.get("name", ""),
        "frame_sha256": hashlib.sha256(frame.read_bytes()).hexdigest(),
        "colors": colors,
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


def _norm_color(value: str) -> str:
    v = value.strip().lower().replace(" ", "")
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        v = "#" + "".join(ch * 2 for ch in v[1:])
    return v


def check(html: str, tok: dict) -> list[str]:
    """Problems with a composition against the identity: colours outside
    the palette, fonts without files, unknown var(--name)s, Broadside-era
    names. Returns [] when it's clean."""
    palette = {_norm_color(v) for v in tok["colors"].values()}
    issues = []
    for m in sorted(set(re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|"
                                   r"rgba?\([^)]*\)", html))):
        if _norm_color(m) not in palette:
            issues.append(f"colour {m} isn't in frame.md's palette")
    families = set(tok["font_files"])
    for m in sorted(set(re.findall(
            r"font-family:\s*((?:\"[^\"]*\"|'[^']*'|[^;}\"'<\n])+)", html))):
        for fam in (f.strip().strip("\"'") for f in m.split(",")):
            if fam and fam.lower() not in ("inherit", "monospace", "sans-serif",
                                           "serif") and fam not in families:
                issues.append(f"font {fam!r} has no file in identity/fonts")
    known = set(tok["colors"])
    for name in sorted(set(re.findall(r"var\(--([a-z0-9-]+)", html))):
        if name not in known:
            issues.append(f"var(--{name}) isn't a colour in frame.md")
    for m in sorted(set(x.group(0) for x in LEGACY.finditer(html))):
        issues.append(f"'{m}' is a Broadside name; use the semantic names")
    return issues


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tokens")
    t.add_argument("--frame", type=Path, default=FRAME)
    i = sub.add_parser("install")
    i.add_argument("project", type=Path)
    i.add_argument("--frame", type=Path, default=FRAME)
    c = sub.add_parser("check")
    c.add_argument("files", type=Path, nargs="+")
    c.add_argument("--project", type=Path,
                   help="use this graphics project's identity.json")
    args = ap.parse_args()
    try:
        if args.cmd == "tokens":
            print(json.dumps(tokens(args.frame), indent=1))
        elif args.cmd == "check":
            tok = (json.loads((args.project / "identity.json").read_text())
                   if args.project else tokens())
            bad = 0
            for f in args.files:
                issues = check(f.read_text(), tok)
                bad += bool(issues)
                print(f"{'FAIL' if issues else 'OK  '} {f}")
                for i in issues:
                    print(f"  - {i}")
            sys.exit(1 if bad else 0)
        else:
            tok = install(args.project, args.frame)
            print(f"Installed '{tok['name']}' into {args.project}")
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
