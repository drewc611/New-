"""Pytest fixtures. Uses mongomock-motor to avoid a live MongoDB."""
from __future__ import annotations

import os

os.environ["LLM_PROVIDER"] = "mock"
os.environ["ADDRESS_VERIFIER"] = "mock"
os.environ["AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.core import mongo_client as mongo_mod
from app.llm import factory as llm_factory
from app.rag import retriever as retriever_mod
from app.services import address_analytics as aa_mod
from app.services import conversation_store as cs_mod
from app.tools import address_base as ab_mod


@pytest.fixture(autouse=True)
def patch_mongo(monkeypatch):
    """Replace the real Mongo client with an in-memory mock."""
    fake_client = AsyncMongoMockClient()

    def _fake_client():
        return fake_client

    def _fake_db():
        return fake_client["amie_test"]

    # Reset caches so the fresh fake is used everywhere.
    mongo_mod.get_mongo_client.cache_clear()
    mongo_mod.get_mongo_db.cache_clear()
    monkeypatch.setattr(mongo_mod, "get_mongo_client", _fake_client)
    monkeypatch.setattr(mongo_mod, "get_mongo_db", _fake_db)
    # Patch the names that consuming modules imported directly.
    monkeypatch.setattr(
        "app.services.conversation_store.get_mongo_db", _fake_db
    )
    monkeypatch.setattr("app.rag.retriever.get_mongo_db", _fake_db)
    monkeypatch.setattr(
        "app.services.address_analytics.get_mongo_db", _fake_db
    )

    retriever_mod._index_instance.cache_clear()
    cs_mod.get_conversation_store.cache_clear()
    aa_mod.get_analytics.cache_clear()
    ab_mod.get_verifier.cache_clear()
    llm_factory.get_llm_provider.cache_clear()
    yield


@pytest.fixture
def client():
    # Import create_app after env vars are set
    from app.main import create_app

    # Skip vector bootstrap (the mock KB load pulls sentence-transformers)
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
