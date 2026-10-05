from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .types import Move


@dataclass(frozen=True, slots=True)
class Observation:
    board: np.ndarray
    score: int
    move_count: int
    legal_moves: tuple[Move, ...]
    time_remaining_ms: float | None = None
    total_time_limit_ms: float | None = None

