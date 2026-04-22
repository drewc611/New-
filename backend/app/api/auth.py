"""Auth discovery and user-info endpoints for the SPA.

The SPA performs the OIDC Authorization Code + PKCE flow directly
against Okta; the backend never sees the client secret and never issues
its own session. Instead it:

* Publishes a small, *public* JSON config at ``/api/auth/config`` that
  the SPA uses to decide whether to show a login screen and where to
  redirect.
* Validates every inbound bearer token against Okta's JWKS (see
  :mod:`app.core.security`).
* Exposes ``/api/auth/me`` so the SPA can render the signed-in user.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.security import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthConfig(BaseModel):
    enabled: bool
    provider: str  # "okta" | "generic" | "none"
    issuer: str
    client_id: str
    audience: str
    scopes: list[str]
    redirect_path: str = "/auth/callback"


class MeResponse(BaseModel):
    sub: str
    email: str
    name: str
    tenant: str
    groups: list[str]


@router.get("/config", response_model=AuthConfig)
async def auth_config(settings: Settings = Depends(get_settings)) -> AuthConfig:
    if not settings.auth_enabled:
        return AuthConfig(
            enabled=False,
            provider="none",
            issuer="",
            client_id="",
            audience="",
            scopes=[],
        )
    provider = "okta" if settings.okta_issuer else "generic"
    return AuthConfig(
        enabled=True,
        provider=provider,
        issuer=settings.effective_jwt_issuer,
        client_id=settings.okta_client_id,
        audience=settings.effective_jwt_audience,
        scopes=settings.okta_scopes_list,
    )


@router.get("/me", response_model=MeResponse)
async def me(user: dict = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        sub=user["sub"],
        email=user.get("email", ""),
        name=user.get("name", ""),
        tenant=user.get("tenant", "default"),
        groups=user.get("groups", []),
    )
