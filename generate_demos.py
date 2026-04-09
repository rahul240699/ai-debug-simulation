"""Generate multiple demo run JSON files with different configs."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.simulation.grid import create_grid
from src.simulation.dungeon_master import render_grid
from src.agents.graph import build_graph, reset_beliefs
from src.instrumentation.trace_builder import start_trace, end_trace

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

DEMO_DIR = Path(__file__).resolve().parent / "demo_runs"
DEMO_DIR.mkdir(exist_ok=True)

CONFIGS = [
    {"label": "small_quick",   "seed": 42,  "width": 6, "height": 6, "max_turns": 30, "dm_stale": 2, "wall_density": 0.1},
    {"label": "default_loss",  "seed": 99,  "width": 8, "height": 8, "max_turns": 40, "dm_stale": 3, "wall_density": 0.15},
    {"label": "high_lag",      "seed": 7,   "width": 8, "height": 8, "max_turns": 50, "dm_stale": 5, "wall_density": 0.15},
    {"label": "dense_walls",   "seed": 123, "width": 8, "height": 8, "max_turns": 40, "dm_stale": 2, "wall_density": 0.3},
    {"label": "large_grid",    "seed": 55,  "width": 10, "height": 10, "max_turns": 60, "dm_stale": 2, "wall_density": 0.12},
]


def generate_run(cfg: dict) -> None:
    label = cfg["label"]
    print(f"\n{'='*50}")
    print(f"Generating: {label}")
    print(f"  seed={cfg['seed']} grid={cfg['width']}x{cfg['height']} turns={cfg['max_turns']} dm_stale={cfg['dm_stale']}")

    dungeon = create_grid(
        width=cfg["width"],
        height=cfg["height"],
        wall_density=cfg["wall_density"],
        seed=cfg["seed"],
    )
    dungeon.max_turns = cfg["max_turns"]
    dungeon.dm_stale_turns = cfg["dm_stale"]

    reset_beliefs()
    start_trace(dungeon.run_id, metadata={
        "grid": f"{dungeon.grid_width}x{dungeon.grid_height}",
        "max_turns": cfg["max_turns"],
        "seed": cfg["seed"],
        "dm_stale_turns": cfg["dm_stale"],
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

    try:
        graph.invoke(initial_state)
    except Exception as exc:
        print(f"  Run failed with error: {exc}")
    finally:
        end_trace(dungeon.run_id)

    run_data = {
        "run_id": dungeon.run_id,
        "label": label,
        "seed": cfg["seed"],
        "grid_size": f"{dungeon.grid_width}x{dungeon.grid_height}",
        "dm_stale_turns": cfg["dm_stale"],
        "total_turns": dungeon.turn_number,
        "game_over": dungeon.game_over,
        "win": dungeon.win,
        "events": dungeon.event_log,
        "final_grid": render_grid(dungeon),
    }

    out_path = DEMO_DIR / f"{label}.json"
    with open(out_path, "w") as f:
        json.dump(run_data, f, indent=2, default=str)

    outcome = "WIN" if dungeon.win else "LOSS"
    print(f"  → {outcome} after {dungeon.turn_number} turns | {len(dungeon.event_log)} events")
    print(f"  Saved to {out_path}")


def main() -> None:
    for cfg in CONFIGS:
        generate_run(cfg)
    print(f"\n✅ Generated {len(CONFIGS)} demo runs in {DEMO_DIR}/")


if __name__ == "__main__":
    main()
