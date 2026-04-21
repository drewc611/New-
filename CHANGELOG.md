# Changelog

All notable changes follow Keep a Changelog and this project uses Semantic Versioning.

## [0.1.0] Initial k8s + Redis scaffold

### Added
* FastAPI backend with layered architecture: API routers, orchestrator, RAG, LLM providers, tools, Redis-backed conversation store
* LLM provider abstraction: Ollama, Anthropic, Mock
* RAG pipeline using Redis Stack RediSearch HNSW vector index, sentence-transformers embeddings, Publication 28 and AMS seed corpus
* Address verification tool with offline mock and USPS Web Tools providers
* Streaming responses over Server Sent Events
* React 18 + TypeScript + Vite + Tailwind frontend with conversation sidebar, markdown rendering, citation panels, tool call inspection
* Docker Compose local development stack with Redis Stack, RedisInsight UI, optional Ollama profile
* Multi-stage Dockerfiles: backend Python slim, frontend nginx-unprivileged for non-root pods
* Helm chart with backend, frontend, Redis StatefulSet, optional in-cluster Ollama, ConfigMap, Secrets (generated or external), ServiceAccount, HPAs, PDBs, Ingress (path-based split between frontend and backend), NetworkPolicies (default deny plus per-component rules), pod security context compatible with the Kubernetes restricted PSS
* Raw Kubernetes manifests for users not using Helm
* GitHub Actions: backend tests with fakeredis + Trivy image scan, frontend typecheck + build, Helm lint + template + kubeconform validation
* Documentation: architecture, security, API reference, local dev, deployment, Helm values reference
* Scripts: helm-install, kind-up (build and load images, install chart in one shot), build-index
