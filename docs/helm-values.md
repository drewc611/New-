# Helm Values Reference

This document describes every value in `deploy/helm/usps-amie/values.yaml`. Defaults are shown in parentheses.

## LLM

| Key | Description |
|---|---|
| `llm.provider` | `ollama`, `anthropic`, or `mock` (default `mock`) |
| `llm.model` | Model identifier passed to the provider (default `claude-opus-4-5`) |
| `llm.maxTokens` | Max tokens per response (default 2048) |
| `llm.temperature` | Sampling temperature as a string (default `"0.2"`) |
| `llm.anthropicApiKey` | Inline Anthropic API key, only used when `existingSecretName` is empty |
| `llm.existingSecretName` | Name of a Secret containing `ANTHROPIC_API_KEY` |
| `llm.ollamaBaseUrl` | Override the Ollama base URL. Defaults to the in-cluster service when `ollama.enabled=true` |
| `llm.ollamaModel` | Ollama model identifier (default `llama3.1`) |

## Address Verification

| Key | Description |
|---|---|
| `addressVerifier.provider` | `mock` or `usps_api` (default `mock`) |
| `addressVerifier.uspsApi.baseUrl` | USPS Web Tools base URL |
| `addressVerifier.uspsApi.userId` | USPS API user id (inline) |
| `addressVerifier.uspsApi.password` | USPS API password (inline) |
| `addressVerifier.uspsApi.existingSecretName` | Secret with `USPS_API_USER_ID` and `USPS_API_PASSWORD` |

## Auth

| Key | Description |
|---|---|
| `auth.enabled` | When true, backend requires a bearer JWT on every request (default false) |
| `auth.jwtAudience` | Expected `aud` claim |
| `auth.jwtIssuer` | OIDC issuer URL for JWKS lookup |

## Backend

| Key | Description |
|---|---|
| `backend.enabled` | Toggle the backend (default true) |
| `backend.replicaCount` | Replica count when HPA disabled |
| `backend.image.repository` | Image repo |
| `backend.image.tag` | Image tag |
| `backend.service.type` | Service type (default ClusterIP) |
| `backend.service.port` | Service port (default 8000) |
| `backend.resources` | Resource requests and limits |
| `backend.autoscaling.enabled` | Enable HPA (default true) |
| `backend.autoscaling.minReplicas` / `maxReplicas` | HPA bounds |
| `backend.autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization |
| `backend.podDisruptionBudget.enabled` | Install a PDB (default true) |
| `backend.podDisruptionBudget.minAvailable` | PDB min available |
| `backend.logLevel` | Log level for structlog (default INFO) |
| `backend.env` | Extra environment variables as key-value map |

## Frontend

Same shape as backend. Uses port 80 for the Service and 8080 for the container.

## Redis

| Key | Description |
|---|---|
| `redis.enabled` | Deploy the bundled Redis Stack StatefulSet (default true) |
| `redis.image.repository` / `tag` | Image coordinates |
| `redis.service.port` | Service port (default 6379) |
| `redis.persistence.enabled` | Mount a PVC for data (default true) |
| `redis.persistence.size` | PVC size (default 10Gi) |
| `redis.persistence.storageClassName` | Specific storage class if any |
| `redis.resources` | Resource requests and limits |
| `redis.password` | Inline password, only used when `existingSecretName` empty |
| `redis.existingSecretName` | Secret with `REDIS_PASSWORD` |
| `redis.vectorIndex` | RediSearch index name (default `amie:vectors`) |
| `redis.convoPrefix` | Key prefix for conversations (default `amie:conv:`) |

## Ollama

| Key | Description |
|---|---|
| `ollama.enabled` | Deploy an Ollama pod (default false) |
| `ollama.image.repository` / `tag` | Image coordinates |
| `ollama.service.port` | Service port (default 11434) |
| `ollama.persistence.enabled` | Mount a PVC for downloaded models (default true) |
| `ollama.persistence.size` | PVC size (default 30Gi) |
| `ollama.resources` | Resource requests and limits |

## Ingress

| Key | Description |
|---|---|
| `ingress.enabled` | Install an Ingress resource (default true) |
| `ingress.className` | IngressClass name (default empty, uses cluster default) |
| `ingress.annotations` | Annotations passed to the Ingress |
| `ingress.hosts[].host` | Host name |
| `ingress.hosts[].paths` | List of `{path, pathType}` for the frontend. The chart always adds an additional `/api` path routed to the backend |
| `ingress.tls` | TLS config list |

## Other

| Key | Description |
|---|---|
| `networkPolicy.enabled` | Install NetworkPolicies (default true) |
| `serviceAccount.create` | Create a ServiceAccount (default true) |
| `podSecurityContext` | Pod-level security context (non-root, fsGroup) |
| `containerSecurityContext` | Container-level security context (no privilege escalation, capabilities dropped) |
| `image.pullPolicy` | Default image pull policy (`IfNotPresent`) |
| `image.pullSecrets` | imagePullSecrets list |
