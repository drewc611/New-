---
name: testing-patterns
description: Scaffold pytest tests for backend code following AMIE conventions — pytest-asyncio, fakeredis, LLM_PROVIDER=mock, AAA structure, one behavior per test, no network calls. Auto-invoke when the user asks for tests, scaffolds tests, or fixes failing tests in backend/.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(pytest:*)
---

# Testing Patterns

## Rules

- `pytest` + `pytest-asyncio`. Async tests use `@pytest.mark.asyncio`.
- Arrange / Act / Assert. One behavior per test.
- `LLM_PROVIDER=mock` and `fakeredis` — never hit the network.
- FastAPI HTTP tests through `httpx.AsyncClient` + `ASGITransport`.
- Fixtures in `backend/tests/conftest.py`. Small, composable.
- Name tests `test_<unit>_<condition>_<expected>`.

## Template

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_<unit>_<condition>_<expected>(<fixtures>):
    # Arrange
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Act
        response = await client.post("/path", json={...})
    # Assert
    assert response.status_code == 200
    assert response.json() == {...}
```

## Output

- Test file at `backend/tests/test_<module>.py`.
- Happy path + at least one edge case + one failure case.
- Run `pytest -q` mentally before handing back.
