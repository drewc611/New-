"""Coverage for the auth discovery and user endpoints."""
from __future__ import annotations


def test_auth_config_when_disabled(client):
    r = client.get("/api/auth/config")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["provider"] == "none"
    assert body["client_id"] == ""


def test_me_returns_dev_user_when_auth_disabled(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["sub"] == "dev-user"
    assert body["email"].endswith("@usps.gov")
    assert isinstance(body["groups"], list)


def test_auth_config_advertises_okta_when_configured(client, monkeypatch):
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("OKTA_ENABLED", "true")
    monkeypatch.setenv("OKTA_ISSUER", "https://dev-12345.okta.com/oauth2/default")
    monkeypatch.setenv("OKTA_CLIENT_ID", "0oaTestClient")
    monkeypatch.setenv("OKTA_AUDIENCE", "api://usps-amie")

    try:
        r = client.get("/api/auth/config")
        assert r.status_code == 200
        body = r.json()
        assert body["enabled"] is True
        assert body["provider"] == "okta"
        assert body["issuer"] == "https://dev-12345.okta.com/oauth2/default"
        assert body["client_id"] == "0oaTestClient"
        assert body["audience"] == "api://usps-amie"
        assert "openid" in body["scopes"]
    finally:
        get_settings.cache_clear()
