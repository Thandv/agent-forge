---
name: token-budget
description: "Estimate the token cost of files or directories BEFORE reading them, so you spend context only where it pays off. Use when about to read many/large files, when deciding what to load into context, when a session is getting expensive, or when planning a repo-wide task. Pairs with the token-optimizer agent."
license: MIT
source:
  repo: original
  commit: original
  path: registry/skills/token-budget/SKILL.md
---

# Token budget

Spend context deliberately. Before reading a pile of files, estimate what each
will cost and read only what the task needs.

## When to use

- You're about to read many files or a few large ones.
- The session is approaching the context limit or getting expensive.
- You're scoping a repo-wide change and want to target the smallest useful set.

## Workflow

1. Estimate cost across the candidate set:
   ```bash
   python3 scripts/estimate_tokens.py path/to/dir --by-file --top 20
   ```
   This prints an approximate token count per file (descending) and a total. It
   is a heuristic (≈ chars/4, with a word-based cross-check), offline, and reads
   files only — no network, no execution.

2. Decide:
   - **Small total** → read directly.
   - **Large total** → read only the top-ranked files relevant to the task, or
     delegate exploration to a subagent that returns a summary (see the
     `token-optimizer` agent), rather than loading everything.

3. Prefer targeted reads (line ranges, grep hits) and diffs over whole-file reads
   and rewrites.

## Notes

- The estimate is a planning aid, not an exact tokenizer; different models
  tokenize differently. Treat it as relative guidance for *what to read*.
- Combine with `/context` (where your tokens are already going) and `/compact`
  (reclaim space at milestones).
