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

## MongoDB

| Key | Description |
|---|---|
| `mongo.enabled` | Deploy the bundled MongoDB StatefulSet (default true). Set to false to use an external Mongo or Atlas. |
| `mongo.image.repository` / `tag` | Image coordinates (default `mongo:7.0`) |
| `mongo.service.port` | Service port (default 27017) |
| `mongo.persistence.enabled` | Mount a PVC for `/data/db` (default true) |
| `mongo.persistence.size` | PVC size (default 20Gi) |
| `mongo.persistence.storageClassName` | Specific storage class if any |
| `mongo.resources` | Resource requests and limits |
| `mongo.rootPassword` | Inline password, only used when `existingSecretName` empty |
| `mongo.existingSecretName` | Secret with `MONGO_ROOT_PASSWORD` |
| `mongo.database` | Database name (default `amie`) |
| `mongo.useAtlasVectorSearch` | When true, point at Atlas and use `$vectorSearch` |
| `mongo.atlasVectorIndexName` | Atlas vector search index name (default `vector_index`) |
| `mongo.externalUri` | Used when `enabled=false`; overrides `MONGO_URI` |

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
