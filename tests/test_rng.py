import numpy as np

from game2048.rng import ScenarioTape, SpawnEvent, apply_spawn


def test_spawn_mapping_and_threshold():
    board = np.zeros((4, 4), dtype=np.uint32)
    first, position, tile = apply_spawn(board, SpawnEvent(0.0, 0.899999))
    assert position == (0, 0) and tile == 2 and first[0, 0] == 2
    last, position, tile = apply_spawn(board, SpawnEvent(0.999999, 0.9))
    assert position == (3, 3) and tile == 4 and last[3, 3] == 4


def test_tape_is_reproducible():
    left, right = ScenarioTape(42), ScenarioTape(42)
    assert [left.next_event() for _ in range(20)] == [right.next_event() for _ in range(20)]

