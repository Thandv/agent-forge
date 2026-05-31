"""Adapter: canonical registry -> Cursor layout.

Emits Cursor MDC rules (frontmatter: description, globs, alwaysApply):
  dist/cursor/.cursor/rules/<name>.mdc

Agents and skills both become manually-invokable rules (alwaysApply: false,
no globs) so the user opts in per task rather than loading everything always.
Skill scripts are not copied into a rule; the rule body references the skill's
source path. Read-only; never executes content.
"""
from __future__ import annotations

from pathlib import Path

from . import common

TOOL = "cursor"


def _mdc(description: str, body: str) -> str:
    fm = {"description": description, "globs": "", "alwaysApply": False}
    return common.build_frontmatter(fm) + "\n" + body.lstrip("\n")


def emit(items: list[common.Item], out_root: Path) -> dict:
    rules = out_root / TOOL / ".cursor" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    n_a = n_s = 0
    for it in items:
        dest = common.safe_join(rules, common.slug(it.name) + ".mdc")
        if it.kind == "agent":
            dest.write_text(_mdc(it.description, it.body), encoding="utf-8")
            n_a += 1
        else:
            body = it.body
            extras = [p for p in ("scripts", "references", "assets")
                      if (it.path / p).is_dir()]
            if extras:
                body += (f"\n\n---\n\n> This skill ships supporting "
                         f"{', '.join(extras)}. See the source skill directory "
                         f"`{it.source_repo or 'registry'}` (`{it.path.name}`).")
            dest.write_text(_mdc(it.description, body), encoding="utf-8")
            n_s += 1
    return {"tool": TOOL, "agents": n_a, "skills": n_s, "root": str(out_root / TOOL)}
