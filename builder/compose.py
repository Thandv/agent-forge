#!/usr/bin/env python3
"""Phase-3 builder: compose one installable image from many content sources.

Reads builder/sources.yaml (a list of content sources — local paths or git
repos pinned to a commit), merges their registries into one item set,
de-duplicates by id (highest precedence wins), RE-SCANS the merged tree for
security (defense in depth — it does not trust a source's own CI), then renders
the per-tool images via the shared adapters.

This is the seed of the standalone builder repo described in
docs/roadmap-split.md: it already consumes N content repos via catalog/registry
and produces the same dist/<tool>/ output as the monorepo build.

Usage: compose.py [--sources FILE] [--out DIR] [--tool all|<name>]
Stdlib only; never executes content.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
from adapters import common, claude_code, claude_plugin, codex, cursor, gemini  # noqa: E402
from adapters import thandv as thandv_adapter  # noqa: E402
from scripts import scan as scanner  # noqa: E402

ADAPTERS = {"claude-code": claude_code, "claude-plugin": claude_plugin,
            "codex": codex, "cursor": cursor, "gemini": gemini,
            "thandv": thandv_adapter}
CACHE = HERE / ".cache"


def resolve_registry(src: dict) -> Path:
    """Return the registry/ path for a source (local path or pinned git repo)."""
    if src.get("path"):
        base = (REPO / src["path"]).resolve() if not Path(src["path"]).is_absolute() \
            else Path(src["path"]).resolve()
    else:
        dest = CACHE / src["id"]
        commit = str(src["commit"])
        if not (dest / ".git").is_dir():
            dest.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
                            src["repo"], str(dest)], check=True)
        subprocess.run(["git", "-C", str(dest), "fetch", "-q", "--depth", "1",
                        "origin", commit], check=False)
        subprocess.run(["git", "-C", str(dest), "checkout", "-q", commit], check=True)
        base = dest
    reg = base / "registry"
    return reg if reg.is_dir() else base


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compose one image from many content sources.")
    ap.add_argument("--sources", default=str(HERE / "sources.yaml"))
    ap.add_argument("--out", default=str(HERE / "dist"))
    ap.add_argument("--tool", default="all", choices=["all", *ADAPTERS])
    args = ap.parse_args(argv)

    cfg = common.load_yaml(Path(args.sources).read_text(encoding="utf-8"))
    sources = sorted(cfg.get("sources", []), key=lambda s: s.get("precedence", 0))

    # Merge by id; later (higher precedence) sources overwrite earlier ones.
    merged: dict[str, common.Item] = {}
    provenance: dict[str, str] = {}
    for src in sources:
        reg = resolve_registry(src)
        items = common.load_registry(reg)
        for it in items:
            if it.id in merged:
                print(f"  merge: {it.id} overridden by source '{src['id']}' "
                      f"(was '{provenance[it.id]}')")
            merged[it.id] = it
            provenance[it.id] = src["id"]
        print(f"  source {src['id']:<22} +{len(items)} item(s) from {reg}")

    items = list(merged.values())

    # Defense in depth: re-scan the merged tree regardless of any source's CI.
    blocks = 0
    for it in items:
        findings = scanner.scan_path(it.path if it.kind == "skill" else it.path)
        for f in findings:
            if f.severity == "block":
                blocks += 1
                print(f"  SECURITY BLOCK: {it.id} {f.path}:{f.line} {f.description}")
    if blocks:
        print(f"\ncompose: ABORT — {blocks} blocking security finding(s) in merged content")
        return 1

    out_root = Path(args.out)
    tools = list(ADAPTERS) if args.tool == "all" else [args.tool]
    for tool in tools:
        tdir = out_root / tool
        if tdir.exists():
            shutil.rmtree(tdir)
        r = ADAPTERS[tool].emit(items, out_root)
        print(f"  build {tool:<12} {r['agents']} agents, {r['skills']} skills")

    print(f"\ncompose: {len(items)} merged items from {len(sources)} source(s) "
          f"-> {out_root} ({len(tools)} tool image(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
