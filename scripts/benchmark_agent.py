from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
from game2048.benchmark import benchmark, format_summary, load_agent, save_json


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark one 2048 agent")
    parser.add_argument("--agent", default="student.agent:Agent")
    parser.add_argument("--seeds", type=int, default=10, help="number of sequential seeds")
    parser.add_argument("--start-seed", type=int, default=0)
    parser.add_argument("--time-ms", type=float, help="optional per-move cap in milliseconds")
    parser.add_argument("--total-time-sec", type=float, help="total agent thinking time per game")
    parser.add_argument("--strict-time", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    seeds = list(range(args.start_seed, args.start_seed + args.seeds))
    per_move_ms = args.time_ms if args.time_ms is not None or args.total_time_sec is not None else 50.0
    records, summary = benchmark(
        load_agent(args.agent),
        seeds,
        per_move_ms,
        args.strict_time,
        args.total_time_sec,
    )
    print(format_summary(summary))
    if args.output:
        save_json(args.output, records, summary)

