"""Top-level orchestration for the five-stage MMKG pipeline.

Wires stage 1 (parse) → stage 2 (route) → stage 3 (analyze, via router) →
stage 4 (graph ingest). Stage 5 (retrieval) is surfaced separately via
:class:`ModalityAwareRetriever`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.mmkg.graph import MultiModalKnowledgeGraph
from app.mmkg.parsers import parse_document
from app.mmkg.retrieval import ModalityAwareRetriever
from app.mmkg.router import ContentRouter, build_section_tree
from app.mmkg.schemas import GraphEntity, Modality, RetrievalHit

log = get_logger(__name__)


class MMKGPipeline:
    def __init__(
        self,
        graph: MultiModalKnowledgeGraph | None = None,
        router: ContentRouter | None = None,
    ) -> None:
        self._graph = graph or MultiModalKnowledgeGraph(get_redis())
        self._router = router or ContentRouter()

    async def ingest(
        self,
        *,
        doc_id: str | None = None,
        path: str | Path | None = None,
        content: str | None = None,
    ) -> list[GraphEntity]:
        blocks = parse_document(path=path, content=content, doc_id=doc_id)
        if not blocks:
            log.warning("mmkg_ingest_empty", doc_id=doc_id)
            return []
        resolved_id = blocks[0].doc_id
        section_tree = build_section_tree(blocks)
        analyzed = await self._router.route(blocks)
        return await self._graph.ingest(
            doc_id=resolved_id, analyzed=analyzed, section_tree=section_tree
        )

    async def query(
        self,
        query: str,
        doc_ids: list[str],
        top_k: int = 5,
        modality_bias: dict[Modality, float] | None = None,
    ) -> list[RetrievalHit]:
        retriever = ModalityAwareRetriever(self._graph, modality_bias=modality_bias)
        return await retriever.retrieve(query, doc_ids=doc_ids, top_k=top_k)


@lru_cache
def get_pipeline() -> MMKGPipeline:
    return MMKGPipeline()


async def ingest_document(
    *,
    doc_id: str | None = None,
    path: str | Path | None = None,
    content: str | None = None,
) -> list[GraphEntity]:
    """Module-level convenience wrapper."""
    return await get_pipeline().ingest(doc_id=doc_id, path=path, content=content)
