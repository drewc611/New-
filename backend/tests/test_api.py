"""Integration tests for AMIE backend."""
from __future__ import annotations


def test_health_live(client):
    r = client.get("/api/health/live")
    assert r.status_code == 200
    assert r.json() == {"live": True}


def test_health_returns_db_flag(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert "db_ok" in body
    assert body["llm_provider"] == "mock"


def test_chat_creates_conversation(client, monkeypatch):
    # Bypass retrieval for tests (mongomock-motor does not load the embedding model)
    from app.services import orchestrator as o

    async def _no_retrieve(_q, **_kw):
        return []

    monkeypatch.setattr(o, "retrieve", _no_retrieve)

    r = client.post("/api/chat", json={"message": "What does DPV Y mean?"})
    assert r.status_code == 200
    body = r.json()
    assert body["conversation_id"]
    assert body["message"]["role"] == "assistant"
    assert "mock response" in body["message"]["content"].lower()


def test_chat_address_triggers_tool(client, monkeypatch):
    from app.services import orchestrator as o

    async def _no_retrieve(_q, **_kw):
        return []

    monkeypatch.setattr(o, "retrieve", _no_retrieve)

    r = client.post(
        "/api/chat",
        json={"message": "Please verify 1600 Pennsylvania Ave, Washington, DC 20500"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tool_calls"]
    assert body["tool_calls"][0]["name"] == "address_verify"
    assert body["address_result"] is not None


def test_tools_address_verify(client):
    r = client.post(
        "/api/tools/address/verify",
        json={"address": "1 Main St, Dallas, TX 75201"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["zip5"] == "75201"
    assert body["state"] == "TX"
    assert body["street_suffix"] == "ST"


def test_tools_address_verify_urbanization(client):
    r = client.post(
        "/api/tools/address/verify",
        json={"address": "URB Las Flores, 12 Calle Central, Ponce, PR 00716"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["urbanization"] == "LAS FLORES"
    assert body["state"] == "PR"


def test_conversation_roundtrip(client, monkeypatch):
    from app.services import orchestrator as o

    async def _no_retrieve(_q, **_kw):
        return []

    monkeypatch.setattr(o, "retrieve", _no_retrieve)

    first = client.post("/api/chat", json={"message": "Hello AMIE"}).json()
    conv_id = first["conversation_id"]

    listing = client.get("/api/conversations").json()
    assert any(c["id"] == conv_id for c in listing)

    fetched = client.get(f"/api/conversations/{conv_id}").json()
    assert fetched["id"] == conv_id
    assert len(fetched["messages"]) >= 2

    deleted = client.delete(f"/api/conversations/{conv_id}").json()
    assert deleted["deleted"] == conv_id
