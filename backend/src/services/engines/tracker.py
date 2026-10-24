"""Virtual outcome tracking: did each signal reach +1R before -1R?

Every signal is tracked whether it traded or not, against the same candles
the engine used. That label -- reached +1R first (1) or the stop first (0) --
is what each engine's model learns to predict. Signals that do neither
within `MAX_BARS` expire with label 0: a setup that goes nowhere for two days
was not a good one.

A bar that touches both +1R and the stop is scored as a LOSS: from OHLC
alone the order inside the bar is unknown, and assuming the good outcome
would teach the model to trust exactly the volatile bars that hurt most.
"""
from __future__ import annotations

from typing import Sequence

from backend.src.services.exchange.types import Candle
from backend.src.services.risk.sizing import r_multiple

MAX_BARS = 192          # 2 days of 15m bars, 8 days of 1h bars
TARGET_R = 1.0


def evaluate(signal: dict, bars_after: Sequence[Candle]) -> dict:
    """Outcome so far for one tracking signal, given the closed bars after it."""
    direction, entry, stop = signal["direction"], signal["entry"], signal["stop"]
    mfe, mae = signal.get("mfe_r") or 0.0, signal.get("mae_r") or 0.0
    for i, c in enumerate(bars_after):
        best = c.high if direction == "long" else c.low
        worst = c.low if direction == "long" else c.high
        mfe = max(mfe, r_multiple(direction, entry, stop, best))
        mae = min(mae, r_multiple(direction, entry, stop, worst))
        stopped = mae <= -1.0
        won = mfe >= TARGET_R
        if stopped:
            return {"status": "loss", "label": 0, "r_final": -1.0, "mfe_r": mfe, "mae_r": mae,
                    "resolved_at": (c.t / 1000)}
        if won:
            return {"status": "win", "label": 1, "r_final": TARGET_R, "mfe_r": mfe, "mae_r": mae,
                    "resolved_at": (c.t / 1000)}
        if i + 1 >= MAX_BARS:
            return {"status": "expired", "label": 0,
                    "r_final": r_multiple(direction, entry, stop, c.close),
                    "mfe_r": mfe, "mae_r": mae, "resolved_at": (c.t / 1000)}
    return {"status": "tracking", "mfe_r": mfe, "mae_r": mae}
