"""Mock provider for tests and demos."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMUsage


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, delay: float = 0.02) -> None:
        self._delay = delay

    def _canned(self, messages: list[LLMMessage]) -> str:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return (
            "This is a mock response used for local tests. You asked about: "
            f"{last_user[:140]}"
        )

    async def complete(self, messages, system=None, max_tokens=2048, temperature=0.2):
        text = self._canned(messages)
        return LLMResponse(
            text=text,
            usage=LLMUsage(
                input_tokens=len(" ".join(m.content for m in messages).split()),
                output_tokens=len(text.split()),
            ),
            stop_reason="end_turn",
        )

    async def stream(self, messages, system=None, max_tokens=2048, temperature=0.2) -> AsyncIterator[str]:
        text = self._canned(messages)
        for word in text.split():
            await asyncio.sleep(self._delay)
            yield word + " "
