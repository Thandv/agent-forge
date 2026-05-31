# agent-forge

A unified, **security-gated**, **multi-tool** collection of the best open-source
AI coding **agents** and **skills** — vendored from top-rated repositories, kept
in one tool-agnostic source of truth, and rendered into native formats you can
install **locally** for Claude Code, OpenAI Codex, Cursor, and Gemini CLI.

```
upstreams ──sync(scan+license gate)──► registry/ (canonical) ──build(adapters)──► dist/<tool>/ ──install──► your tools
```

- **One source of truth.** Agents are markdown + YAML frontmatter; skills follow
  the `SKILL.md` standard. Everything lives in `registry/`.
- **Multi-tool.** Adapters emit Claude Code (`.claude/agents`, `.claude/skills`),
  Codex (`AGENTS.md` + `.codex/`), Cursor (`.cursor/rules/*.mdc`), and Gemini CLI
  (`GEMINI.md` + `.gemini/`).
- **Security is the top priority.** All upstream content is untrusted until it
  passes a static security scanner; sources are pinned to commit SHAs and locked
  by file hash; nothing vendored is ever executed by the tooling. See
  [SECURITY.md](SECURITY.md).
- **Local-first & offline.** Vendored content is committed to the repo; build and
  install need no network (only `sync` does).
- **Zero dependencies.** Pure Python 3 stdlib + bash.

## What's inside (current seed)

- **48 agents** across `optimization`, `backend`, `languages`, `frontend`,
  `review`, `security`, `devops`, `data`, `docs`, `experts` — vendored from
  [wshobson/agents](https://github.com/wshobson/agents) (MIT, role-based) and
  [0xfurai/claude-code-subagents](https://github.com/0xfurai/claude-code-subagents)
  (MIT, framework/tech experts), plus the original **`token-optimizer`** agent.
- **11 skills**: 9 (Apache-2.0) vendored from
  [anthropics/skills](https://github.com/anthropics/skills) + 2 original token
  skills (`token-budget`, `context-compaction`). Proprietary or flagged skills are
  listed as references, not copied.

Token/context-efficiency is a first-class domain: see
`registry/agents/optimization/` — **`context-manager`**, **`prompt-engineer`**,
and the original **`token-optimizer`**.

Full inventory: [`catalog.yaml`](catalog.yaml) · attributions: [`THIRD_PARTY.md`](THIRD_PARTY.md).

## Quickstart

```bash
# 1. (optional) refresh vendored content from upstreams at their pinned SHAs
scripts/sync.sh

# 2. validate (schema + license + security) and build all tool images
scripts/build.sh --tool all          # or: --tool claude-code | codex | cursor | gemini

# 3. preview, then install for your tool (symlinks by default)
scripts/install.sh --tool claude-code --dry-run
scripts/install.sh --tool claude-code            # -> ~/.claude
scripts/install.sh --tool cursor --target .      # -> project .cursor/rules
scripts/install.sh --tool codex                  # -> ~/.codex
scripts/install.sh --tool gemini                 # -> ~/.gemini (+ /commands)

# re-run build any time to update every installed symlink at once
```

Use `--copy` instead of symlinks for independent copies, and `--force` to
overwrite existing real files.

## How content is selected (the gate)

`scripts/sync.py` clones each upstream at its pinned SHA and, per item:

1. runs `scripts/scan.py` (RCE / exfiltration / destructive / prompt-injection /
   invisible-character checks);
2. detects the license;
3. **vendors** only items that are *both* permissively licensed *and* scan-clean;
4. otherwise records a **reference** entry in `catalog.yaml` with the reason
   (e.g. `webapp-testing` uses `subprocess(shell=True)`; `docx/pdf/pptx/xlsx` are
   Proprietary) — nothing is silently dropped.

`scripts/build.sh` re-runs the validator (which re-scans the whole registry)
before rendering, so unsafe content can never reach `dist/`.

## Repo layout

```
registry/        canonical source of truth (agents/<domain>/<name>/agent.md, skills/<name>/SKILL.md)
adapters/        per-tool emitters (claude_code, codex, cursor, gemini) + common.py
scripts/         sync, validate, scan, build, install, split (.sh wrappers over .py)
builder/         compose.py + sources.yaml — merge N content sources into one image
sources/         manifest.yaml (pinned SHAs) + lock.json (file hashes)
dist/            generated per-tool images (gitignored)
docs/            architecture, adding-content, roadmap-split
catalog.yaml     master index   ·   THIRD_PARTY.md   attributions   ·   SECURITY.md   policy
```

## Scaling to many repos (the split)

The repo is built to split into per-domain content repos + a standalone builder,
with `catalog.yaml` as the contract. The tooling already exists:

```bash
python3 scripts/split.py        # export split-out/agent-forge-<domain>/ self-contained bundles
python3 builder/compose.py      # merge content sources (local or pinned git) into one image
```

Demonstrated round trip: monorepo → `split.py` → bundles → `compose.py` →
identical image. See [docs/roadmap-split.md](docs/roadmap-split.md).

## Documentation

- [docs/architecture.md](docs/architecture.md) — canonical formats & adapter contract
- [docs/adding-content.md](docs/adding-content.md) — add a new agent or skill
- [docs/roadmap-split.md](docs/roadmap-split.md) — splitting into content repos + a builder repo
- [SECURITY.md](SECURITY.md) — threat model & gate

## License

Original glue (scripts, adapters, docs, `token-optimizer`) is MIT. Vendored
agents/skills retain their upstream licenses — see [THIRD_PARTY.md](THIRD_PARTY.md).
