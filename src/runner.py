"""Headless simulation runner — runs N turns and prints state to console."""

from __future__ import annotations

import argparse
import logging
import sys

from src.config import GRID_HEIGHT, GRID_WIDTH, MAX_TURNS, WALL_DENSITY
from src.simulation.grid import create_grid
from src.simulation.dungeon_master import render_grid
from src.agents.graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a headless dungeon simulation.")
    parser.add_argument("--turns", type=int, default=MAX_TURNS, help="Max turns to simulate.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for grid generation.")
    parser.add_argument("--width", type=int, default=GRID_WIDTH)
    parser.add_argument("--height", type=int, default=GRID_HEIGHT)
    parser.add_argument("--wall-density", type=float, default=WALL_DENSITY)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    # Suppress noisy HTTP logs unless verbose.
    if not args.verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    # 1. Create the dungeon.
    dungeon = create_grid(
        width=args.width,
        height=args.height,
        wall_density=args.wall_density,
        seed=args.seed,
    )

    print("=" * 50)
    print("DUNGEON SIMULATION")
    print(f"Run ID: {dungeon.run_id}")
    print(f"Grid: {dungeon.grid_width}×{dungeon.grid_height}")
    print(f"Key: {dungeon.key_position}")
    print(f"Door: {dungeon.door_position}")
    print(f"Exit: {dungeon.exit_position}")
    for aid, agent in dungeon.agents.items():
        print(f"  {aid}: {agent.position}")
    print("=" * 50)
    print("\nInitial Grid:")
    print(render_grid(dungeon))
    print()

    dungeon.max_turns = args.turns

    # 2. Build and run the LangGraph state machine.
    graph = build_graph()

    initial_state = {
        "dungeon": dungeon,
        "current_agent_id": dungeon.active_agent,
        "observation": {},
        "action_name": "",
        "action_args": {},
        "action_result": {},
        "messages": [],
    }

    try:
        result = graph.invoke(initial_state)
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user.")

    # 3. Summary.
    print(f"\nFinal state after {dungeon.turn_number} turns:")
    print(render_grid(dungeon))
    print(f"Game over: {dungeon.game_over}  |  Win: {dungeon.win}")
    print(f"Events logged: {len(dungeon.event_log)}")


if __name__ == "__main__":
    main()
