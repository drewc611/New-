"""Retrieval service. Wraps the Redis vector index with a singleton loader."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.models.schemas import Citation
from app.rag.indexer import RedisVectorIndex, build_from_knowledge_base

log = get_logger(__name__)


@lru_cache
def _index_instance() -> RedisVectorIndex:
    s = get_settings()
    return RedisVectorIndex(
        client=get_redis(),
        index_name=s.redis_vector_index,
        embedding_model=s.embedding_model,
        dim=s.embedding_dim,
    )


async def bootstrap_if_needed() -> None:
    """Build the vector index from the knowledge base if empty."""
    s = get_settings()
    idx = _index_instance()
    await idx.ensure_index()
    # Count keys in vector namespace
    cursor = 0
    has_any = False
    async for _ in get_redis().scan_iter(match="amie:vec:*", count=1):
        has_any = True
        break
    if has_any:
        log.info("vector_index_already_populated")
        return
    log.info("bootstrapping_vector_index", kb=s.kb_path)
    await build_from_knowledge_base(idx, s.kb_path)


async def retrieve(query: str, top_k: int | None = None) -> list[Citation]:
    s = get_settings()
    k = top_k or s.retrieval_top_k
    return await _index_instance().search(query, top_k=k)
