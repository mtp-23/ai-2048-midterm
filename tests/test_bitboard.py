import numpy as np
import pytest

from game2048.bitboard import pack_board, unpack_board


def test_packed_round_trip():
    board = np.asarray([[0, 2, 4, 8], [16, 32, 64, 128], [256, 512, 1024, 2048], [4096, 8192, 16384, 32768]], dtype=np.uint32)
    assert np.array_equal(unpack_board(pack_board(board)), board)


def test_packed_overflow_is_explicit():
    board = np.zeros((4, 4), dtype=np.uint32)
    board[0, 0] = 65536
    with pytest.raises(OverflowError):
        pack_board(board)

