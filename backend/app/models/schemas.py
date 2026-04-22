"""Request and response schemas."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: Role
    content: str
    created_at: datetime = Field(default_factory=_now_utc)


class Citation(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    snippet: str
    score: float
    url: str | None = None


class ToolCall(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    latency_ms: int | None = None
    error: str | None = None


class AddressSuggestion(BaseModel):
    """A single candidate correction for a bad or noisy input address."""

    standardized: str
    confidence: float
    reasons: list[str] = Field(default_factory=list)
    replaced_tokens: list[dict[str, str]] = Field(default_factory=list)
    address_type: str = "unknown"


class AddressVerifyResult(BaseModel):
    input_address: str
    standardized: str | None = None
    # Primary address components
    firm: str | None = None
    primary_number: str | None = None
    predirectional: str | None = None
    street_name: str | None = None
    street_suffix: str | None = None
    postdirectional: str | None = None
    street: str | None = None  # fully assembled delivery address line
    # Secondary (unit) components
    secondary: str | None = None
    secondary_designator: str | None = None
    secondary_number: str | None = None
    # Last line
    city: str | None = None
    state: str | None = None
    zip5: str | None = None
    zip4: str | None = None
    urbanization: str | None = None  # Puerto Rico URB line
    # Classification
    address_type: Literal[
        "street", "po_box", "rural_route", "highway_contract", "military", "general_delivery", "unknown"
    ] = "unknown"
    dpv_code: str | None = None
    return_codes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    noise_removed: list[str] = Field(default_factory=list)
    suggestions: list["AddressSuggestion"] = Field(default_factory=list)
    confidence: float = 0.0
    verified: bool = False


class AddressAnalyticsEvent(BaseModel):
    """An immutable record of a single verification attempt."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = Field(default_factory=_now_utc)
    input_address: str
    noise_removed: list[str] = Field(default_factory=list)
    verifier: str
    dpv_code: str | None = None
    confidence: float
    address_type: str = "unknown"
    warnings: list[str] = Field(default_factory=list)
    suggestions_offered: int = 0
    top_suggestion_score: float = 0.0
    user_id: str = "dev-user"


class AddressAnalyticsSummary(BaseModel):
    total: int
    verified: int
    verified_rate: float
    average_confidence: float
    by_dpv_code: dict[str, int]
    by_address_type: dict[str, int]
    top_warnings: list[dict[str, int | str]] = Field(default_factory=list)
    recent: list[AddressAnalyticsEvent] = Field(default_factory=list)


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    intent_hint: Literal["rag", "address_verify", "auto"] = "auto"
    stream: bool = False


class ChatResponse(BaseModel):
    conversation_id: str
    message: Message
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    address_result: AddressVerifyResult | None = None
    usage: dict[str, int] = Field(default_factory=dict)


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = "New conversation"
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    messages: list[Message] = Field(default_factory=list)
    tenant: str = "default"
    user_id: str = "dev-user"


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"] = "ok"
    version: str
    llm_provider: str
    db_ok: bool
    env: str
