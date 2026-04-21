"""Factory to build the configured LLM provider."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockProvider
from app.llm.ollama_provider import OllamaProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    s = get_settings()
    if s.llm_provider == "anthropic":
        return AnthropicProvider(api_key=s.anthropic_api_key, model=s.llm_model)
    if s.llm_provider == "ollama":
        return OllamaProvider(base_url=s.ollama_base_url, model=s.ollama_model)
    if s.llm_provider == "mock":
        return MockProvider()
    raise ValueError(f"unknown llm provider: {s.llm_provider}")
