# Local Development

## Prerequisites

* Docker Desktop or Docker Engine + Compose plugin
* Node 20 for frontend work outside Docker
* Python 3.11 for backend work outside Docker
* (Optional) An Anthropic API key, or Ollama running locally

## First Run With Docker Compose

```
cp .env.example .env
# Edit .env:
#   LLM_PROVIDER=mock          # easiest, no external calls
#   LLM_PROVIDER=anthropic     # requires ANTHROPIC_API_KEY
#   LLM_PROVIDER=ollama        # requires the offline profile
docker compose up --build
```

Open:

* Frontend: http://localhost:5173
* Backend: http://localhost:8000
* API docs: http://localhost:8000/docs
* Redis Stack UI (RedisInsight): http://localhost:8001

The backend boots with an empty Redis, then builds the vector index from `backend/data/knowledge_base/*.json` on first startup. The embedding model (`all-MiniLM-L6-v2`) is about 90 MB and is cached in the backend volume after first run.

## Offline Profile (with Ollama)

```
docker compose --profile offline up --build
# In another shell, pull a model
docker compose exec ollama ollama pull llama3.1
# Reset LLM_PROVIDER in .env to ollama and restart the backend
```

## Backend Without Docker

```
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Start a local Redis Stack first
docker run -d --rm -p 6379:6379 -p 8001:8001 redis/redis-stack:7.4.0-v0
export $(grep -v '^#' ../.env | xargs)
export REDIS_URL=redis://localhost:6379/0
uvicorn app.main:app --reload --port 8000
```

## Frontend Without Docker

```
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Tests

```
cd backend
pytest -v
```

Tests use `fakeredis` so there is no external dependency.

## Rebuilding the Index

If you add or edit files under `backend/data/knowledge_base/`, rebuild the index:

```
docker compose exec backend bash scripts/build-index.sh
```

## Running on kind

```
./scripts/kind-up.sh
# Port forward
kubectl port-forward -n amie svc/amie-frontend 8080:80
# Open http://localhost:8080
```

## Common Issues

* Slow first response: the embedding model downloads on first use.
* Empty citations: confirm the vector index bootstrapped (`kubectl logs deploy/amie-backend` looking for `bootstrapping_vector_index` and `chunks_indexed`).
* SSE drops through a corporate proxy: use the non-streaming `/api/chat` endpoint, or disable response buffering on the proxy.
