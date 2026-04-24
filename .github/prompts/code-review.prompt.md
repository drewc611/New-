---
description: "Review the current diff for quality, safety, and project conventions"
model: claude-sonnet-4.6
agent: agent
---

# /code-review

Review the changes in the current diff against this repo's conventions.

## What to check

- **Correctness** — logic, edge cases, error paths.
- **Project conventions** — Python type hints, Pydantic v2 models, async handlers, `ruff` style; React function components, typed API clients, Tailwind classes.
- **Design decisions** — provider-agnostic LLM layer preserved; Redis Stack used for the three data roles; no `python-jose` → PyJWT swap; no new Redis client.
- **Tests** — new behavior has tests, tests don't hit the network, `fakeredis` used for Redis.
- **Security** — no secrets in code, XML parsing via `defusedxml`, auth on protected routes, no user input reaching a shell.
- **Accessibility** — 508 compliance for any UI changes.
- **Gotchas** — frontend build artifacts not committed, Helm `charts/` not committed.

## Output

Group findings as `must-fix`, `should-fix`, `nit`. For each, cite `path:line` and propose a concrete replacement. End with a one-sentence verdict: ship, ship with nits, or rework.
