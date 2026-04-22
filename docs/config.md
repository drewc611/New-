# Configuration Reference

Every setting is exposed as an environment variable. Defaults live in
`backend/app/core/config.py`; overrides come from `.env` (created by
copying `.env.example`).

## Application

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `usps-amie-chatbot` | Service name used in logs |
| `APP_ENV` | `dev` | One of `dev, staging, prod, test` |
| `LOG_LEVEL` | `INFO` | Structlog level |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma list of allowed origins |

## LLM

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama`, `anthropic`, or `mock` |
| `LLM_MODEL` | `claude-opus-4-5` | Model id (provider-specific) |
| `LLM_MAX_TOKENS` | `2048` | Completion cap |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature |
| `ANTHROPIC_API_KEY` | empty | Required when `LLM_PROVIDER=anthropic` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama HTTP endpoint |
| `OLLAMA_MODEL` | `llama3.1:8b` | Model name to pull and run |
| `OLLAMA_AUTO_PULL` | `true` | Pull the model on first call |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | `180` | Per-request timeout |

## RAG

| Variable | Default | Purpose |
|---|---|---|
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HF model for embeddings |
| `EMBEDDING_DIM` | `384` | Must match the model output |
| `KB_PATH` | `/app/data/knowledge_base` | JSON and markdown source dir |
| `CONTENT_DIR` | `/app/content` | Prompts and standards overrides |
| `RETRIEVAL_TOP_K` | `5` | Citations returned per query |

## MongoDB

| Variable | Default | Purpose |
|---|---|---|
| `MONGO_URI` | `mongodb://localhost:27017` | Mongo connection string; use `mongodb+srv://...` for Atlas |
| `MONGO_DATABASE` | `amie` | Database name |
| `MONGO_CONVERSATIONS_COLLECTION` | `conversations` | Chat history |
| `MONGO_VECTORS_COLLECTION` | `vectors` | KB chunks + embeddings |
| `MONGO_ADDRESS_EVENTS_COLLECTION` | `address_events` | Capped collection for analytics |
| `MONGO_ADDRESS_EVENTS_CAPPED_SIZE_MB` | `64` | Capped size ceiling |
| `MONGO_ADDRESS_EVENTS_CAPPED_MAX_DOCS` | `50000` | Capped document ceiling |
| `MONGO_USE_ATLAS_VECTOR_SEARCH` | `false` | When true, use `$vectorSearch` against Atlas |
| `MONGO_ATLAS_VECTOR_INDEX_NAME` | `vector_index` | Atlas vector index name |

Self-hosted MongoDB (community edition, 5.0+) works for the default
in-process cosine similarity path. For Atlas Vector Search, the
deployment must be MongoDB Atlas with an index of type
`vectorSearch` defined on the `vector` field. See
[docs/architecture.md](architecture.md#vector-search) for details.

## Address Verification

| Variable | Default | Purpose |
|---|---|---|
| `ADDRESS_VERIFIER` | `mock` | `mock` (offline) or `usps_api` |
| `USPS_API_BASE_URL` | `https://secure.shippingapis.com` | USPS Web Tools host |
| `USPS_API_USER_ID` | empty | Required for `usps_api` |
| `USPS_API_PASSWORD` | empty | Required for `usps_api` |
| `USPS_API_TIMEOUT_SECONDS` | `15` | USPS request timeout |

## Security

| Variable | Default | Purpose |
|---|---|---|
| `AUTH_ENABLED` | `false` | When true, every request must carry a JWT |
| `JWT_AUDIENCE` | `usps-amie` | Expected `aud` claim |
| `JWT_ISSUER` | empty | Expected `iss` claim |
| `JWT_JWKS_URL` | empty | JWKS endpoint, cached for one hour |
| `JWT_ALGORITHMS` | `RS256` | Comma list of acceptable algs |
| `REQUEST_MAX_BODY_BYTES` | `262144` | Reject larger POST bodies with 413 |

## Okta / OIDC

| Variable | Default | Purpose |
|---|---|---|
| `OKTA_ENABLED` | `false` | Advertises Okta as the provider in `/api/auth/config` |
| `OKTA_ISSUER` | empty | Okta auth server base URL; JWKS is auto-derived |
| `OKTA_CLIENT_ID` | empty | SPA client id (not a secret) |
| `OKTA_AUDIENCE` | empty | Expected `aud` claim, overrides `JWT_AUDIENCE` |
| `OKTA_SCOPES` | `openid profile email offline_access` | Space separated |

The SPA receives these via `/api/auth/config` at runtime, and also
accepts fallbacks in `VITE_OKTA_*` for the very first page load.

## Frontend

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend URL |
| `VITE_APP_TITLE` | `USPS AMIE` | Browser tab title |

See `docs/markdown-driven.md` for content that is configured via
markdown files rather than environment variables.
