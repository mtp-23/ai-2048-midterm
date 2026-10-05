from __future__ import annotations

import math
from statistics import median
from typing import Any, Iterable

import numpy as np


def summarize(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    if not rows:
        raise ValueError("at least one result is required")
    scores = np.asarray([row["score"] for row in rows], dtype=np.float64)
    tiles = np.asarray([row["max_tile"] for row in rows], dtype=np.float64)
    moves = np.asarray([row["moves"] for row in rows], dtype=np.float64)
    timings = [time for row in rows for time in row.get("decision_times_ms", [])]
    result: dict[str, Any] = {
        "games": len(rows),
        "mean_score": float(scores.mean()),
        "median_score": float(np.median(scores)),
        "std_score": float(scores.std()),
        "geometric_mean_score": float(math.exp(np.log(np.maximum(scores, 1)).mean())),
        "min_score": int(scores.min()),
        "max_score": int(scores.max()),
        "mean_max_tile": float(tiles.mean()),
        "median_max_tile": float(np.median(tiles)),
        "mean_moves": float(moves.mean()),
        "median_moves": float(np.median(moves)),
        "timeouts": sum(int(row.get("timeouts", 0)) for row in rows),
        "illegal_moves": sum(int(row.get("illegal_moves", 0)) for row in rows),
        "exceptions": sum(int(row.get("exceptions", 0)) for row in rows),
        "budget_exhausted": sum(bool(row.get("budget_exhausted", False)) for row in rows),
        "mean_total_decision_time_ms": float(
            np.mean([row.get("total_decision_time_ms", 0.0) for row in rows])
        ),
        "mean_states_per_second": float(
            np.mean([row.get("states_per_second", 0.0) for row in rows])
        ),
        "mean_search_depth": float(
            np.mean([row.get("mean_search_depth", 0.0) for row in rows])
        ),
    }
    for target in (2048, 4096, 8192, 16384, 32768, 65536):
        if target <= 32768 or np.any(tiles >= target):
            result[f"p_{target}"] = float(np.mean(tiles >= target))
    result["mean_decision_time_ms"] = float(np.mean(timings)) if timings else 0.0
    result["p95_decision_time_ms"] = float(np.percentile(timings, 95)) if timings else 0.0
    return result


def paired_summary(a: Iterable[dict[str, Any]], b: Iterable[dict[str, Any]]) -> dict[str, Any]:
    left = {row["seed"]: row for row in a}
    right = {row["seed"]: row for row in b}
    seeds = sorted(left.keys() & right.keys())
    if not seeds:
        raise ValueError("no paired seeds")
    a_scores = np.asarray([left[seed]["score"] for seed in seeds], dtype=np.float64)
    b_scores = np.asarray([right[seed]["score"] for seed in seeds], dtype=np.float64)
    differences = a_scores - b_scores
    ratios = a_scores / np.maximum(b_scores, 1)
    return {
        "paired_games": len(seeds),
        "paired_win_rate_A": float(np.mean(differences > 0)),
        "paired_win_rate_B": float(np.mean(differences < 0)),
        "ties": int(np.sum(differences == 0)),
        "mean_score_ratio": float(np.mean(ratios)),
        "median_score_ratio": float(median(ratios)),
        "paired_score_difference_mean": float(differences.mean()),
        "paired_score_difference_median": float(np.median(differences)),
    }

