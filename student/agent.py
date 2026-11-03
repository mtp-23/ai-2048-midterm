from __future__ import annotations

import time

import numpy as np

from game2048.observation import Observation
from game2048.rules import move_board
from game2048.types import Move


class _TimeUp(Exception):
    """Hết giờ giữa chừng một độ sâu tìm kiếm."""


def _real_limit(ms: float | None) -> float | None:
    """Giới hạn thời gian thật, hoặc None nếu là None/vô cực/quá 1 giờ (= không giới hạn)."""
    if ms is None or not np.isfinite(ms) or ms > 3_600_000:
        return None
    return float(ms)


class Agent:
    name = "group-5-ai4"

    # Chế độ giới hạn tổng thời gian: chia đều cho số nước còn dự tính.
    EXPECTED_MOVES = 1500
    MIN_MOVES_LEFT = 200
    MAX_SHARE = 0.10          # một nước dùng tối đa 10% thời gian còn lại
    MAX_MOVE_MS = 500
    # Chế độ không giới hạn: ngân sách cố định mỗi nước.
    UNLIMITED_MOVE_MS = 100
    # Chung.
    SAFETY = 0.85             # chừa 15% cho overhead
    MAX_DEPTH = 8
    DEAD_SCORE = -10_000_000
    CACHE_LIMIT = 500_000

    def __init__(self) -> None:
        self._deadline = 0.0
        self._nodes = 0
        self._cache: dict[tuple[bytes, int, bool], float] = {}
        self.last_nodes = 0
        self.last_completed_depth = 0

    def reset(self, seed: int | None = None) -> None:
        self._cache.clear()
        self.last_nodes = 0
        self.last_completed_depth = 0

    # ---------------- Hàm đánh giá (8 đường = 4 hàng + 4 cột) ----------------
    @staticmethod
    def evaluate(board: np.ndarray, merge_score: int = 0) -> float:
        ranks = np.log2(np.maximum(board, 1))            # ô trống = 0, 2 = 1, 4 = 2...
        lines = np.concatenate((ranks, ranks.T))         # shape (8, 4)

        empty = np.count_nonzero(lines == 0)                                          # ô trống
        merges = np.count_nonzero((lines[:, 1:] == lines[:, :-1]) & (lines[:, 1:] > 0))  # cặp gộp được
        diff = np.diff(lines ** 4, axis=1)
        mono_penalty = np.minimum(np.maximum(-diff, 0).sum(1), np.maximum(diff, 0).sum(1)).sum()
        spread_penalty = (lines ** 3.5).sum()                                         # ô lớn rải rác

        return 1_600_000 + 270 * empty + 700 * merges - 47 * mono_penalty - 11 * spread_penalty

    # ---------------- Expectimax ----------------
    def _tick(self) -> None:
        self._nodes += 1
        if time.perf_counter() >= self._deadline:
            raise _TimeUp

    def _max_node(self, board: np.ndarray, depth: int) -> float:
        """Người chơi chọn hướng tốt nhất."""
        self._tick()
        if depth == 0:
            return self.evaluate(board)
        key = (board.tobytes(), depth, False)
        if key not in self._cache:
            values = [self._chance_node(moved, depth - 1)
                      for moved, _, changed in (move_board(board, m) for m in Move) if changed]
            self._cache[key] = max(values, default=self.DEAD_SCORE)
        return self._cache[key]

    def _chance_node(self, board: np.ndarray, depth: int) -> float:
        """Trung bình theo vị trí ô mới (chỉ xét ô 2, xác suất 90%, để giảm nhánh)."""
        self._tick()
        key = (board.tobytes(), depth, True)
        if key not in self._cache:
            total = 0.0
            cells = np.argwhere(board == 0)
            for r, c in cells:
                child = board.copy()
                child[r, c] = 2
                total += self._max_node(child, depth)
            self._cache[key] = total / len(cells)
        return self._cache[key]

    def _score_move(self, board: np.ndarray, move: Move, depth: int) -> float:
        moved, _, _ = move_board(board, move)
        return self._chance_node(moved, depth - 1) if depth > 0 else self.evaluate(moved)

    # ---------------- Chia thời gian ----------------
    def _budget_ms(self, obs: Observation, time_limit_ms: float | None) -> float:
        remaining = _real_limit(obs.time_remaining_ms)
        limit = _real_limit(time_limit_ms)

        empty = int(np.count_nonzero(obs.board == 0))
        danger = 3.0 if empty <= 3 else 1.5 if empty <= 6 else 0.6   # bàn chật -> nghĩ lâu hơn

        if remaining is None:                       # không giới hạn tổng thời gian
            budget = self.UNLIMITED_MOVE_MS * danger
            if limit is not None:
                budget = min(budget, limit)
        else:                                       # giới hạn tổng thời gian
            if limit is not None:
                remaining = min(remaining, limit)
            moves_left = max(self.EXPECTED_MOVES - obs.move_count, self.MIN_MOVES_LEFT)
            budget = min(remaining / moves_left * danger, remaining * self.MAX_SHARE, self.MAX_MOVE_MS)
        return budget * self.SAFETY

    # ---------------- Chọn nước đi ----------------
    def choose_move(self, obs: Observation, time_limit_ms: float) -> Move:
        if not obs.legal_moves:
            raise ValueError("choose_move được gọi ở trạng thái kết thúc")

        # Đáp án dự phòng rẻ (độ sâu 0), luôn có sẵn kể cả khi gần hết giờ.
        answer = max(obs.legal_moves, key=lambda m: self._score_move(obs.board, m, 0))

        budget_ms = self._budget_ms(obs, time_limit_ms)
        self._nodes = 0
        self.last_completed_depth = 0
        if budget_ms >= 2.0:
            self._deadline = time.perf_counter() + budget_ms / 1000.0
            if len(self._cache) > self.CACHE_LIMIT:
                self._cache.clear()
            for depth in range(1, self.MAX_DEPTH + 1):      # tìm sâu dần đến khi hết giờ
                try:
                    answer = max(obs.legal_moves, key=lambda m: self._score_move(obs.board, m, depth))
                except _TimeUp:
                    break
                self.last_completed_depth = depth

        self.last_nodes = self._nodes
        return answer