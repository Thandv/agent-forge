"""Adapter: canonical registry -> Claude Code layout.

Emits:
  dist/claude-code/agents/<name>.md          (frontmatter: name, description, model)
  dist/claude-code/skills/<name>/SKILL.md     (full skill directory, copied)

Install target is typically ~/.claude (agents -> ~/.claude/agents, skills ->
~/.claude/skills). Read/copy only; never executes content.
"""
from __future__ import annotations

from pathlib import Path

from . import common

TOOL = "claude-code"


def emit(items: list[common.Item], out_root: Path) -> dict:
    root = out_root / TOOL
    agents_dir = root / "agents"
    skills_dir = root / "skills"
    agents_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)
    n_a = n_s = 0
    for it in items:
        if it.kind == "agent":
            fm = {"name": common.slug(it.name), "description": it.description}
            if it.model:
                fm["model"] = it.model
            if it.tools:
                fm["tools"] = it.tools
            dest = common.safe_join(agents_dir, common.slug(it.name) + ".md")
            dest.write_text(common.build_frontmatter(fm) + "\n" + it.body.lstrip("\n"),
                            encoding="utf-8")
            n_a += 1
        else:
            dest = common.safe_join(skills_dir, common.slug(it.name))
            common.copy_tree_confined(it.path, dest)
            n_s += 1
    return {"tool": TOOL, "agents": n_a, "skills": n_s, "root": str(root)}
