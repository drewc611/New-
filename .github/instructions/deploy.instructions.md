---
applyTo: "deploy/**"
description: "Deployment (Docker, Helm, k8s) conventions"
---

# Deploy

## Docker

- Multi-stage builds. Pin base images by digest where possible.
- Non-root user in the final stage.
- Keep images slim — no build tools in the runtime layer.

## Helm

- Chart at `deploy/helm/usps-amie/`. Values documented in `docs/helm-values.md`.
- Don't commit `charts/` or `Chart.lock` — gitignored.
- Subcharts are optional (Redis, Ollama) — gate with `enabled` flags.

## Kubernetes

- Works on vanilla k8s, OpenShift, Rancher, kind, minikube.
- No hostPath volumes, no privileged containers, no cluster-wide RBAC without justification.
- Liveness and readiness probes on every workload.

## Security

- Secrets via Kubernetes Secrets or sealed-secrets — never bake into images.
- TLS terminated at the ingress. Backend listens on plain HTTP inside the mesh.
