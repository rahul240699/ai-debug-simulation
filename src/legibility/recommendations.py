"""Prescriptive insight generation from run diagnosis data.

Uses an LLM-as-judge to analyze the run's metrics, failure categories,
and event patterns, then produces actionable optimisation recommendations.
Falls back to a lightweight heuristic summary if the LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert AI-systems diagnostician reviewing a multi-agent dungeon \
simulation run. Two LLM-powered agents navigate a grid to find a key and \
reach an exit. A Dungeon Master (DM) oracle answers questions but may \
return stale data.

Given the run's metrics, failure breakdown, and event-level statistics, \
produce exactly 3-4 prescriptive recommendations to improve system \
performance. Each recommendation must be grounded in the data provided — \
reference specific numbers.

Categorise each recommendation into one of:
  prompt_engineering, tooling, architecture, dm_config, exploration, efficiency

Respond ONLY with a JSON array. Each element must have exactly these keys:
  "category" (string), "icon" (single emoji), "title" (≤12 words), "detail" (2-3 sentences, specific and actionable)

No markdown, no explanation outside the JSON array.\
"""


def _build_user_prompt(
    metrics: dict[str, Any],
    failure_categories: list[dict[str, Any]],
    event_stats: dict[str, Any],
    win: bool,
    total_turns: int,
    dm_stale_turns: int,
) -> str:
    return json.dumps({
        "outcome": "WIN" if win else "LOSS",
        "total_turns": total_turns,
        "dm_stale_turns_config": dm_stale_turns,
        "metrics": {
            "avg_information_lag": metrics.get("avg_information_lag", 0),
            "discrepancy_count": metrics.get("discrepancy_count", 0),
            "coordination_efficiency": metrics.get("coordination_efficiency"),
        },
        "failure_categories": [
            {"category": fc["category"], "count": fc["count"], "description": fc["description"]}
            for fc in failure_categories
        ],
        "event_stats": event_stats,
    }, indent=2)


def _compute_event_stats(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Distill event-level patterns into compact stats for the LLM."""
    return {
        "wall_hits": sum(
            1 for e in events
            if e.get("discrepancy_detected")
            and "wall" in (e.get("discrepancy_details") or "").lower()
        ),
        "stale_dm_queries": sum(
            1 for e in events
            if (e.get("dm_stale_turns_count") or 0) > 0
        ),
        "failed_pickups": sum(
            1 for e in events
            if e.get("chosen_action") == "pick_up_item"
            and not e.get("action_result", {}).get("success", True)
        ),
        "messages_sent": sum(
            1 for e in events
            if e.get("chosen_action") == "send_message"
            and e.get("action_result", {}).get("success", True)
        ),
        "partner_location_stale": sum(
            1 for e in events
            if e.get("discrepancy_detected")
            and "partner" in (e.get("discrepancy_details") or "").lower()
        ),
        "total_events": len(events),
    }


def generate_recommendations(
    metrics: dict[str, Any],
    failure_categories: list[dict[str, Any]],
    events: list[dict[str, Any]],
    win: bool,
    total_turns: int,
    dm_stale_turns: int,
) -> list[dict[str, str]]:
    """Return 3-4 prioritised recommendations from an LLM judge."""
    event_stats = _compute_event_stats(events)

    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning empty recommendations")
        return []

    user_msg = _build_user_prompt(
        metrics, failure_categories, event_stats, win, total_turns, dm_stale_turns,
    )

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.4,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
        )
        raw = resp.choices[0].message.content or "[]"
        # Strip markdown fences if the model wraps output
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        recs = json.loads(raw)
        if not isinstance(recs, list):
            raise ValueError("LLM returned non-list JSON")

        # Validate shape
        valid: list[dict[str, str]] = []
        for r in recs[:4]:
            if all(k in r for k in ("category", "icon", "title", "detail")):
                valid.append({
                    "category": str(r["category"]),
                    "icon": str(r["icon"]),
                    "title": str(r["title"]),
                    "detail": str(r["detail"]),
                })
        return valid

    except Exception:
        logger.exception("LLM recommendation generation failed")
        return []
