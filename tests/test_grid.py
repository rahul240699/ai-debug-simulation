"""Tests for grid creation and spatial utilities."""

from src.simulation.grid import create_grid, is_in_bounds, neighbor_position
from src.simulation.items import CellType


def test_create_grid_dimensions():
    state = create_grid(width=8, height=8, seed=42)
    assert state.grid_width == 8
    assert state.grid_height == 8
    assert len(state.grid) == 8
    assert all(len(row) == 8 for row in state.grid)


def test_create_grid_has_required_items():
    state = create_grid(seed=42)
    # Before pickup, key should exist on grid.
    assert state.key_position is not None
    r, c = state.key_position
    assert state.grid[r][c] == CellType.KEY

    # Door should exist.
    assert state.door_position is not None
    r, c = state.door_position
    assert state.grid[r][c] == CellType.LOCKED_DOOR

    # Exit should exist.
    assert state.exit_position is not None
    r, c = state.exit_position
    assert state.grid[r][c] == CellType.EXIT


def test_create_grid_agents_placed():
    state = create_grid(seed=42)
    assert "agent_a" in state.agents
    assert "agent_b" in state.agents
    a = state.agents["agent_a"]
    b = state.agents["agent_b"]
    # Agents should be on empty cells and at different positions.
    assert a.position != b.position
    assert state.grid[a.position[0]][a.position[1]] != CellType.WALL
    assert state.grid[b.position[0]][b.position[1]] != CellType.WALL


def test_create_grid_border_walls():
    state = create_grid(width=6, height=6, seed=1)
    for c in range(6):
        assert state.grid[0][c] == CellType.WALL
        assert state.grid[5][c] == CellType.WALL
    for r in range(6):
        assert state.grid[r][0] == CellType.WALL
        assert state.grid[r][5] == CellType.WALL


def test_create_grid_deterministic_with_seed():
    s1 = create_grid(seed=99)
    s2 = create_grid(seed=99)
    assert s1.grid == s2.grid
    assert s1.key_position == s2.key_position
    assert s1.agents["agent_a"].position == s2.agents["agent_a"].position


def test_is_in_bounds():
    assert is_in_bounds(0, 0, 8, 8)
    assert is_in_bounds(7, 7, 8, 8)
    assert not is_in_bounds(-1, 0, 8, 8)
    assert not is_in_bounds(0, 8, 8, 8)


def test_neighbor_position():
    assert neighbor_position((3, 3), "north") == (2, 3)
    assert neighbor_position((3, 3), "south") == (4, 3)
    assert neighbor_position((3, 3), "east") == (3, 4)
    assert neighbor_position((3, 3), "west") == (3, 2)
    assert neighbor_position((3, 3), "invalid") is None
