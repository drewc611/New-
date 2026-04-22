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
* MongoDB: mongodb://localhost:27017 (browse with MongoDB Compass)

The backend boots with an empty MongoDB, then builds the `vectors` collection from `backend/data/knowledge_base/*.json` and `*.md` on first startup. The embedding model (`all-MiniLM-L6-v2`) is about 90 MB and is cached in the backend volume after first run.

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
# Start a local MongoDB first
docker run -d --rm -p 27017:27017 -v amie-mongo-data:/data/db mongo:7.0
export $(grep -v '^#' ../.env | xargs)
export MONGO_URI=mongodb://localhost:27017
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

Tests use `mongomock-motor` so there is no external dependency.

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
* Empty citations: confirm the vector collection bootstrapped (`kubectl logs deploy/amie-backend` looking for `bootstrapping_vector_index` and `chunks_indexed`).
* SSE drops through a corporate proxy: use the non-streaming `/api/chat` endpoint, or disable response buffering on the proxy.
