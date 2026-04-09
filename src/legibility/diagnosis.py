"""Automated failure-mode analysis and diagnosis logic.

Analyses a list of EventRecord dicts from a simulation run and produces:
- Metrics (avg info lag, discrepancy count, coordination efficiency)
- Critical events timeline (only decision/divergence points)
- Root-cause summary
"""

from __future__ import annotations

from typing import Any

from src.legibility.schemas import (
    CriticalEvent,
    DiagnosisSummary,
    FailureCategory,
    MetricsCard,
)


def compute_metrics(events: list[dict[str, Any]]) -> MetricsCard:
    """Compute the three core metrics from event records."""
    discrepancy_count = sum(1 for e in events if e.get("discrepancy_detected"))

    # Avg information lag: for each event, lag = turn_number - belief.last_updated_turn
    lags: list[int] = []
    for e in events:
        belief = e.get("belief_before", {})
        last_updated = belief.get("last_updated_turn", -1)
        turn = e.get("turn_number", 0)
        if last_updated >= 0:
            lag = turn - last_updated
            lags.append(lag)
    avg_lag = round(sum(lags) / len(lags), 2) if lags else 0.0

    # Coordination efficiency: turns until "key found" message was shared
    coord_eff: int | None = None
    key_pickup_turn: int | None = None
    key_message_turn: int | None = None

    for e in events:
        result = e.get("action_result", {})
        action = e.get("chosen_action", "")
        # Detect key pickup
        if action == "pick_up_item" and result.get("success"):
            if key_pickup_turn is None:
                key_pickup_turn = e["turn_number"]
        # Detect key-related message sent
        if action == "send_message":
            text = e.get("action_args", {}).get("text", "").lower()
            if "key" in text and result.get("success"):
                if key_message_turn is None:
                    key_message_turn = e["turn_number"]

    if key_pickup_turn is not None and key_message_turn is not None:
        coord_eff = key_message_turn - key_pickup_turn
    elif key_pickup_turn is not None:
        # Key picked up but never communicated
        coord_eff = None

    return MetricsCard(
        avg_information_lag=avg_lag,
        discrepancy_count=discrepancy_count,
        coordination_efficiency=coord_eff,
    )


def extract_critical_events(events: list[dict[str, Any]]) -> list[CriticalEvent]:
    """Filter events to only decision points and critical divergences."""
    timeline: list[CriticalEvent] = []

    for e in events:
        action = e.get("chosen_action", "")
        result = e.get("action_result", {})
        agent = e.get("agent_id", "")
        turn = e.get("turn_number", 0)
        disc = e.get("discrepancy_detected", False)
        disc_details = e.get("discrepancy_details")
        dm_query = e.get("dm_query")
        dm_advice = e.get("dm_advice")
        dm_stale = e.get("dm_stale_turns_count")

        # DM oracle query → always a critical event
        if dm_query:
            stale_label = f" ({dm_stale} turns stale)" if dm_stale and dm_stale > 0 else ""
            timeline.append(CriticalEvent(
                turn_number=turn,
                agent_id=agent,
                event_type="dm_oracle",
                severity="yellow" if dm_stale and dm_stale > 0 else "green",
                headline=f"{agent} asked DM: \"{dm_query}\"{stale_label}",
                details=f"DM advice: {dm_advice}",
                dm_query=dm_query,
                dm_advice=dm_advice,
                stale_turns=dm_stale,
            ))
            continue

        # Discrepancy detected → critical divergence
        if disc and disc_details:
            # Classify severity
            severity = "red"
            if "soft failure" in disc_details.lower():
                severity = "yellow"
            elif "partner" in disc_details.lower() and "expected" in disc_details.lower():
                severity = "yellow"

            headline = _build_headline(agent, action, disc_details, result)
            timeline.append(CriticalEvent(
                turn_number=turn,
                agent_id=agent,
                event_type="critical_divergence",
                severity=severity,
                headline=headline,
                details=disc_details,
            ))
            continue

        # Key pickup → decision point
        if action == "pick_up_item" and result.get("success"):
            timeline.append(CriticalEvent(
                turn_number=turn,
                agent_id=agent,
                event_type="decision_point",
                severity="green",
                headline=f"{agent} picked up the key",
                details=result.get("message"),
            ))
            continue

        # Door unlock → decision point
        if action == "unlock_door" and result.get("success"):
            timeline.append(CriticalEvent(
                turn_number=turn,
                agent_id=agent,
                event_type="decision_point",
                severity="green",
                headline=f"{agent} unlocked the door",
                details=result.get("message"),
            ))
            continue

        # Message sent → coordination event
        if action == "send_message" and result.get("success"):
            text = e.get("action_args", {}).get("text", "")
            timeline.append(CriticalEvent(
                turn_number=turn,
                agent_id=agent,
                event_type="coordination",
                severity="green",
                headline=f"{agent} messaged partner: \"{text[:60]}\"",
                details=text,
            ))
            continue

        # Failed action → always notable
        if not result.get("success", True):
            timeline.append(CriticalEvent(
                turn_number=turn,
                agent_id=agent,
                event_type="critical_divergence",
                severity="red",
                headline=f"{agent}'s {action} failed: {result.get('message', '')[:80]}",
                details=result.get("message"),
            ))

    return timeline


def build_diagnosis(events: list[dict[str, Any]], win: bool) -> DiagnosisSummary:
    """Produce a root-cause summary from events."""
    categories: dict[str, FailureCategory] = {}

    for e in events:
        disc = e.get("discrepancy_detected", False)
        disc_details = e.get("discrepancy_details", "") or ""
        turn = e.get("turn_number", 0)
        action = e.get("chosen_action", "")
        result = e.get("action_result", {})
        dm_stale = e.get("dm_stale_turns_count")

        if not disc and result.get("success", True):
            continue

        # Categorise
        if dm_stale and dm_stale > 0:
            cat = "dm_oracle"
            desc = "Agent acted on stale DM oracle advice"
        elif "soft failure" in disc_details.lower() or "wall" in disc_details.lower():
            cat = "stale_info"
            desc = "Agent hit an obstacle it didn't know about"
        elif "partner" in disc_details.lower():
            cat = "coordination"
            desc = "Agent had outdated information about partner's location"
        elif "key expected" in disc_details.lower():
            cat = "stale_info"
            desc = "Agent went to stale key location"
        elif not result.get("success", True):
            cat = "tool_failure"
            desc = "Action failed unexpectedly"
        else:
            cat = "stale_info"
            desc = "Belief contradicted reality"

        if cat not in categories:
            categories[cat] = FailureCategory(
                category=cat, count=0, description=desc, related_turns=[]
            )
        categories[cat].count += 1
        categories[cat].related_turns.append(turn)

    failure_list = sorted(categories.values(), key=lambda c: c.count, reverse=True)

    # Build root cause narrative
    if win:
        root_cause = "The agents succeeded despite encountering information decay issues."
    elif not failure_list:
        root_cause = "No significant failures detected — the run may have hit the turn limit."
    else:
        top = failure_list[0]
        total_disc = sum(c.count for c in failure_list)
        parts = []
        if top.category == "dm_oracle":
            parts.append(
                f"The primary failure mode was stale DM oracle advice ({top.count} events). "
                "Agents relied on the Dungeon Master's outdated world view, leading to "
                "wasted turns pursuing incorrect information."
            )
        elif top.category == "stale_info":
            parts.append(
                f"Agents frequently acted on outdated beliefs ({top.count} events). "
                "Fog-of-war combined with information decay caused agents to navigate "
                "toward positions that had already changed."
            )
        elif top.category == "coordination":
            parts.append(
                f"Coordination breakdown was the main issue ({top.count} events). "
                "Agents had stale knowledge of each other's positions due to "
                "limited visibility and message delay."
            )
        elif top.category == "tool_failure":
            parts.append(
                f"Multiple tool failures ({top.count} events) suggest agents attempted "
                "actions without sufficient information."
            )

        if len(failure_list) > 1:
            secondary = ", ".join(
                f"{c.category} ({c.count})" for c in failure_list[1:]
            )
            parts.append(f"Secondary issues: {secondary}.")

        parts.append(f"Total divergence events: {total_disc}.")
        root_cause = " ".join(parts)

    return DiagnosisSummary(root_cause=root_cause, failure_categories=failure_list)


def _build_headline(agent: str, action: str, details: str, result: dict) -> str:
    """Generate a concise headline for a critical event."""
    details_lower = details.lower()
    result_action = result.get("action", action)
    if "soft failure" in details_lower:
        direction = result_action.replace("move_", "") if "move" in result_action else action
        return f"{agent} hit a hidden wall moving {direction}"
    if "key expected" in details_lower:
        return f"{agent} went to key location but it was gone"
    if "partner" in details_lower and "expected" in details_lower:
        return f"{agent} had stale partner location info"
    if "dm oracle" in details_lower:
        return f"{agent} received stale advice from DM oracle"
    if not result.get("success", True):
        return f"{agent}'s {action} failed: {result.get('message', '')[:60]}"
    return f"{agent} encountered discrepancy: {details[:80]}"
