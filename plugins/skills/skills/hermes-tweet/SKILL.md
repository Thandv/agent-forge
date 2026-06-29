---
name: hermes-tweet
description: "Use the Hermes Tweet Hermes Agent plugin for X/Twitter research, monitoring, and approval-gated account actions through Xquik."
license: MIT
source:
  repo: "https://github.com/Xquik-dev/hermes-tweet"
  commit: c26e245643e5e0cb29873fa67c78ada97e84cadb
  path: skills/hermes-tweet/SKILL.md
---

# Hermes Tweet

Use Hermes Tweet when an agent needs X/Twitter research, monitoring, or
carefully approved account actions through the Hermes Agent plugin.

## When to Use

- Search public X/Twitter posts, profiles, trends, and conversation context.
- Monitor launches, brands, communities, support topics, and creators.
- Prepare account actions such as posts, replies, likes, follows, DMs,
  monitors, extraction jobs, media operations, and giveaway draws.
- Verify which Xquik API route fits a request before reading or acting.

## Workflow

1. Install and enable the plugin:
   `hermes plugins install Xquik-dev/hermes-tweet --enable`.
2. Configure `XQUIK_API_KEY` in the Hermes runtime environment.
3. Keep `HERMES_TWEET_ENABLE_ACTIONS=false` unless the session explicitly
   allows account-changing actions.
4. Use `tweet_explore` first to find a catalog-listed endpoint.
5. Use `tweet_read` for public read-only endpoints.
6. Use `tweet_action` only after the user approves the exact endpoint and
   payload.

## Safety

- Never ask for, echo, or pass API keys, cookies, passwords, signing keys, or
  TOTP secrets in chat or tool arguments.
- Do not guess endpoint paths or call direct HTTP fallbacks.
- Use only catalog-listed `/api/v1/...` routes returned by `tweet_explore`.
- Treat writes, private reads, monitors, webhooks, extraction jobs, media
  operations, and giveaway draws as gated actions.
- Summarize side effects before any account-changing call.

## Expected Tools

- `tweet_explore`: endpoint and capability discovery without live X/Twitter
  reads.
- `tweet_read`: authenticated reads for catalog-listed read-only routes.
- `tweet_action`: approval-gated writes, private reads, monitors, jobs, and
  media workflows.

## Troubleshooting

- If the plugin is installed but not active, run
  `hermes plugins enable hermes-tweet`.
- If tools are missing, run `hermes tools list` and confirm the
  `hermes-tweet` toolset is enabled.
- If reads fail, check that `XQUIK_API_KEY` exists in the runtime environment
  without printing its value.
- If actions are unavailable, confirm that `HERMES_TWEET_ENABLE_ACTIONS=true`
  is intentional for the current session.
