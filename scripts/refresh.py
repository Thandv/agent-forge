#!/usr/bin/env python3
"""Check upstreams for new commits and (optionally) refresh the vendored content.

  --check : report which sources are behind their upstream default branch (no changes)
  (apply) : bump the pinned SHAs in sources/manifest.yaml to the latest, re-run sync
            (which re-scans + license-gates everything), and rebuild the marketplace.

Used by .github/workflows/refresh.yml on a schedule: it bumps, re-syncs through
the security gate, validates, and — only if everything still passes — opens a PR
for human review. Never executes upstream content.

Stdlib only. Writes a markdown summary to --summary (default .refresh-summary.md).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from adapters import common  # noqa: E402

MANIFEST = ROOT / "sources" / "manifest.yaml"


def latest_sha(repo: str) -> str | None:
    out = subprocess.run(["git", "ls-remote", repo, "HEAD"],
                         capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return out.stdout.split()[0].strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check/refresh pinned upstream SHAs.")
    ap.add_argument("--check", action="store_true", help="report drift only; make no changes")
    ap.add_argument("--summary", default=str(ROOT / ".refresh-summary.md"))
    args = ap.parse_args(argv)

    text = MANIFEST.read_text(encoding="utf-8")
    manifest = common.load_yaml(text)
    bumps = []
    for src in manifest.get("sources", []):
        repo, pinned = src.get("repo"), str(src.get("commit", ""))
        if not repo:
            continue
        latest = latest_sha(repo)
        if not latest:
            print(f"  ?  {src['id']}: could not reach {repo}")
            continue
        if latest != pinned:
            bumps.append((src["id"], repo, pinned, latest))
            print(f"  ↑  {src['id']}: {pinned[:10]} -> {latest[:10]}")
        else:
            print(f"  ✓  {src['id']}: up to date ({pinned[:10]})")

    lines = ["## agent-forge upstream refresh", ""]
    if not bumps:
        lines.append("All sources are up to date — nothing to do.")
        Path(args.summary).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\nrefresh: all up to date")
        return 0

    lines.append(f"Bumped {len(bumps)} source(s) to their latest upstream commit:")
    lines.append("")
    for sid, repo, old, new in bumps:
        lines.append(f"- **{sid}** ({repo}): `{old[:10]}` → `{new[:10]}`")
    lines += ["", "Re-vendored through the security + license gate. Review the registry "
              "diff before merging.", ""]
    Path(args.summary).write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.check:
        print(f"\nrefresh --check: {len(bumps)} source(s) behind upstream")
        return 0

    # Apply: rewrite pinned SHAs, then re-sync + rebuild the marketplace.
    for _sid, _repo, old, new in bumps:
        text = text.replace(old, new)
    MANIFEST.write_text(text, encoding="utf-8")
    print(f"\nrefresh: bumped {len(bumps)} source(s); re-syncing through the gate…")

    from scripts import sync as sync_mod
    from scripts import build_marketplace
    rc = sync_mod.main()
    if rc != 0:
        print("refresh: sync failed", file=sys.stderr)
        return rc
    build_marketplace.build_into(ROOT)
    print("refresh: re-sync + marketplace rebuild complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
