"""Tests for discrepancy detection and belief model."""

from src.agents.belief import BeliefModel, update_belief
from src.instrumentation.discrepancy import detect_discrepancies


# ── Helpers ──────────────────────────────────────────────────────────────────


def _obs(
    pos=(2, 2),
    current_cell="empty",
    adjacent=None,
    entities=None,
    has_key=False,
    turn=0,
    messages=None,
):
    """Build a minimal observation dict."""
    return {
        "agent_position": list(pos),
        "current_cell": current_cell,
        "adjacent_cells": adjacent or {"north": "empty", "south": "empty", "east": "empty", "west": "empty"},
        "visible_entities": entities or [],
        "has_key": has_key,
        "turn_number": turn,
        "messages_received": messages or [],
    }


def _result(success=True, action="move_south", message="Moved south.", game_over=False):
    return {
        "success": success,
        "action": action,
        "new_position": [3, 2],
        "message": message,
        "game_over": game_over,
        "win": False,
    }


# ── BeliefModel tests ───────────────────────────────────────────────────────


class TestBeliefModel:
    def test_initial_snapshot_empty(self):
        b = BeliefModel()
        snap = b.snapshot()
        assert snap["grid_knowledge"] == {}
        assert snap["key_location"] is None
        assert snap["has_key"] is False

    def test_update_records_cells(self):
        b = BeliefModel()
        obs = _obs(pos=(2, 2), adjacent={"north": "wall", "south": "key", "east": "empty", "west": "wall"})
        update_belief(b, obs)
        assert b.grid_knowledge["2,2"] == "empty"
        assert b.grid_knowledge["1,2"] == "wall"
        assert b.grid_knowledge["3,2"] == "key"

    def test_update_detects_key_location(self):
        b = BeliefModel()
        obs = _obs(pos=(2, 2), adjacent={"north": "empty", "south": "key", "east": "empty", "west": "empty"})
        update_belief(b, obs)
        assert b.key_location == [3, 2]

    def test_update_clears_key_when_gone(self):
        b = BeliefModel()
        b.key_location = [3, 2]
        b.grid_knowledge["3,2"] = "key"
        # Now observe that cell and it's empty
        obs = _obs(pos=(2, 2), adjacent={"north": "empty", "south": "empty", "east": "empty", "west": "empty"})
        update_belief(b, obs)
        assert b.key_location is None

    def test_update_partner_location(self):
        b = BeliefModel()
        obs = _obs(entities=[{"type": "agent", "id": "agent_b", "position": [2, 3]}])
        update_belief(b, obs)
        assert b.partner_location == [2, 3]

    def test_update_door_location(self):
        b = BeliefModel()
        obs = _obs(adjacent={"north": "empty", "south": "locked_door", "east": "empty", "west": "empty"})
        update_belief(b, obs)
        assert b.door_location == [3, 2]

    def test_update_exit_location(self):
        b = BeliefModel()
        obs = _obs(adjacent={"north": "empty", "south": "exit", "east": "empty", "west": "empty"})
        update_belief(b, obs)
        assert b.exit_location == [3, 2]

    def test_partner_has_key_from_message(self):
        b = BeliefModel()
        obs = _obs(messages=[{"from": "agent_b", "text": "I have the key!", "sent_turn": 0}])
        update_belief(b, obs)
        assert b.partner_has_key is True

    def test_snapshot_is_deep_copy(self):
        b = BeliefModel()
        b.grid_knowledge["1,1"] = "wall"
        snap = b.snapshot()
        snap["grid_knowledge"]["1,1"] = "empty"
        assert b.grid_knowledge["1,1"] == "wall"


# ── Discrepancy detection tests ──────────────────────────────────────────────


class TestDiscrepancy:
    def test_no_discrepancy_on_matching_belief(self):
        belief = {
            "grid_knowledge": {"1,2": "wall", "3,2": "empty", "2,3": "empty", "2,1": "empty"},
            "key_location": None,
            "partner_location": None,
        }
        obs = _obs(adjacent={"north": "wall", "south": "empty", "east": "empty", "west": "empty"})
        detected, details, diff = detect_discrepancies(belief, obs, _result())
        assert detected is False

    def test_adjacent_cell_contradiction(self):
        belief = {
            "grid_knowledge": {"1,2": "empty"},  # believed empty
            "key_location": None,
            "partner_location": None,
        }
        obs = _obs(adjacent={"north": "wall", "south": "empty", "east": "empty", "west": "empty"})
        detected, details, diff = detect_discrepancies(belief, obs, _result())
        assert detected is True
        assert "believed=empty, actual=wall" in details

    def test_soft_failure_no_movement(self):
        belief = {"grid_knowledge": {}, "key_location": None, "partner_location": None}
        obs = _obs()
        result = _result(success=True, action="move_south", message="No Movement — blocked by a wall.")
        detected, details, _ = detect_discrepancies(belief, obs, result)
        assert detected is True
        assert "soft failure" in details.lower()

    def test_stale_key_location(self):
        belief = {
            "grid_knowledge": {},
            "key_location": [3, 2],
            "partner_location": None,
        }
        obs = _obs(adjacent={"north": "empty", "south": "empty", "east": "empty", "west": "empty"})
        detected, details, diff = detect_discrepancies(belief, obs, _result())
        assert detected is True
        assert "key expected" in details.lower()

    def test_partner_drift(self):
        belief = {
            "grid_knowledge": {},
            "key_location": None,
            "partner_location": [2, 1],
        }
        obs = _obs(entities=[{"type": "agent", "id": "agent_b", "position": [2, 3]}])
        detected, details, diff = detect_discrepancies(belief, obs, _result())
        assert detected is True
        assert "partner" in details.lower()

    def test_action_failure_discrepancy(self):
        belief = {"grid_knowledge": {}, "key_location": None, "partner_location": None}
        obs = _obs()
        result = _result(success=False, action="pick_up_item", message="No item here.")
        detected, details, _ = detect_discrepancies(belief, obs, result)
        assert detected is True
        assert "failed unexpectedly" in details.lower()

    def test_empty_belief_no_crash(self):
        """Discrepancy detection works even with a completely empty belief."""
        belief = {}
        obs = _obs()
        detected, details, diff = detect_discrepancies(belief, obs, _result())
        assert detected is False


# ── DM Oracle discrepancy tests ──────────────────────────────────────────────


class TestDMOracleDiscrepancy:
    def test_stale_dm_advice_flagged(self):
        belief = {"grid_knowledge": {}, "key_location": None, "partner_location": None}
        obs = _obs()
        result = {
            **_result(),
            "action": "query_dm",
            "stale_turns_count": 3,
            "advice": "The key is at (2,2).",
        }
        detected, details, diff = detect_discrepancies(belief, obs, result)
        assert detected is True
        assert "stale" in details.lower()
        assert "3" in details

    def test_fresh_dm_advice_not_flagged(self):
        belief = {"grid_knowledge": {}, "key_location": None, "partner_location": None}
        obs = _obs()
        result = {
            **_result(),
            "action": "query_dm",
            "stale_turns_count": 0,
            "advice": "The key is at (2,2).",
        }
        detected, details, diff = detect_discrepancies(belief, obs, result)
        assert detected is False

    def test_dm_stale_advice_diff_contains_info(self):
        belief = {"grid_knowledge": {}, "key_location": None, "partner_location": None}
        obs = _obs()
        result = {
            **_result(),
            "stale_turns_count": 2,
            "advice": "Partner at (1,1).",
        }
        detected, _, diff = detect_discrepancies(belief, obs, result)
        assert detected is True
        assert any(d.get("op") == "info" and d.get("path") == "/dm_oracle" for d in diff)


# ── Message correlation tests ────────────────────────────────────────────────


class TestMessageCorrelation:
    def test_pending_message_has_correlation_id(self):
        from src.simulation.state import PendingMessage
        msg = PendingMessage(from_agent="a", to_agent="b", text="hi", sent_turn=0)
        assert msg.correlation_id is not None
        assert len(msg.correlation_id) == 8

    def test_send_message_returns_correlation_ids(self):
        from src.simulation.dungeon_master import execute_action
        from src.simulation.state import DungeonState, AgentState
        state = DungeonState(
            grid=[["wall", "wall", "wall"], ["wall", "empty", "wall"], ["wall", "wall", "wall"]],
            grid_width=3, grid_height=3,
            agents={
                "agent_a": AgentState(agent_id="agent_a", position=(1, 1)),
                "agent_b": AgentState(agent_id="agent_b", position=(1, 1)),
            },
        )
        result = execute_action(state, "agent_a", "send_message", {"text": "hello"})
        assert result["success"] is True
        assert "correlation_ids" in result
        assert len(result["correlation_ids"]) == 1
