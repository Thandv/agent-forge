"""Adapter: canonical registry -> Thandv (local open-weights Claude-style CLI).

Thandv loads skills as flat `<stem>.md` files (body only, no frontmatter) from
~/.thandv/skills/, and — with the disk-persona patch — user personas as
`<name>.json` from ~/.thandv/personas/. So:

  agent-forge skill  -> dist/thandv/skills/<stem>.md          (frontmatter stripped)
  agent-forge agent  -> dist/thandv/personas/<name>.json      (body = system_prompt)

Each generated persona attaches Thandv's built-in `tool-use` and `honesty`
skills so it behaves like a native persona, plus the agent's specialized prompt.
Install with `scripts/install.sh --tool thandv` (-> ~/.thandv). Thandv never
executes skill scripts, so only the prompt text crosses over. Read/copy only.
"""
from __future__ import annotations

from pathlib import Path

from . import common

TOOL = "thandv"
BASE_SKILLS = ["tool-use", "honesty"]


def emit(items: list[common.Item], out_root: Path) -> dict:
    root = out_root / TOOL
    skills_dir = root / "skills"
    personas_dir = root / "personas"
    skills_dir.mkdir(parents=True, exist_ok=True)
    personas_dir.mkdir(parents=True, exist_ok=True)
    n_a = n_s = 0
    for it in items:
        if it.kind == "skill":
            # Body only — Thandv concatenates the file text into the prompt.
            common.safe_join(skills_dir, common.slug(it.name) + ".md").write_text(
                it.body.lstrip("\n"), encoding="utf-8")
            n_s += 1
        else:
            persona = {
                "name": common.slug(it.name),
                "description": it.description,
                "system_prompt": it.body.lstrip("\n"),
                "skills": BASE_SKILLS,
                "eval_suite": "smoke",
                "_source": {"domain": it.domain, "repo": it.source_repo,
                            "license": it.license},
            }
            common.safe_join(personas_dir, common.slug(it.name) + ".json").write_text(
                common.json.dumps(persona, indent=2) + "\n", encoding="utf-8")
            n_a += 1
    return {"tool": TOOL, "agents": n_a, "skills": n_s, "root": str(root)}
