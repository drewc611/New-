"""Conversation management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.models.schemas import Conversation, ConversationSummary
from app.services.conversation_store import MongoConversationStore, get_conversation_store

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _store() -> MongoConversationStore:
    return get_conversation_store()


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    user: dict = Depends(get_current_user),
    store: MongoConversationStore = Depends(_store),
) -> list[ConversationSummary]:
    return await store.list_for_user(user["sub"])


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    store: MongoConversationStore = Depends(_store),
) -> Conversation:
    conv = await store.get(conversation_id)
    if not conv or conv.user_id != user["sub"]:
        raise HTTPException(404, "conversation not found")
    return conv


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    store: MongoConversationStore = Depends(_store),
) -> dict:
    conv = await store.get(conversation_id)
    if not conv or conv.user_id != user["sub"]:
        raise HTTPException(404, "conversation not found")
    await store.delete(conversation_id)
    return {"deleted": conversation_id}
