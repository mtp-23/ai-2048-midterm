from __future__ import annotations

from itertools import combinations
from typing import Any

from .benchmark import benchmark
from .metrics import paired_summary


def round_robin(
    agents: dict[str, type[Any]],
    seeds: list[int],
    decision_budget_ms: float | None = 50.0,
    total_budget_seconds: float | None = None,
) -> dict[str, Any]:
    records: dict[str, list[dict[str, Any]]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for name, agent_class in agents.items():
        records[name], summaries[name] = benchmark(
            agent_class,
            seeds,
            decision_budget_ms,
            total_budget_seconds=total_budget_seconds,
        )
    pairings = {
        f"{left}_vs_{right}": paired_summary(records[left], records[right])
        for left, right in combinations(agents, 2)
    }
    return {"summaries": summaries, "pairings": pairings, "games": records}

