"""LangGraph graph state — the typed dict that flows through nodes."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph import add_messages


class GraphState(TypedDict):
    """State flowing through the LangGraph dungeon loop.

    The DungeonState dataclass is stored as a mutable reference inside
    `dungeon` — LangGraph nodes mutate it in place and propagate the
    reference forward.
    """

    # Core simulation state (mutable dataclass, passed by reference).
    dungeon: Any  # src.simulation.state.DungeonState

    # Per-turn ephemeral fields (overwritten each step).
    current_agent_id: str
    observation: dict[str, Any]
    action_name: str
    action_args: dict[str, Any]
    action_result: dict[str, Any]

    # Belief snapshots for discrepancy detection.
    belief_before: dict[str, Any]
    belief_after: dict[str, Any]
    message_correlation_ids: list[str]

    # Rationale extracted from the LLM response text.
    rationale: str

    # LangGraph message history — accumulates across turns.
    messages: Annotated[list, add_messages]
