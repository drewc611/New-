---
name: security-review
description: Security review of pending changes on the current branch — auth, input validation, prompt injection, XML, shell injection, SSRF, secrets, Redis, Docker/Helm, 508. Auto-invoke when the user asks for a security review, threat model check, or vulnerability scan.
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git log:*)
---

# Security Review

Focus on the OWASP top ten and the AMIE threat model (`docs/security.md`).

## Scope

- **Auth** — Okta OIDC, JWT via `python-jose[cryptography]`, token lifetime, refresh.
- **Input validation** — Pydantic v2 at all HTTP boundaries; no raw `request.json()` into the LLM.
- **Prompt injection** — user content reaching LLM prompts, tool calls, RAG context.
- **XML** — must use `defusedxml`.
- **Shell / command injection** — nothing user-controlled reaches `subprocess` unescaped.
- **SSRF** — outbound HTTP allowlisted to Ollama, Anthropic, and configured endpoints.
- **Secrets** — no keys, tokens, passwords in code, tests, fixtures.
- **Redis** — no eval/script with user input; keys namespaced; TTLs on cache.
- **Docker / Helm** — non-root, no privileged, no hostPath.
- **508** — accessibility regressions count.

## Output

Findings as `critical | high | medium | low | info`. For each: `path:line`, what, why it matters, specific fix. End with a one-line recommendation.
