"""Belief model: per-agent internal map memory and belief update logic.

Each agent maintains a cumulative belief about the grid — what it has seen
so far.  On every observation the belief is updated with the new data.  The
old belief snapshot is preserved so the discrepancy detector can diff
before/after.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from src.simulation.items import DIRECTIONS


@dataclass
class BeliefModel:
    """An agent's internal model of the world."""

    # Cumulative map memory: "row,col" → last-known cell type.
    grid_knowledge: dict[str, str] = field(default_factory=dict)

    key_location: list[int] | None = None       # [row, col] or None
    exit_location: list[int] | None = None
    door_location: list[int] | None = None
    partner_location: list[int] | None = None

    has_key: bool = False
    partner_has_key: bool = False
    last_updated_turn: int = -1

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serialisable deep copy of the belief."""
        return {
            "grid_knowledge": dict(self.grid_knowledge),
            "key_location": list(self.key_location) if self.key_location else None,
            "exit_location": list(self.exit_location) if self.exit_location else None,
            "door_location": list(self.door_location) if self.door_location else None,
            "partner_location": list(self.partner_location) if self.partner_location else None,
            "has_key": self.has_key,
            "partner_has_key": self.partner_has_key,
            "last_updated_turn": self.last_updated_turn,
        }


def update_belief(
    belief: BeliefModel,
    observation: dict[str, Any],
) -> None:
    """Mutate *belief* in place using the new observation from the DM."""
    pos = observation["agent_position"]
    adj = observation["adjacent_cells"]
    turn = observation["turn_number"]

    # 1. Record what we see in grid_knowledge.
    current_key = f"{pos[0]},{pos[1]}"
    belief.grid_knowledge[current_key] = observation["current_cell"]

    for direction, cell_type in adj.items():
        delta = DIRECTIONS.get(direction)
        if delta is None:
            continue
        nr, nc = pos[0] + delta[0], pos[1] + delta[1]
        belief.grid_knowledge[f"{nr},{nc}"] = cell_type

    # 2. Update key location if we see the key.
    for direction, cell_type in adj.items():
        if cell_type == "key":
            delta = DIRECTIONS[direction]
            belief.key_location = [pos[0] + delta[0], pos[1] + delta[1]]
    if observation["current_cell"] == "key":
        belief.key_location = list(pos)

    # If we're on a cell that used to have the key and it's gone, clear belief.
    if belief.key_location is not None:
        bk = f"{belief.key_location[0]},{belief.key_location[1]}"
        if bk in belief.grid_knowledge and belief.grid_knowledge[bk] != "key":
            belief.key_location = None

    # 3. Update door / exit locations.
    for direction, cell_type in adj.items():
        delta = DIRECTIONS[direction]
        cell_pos = [pos[0] + delta[0], pos[1] + delta[1]]
        if cell_type == "locked_door":
            belief.door_location = cell_pos
        elif cell_type == "exit":
            belief.exit_location = cell_pos
    if observation["current_cell"] == "exit":
        belief.exit_location = list(pos)

    # 4. Update partner location from visible entities.
    for entity in observation.get("visible_entities", []):
        if entity["type"] == "agent":
            belief.partner_location = list(entity["position"])

    # 5. Update key possession.
    belief.has_key = observation["has_key"]

    # 6. Update from messages received.
    for msg in observation.get("messages_received", []):
        text = msg.get("text", "").lower()
        if "picked up the key" in text or "i have the key" in text:
            belief.partner_has_key = True
            belief.key_location = None

    belief.last_updated_turn = turn

