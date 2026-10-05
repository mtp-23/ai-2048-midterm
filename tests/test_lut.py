import numpy as np

from game2048.lut import decode_row, encode_row
from game2048.rules import merge_row_left


def test_row_encoding_round_trip():
    for encoded in (0, 1, 0x1234, 0xFFFF, 0xA20C):
        assert encode_row(decode_row(encoded)) == encoded


def test_sample_lut_semantics_match_reference():
    row = np.asarray([2, 0, 2, 2], dtype=np.uint32)
    moved, reward = merge_row_left(row)
    assert decode_row(encode_row(moved)).tolist() == [4, 2, 0, 0]
    assert reward == 4

