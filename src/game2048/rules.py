from __future__ import annotations

import numpy as np

from .types import Move

BOARD_SIZE = 4


def _validate_board(board: np.ndarray) -> None:
    if not isinstance(board, np.ndarray) or board.shape != (BOARD_SIZE, BOARD_SIZE):
        raise ValueError("board must be a NumPy array with shape (4, 4)")


def merge_row_left(row: np.ndarray) -> tuple[np.ndarray, int]:
    """Return a left-moved row and the score earned by its merges."""
    values = [int(value) for value in row if value]
    merged: list[int] = []
    reward = 0
    index = 0
    while index < len(values):
        if index + 1 < len(values) and values[index] == values[index + 1]:
            value = values[index] * 2
            merged.append(value)
            reward += value
            index += 2
        else:
            merged.append(values[index])
            index += 1
    merged.extend([0] * (BOARD_SIZE - len(merged)))
    return np.asarray(merged, dtype=np.uint32), reward


def move_board(board: np.ndarray, move: Move | int) -> tuple[np.ndarray, int, bool]:
    """Apply only the deterministic player move; never spawn a tile."""
    _validate_board(board)
    try:
        direction = Move(move)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid move: {move!r}") from exc

    if direction == Move.LEFT:
        working = board
        restore = lambda value: value
    elif direction == Move.RIGHT:
        working = np.fliplr(board)
        restore = np.fliplr
    elif direction == Move.UP:
        working = board.T
        restore = lambda value: value.T
    else:
        working = np.fliplr(board.T)
        restore = lambda value: np.fliplr(value).T

    rows: list[np.ndarray] = []
    reward = 0
    for row in working:
        moved_row, row_reward = merge_row_left(row)
        rows.append(moved_row)
        reward += row_reward
    result = np.asarray(restore(np.stack(rows)), dtype=np.uint32)
    changed = not np.array_equal(result, board)
    return result, reward, changed


def legal_moves(board: np.ndarray) -> tuple[Move, ...]:
    return tuple(move for move in Move if move_board(board, move)[2])


def is_game_over(board: np.ndarray) -> bool:
    return not legal_moves(board)

