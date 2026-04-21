"""Redis conversation store.

Uses standard Redis hashes keyed by prefix + conversation id for each
conversation, plus a sorted set per user for recent conversation listings.

Keys:
  amie:conv:{id}            HASH with `json` field containing the Conversation JSON
  amie:user:{user_id}:convs ZSET of conversation ids scored by updated_at epoch
"""
from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.redis_client import get_redis
from app.models.schemas import Conversation, ConversationSummary, Message


class RedisConversationStore:
    def __init__(self, client: Redis, prefix: str) -> None:
        self._client = client
        self._prefix = prefix

    def _conv_key(self, conversation_id: str) -> str:
        return f"{self._prefix}{conversation_id}"

    def _user_key(self, user_id: str) -> str:
        return f"amie:user:{user_id}:convs"

    async def get(self, conversation_id: str) -> Conversation | None:
        raw = await self._client.hget(self._conv_key(conversation_id), "json")
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return Conversation.model_validate_json(raw)

    async def put(self, conversation: Conversation) -> None:
        key = self._conv_key(conversation.id)
        payload = conversation.model_dump_json()
        score = conversation.updated_at.timestamp()
        pipe = self._client.pipeline(transaction=False)
        pipe.hset(key, "json", payload)
        pipe.zadd(self._user_key(conversation.user_id), {conversation.id: score})
        await pipe.execute()

    async def list_for_user(self, user_id: str, limit: int = 50) -> list[ConversationSummary]:
        ids = await self._client.zrevrange(self._user_key(user_id), 0, limit - 1)
        ids = [i.decode() if isinstance(i, bytes) else i for i in ids]
        summaries: list[ConversationSummary] = []
        for cid in ids:
            conv = await self.get(cid)
            if not conv:
                continue
            summaries.append(
                ConversationSummary(
                    id=conv.id,
                    title=conv.title,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    message_count=len(conv.messages),
                )
            )
        return summaries

    async def delete(self, conversation_id: str) -> None:
        conv = await self.get(conversation_id)
        pipe = self._client.pipeline(transaction=False)
        pipe.delete(self._conv_key(conversation_id))
        if conv:
            pipe.zrem(self._user_key(conv.user_id), conversation_id)
        await pipe.execute()


@lru_cache
def get_conversation_store() -> RedisConversationStore:
    s = get_settings()
    return RedisConversationStore(get_redis(), s.redis_convo_prefix)


def append_message(conv: Conversation, msg: Message) -> Conversation:
    conv.messages.append(msg)
    conv.updated_at = msg.created_at
    if conv.title == "New conversation" and msg.role.value == "user":
        conv.title = msg.content[:60].strip() or "New conversation"
    return conv
