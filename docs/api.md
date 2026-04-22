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
  "db_ok": true,
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

## Authentication

### GET `/api/auth/config`

Public. Returns the SSO config the SPA uses to initiate login.

```json
{
  "enabled": true,
  "provider": "okta",
  "issuer": "https://dev-12345.okta.com/oauth2/default",
  "client_id": "0oaXXXXXXXXXXXXX",
  "audience": "api://usps-amie",
  "scopes": ["openid", "profile", "email", "offline_access"],
  "redirect_path": "/auth/callback"
}
```

### GET `/api/auth/me`

Requires `Authorization: Bearer <access_token>`. Returns the
authenticated user's profile and group claims.

```json
{
  "sub": "00uABCDEFGHIJKLMNO",
  "email": "jane.doe@usps.gov",
  "name": "Jane Doe",
  "tenant": "default",
  "groups": ["amie-users"]
}
```

See [docs/okta-sso.md](okta-sso.md) for the full flow.

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

Returns an `AddressVerifyResult` with:

- Primary components: `primary_number`, `predirectional`, `street_name`,
  `street_suffix`, `postdirectional`
- Secondary components: `secondary_designator`, `secondary_number`
- Last line: `city`, `state`, `zip5`, `zip4`, `urbanization`
- `address_type`: `street`, `po_box`, `rural_route`, `highway_contract`,
  `military`, `general_delivery`, or `unknown`
- `dpv_code`, `confidence` (0..1), `verified` (bool)
- `warnings`, `noise_removed` (categories cleaned from the input)
- `suggestions`: up to three `AddressSuggestion` objects, present when
  confidence is below 0.9 or the parser had warnings

### POST `/api/tools/address/suggest`

```json
{ "address": "123 Peachtree Stret, Atlanta, GA 30303", "max_suggestions": 3 }
```

Returns:

```json
{
  "input_address": "123 Peachtree Stret, Atlanta, GA 30303",
  "noise_removed": [],
  "suggestions": [
    {
      "standardized": "123 PEACHTREE ST\nATLANTA, GA 30303",
      "confidence": 0.48,
      "reasons": ["corrected suffix 'STRET' -> 'ST'"],
      "replaced_tokens": [
        {"from": "STRET", "to": "ST", "category": "suffix", "score": "0.91"}
      ],
      "address_type": "street"
    }
  ]
}
```

### GET `/api/tools/address/analytics`

Returns an `AddressAnalyticsSummary` with `total`, `verified`,
`verified_rate`, `average_confidence`, `by_dpv_code`,
`by_address_type`, `top_warnings`, and the 25 most recent events.

## Authentication

When `auth.enabled=true` in the chart, every request must include a bearer token:

```
Authorization: Bearer <jwt>
```

In dev, auth is disabled and requests are attributed to `dev-user`.
