import numpy as np

from game2048.engine import Game
from game2048.types import Move


def test_initial_state_has_two_tiles():
    game = Game(7)
    assert np.count_nonzero(game.board) == 2
    assert set(game.board.flat) <= {0, 2, 4}
    assert game.score == 0 and game.move_count == 0


def test_illegal_move_does_not_consume_rng():
    game = Game(1)
    game.board = np.asarray([[2, 4, 8, 16]] + [[0, 0, 0, 0]] * 3, dtype=np.uint32)
    consumed = game._tape.events_consumed
    before = game.board.copy()
    assert not game.move(Move.LEFT)
    assert game._tape.events_consumed == consumed
    assert np.array_equal(game.board, before)


def test_observation_is_defensive_and_read_only():
    game = Game(2)
    observation = game.observe()
    assert not observation.board.flags.writeable
    game.board[0, 0] = 1024
    assert observation.board[0, 0] != 1024


def test_score_and_move_count():
    game = Game(3)
    game.board = np.asarray([[2, 2, 4, 4]] + [[0, 0, 0, 0]] * 3, dtype=np.uint32)
    assert game.move(Move.LEFT)
    assert game.score == 12 and game.move_count == 1
    assert np.count_nonzero(game.board) == 3  # two merged tiles plus spawn

