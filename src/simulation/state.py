"""Core state definitions for the dungeon simulation.

These are plain dataclasses (not TypedDicts) so we get runtime mutability and
clear semantics.  LangGraph wraps them inside its own TypedDict graph state.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any


# ── Per-agent state ──────────────────────────────────────────────────────────

@dataclass
class AgentState:
    """Mutable per-agent state tracked by the Dungeon Master."""

    agent_id: str
    position: tuple[int, int]          # (row, col)
    has_key: bool = False
    # Cells this agent has personally observed (for map_revealed).
    revealed_cells: dict[str, str] = field(default_factory=dict)
    # Inbound message queue: messages arrive with a 1-turn delay.
    inbox: list[dict[str, Any]] = field(default_factory=list)


# ── Message envelope ─────────────────────────────────────────────────────────

@dataclass
class PendingMessage:
    """A message in transit between agents (delivered next turn)."""

    from_agent: str
    to_agent: str
    text: str
    sent_turn: int
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


# ── World-state snapshot (for DM oracle) ─────────────────────────────────────

@dataclass
class WorldSnapshot:
    """A frozen snapshot of the world at a specific turn.

    Stored each turn so the DM oracle can answer queries using
    an intentionally-stale view.
    """
    turn_number: int
    grid: list[list[str]]
    key_position: tuple[int, int] | None
    door_position: tuple[int, int] | None
    exit_position: tuple[int, int] | None
    agent_positions: dict[str, tuple[int, int]]


# ── World state ──────────────────────────────────────────────────────────────

@dataclass
class DungeonState:
    """Complete world state managed by the Dungeon Master."""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    grid: list[list[str]] = field(default_factory=list)
    grid_width: int = 8
    grid_height: int = 8

    key_position: tuple[int, int] | None = None   # None once picked up
    door_position: tuple[int, int] | None = None
    exit_position: tuple[int, int] | None = None

    agents: dict[str, AgentState] = field(default_factory=dict)

    turn_number: int = 0
    max_turns: int = 100
    turn_order: list[str] = field(default_factory=lambda: ["agent_a", "agent_b"])
    active_agent_idx: int = 0

    game_over: bool = False
    win: bool = False

    # Messages waiting to be delivered next turn.
    pending_messages: list[PendingMessage] = field(default_factory=list)

    # Full event log (list of dicts) — ready for instrumentation later.
    event_log: list[dict[str, Any]] = field(default_factory=list)

    # ── History for DM oracle ────────────────────────────────────────────
    # Keyed by turn_number.  Populated at the start of each turn.
    history: dict[int, WorldSnapshot] = field(default_factory=dict)
    # How many turns stale the DM oracle's view is.
    dm_stale_turns: int = 2

    @property
    def active_agent(self) -> str:
        return self.turn_order[self.active_agent_idx % len(self.turn_order)]

    # ── Snapshot helpers ─────────────────────────────────────────────────

    def take_snapshot(self) -> None:
        """Record a deep-copy snapshot of the current world state."""
        self.history[self.turn_number] = WorldSnapshot(
            turn_number=self.turn_number,
            grid=copy.deepcopy(self.grid),
            key_position=self.key_position,
            door_position=self.door_position,
            exit_position=self.exit_position,
            agent_positions={
                aid: a.position for aid, a in self.agents.items()
            },
        )

    def get_stale_snapshot(self) -> WorldSnapshot | None:
        """Return the snapshot *dm_stale_turns* turns ago, or the oldest available."""
        target = max(0, self.turn_number - self.dm_stale_turns)
        # Walk backwards from target to find the closest available.
        for t in range(target, -1, -1):
            if t in self.history:
                return self.history[t]
        return None
