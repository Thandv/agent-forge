---
name: context-compaction
description: "Keep a long session lean: when and how to checkpoint and compact context so work continues without hitting the limit or paying for stale history. Use during long-running tasks, before/after big milestones, when context is filling up, or when responses slow down from accumulated history. Pairs with the token-optimizer agent and token-budget skill."
license: MIT
source:
  repo: original
  commit: original
  path: registry/skills/context-compaction/SKILL.md
---

# Context compaction

Long sessions accumulate context that becomes increasingly expensive and less
useful. Compact deliberately instead of waiting for an automatic cutover.

## Triggers

- A milestone or sub-task just finished (natural checkpoint).
- `/context` shows history dominating the window.
- Responses are slowing or quality is drifting from too much stale context.

## Procedure

1. **Checkpoint first.** Before compacting, write the durable state somewhere
   outside the conversation — a short notes file, a commit, or a task list — so
   nothing important depends only on history that compaction will summarize:
   - what was decided and why,
   - what's done vs. remaining,
   - exact file paths / commands needed to resume.

2. **Compact at the boundary.** Use `/compact` proactively at the checkpoint
   rather than near the limit. Structured compaction typically reclaims 60–80%
   of the window while preserving the summary.

3. **Trim standing context.** Use `/context` to see consumers (system prompt,
   tools, memory, skills, MCP servers, history). Disable MCP servers and skills
   not needed for the next phase; keep `CLAUDE.md` lean.

4. **Prefer fresh short sessions** for distinct phases over one ever-growing
   session. Resume from the checkpoint you wrote in step 1.

## Anti-patterns

- Compacting mid-sub-task (you lose working detail you still need).
- Relying on history as the only record of decisions — checkpoint instead.
- Letting unused MCP servers/skills tax every turn.
