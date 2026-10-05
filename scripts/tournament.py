from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from game2048.tournament import round_robin


def discover(folder: Path) -> dict[str, type]:
    agents: dict[str, type] = {}
    for path in sorted(folder.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"submission_{path.stem}", path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        agents[path.stem] = module.Agent
    return agents


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paired-seed round-robin tournament")
    parser.add_argument("--agents", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--time-ms", type=float)
    parser.add_argument("--total-time-sec", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    per_move_ms = args.time_ms if args.time_ms is not None or args.total_time_sec is not None else 50.0
    result = round_robin(
        discover(args.agents),
        list(range(args.seeds)),
        per_move_ms,
        args.total_time_sec,
    )
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")

