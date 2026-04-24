# USPS AMIE Chatbot — Project Memory

FastAPI + React RAG assistant for USPS Address Management workflows, grounded in Publication 28 and AMS docs.

## Tech Stack

- Backend: FastAPI, Python 3.11, Pydantic v2, SSE streaming, structlog
- Frontend: React 18 + TypeScript + Vite + Tailwind
- Data: Redis Stack (RediSearch HNSW vectors, RedisJSON conversations, TTL cache)
- LLM: Ollama (local), Anthropic (dev/cloud), Mock (tests) — switch via `LLM_PROVIDER`
- Deploy: Docker Compose (local), Helm chart (K8s — vanilla, OpenShift, kind)
- Auth: Okta SSO (OIDC)

## Commands

```
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest
ruff check .

# Frontend
cd frontend
npm install
npm run dev
npm run build

# Full stack
docker compose up --build
```

## Architecture

- `backend/app/api/` — HTTP routers (chat, admin, health)
- `backend/app/core/` — config, logging, security
- `backend/app/llm/` — provider abstractions (ollama, anthropic, mock)
- `backend/app/rag/` — chunking, Redis vector index, prompt builders
- `backend/app/services/` — orchestrator, Redis conversation store
- `backend/app/tools/` — address verification tool
- `backend/content/` — markdown-driven knowledge base
- `frontend/src/` — React SPA
- `deploy/helm/usps-amie/` — Helm chart
- `docs/` — architecture, security, API, deployment

## Design Decisions

- **Provider-agnostic LLM layer**: `ollama | anthropic | mock` selected at runtime — no hard dependency on any vendor.
- **Markdown-driven content**: knowledge base lives in `backend/content/` as markdown, indexed into Redis at startup. See `docs/markdown-driven.md`.
- **Redis Stack (not separate DBs)**: RediSearch for vectors, RedisJSON for conversations, standard Redis for cache — one system, three roles.
- **508 compliance is required**, not optional. See `docs/508-compliance.md`.
- **Proprietary license** — USPS and authorized contractors only.

## Gotchas

- Set `LLM_PROVIDER=mock` for tests and keyless demos; tests must not hit the network.
- `python-jose[cryptography]` is the JWT lib — not PyJWT. Do not swap.
- `pydantic-settings` v2 — config lives in `backend/app/core/config.py`. Environment vars are read at import time; restart the process after changes.
- Windows local dev uses `scripts/start-windows.ps1` and Ollama Desktop, not the bundled container.
- Frontend build artifacts (`frontend/src/**/*.js`) are gitignored — don't commit compiled TS.
- Helm chart dependencies (`charts/`, `Chart.lock`) are gitignored — run `helm dep update` locally.

## Workflow

- Start each feature from a fresh branch; commit frequently.
- Drop specs in `cowork/outputs/` using `cowork/templates/spec.yaml` before coding non-trivial features.
- `AskUserQuestion` when scope is ambiguous — don't guess architecture.
- Run `ruff check` and `pytest` before declaring done.
