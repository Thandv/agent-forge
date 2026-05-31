#!/usr/bin/env python3
"""Estimate the approximate token cost of files/directories.

Heuristic and OFFLINE: reads files only, no network, no execution. Token count
is approximated as max(chars/4, words/0.75) — a reasonable cross-check that
brackets common BPE tokenizers well enough for "what should I read?" planning.

Usage:
    estimate_tokens.py PATH [PATH ...] [--by-file] [--top N] [--ext .py,.md]

Output: total estimate, and (with --by-file) a per-file breakdown sorted by cost.
Stdlib only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", ".cache"}
BINARY_HINT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".woff",
               ".woff2", ".ttf", ".mp3", ".mp4", ".so", ".dylib", ".wasm", ".ico"}


def estimate(text: str) -> int:
    chars = len(text)
    words = len(text.split())
    return int(max(chars / 4.0, words / 0.75))


def iter_files(paths: list[str], exts: set[str] | None):
    for p in paths:
        root = Path(p)
        if root.is_file():
            yield root
            continue
        for f in sorted(root.rglob("*")):
            if not f.is_file():
                continue
            if any(part in SKIP_DIRS for part in f.parts):
                continue
            if f.suffix.lower() in BINARY_HINT:
                continue
            if exts and f.suffix.lower() not in exts:
                continue
            yield f


def human(n: int) -> str:
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Approximate token cost of files/dirs.")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--by-file", action="store_true", help="show per-file breakdown")
    ap.add_argument("--top", type=int, default=0, help="limit breakdown to N files")
    ap.add_argument("--ext", default="", help="comma-separated extensions, e.g. .py,.md")
    args = ap.parse_args(argv)

    exts = {e if e.startswith(".") else "." + e
            for e in args.ext.split(",") if e.strip()} or None

    rows: list[tuple[int, str]] = []
    total = 0
    n = 0
    for f in iter_files(args.paths, exts):
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        est = estimate(text)
        total += est
        n += 1
        rows.append((est, str(f)))

    if args.by_file:
        rows.sort(reverse=True)
        shown = rows[: args.top] if args.top else rows
        width = max((len(p) for _, p in shown), default=4)
        for est, p in shown:
            print(f"{human(est):>8}  {p:<{width}}")
        if args.top and len(rows) > args.top:
            print(f"... (+{len(rows) - args.top} more files)")
        print("-" * (width + 10))

    print(f"~{human(total)} tokens across {n} file(s) (heuristic estimate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
