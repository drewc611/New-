"""FastAPI application entry point for USPS AMIE."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import auth, chat, conversations, health, tools
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.rag.retriever import bootstrap_if_needed


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger(__name__)
    log.info(
        "startup",
        app=settings.app_name,
        env=settings.app_env,
        llm_provider=settings.llm_provider,
        version=__version__,
    )

    try:
        from app.tools.address_overrides import apply_overrides

        apply_overrides()
    except Exception as e:
        log.warning("address_overrides_failed", error=str(e))

    try:
        await bootstrap_if_needed()
    except Exception as e:
        log.error("vector_bootstrap_failed", error=str(e))

    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="USPS AMIE",
        description="Address Management Intelligent Engine for USPS AMS workflows.",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        BodySizeLimitMiddleware, max_bytes=settings.request_max_body_bytes
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(tools.router)
    return app


app = create_app()
