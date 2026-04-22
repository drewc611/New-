# USPS AMIE Chatbot

Address Management Intelligent Engine. A conversational AI assistant for USPS Address Management System workflows, modeled on ChatGPT and Claude with RAG grounding in Publication 28 and AMS documentation.

## Stack

* **Backend**: FastAPI, Python 3.11
* **Frontend**: React 18, TypeScript, Vite, Tailwind
* **Data**: MongoDB (conversations, KB chunks + embeddings, capped analytics collection; optional Atlas Vector Search)
* **LLM providers**: Ollama (local), Anthropic (dev/cloud), Mock (tests)
* **Deployment**: Docker Compose (local), Helm chart (Kubernetes)
* **Runtime**: Any Kubernetes distribution (vanilla k8s, OpenShift, Rancher, kind, minikube)

## Architecture

```
  [React SPA]
      |
      v  HTTPS
  [Ingress, TLS termination]
      |
      +---> [Frontend Deployment] (nginx + static build)
      |
      +---> [Backend Deployment]  (FastAPI, uvicorn)
              |
              +---> [MongoDB StatefulSet or Atlas]
              |       - conversations    (user chat history)
              |       - vectors          (KB chunks + embeddings)
              |       - address_events   (capped analytics log)
              |
              +---> [Ollama Deployment, optional]
              |       - local LLM inference
              |
              +---> [Anthropic API, optional]
                      - egress via HTTPS
```

## Repo Layout

```
usps-amie-chatbot/
  backend/              FastAPI service, RAG, tools, LLM providers
    app/
      api/              HTTP routers
      core/             config, logging, security
      llm/              Ollama, Anthropic, Mock providers
      rag/              chunking, Redis vector index, prompts
      tools/            address verification
      models/           Pydantic schemas
      services/         orchestrator, Redis conversation store
    data/knowledge_base seed JSON for indexing
    tests/              pytest suite
  frontend/             React, TypeScript, Vite, Tailwind
  deploy/
    docker/             Dockerfiles and nginx config
    helm/usps-amie/     Helm chart for Kubernetes
    k8s/                Raw manifests for users not using Helm
  scripts/              helpers
  docs/                 architecture, security, API, local dev, deployment
  docker-compose.yml    local dev stack
  .github/workflows/    CI
```

## Quickstart (Windows local build)

```
# Install Ollama Desktop from https://ollama.com/download/windows
pwsh -ExecutionPolicy Bypass -File .\scripts\start-windows.ps1
```

See [docs/windows-quickstart.md](docs/windows-quickstart.md) for details.

## Quickstart (Docker Compose)

```
cp .env.example .env
# edit .env: set LLM_PROVIDER=mock for no-key demo,
# LLM_PROVIDER=ollama for local inference via the bundled Ollama
# container, or LLM_PROVIDER=anthropic with ANTHROPIC_API_KEY
docker compose up --build
```

* Frontend: http://localhost:5173
* Backend: http://localhost:8000
* API docs: http://localhost:8000/docs
* MongoDB: mongodb://localhost:27017 (browse with MongoDB Compass)

## Documentation

| Topic | File |
|---|---|
| Okta single sign-on setup | [docs/okta-sso.md](docs/okta-sso.md) |
| Markdown-driven configuration and content | [docs/markdown-driven.md](docs/markdown-driven.md) |
| Environment variable reference | [docs/config.md](docs/config.md) |
| Address verification pipeline and API | [docs/address-verification.md](docs/address-verification.md) |
| Windows quickstart with Ollama Desktop | [docs/windows-quickstart.md](docs/windows-quickstart.md) |
| Architecture overview | [docs/architecture.md](docs/architecture.md) |
| Security model | [docs/security.md](docs/security.md) |
| Deployment guide | [docs/deployment.md](docs/deployment.md) |
| Local development (Docker) | [docs/local-dev.md](docs/local-dev.md) |
| API surface | [docs/api.md](docs/api.md) |

## Quickstart (Kubernetes via Helm)

```
# Local cluster (kind)
kind create cluster --name amie

# Load images or push to a registry
docker build -t usps-amie-backend:0.1.0 -f deploy/docker/backend.Dockerfile .
docker build -t usps-amie-frontend:0.1.0 -f deploy/docker/frontend.Dockerfile --target prod .
kind load docker-image usps-amie-backend:0.1.0 --name amie
kind load docker-image usps-amie-frontend:0.1.0 --name amie

# Install
helm install amie deploy/helm/usps-amie \
  --namespace amie --create-namespace \
  --set llm.provider=ollama

# Reach it
kubectl port-forward -n amie svc/amie-frontend 8080:80
# open http://localhost:8080
```

## Provider Modes

Set `LLM_PROVIDER` to one of:

* `ollama` for offline local or cluster-internal inference
* `anthropic` for dev with an API key
* `mock` for tests and demos with no external calls

## License

Proprietary. For USPS and authorized contractor use only.
