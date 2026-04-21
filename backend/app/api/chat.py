"""Chat endpoints: /api/chat synchronous, /api/chat/stream SSE."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.core.security import get_current_user
from app.models.schemas import ChatRequest, ChatResponse
from app.services.orchestrator import ChatOrchestrator

router = APIRouter(prefix="/api", tags=["chat"])


def get_orchestrator() -> ChatOrchestrator:
    return ChatOrchestrator()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user: dict = Depends(get_current_user),
    orch: ChatOrchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    return await orch.handle(req, user_id=user["sub"])


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    user: dict = Depends(get_current_user),
    orch: ChatOrchestrator = Depends(get_orchestrator),
) -> EventSourceResponse:
    async def event_gen():
        async for event in orch.stream(req, user_id=user["sub"]):
            yield {"event": event["type"], "data": json.dumps(event)}

    return EventSourceResponse(event_gen())
