"""Structured event record emitted for every agent step.

This is the core observability artifact.  Each record captures what the
agent saw, what it believed, what it chose, and whether a discrepancy
between belief and reality was detected.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EventRecord:
    """One per agent step — the full instrumentation payload."""

    run_id: str
    turn_number: int
    agent_id: str
    timestamp: str                                  # ISO 8601

    # Observation from the Dungeon Master (3×3-ish view).
    observed_state: dict[str, Any] = field(default_factory=dict)

    # Agent's cumulative belief *before* this observation was applied.
    belief_before: dict[str, Any] = field(default_factory=dict)
    # Agent's cumulative belief *after* this observation was applied.
    belief_after: dict[str, Any] = field(default_factory=dict)

    # LLM reasoning.
    rationale: str = ""
    chosen_action: str = ""
    action_args: dict[str, Any] = field(default_factory=dict)

    # DM action result.
    action_result: dict[str, Any] = field(default_factory=dict)

    # Discrepancy tracking.
    discrepancy_detected: bool = False
    discrepancy_details: str | None = None
    belief_diff: list[dict[str, Any]] | None = None

    # Message correlation.
    message_correlation_ids: list[str] = field(default_factory=list)

    # DM oracle metadata.
    dm_query: str | None = None
    dm_advice: str | None = None
    dm_stale_turns_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
