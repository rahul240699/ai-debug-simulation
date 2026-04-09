"""Item and cell-type constants for the dungeon grid."""

from __future__ import annotations

from enum import StrEnum


class CellType(StrEnum):
    """Every cell on the grid is one of these types."""

    EMPTY = "empty"
    WALL = "wall"
    KEY = "key"
    LOCKED_DOOR = "locked_door"
    EXIT = "exit"


# Directions an agent can move (Von Neumann neighborhood).
DIRECTIONS: dict[str, tuple[int, int]] = {
    "north": (-1, 0),
    "south": (1, 0),
    "east": (0, 1),
    "west": (0, -1),
}
