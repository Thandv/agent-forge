#!/usr/bin/env bash
# Sync vendored content from sources/manifest.yaml into registry/.
# Thin wrapper around scripts/sync.py (all logic lives in Python, stdlib only).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v git  >/dev/null || { echo "sync: git is required" >&2; exit 1; }
command -v python3 >/dev/null || { echo "sync: python3 is required" >&2; exit 1; }
exec python3 "$HERE/sync.py" "$@"
