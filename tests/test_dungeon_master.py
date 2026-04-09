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

    def test_move_into_wall_fails(self):
        state = _make_simple_dungeon()
        result = execute_action(state, "agent_a", "move", {"direction": "west"})
        assert result["success"] is False
        assert state.agents["agent_a"].position == (1, 1)  # didn't move

    def test_move_into_locked_door_fails(self):
        state = _make_simple_dungeon()
        state.agents["agent_a"].position = (2, 2)
        result = execute_action(state, "agent_a", "move", {"direction": "south"})
        assert result["success"] is False
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


class TestRender:
    def test_render_grid_contains_agents(self):
        state = _make_simple_dungeon()
        output = render_grid(state)
        assert "Aa" in output  # agent_a marker
        assert "Ab" in output  # agent_b marker
