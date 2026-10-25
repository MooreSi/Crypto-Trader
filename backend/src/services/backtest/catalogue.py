"""Every strategy the backtester can replay: the three engines plus the Lab.

| name            | bars | higher tf | source                                        |
|-----------------|------|-----------|-----------------------------------------------|
| breakout        | 15m  | -         | engine (live-capable)                         |
| reversal        | 15m  | 1d        | engine (live-capable)                         |
| trend_pa        | 1h   | 4h        | engine (live-capable)                         |
| donchian_trend  | 4h   | 1d        | Lab: time-series momentum, Donchian ensemble  |
| bb_rsi_revert   | 15m  | -         | Lab: Bollinger + RSI range reversion          |
| supertrend_flip | 1h   | 4h        | Lab: Supertrend flip with EMA200              |

**Lab strategies cannot trade.** They are not in `engines/registry.py`, have
no signal database, no model and no live toggle; the only thing that runs
them is the backtester. Promoting one to an engine is an owner decision.
"""
from __future__ import annotations

from typing import Callable, NamedTuple, Optional, Sequence

from backend.src.services.breakout import generator as breakout
from backend.src.services.engines.service import Setup
from backend.src.services.exchange.types import Candle
from backend.src.services.reversal import generator as reversal
from backend.src.services.strategies import bb_rsi_revert, donchian_trend, supertrend_flip
from backend.src.services.trend_pa import generator as trend_pa


class Strategy(NamedTuple):
    name: str
    interval: str
    htf: Optional[str]
    generate: Callable[[Sequence[Candle], Sequence[Candle]], list[Setup]]
    kind: str
    about: str
    #: Values the walk-forward tuner may try for each tunable constant (Lab only).
    grid: dict = {}
    #: The constants' values when untuned (the strategy module's DEFAULTS).
    defaults: dict = {}


STRATEGIES: dict[str, Strategy] = {s.name: s for s in (
    Strategy("breakout", "15m", None, breakout.generate, "engine",
             "Tight range broken on volume, or broken then retested."),
    Strategy("reversal", "15m", "1d", reversal.generate, "engine",
             "ICT liquidity sweep of a key level, then a market structure shift."),
    Strategy("trend_pa", "1h", "4h", trend_pa.generate, "engine",
             "Pullback to EMA20 in an EMA20/50/200 trend with a rejection wick."),
    Strategy("donchian_trend", "4h", "1d", donchian_trend.generate, "lab",
             "Time-series momentum: fresh 20-bar Donchian break confirmed by a 20/55/100 "
             "ensemble, 2 ATR stop (Turtle rules).",
             {"ENTRY_N": [20, 30, 55], "STOP_ATR": [1.5, 2.0, 3.0]}, donchian_trend.DEFAULTS),
    Strategy("bb_rsi_revert", "15m", None, bb_rsi_revert.generate, "lab",
             "Mean reversion: oversold/overbought flush outside Bollinger(20,2) with RSI "
             "30/70, in a low-ADX range, closing back inside.",
             {"RSI_BAND": [25.0, 30.0, 35.0], "MAX_ADX": [20.0, 25.0, 30.0]}, bb_rsi_revert.DEFAULTS),
    Strategy("supertrend_flip", "1h", "4h", supertrend_flip.generate, "lab",
             "Supertrend(10,3) flip in the direction of EMA200; 4h Supertrend as a feature.",
             {"ST_PERIOD": [10, 14], "ST_MULT": [2.0, 3.0, 4.0]}, supertrend_flip.DEFAULTS),
)}


def get(name: str) -> Strategy:
    if name not in STRATEGIES:
        raise ValueError(f"unknown strategy {name!r}; one of {sorted(STRATEGIES)}")
    return STRATEGIES[name]


def describe() -> list[dict]:
    return [{"name": s.name, "interval": s.interval, "htf": s.htf, "kind": s.kind,
             "about": s.about, "grid": s.grid, "defaults": s.defaults} for s in STRATEGIES.values()]
