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

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_database: str = "amie"
    mongo_conversations_collection: str = "conversations"
    mongo_vectors_collection: str = "vectors"
    mongo_address_events_collection: str = "address_events"
    mongo_address_events_capped_size_mb: int = 64
    mongo_address_events_capped_max_docs: int = 50_000
    # When set, use Atlas Vector Search (requires a vectorSearch index on
    # the vectors collection). When false, use in-process cosine similarity.
    mongo_use_atlas_vector_search: bool = False
    mongo_atlas_vector_index_name: str = "vector_index"

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

    # Okta / OIDC. When set, these override the generic JWT_* values so
    # operators can configure the provider in one place without having
    # to assemble the three URLs by hand.
    okta_issuer: str = ""           # e.g. https://dev-12345.okta.com/oauth2/default
    okta_audience: str = ""         # e.g. api://usps-amie
    okta_client_id: str = ""        # SPA client id exposed to the frontend
    okta_scopes: str = "openid profile email offline_access"
    # Frontend-only. When true, /api/auth/config advertises Okta to the SPA.
    okta_enabled: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jwt_algorithms_list(self) -> list[str]:
        return [a.strip() for a in self.jwt_algorithms.split(",") if a.strip()]

    @property
    def effective_jwt_issuer(self) -> str:
        return self.okta_issuer or self.jwt_issuer

    @property
    def effective_jwt_audience(self) -> str:
        return self.okta_audience or self.jwt_audience

    @property
    def effective_jwks_url(self) -> str:
        if self.jwt_jwks_url:
            return self.jwt_jwks_url
        if self.okta_issuer:
            return f"{self.okta_issuer.rstrip('/')}/v1/keys"
        return ""

    @property
    def okta_scopes_list(self) -> list[str]:
        return [s.strip() for s in self.okta_scopes.split() if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
