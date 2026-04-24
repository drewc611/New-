"""Multi-modal knowledge graph pipeline.

Five stages wired in order:

1. :mod:`app.mmkg.parsers` — adaptive document parsing.
2. :mod:`app.mmkg.router`  — content routing + hierarchy extraction.
3. :mod:`app.mmkg.analyzers` — modality-aware analysis engine.
4. :mod:`app.mmkg.graph`  — knowledge-graph index persisted in Redis.
5. :mod:`app.mmkg.retrieval` — vector + graph fusion retrieval.

The top-level entry point is :func:`app.mmkg.pipeline.ingest_document`.
"""
from __future__ import annotations

from app.mmkg.pipeline import MMKGPipeline, ingest_document
from app.mmkg.retrieval import ModalityAwareRetriever
from app.mmkg.schemas import (
    GraphEntity,
    GraphRelation,
    Modality,
    ParsedBlock,
    RetrievalHit,
)

__all__ = [
    "GraphEntity",
    "GraphRelation",
    "MMKGPipeline",
    "Modality",
    "ModalityAwareRetriever",
    "ParsedBlock",
    "RetrievalHit",
    "ingest_document",
]
