# Cowork

Spec-first workspace for AI coding agents on this repo. Use it whether you're driving Copilot, Claude Code, or any other AGENTS.md-aware tool.

## Folder protocol

| Folder | Read | Write | Purpose |
|---|---|---|---|
| `about-me.md` | yes | rarely | Who's working on this and how they prefer to work |
| `writing-style.md` | yes | rarely | Anti-AI-slop rules for prose / docs / commit messages |
| `templates/` | yes | no (treat as read-only) | Canonical templates — copy, don't edit in place |
| `outputs/` | yes | yes | Where agents write specs, plans, scratch notes, summaries |

The agent's rule: **read `about-me.md`, `writing-style.md`, and any relevant template before each task; write only into `outputs/`.**

## Daily workflow

1. **Plan in chat, build with the agent.** Talk through what you want. When the shape is clear, hand off.
2. **Spec first.** For anything non-trivial, ask the agent to draft a spec (`/spec` in Copilot or Claude Code) using `templates/spec.yaml` and save to `outputs/<kebab-name>.yaml`.
3. **Approve, then implement.** Don't let the agent code until the spec is signed off.
4. **AskUserQuestion is always on.** If scope is ambiguous, the agent asks instead of guessing.
5. **One topic per session.** New topic = new chat. Don't drag stale context forward.
6. **Summarize every 15–20 messages.** Long threads burn tokens re-reading themselves.
7. **Pick the right model.** Haiku for trivial edits, Sonnet for feature work, Opus for architecture and security work.

## What never goes in this folder

- Secrets, API keys, customer PII.
- Generated code (those go in `backend/` or `frontend/`).
- Anything that should be in git history of the source tree (commit those normally).

## Naming

`outputs/<topic>_<type>_v<n>.<ext>` — e.g. `outputs/redis-cache_spec_v1.yaml`, `outputs/okta-flow_plan_v2.md`.
