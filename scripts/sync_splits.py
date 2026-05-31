#!/usr/bin/env python3
"""Push registry changes out to the per-domain split repos (Thandv/agent-forge-*).

Regenerates every bundle from the current registry, then for each one compares
against its remote and pushes only if content changed. Used by the
sync-splits.yml workflow after the registry updates (e.g. an auto-refresh PR
merges), and runnable locally.

Auth:
  * default: SSH remotes (git@github.com:OWNER/<bundle>.git) — uses your keys.
  * --token TOKEN: HTTPS with a token (for CI; pass a PAT with repo scope).

Usage:
    sync_splits.py [--owner Thandv] [--dry-run] [--token TOKEN] [--only a,b]
Stdlib only; never executes content.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from adapters import common  # noqa: E402
from scripts import split  # noqa: E402


def remote_url(owner: str, name: str, token: str | None) -> str:
    if token:
        return f"https://x-access-token:{token}@github.com/{owner}/{name}.git"
    return f"git@github.com:{owner}/{name}.git"


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True)


def sync_one(bundle: str, bdir: Path, owner: str, token: str | None,
             dry_run: bool, work: Path) -> str:
    url = remote_url(owner, bundle, token)
    clone = work / bundle
    r = _run(["git", "clone", "-q", "--depth", "1", url, str(clone)])
    if r.returncode != 0:
        return "missing"  # repo doesn't exist / no access

    # Replace everything tracked (except .git) with the freshly generated bundle.
    for entry in clone.iterdir():
        if entry.name == ".git":
            continue
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    shutil.copytree(bdir, clone, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))

    _run(["git", "add", "-A"], cwd=clone)
    if _run(["git", "diff", "--cached", "--quiet"], cwd=clone).returncode == 0:
        return "unchanged"
    if dry_run:
        return "would-update"

    _run(["git", "config", "user.name", "agent-forge-bot"], cwd=clone)
    _run(["git", "config", "user.email", "actions@github.com"], cwd=clone)
    _run(["git", "commit", "-q", "-m",
          "chore: sync content from agent-forge monorepo"], cwd=clone)
    p = _run(["git", "push", "-q", "origin", "HEAD:main"], cwd=clone)
    return "pushed" if p.returncode == 0 else f"push-failed: {p.stderr.strip()[:80]}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Push registry changes to split repos.")
    ap.add_argument("--owner", default="Thandv")
    ap.add_argument("--token", default=None)
    ap.add_argument("--only", default="", help="comma-separated bundle names to limit to")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    work = Path(tempfile.mkdtemp(prefix="af-splits-"))
    gen = work / "_gen"
    bundles = split.export_bundles(gen)
    only = {b.strip() for b in args.only.split(",") if b.strip()}

    results: dict[str, int] = {}
    for bundle, bdir, _count in bundles:
        if only and bundle not in only:
            continue
        status = sync_one(bundle, bdir, args.owner, args.token, args.dry_run, work)
        results[status] = results.get(status, 0) + 1
        print(f"  {status:<14} {bundle}")

    shutil.rmtree(work, ignore_errors=True)
    summary = ", ".join(f"{k}={v}" for k, v in sorted(results.items()))
    print(f"\nsync_splits ({'dry-run' if args.dry_run else 'apply'}): {summary or 'nothing'}")
    return 1 if any(k.startswith("push-failed") for k in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
