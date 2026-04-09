"""Dungeon Master: fog-of-war observations, action validation, turn management."""

from __future__ import annotations

import copy
from typing import Any

from src.simulation.grid import is_in_bounds, neighbor_position
from src.simulation.items import CellType, DIRECTIONS
from src.simulation.state import AgentState, DungeonState, PendingMessage


# ── Observation (Fog of War) ─────────────────────────────────────────────────


def get_observation(state: DungeonState, agent_id: str) -> dict[str, Any]:
    """Return what *agent_id* can see right now.

    Reveals the agent's own cell and the 4 orthogonal neighbours.
    Also delivers any messages that arrived (sent last turn).
    """
    agent = state.agents[agent_id]
    r, c = agent.position

    # Adjacent cells (only if in bounds).
    adjacent: dict[str, str] = {}
    for direction, (dr, dc) in DIRECTIONS.items():
        nr, nc = r + dr, c + dc
        if is_in_bounds(nr, nc, state.grid_height, state.grid_width):
            adjacent[direction] = state.grid[nr][nc]
        else:
            adjacent[direction] = CellType.WALL  # out of bounds = wall

    # Visible entities (other agents in sight).
    visible_entities: list[dict[str, Any]] = []
    visible_positions = {(r, c)}
    for dr, dc in DIRECTIONS.values():
        nr, nc = r + dr, c + dc
        if is_in_bounds(nr, nc, state.grid_height, state.grid_width):
            visible_positions.add((nr, nc))

    for other_id, other_agent in state.agents.items():
        if other_id != agent_id and other_agent.position in visible_positions:
            visible_entities.append({
                "type": "agent",
                "id": other_id,
                "position": list(other_agent.position),
            })

    # Record which cells this agent has now seen (for map_revealed).
    for pos in visible_positions:
        key = f"{pos[0]},{pos[1]}"
        agent.revealed_cells[key] = state.grid[pos[0]][pos[1]]

    # Collect delivered messages (inbox) and clear.
    messages = list(agent.inbox)
    agent.inbox.clear()

    return {
        "agent_position": list(agent.position),
        "current_cell": state.grid[r][c],
        "adjacent_cells": adjacent,
        "visible_entities": visible_entities,
        "turn_number": state.turn_number,
        "has_key": agent.has_key,
        "messages_received": messages,
    }


# ── Action execution ─────────────────────────────────────────────────────────


def execute_action(
    state: DungeonState,
    agent_id: str,
    action: str,
    action_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and execute an agent action, mutating *state* in place.

    Returns an ActionResult dict.
    """
    action_args = action_args or {}
    agent = state.agents[agent_id]

    if action == "move":
        return _do_move(state, agent, action_args.get("direction", ""))
    elif action == "pick_up_item":
        return _do_pick_up(state, agent)
    elif action == "unlock_door":
        return _do_unlock_door(state, agent)
    elif action == "send_message":
        return _do_send_message(state, agent, action_args.get("text", ""))
    elif action == "wait":
        return _result(True, "wait", agent.position, "Waited.")
    else:
        return _result(False, action, agent.position, f"Unknown action: {action}")


# ── Turn management ──────────────────────────────────────────────────────────


def advance_turn(state: DungeonState) -> None:
    """Move to the next agent's turn and deliver pending messages."""
    state.active_agent_idx = (state.active_agent_idx + 1) % len(state.turn_order)

    # Every time we wrap back to agent 0 we bump the turn counter.
    if state.active_agent_idx == 0:
        state.turn_number += 1

    # Deliver messages that were sent last turn.
    still_pending: list[PendingMessage] = []
    for msg in state.pending_messages:
        if msg.sent_turn < state.turn_number:
            recipient = state.agents.get(msg.to_agent)
            if recipient is not None:
                recipient.inbox.append({
                    "from": msg.from_agent,
                    "text": msg.text,
                    "sent_turn": msg.sent_turn,
                })
        else:
            still_pending.append(msg)
    state.pending_messages = still_pending


def check_win(state: DungeonState) -> bool:
    """Check if an agent with the key is standing on the exit (door unlocked)."""
    for agent in state.agents.values():
        if agent.has_key and state.exit_position is not None:
            if agent.position == state.exit_position:
                # Door must already be unlocked (cell changed to EXIT).
                if state.grid[agent.position[0]][agent.position[1]] == CellType.EXIT:
                    state.game_over = True
                    state.win = True
                    return True
    return False


# ── Private action helpers ───────────────────────────────────────────────────


def _do_move(
    state: DungeonState, agent: AgentState, direction: str
) -> dict[str, Any]:
    pos = neighbor_position(agent.position, direction)
    if pos is None:
        return _result(False, f"move_{direction}", agent.position, f"Invalid direction: {direction}")

    r, c = pos
    if not is_in_bounds(r, c, state.grid_height, state.grid_width):
        return _result(False, f"move_{direction}", agent.position, "Out of bounds.")

    cell = state.grid[r][c]
    if cell == CellType.WALL:
        return _result(False, f"move_{direction}", agent.position, "Blocked by a wall.")
    if cell == CellType.LOCKED_DOOR:
        return _result(False, f"move_{direction}", agent.position, "The door is locked.")

    agent.position = (r, c)
    return _result(True, f"move_{direction}", agent.position, f"Moved {direction} to ({r},{c}).")


def _do_pick_up(state: DungeonState, agent: AgentState) -> dict[str, Any]:
    if state.key_position is None:
        return _result(False, "pick_up_item", agent.position, "The key has already been picked up.")

    if agent.position != state.key_position:
        return _result(
            False, "pick_up_item", agent.position,
            f"No item here. The key is not at your position ({agent.position[0]},{agent.position[1]}).",
        )

    agent.has_key = True
    state.grid[state.key_position[0]][state.key_position[1]] = CellType.EMPTY
    state.key_position = None
    return _result(True, "pick_up_item", agent.position, "Picked up the key!")


def _do_unlock_door(state: DungeonState, agent: AgentState) -> dict[str, Any]:
    if not agent.has_key:
        return _result(False, "unlock_door", agent.position, "You don't have the key.")

    if state.door_position is None:
        return _result(False, "unlock_door", agent.position, "Door is already unlocked.")

    # Agent must be adjacent to the locked door.
    for direction in DIRECTIONS:
        adj = neighbor_position(agent.position, direction)
        if adj == state.door_position:
            state.grid[state.door_position[0]][state.door_position[1]] = CellType.EXIT
            state.door_position = None
            return _result(True, "unlock_door", agent.position, "Door unlocked! The exit is now open.")

    return _result(
        False, "unlock_door", agent.position,
        "You must be adjacent to the locked door to unlock it.",
    )


def _do_send_message(
    state: DungeonState, agent: AgentState, text: str
) -> dict[str, Any]:
    if not text.strip():
        return _result(False, "send_message", agent.position, "Cannot send an empty message.")

    # Determine recipient (the other agent).
    others = [aid for aid in state.turn_order if aid != agent.agent_id]
    if not others:
        return _result(False, "send_message", agent.position, "No other agent to send to.")

    for recipient_id in others:
        state.pending_messages.append(
            PendingMessage(
                from_agent=agent.agent_id,
                to_agent=recipient_id,
                text=text.strip(),
                sent_turn=state.turn_number,
            )
        )

    return _result(
        True, "send_message", agent.position,
        f"Message sent (will be delivered next turn): \"{text.strip()[:60]}\"",
    )


def _result(
    success: bool, action: str, position: tuple[int, int], message: str
) -> dict[str, Any]:
    return {
        "success": success,
        "action": action,
        "new_position": list(position),
        "message": message,
        "game_over": False,   # caller patches this if needed
        "win": False,
    }


# ── Pretty-printing ─────────────────────────────────────────────────────────


CELL_CHARS: dict[str, str] = {
    CellType.EMPTY: ".",
    CellType.WALL: "#",
    CellType.KEY: "K",
    CellType.LOCKED_DOOR: "D",
    CellType.EXIT: "E",
}


def render_grid(state: DungeonState) -> str:
    """Return a human-readable string of the grid with agent positions."""
    lines: list[str] = []
    agent_positions: dict[tuple[int, int], str] = {
        a.position: a.agent_id[0].upper() + a.agent_id[-1]  # "Aa", "Ab"
        for a in state.agents.values()
    }
    for r, row in enumerate(state.grid):
        chars: list[str] = []
        for c, cell in enumerate(row):
            if (r, c) in agent_positions:
                chars.append(agent_positions[(r, c)])
            else:
                chars.append(CELL_CHARS.get(cell, "?"))
        lines.append(" ".join(chars))
    return "\n".join(lines)
