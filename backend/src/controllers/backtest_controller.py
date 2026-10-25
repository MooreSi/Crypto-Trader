"""Strategy Lab: the strategy catalogue, backtests and walk-forward tuning (read-only)."""
from __future__ import annotations

from backend.src.services.backtest import catalogue, runner, tuning


def strategies() -> list[dict]:
    return catalogue.describe()


def run(strategy: str, coin: str, bars: int) -> dict:
    return runner.run(strategy, coin, bars)


def tune(strategy: str, coin: str, bars: int, folds: int) -> dict:
    return tuning.run(strategy, coin, bars, folds)
