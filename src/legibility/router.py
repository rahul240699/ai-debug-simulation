"""FastAPI router for /api/runs/* legibility endpoints.

Serves diagnosis data from:
1. The in-memory event_log on DungeonState (when a run just completed), OR
2. A sample_run.json file (for demo/development).

The /api/diagnose endpoint is the primary entry point — it loads events and
runs the full diagnosis pipeline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from src.legibility.diagnosis import (
    build_diagnosis,
    compute_metrics,
    extract_critical_events,
)
from src.legibility.schemas import BeliefComparison, RunDiagnosis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["legibility"])

# ── In-memory store for completed runs ───────────────────────────────────────
# Populated by the simulation endpoint after a run finishes.
_completed_runs: dict[str, dict[str, Any]] = {}

SAMPLE_RUN_PATH = Path(__file__).resolve().parent.parent.parent / "sample_run.json"


def store_run(run_data: dict[str, Any]) -> None:
    """Store a completed run's data for later diagnosis."""
    run_id = run_data.get("run_id", "")
    if run_id:
        _completed_runs[run_id] = run_data


def _load_sample_run() -> dict[str, Any] | None:
    """Load sample_run.json if it exists."""
    if SAMPLE_RUN_PATH.exists():
        with open(SAMPLE_RUN_PATH) as f:
            return json.load(f)
    return None


def _get_run(run_id: str) -> dict[str, Any]:
    """Retrieve a run by ID or fall back to sample_run.json."""
    if run_id in _completed_runs:
        return _completed_runs[run_id]
    # Try sample run
    sample = _load_sample_run()
    if sample and (run_id == "latest" or sample.get("run_id") == run_id):
        return sample
    raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/diagnose")
async def diagnose(run_id: str = "latest") -> RunDiagnosis:
    """Full diagnosis for a run — metrics, timeline, root-cause summary.

    Use ?run_id=latest to diagnose the most recent sample run.
    """
    run = _get_run(run_id)
    events = run.get("events", [])
    win = run.get("win", False)

    metrics = compute_metrics(events)
    timeline = extract_critical_events(events)
    summary = build_diagnosis(events, win)

    return RunDiagnosis(
        run_id=run.get("run_id", run_id),
        seed=run.get("seed"),
        grid_size=run.get("grid_size", "8x8"),
        dm_stale_turns=run.get("dm_stale_turns", 2),
        total_turns=run.get("total_turns", 0),
        game_over=run.get("game_over", False),
        win=win,
        metrics=metrics,
        summary=summary,
        timeline=timeline,
        events=events,
    )


@router.get("/runs/{run_id}/events/{turn}")
async def get_event_detail(run_id: str, turn: int) -> BeliefComparison:
    """Split-view data for a specific turn: belief vs reality."""
    run = _get_run(run_id)
    events = run.get("events", [])

    # Find the event for this turn
    matching = [e for e in events if e["turn_number"] == turn]
    if not matching:
        raise HTTPException(status_code=404, detail=f"Turn {turn} not found")

    e = matching[0]
    belief = e.get("belief_before", {})
    obs = e.get("observed_state", {})

    return BeliefComparison(
        turn_number=e["turn_number"],
        agent_id=e["agent_id"],
        agent_position=obs.get("agent_position", [0, 0]),
        believed_grid=belief.get("grid_knowledge", {}),
        believed_key_location=belief.get("key_location"),
        believed_partner_location=belief.get("partner_location"),
        believed_has_key=belief.get("has_key", False),
        believed_partner_has_key=belief.get("partner_has_key", False),
        actual_adjacent=obs.get("adjacent_cells", {}),
        actual_key_exists=obs.get("current_cell") == "key" or any(
            v == "key" for v in obs.get("adjacent_cells", {}).values()
        ),
        actual_visible_entities=obs.get("visible_entities", []),
        actual_has_key=obs.get("has_key", False),
        chosen_action=e.get("chosen_action", ""),
        action_args=e.get("action_args", {}),
        action_result=e.get("action_result", {}),
        discrepancy_detected=e.get("discrepancy_detected", False),
        discrepancy_details=e.get("discrepancy_details"),
        belief_diff=e.get("belief_diff"),
    )


@router.get("/runs")
async def list_runs() -> list[dict[str, Any]]:
    """List available runs."""
    runs = []
    for rid, data in _completed_runs.items():
        runs.append({
            "run_id": rid,
            "total_turns": data.get("total_turns", 0),
            "win": data.get("win", False),
            "game_over": data.get("game_over", False),
        })
    # Include sample run if available
    sample = _load_sample_run()
    if sample:
        sid = sample.get("run_id", "sample")
        if sid not in _completed_runs:
            runs.append({
                "run_id": sid,
                "total_turns": sample.get("total_turns", 0),
                "win": sample.get("win", False),
                "game_over": sample.get("game_over", False),
            })
    return runs
