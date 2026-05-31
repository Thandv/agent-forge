#!/usr/bin/env bash
# Build per-tool images from registry/ into dist/.
# Validates (schema + license + security gate) first, then renders adapters.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { echo "build: python3 is required" >&2; exit 1; }
echo "==> validate"
python3 "$HERE/validate.py"
echo "==> build"
exec python3 "$HERE/build.py" "$@"
