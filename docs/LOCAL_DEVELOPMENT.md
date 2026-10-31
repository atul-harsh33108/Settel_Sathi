# Local Development

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 24+ and npm

## One-time setup

Run all commands from the repository root. Python always uses the project-local `.venv`.

```powershell
Copy-Item .env.example .env
uv venv .venv
.\.venv\Scripts\Activate.ps1
uv sync --all-groups
Set-Location web
npm install
Set-Location ..
```

`npm install` resolves the newest stable compatible frontend dependencies and writes `web/package-lock.json`. Thereafter use `npm ci` for repeatable installs.

## Run locally

Use two PowerShell terminals.

```powershell
# Terminal 1 — API
.\.venv\Scripts\Activate.ps1
uv run uvicorn app.main:app --reload --port 8000
```

```powershell
# Terminal 2 — web client
Set-Location web
npm run dev
```

- API health: `http://localhost:8000/health`
- OpenAPI: `http://localhost:8000/api/v1/docs`
- Web client: `http://localhost:5173`

## Verify before updating the tracker

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest
Set-Location web
npm run lint
npm run build
```

## Data-workstream boundary

Do not edit `serv_data/`; it is reserved for the separate data implementation workstream. Until its validated fixture bundle is handed off, this product foundation does not load or claim real payment or bank data.
