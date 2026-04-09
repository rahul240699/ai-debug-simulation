"""Helpers to build structured Langfuse traces and spans.

Wraps the Langfuse SDK so the rest of the codebase only deals with plain
dicts and dataclasses.  When Langfuse is not configured, every public
function is a silent no-op.

Targets **Langfuse SDK v4.x** which uses ``start_observation()`` and
``TraceContext`` instead of the legacy ``trace()`` / ``span()`` helpers.
"""

from __future__ import annotations

import logging
from typing import Any

from src.instrumentation.event_schema import EventRecord
from src.instrumentation.langfuse_client import get_langfuse

logger = logging.getLogger(__name__)


# ── Trace (per-run) ──────────────────────────────────────────────────────────

_active_trace_ids: dict[str, str] = {}   # run_id → langfuse trace_id
_active_metadata: dict[str, dict[str, Any]] = {}  # run_id → metadata


def _trace_context(run_id: str) -> dict[str, str] | None:
    """Build a TraceContext dict for *run_id*, or None if not tracked."""
    tid = _active_trace_ids.get(run_id)
    if tid is None:
        return None
    return {"trace_id": tid}


def start_trace(
    run_id: str,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> str | None:
    """Register a new trace for a simulation run.

    In Langfuse v4 there is no ``lf.trace()`` call.  Instead we store
    the trace_id and pass it as ``trace_context`` to every observation.
    A root span is created to represent the overall simulation.
    """
    lf = get_langfuse()
    if lf is None:
        return None

    trace_id = run_id  # use the simulation run_id as the trace ID

    _active_trace_ids[run_id] = trace_id
    _active_metadata[run_id] = metadata or {}

    # Create a root "agent" span that groups the whole simulation.
    try:
        root = lf.start_observation(
            trace_context={"trace_id": trace_id},
            name="dungeon_simulation",
            as_type="agent",
            input=metadata or {},
            metadata={
                "tags": tags or ["dungeon", "multi-agent", "observability-demo"],
            },
        )
        root.end()
    except Exception:
        logger.warning("Failed to create root Langfuse span", exc_info=True)

    logger.debug("Langfuse trace started: %s", trace_id)
    return trace_id


def end_trace(run_id: str) -> None:
    """Flush pending events and clean up for *run_id*."""
    _active_trace_ids.pop(run_id, None)
    _active_metadata.pop(run_id, None)
    from src.instrumentation.langfuse_client import flush
    flush()
    logger.debug("Langfuse trace ended: %s", run_id)


# ── Span (per-turn) ─────────────────────────────────────────────────────────


def record_turn_span(run_id: str, event: EventRecord) -> None:
    """Emit a Langfuse span for a single agent turn with full EventRecord."""
    lf = get_langfuse()
    ctx = _trace_context(run_id)
    if lf is None or ctx is None:
        return

    span_name = f"turn_{event.turn_number:03d}_{event.agent_id}"

    input_payload = {
        "observed_state": event.observed_state,
        "belief_before": event.belief_before,
    }
    output_payload = {
        "rationale": event.rationale,
        "chosen_action": event.chosen_action,
        "action_args": event.action_args,
        "action_result": event.action_result,
        "belief_after": event.belief_after,
        "discrepancy_detected": event.discrepancy_detected,
        "discrepancy_details": event.discrepancy_details,
        "belief_diff": event.belief_diff,
        "dm_query": event.dm_query,
        "dm_advice": event.dm_advice,
        "stale_turns_count": event.dm_stale_turns_count,
    }

    metadata = {
        "turn_number": event.turn_number,
        "agent_id": event.agent_id,
        "discrepancy_detected": event.discrepancy_detected,
        "message_correlation_ids": event.message_correlation_ids,
        "dm_query": event.dm_query,
        "dm_advice": event.dm_advice,
        "stale_turns_count": event.dm_stale_turns_count,
    }

    level = "WARNING" if event.discrepancy_detected else "DEFAULT"

    try:
        span = lf.start_observation(
            trace_context=ctx,
            name=span_name,
            as_type="span",
            input=input_payload,
            output=output_payload,
            metadata=metadata,
            level=level,
            status_message="discrepancy_detected" if event.discrepancy_detected else "ok",
        )
        span.end()
    except Exception:
        logger.warning("Failed to record Langfuse span for %s", span_name, exc_info=True)


def record_generation(
    run_id: str,
    turn_number: int,
    agent_id: str,
    model: str,
    messages_in: list[dict[str, str]],
    response_text: str,
    usage: dict[str, int] | None = None,
) -> None:
    """Record the LLM generation as a Langfuse generation observation."""
    lf = get_langfuse()
    ctx = _trace_context(run_id)
    if lf is None or ctx is None:
        return

    gen_name = f"gen_turn{turn_number}_{agent_id}"
    try:
        gen = lf.start_observation(
            trace_context=ctx,
            name=gen_name,
            as_type="generation",
            model=model,
            input=messages_in,
            output=response_text,
            usage_details=usage or {},
            metadata={"turn_number": turn_number, "agent_id": agent_id},
        )
        gen.end()
    except Exception:
        logger.warning("Failed to record Langfuse generation %s", gen_name, exc_info=True)
