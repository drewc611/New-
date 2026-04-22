"""MongoDB conversation store.

Schema (collection ``conversations``):

```
{
  "_id": "<uuid>",
  "title": "...",
  "user_id": "<sub>",
  "tenant": "default",
  "created_at": ISODate,
  "updated_at": ISODate,
  "messages": [ {id, role, content, created_at}, ... ]
}
```

Required index: ``{ user_id: 1, updated_at: -1 }`` for the
"list the current user's recent conversations" query.
"""
from __future__ import annotations

from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.mongo_client import get_mongo_db
from app.models.schemas import Conversation, ConversationSummary, Message


class MongoConversationStore:
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str) -> None:
        self._collection: AsyncIOMotorCollection = db[collection_name]
        self._index_ensured = False

    async def _ensure_indexes(self) -> None:
        if self._index_ensured:
            return
        try:
            await self._collection.create_index(
                [("user_id", 1), ("updated_at", -1)], name="user_recent"
            )
            self._index_ensured = True
        except Exception:
            # Indexes are best-effort; tests against mongomock may not need them.
            self._index_ensured = True

    @staticmethod
    def _to_document(conv: Conversation) -> dict:
        data = conv.model_dump(mode="python")
        data["_id"] = data.pop("id")
        return data

    @staticmethod
    def _from_document(doc: dict) -> Conversation:
        data = dict(doc)
        data["id"] = data.pop("_id")
        return Conversation.model_validate(data)

    async def get(self, conversation_id: str) -> Conversation | None:
        await self._ensure_indexes()
        doc = await self._collection.find_one({"_id": conversation_id})
        return self._from_document(doc) if doc else None

    async def put(self, conversation: Conversation) -> None:
        await self._ensure_indexes()
        doc = self._to_document(conversation)
        await self._collection.replace_one(
            {"_id": conversation.id}, doc, upsert=True
        )

    async def list_for_user(
        self, user_id: str, limit: int = 50
    ) -> list[ConversationSummary]:
        await self._ensure_indexes()
        cursor = (
            self._collection.find(
                {"user_id": user_id},
                projection={
                    "_id": 1,
                    "title": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "messages": 1,
                },
            )
            .sort("updated_at", -1)
            .limit(limit)
        )
        summaries: list[ConversationSummary] = []
        async for doc in cursor:
            summaries.append(
                ConversationSummary(
                    id=doc["_id"],
                    title=doc.get("title", "New conversation"),
                    created_at=doc["created_at"],
                    updated_at=doc["updated_at"],
                    message_count=len(doc.get("messages", [])),
                )
            )
        return summaries

    async def delete(self, conversation_id: str) -> None:
        await self._ensure_indexes()
        await self._collection.delete_one({"_id": conversation_id})


@lru_cache
def get_conversation_store() -> MongoConversationStore:
    s = get_settings()
    return MongoConversationStore(get_mongo_db(), s.mongo_conversations_collection)


def append_message(conv: Conversation, msg: Message) -> Conversation:
    conv.messages.append(msg)
    conv.updated_at = msg.created_at
    if conv.title == "New conversation" and msg.role.value == "user":
        conv.title = msg.content[:60].strip() or "New conversation"
    return conv
