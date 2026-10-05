from __future__ import annotations

import argparse

from .benchmark import benchmark, format_summary, load_agent, save_json


def main() -> None:
    parser = argparse.ArgumentParser(prog="game2048")
    parser.add_argument("agent", help="module.path:AgentClass")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--start-seed", type=int, default=0)
    parser.add_argument("--time-ms", type=float, help="optional hard budget for each move")
    parser.add_argument("--total-time-sec", type=float, help="shared thinking-time budget for one game")
    parser.add_argument("--output")
    args = parser.parse_args()
    per_move_ms = args.time_ms if args.time_ms is not None or args.total_time_sec is not None else 50.0
    records, summary = benchmark(
        load_agent(args.agent),
        list(range(args.start_seed, args.start_seed + args.seeds)),
        per_move_ms,
        total_budget_seconds=args.total_time_sec,
    )
    print(format_summary(summary))
    if args.output:
        save_json(args.output, records, summary)


if __name__ == "__main__":
    main()

