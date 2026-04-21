"""Health check endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app import __version__
from app.core.config import Settings, get_settings
from app.core.redis_client import ping as redis_ping
from app.models.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    redis_ok = await redis_ping()
    return HealthResponse(
        status="ok" if redis_ok else "degraded",
        version=__version__,
        llm_provider=settings.llm_provider,
        redis_ok=redis_ok,
        env=settings.app_env,
    )


@router.get("/health/ready")
async def ready() -> dict:
    """Kubernetes readiness probe. Redis must be up to accept traffic."""
    ok = await redis_ping()
    return {"ready": ok}


@router.get("/health/live")
async def live() -> dict:
    """Kubernetes liveness probe. Always true if the process is responding."""
    return {"live": True}
