# Security Policy

Security is the top priority of this project. We aggregate third-party agents and
skills from the open-source ecosystem, and **all upstream content is treated as
untrusted** until it passes the automated security gate described below.

## Threat model

| Threat | Vector | Mitigation |
| --- | --- | --- |
| Supply-chain code execution | A vendored skill ships `scripts/` (Python/bash) that run on the user's machine | `scripts/scan.py` flags `curl\|bash`, `eval`, `exec`, `os.system`, `subprocess(shell=True)`, `pickle.loads`, base64-decoded-and-executed blobs, dynamic `__import__`/`importlib` |
| Credential / data exfiltration | Skill scripts read secrets and phone home | Scanner flags outbound network use (`requests`, `urllib`, `socket`, `nc`) and reads of `~/.ssh`, `~/.aws`, `.env`, `*_TOKEN`/`*_KEY`/`*_SECRET`, keychain |
| Destructive operations | `rm -rf`, `dd`, `mkfs`, writes outside the skill dir | Scanner flags these patterns |
| Prompt injection | Hidden instructions embedded in agent/skill markdown | Scanner flags injection markers ("ignore previous instructions", fake tool-call blocks) and zero-width / bidi Unicode tricks |
| Tampered upstream | An upstream force-push changes content | Every source is pinned to an exact commit SHA; `sources/lock.json` records a SHA-256 of each vendored file. A hash mismatch fails the build |
| Path traversal on install | A crafted item name escapes the install target | `scripts/install.sh` and the adapters resolve and confine every path to the chosen target; `..`/absolute escapes are rejected |
| Dependency attack surface | Malicious transitive deps | Repo tooling is **stdlib-only** (Python 3 + bash). No `pip install`, no `npm install` |

## Guarantees of the build/install tooling

1. **Nothing vendored is executed** during `sync`, `scan`, `validate`, `build`, or
   `install`. The tooling only reads, copies, and symlinks files. Skill scripts run
   later only when the end user's tool invokes them, by explicit user action.
2. **The scanner is a hard gate.** `scripts/sync.sh` and CI fail the build on any
   finding. Flagged items are **quarantined** (rejected and listed in
   `catalog.yaml` with the reason) — never silently stripped or hidden.
3. **Our own scripts are safe-by-construction**: no `eval`, no `shell=True`,
   confined paths, `--dry-run` available, no-clobber by default, no network except
   in `sync.sh`, no secrets.

## Reporting a vulnerability

Open a private security advisory on the repository, or email the maintainers.
Please do not file public issues for undisclosed vulnerabilities. Include the
affected file/path, the upstream source if relevant, and reproduction steps.

## Reviewing vendored content yourself

- `sources/manifest.yaml` — every upstream, pinned SHA, license, vendor/submodule mode.
- `sources/lock.json` — SHA-256 of every vendored file.
- `THIRD_PARTY.md` — human-readable attribution and licenses.
- `python3 scripts/scan.py registry` — re-run the scanner over the vendored tree at any time.
