"""Factory to build the configured LLM provider.

Provider modules are imported lazily so a deployment only requires the
SDKs for the providers it actually uses. For instance a Windows local
build with ``LLM_PROVIDER=ollama`` does not pull in ``anthropic``.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.llm.base import LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    s = get_settings()
    if s.llm_provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=s.anthropic_api_key, model=s.llm_model)
    if s.llm_provider == "ollama":
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider(
            base_url=s.ollama_base_url,
            model=s.ollama_model,
            auto_pull=s.ollama_auto_pull,
            request_timeout_seconds=s.ollama_request_timeout_seconds,
        )
    if s.llm_provider == "mock":
        from app.llm.mock_provider import MockProvider

        return MockProvider()
    raise ValueError(f"unknown llm provider: {s.llm_provider}")
