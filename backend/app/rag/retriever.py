"""Retrieval facade.

Wraps :class:`MongoVectorIndex` with a cached singleton and helper
entry points used by the orchestrator and FastAPI lifespan hook.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.mongo_client import get_mongo_db
from app.models.schemas import Citation
from app.rag.indexer import MongoVectorIndex, build_from_knowledge_base

log = get_logger(__name__)


@lru_cache
def _index_instance() -> MongoVectorIndex:
    s = get_settings()
    return MongoVectorIndex(
        db=get_mongo_db(),
        collection_name=s.mongo_vectors_collection,
        embedding_model=s.embedding_model,
        dim=s.embedding_dim,
        use_atlas_vector_search=s.mongo_use_atlas_vector_search,
        atlas_index_name=s.mongo_atlas_vector_index_name,
    )


async def bootstrap_if_needed() -> None:
    """Ensure the vectors collection exists and is populated from the KB."""
    s = get_settings()
    index = _index_instance()
    await index.ensure_index()
    count = await index.count()
    if count > 0:
        log.info("vector_index_ready", count=count)
        return
    log.info("bootstrapping_vector_index", kb_path=s.kb_path)
    indexed = await build_from_knowledge_base(index, s.kb_path)
    log.info("vector_index_bootstrap_complete", chunks_indexed=indexed)


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
