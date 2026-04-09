"""Generate a deterministic sample run JSON that demonstrates discrepancy events.

Uses a fixed seed to create a reproducible simulation, then plays a scripted
sequence (no LLM) to guarantee at least one discrepancy event — including
an agent following stale DM oracle advice.

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


def run_scripted_simulation() -> dict:
    """Execute a scripted simulation demonstrating DM oracle stale advice failure."""
    dungeon = create_grid(width=8, height=8, wall_density=0.15, seed=42)
    dungeon.max_turns = 20
    dungeon.dm_stale_turns = 2  # DM sees world 2 turns ago

    beliefs: dict[str, BeliefModel] = {
        "agent_a": BeliefModel(),
        "agent_b": BeliefModel(),
    }

    # ── Scripted actions ─────────────────────────────────────────────────
    # The sequence is designed so:
    # 1. Early turns: agents explore, world snapshots build up
    # 2. Agent A queries the DM for key location
    # 3. Meanwhile Agent B picks up the key (world changes)
    # 4. Agent A acts on the stale DM advice (goes to old key location)
    # 5. Discrepancy: key is not where DM said it would be

    agent_a_actions = [
        ("move", {"direction": "east"}),       # Turn 0: explore
        ("move", {"direction": "east"}),       # Turn 1: explore
        ("query_dm", {"question": "Where is the key?"}),  # Turn 2: ask DM (gets stale info)
        ("move", {"direction": "south"}),      # Turn 3: follow DM advice
        ("move", {"direction": "south"}),      # Turn 4: follow DM advice
        ("move", {"direction": "south"}),      # Turn 5: follow DM advice
        ("pick_up_item", {}),                  # Turn 6: try to pick up key (FAIL — stale!)
        ("query_dm", {"question": "Where is the key and exit?"}),  # Turn 7: ask again
        ("move", {"direction": "east"}),       # Turn 8
        ("wait", {}),                          # Turn 9
    ]

    agent_b_actions = [
        ("move", {"direction": "south"}),      # Turn 0: explore
        ("move", {"direction": "south"}),      # Turn 1: head toward key
        ("move", {"direction": "west"}),       # Turn 2: navigate
        ("move", {"direction": "south"}),      # Turn 3: navigate
        ("pick_up_item", {}),                  # Turn 4: pick up key (may succeed)
        ("send_message", {"text": "I picked up the key!"}),  # Turn 5: tell partner
        ("move", {"direction": "south"}),      # Turn 6: head to door
        ("move", {"direction": "east"}),       # Turn 7: navigate
        ("move", {"direction": "south"}),      # Turn 8
        ("wait", {}),                          # Turn 9
    ]

    action_queues = {
        "agent_a": list(agent_a_actions),
        "agent_b": list(agent_b_actions),
    }

    events: list[dict] = []

    while not dungeon.game_over and dungeon.turn_number < dungeon.max_turns:
        agent_id = dungeon.active_agent
        belief = beliefs[agent_id]

        # 1. Observe
        obs = get_observation(dungeon, agent_id)
        belief_before = belief.snapshot()
        update_belief(belief, obs)
        belief_after = belief.snapshot()

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

        msg_corr += result.get("correlation_ids", [])

        # 4. Discrepancy detection
        detected, details, diff = detect_discrepancies(belief_before, obs, result)

        # 5. DM oracle metadata
        dm_query = None
        dm_advice = None
        dm_stale = None
        if action_name == "query_dm":
            dm_query = action_args.get("question", "")
            dm_advice = result.get("advice", "")
            dm_stale = result.get("stale_turns_count", 0)

        # 6. Record event
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
            dm_query=dm_query,
            dm_advice=dm_advice,
            dm_stale_turns_count=dm_stale,
        )
        events.append(event.to_dict())

        if detected:
            print(f"  ⚠ DISCREPANCY Turn {dungeon.turn_number} {agent_id}: {details}")
        if dm_advice:
            print(f"  🔮 DM ORACLE Turn {dungeon.turn_number} {agent_id}: {dm_advice} (stale={dm_stale})")

        # 7. Advance turn
        advance_turn(dungeon)

    # Separate DM oracle events for the summary
    dm_events = [
        {
            "turn": e["turn_number"],
            "agent": e["agent_id"],
            "dm_query": e["dm_query"],
            "dm_advice": e["dm_advice"],
            "stale_turns_count": e["dm_stale_turns_count"],
        }
        for e in events
        if e.get("dm_query")
    ]

    output = {
        "run_id": dungeon.run_id,
        "seed": 42,
        "grid_size": f"{dungeon.grid_width}x{dungeon.grid_height}",
        "dm_stale_turns": dungeon.dm_stale_turns,
        "max_turns": dungeon.max_turns,
        "total_turns": dungeon.turn_number,
        "game_over": dungeon.game_over,
        "win": dungeon.win,
        "final_grid": render_grid(dungeon),
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
        "dm_oracle_events": dm_events,
    }
    return output


def main():
    print("Generating sample run with seed=42, dm_stale_turns=2 ...")
    result = run_scripted_simulation()

    out_path = Path(__file__).resolve().parent.parent / "sample_run.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    n_discrepancies = len(result["discrepancy_summary"])
    n_dm = len(result["dm_oracle_events"])
    print(f"\nDone: {len(result['events'])} events, {n_discrepancies} discrepancies, {n_dm} DM oracle calls.")
    print(f"Written to: {out_path}")

    if n_discrepancies > 0:
        print("\nDiscrepancy events:")
        for d in result["discrepancy_summary"]:
            print(f"  Turn {d['turn']} | {d['agent']}: {d['details']}")

    if n_dm > 0:
        print("\nDM Oracle calls:")
        for d in result["dm_oracle_events"]:
            print(f"  Turn {d['turn']} | {d['agent']}: Q=\"{d['dm_query']}\" → \"{d['dm_advice']}\" (stale={d['stale_turns_count']})")


if __name__ == "__main__":
    main()
