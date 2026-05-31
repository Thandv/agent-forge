#!/usr/bin/env python3
"""Phase-2 split: export the monorepo registry into per-domain content bundles.

Each bundle is a self-contained mini content-repo:
    agent-forge-<group>/
      registry/...                  (just that group's content)
      adapters/common.py            (shared lib, copied)
      scripts/{scan.py,validate.py} (the security gate, copied)
      catalog.yaml                  (subset)
      README.md
so its own CI can run `python3 scripts/validate.py` independently. The builder
(builder/compose.py) later recombines these into one image.

Grouping: agents by domain -> agent-forge-<domain>; all skills -> agent-forge-skills.

Usage: split.py [--out DIR]   (default ./split-out)
Stdlib only; never executes content.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from adapters import common  # noqa: E402

GATE_FILES = [("adapters/common.py", "adapters/common.py"),
              ("scripts/scan.py", "scripts/scan.py"),
              ("scripts/validate.py", "scripts/validate.py")]


def _bundle_for(item: common.Item) -> str:
    return f"agent-forge-{item.domain}" if item.kind == "agent" else "agent-forge-skills"


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Split the registry into per-domain content bundles.")
    ap.add_argument("--out", default=str(ROOT / "split-out"))
    args = ap.parse_args(argv)

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    items = common.load_registry(ROOT / "registry")

    groups: dict[str, list[common.Item]] = {}
    for it in items:
        groups.setdefault(_bundle_for(it), []).append(it)

    for bundle, group in sorted(groups.items()):
        bdir = out / bundle
        (bdir / "scripts").mkdir(parents=True, exist_ok=True)
        (bdir / "adapters").mkdir(parents=True, exist_ok=True)
        for src_rel, dst_rel in GATE_FILES:
            shutil.copy2(ROOT / src_rel, bdir / dst_rel)

        lock: dict[str, str] = {}
        cat_items = []
        for it in group:
            if it.kind == "agent":
                rel = Path("registry/agents") / it.domain / it.path.parent.name
                common.copy_tree_confined(it.path.parent, bdir / rel)
            else:
                rel = Path("registry/skills") / it.path.name
                common.copy_tree_confined(it.path, bdir / rel)
            for f in sorted((bdir / rel).rglob("*")):
                if f.is_file():
                    lock[str(f.relative_to(bdir))] = _sha256(f)
            cat_items.append(dict(id=it.id, kind=it.kind, name=it.name,
                                  domain=it.domain, license=it.license,
                                  description=it.description[:160]))

        (bdir / "sources").mkdir(exist_ok=True)
        (bdir / "sources" / "lock.json").write_text(
            common.json.dumps(dict(sorted(lock.items())), indent=2) + "\n", encoding="utf-8")
        (bdir / "catalog.yaml").write_text(
            common.dump_yaml({"bundle": bundle, "items": cat_items}) + "\n", encoding="utf-8")
        (bdir / "README.md").write_text(
            f"# {bundle}\n\nContent bundle split from agent-forge "
            f"({len(group)} item(s)). Self-contained: run `python3 scripts/validate.py` "
            f"to check the security + schema gate. Recombine with other bundles via "
            f"the agent-forge builder (`builder/compose.py`).\n", encoding="utf-8")
        print(f"  bundle {bundle:<28} {len(group)} item(s)")

    print(f"\nsplit: {len(groups)} bundle(s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
