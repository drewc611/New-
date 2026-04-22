"""Retrieval facade.

Wraps :class:`RedisVectorIndex` with a cached singleton and helper entry
points used by the orchestrator and FastAPI lifespan hook.
"""
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


async def _index_is_populated(index: RedisVectorIndex) -> bool:
    try:
        info = await index._client.ft(index._index).info()
    except Exception:
        return False
    if isinstance(info, dict):
        count = info.get("num_docs") or info.get("numDocs") or 0
    else:
        count = 0
        for i, item in enumerate(info):
            if isinstance(item, (bytes, str)) and str(item) in ("num_docs", "numDocs"):
                count = info[i + 1]
                break
    try:
        return int(count) > 0
    except (TypeError, ValueError):
        return False


async def bootstrap_if_needed() -> None:
    """Ensure the vector index exists and is populated from the KB on boot."""
    s = get_settings()
    index = _index_instance()
    await index.ensure_index()
    if await _index_is_populated(index):
        log.info("vector_index_ready")
        return
    log.info("bootstrapping_vector_index", kb_path=s.kb_path)
    count = await build_from_knowledge_base(index, s.kb_path)
    log.info("vector_index_bootstrap_complete", chunks_indexed=count)


async def retrieve(query: str, top_k: int | None = None) -> list[Citation]:
    """Run a vector similarity search. Returns [] on any failure."""
    if not query or not query.strip():
        return []
    s = get_settings()
    k = top_k if top_k is not None else s.retrieval_top_k
    try:
        return await _index_instance().search(query, top_k=k)
    except Exception as e:
        log.warning("retrieval_failed", error=str(e))
        return []
