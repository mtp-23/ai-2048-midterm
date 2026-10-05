import numpy as np

from game2048.engine import Game


def test_same_seed_and_policy_replay_exactly():
    games = [Game(2026), Game(2026)]
    for _ in range(100):
        if games[0].game_over:
            break
        action = games[0].available_moves[0]
        assert games[1].available_moves[0] == action
        games[0].move(action)
        games[1].move(action)
    assert games[0].score == games[1].score
    assert games[0].move_count == games[1].move_count
    assert np.array_equal(games[0].board, games[1].board)

