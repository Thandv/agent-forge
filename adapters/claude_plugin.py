"""Adapter: canonical registry -> a Claude Code *plugin marketplace*.

Emits a marketplace whose plugins are grouped by domain, installable with:
    /plugin marketplace add <path-to>/dist/claude-plugin
    /plugin install agentforge-optimization@agent-forge

Layout:
  dist/claude-plugin/
    .claude-plugin/marketplace.json
    plugins/<domain>/.claude-plugin/plugin.json
    plugins/<domain>/agents/<name>.md
    plugins/skills/skills/<name>/...

This is additive to the claude_code adapter (which stays the flat ~/.claude
symlink layout). Read/copy only; never executes content.
"""
from __future__ import annotations

from pathlib import Path

from . import common

TOOL = "claude-plugin"
VERSION = "0.1.0"


def _agent_md(it: common.Item) -> str:
    fm = {"name": common.slug(it.name), "description": it.description}
    if it.model:
        fm["model"] = it.model
    if it.tools:
        fm["tools"] = it.tools
    return common.build_frontmatter(fm) + "\n" + it.body.lstrip("\n")


def emit(items: list[common.Item], out_root: Path) -> dict:
    """Standard adapter entrypoint: emit under out_root/claude-plugin."""
    r = emit_to(items, out_root / TOOL)
    return {"tool": TOOL, **r, "root": str(out_root / TOOL)}


def emit_to(items: list[common.Item], root: Path) -> dict:
    """Emit a Claude Code plugin marketplace directly into `root`.

    Used both for dist/claude-plugin (via emit) and for the committed root
    marketplace at the repo root (via scripts/build_marketplace.py).
    """
    plugins_dir = root / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    by_domain: dict[str, list] = {}
    skills = []
    for it in items:
        if it.kind == "agent":
            by_domain.setdefault(it.domain or "general", []).append(it)
        else:
            skills.append(it)

    plugins_meta = []

    for domain, agents in sorted(by_domain.items()):
        pname = f"agentforge-{domain}"
        pdir = common.safe_join(plugins_dir, domain)
        (pdir / "agents").mkdir(parents=True, exist_ok=True)
        (pdir / ".claude-plugin").mkdir(parents=True, exist_ok=True)
        for it in agents:
            common.safe_join(pdir / "agents", common.slug(it.name) + ".md").write_text(
                _agent_md(it), encoding="utf-8")
        desc = f"agent-forge {domain} agents ({len(agents)})."
        (pdir / ".claude-plugin" / "plugin.json").write_text(
            common.json.dumps({"name": pname, "version": VERSION, "description": desc},
                              indent=2) + "\n", encoding="utf-8")
        plugins_meta.append({"name": pname, "source": f"./plugins/{domain}",
                             "description": desc, "version": VERSION,
                             "license": "MIT", "category": domain})

    if skills:
        pdir = common.safe_join(plugins_dir, "skills")
        (pdir / ".claude-plugin").mkdir(parents=True, exist_ok=True)
        for it in skills:
            common.copy_tree_confined(it.path, common.safe_join(pdir / "skills", common.slug(it.name)))
        desc = f"agent-forge skills ({len(skills)})."
        (pdir / ".claude-plugin" / "plugin.json").write_text(
            common.json.dumps({"name": "agentforge-skills", "version": VERSION,
                               "description": desc}, indent=2) + "\n", encoding="utf-8")
        plugins_meta.append({"name": "agentforge-skills", "source": "./plugins/skills",
                             "description": desc, "version": VERSION,
                             "license": "Apache-2.0", "category": "skills"})

    marketplace = {
        "name": "agent-forge",
        "owner": {"name": "agent-forge", "url": "https://github.com/Thandv/agent-forge"},
        "metadata": {
            "description": "Security-gated, multi-tool collection of open-source AI "
                           "coding agents & skills. Granular per-domain plugins.",
            "version": VERSION,
        },
        "plugins": plugins_meta,
    }
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "marketplace.json").write_text(
        common.json.dumps(marketplace, indent=2) + "\n", encoding="utf-8")

    n_a = sum(len(v) for v in by_domain.values())
    return {"agents": n_a, "skills": len(skills)}
