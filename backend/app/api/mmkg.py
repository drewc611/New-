"""Admin API for the multimodal knowledge graph pipeline.

Exposes ingest + query endpoints. Both require an authenticated user —
this is an admin surface, not a public chat endpoint.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.mmkg.pipeline import MMKGPipeline, get_pipeline
from app.mmkg.schemas import GraphEntity, Modality, RetrievalHit

router = APIRouter(prefix="/api/mmkg", tags=["mmkg"])


class IngestRequest(BaseModel):
    doc_id: str | None = None
    path: str | None = None
    content: str | None = None


class IngestResponse(BaseModel):
    doc_id: str
    entities: list[GraphEntity]


class QueryRequest(BaseModel):
    query: str
    doc_ids: list[str]
    top_k: int = 5
    modality_bias: dict[Modality, float] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    hits: list[RetrievalHit]


def _pipeline() -> MMKGPipeline:
    return get_pipeline()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    req: IngestRequest,
    _user: dict[str, Any] = Depends(get_current_user),
    pipeline: MMKGPipeline = Depends(_pipeline),
) -> IngestResponse:
    if not req.path and not req.content:
        raise HTTPException(status_code=400, detail="path or content is required")
    entities = await pipeline.ingest(
        doc_id=req.doc_id, path=req.path, content=req.content
    )
    if not entities:
        raise HTTPException(status_code=422, detail="document produced no entities")
    return IngestResponse(doc_id=entities[0].doc_id, entities=entities)


@router.post("/query", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    _user: dict[str, Any] = Depends(get_current_user),
    pipeline: MMKGPipeline = Depends(_pipeline),
) -> QueryResponse:
    hits = await pipeline.query(
        req.query,
        doc_ids=req.doc_ids,
        top_k=req.top_k,
        modality_bias=req.modality_bias or None,
    )
    return QueryResponse(hits=hits)
