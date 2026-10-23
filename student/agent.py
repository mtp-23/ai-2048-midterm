from __future__ import annotations

import time
from math import log2

import numpy as np

from game2048.observation import Observation
from game2048.rules import move_board
from game2048.types import Move


class _TimeUp(Exception):
    """Internal signal used to stop an unfinished search depth."""


class Agent:
    name = "group-5-ai4"

    # A snake pattern encourages the largest tile to stay in a corner.
    _SNAKE = np.array(
        (
            (16, 15, 14, 13),
            (9, 10, 11, 12),
            (8, 7, 6, 5),
            (1, 2, 3, 4),
        ),
        dtype=np.float64,
    )

    def __init__(self) -> None:
        self._deadline = 0.0
        self._nodes = 0
        self._cache: dict[tuple[bytes, int, bool], float] = {}
        self.last_nodes = 0
        self.last_completed_depth = 0

    def reset(self, seed: int | None = None) -> None:
        """Clear data that belongs to the previous game."""
        self._cache.clear()
        self.last_nodes = 0
        self.last_completed_depth = 0

    @classmethod
    def evaluate(cls, board: np.ndarray, merge_score: int = 0) -> float:
        """Return a larger value for safer, more promising boards."""
        values = np.log2(np.where(board == 0, 1, board))
        empty = float(np.count_nonzero(board == 0))
        largest = float(values.max())

        # Consider both horizontal snake directions. Rotating the board is
        # intentionally avoided here because it is expensive at every leaf.
        snake_score = max(
            float(np.sum(values * cls._SNAKE)),
            float(np.sum(np.fliplr(values) * cls._SNAKE)),
        )

        # Penalise neighbouring tiles with very different sizes.
        smoothness = 0.0
        for line in (*values, *values.T):
            smoothness -= float(np.sum(np.abs(line[1:] - line[:-1])))

        # Reward lines that consistently increase or decrease toward a corner.
        monotonicity = 0.0
        for line in (*values, *values.T):
            up = float(np.sum(np.maximum(line[:-1] - line[1:], 0.0)))
            down = float(np.sum(np.maximum(line[1:] - line[:-1], 0.0)))
            monotonicity += max(up, down)

        # Adjacent equal tiles are immediate merge opportunities.
        mergeable = 0
        for line in (*board, *board.T):
            mergeable += int(np.count_nonzero((line[:-1] != 0) & (line[:-1] == line[1:])))

        return (
            4.0 * empty
            + 0.12 * snake_score
            + 1.1 * monotonicity
            + 0.25 * smoothness
            + 1.0 * largest
            + 1.8 * mergeable
            + 0.15 * log2(merge_score + 1)
        )

    def _check_time(self) -> None:
        self._nodes += 1
        # Checking every node is cheap, and gives a predictable time limit.
        if time.perf_counter() >= self._deadline:
            raise _TimeUp

    @staticmethod
    def _key(board: np.ndarray, depth: int, chance: bool) -> tuple[bytes, int, bool]:
        return board.tobytes(), depth, chance

    def _player_value(self, board: np.ndarray, depth: int) -> float:
        """Expectimax MAX node: the player chooses one direction."""
        self._check_time()
        if depth == 0:
            return self.evaluate(board)

        key = self._key(board, depth, False)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        best = float("-inf")
        for move in Move:
            moved, reward, changed = move_board(board, move)
            if changed:
                best = max(
                    best,
                    reward + self._chance_value(moved, depth - 1),
                )

        value = self.evaluate(board) if best == float("-inf") else best
        self._cache[key] = value
        return value

    def _chance_value(self, board: np.ndarray, depth: int) -> float:
        """Expectimax chance node: average every legal spawn outcome."""
        self._check_time()
        key = self._key(board, depth, True)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        empty_cells = np.argwhere(board == 0)
        if len(empty_cells) == 0:
            value = self._player_value(board, depth)
            self._cache[key] = value
            return value

        total = 0.0
        position_probability = 1.0 / len(empty_cells)
        for row, column in empty_cells:
            for tile, tile_probability in ((2, 0.9), (4, 0.1)):
                child = board.copy()
                child[row, column] = tile
                total += (
                    position_probability
                    * tile_probability
                    * self._player_value(child, depth)
                )

        self._cache[key] = total
        return total

    def _best_move(
        self,
        board: np.ndarray,
        legal_moves: tuple[Move, ...],
        depth: int,
    ) -> Move:
        """Find the best move for one completely searched depth."""
        best_move = legal_moves[0]
        best_value = float("-inf")

        # A good move first makes the fallback useful if the next depth times out.
        candidates: list[tuple[float, Move, np.ndarray, int]] = []
        for move in legal_moves:
            moved, reward, _ = move_board(board, move)
            candidates.append((self.evaluate(moved, reward), move, moved, reward))
        candidates.sort(reverse=True, key=lambda item: item[0])

        for _, move, moved, reward in candidates:
            value = reward + self._chance_value(moved, depth - 1)
            if value > best_value:
                best_move, best_value = move, value
        return best_move

    def choose_move(self, obs: Observation, time_limit_ms: float) -> Move:
        """Return the deepest fully searched result before the deadline."""
        if not obs.legal_moves:
            raise ValueError("choose_move được gọi ở trạng thái kết thúc")

        # time_limit_ms may be the remaining budget for the whole game.
        # A cap leaves enough budget for many future turns.
        #
        budget_ms = max(1.0, min(float(time_limit_ms) * 0.9, 75))
        self._deadline = time.perf_counter() + budget_ms / 1000.0
        self._nodes = 0
        self._cache.clear()
        self.last_completed_depth = 0
        answer = obs.legal_moves[0]

        for depth in range(1, 8):
            try:
                answer = self._best_move(obs.board, obs.legal_moves, depth)
            except _TimeUp:
                break
            self.last_completed_depth = depth

        self.last_nodes = self._nodes
        return answer
