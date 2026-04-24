# USPS AMIE Chatbot — Copilot Instructions

Repository-wide instructions for GitHub Copilot (all Claude models: Sonnet, Opus, Haiku). Copilot auto-loads this file at the start of every chat.

## What this project is

A conversational AI assistant for USPS Address Management System workflows. FastAPI backend, React SPA, Redis Stack for vectors/conversations/cache, pluggable LLM providers. Grounded in Publication 28 and AMS documentation via RAG.

## Tech stack

- Backend: FastAPI, Python 3.11, Pydantic v2, SSE streaming, structlog
- Frontend: React 18 + TypeScript + Vite + Tailwind
- Data: Redis Stack (RediSearch HNSW vectors, RedisJSON, TTL cache)
- LLM: Ollama (local), Anthropic (dev/cloud), Mock (tests) — selected by `LLM_PROVIDER`
- Deploy: Docker Compose, Helm chart (works on vanilla k8s, OpenShift, kind)
- Auth: Okta OIDC

## Commands

```
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest
ruff check .

# Frontend
cd frontend && npm install && npm run dev
npm run build

# Full stack
docker compose up --build
```

## Repo layout

- `backend/app/api/` — HTTP routers
- `backend/app/core/` — config, logging, security
- `backend/app/llm/` — provider abstractions
- `backend/app/rag/` — chunking, Redis vector index, prompt builders
- `backend/app/services/` — orchestrator, conversation store
- `backend/app/tools/` — address verification
- `backend/content/` — markdown knowledge base
- `frontend/src/` — React SPA
- `deploy/helm/usps-amie/` — Helm chart
- `docs/` — architecture, security, API, deployment

## Conventions

- Python: type hints required, Pydantic v2 models for all I/O, `ruff` clean, 100-char lines.
- Async-by-default in FastAPI routers and the LLM layer.
- Tests: pytest with `fakeredis` and `LLM_PROVIDER=mock`. Never hit the network in tests.
- Frontend: function components + hooks, Tailwind utility classes, no CSS modules.
- Commit messages: imperative mood, scope prefix (`backend:`, `frontend:`, `deploy:`, `docs:`).
- Follow the spec-first workflow — drop a spec in `cowork/outputs/` using `cowork/templates/spec.yaml` before implementing non-trivial features.

## Design decisions (don't undo these)

- Provider-agnostic LLM layer (`ollama | anthropic | mock`) — no hard vendor lock-in.
- Markdown-driven knowledge base indexed at startup — see `docs/markdown-driven.md`.
- Redis Stack for all three data roles (vectors, JSON conversations, TTL cache).
- 508 accessibility compliance is required — see `docs/508-compliance.md`.
- Proprietary license — USPS and authorized contractors only.

## Gotchas

- `python-jose[cryptography]` is the JWT library, not PyJWT. Do not swap.
- `pydantic-settings` v2 reads env at import time — restart after edits.
- Windows dev uses `scripts/start-windows.ps1` and Ollama Desktop, not the container.
- Frontend compiled `.js` is gitignored — don't commit build output.
- Helm `charts/` and `Chart.lock` are gitignored — run `helm dep update` locally.

## How Copilot should behave here

- Ask clarifying questions when scope is ambiguous rather than guessing architecture.
- Prefer editing existing files over creating new ones.
- Don't add features, abstractions, or error handling beyond what the task requires.
- Don't add comments that restate the code. Only note non-obvious WHY.
- When fixing a test failure, diagnose the root cause — don't silence the assertion.

## Model guidance (Copilot model picker)

Copilot supports the full Claude lineup. Pick from the model picker in chat (or pin via `model:` frontmatter in a prompt file):

| Model | Use it for |
|---|---|
| `claude-opus-4.7` | Architecture, multi-file refactors, RAG/prompt tuning, security review. Highest premium multiplier — use when it matters. |
| `claude-opus-4.6` | Same as 4.7 when 4.7 is throttled or you want the cheaper Opus tier. `claude-opus-4.6 (fast mode)` for snappier output. |
| `claude-opus-4.5` | Long-context architecture work where the older Opus is sufficient. |
| `claude-sonnet-4.6` | **Default for feature work, bug fixes, PR reviews.** Best speed-to-quality trade. |
| `claude-sonnet-4.5` | Fallback when 4.6 isn't available. |
| `claude-sonnet-4` | Legacy fallback. |
| `claude-haiku-4.5` | Quick edits, renames, doc tweaks, test scaffolds, lint cleanup. Cheapest tier. |

The repo's prompt files in `.github/prompts/` already pin sensible defaults. Override per-chat via the picker if you need to.
