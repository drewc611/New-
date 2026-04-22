# USPS AMIE - Windows local development launcher
#
# Prereqs (install once):
#   1. Python 3.11+                    https://www.python.org/downloads/windows/
#   2. Node.js 20 LTS                  https://nodejs.org/en/download
#   3. Docker Desktop (for Redis)      https://www.docker.com/products/docker-desktop/
#   4. Ollama Desktop                  https://ollama.com/download/windows
#
# Run from the repo root:
#   pwsh -ExecutionPolicy Bypass -File .\scripts\start-windows.ps1

[CmdletBinding()]
param(
    [string]$OllamaModel = "llama3.1:8b",
    [switch]$SkipOllama,
    [switch]$SkipRedis,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Write-Step($Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

# 1. Env file
if (-not (Test-Path ".env")) {
    Write-Step "Creating .env from .env.example"
    Copy-Item ".env.example" ".env"
}

# 2. Ollama
if (-not $SkipOllama) {
    Write-Step "Checking Ollama Desktop at http://localhost:11434"
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3
    } catch {
        Write-Warning "Ollama is not reachable. Start Ollama Desktop, then rerun this script."
        Write-Warning "Download: https://ollama.com/download/windows"
        throw
    }
    Write-Step "Pulling model $OllamaModel (idempotent, skipped if already present)"
    & ollama pull $OllamaModel | Out-Host
}

# 3. Redis Stack via Docker Desktop
if (-not $SkipRedis) {
    Write-Step "Starting Redis Stack (requires Docker Desktop)"
    $existing = docker ps -a --filter "name=amie-redis" --format "{{.Names}}"
    if ($existing -eq "amie-redis") {
        docker start amie-redis | Out-Null
    } else {
        docker run -d --name amie-redis `
            -p 6379:6379 -p 8001:8001 `
            redis/redis-stack:7.4.0-v0 | Out-Null
    }
}

# 4. Backend Python deps
Write-Step "Preparing Python virtual environment"
$venv = Join-Path $RepoRoot "backend\.venv"
if (-not (Test-Path $venv)) {
    python -m venv $venv
}
$pip = Join-Path $venv "Scripts\pip.exe"
& $pip install --upgrade pip | Out-Host
& $pip install -r (Join-Path $RepoRoot "backend\requirements.txt") | Out-Host

# 5. Launch backend
Write-Step "Launching backend on http://localhost:8000"
$backendArgs = @(
    "/c", "cd /d `"$RepoRoot\backend`"",
    "&& `"$venv\Scripts\activate.bat`"",
    "&& set KB_PATH=$RepoRoot\backend\data\knowledge_base",
    "&& uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)
Start-Process -FilePath "cmd.exe" -ArgumentList $backendArgs

# 6. Launch frontend
if (-not $SkipFrontend) {
    Write-Step "Launching frontend on http://localhost:5173"
    $frontendArgs = @(
        "/c", "cd /d `"$RepoRoot\frontend`"",
        "&& npm install",
        "&& set VITE_API_BASE_URL=http://localhost:8000",
        "&& npm run dev"
    )
    Start-Process -FilePath "cmd.exe" -ArgumentList $frontendArgs
}

Write-Host ""
Write-Host "AMIE is starting up:" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000/docs"
Write-Host "  Frontend: http://localhost:5173"
Write-Host "  Redis UI: http://localhost:8001"
