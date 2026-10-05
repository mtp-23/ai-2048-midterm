from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SpawnEvent:
    u_position: float
    u_tile: float


class ScenarioTape:
    """Private deterministic stream of uniform pairs used by the environment."""

    def __init__(self, seed: int | None = None):
        self.seed = seed
        self._generator = np.random.default_rng(seed)
        self.events_consumed = 0

    def next_event(self) -> SpawnEvent:
        values = self._generator.random(2)
        self.events_consumed += 1
        return SpawnEvent(float(values[0]), float(values[1]))


def apply_spawn(board: np.ndarray, event: SpawnEvent) -> tuple[np.ndarray, tuple[int, int], int]:
    """Map an event to row-major sorted empty cells and return a new board."""
    empty = np.argwhere(board == 0)
    if len(empty) == 0:
        raise ValueError("cannot spawn on a full board")
    index = min(int(event.u_position * len(empty)), len(empty) - 1)
    row, column = (int(value) for value in empty[index])
    tile = 2 if event.u_tile < 0.9 else 4
    result = board.copy()
    result[row, column] = tile
    return result, (row, column), tile

