# Windows Quickstart (Ollama Desktop + local dev)

This is the path most developers want: FastAPI on the host, Redis Stack
in Docker Desktop, and Ollama Desktop serving the LLM. No cloud keys, no
corporate network tricks.

## Prerequisites

Install once:

1. Python 3.11 or newer: <https://www.python.org/downloads/windows/>
2. Node.js 20 LTS: <https://nodejs.org/en/download>
3. Docker Desktop: <https://www.docker.com/products/docker-desktop/>
4. Ollama Desktop: <https://ollama.com/download/windows>

After installing Ollama Desktop, start it once so it registers as a
service on `http://localhost:11434`.

## One-command launch

From a PowerShell prompt at the repo root:

```
pwsh -ExecutionPolicy Bypass -File .\scripts\start-windows.ps1
```

What the script does:

1. Copies `.env.example` to `.env` if missing.
2. Verifies Ollama Desktop is reachable, then `ollama pull llama3.1:8b`.
3. Starts `amie-mongo` (MongoDB 7.0) in Docker Desktop.
4. Creates a Python venv under `backend\.venv` and installs requirements.
5. Launches the FastAPI backend on <http://localhost:8000>.
6. Launches the Vite frontend on <http://localhost:5173>.

Flags:

- `-SkipOllama` skip the Ollama pull (if you already pulled the model)
- `-SkipMongo` skip the Docker step (if you have MongoDB running elsewhere)
- `-SkipFrontend` run backend only
- `-OllamaModel llama3.2:3b` use a different model

## Manual steps (if you prefer not to use the script)

```powershell
# 1. One-time
Copy-Item .env.example .env
docker run -d --name amie-mongo -p 27017:27017 -v amie-mongo-data:/data/db mongo:7.0

# 2. Pull a model
ollama pull llama3.1:8b

# 3. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:KB_PATH = "$PWD\data\knowledge_base"
$env:CONTENT_DIR = "$PWD\content"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 4. Frontend (new terminal)
cd frontend
npm install
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev
```

## Running Docker Compose with host Ollama

If you prefer the whole stack in Compose but want to keep using Ollama
Desktop on the host:

```
docker compose -f docker-compose.yml -f docker-compose.windows.yml up --build
```

The override sets `OLLAMA_BASE_URL=http://host.docker.internal:11434`
and adds the host-gateway entry needed on Windows.

## Troubleshooting

- **`Ollama is not reachable`**: open Ollama Desktop, wait for the tray
  icon, then rerun the script.
- **Vite cannot find the backend**: confirm `VITE_API_BASE_URL` is set
  to `http://localhost:8000`, and that the backend logged
  `startup` with `llm_provider=ollama`.
- **First reply is slow**: the embedding model (about 90 MB) downloads
  on first use, and the Ollama model loads into RAM. Subsequent replies
  are fast.
- **Wrong network**: corporate proxies sometimes intercept
  `localhost`. Try `127.0.0.1` explicitly.
