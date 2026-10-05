import numpy as np
import pytest

from game2048.rules import legal_moves, merge_row_left, move_board
from game2048.types import Move


@pytest.mark.parametrize(
    ("source", "expected", "reward"),
    [
        ([2, 2, 2, 2], [4, 4, 0, 0], 8),
        ([2, 2, 4, 0], [4, 4, 0, 0], 4),
        ([4, 4, 8, 8], [8, 16, 0, 0], 24),
        ([2, 0, 2, 2], [4, 2, 0, 0], 4),
        ([4, 4, 4, 0], [8, 4, 0, 0], 8),
    ],
)
def test_merge_examples(source, expected, reward):
    actual, actual_reward = merge_row_left(np.asarray(source, dtype=np.uint32))
    assert actual.tolist() == expected
    assert actual_reward == reward


def test_all_directions_and_legality():
    board = np.asarray([[2, 0, 0, 0], [2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], dtype=np.uint32)
    up, reward, changed = move_board(board, Move.UP)
    assert up[:, 0].tolist() == [4, 0, 0, 0]
    assert reward == 4 and changed
    down, reward, changed = move_board(board, Move.DOWN)
    assert down[:, 0].tolist() == [0, 0, 0, 4]
    assert reward == 4 and changed
    assert Move.LEFT not in legal_moves(board)


def test_move_does_not_mutate_input():
    board = np.asarray([[2, 2, 0, 0]] + [[0, 0, 0, 0]] * 3, dtype=np.uint32)
    original = board.copy()
    move_board(board, Move.LEFT)
    assert np.array_equal(board, original)

