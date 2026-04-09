"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field

from src.config import GRID_HEIGHT, GRID_WIDTH, MAX_TURNS, WALL_DENSITY, DM_STALE_TURNS
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
from src.legibility.router import router as legibility_router, store_run

logger = logging.getLogger(__name__)

app = FastAPI(title="Prove AI Dungeon", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(legibility_router)


# ── In-memory session store for async simulations ────────────────────────────
_sessions: dict[str, dict[str, Any]] = {}
_sessions_lock = threading.Lock()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


class SimulationConfig(BaseModel):
    """Request body for starting a simulation."""

    seed: int | None = None
    max_turns: int = Field(default=MAX_TURNS, ge=1, le=500)
    width: int = Field(default=GRID_WIDTH, ge=4, le=20)
    height: int = Field(default=GRID_HEIGHT, ge=4, le=20)
    wall_density: float = Field(default=WALL_DENSITY, ge=0.0, le=0.4)
    dm_stale_turns: int = Field(default=DM_STALE_TURNS, ge=0, le=10)


@app.post("/api/simulation/start", status_code=202)
async def start_simulation(config: SimulationConfig) -> dict[str, Any]:
    """Fire-and-forget: start a simulation in the background, return session_id."""
    session_id = uuid.uuid4().hex[:12]

    # Create the dungeon eagerly so we can return grid info immediately.
    dungeon = create_grid(
        width=config.width,
        height=config.height,
        wall_density=config.wall_density,
        seed=config.seed,
    )
    dungeon.max_turns = config.max_turns
    dungeon.dm_stale_turns = config.dm_stale_turns

    with _sessions_lock:
        _sessions[session_id] = {
            "status": "running",
            "run_id": dungeon.run_id,
            "current_turn": 0,
            "max_turns": config.max_turns * 2,  # 2 agents per turn
            "grid_size": f"{dungeon.grid_width}x{dungeon.grid_height}",
            "error": None,
            "result": None,
        }

    def _run() -> None:
        try:
            reset_beliefs()
            start_trace(dungeon.run_id, metadata={
                "grid": f"{dungeon.grid_width}x{dungeon.grid_height}",
                "max_turns": config.max_turns,
                "seed": config.seed,
                "dm_stale_turns": config.dm_stale_turns,
            })

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

            # Use a custom list that updates the session turn counter on append.
            class TrackedEventLog(list):  # type: ignore[type-arg]
                def append(self_, event: Any) -> None:
                    super().append(event)
                    with _sessions_lock:
                        if session_id in _sessions:
                            _sessions[session_id]["current_turn"] = len(self_)

            tracked_log = TrackedEventLog(dungeon.event_log)
            dungeon.event_log = tracked_log

            graph.invoke(initial_state)

            run_data = {
                "run_id": dungeon.run_id,
                "seed": config.seed,
                "grid_size": f"{dungeon.grid_width}x{dungeon.grid_height}",
                "dm_stale_turns": config.dm_stale_turns,
                "total_turns": dungeon.turn_number,
                "game_over": dungeon.game_over,
                "win": dungeon.win,
                "events": dungeon.event_log,
                "final_grid": render_grid(dungeon),
            }
            store_run(run_data)

            with _sessions_lock:
                if session_id in _sessions:
                    _sessions[session_id]["status"] = "completed"
                    _sessions[session_id]["current_turn"] = dungeon.turn_number
                    _sessions[session_id]["result"] = run_data

        except Exception as exc:
            logger.exception("Simulation %s failed", session_id)
            with _sessions_lock:
                if session_id in _sessions:
                    _sessions[session_id]["status"] = "failed"
                    _sessions[session_id]["error"] = str(exc)
        finally:
            end_trace(dungeon.run_id)

    # Launch in a background thread — no socket to hold open.
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {
        "session_id": session_id,
        "run_id": dungeon.run_id,
        "status": "running",
        "grid_size": f"{dungeon.grid_width}x{dungeon.grid_height}",
        "max_turns": config.max_turns * 2,
    }


@app.get("/api/simulation/status/{session_id}")
async def simulation_status(session_id: str) -> JSONResponse:
    """Poll the progress of a running simulation."""
    with _sessions_lock:
        session = _sessions.get(session_id)

    if not session:
        return JSONResponse(status_code=404, content={"detail": f"Session '{session_id}' not found"})

    response: dict[str, Any] = {
        "session_id": session_id,
        "status": session["status"],
        "run_id": session["run_id"],
        "current_turn": session["current_turn"],
        "max_turns": session["max_turns"],
        "grid_size": session["grid_size"],
    }

    if session["status"] == "failed":
        response["error"] = session["error"]

    if session["status"] == "completed" and session["result"]:
        response["run_id"] = session["result"]["run_id"]

    return JSONResponse(content=response)
