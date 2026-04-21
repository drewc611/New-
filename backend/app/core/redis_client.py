"""Redis client singleton. Uses redis-py with async support."""
from __future__ import annotations

from functools import lru_cache

import redis.asyncio as redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    s = get_settings()
    return redis.Redis.from_url(
        s.redis_url,
        decode_responses=False,  # we store bytes for vectors
        encoding="utf-8",
        health_check_interval=30,
    )


async def ping() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False
