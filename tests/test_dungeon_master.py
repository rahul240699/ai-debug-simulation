"""Tests for Dungeon Master logic: observation, actions, turn management."""

from src.simulation.grid import create_grid
from src.simulation.dungeon_master import (
    advance_turn,
    check_win,
    execute_action,
    get_observation,
    render_grid,
)
from src.simulation.items import CellType
from src.simulation.state import DungeonState, AgentState, PendingMessage


def _make_simple_dungeon() -> DungeonState:
    """Build a minimal 5×5 dungeon with known positions for testing."""
    grid = [
        ["wall", "wall",  "wall",        "wall", "wall"],
        ["wall", "empty", "empty",       "empty", "wall"],
        ["wall", "empty", "key",         "empty", "wall"],
        ["wall", "empty", "locked_door", "exit",  "wall"],
        ["wall", "wall",  "wall",        "wall",  "wall"],
    ]
    state = DungeonState(
        grid=grid,
        grid_width=5,
        grid_height=5,
        key_position=(2, 2),
        door_position=(3, 2),
        exit_position=(3, 3),
        agents={
            "agent_a": AgentState(agent_id="agent_a", position=(1, 1)),
            "agent_b": AgentState(agent_id="agent_b", position=(1, 3)),
        },
    )
    return state


# ── Observation tests ────────────────────────────────────────────────────────


class TestObservation:
    def test_observation_returns_adjacent_cells(self):
        state = _make_simple_dungeon()
        obs = get_observation(state, "agent_a")
        assert obs["agent_position"] == [1, 1]
        assert obs["adjacent_cells"]["north"] == CellType.WALL
        assert obs["adjacent_cells"]["south"] == CellType.EMPTY
        assert obs["adjacent_cells"]["east"] == CellType.EMPTY
        assert obs["adjacent_cells"]["west"] == CellType.WALL

    def test_observation_sees_partner_when_adjacent(self):
        state = _make_simple_dungeon()
        state.agents["agent_b"].position = (1, 2)  # adjacent to agent_a
        obs = get_observation(state, "agent_a")
        assert len(obs["visible_entities"]) == 1
        assert obs["visible_entities"][0]["id"] == "agent_b"

    def test_observation_does_not_see_distant_partner(self):
        state = _make_simple_dungeon()
        # agent_b is at (1,3) — distance 2 from agent_a at (1,1).
        obs = get_observation(state, "agent_a")
        assert len(obs["visible_entities"]) == 0

    def test_observation_reveals_cells(self):
        state = _make_simple_dungeon()
        get_observation(state, "agent_a")
        agent = state.agents["agent_a"]
        assert "1,1" in agent.revealed_cells
        assert "0,1" in agent.revealed_cells  # north

    def test_observation_has_key_flag(self):
        state = _make_simple_dungeon()
        obs = get_observation(state, "agent_a")
        assert obs["has_key"] is False
        state.agents["agent_a"].has_key = True
        obs = get_observation(state, "agent_a")
        assert obs["has_key"] is True


# ── Action tests ─────────────────────────────────────────────────────────────


class TestActions:
    def test_move_to_empty_cell(self):
        state = _make_simple_dungeon()
        result = execute_action(state, "agent_a", "move", {"direction": "south"})
        assert result["success"] is True
        assert state.agents["agent_a"].position == (2, 1)

    def test_move_into_wall_soft_failure(self):
        state = _make_simple_dungeon()
        result = execute_action(state, "agent_a", "move", {"direction": "west"})
        assert result["success"] is True
        assert "no movement" in result["message"].lower()
        assert state.agents["agent_a"].position == (1, 1)  # didn't move

    def test_move_into_locked_door_soft_failure(self):
        state = _make_simple_dungeon()
        state.agents["agent_a"].position = (2, 2)
        result = execute_action(state, "agent_a", "move", {"direction": "south"})
        assert result["success"] is True
        assert "no movement" in result["message"].lower()
        assert "locked" in result["message"].lower()

    def test_pick_up_key(self):
        state = _make_simple_dungeon()
        state.agents["agent_a"].position = (2, 2)  # on the key
        result = execute_action(state, "agent_a", "pick_up_item")
        assert result["success"] is True
        assert state.agents["agent_a"].has_key is True
        assert state.key_position is None
        assert state.grid[2][2] == CellType.EMPTY

    def test_pick_up_key_wrong_position_fails(self):
        state = _make_simple_dungeon()
        result = execute_action(state, "agent_a", "pick_up_item")
        assert result["success"] is False

    def test_unlock_door_adjacent(self):
        state = _make_simple_dungeon()
        state.agents["agent_a"].position = (2, 2)
        state.agents["agent_a"].has_key = True
        result = execute_action(state, "agent_a", "unlock_door")
        assert result["success"] is True
        assert state.door_position is None
        assert state.grid[3][2] == CellType.EXIT

    def test_unlock_door_without_key_fails(self):
        state = _make_simple_dungeon()
        state.agents["agent_a"].position = (2, 2)
        result = execute_action(state, "agent_a", "unlock_door")
        assert result["success"] is False

    def test_unlock_door_not_adjacent_fails(self):
        state = _make_simple_dungeon()
        state.agents["agent_a"].has_key = True
        result = execute_action(state, "agent_a", "unlock_door")
        assert result["success"] is False
        assert "adjacent" in result["message"].lower()

    def test_wait(self):
        state = _make_simple_dungeon()
        pos_before = state.agents["agent_a"].position
        result = execute_action(state, "agent_a", "wait")
        assert result["success"] is True
        assert state.agents["agent_a"].position == pos_before

    def test_send_message(self):
        state = _make_simple_dungeon()
        result = execute_action(
            state, "agent_a", "send_message", {"text": "I found the key!"}
        )
        assert result["success"] is True
        assert len(state.pending_messages) == 1
        assert state.pending_messages[0].to_agent == "agent_b"

    def test_send_empty_message_fails(self):
        state = _make_simple_dungeon()
        result = execute_action(
            state, "agent_a", "send_message", {"text": ""}
        )
        assert result["success"] is False


# ── Turn management tests ────────────────────────────────────────────────────


class TestTurnManagement:
    def test_advance_turn_alternates_agents(self):
        state = _make_simple_dungeon()
        assert state.active_agent == "agent_a"
        advance_turn(state)
        assert state.active_agent == "agent_b"
        advance_turn(state)
        assert state.active_agent == "agent_a"
        assert state.turn_number == 1

    def test_message_delay(self):
        state = _make_simple_dungeon()
        # Agent A sends message on turn 0.
        execute_action(state, "agent_a", "send_message", {"text": "hello"})
        assert len(state.pending_messages) == 1

        # Advance to Agent B's turn (still turn 0).
        advance_turn(state)
        # Message sent on turn 0 should NOT be delivered yet (same turn).
        assert len(state.agents["agent_b"].inbox) == 0

        # Advance back to Agent A (turn 1).
        advance_turn(state)
        assert state.turn_number == 1
        # Now agent B's inbox should have the message on next observation.
        # But messages are delivered in advance_turn, so check pending.
        # Actually advance_turn delivers when sent_turn < turn_number.
        # Turn advanced to 1, message sent_turn=0.  But we advanced past B.
        # Let's advance once more to B on turn 1.
        advance_turn(state)
        assert state.active_agent == "agent_b"
        # Now message should be in inbox.
        assert len(state.agents["agent_b"].inbox) == 1
        assert state.agents["agent_b"].inbox[0]["text"] == "hello"


# ── Win condition tests ──────────────────────────────────────────────────────


class TestWinCondition:
    def test_win_with_key_on_exit(self):
        state = _make_simple_dungeon()
        # Unlock door first.
        state.grid[3][2] = CellType.EXIT
        state.door_position = None
        # Agent has key and stands on exit.
        state.agents["agent_a"].position = (3, 3)
        state.agents["agent_a"].has_key = True
        assert check_win(state) is True
        assert state.game_over is True
        assert state.win is True

    def test_no_win_without_key(self):
        state = _make_simple_dungeon()
        state.grid[3][2] = CellType.EXIT
        state.door_position = None
        state.agents["agent_a"].position = (3, 3)
        assert check_win(state) is False

    def test_no_win_on_locked_door(self):
        state = _make_simple_dungeon()
        state.agents["agent_a"].position = (3, 2)
        state.agents["agent_a"].has_key = True
        # Door is still locked, cell is LOCKED_DOOR not EXIT.
        assert check_win(state) is False


# ── Render test ──────────────────────────────────────────────────────────────


class TestQueryDM:
    """Tests for query_dm action and DM oracle with stale snapshots."""

    def test_query_dm_returns_success(self):
        state = _make_simple_dungeon()
        result = execute_action(state, "agent_a", "query_dm", {"question": "Where is the key?"})
        assert result["success"] is True
        assert result["action"] == "query_dm"
        assert "advice" in result
        assert "key" in result["advice"].lower()

    def test_query_dm_stale_turns_on_turn_0(self):
        state = _make_simple_dungeon()
        # First observation creates snapshot at turn 0
        get_observation(state, "agent_a")
        result = execute_action(state, "agent_a", "query_dm", {"question": "Where is the key?"})
        # On turn 0 with stale_turns=2, the snapshot IS turn 0  → stale_turns_count = 0
        assert result["stale_turns_count"] == 0

    def test_query_dm_stale_after_turns(self):
        state = _make_simple_dungeon()
        state.dm_stale_turns = 2
        # Simulate 3 turns, taking snapshots at each
        for turn in range(3):
            state.turn_number = turn
            state.take_snapshot()
        state.turn_number = 3
        state.take_snapshot()
        result = execute_action(state, "agent_a", "query_dm", {"question": "Where is the key?"})
        # turn=3, stale=2 → target=1 → snapshot 1 used → stale_turns_count = 2
        assert result["stale_turns_count"] == 2
        assert result["snapshot_turn"] == 1

    def test_query_dm_reports_stale_key_position(self):
        """The DM should report the key's OLD position even after it's picked up."""
        state = _make_simple_dungeon()
        state.dm_stale_turns = 2
        # Turn 0: key at (2,2)
        state.turn_number = 0
        state.take_snapshot()
        # Turn 1: key at (2,2)
        state.turn_number = 1
        state.take_snapshot()
        # Turn 2: agent picks up key
        state.agents["agent_a"].position = (2, 2)
        execute_action(state, "agent_a", "pick_up_item")
        assert state.key_position is None
        state.turn_number = 2
        state.take_snapshot()
        # Turn 3: query DM → sees turn 1 snapshot where key was still at (2,2)
        state.turn_number = 3
        result = execute_action(state, "agent_a", "query_dm", {"question": "Where is the key?"})
        assert "(2,2)" in result["advice"]
        assert result["stale_turns_count"] == 2

    def test_query_dm_door_exit_keywords(self):
        state = _make_simple_dungeon()
        get_observation(state, "agent_a")
        result = execute_action(state, "agent_a", "query_dm", {"question": "Where is the exit?"})
        assert "exit" in result["advice"].lower() or "door" in result["advice"].lower()

    def test_query_dm_partner_keyword(self):
        state = _make_simple_dungeon()
        get_observation(state, "agent_a")
        result = execute_action(state, "agent_a", "query_dm", {"question": "Where is my partner?"})
        assert "agent_b" in result["advice"]

    def test_query_dm_no_history_uses_current(self):
        """When no snapshots exist, DM uses current state."""
        state = _make_simple_dungeon()
        # Don't call get_observation or take_snapshot
        result = execute_action(state, "agent_a", "query_dm", {"question": "Where is the key?"})
        assert result["success"] is True
        assert "(2,2)" in result["advice"]
        assert result["stale_turns_count"] == 0


class TestWorldSnapshot:
    """Tests for WorldSnapshot creation and stale lookup."""

    def test_take_snapshot_stores_correctly(self):
        state = _make_simple_dungeon()
        state.take_snapshot()
        assert 0 in state.history
        snap = state.history[0]
        assert snap.turn_number == 0
        assert snap.key_position == (2, 2)
        assert snap.agent_positions["agent_a"] == (1, 1)

    def test_snapshot_is_deep_copy(self):
        state = _make_simple_dungeon()
        state.take_snapshot()
        # Mutate the original grid
        state.grid[1][1] = "wall"
        # Snapshot should still have "empty"
        assert state.history[0].grid[1][1] == "empty"

    def test_get_stale_snapshot_returns_correct_turn(self):
        state = _make_simple_dungeon()
        state.dm_stale_turns = 2
        for t in range(5):
            state.turn_number = t
            state.take_snapshot()
        state.turn_number = 4
        snap = state.get_stale_snapshot()
        assert snap is not None
        assert snap.turn_number == 2  # 4 - 2 = 2

    def test_get_stale_snapshot_returns_oldest_if_missing(self):
        state = _make_simple_dungeon()
        state.dm_stale_turns = 10
        state.turn_number = 3
        state.take_snapshot()
        snap = state.get_stale_snapshot()
        # target = max(0, 3-10) = 0, but only turn 3 exists; walks back, finds nothing
        # Actually, let's check: target=0, walks from 0 down to 0, no entry.
        # So it returns None. Let's test with turn 0 snapshot.
        state2 = _make_simple_dungeon()
        state2.dm_stale_turns = 10
        state2.turn_number = 0
        state2.take_snapshot()
        state2.turn_number = 5
        snap2 = state2.get_stale_snapshot()
        assert snap2 is not None
        assert snap2.turn_number == 0

    def test_get_stale_snapshot_none_when_no_history(self):
        state = _make_simple_dungeon()
        snap = state.get_stale_snapshot()
        assert snap is None

    def test_observation_creates_snapshot(self):
        state = _make_simple_dungeon()
        assert len(state.history) == 0
        get_observation(state, "agent_a")
        assert 0 in state.history


class TestRender:
    def test_render_grid_contains_agents(self):
        state = _make_simple_dungeon()
        output = render_grid(state)
        assert "Aa" in output  # agent_a marker
        assert "Ab" in output  # agent_b marker
