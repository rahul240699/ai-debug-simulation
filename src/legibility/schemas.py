"""Pydantic response models for legibility API."""

from __future__ import annotations

from pydantic import BaseModel


class MetricsCard(BaseModel):
    """Three core metrics for a simulation run."""
    avg_information_lag: float          # avg turns behind agents were
    discrepancy_count: int              # total discrepancy events
    coordination_efficiency: int | None  # turns to share "key found" message (None if never)


class CriticalEvent(BaseModel):
    """A decision point or critical divergence on the timeline."""
    turn_number: int
    agent_id: str
    event_type: str   # "decision_point" | "critical_divergence" | "dm_oracle" | "coordination"
    severity: str     # "green" | "yellow" | "red"
    headline: str     # e.g. "Agent A moved South based on DM info from 2 turns ago"
    details: str | None = None
    dm_query: str | None = None
    dm_advice: str | None = None
    stale_turns: int | None = None


class BeliefComparison(BaseModel):
    """Split-view data: what agent believed vs actual world state."""
    turn_number: int
    agent_id: str
    agent_position: list[int]
    # Agent's belief
    believed_grid: dict[str, str]
    believed_key_location: list[int] | None
    believed_partner_location: list[int] | None
    believed_has_key: bool
    believed_partner_has_key: bool
    # Actual world
    actual_adjacent: dict[str, str]
    actual_key_exists: bool         # was key still on the grid?
    actual_visible_entities: list[dict]
    actual_has_key: bool
    # Action taken and result
    chosen_action: str
    action_args: dict
    action_result: dict
    # Discrepancy
    discrepancy_detected: bool
    discrepancy_details: str | None
    belief_diff: list[dict] | None


class FailureCategory(BaseModel):
    category: str       # "stale_info" | "tool_failure" | "coordination" | "dm_oracle"
    count: int
    description: str
    related_turns: list[int]


class DiagnosisSummary(BaseModel):
    """Root cause analysis for a run."""
    root_cause: str             # natural-language summary
    failure_categories: list[FailureCategory]


class RunDiagnosis(BaseModel):
    """Full diagnosis payload for /api/diagnose."""
    run_id: str
    seed: int | None = None
    grid_size: str
    dm_stale_turns: int
    total_turns: int
    game_over: bool
    win: bool
    metrics: MetricsCard
    summary: DiagnosisSummary
    timeline: list[CriticalEvent]
    events: list[dict]            # all raw EventRecords
