# Adding content

There are two ways to add an agent or skill: **vendor** it from an upstream repo,
or **author** it directly in the registry.

## A. Vendor from an upstream repo

1. Find the upstream commit SHA you want to pin (never a branch/tag):
   ```bash
   git ls-remote https://github.com/OWNER/REPO main
   ```
2. Add (or extend) a source block in `sources/manifest.yaml`:
   ```yaml
   sources:
     - id: my-upstream
       repo: https://github.com/OWNER/REPO
       commit: <full-40-char-sha>
       license: MIT            # repo-level license for agents
       kind: agents            # or: skills
       mode: vendor            # vendor | auto | reference | submodule
       agents:                 # for kind: agents
         - src: path/in/upstream/agent.md
           name: my-agent
           domain: backend
       # for kind: skills instead:
       # skills_dir: skills
       # skills: [skill-a, skill-b]     # auto-detect license; vendor if clean+permissive
       # reference: [proprietary-skill] # force reference (never copied)
   ```
3. Sync, validate, build:
   ```bash
   scripts/sync.sh && scripts/build.sh --tool all
   ```
   The scanner + license gate decide vendor vs reference automatically. Check the
   `sync` output and `catalog.yaml` for the verdict and any reason.

### Modes

- `vendor` — copy items (still subject to scan + license gate).
- `auto` — vendor if clean + permissive, else reference. Good for mixed-license repos.
- `reference` — never copied; cataloged as a pointer to upstream.
- `submodule` — register under `sources/vendor/` as a git submodule (for large /
  fast-moving upstreams). Content keeps its upstream license and isn't relicensed.

## B. Author an original agent or skill

Create the file(s) directly under `registry/` with `license: MIT` (or another
permissive license) and a `source` of `original`:

```
registry/agents/<domain>/<name>/agent.md
registry/skills/<name>/SKILL.md
```

`sync.py` auto-catalogs originals (status `original`) and adds their hashes to the
lock file. See `registry/agents/optimization/token-optimizer/agent.md` for a
worked example.

## Rules enforced by `validate.py`

- `name` present; `description` ≥ 10 chars.
- Agents have a `domain`.
- License is in the permissive allow-list (`MIT`, `Apache-2.0`, `BSD`, `ISC`,
  `CC0`, `CC-BY`, `Unlicense`, `0BSD`).
- IDs are unique; lock hashes match; the registry re-scans clean.

## Frontmatter gotchas

The bundled YAML parser handles a deliberate subset. Keep `description` on a
single line (quote it if it contains `:`, `#`, `[`, `]`, quotes, etc.). Block
scalars (`>`/`|`) work but lose internal indentation — fine for prose, not for
embedded code.
