"""Chat orchestrator with intent routing and streaming."""
from __future__ import annotations

import re
import time
from collections.abc import AsyncIterator

from app.core.logging import get_logger
from app.llm.base import LLMMessage, LLMProvider
from app.llm.factory import get_llm_provider
from app.models.schemas import (
    AddressVerifyResult,
    ChatRequest,
    ChatResponse,
    Citation,
    Conversation,
    Message,
    Role,
    ToolCall,
)
from app.rag.prompts import SYSTEM_PROMPT, build_user_turn_with_context
from app.rag.retriever import retrieve
from app.services.conversation_store import (
    RedisConversationStore,
    append_message,
    get_conversation_store,
)
from app.tools.address_base import get_verifier

log = get_logger(__name__)

_ADDRESS_TRIGGERS = re.compile(
    r"\b(verify|validate|standardize|check|lookup)\b.*\b(address|zip|street)\b",
    re.IGNORECASE,
)
_ADDRESS_SHAPE = re.compile(r"\d{1,6}\s+\w.+,\s*\w+,\s*[A-Za-z]{2}\s*\d{5}", re.IGNORECASE)


def _detect_address(message: str) -> str | None:
    m = _ADDRESS_SHAPE.search(message)
    return m.group(0) if m else None


def _should_verify(message: str, hint: str) -> bool:
    if hint == "address_verify":
        return True
    if hint == "rag":
        return False
    return bool(_ADDRESS_TRIGGERS.search(message) or _ADDRESS_SHAPE.search(message))


def _should_retrieve(message: str, hint: str) -> bool:
    if hint == "rag":
        return True
    if hint == "address_verify":
        return False
    return True


class ChatOrchestrator:
    def __init__(
        self,
        llm: LLMProvider | None = None,
        store: RedisConversationStore | None = None,
    ) -> None:
        self._llm = llm or get_llm_provider()
        self._store = store or get_conversation_store()

    async def _load_or_create(self, conv_id: str | None, user_id: str) -> Conversation:
        if conv_id:
            existing = await self._store.get(conv_id)
            if existing:
                return existing
        return Conversation(user_id=user_id)

    def _to_llm_history(self, conv: Conversation, current_user_turn: str) -> list[LLMMessage]:
        msgs = [
            LLMMessage(role=m.role.value, content=m.content)
            for m in conv.messages
            if m.role in (Role.USER, Role.ASSISTANT)
        ]
        msgs.append(LLMMessage(role="user", content=current_user_turn))
        return msgs

    async def _maybe_verify(
        self, message: str, hint: str
    ) -> tuple[AddressVerifyResult | None, ToolCall | None]:
        if not _should_verify(message, hint):
            return None, None
        address = _detect_address(message) or message
        verifier = get_verifier()
        start = time.perf_counter()
        try:
            result = await verifier.verify(address)
            latency = int((time.perf_counter() - start) * 1000)
            call = ToolCall(
                name="address_verify",
                input={"address": address, "provider": verifier.name},
                output=result.model_dump(mode="json"),
                latency_ms=latency,
            )
            return result, call
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            call = ToolCall(
                name="address_verify",
                input={"address": address, "provider": verifier.name},
                latency_ms=latency,
                error=str(e),
            )
            log.error("address_verify_failed", error=str(e))
            return None, call

    def _augment_with_address_result(self, message: str, result: AddressVerifyResult) -> str:
        return (
            f"{message}\n\n<address_verification>\n"
            f"{result.model_dump_json(indent=2)}\n</address_verification>"
        )

    async def handle(self, req: ChatRequest, user_id: str) -> ChatResponse:
        conv = await self._load_or_create(req.conversation_id, user_id)
        user_msg = Message(role=Role.USER, content=req.message)
        append_message(conv, user_msg)

        citations: list[Citation] = []
        tool_calls: list[ToolCall] = []

        address_result, address_call = await self._maybe_verify(req.message, req.intent_hint)
        if address_call:
            tool_calls.append(address_call)

        if _should_retrieve(req.message, req.intent_hint):
            citations = await retrieve(req.message)

        user_turn = req.message
        if address_result:
            user_turn = self._augment_with_address_result(user_turn, address_result)
        if citations:
            user_turn = build_user_turn_with_context(user_turn, citations)

        history = self._to_llm_history(conv, user_turn)
        resp = await self._llm.complete(
            messages=history,
            system=SYSTEM_PROMPT,
            max_tokens=2048,
        )

        assistant_msg = Message(role=Role.ASSISTANT, content=resp.text)
        append_message(conv, assistant_msg)
        await self._store.put(conv)

        return ChatResponse(
            conversation_id=conv.id,
            message=assistant_msg,
            citations=citations,
            tool_calls=tool_calls,
            address_result=address_result,
            usage={
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
        )

    async def stream(self, req: ChatRequest, user_id: str) -> AsyncIterator[dict]:
        conv = await self._load_or_create(req.conversation_id, user_id)
        user_msg = Message(role=Role.USER, content=req.message)
        append_message(conv, user_msg)

        yield {"type": "start", "conversation_id": conv.id}

        address_result, address_call = await self._maybe_verify(req.message, req.intent_hint)
        if address_call:
            yield {"type": "tool_call", "tool_call": address_call.model_dump(mode="json")}

        citations: list[Citation] = []
        if _should_retrieve(req.message, req.intent_hint):
            citations = await retrieve(req.message)
            yield {"type": "citations", "citations": [c.model_dump(mode="json") for c in citations]}

        user_turn = req.message
        if address_result:
            user_turn = self._augment_with_address_result(user_turn, address_result)
        if citations:
            user_turn = build_user_turn_with_context(user_turn, citations)

        history = self._to_llm_history(conv, user_turn)
        chunks: list[str] = []
        try:
            async for tok in self._llm.stream(
                messages=history,
                system=SYSTEM_PROMPT,
                max_tokens=2048,
            ):
                chunks.append(tok)
                yield {"type": "token", "text": tok}
        except Exception as e:
            log.error("stream_failed", error=str(e))
            yield {"type": "error", "error": str(e)}
            return

        full_text = "".join(chunks)
        assistant_msg = Message(role=Role.ASSISTANT, content=full_text)
        append_message(conv, assistant_msg)
        await self._store.put(conv)

        yield {
            "type": "done",
            "message_id": assistant_msg.id,
            "conversation_id": conv.id,
        }
