# builder — compose one image from many content sources

This is the seed of the standalone **builder repo** from
[docs/roadmap-split.md](../docs/roadmap-split.md) (Phase 3). It consumes one or
more content sources (local paths or git repos pinned to a commit), merges their
registries, re-scans for security, and renders the per-tool images via the shared
adapters.

## Use

```bash
# compose whatever builder/sources.yaml lists (default: the monorepo registry)
python3 builder/compose.py

# point it at split content bundles instead
python3 scripts/split.py                       # produce split-out/agent-forge-*
python3 builder/compose.py --sources my-sources.yaml --tool claude-code
```

`sources.yaml`:

```yaml
out: dist
tools: [claude-code, codex, cursor, gemini]
sources:
  - {id: optimization, path: split-out/agent-forge-optimization, precedence: 10}
  - {id: skills,       path: split-out/agent-forge-skills}
  - {id: community,    repo: https://github.com/your-org/agent-forge-x, commit: <sha>, precedence: 5}
```

## Guarantees

- **Merge by id**, highest `precedence` wins; overrides are logged.
- **Defense in depth**: the merged tree is re-scanned with `scripts/scan.py`
  regardless of any source repo's own green CI; a blocking finding aborts the
  build before anything is written.
- Pinned git sources are cloned at the exact SHA into `builder/.cache/`.
- Output matches the monorepo `build.py` layout, so `scripts/install.py` installs
  a composed image identically.

## Becoming a standalone repo

To extract this into its own repo later, move `builder/`, `adapters/`, and
`scripts/{scan,validate}.py` into it; content lives in separate repos referenced
from `sources.yaml`. Nothing else changes — `catalog.yaml` and the registry
on-disk format are the contract.
