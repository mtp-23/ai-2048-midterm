from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
from game2048.ui_tk import launch


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Open the 2048 AI Arena")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--agent", help="Optional package.module:AgentClass")
    args = parser.parse_args()
    launch(args.seed, agent_spec=args.agent)

