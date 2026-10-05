from __future__ import annotations

import random

from game2048.observation import Observation
from game2048.types import Move


class Agent:
    name = "boss0-random"

    def __init__(self) -> None:
        self._rng = random.Random()

    def reset(self, seed: int | None = None) -> None:
        self._rng.seed(seed)

    def choose_move(self, obs: Observation, time_limit_ms: float) -> Move:
        return self._rng.choice(obs.legal_moves)

