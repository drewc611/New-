"""Application configuration. All values overridable by env vars."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "usps-amie-chatbot"
    app_env: Literal["dev", "staging", "prod", "test"] = "dev"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM
    llm_provider: Literal["ollama", "anthropic", "mock"] = "ollama"
    llm_model: str = "claude-opus-4-5"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.2

    anthropic_api_key: str = ""

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_auto_pull: bool = True
    ollama_request_timeout_seconds: float = 180.0

    # RAG
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    kb_path: str = "/app/data/knowledge_base"
    content_dir: str = "/app/content"
    retrieval_top_k: int = 5

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_vector_index: str = "amie:vectors"
    redis_convo_prefix: str = "amie:conv:"
    redis_cache_ttl_seconds: int = 3600

    # Address verification
    address_verifier: Literal["mock", "usps_api"] = "mock"
    usps_api_base_url: str = "https://secure.shippingapis.com"
    usps_api_user_id: str = ""
    usps_api_password: str = ""
    usps_api_timeout_seconds: float = 15.0

    # Security
    auth_enabled: bool = False
    jwt_audience: str = "usps-amie"
    jwt_issuer: str = ""
    jwt_jwks_url: str = ""
    jwt_algorithms: str = "RS256"
    request_max_body_bytes: int = 262144  # 256 KiB

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jwt_algorithms_list(self) -> list[str]:
        return [a.strip() for a in self.jwt_algorithms.split(",") if a.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
