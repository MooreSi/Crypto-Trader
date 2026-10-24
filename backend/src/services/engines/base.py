"""What an engine hands to the executor.

An engine never places an order. It produces a `Signal`, stores it in its own
database, and -- only when its own live toggle is on -- passes it to
`trading/executor.py`, which runs the risk gates, sizes it and calls the
order service. That keeps the real-money surface to one file
(`trading/order_service.py`) whatever the number of engines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

ENGINE_NAMES = ("breakout", "reversal", "trend_pa")
DIRECTIONS = ("long", "short")


@dataclass
class Signal:
    engine: str
    coin: str
    direction: str
    entry: float
    stop: float
    created_at: float
    interval: str
    reason: str = ""
    features: dict = field(default_factory=dict)
    ml_score: Optional[float] = None     # probability of a winner, or None (no model)
    id: Optional[int] = None             # the row id in the engine's own database

    def __post_init__(self) -> None:
        if self.engine not in ENGINE_NAMES:
            raise ValueError(f"unknown engine {self.engine!r}")
        if self.direction not in DIRECTIONS:
            raise ValueError(f"direction must be long or short, not {self.direction!r}")
        if self.direction == "long" and not self.stop < self.entry:
            raise ValueError("a long's stop must be below its entry")
        if self.direction == "short" and not self.stop > self.entry:
            raise ValueError("a short's stop must be above its entry")

    @property
    def risk_fraction(self) -> float:
        return abs(self.entry - self.stop) / self.entry
