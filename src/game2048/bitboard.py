"""Correct exponent packing helpers reserved for the later optimization phase."""

from __future__ import annotations

import numpy as np


def pack_board(board: np.ndarray) -> int:
    packed = 0
    for index, value in enumerate(board.reshape(-1)):
        exponent = 0 if value == 0 else int(value).bit_length() - 1
        if exponent > 15:
            raise OverflowError("classic 64-bit packing supports tiles only through 32768")
        packed |= exponent << (index * 4)
    return packed


def unpack_board(packed: int) -> np.ndarray:
    board = np.zeros((4, 4), dtype=np.uint32)
    for index in range(16):
        exponent = (packed >> (index * 4)) & 0xF
        board.flat[index] = 0 if exponent == 0 else 1 << exponent
    return board

