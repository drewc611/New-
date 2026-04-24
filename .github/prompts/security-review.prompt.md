---
description: "Security review of the pending changes on the current branch"
model: claude-opus-4.7
agent: agent
---

# /security-review

Perform a security review focused on the OWASP top ten and this project's threat model (see `docs/security.md`).

## Scope

- Auth flows — Okta OIDC, JWT handling via `python-jose[cryptography]`, token lifetime, refresh.
- Input validation — Pydantic v2 at all HTTP boundaries; no raw `request.json()` into the LLM.
- Prompt injection — user-provided content going into LLM prompts, tool calls, or RAG context.
- XML — must use `defusedxml`.
- Shell / command injection — nothing user-controlled reaches `subprocess` unescaped.
- SSRF — outbound HTTP is restricted to allowlisted hosts (Ollama, Anthropic).
- Secrets — no keys, tokens, or passwords in code, tests, or fixtures.
- Redis — no eval / script with user input, keys namespaced, TTLs on cache.
- Docker / Helm — non-root containers, no privileged mode, no hostPath.
- 508 compliance is a requirement — call out regressions.

## Output

List findings as `critical`, `high`, `medium`, `low`, `info`. For each: where (`path:line`), what, why it matters, and a specific fix. End with a one-line recommendation.
