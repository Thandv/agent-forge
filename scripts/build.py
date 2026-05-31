#!/usr/bin/env python3
"""The builder: render the canonical registry into per-tool images under dist/.

Usage:
    build.py [--tool all|claude-code|codex|cursor|gemini] [--out DIR]

Loads registry/, runs the selected adapters, writes dist/<tool>/. Read/copy
only — never executes registry content. Stdlib only.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from adapters import common, claude_code, claude_plugin, codex, cursor, gemini  # noqa: E402

ADAPTERS = {
    "claude-code": claude_code,
    "claude-plugin": claude_plugin,
    "codex": codex,
    "cursor": cursor,
    "gemini": gemini,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render registry into per-tool images.")
    ap.add_argument("--tool", default="all", choices=["all", *ADAPTERS])
    ap.add_argument("--out", default=str(ROOT / "dist"))
    args = ap.parse_args(argv)

    items = common.load_registry(ROOT / "registry")
    if not items:
        print("build: registry is empty — run scripts/sync.sh first", file=sys.stderr)
        return 1
    out_root = Path(args.out)
    tools = list(ADAPTERS) if args.tool == "all" else [args.tool]

    for tool in tools:
        tdir = out_root / tool
        if tdir.exists():
            shutil.rmtree(tdir)
        result = ADAPTERS[tool].emit(items, out_root)
        print(f"build: {tool:<12} {result['agents']} agents, {result['skills']} skills "
              f"-> {result['root']}")
    print(f"\nbuild: done ({len(items)} items, {len(tools)} tool(s)) -> {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
