from __future__ import annotations

from enum import IntEnum


class Move(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3


MOVE_NAMES = {move.name.lower(): move for move in Move}

