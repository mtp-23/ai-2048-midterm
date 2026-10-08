"""Điểm bắt đầu của bài nộp — sinh viên chỉ cần sửa file này.

Baseline bên dưới nhìn trước đúng một nước. Nó minh họa API và cách mô phỏng
nước đi, nhưng cố ý chưa xử lý ô ngẫu nhiên và chưa phải một thuật toán mạnh.
"""

from __future__ import annotations

import numpy as np

from game2048.observation import Observation
from game2048.rules import move_board
from game2048.types import Move


class Agent:
    # Đổi tên này thành tên đội; nó sẽ xuất hiện trong UI và file kết quả.
    name = "group-5-ai4"

    def reset(self, seed: int | None = None) -> None:
        """Xóa cache/trạng thái giữa hai ván nếu thuật toán của bạn có dùng."""

    @staticmethod
    def evaluate(board: np.ndarray, merge_score: int) -> float:
        """Heuristic mẫu; hãy thay bằng thiết kế của nhóm."""
        empty_cells = int(np.count_nonzero(board == 0))
        largest_tile = int(board.max())
        return 250.0 * empty_cells + merge_score + 0.1 * largest_tile

    def choose_move(self, obs: Observation, time_limit_ms: float) -> Move:
        """Trả về đúng một phần tử ``Move`` có trong ``obs.legal_moves``.

        Khi chấm theo tổng thời gian, ``time_limit_ms`` và
        ``obs.time_remaining_ms`` là ngân sách còn lại của cả ván — không phải
        lời hứa rằng mỗi nước được phép dùng hết số đó.
        """
        if not obs.legal_moves:
            raise ValueError("choose_move được gọi ở trạng thái kết thúc")

        best_move = obs.legal_moves[0]
        best_value = float("-inf")
        for move in obs.legal_moves:
            next_board, merge_score, _changed = move_board(obs.board, move)
            value = self.evaluate(next_board, merge_score)
            if value > best_value:
                best_value, best_move = value, move
        return best_move
