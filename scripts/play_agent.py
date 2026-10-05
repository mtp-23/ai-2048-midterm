from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
from game2048.ui_tk import launch


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Watch an agent play 2048")
    parser.add_argument("--agent", default="student.agent:Agent")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    launch(args.seed, agent_spec=args.agent)

