# agent-forge

[![ci](https://github.com/Thandv/agent-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/Thandv/agent-forge/actions/workflows/ci.yml)

📚 **[Browse the catalog](https://thandv.github.io/agent-forge/)** — searchable index of every agent & skill, generated from `catalog.yaml`.

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
  Codex (`AGENTS.md` + `.codex/`), Cursor (`.cursor/rules/*.mdc`), Gemini CLI
  (`GEMINI.md` + `.gemini/`), and **Thandv** (a local open-weights Claude-style
  CLI — agents become `~/.thandv/personas/*.json`, skills become `~/.thandv/skills/*.md`).
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
overwrite existing real files. There's also a `Makefile` (`make build`,
`make install`, `make test`, …).

### Install as a Claude Code plugin marketplace (one command, no build)

A granular, per-domain **plugin marketplace** is committed at the repo root
(`.claude-plugin/marketplace.json` + `plugins/`), so you can add it straight from
GitHub and install just the domains you want (keeps context lean):

```
/plugin marketplace add Thandv/agent-forge
/plugin install agentforge-optimization@agent-forge
/plugin install agentforge-security@agent-forge
```

The root marketplace is generated from the registry by
`scripts/build_marketplace.py`; CI fails if it drifts out of sync. (A build-time
copy is also emitted under `dist/claude-plugin/` by `scripts/build.sh`.)

### Use it with Thandv (local open-weights CLI)

[Thandv](https://github.com/Thandv) is a local, open-weights, Claude-style coding
assistant with personas + a skills directory. agent-forge feeds it directly:

```bash
scripts/build.sh --tool thandv
scripts/install.sh --tool thandv          # -> ~/.thandv (personas/ + skills/)
thandv --persona security-auditor "review this diff"
thandv --persona token-optimizer "this session is getting expensive"
```

Each agent-forge **agent** becomes a selectable Thandv `--persona` (its body is the
system prompt, with Thandv's `tool-use`/`honesty` skills attached); each **skill**
becomes a `~/.thandv/skills/*.md` entry. Loading user personas from disk needs the
small thandv patch on the `agent-forge-personas` branch (`thandv/personas.py` +
`config.py`); skills work unpatched.

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

The split was demonstrated live as 15 published per-domain repos
([`Thandv/agent-forge-*`](https://github.com/Thandv?tab=repositories&q=agent-forge-),
since archived — this monorepo is the single source of truth). The archived
repos remain clonable, so remote composition still works:

```bash
python3 builder/compose.py --sources builder/sources.remote.example.yaml
```

## Documentation

- [docs/architecture.md](docs/architecture.md) — canonical formats & adapter contract
- [docs/adding-content.md](docs/adding-content.md) — add a new agent or skill
- [docs/roadmap-split.md](docs/roadmap-split.md) — splitting into content repos + a builder repo
- [SECURITY.md](SECURITY.md) — threat model & gate

## License

Original glue (scripts, adapters, docs, `token-optimizer`) is MIT. Vendored
agents/skills retain their upstream licenses — see [THIRD_PARTY.md](THIRD_PARTY.md).
