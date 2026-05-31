#!/usr/bin/env bash
# Install a built per-tool image into the tool's config directory.
# Thin wrapper around scripts/install.py. Symlinks by default; --copy to copy.
#
# Examples:
#   scripts/install.sh --tool claude-code --dry-run
#   scripts/install.sh --tool claude-code            # -> ~/.claude
#   scripts/install.sh --tool cursor --target .      # project .cursor/rules
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { echo "install: python3 is required" >&2; exit 1; }
exec python3 "$HERE/install.py" "$@"
