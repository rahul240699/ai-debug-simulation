# Prove AI — Multi-Agent Dungeon Simulation

A multi-agent dungeon simulation built for demonstrating **agent observability and legibility**. Two LLM-powered agents navigate a grid to find a key and reach an exit, while every decision is captured in structured traces for human diagnosis.

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| **Python** | ≥ 3.11 | 3.14 tested |
| **Node.js** | ≥ 18 | For the Next.js dashboard |
| **npm** | ≥ 9 | Ships with Node |
| **OpenAI API key** | — | GPT-4o used by default |
| **Langfuse account** | — | Free tier at [cloud.langfuse.com](https://cloud.langfuse.com) |

## 1. Clone & create a virtual environment

```bash
git clone <repo-url> && cd prove-ai-assignment
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
```

## 2. Set up environment variables

Copy the example file and fill in your keys:

```bash
cp .env.example .env
```

Open `.env` and set:

```dotenv
# OpenAI — required for running simulations
OPENAI_API_KEY=sk-...

# Langfuse — required for trace instrumentation
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

**Where to get these:**

- **OpenAI**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys) → Create new secret key
- **Langfuse**: [cloud.langfuse.com](https://cloud.langfuse.com) → Sign up → Project Settings → API Keys → Create new key pair (public + secret)

> The dashboard can display pre-generated demo runs without any API keys. Keys are only needed to run new simulations.

## 3. Install Python dependencies

```bash
pip install -e ".[dev]"
```

Key packages installed:
- `fastapi` + `uvicorn` — API server
- `langgraph` + `langchain-openai` — Agent orchestration & LLM calls
- `langfuse` — Observability traces
- `pydantic` — Structured schemas
- `pytest` — Test suite (dev)

## 4. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

## 5. Run the application

Start the backend and frontend in **separate terminals**:

```bash
# Terminal 1 — Backend (port 8000)
source .venv/bin/activate
uvicorn src.main:app --port 8000 --reload

# Terminal 2 — Frontend (port 3000)
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the Diagnosis Dashboard.

## 6. Run tests

```bash
source .venv/bin/activate
pytest
```

## 7. Generate demo runs (optional)

Pre-generate simulation JSON files so the dashboard has data without needing API keys:

```bash
source .venv/bin/activate
python generate_demos.py
```

Demo runs are saved to `demo_runs/` and loaded automatically by the backend.

---

## Project Structure

```
├── src/
│   ├── simulation/       # Core grid logic, items, Dungeon Master state
│   ├── agents/           # LangGraph node definitions, tools, LLM logic
│   ├── instrumentation/  # Langfuse wrappers and Event Schema
│   ├── legibility/       # Diagnosis API endpoints
│   └── main.py           # FastAPI app (simulation start/poll + diagnosis)
├── frontend/             # Next.js Diagnosis Dashboard
│   └── src/
│       ├── app/          # Dashboard page
│       ├── components/   # UI components (SimulationControls, StepViewer, RunSelector, etc.)
│       └── lib/          # API client & types
├── demo_runs/            # Pre-generated simulation JSONs
├── tests/                # pytest test suite
├── generate_demos.py     # Script to create demo runs
├── .env.example          # Environment variable template
└── pyproject.toml        # Python project config & dependencies
```

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | For simulations | OpenAI API key |
| `LANGFUSE_PUBLIC_KEY` | For tracing | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | For tracing | Langfuse project secret key |
| `LANGFUSE_HOST` | For tracing | Langfuse endpoint (default: `https://cloud.langfuse.com`) |
| `APP_ENV` | No | `development` or `production` |
| `LOG_LEVEL` | No | Logging level (default: `INFO`) |
| `GRID_WIDTH` | No | Default grid width (default: `8`) |
| `GRID_HEIGHT` | No | Default grid height (default: `8`) |
| `MAX_TURNS` | No | Default max turns per simulation (default: `20`) |
