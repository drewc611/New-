---
description: "Scaffold pytest tests following repo conventions"
model: claude-haiku-4.5
agent: agent
---

# /testing-patterns

Generate pytest tests for the code I point you at, following this repo's conventions.

## Rules

- `pytest` + `pytest-asyncio`. Async tests use `@pytest.mark.asyncio`.
- Arrange / Act / Assert. One behavior per test.
- `LLM_PROVIDER=mock` and `fakeredis` — never hit the network.
- FastAPI HTTP tests go through `httpx.AsyncClient` + `ASGITransport`.
- Fixtures in `backend/tests/conftest.py`. Small, composable.
- Name tests `test_<unit>_<condition>_<expected>`.

## Output

- A test file at the canonical location (`backend/tests/test_<module>.py`).
- Include happy path, at least one edge case, and one failure case.
- Run `pytest -q` in your head first — if a test would fail as written, fix it before handing back.
