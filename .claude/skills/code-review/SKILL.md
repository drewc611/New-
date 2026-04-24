---
name: code-review
description: Review the current diff against USPS AMIE conventions — Python type hints, Pydantic v2, async handlers, ruff style; React function components, typed API clients, Tailwind; provider-agnostic LLM layer preserved; tests don't hit the network.
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git log:*), Bash(ruff check:*)
---

# Code Review Skill

Review changes against this repo's conventions and design decisions.

## Checks

- **Correctness** — logic, edge cases, error paths.
- **Conventions** — Python type hints + Pydantic v2 models, async I/O, `ruff` clean; React function components + hooks, typed API client wrappers, Tailwind utilities.
- **Design decisions** — provider-agnostic LLM layer preserved (`ollama | anthropic | mock`); Redis Stack used for vectors/JSON/cache; `python-jose[cryptography]` not swapped for PyJWT; no second Redis client added.
- **Tests** — new behavior has tests; `LLM_PROVIDER=mock` and `fakeredis` used; no network calls.
- **Security** — no secrets in code; `defusedxml` for XML; auth on protected routes; no user input reaching a shell.
- **Accessibility** — 508 compliance for any UI changes (`docs/508-compliance.md`).

## Output

Group findings as `must-fix`, `should-fix`, `nit`. Cite `path:line` and propose a concrete replacement. End with: ship / ship-with-nits / rework.
