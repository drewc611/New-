---
applyTo: "**/tests/**"
description: "Test conventions"
---

# Tests

## Principles

- Arrange / Act / Assert. One behavior per test.
- No network calls. `LLM_PROVIDER=mock` and `fakeredis` for Redis.
- Fast: under 5 seconds per test. Mark anything slower with `@pytest.mark.slow`.

## Python (backend)

- `pytest` + `pytest-asyncio`. Async tests use `@pytest.mark.asyncio`.
- Fixtures in `backend/tests/conftest.py`. Prefer small, composable fixtures.
- Use `httpx.AsyncClient` against the FastAPI app via `ASGITransport`.
- Name tests `test_<unit>_<condition>_<expected>`.

## Coverage

- New code ships with tests. Regressions ship with a failing-first test.
- Don't chase coverage for its own sake — cover behavior, not lines.
