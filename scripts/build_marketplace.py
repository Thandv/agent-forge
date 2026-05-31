#!/usr/bin/env python3
"""Generate the COMMITTED root plugin marketplace.

Writes `.claude-plugin/marketplace.json` and `plugins/<domain>/...` at the repo
root so the marketplace can be installed straight from GitHub with no build step:

    /plugin marketplace add Thandv/agent-forge
    /plugin install agentforge-optimization@agent-forge

Unlike dist/ (gitignored), this output IS committed — it's the distributable
artifact. CI regenerates it and fails on drift (see .github/workflows/ci.yml),
so it always matches the registry. Stdlib only; never executes content.

Usage: build_marketplace.py [--check]   (--check: build to a temp dir and diff)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from adapters import common, claude_plugin  # noqa: E402

MANAGED = [".claude-plugin", "plugins"]


def build_into(root: Path) -> dict:
    for m in MANAGED:
        if (root / m).exists():
            shutil.rmtree(root / m)
    items = common.load_registry(ROOT / "registry")
    return claude_plugin.emit_to(items, root)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate the committed root plugin marketplace.")
    ap.add_argument("--check", action="store_true",
                    help="build into a temp dir and diff against the committed tree")
    args = ap.parse_args(argv)

    if args.check:
        import filecmp
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        build_into(tmp)
        diffs = []
        for m in MANAGED:
            a, b = ROOT / m, tmp / m
            cmp = filecmp.dircmp(a, b) if a.exists() and b.exists() else None
            if not a.exists() or not b.exists():
                diffs.append(f"{m}: missing on one side")
            elif cmp and (cmp.left_only or cmp.right_only or cmp.diff_files or _deep(cmp)):
                diffs.append(f"{m}: differs")
        shutil.rmtree(tmp, ignore_errors=True)
        if diffs:
            print("build_marketplace --check: OUT OF SYNC -> " + "; ".join(diffs))
            print("  run: python3 scripts/build_marketplace.py && git add .claude-plugin plugins")
            return 1
        print("build_marketplace --check: committed marketplace matches registry")
        return 0

    r = build_into(ROOT)
    print(f"build_marketplace: wrote .claude-plugin/marketplace.json + plugins/ "
          f"({r['agents']} agents, {r['skills']} skills)")
    return 0


def _deep(cmp) -> bool:
    if cmp.diff_files or cmp.left_only or cmp.right_only:
        return True
    return any(_deep(sub) for sub in cmp.subdirs.values())


if __name__ == "__main__":
    raise SystemExit(main())
