"""Pydantic models for the multimodal knowledge graph pipeline.

Kept in one module so the five stage modules can import shared types
without risking circular imports.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Modality(str, Enum):
    TEXT = "text"
    HEADING = "heading"
    IMAGE = "image"
    TABLE = "table"
    EQUATION = "equation"
    CODE = "code"
    LIST = "list"
    OTHER = "other"


class ParsedBlock(BaseModel):
    """A single block emitted by a stage-1 parser.

    ``section_path`` is the heading breadcrumb from document root to the
    section that contains this block. It drives hierarchy preservation in
    stages 2 and 4.
    """

    block_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    doc_id: str
    modality: Modality
    order: int = 0
    section_path: list[str] = Field(default_factory=list)
    raw_content: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class AnalyzedBlock(BaseModel):
    """A block after stage-3 analysis has added semantic context.

    ``summary`` is short, human-readable prose suitable for embedding.
    ``facts`` is a list of atomic key-value observations surfaced by the
    analyzer (e.g. detected columns in a table, LaTeX tokens, visual tags).
    """

    block: ParsedBlock
    summary: str = ""
    facts: list[dict[str, Any]] = Field(default_factory=list)
    analyzer: str = "noop"


class GraphEntity(BaseModel):
    entity_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    doc_id: str
    modality: Modality
    label: str
    summary: str = ""
    section_path: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    block_id: str | None = None


class GraphRelation(BaseModel):
    src: str
    dst: str
    type: Literal[
        "belongs_to",
        "references",
        "describes",
        "derives_from",
        "co_occurs_with",
        "depends_on",
    ]
    weight: float = 0.5
    meta: dict[str, Any] = Field(default_factory=dict)


class RetrievalHit(BaseModel):
    entity: GraphEntity
    score: float
    source: Literal["vector", "graph", "fusion"]
    coherent_with: list[str] = Field(default_factory=list)
