from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .observation import Observation
from .rng import ScenarioTape, apply_spawn
from .rules import BOARD_SIZE, legal_moves, move_board
from .types import Move


@dataclass(frozen=True, slots=True)
class GameResult:
    score: int
    max_tile: int
    move_count: int
    final_board: np.ndarray


class Game:
    """Authoritative 2048 environment with an environment-owned RNG."""

    def __init__(self, seed: int | None = None):
        self.seed = seed
        self.board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.uint32)
        self.score = 0
        self.move_count = 0
        self._tape = ScenarioTape(seed)
        self.last_spawn: tuple[tuple[int, int], int] | None = None
        self._spawn()
        self._spawn()

    def _spawn(self) -> None:
        self.board, position, tile = apply_spawn(self.board, self._tape.next_event())
        self.last_spawn = position, tile

    @property
    def available_moves(self) -> tuple[Move, ...]:
        return legal_moves(self.board)

    @property
    def game_over(self) -> bool:
        return not self.available_moves

    def observe(
        self,
        time_remaining_ms: float | None = None,
        total_time_limit_ms: float | None = None,
    ) -> Observation:
        safe_board = self.board.copy()
        safe_board.flags.writeable = False
        return Observation(
            safe_board,
            self.score,
            self.move_count,
            self.available_moves,
            time_remaining_ms,
            total_time_limit_ms,
        )

    def move(self, move: Move | int) -> bool:
        moved, reward, changed = move_board(self.board, move)
        if not changed:
            return False
        self.board = moved
        self.score += reward
        self.move_count += 1
        self._spawn()
        return True

    def result(self) -> GameResult:
        final_board = self.board.copy()
        final_board.flags.writeable = False
        return GameResult(self.score, int(self.board.max()), self.move_count, final_board)

