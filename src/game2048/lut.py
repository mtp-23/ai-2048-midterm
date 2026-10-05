"""Small, lazy row-table utilities; full optimized search belongs to Boss 3."""

from __future__ import annotations

import numpy as np

from .rules import merge_row_left


def decode_row(encoded: int) -> np.ndarray:
    return np.asarray([0 if (e := (encoded >> (4 * i)) & 0xF) == 0 else 1 << e for i in range(4)], dtype=np.uint32)


def encode_row(row: np.ndarray) -> int:
    encoded = 0
    for index, value in enumerate(row):
        exponent = 0 if value == 0 else int(value).bit_length() - 1
        if exponent > 15:
            raise OverflowError("row encoding supports tiles only through 32768")
        encoded |= exponent << (4 * index)
    return encoded


def build_left_tables() -> tuple[np.ndarray, np.ndarray]:
    moves = np.zeros(65536, dtype=np.uint16)
    rewards = np.zeros(65536, dtype=np.uint32)
    for encoded in range(65536):
        row, reward = merge_row_left(decode_row(encoded))
        moves[encoded] = encode_row(row)
        rewards[encoded] = reward
    return moves, rewards

