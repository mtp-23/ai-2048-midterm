from __future__ import annotations

from typing import Protocol

from .observation import Observation
from .types import Move


class AgentProtocol(Protocol):
    name: str

    def reset(self, seed: int | None = None) -> None: ...

    def choose_move(self, obs: Observation, time_limit_ms: float) -> Move: ...

