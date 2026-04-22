"""JWT verification and request hardening.

When ``auth_enabled`` is False the app attributes every request to
``dev-user``. When it is True the request must carry a Bearer token that
validates against the configured OIDC issuer's JWKS endpoint.
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_JWKS_CACHE_TTL_SECONDS = 3600


class _JWKSCache:
    def __init__(self) -> None:
        self._jwks: dict[str, Any] | None = None
        self._fetched_at: float = 0.0

    def invalidate(self) -> None:
        self._jwks = None
        self._fetched_at = 0.0

    async def get(self, url: str) -> dict[str, Any]:
        now = time.time()
        if self._jwks and (now - self._fetched_at) < _JWKS_CACHE_TTL_SECONDS:
            return self._jwks
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            self._jwks = r.json()
            self._fetched_at = now
        return self._jwks


@lru_cache
def _jwks_cache() -> _JWKSCache:
    return _JWKSCache()


async def _verify_token(token: str, settings: Settings) -> dict[str, Any]:
    # Lazy import so the module loads in environments without cryptography
    # (for example the mock/dev path where auth_enabled=False).
    from jose import ExpiredSignatureError, JWTError, jwt

    if not settings.jwt_jwks_url:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "auth enabled but JWT_JWKS_URL is not configured",
        )
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token header") from e
    kid = header.get("kid")
    if not kid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token missing kid")

    jwks = await _jwks_cache().get(settings.jwt_jwks_url)
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        # refresh once in case of rotation
        _jwks_cache().invalidate()
        jwks = await _jwks_cache().get(settings.jwt_jwks_url)
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no matching JWKS key")

    options = {"verify_aud": bool(settings.jwt_audience)}
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=settings.jwt_algorithms_list,
            audience=settings.jwt_audience or None,
            issuer=settings.jwt_issuer or None,
            options=options,
        )
    except ExpiredSignatureError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expired") from e
    except JWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from e

    return claims


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    if not settings.auth_enabled:
        return {"sub": "dev-user", "email": "dev@usps.gov", "tenant": "default"}

    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "empty token")

    claims = await _verify_token(token, settings)
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token missing sub")
    return {
        "sub": sub,
        "email": claims.get("email", ""),
        "tenant": claims.get("tenant") or claims.get("org") or "default",
        "claims": claims,
    }
