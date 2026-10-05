from __future__ import annotations

import importlib
import json
import os
import time
from pathlib import Path
from typing import Any

from .engine import Game
from .interfaces import AgentProtocol
from .metrics import summarize
from .types import Move

for variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(variable, "1")


def load_agent(spec: str) -> type[Any]:
    module_name, separator, class_name = spec.partition(":")
    if not separator:
        raise ValueError("agent must use module.path:ClassName syntax")
    module = importlib.import_module(module_name)
    candidate = getattr(module, class_name)
    if not callable(candidate):
        raise TypeError(f"{spec} is not callable")
    return candidate


def run_game(
    agent: AgentProtocol,
    seed: int,
    decision_budget_ms: float | None = 50.0,
    strict_time: bool = False,
    total_budget_seconds: float | None = None,
) -> dict[str, Any]:
    if decision_budget_ms is not None and decision_budget_ms <= 0:
        raise ValueError("decision_budget_ms must be positive or None")
    if total_budget_seconds is not None and total_budget_seconds <= 0:
        raise ValueError("total_budget_seconds must be positive or None")
    game = Game(seed)
    decision_times: list[float] = []
    search_nodes: list[int] = []
    search_depths: list[int] = []
    timeouts = illegal_moves = exceptions = 0
    budget_exhausted = False
    total_decision_ms = 0.0
    total_budget_ms = None if total_budget_seconds is None else total_budget_seconds * 1000.0
    failure: str | None = None
    started = time.perf_counter()
    try:
        agent.reset(seed)
    except Exception as exc:  # benchmark boundary intentionally catches submissions
        exceptions = 1
        failure = f"reset: {type(exc).__name__}: {exc}"

    while failure is None and not game.game_over:
        remaining_ms = None if total_budget_ms is None else max(0.0, total_budget_ms - total_decision_ms)
        if remaining_ms is not None and remaining_ms <= 0:
            budget_exhausted = True
            break
        effective_limit_ms = decision_budget_ms
        if remaining_ms is not None:
            effective_limit_ms = remaining_ms if effective_limit_ms is None else min(effective_limit_ms, remaining_ms)
        if effective_limit_ms is None:
            effective_limit_ms = 50.0
        observation = game.observe(remaining_ms, total_budget_ms)
        before = time.perf_counter_ns()
        try:
            action = agent.choose_move(observation, effective_limit_ms)
        except Exception as exc:  # benchmark boundary intentionally catches submissions
            exceptions += 1
            failure = f"choose_move: {type(exc).__name__}: {exc}"
            break
        elapsed_ms = (time.perf_counter_ns() - before) / 1_000_000
        decision_times.append(elapsed_ms)
        if hasattr(agent, "last_nodes"):
            search_nodes.append(int(getattr(agent, "last_nodes")))
        if hasattr(agent, "last_completed_depth"):
            search_depths.append(int(getattr(agent, "last_completed_depth")))
        total_decision_ms += elapsed_ms
        if decision_budget_ms is not None and elapsed_ms > decision_budget_ms:
            timeouts += 1
            if strict_time:
                failure = f"decision exceeded {decision_budget_ms:g} ms"
                break
        if total_budget_ms is not None and total_decision_ms > total_budget_ms:
            budget_exhausted = True
            break
        try:
            move = Move(action)
        except (TypeError, ValueError):
            illegal_moves += 1
            failure = f"invalid action: {action!r}"
            break
        if move not in observation.legal_moves:
            illegal_moves += 1
            failure = f"illegal move: {move.name}"
            break
        game.move(move)

    result = game.result()
    return {
        "agent": getattr(agent, "name", type(agent).__name__),
        "seed": seed,
        "score": result.score,
        "max_tile": result.max_tile,
        "moves": result.move_count,
        "final_board": result.final_board.tolist(),
        "wall_time_sec": time.perf_counter() - started,
        "decision_times_ms": decision_times,
        "mean_decision_ms": sum(decision_times) / len(decision_times) if decision_times else 0.0,
        "total_decision_time_ms": total_decision_ms,
        "total_budget_seconds": total_budget_seconds,
        "budget_exhausted": budget_exhausted,
        "search_nodes": sum(search_nodes),
        "states_per_second": (
            sum(search_nodes) / (total_decision_ms / 1000.0)
            if search_nodes and total_decision_ms > 0
            else 0.0
        ),
        "mean_search_depth": (
            sum(search_depths) / len(search_depths) if search_depths else 0.0
        ),
        "timeouts": timeouts,
        "illegal_moves": illegal_moves,
        "exceptions": exceptions,
        "failure": failure,
    }


def benchmark(
    agent_class: type[Any],
    seeds: list[int],
    decision_budget_ms: float | None = 50.0,
    strict_time: bool = False,
    total_budget_seconds: float | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = [
        run_game(agent_class(), seed, decision_budget_ms, strict_time, total_budget_seconds)
        for seed in seeds
    ]
    return records, summarize(records)


def save_json(path: str | Path, records: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"summary": summary, "games": records}, indent=2), encoding="utf-8")


def format_summary(summary: dict[str, Any]) -> str:
    keys = (
        "games", "mean_score", "median_score", "std_score", "mean_max_tile",
        "p_2048", "p_4096", "mean_moves", "mean_decision_time_ms",
        "p95_decision_time_ms", "mean_total_decision_time_ms", "budget_exhausted",
        "mean_states_per_second", "mean_search_depth",
        "timeouts", "illegal_moves", "exceptions",
    )
    return "\n".join(f"{key:>24}: {summary[key]:.3f}" if isinstance(summary.get(key), float) else f"{key:>24}: {summary.get(key)}" for key in keys)

