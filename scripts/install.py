#!/usr/bin/env python3
"""Install a built per-tool image into the tool's config location.

Usage:
    install.py --tool claude-code [--target DIR] [--copy] [--dry-run] [--force]

Default is to SYMLINK from the tool's config dir back to dist/ (single source of
truth; re-running build updates everything). --copy makes independent copies.

Safety:
  * every destination path is confined under --target (no traversal);
  * existing real files are never clobbered without --force (existing symlinks
    we manage are relinked);
  * --dry-run prints the plan and changes nothing;
  * never executes any content.

Stdlib only.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from adapters import common  # noqa: E402

# Per tool: default target, and (source-subpath-within-dist/<tool>) -> (dest-subpath-within-target)
TOOLS = {
    "claude-code": {
        "target": "~/.claude",
        "map": [("agents", "agents"), ("skills", "skills")],
    },
    "codex": {
        "target": "~/.codex",
        "map": [(".codex/agents", "agents"), (".codex/skills", "skills"),
                ("AGENTS.md", "AGENTS.md")],
    },
    "cursor": {
        "target": ".",  # Cursor rules are project-scoped by default
        "map": [(".cursor/rules", ".cursor/rules")],
    },
    "gemini": {
        "target": "~",
        "map": [(".gemini/agents", ".gemini/agents"),
                (".gemini/commands", ".gemini/commands"),
                (".gemini/skills", ".gemini/skills"),
                ("GEMINI.md", "GEMINI.md")],
    },
    "thandv": {
        "target": "~/.thandv",
        "map": [("skills", "skills"), ("personas", "personas")],
    },
}


def _iter_files(src: Path):
    if src.is_file():
        yield src, src.name
    elif src.is_dir():
        for f in sorted(src.rglob("*")):
            if f.is_file():
                yield f, str(f.relative_to(src))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Install a built image into a tool's config dir.")
    ap.add_argument("--tool", required=True, choices=list(TOOLS))
    ap.add_argument("--target", default=None, help="install root (tool default if omitted)")
    ap.add_argument("--dist", default=str(ROOT / "dist"))
    ap.add_argument("--copy", action="store_true", help="copy instead of symlink")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite existing real files")
    args = ap.parse_args(argv)

    spec = TOOLS[args.tool]
    target = Path(os.path.expanduser(args.target or spec["target"])).resolve()
    dist_tool = Path(args.dist) / args.tool
    if not dist_tool.is_dir():
        print(f"install: {dist_tool} not found — run scripts/build.sh --tool {args.tool}",
              file=sys.stderr)
        return 1

    planned = linked = skipped = 0
    for src_sub, dest_sub in spec["map"]:
        src = dist_tool / src_sub
        if not src.exists():
            continue
        for f, rel in _iter_files(src):
            try:
                dest = common.safe_join(target, dest_sub, rel) if src.is_dir() \
                    else common.safe_join(target, dest_sub)
            except ValueError as e:
                print(f"  REFUSE  {e}")
                skipped += 1
                continue
            planned += 1
            action = "copy" if args.copy else "link"
            if dest.exists() or dest.is_symlink():
                if dest.is_symlink():
                    if not args.dry_run:
                        dest.unlink()
                elif not args.force:
                    print(f"  skip    {dest}  (exists; use --force)")
                    skipped += 1
                    continue
                else:
                    if not args.dry_run:
                        dest.unlink()
            rel_disp = dest.relative_to(target)
            print(f"  {action:<6}  {rel_disp}")
            if args.dry_run:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if args.copy:
                shutil.copy2(f, dest)
            else:
                os.symlink(f.resolve(), dest)
            linked += 1

    mode = "DRY-RUN" if args.dry_run else ("copied" if args.copy else "linked")
    print(f"\ninstall ({mode}): tool={args.tool} target={target} "
          f"planned={planned} {mode.lower()}={linked} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
