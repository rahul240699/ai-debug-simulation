"""FastAPI application entrypoint."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.config import GRID_HEIGHT, GRID_WIDTH, MAX_TURNS, WALL_DENSITY
from src.simulation.grid import create_grid
from src.simulation.dungeon_master import (
    advance_turn,
    check_win,
    execute_action,
    get_observation,
    render_grid,
)
from src.agents.graph import build_graph, reset_beliefs
from src.instrumentation.trace_builder import start_trace, end_trace

logger = logging.getLogger(__name__)

app = FastAPI(title="Prove AI Dungeon", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/simulation/start")
async def start_simulation(
    seed: int | None = None,
    max_turns: int = MAX_TURNS,
) -> dict[str, Any]:
    """Start a new headless simulation run and return the results."""
    dungeon = create_grid(
        width=GRID_WIDTH,
        height=GRID_HEIGHT,
        wall_density=WALL_DENSITY,
        seed=seed,
    )

    graph = build_graph()
    initial_state = {
        "dungeon": dungeon,
        "current_agent_id": dungeon.active_agent,
        "observation": {},
        "action_name": "",
        "action_args": {},
        "action_result": {},
        "belief_before": {},
        "belief_after": {},
        "message_correlation_ids": [],
        "messages": [],
    }

    dungeon.max_turns = max_turns
    reset_beliefs()
    start_trace(dungeon.run_id, metadata={
        "grid": f"{dungeon.grid_width}x{dungeon.grid_height}",
        "max_turns": max_turns,
    })
    try:
        graph.invoke(initial_state)
    finally:
        end_trace(dungeon.run_id)

    return {
        "run_id": dungeon.run_id,
        "turns": dungeon.turn_number,
        "game_over": dungeon.game_over,
        "win": dungeon.win,
        "events": dungeon.event_log,
        "final_grid": render_grid(dungeon),
    }
