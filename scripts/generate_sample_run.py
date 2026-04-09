"""Generate a deterministic sample run JSON that demonstrates discrepancy events.

Uses a fixed seed to create a reproducible simulation, then plays a scripted
sequence (no LLM) to guarantee at least one discrepancy event — typically
an agent bumping into an unseen wall (soft failure) or acting on a stale
key location.

Usage:
    python -m scripts.generate_sample_run
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.belief import BeliefModel, update_belief
from src.instrumentation.discrepancy import detect_discrepancies
from src.instrumentation.event_schema import EventRecord
from src.simulation.dungeon_master import (
    advance_turn,
    check_win,
    execute_action,
    get_observation,
    render_grid,
)
from src.simulation.grid import create_grid

# ── Scripted action sequences ────────────────────────────────────────────────

AGENT_A_ACTIONS = [
    ("move", {"direction": "east"}),
    ("move", {"direction": "east"}),
    ("move", {"direction": "south"}),
    ("move", {"direction": "south"}),
    ("move", {"direction": "south"}),   # likely hits wall/obstacle → soft failure
    ("move", {"direction": "west"}),
    ("pick_up_item", {}),               # may fail if not on key
    ("send_message", {"text": "I picked up the key!"}),
    ("move", {"direction": "south"}),
    ("wait", {}),
]

AGENT_B_ACTIONS = [
    ("move", {"direction": "south"}),
    ("move", {"direction": "south"}),
    ("move", {"direction": "west"}),
    ("move", {"direction": "west"}),
    ("move", {"direction": "south"}),   # likely hits wall → discrepancy
    ("move", {"direction": "east"}),
    ("move", {"direction": "east"}),
    ("wait", {}),
    ("move", {"direction": "south"}),
    ("wait", {}),
]


def run_scripted_simulation() -> dict:
    """Execute a scripted simulation and return the full event log."""
    dungeon = create_grid(width=8, height=8, wall_density=0.15, seed=42)
    dungeon.max_turns = 10

    beliefs: dict[str, BeliefModel] = {
        "agent_a": BeliefModel(),
        "agent_b": BeliefModel(),
    }

    action_queues = {
        "agent_a": list(AGENT_A_ACTIONS),
        "agent_b": list(AGENT_B_ACTIONS),
    }

    events: list[dict] = []
    step = 0

    while not dungeon.game_over and dungeon.turn_number < dungeon.max_turns:
        agent_id = dungeon.active_agent
        belief = beliefs[agent_id]

        # 1. Observe
        obs = get_observation(dungeon, agent_id)
        belief_before = belief.snapshot()
        update_belief(belief, obs)
        belief_after = belief.snapshot()

        # Collect correlation IDs from received messages
        msg_corr = [
            m["correlation_id"]
            for m in obs.get("messages_received", [])
            if "correlation_id" in m
        ]

        # 2. Choose action (scripted)
        queue = action_queues[agent_id]
        if queue:
            action_name, action_args = queue.pop(0)
        else:
            action_name, action_args = "wait", {}

        # 3. Act
        result = execute_action(dungeon, agent_id, action_name, action_args)
        check_win(dungeon)

        # Collect send_message correlation IDs
        msg_corr += result.get("correlation_ids", [])

        # 4. Discrepancy detection
        detected, details, diff = detect_discrepancies(belief_before, obs, result)

        # 5. Record event
        event = EventRecord(
            run_id=dungeon.run_id,
            turn_number=dungeon.turn_number,
            agent_id=agent_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            observed_state=obs,
            belief_before=belief_before,
            belief_after=belief_after,
            rationale=f"Scripted: {action_name}",
            chosen_action=action_name,
            action_args=action_args,
            action_result=result,
            discrepancy_detected=detected,
            discrepancy_details=details,
            belief_diff=diff,
            message_correlation_ids=msg_corr,
        )
        events.append(event.to_dict())

        if detected:
            print(
                f"  ⚠ DISCREPANCY Turn {dungeon.turn_number} {agent_id}: {details}"
            )

        # 6. Advance turn
        advance_turn(dungeon)
        step += 1

    # Build final output
    output = {
        "run_id": dungeon.run_id,
        "seed": 42,
        "grid_size": f"{dungeon.grid_width}x{dungeon.grid_height}",
        "max_turns": dungeon.max_turns,
        "total_turns": dungeon.turn_number,
        "game_over": dungeon.game_over,
        "win": dungeon.win,
        "initial_grid": render_grid(dungeon),
        "events": events,
        "discrepancy_summary": [
            {
                "turn": e["turn_number"],
                "agent": e["agent_id"],
                "details": e["discrepancy_details"],
            }
            for e in events
            if e["discrepancy_detected"]
        ],
    }
    return output


def main():
    print("Generating sample run with seed=42 ...")
    result = run_scripted_simulation()

    out_path = Path(__file__).resolve().parent.parent / "sample_run.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    n_discrepancies = len(result["discrepancy_summary"])
    print(f"\nDone: {len(result['events'])} events, {n_discrepancies} discrepancies.")
    print(f"Written to: {out_path}")

    if n_discrepancies > 0:
        print("\nDiscrepancy events:")
        for d in result["discrepancy_summary"]:
            print(f"  Turn {d['turn']} | {d['agent']}: {d['details']}")
    else:
        print("\n⚠ No discrepancies detected — try a different seed or longer run.")


if __name__ == "__main__":
    main()
