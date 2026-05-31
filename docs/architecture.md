# Architecture

agent-forge separates **content** (the canonical registry) from the **builder**
(adapters + scripts). The contract between them is the registry's on-disk format
plus `catalog.yaml`. This separation is what makes the
[multi-repo split](roadmap-split.md) possible later with no rework.

```
sources/manifest.yaml ─► sync.py ─► registry/ ─► build.py ─► dist/<tool>/ ─► install.py ─► tool config
   (pinned SHAs)        (scan +      (canonical)   (adapters)   (per-tool)      (symlink/copy)
                         license)
```

## Canonical formats (the source of truth)

### Agent — `registry/agents/<domain>/<name>/agent.md`

YAML frontmatter + markdown body (the system prompt):

```markdown
---
name: token-optimizer
description: "One-line trigger description (single line; quotes if it has punctuation)."
domain: optimization
model: inherit
tags: [tokens, context]          # optional
source:                          # provenance (repo + pinned commit + upstream path)
  repo: https://github.com/wshobson/agents
  commit: 0818067b4ecad18c234b2ae427cc44f2053792d4
  path: plugins/.../agent.md
license: MIT
---

You are ...   <- the agent's system prompt
```

### Skill — `registry/skills/<name>/SKILL.md` (+ `scripts/`, `references/`, `assets/`)

Follows the `SKILL.md` standard (`name`, `description`, plus injected `source`
and `license`). Supporting directories are preserved verbatim.

## The tooling (stdlib only)

| File | Role |
| --- | --- |
| `scripts/scan.py` | Static security scanner. Importable (`scan_path`, `worst_severity`) + CLI. Classifies findings `block`/`warn`. |
| `scripts/sync.py` | Clone upstreams at pinned SHAs → scan → license-detect → vendor or reference. Writes `catalog.yaml`, `sources/lock.json`, `THIRD_PARTY.md`. |
| `scripts/validate.py` | Schema + license gate + lock-hash integrity + a full re-scan of `registry/`. Build fails on any error. |
| `scripts/build.py` | Loads registry, runs adapters → `dist/<tool>/`. |
| `scripts/install.py` | Symlinks/copies a built image into a tool's config dir, with path confinement, `--dry-run`, no-clobber. |
| `adapters/common.py` | Minimal YAML load/dump, frontmatter parse/build, registry model (`Item`), `safe_join`/`slug`. |
| `adapters/<tool>.py` | `emit(items, out_root) -> dict`. The only thing a new tool needs. |

## Adapter contract

Each adapter module exposes:

```python
TOOL = "claude-code"
def emit(items: list[common.Item], out_root: Path) -> dict:
    # write files under out_root / TOOL using common.safe_join(...)
    return {"tool": TOOL, "agents": n_a, "skills": n_s, "root": str(out_root / TOOL)}
```

Adapters **read and write only** — they never execute registry content, and all
output paths go through `common.safe_join` to prevent traversal. Register a new
adapter in `scripts/build.py`'s `ADAPTERS` map and `scripts/install.py`'s `TOOLS`
map (target + path mapping).

## Why a hand-rolled YAML parser?

The `dependency-free` rule (see [SECURITY.md](../SECURITY.md)) keeps the
dependency attack surface at zero. We own every YAML file in the repo, so
`adapters/common.py` ships a small, auditable parser for the subset we use
(nested maps, block/flow sequences, scalars, block scalars, comments) instead of
vendoring PyYAML.
