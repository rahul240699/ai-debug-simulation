"""Grid creation, random wall placement, and spatial utilities."""

from __future__ import annotations

import random
from collections import deque

from src.simulation.items import CellType, DIRECTIONS
from src.simulation.state import AgentState, DungeonState


def create_grid(
    width: int = 8,
    height: int = 8,
    wall_density: float = 0.15,
    seed: int | None = None,
) -> DungeonState:
    """Build a new dungeon with random walls, a key, locked door, exit, and two agents.

    The generator guarantees a reachable path from every agent start to the key,
    from the key to the door, and from the door to the exit.
    """
    rng = random.Random(seed)

    # Start with an empty grid.
    grid: list[list[str]] = [
        [CellType.EMPTY for _ in range(width)] for _ in range(height)
    ]

    # Border walls.
    for r in range(height):
        for c in range(width):
            if r == 0 or r == height - 1 or c == 0 or c == width - 1:
                grid[r][c] = CellType.WALL

    # Collect interior cells for random placement.
    interior: list[tuple[int, int]] = [
        (r, c)
        for r in range(1, height - 1)
        for c in range(1, width - 1)
    ]
    rng.shuffle(interior)

    # Reserve cells for special items and agents (pop from shuffled list).
    agent_a_pos = interior.pop()
    agent_b_pos = interior.pop()
    key_pos = interior.pop()
    door_pos = interior.pop()
    exit_pos = interior.pop()

    # Place interior walls.
    num_walls = int(len(interior) * wall_density)
    wall_candidates = interior[:num_walls]

    for pos in wall_candidates:
        grid[pos[0]][pos[1]] = CellType.WALL

    # Place special cells.
    grid[key_pos[0]][key_pos[1]] = CellType.KEY
    grid[door_pos[0]][door_pos[1]] = CellType.LOCKED_DOOR
    grid[exit_pos[0]][exit_pos[1]] = CellType.EXIT

    # Verify connectivity — all special cells must be reachable from each other.
    important = [agent_a_pos, agent_b_pos, key_pos, door_pos, exit_pos]
    if not _all_reachable(grid, important, height, width):
        # Remove walls until connected (simple fallback).
        for pos in wall_candidates:
            grid[pos[0]][pos[1]] = CellType.EMPTY
            if _all_reachable(grid, important, height, width):
                break

    state = DungeonState(
        grid=grid,
        grid_width=width,
        grid_height=height,
        key_position=key_pos,
        door_position=door_pos,
        exit_position=exit_pos,
        agents={
            "agent_a": AgentState(agent_id="agent_a", position=agent_a_pos),
            "agent_b": AgentState(agent_id="agent_b", position=agent_b_pos),
        },
    )
    return state


# ── Spatial helpers ──────────────────────────────────────────────────────────


def is_in_bounds(row: int, col: int, height: int, width: int) -> bool:
    return 0 <= row < height and 0 <= col < width


def neighbor_position(pos: tuple[int, int], direction: str) -> tuple[int, int] | None:
    """Return the (row, col) one step in *direction* from *pos*, or None."""
    delta = DIRECTIONS.get(direction)
    if delta is None:
        return None
    return (pos[0] + delta[0], pos[1] + delta[1])


def _all_reachable(
    grid: list[list[str]],
    positions: list[tuple[int, int]],
    height: int,
    width: int,
) -> bool:
    """BFS from positions[0] — returns True if all other positions are reachable."""
    if not positions:
        return True
    passable = {CellType.EMPTY, CellType.KEY, CellType.LOCKED_DOOR, CellType.EXIT}
    start = positions[0]
    visited: set[tuple[int, int]] = {start}
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in DIRECTIONS.values():
            nr, nc = r + dr, c + dc
            if (nr, nc) not in visited and is_in_bounds(nr, nc, height, width):
                if grid[nr][nc] in passable or (nr, nc) in positions:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
    return all(p in visited for p in positions)
