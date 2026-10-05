from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .rules import move_board
from .types import Move


@dataclass(frozen=True, slots=True)
class HeuristicWeights:
    empty: float = 270.0
    monotonicity: float = 47.0
    smoothness: float = 15.0
    corner: float = 120.0
    merge_potential: float = 35.0
    immediate_reward: float = 1.0


def exponent_board(board: np.ndarray) -> np.ndarray:
    result = np.zeros(board.shape, dtype=np.float64)
    occupied = board > 0
    result[occupied] = np.log2(board[occupied])
    return result


def monotonicity(exponents: np.ndarray) -> float:
    total = 0.0
    for lines in (exponents, exponents.T):
        for line in lines:
            increasing = float(np.maximum(line[1:] - line[:-1], 0).sum())
            decreasing = float(np.maximum(line[:-1] - line[1:], 0).sum())
            total += max(increasing, decreasing)
    return total


def smoothness(exponents: np.ndarray) -> float:
    penalty = 0.0
    horizontal = (exponents[:, :-1] > 0) & (exponents[:, 1:] > 0)
    vertical = (exponents[:-1, :] > 0) & (exponents[1:, :] > 0)
    penalty += float(np.abs(exponents[:, :-1] - exponents[:, 1:])[horizontal].sum())
    penalty += float(np.abs(exponents[:-1, :] - exponents[1:, :])[vertical].sum())
    return penalty


def merge_potential(board: np.ndarray) -> int:
    horizontal = (board[:, :-1] == board[:, 1:]) & (board[:, :-1] != 0)
    vertical = (board[:-1, :] == board[1:, :]) & (board[:-1, :] != 0)
    return int(horizontal.sum() + vertical.sum())


def corner_score(board: np.ndarray) -> float:
    maximum = int(board.max())
    if maximum == 0:
        return 0.0
    return float(np.log2(maximum)) if maximum in board[[0, 0, -1, -1], [0, -1, 0, -1]] else 0.0


def evaluate_board(
    board: np.ndarray,
    weights: HeuristicWeights = HeuristicWeights(),
    immediate_reward: int = 0,
) -> float:
    exponents = exponent_board(board)
    return (
        weights.empty * float(np.count_nonzero(board == 0))
        + weights.monotonicity * monotonicity(exponents)
        - weights.smoothness * smoothness(exponents)
        + weights.corner * corner_score(board)
        + weights.merge_potential * merge_potential(board)
        + weights.immediate_reward * immediate_reward
    )


def best_greedy_move(board: np.ndarray, weights: HeuristicWeights = HeuristicWeights()) -> Move:
    candidates: list[tuple[float, int, Move]] = []
    for move in Move:
        afterstate, reward, changed = move_board(board, move)
        if changed:
            candidates.append((evaluate_board(afterstate, weights, reward), -int(move), move))
    if not candidates:
        raise ValueError("no legal moves")
    return max(candidates)[2]

