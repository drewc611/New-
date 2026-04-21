# AMIE API Reference

Base URL
* Local dev: `http://localhost:8000`
* Cluster: `http(s)://<ingress-host>`

All endpoints under `/api` accept and return `application/json` unless noted.

## Health

### GET `/api/health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "llm_provider": "ollama",
  "redis_ok": true,
  "env": "prod"
}
```

### GET `/api/health/live`

Kubernetes liveness probe. Returns `{"live": true}` as long as the process is up.

### GET `/api/health/ready`

Kubernetes readiness probe. Returns `{"ready": true}` only if Redis responds to PING.

## Chat

### POST `/api/chat`

Synchronous chat. Returns the full assistant turn, citations, and any tool calls.

Request
```json
{
  "conversation_id": null,
  "message": "Verify 1 Main St, Dallas, TX 75201",
  "intent_hint": "auto",
  "stream": false
}
```

Response (abridged)
```json
{
  "conversation_id": "uuid",
  "message": { "id": "uuid", "role": "assistant", "content": "..." },
  "citations": [ { "chunk_id": "pub28-sec-22-zip4#0", "score": 0.74 } ],
  "tool_calls": [ { "name": "address_verify", "output": { "verified": true } } ],
  "address_result": { "verified": true, "zip5": "75201", "dpv_code": "Y" },
  "usage": { "input_tokens": 412, "output_tokens": 187 }
}
```

### POST `/api/chat/stream`

Server Sent Events. Response type is `text/event-stream`.

Event types
| event | data shape |
|---|---|
| `start` | `{ "conversation_id": "uuid" }` |
| `tool_call` | `{ "tool_call": { ... } }` |
| `citations` | `{ "citations": [ ... ] }` |
| `token` | `{ "text": "partial text" }` |
| `done` | `{ "message_id": "uuid", "conversation_id": "uuid" }` |
| `error` | `{ "error": "message" }` |

## Conversations

| Method | Path | Description |
|---|---|---|
| GET | `/api/conversations` | List the current user's conversations, newest first |
| GET | `/api/conversations/{id}` | Full conversation including all messages |
| DELETE | `/api/conversations/{id}` | Delete the conversation |

## Tools

### POST `/api/tools/address/verify`

```json
{ "address": "1 Main St, Dallas, TX 75201" }
```

Returns an `AddressVerifyResult` with `standardized`, `zip5`, `zip4`, `dpv_code`, and `confidence`.

## Authentication

When `auth.enabled=true` in the chart, every request must include a bearer token:

```
Authorization: Bearer <jwt>
```

In dev, auth is disabled and requests are attributed to `dev-user`.
