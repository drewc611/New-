"""Async MongoDB client singleton.

Uses Motor (the official async MongoDB driver). A single client is
shared across the process and handed out as both the raw client and
bound to the configured database.
"""
from __future__ import annotations

from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings


@lru_cache
def get_mongo_client() -> AsyncIOMotorClient:
    s = get_settings()
    # ``tz_aware`` makes Motor return timezone-aware datetimes, matching
    # the timezone-aware _now_utc() used in the schemas.
    return AsyncIOMotorClient(s.mongo_uri, tz_aware=True, uuidRepresentation="standard")


@lru_cache
def get_mongo_db() -> AsyncIOMotorDatabase:
    s = get_settings()
    return get_mongo_client()[s.mongo_database]


async def ping() -> bool:
    try:
        await get_mongo_client().admin.command("ping")
        return True
    except Exception:
        return False
