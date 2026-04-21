"""Ollama provider for local or in-cluster LLM inference."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMUsage


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def _payload(
        self,
        messages: list[LLMMessage],
        system: str | None,
        max_tokens: int,
        temperature: float,
        stream: bool,
    ) -> dict:
        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend({"role": m.role, "content": m.content} for m in messages)
        return {
            "model": self._model,
            "messages": msgs,
            "stream": stream,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }

    async def complete(
        self,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse:
        payload = self._payload(messages, system, max_tokens, temperature, stream=False)
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(f"{self._base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
        text = data.get("message", {}).get("content", "")
        return LLMResponse(
            text=text,
            usage=LLMUsage(
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
            ),
            stop_reason=data.get("done_reason"),
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, system, max_tokens, temperature, stream=True)
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    obj = json.loads(line)
                    if obj.get("done"):
                        break
                    content = obj.get("message", {}).get("content", "")
                    if content:
                        yield content
