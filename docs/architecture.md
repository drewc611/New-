# AMIE Architecture

## Overview

AMIE is a conversational AI assistant that grounds every answer in USPS addressing authorities (Publication 28, AMS Coding Manual) and can invoke tools such as USPS Address Validation. It runs locally on Docker Compose for developer loops and deploys to any Kubernetes cluster via a Helm chart.

## Runtime Topology

```
  [Browser]
      |
      v  HTTPS
  [Ingress Controller (nginx, Traefik, HAProxy, etc.)]
      |
      +---> [Frontend Deployment]
      |       image: nginx serving the built React SPA
      |       port: 8080 (non-privileged)
      |
      +---> [Backend Deployment]   (path /api/*)
              image: FastAPI with uvicorn
              port: 8000
              |
              +---> [Redis Stack StatefulSet]
              |       - vectors  (RediSearch HNSW index)
              |       - conversations  (JSON in hash keys)
              |       - cache
              |
              +---> [Ollama Deployment, optional]
                      - local LLM inference
```

## Backend Layers

| Layer | Module | Responsibility |
|---|---|---|
| API | `app/api/` | Health, chat, conversations, tools routers |
| Orchestration | `app/services/orchestrator.py` | Intent routing, tool invocation, history assembly |
| RAG | `app/rag/` | Chunking, Redis vector index, prompt templates |
| LLM | `app/llm/` | Ollama, Anthropic, Mock providers |
| Tools | `app/tools/` | Address verification: mock and USPS Web Tools |
| Storage | `app/services/conversation_store.py` | Redis-backed conversation persistence |
| Core | `app/core/` | Config, logging with PII redaction, Redis client, security |

## Per Turn Lifecycle

1. Client posts to `/api/chat/stream` with the user message and optional conversation id.
2. Orchestrator loads or creates the conversation from Redis.
3. Heuristic router decides whether to call `address_verify` and whether to retrieve from the vector index.
4. If a tool runs, its input and output are captured with latency and any error.
5. If retrieval runs, top-k citations are pulled from RediSearch (HNSW, cosine).
6. The user turn is augmented with a context block containing retrieved chunks and any tool output, then sent to the LLM.
7. Tokens stream over Server Sent Events back to the client.
8. Final assistant message is appended to the conversation and persisted in Redis.

## Frontend

* React 18 with TypeScript, Vite, Tailwind.
* Zustand store (`useChat`) holds messages, streaming state, citations, tool calls, and the conversation list.
* Streaming uses `@microsoft/fetch-event-source`.
* Served by nginx-unprivileged in the container so the pod can run under a `runAsNonRoot` policy.

## Redis Stack

Three uses of the same Redis instance:

1. **Vector search.** A RediSearch HNSW index `amie:vectors` over hash keys prefixed `amie:vec:{chunk_id}` with a FLOAT32 COSINE vector field. The backend builds the index on boot if empty.
2. **Conversations.** Each conversation is stored as a hash at `amie:conv:{id}` with a `json` field. A sorted set per user (`amie:user:{user_id}:convs`) keeps the list of conversation ids scored by `updated_at` for fast recents queries.
3. **Cache.** TTL keys for per-session caching (reserved for future use).

Swap to a managed Redis or Redis cluster in production by changing `redis.enabled=false` in the Helm chart and pointing `REDIS_URL` at your external endpoint.

## Observability

* Structured JSON logs to stdout, ingested by whatever log stack the cluster has (Fluent Bit, Vector, Loki, etc.).
* Liveness and readiness probes at `/api/health/live` and `/api/health/ready`.
* Readiness requires Redis to be reachable so pods do not take traffic before the data plane is up.

## Environments

| Environment | Purpose |
|---|---|
| Local | Docker Compose. Optional Ollama profile. |
| Dev | kind/minikube cluster, Helm chart with `llm.provider=mock`. |
| Staging | Real cluster, `llm.provider=ollama` or `anthropic`, persistence on. |
| Prod | Hardened cluster with ingress TLS, external secrets, resource quotas, network policies enforced. |
