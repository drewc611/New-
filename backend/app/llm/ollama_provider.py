"""Ollama provider for local or in-cluster LLM inference.

Tuned for a friction-free Windows developer experience. On startup, if
``OLLAMA_AUTO_PULL`` is enabled, the provider will pull the configured
model the first time it is asked to generate. Networking defaults point
at ``http://localhost:11434`` so Ollama Desktop for Windows works out of
the box.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import httpx

from app.core.logging import get_logger
from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMUsage

log = get_logger(__name__)


class OllamaError(RuntimeError):
    pass


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        auto_pull: bool = True,
        request_timeout_seconds: float = 180.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._auto_pull = auto_pull
        self._timeout = request_timeout_seconds
        self._pull_lock = asyncio.Lock()
        self._pulled = False

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

    async def _ensure_model(self) -> None:
        """Verify the model is present locally; optionally pull it."""
        if self._pulled:
            return
        async with self._pull_lock:
            if self._pulled:
                return
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.post(
                        f"{self._base_url}/api/show",
                        json={"name": self._model},
                    )
                if r.status_code == 200:
                    self._pulled = True
                    return
            except httpx.HTTPError as e:
                if not self._auto_pull:
                    raise OllamaError(
                        f"Cannot reach Ollama at {self._base_url}: {e}. "
                        "Install Ollama Desktop from https://ollama.com/download "
                        "and ensure it is running."
                    ) from e

            if not self._auto_pull:
                raise OllamaError(
                    f"Ollama model '{self._model}' is not pulled. "
                    f"Run: ollama pull {self._model}"
                )

            log.info("ollama_pulling_model", model=self._model)
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST",
                        f"{self._base_url}/api/pull",
                        json={"name": self._model, "stream": True},
                    ) as r:
                        r.raise_for_status()
                        async for line in r.aiter_lines():
                            if not line:
                                continue
                            try:
                                obj = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if obj.get("error"):
                                raise OllamaError(obj["error"])
                            status = obj.get("status")
                            if status and status.startswith("pulling"):
                                continue
                            if status == "success":
                                break
            except httpx.HTTPError as e:
                raise OllamaError(
                    f"Failed to pull Ollama model '{self._model}' from "
                    f"{self._base_url}: {e}"
                ) from e
            self._pulled = True
            log.info("ollama_model_ready", model=self._model)

    async def complete(
        self,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse:
        await self._ensure_model()
        payload = self._payload(messages, system, max_tokens, temperature, stream=False)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(f"{self._base_url}/api/chat", json=payload)
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as e:
            raise OllamaError(
                f"Ollama chat request failed against {self._base_url}: {e}"
            ) from e
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
        await self._ensure_model()
        payload = self._payload(messages, system, max_tokens, temperature, stream=True)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST", f"{self._base_url}/api/chat", json=payload
                ) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if obj.get("done"):
                            break
                        content = obj.get("message", {}).get("content", "")
                        if content:
                            yield content
        except httpx.HTTPError as e:
            raise OllamaError(
                f"Ollama stream failed against {self._base_url}: {e}"
            ) from e
