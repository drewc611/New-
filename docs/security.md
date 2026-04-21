# AMIE Security

## Pod Security

| Control | Setting |
|---|---|
| Non-root user | `runAsNonRoot: true`, `runAsUser: 1000`, `fsGroup: 1000` |
| Privilege escalation | `allowPrivilegeEscalation: false` |
| Capabilities | `drop: [ALL]` |
| nginx | Uses `nginx-unprivileged` image, listens on 8080 |

The defaults in `values.yaml` satisfy the Kubernetes `restricted` Pod Security Standard.

## Network Policies

When `networkPolicy.enabled=true` (default) the chart installs:

| Policy | Effect |
|---|---|
| Default deny | All AMIE pods deny ingress and egress unless another rule allows it |
| Backend | Accepts from frontend and ingress namespace on 8000, egresses to Redis 6379, Ollama 11434 (if enabled), DNS, and external HTTPS (0.0.0.0/0 except RFC1918) for Anthropic and USPS API |
| Frontend | Accepts from ingress namespace on 8080, egresses only to the backend and DNS |
| Redis | Accepts only from backend on 6379 |

Tighten the backend HTTPS egress in production by replacing the `ipBlock` rule with specific IP ranges for the Anthropic and USPS endpoints.

## Secrets

Secrets are provisioned by the chart:

| Secret | Contents |
|---|---|
| `{release}-llm` | `ANTHROPIC_API_KEY` (only when `llm.provider=anthropic`) |
| `{release}-usps` | `USPS_API_USER_ID`, `USPS_API_PASSWORD` (only when `addressVerifier.provider=usps_api`) |
| `{release}-redis` | `REDIS_PASSWORD` (generated if not supplied) |

Bring your own secrets by setting `llm.existingSecretName`, `addressVerifier.uspsApi.existingSecretName`, or `redis.existingSecretName`. This is the recommended pattern for production where secrets come from External Secrets Operator, Sealed Secrets, Vault CSI, or similar.

## Data Protection

| Data | Storage | Encryption |
|---|---|---|
| Vector chunks | Redis hashes | Encryption at rest depends on PV storage class. Use a CSI driver with encryption enabled (for example Portworx, EBS CSI with KMS, Azure Disk CSI with customer-managed keys). |
| Conversations | Redis hashes + ZSET | Same as above. |
| Logs | stdout, picked up by cluster log stack | Follow cluster log stack encryption. |

## Authentication

Production deployments set `auth.enabled=true` and supply `auth.jwtIssuer` for your OIDC provider (Keycloak, Okta, Azure AD, etc.). The backend validates JWTs on every request. When auth is disabled all requests are attributed to `dev-user`.

## PII Handling

`app/core/logging.py` redacts fields named `address`, `street`, `email`, `phone`, `ssn`, `password`, `api_key` from structured log entries before they reach stdout. Add fields to `PII_FIELDS` in that module to extend the list.

## Application Hardening

* System prompt pins the assistant identity and requires grounding in retrieved context.
* Tool outputs are wrapped in a dedicated `<address_verification>` block that the model is instructed not to echo verbatim.
* Tool failures are captured as structured `ToolCall.error` entries so the audit trail records every attempt.

## Supply Chain

* Images are built multi-stage and run as non-root.
* `deploy/docker/frontend.Dockerfile` uses `nginxinc/nginx-unprivileged` to avoid UID 0.
* CI runs Trivy against both images and fails on CRITICAL or HIGH CVEs that have a fix.

## Known Residual Risks

| Risk | Mitigation |
|---|---|
| LLM hallucination | Retrieval grounding with explicit citation, optional human review for sensitive output |
| Redis data loss | Enable persistence, use a PV with snapshot capability, or an external managed Redis |
| Single Redis replica | The chart deploys one Redis pod. For HA, use Redis Enterprise or Redis Sentinel/Cluster via a dedicated chart and disable the bundled StatefulSet |
| Prompt injection via retrieved content | Content review on corpus ingest, output filtering, system prompt rules |
