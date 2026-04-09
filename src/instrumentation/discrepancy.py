"""Discrepancy detection: compare belief-before against observation & result.

A discrepancy is flagged whenever the agent's internal belief contradicts
what the Dungeon Master actually reports — stale key locations, unexpected
walls, partner position drift, etc.
"""

from __future__ import annotations

from typing import Any

from src.simulation.items import DIRECTIONS


def detect_discrepancies(
    belief_before: dict[str, Any],
    observation: dict[str, Any],
    action_result: dict[str, Any],
) -> tuple[bool, str | None, list[dict[str, Any]] | None]:
    """Compare *belief_before* against the new *observation* and *action_result*.

    Returns (detected, details_string, json_patch_diff).
    """
    discrepancies: list[str] = []
    diff: list[dict[str, Any]] = []
    grid_knowledge: dict[str, str] = belief_before.get("grid_knowledge", {})
    pos = observation["agent_position"]

    # ── 1. Check adjacent cells against grid_knowledge ───────────────────
    for direction, actual_content in observation["adjacent_cells"].items():
        delta = DIRECTIONS.get(direction)
        if delta is None:
            continue
        nr, nc = pos[0] + delta[0], pos[1] + delta[1]
        cell_key = f"{nr},{nc}"
        believed = grid_knowledge.get(cell_key)
        if believed is not None and believed != actual_content:
            discrepancies.append(
                f"Cell ({nr},{nc}): believed={believed}, actual={actual_content}"
            )
            diff.append({
                "op": "replace",
                "path": f"/grid_knowledge/{cell_key}",
                "from": believed,
                "to": actual_content,
            })

    # ── 2. Action failed → agent expected to succeed (soft failure) ──────
    if not action_result.get("success", True):
        action = action_result.get("action", "")
        msg = action_result.get("message", "")
        # A move that returned success=False means the agent didn't know
        # about the obstacle.
        discrepancies.append(f"Action '{action}' failed unexpectedly: {msg}")

    # ── 3. Soft failure: success but no movement ─────────────────────────
    if action_result.get("success") and action_result.get("action", "").startswith("move_"):
        # If the result says "no movement" despite success, it's a soft wall hit.
        result_msg = action_result.get("message", "").lower()
        if "no movement" in result_msg:
            direction = action_result["action"].replace("move_", "")
            discrepancies.append(
                f"Soft failure: moved {direction} but stayed at same position (hidden obstacle)"
            )

    # ── 4. Key location consistency ──────────────────────────────────────
    believed_key = belief_before.get("key_location")
    if believed_key is not None:
        bk_key = f"{believed_key[0]},{believed_key[1]}"
        # If the believed key cell is now visible and doesn't have the key…
        for direction, actual_content in observation["adjacent_cells"].items():
            delta = DIRECTIONS[direction]
            nr, nc = pos[0] + delta[0], pos[1] + delta[1]
            if [nr, nc] == believed_key and actual_content != "key":
                discrepancies.append(
                    f"Key expected at ({nr},{nc}) but found '{actual_content}' — stale belief"
                )
                diff.append({
                    "op": "replace",
                    "path": "/key_location",
                    "from": believed_key,
                    "to": None,
                })
                break
        # Also check current cell.
        if list(pos) == believed_key and observation["current_cell"] != "key":
            if not any("key_location" in d.get("path", "") for d in diff):
                discrepancies.append(
                    f"Key expected at ({pos[0]},{pos[1]}) but cell is '{observation['current_cell']}'"
                )
                diff.append({
                    "op": "replace",
                    "path": "/key_location",
                    "from": believed_key,
                    "to": None,
                })

    # ── 5. Partner location drift ────────────────────────────────────────
    believed_partner = belief_before.get("partner_location")
    if believed_partner is not None:
        # If we now see the partner at a different position, it's a drift.
        for entity in observation.get("visible_entities", []):
            if entity["type"] == "agent":
                actual_partner = entity["position"]
                if actual_partner != believed_partner:
                    discrepancies.append(
                        f"Partner expected at ({believed_partner[0]},{believed_partner[1]}) "
                        f"but seen at ({actual_partner[0]},{actual_partner[1]})"
                    )
                    diff.append({
                        "op": "replace",
                        "path": "/partner_location",
                        "from": believed_partner,
                        "to": actual_partner,
                    })

    # ── 6. DM oracle stale advice ──────────────────────────────────────
    dm_stale = action_result.get("stale_turns_count")
    dm_advice = action_result.get("advice")
    if dm_stale is not None and dm_stale > 0 and dm_advice:
        discrepancies.append(
            f"DM oracle advice is {dm_stale} turns stale: \"{dm_advice[:100]}\""
        )
        diff.append({
            "op": "info",
            "path": "/dm_oracle",
            "stale_turns_count": dm_stale,
            "advice": dm_advice,
        })

    detected = len(discrepancies) > 0
    details = "; ".join(discrepancies) if detected else None
    return detected, details, diff if diff else None
