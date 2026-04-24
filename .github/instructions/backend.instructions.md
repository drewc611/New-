---
applyTo: "backend/**"
description: "Python / FastAPI backend conventions"
---

# Backend (FastAPI + Python 3.11)

## Language and style

- Python 3.11, full type hints, Pydantic v2 models at all boundaries.
- `ruff` clean — 100-char lines, sorted imports, no unused code.
- `async def` for handlers and I/O. Do not block the event loop.
- Log via `structlog` with a bound context; never use `print`.

## Structure

- Routers live in `backend/app/api/`, one module per resource. Keep routers thin — delegate to `services/`.
- Config in `backend/app/core/config.py` (pydantic-settings v2). Read env once; restart after changes.
- LLM providers in `backend/app/llm/` must implement the shared interface so `ollama | anthropic | mock` stay interchangeable.
- RAG code in `backend/app/rag/` — chunking, Redis vector index, prompt builders. Keep them pure and testable.
- Orchestration in `backend/app/services/` — tie RAG, LLM, tools, and the Redis conversation store together.

## Dependencies — do not swap

- `python-jose[cryptography]` for JWT (not PyJWT).
- `redis` (Redis Stack client) — don't add a second Redis client.
- `sentence-transformers` for embeddings — if you change models, update the index dimension and reindex.
- `defusedxml` anywhere XML touches user input.

## Tests

- `pytest` + `pytest-asyncio`. Use `fakeredis` for Redis.
- Set `LLM_PROVIDER=mock` — tests must not hit the network.
- Put fixtures in `backend/tests/conftest.py`. One behavior per test.
