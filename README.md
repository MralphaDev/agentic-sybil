# Agentic Sybil

An investigation platform for exploring coordinated and Sybil-like activity on Solana. It combines wallet/event ingestion, graph and process-mining analysis, an agentic investigation workflow, and a Next.js frontend.

> **Status:** Active development. Docker configuration and unit tests are provided, but a full live deployment and Helius/Supabase integration test still need to be run in your environment.

## Features

- Solana event ingestion and wallet feature extraction through Helius and Solana RPC.
- Funding and aggregated transaction graphs for relationship analysis.
- Process-mining and wallet-clustering tools for coordinated behavior investigation.
- Investigation Copilot using DeepSeek, read-only database queries, and Helius MCP for targeted wallet evidence.
- Next.js frontend with investigation, forensic, graph, and process-mining views.

## Architecture

- `frontend/`: Next.js app (port 3000).
- `backend/app/`: FastAPI service (port 8000), analysis pipeline, agent tools, providers, and database access.
- PostgreSQL/Supabase: persistent wallet profiles and event data. The database is external; Compose does not create a local database.
- Helius MCP: launched by the backend via `npx`; Node.js/npm are included in the backend image.

## Requirements

For Docker:
- Docker Desktop (Windows/macOS) or Docker Engine + Docker Compose plugin (Linux).
- API credentials for DeepSeek and Helius.
- A reachable PostgreSQL/Supabase database with the schema expected by the application.

For local development:
- Python 3.12 recommended.
- Node.js 22 recommended for the frontend; Node.js/npm are also needed for Helius MCP.
- PostgreSQL/Supabase connection.

## Configuration

At the repository root, create your local `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Fill in the values:

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
HELIUS_API_KEY=your_helius_api_key
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require
```

Use the connection string from your Supabase project. For Docker, use a hostname reachable from inside the container; do not use `localhost` for a database running on your host machine. Never commit `.env` or publish real API keys.

## Run the full app with Docker

Run these commands from the repository root.

### 1. Build images

```powershell
docker compose build
```

### 2. Start backend and frontend

```powershell
docker compose up -d
```

### 3. Check status and logs

```powershell
docker compose ps
docker compose logs -f backend
```

In a second terminal, if needed:

```powershell
docker compose logs -f frontend
```

Open:
- Frontend: http://localhost:3000
- FastAPI Swagger docs: http://localhost:8000/docs

The frontend uses `BACKEND_INTERNAL_URL=http://backend:8000` inside the Compose network. Do not change this to `localhost` in the container, because `localhost` would refer to the frontend container itself.

### Stop the app

```powershell
docker compose down
```

Rebuild after code or dependency changes:

```powershell
docker compose up -d --build
```

View the most recent backend logs:

```powershell
docker compose logs --tail 200 backend
```

### Notes

- The backend requires `DATABASE_URL`, `DEEPSEEK_API_KEY`, and `HELIUS_API_KEY` at startup/configuration time.
- Compose uses your external database; it does not migrate or provision Supabase tables.
- Helius MCP is started by the backend when the relevant fallback is called. The first invocation may take longer while `npx` resolves/downloads the package. Outbound network access is required.
- For a public deployment, configure HTTPS, restrict database/network access, and use your hosting platform's secret manager instead of committing secrets.

## Run locally without Docker

### Backend

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload
```

### Frontend

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Local frontend rewrites default to `http://127.0.0.1:8000`. Docker overrides this with the internal service URL.

## Tests

Install Python dependencies first, then run from the repository root:

```powershell
pytest
```

The Helius routing tests are unit tests: they verify that wallet questions are routed to read-only actions and that MCP validation errors embedded in text are detected even when `isError` is false. They do not make live Helius requests or require API credentials.

To run just those tests:

```powershell
pytest backend/tests/test_helius_routing.py -v
```

To run tests inside the backend container image:

```powershell
docker compose run --rm --entrypoint pytest backend backend/tests/test_helius_routing.py -v
```

Live API/database integration tests should be run separately against a test environment to avoid accidental usage or writes to production resources.

## Troubleshooting

- **Backend exits immediately:** inspect `docker compose logs backend`; verify all three environment variables and the database connection string.
- **Frontend cannot reach backend:** confirm Compose is running and `BACKEND_INTERNAL_URL` is set to `http://backend:8000`.
- **Helius MCP fails:** inspect backend logs. Confirm the API key, outbound network access, and that the Node/npm installation can run `npx -y helius-mcp@latest`.
- **Database connection fails:** verify the Supabase pooler/direct connection string and SSL options. A database hostname valid on your host may not be reachable from the container.
- **Port already in use:** change the left side of the port mapping in `docker-compose.yml`, e.g. `"3001:3000"` for the frontend.
