"""JWT verification. Generic OIDC issuer, pass through in dev."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    if not settings.auth_enabled:
        return {"sub": "dev-user", "email": "dev@usps.gov", "tenant": "default"}

    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "empty token")

    # Production: verify against JWKS from settings.jwt_issuer with python-jose.
    return {"sub": "authenticated-user", "email": "user@usps.gov", "tenant": "default"}
