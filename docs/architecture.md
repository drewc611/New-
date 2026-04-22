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
              +---> [MongoDB StatefulSet or Atlas]
              |       - conversations    (user chat history)
              |       - vectors          (KB chunks + embeddings)
              |       - address_events   (capped analytics log)
              |
              +---> [Ollama Deployment, optional]
                      - local LLM inference
```

## Backend Layers

| Layer | Module | Responsibility |
|---|---|---|
| API | `app/api/` | Health, chat, conversations, tools, auth routers |
| Orchestration | `app/services/orchestrator.py` | Intent routing, tool invocation, history assembly |
| RAG | `app/rag/` | Chunking, Mongo vector index, prompt templates |
| LLM | `app/llm/` | Ollama, Anthropic, Mock providers |
| Tools | `app/tools/` | Address verification: parser, noise cancel, suggester |
| Storage | `app/services/conversation_store.py` | Mongo-backed conversation persistence |
| Analytics | `app/services/address_analytics.py` | Capped Mongo collection for verification events |
| Core | `app/core/` | Config, logging with PII redaction, Mongo client, security |

## Per Turn Lifecycle

1. Client posts to `/api/chat/stream` with the user message and optional conversation id.
2. Orchestrator loads or creates the conversation from MongoDB.
3. Heuristic router decides whether to call `address_verify` and whether to retrieve from the vector collection.
4. If a tool runs, its input and output are captured with latency and any error; each verification is recorded to the `address_events` capped collection for analytics.
5. If retrieval runs, top-k citations are pulled from the vector index (see below).
6. The user turn is augmented with a context block containing retrieved chunks and any tool output, then sent to the LLM.
7. Tokens stream over Server Sent Events back to the client.
8. Final assistant message is appended to the conversation document and persisted to MongoDB.

## Frontend

* React 18 with TypeScript, Vite, Tailwind.
* Zustand stores (`useChat`, `useAuth`) hold messages, streaming state, citations, tool calls, conversation list, and the signed-in user.
* Streaming uses `@microsoft/fetch-event-source`.
* Served by nginx-unprivileged in the container so the pod can run under a `runAsNonRoot` policy.

## MongoDB

Three collections in a single database (default `amie`):

1. **`conversations`** - one document per conversation, with the full message array embedded. Indexed on `{user_id, updated_at}` so the "recent conversations" query is a range scan.
2. **`vectors`** - one document per KB chunk. Fields: `doc_id`, `title`, `url`, `text`, `vector` (array of 384 float32 values). The indexer ingests both JSON and Markdown files under `backend/data/knowledge_base/`.
3. **`address_events`** - capped collection (default 64 MiB, 50k docs) that auto-trims on insert. Each document is an immutable record of a verification attempt.

### Vector search

Two retrieval backends, selectable via `MONGO_USE_ATLAS_VECTOR_SEARCH`:

| Backend | When | How |
|---|---|---|
| **In-process cosine** (default) | Local dev, self-hosted Mongo, up to roughly 50k chunks | Load all vectors once per query, compute `query_vec @ matrix.T`, `argpartition` for top-K. Pure numpy, no Atlas feature required. |
| **Atlas Vector Search** | MongoDB Atlas with a `vectorSearch` index | `$vectorSearch` aggregation stage with cosine similarity. Index name is `MONGO_ATLAS_VECTOR_INDEX_NAME`. |

Both paths store identical documents, so you can switch between them without re-ingesting.

Swap to Atlas or a managed Mongo in production by changing `MONGO_URI` to `mongodb+srv://...`. The Helm chart can either deploy its bundled StatefulSet or be told `mongo.enabled=false` to use an external cluster.

## Observability

* Structured JSON logs to stdout, ingested by whatever log stack the cluster has (Fluent Bit, Vector, Loki, etc.).
* Liveness and readiness probes at `/api/health/live` and `/api/health/ready`.
* Readiness requires MongoDB to be reachable so pods do not take traffic before the data plane is up.

## Environments

| Environment | Purpose |
|---|---|
| Local | Docker Compose with MongoDB 7.0. Optional Ollama profile. |
| Dev | kind/minikube cluster, Helm chart with `llm.provider=mock`. |
| Staging | Real cluster or Atlas, `llm.provider=ollama` or `anthropic`, persistence on. |
| Prod | Hardened cluster + Atlas with vector search, ingress TLS, external secrets, resource quotas, network policies enforced. |
