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
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from adapters import common  # noqa: E402

GATE_FILES = [("adapters/common.py", "adapters/common.py"),
              ("scripts/scan.py", "scripts/scan.py"),
              ("scripts/validate.py", "scripts/validate.py")]

CI_YAML = """\
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Security scan (blocks on any finding)
        run: python3 scripts/scan.py registry
      - name: Validate (schema + license + lock + re-scan)
        run: python3 scripts/validate.py
"""

GITIGNORE = "__pycache__/\n*.pyc\n.DS_Store\n"


def _git_init(bundle_dir: Path, name: str) -> str:
    subprocess.run(["git", "init", "-q", str(bundle_dir)], check=True)
    subprocess.run(["git", "-C", str(bundle_dir), "config", "user.name", "Gokul PM"], check=True)
    subprocess.run(["git", "-C", str(bundle_dir), "config", "user.email",
                    "gokulpm@users.noreply.github.com"], check=True)
    subprocess.run(["git", "-C", str(bundle_dir), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(bundle_dir), "commit", "-q", "-m",
                    f"Initial content bundle: {name} (split from agent-forge)"], check=True)
    return subprocess.run(["git", "-C", str(bundle_dir), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def _bundle_for(item: common.Item) -> str:
    return f"agent-forge-{item.domain}" if item.kind == "agent" else "agent-forge-skills"


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Split the registry into per-domain content bundles.")
    ap.add_argument("--out", default=str(ROOT / "split-out"))
    ap.add_argument("--git-init", action="store_true",
                    help="initialize each bundle as its own git repo with an initial commit")
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
            f"the agent-forge builder (`builder/compose.py`).\n\nSee THIRD_PARTY.md for "
            f"upstream attributions.\n", encoding="utf-8")
        (bdir / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        (bdir / ".github" / "workflows" / "ci.yml").write_text(CI_YAML, encoding="utf-8")
        (bdir / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
        tp = ["# Third-Party Attributions", "",
              f"Content in `{bundle}` retains its upstream license.", ""]
        for it in sorted(group, key=lambda x: x.id):
            tp.append(f"- `{it.id}` — {it.license} — {it.source_repo or 'original'}")
        (bdir / "THIRD_PARTY.md").write_text("\n".join(tp) + "\n", encoding="utf-8")

        head = ""
        if args.git_init:
            head = " @" + _git_init(bdir, bundle)
        print(f"  bundle {bundle:<28} {len(group)} item(s){head}")

    mode = " (git repos)" if args.git_init else ""
    print(f"\nsplit: {len(groups)} bundle(s){mode} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
