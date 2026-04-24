---
description: "Draft a spec in cowork/outputs/ before implementing a non-trivial feature"
model: claude-opus-4.7
agent: agent
---

# /spec

Before writing code for a non-trivial feature, draft a spec using `cowork/templates/spec.yaml`.

## Steps

1. Ask me clarifying questions if scope is ambiguous — do not guess.
2. Copy `cowork/templates/spec.yaml` to `cowork/outputs/<short-feature-name>.yaml`.
3. Fill in:
   - `goal` — short, clear, written for the agent.
   - `decisions` — architectural or scope choices and their rationale (the WHY).
   - `steps` — ordered `implement` / `verify` actions.
   - `done` — the checklist that makes this shippable.
4. Show me the filled-in spec. Wait for approval before implementing.

## Principles

- Avoid vibe coding. Spec first, code second.
- Document the why, not the what.
