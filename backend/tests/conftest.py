"""Pytest fixtures. Uses fakeredis to avoid a live Redis dependency."""
from __future__ import annotations

import os

os.environ["LLM_PROVIDER"] = "mock"
os.environ["ADDRESS_VERIFIER"] = "mock"
os.environ["AUTH_ENABLED"] = "false"

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from app.core import redis_client as rc_mod
from app.llm import factory as llm_factory
from app.rag import retriever as retriever_mod
from app.services import conversation_store as cs_mod
from app.tools import address_base as ab_mod


@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    """Replace the real Redis client with fakeredis for every test."""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=False)

    def _fake_redis():
        return fake

    rc_mod.get_redis.cache_clear()
    monkeypatch.setattr(rc_mod, "get_redis", _fake_redis)
    # Patch the names that consuming modules imported directly.
    monkeypatch.setattr("app.services.conversation_store.get_redis", _fake_redis)
    monkeypatch.setattr("app.rag.retriever.get_redis", _fake_redis)

    # Rebind downstream singletons that captured the real client.
    retriever_mod._index_instance.cache_clear()
    cs_mod.get_conversation_store.cache_clear()
    ab_mod.get_verifier.cache_clear()
    llm_factory.get_llm_provider.cache_clear()
    yield


@pytest.fixture
def client():
    # Import create_app after env vars are set
    from app.main import create_app

    # Skip vector bootstrap (fakeredis lacks RediSearch commands)
    import app.rag.retriever as r

    async def _noop():
        return None

    async def _no_retrieve(_q, **_kw):
        return []

    r.bootstrap_if_needed = _noop  # type: ignore[assignment]
    r.retrieve = _no_retrieve  # type: ignore[assignment]

    # The orchestrator module captured `retrieve` at import time.
    import app.services.orchestrator as o

    o.retrieve = _no_retrieve  # type: ignore[assignment]

    return TestClient(create_app())
