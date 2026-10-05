import time

from game2048.benchmark import run_game
from game2048.observation import Observation
from game2048.types import Move
from student.agent import Agent


def test_starter_agent_completes_game_legally():
    result = run_game(Agent(), seed=0, decision_budget_ms=50)
    assert result["failure"] is None
    assert result["illegal_moves"] == result["exceptions"] == 0


def test_agent_receives_read_only_board():
    class MutatingAgent:
        name = "bad"

        def reset(self, seed=None):
            pass

        def choose_move(self, obs: Observation, time_limit_ms: float) -> Move:
            obs.board[0, 0] = 99
            return obs.legal_moves[0]

    result = run_game(MutatingAgent(), 0)
    assert result["exceptions"] == 1


def test_total_game_budget_is_exposed_and_stops_game():
    class SlowAgent:
        name = "slow"

        def __init__(self):
            self.remaining = []

        def reset(self, seed=None):
            pass

        def choose_move(self, obs: Observation, time_limit_ms: float) -> Move:
            self.remaining.append(obs.time_remaining_ms)
            time.sleep(0.003)
            return obs.legal_moves[0]

    agent = SlowAgent()
    result = run_game(agent, 0, decision_budget_ms=None, total_budget_seconds=0.001)
    assert result["budget_exhausted"]
    assert result["moves"] == 0  # the over-budget decision is not applied
    assert result["total_decision_time_ms"] >= 1.0
    assert agent.remaining[0] == 1.0

