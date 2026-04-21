"""Request and response schemas."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: Role
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


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


class AddressVerifyResult(BaseModel):
    input_address: str
    standardized: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    zip5: str | None = None
    zip4: str | None = None
    dpv_code: str | None = None
    return_codes: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    verified: bool = False


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
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
    redis_ok: bool
    env: str
