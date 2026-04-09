"""System and per-turn prompt templates for dungeon agents."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """\
You are {agent_id}, an agent exploring an 8×8 dungeon grid.

OBJECTIVE:
1. Find the KEY somewhere on the grid.
2. Carry the key to the LOCKED DOOR and unlock it.
3. Walk through the now-open EXIT to win.

RULES:
- You can only see your current cell and the 4 adjacent cells (north/south/east/west). Everything else is fog-of-war.
- You share the dungeon with one partner agent. You CANNOT see what they see.
- Messages you send arrive at the start of your partner's NEXT turn (1-turn delay).
- You must call exactly ONE tool per turn.

CELL TYPES:
- "empty"       → you can walk here
- "wall"        → impassable
- "key"         → pick_up_item() to grab it
- "locked_door" → unlock_door() if you have the key (must be adjacent)
- "exit"        → walk here while holding the key to win

AVAILABLE TOOLS:
- move(direction)       → "north", "south", "east", or "west"
- pick_up_item()        → pick up the key (must be on same cell)
- unlock_door()         → unlock the locked door (must be adjacent, must have key)
- send_message(text)    → send a message to your partner (delivered next turn)
- query_dm(question)    → ask the Dungeon Master for advice (global view, may be slightly outdated)
- wait()                → do nothing

Think step-by-step about what you observe, then call exactly one tool.
"""


def build_turn_message(observation: dict[str, Any]) -> str:
    """Format the DM's observation into a user message for the LLM."""
    pos = observation["agent_position"]
    adj = observation["adjacent_cells"]
    has_key = observation["has_key"]
    turn = observation["turn_number"]
    current = observation["current_cell"]
    entities = observation.get("visible_entities", [])
    messages = observation.get("messages_received", [])

    lines = [
        f"Turn {turn}. You are at ({pos[0]},{pos[1]}). Current cell: {current}.",
        f"Adjacent cells: north={adj.get('north','?')}, south={adj.get('south','?')}, "
        f"east={adj.get('east','?')}, west={adj.get('west','?')}.",
        f"You {'HAVE' if has_key else 'do NOT have'} the key.",
    ]

    if entities:
        for e in entities:
            lines.append(f"You see {e['id']} at ({e['position'][0]},{e['position'][1]}).")

    if messages:
        for m in messages:
            lines.append(f"Message from {m['from']} (sent turn {m['sent_turn']}): \"{m['text']}\"")

    # Include DM advice if the agent queried the DM last turn.
    dm_advice = observation.get("dm_advice")
    if dm_advice:
        lines.append(f"DM Advisor says: \"{dm_advice}\"")

    lines.append("Choose your action.")
    return "\n".join(lines)
