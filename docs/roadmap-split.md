# Roadmap: splitting into content repos + a builder repo

The long-term shape is **many small content repos** + **one builder repo** that
consumes them all and produces a combined installable image. agent-forge is laid
out so this split is mechanical, not a rewrite.

## The stable contract

Two things are the contract between content and builder:

1. **Registry on-disk format** — `registry/agents/<domain>/<name>/agent.md` and
   `registry/skills/<name>/SKILL.md` with the frontmatter in
   [architecture.md](architecture.md).
2. **`catalog.yaml`** — the machine-readable index every content repo publishes.

As long as a content repo honors these, the builder can consume it.

## Phase 1 — today (one repo)

Content (`registry/`, `sources/`) and builder (`adapters/`, `scripts/`) live
together. Good for iterating quickly.

## Phase 2 — split content out

Lift each domain (or each upstream) into its own repo, each self-contained with
its own `registry/`, `sources/manifest.yaml`, `catalog.yaml`, and `THIRD_PARTY.md`:

```
agent-forge-optimization/   registry/agents/optimization/... + catalog.yaml
agent-forge-security/       registry/agents/security/...     + catalog.yaml
agent-forge-skills-core/    registry/skills/...              + catalog.yaml
```

Each runs the *same* `scan.py` + `validate.py` in its own CI, so the security gate
travels with the content. Nothing about the file layout changes — just the repo
boundary.

## Phase 3 — the builder repo

Extract `adapters/` + `scripts/build.py` + `install.py` into a standalone
**builder** repo. It takes a list of content sources (git URLs or local paths),
reads each one's `catalog.yaml`, merges them (de-duplicating by `id`, with an
explicit precedence order), and renders the combined `dist/<tool>/` image — the
same per-tool output as today, just sourced from N repos.

```
builder/
  sources.yaml          # list of content repos + pinned SHAs
  scripts/compose.sh    # fetch each content repo (pinned) -> run scan -> merge catalogs -> build -> image
  adapters/             # unchanged from Phase 1
```

The builder re-runs `scan.py` across the merged tree (defense in depth — it does
not trust a content repo's own green CI) before emitting the image.

## Why it works without rework

- Adapters already consume `common.load_registry()` over a `registry/` tree — they
  don't care whether that tree came from one repo or ten merged together.
- The scanner and validator are path-agnostic and stdlib-only, so they drop into
  any repo's CI unchanged.
- `catalog.yaml` is emitted today and is already the merge unit the builder needs.
