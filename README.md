# Prove AI — Multi-Agent Dungeon Simulation

A multi-agent dungeon simulation built for demonstrating **agent observability and legibility**. Two LLM-powered agents navigate a grid to find a key and reach an exit, while every decision is captured in structured traces for human diagnosis.

See [TECHNICAL_PLAN.md](TECHNICAL_PLAN.md) for the full architecture and design.

## Quick Start

```bash
# Backend
pip install -e ".[dev]"
uvicorn src.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

## Project Structure

- `src/simulation/` — Core grid logic, items, and Dungeon Master state
- `src/agents/` — LangGraph node definitions, tools, and LLM logic
- `src/instrumentation/` — Langfuse wrappers and Event Schema
- `src/legibility/` — API endpoints for the Diagnosis Dashboard
- `frontend/` — Next.js Diagnosis Dashboard
