"""Virtual outcome tracking: would this signal have made money as traded?

Every signal is tracked whether it traded or not, against the same candles
the engine used, through the SAME exit plan the live trade gets: the owner's
TP ladder, the stop moved to entry after `breakeven_after_tp` TPs, and a
round-trip taker fee charged in R (`backtest/simulator.py` does the replay,
so the tracker and the Strategy Lab can never disagree). A signal that was
executed is replayed from its real fill (`fill`), not the price the engine
asked for. The label is 1 when the net result is above zero, else 0; that is
what each engine's model learns to predict.

Signals that neither stop nor finish within `MAX_BARS` expire with label 0:
a setup that goes nowhere for two days was not a good one.

A bar that touches both a target and the stop is scored as the stop: from
OHLC alone the order inside the bar is unknown, and assuming the good outcome
would teach the model to trust exactly the volatile bars that hurt most.

`LABEL_VERSION` names the rule. Version 1 was "+1R before -1R" from the
signal price, before fees; it called signals winners that the 3R take-profit
never paid. Labels from an older rule are re-scored while their candles are
still held, and are never trained on otherwise.
"""
from __future__ import annotations

from typing import Sequence

from backend.src.services.backtest import simulator
from backend.src.services.exchange.types import Candle
from backend.src.services.risk.sizing import r_multiple

MAX_BARS = 192          # 2 days of 15m bars, 8 days of 1h bars
LABEL_VERSION = 2


def evaluate(signal: dict, bars_after: Sequence[Candle], plan: dict) -> dict:
    """Outcome so far for one tracking signal, given the closed bars after it.

    `plan` holds `tp_ladder`, `breakeven_after_tp`, `fee_rate` and optionally
    `stop_lock_r`.
    """
    direction, stop = signal["direction"], signal["stop"]
    entry = signal.get("fill") or signal["entry"]
    out = simulator.simulate(direction, entry, stop, bars_after, plan["tp_ladder"],
                             int(plan["breakeven_after_tp"]), plan["fee_rate"], MAX_BARS,
                             float(plan.get("stop_lock_r", 0.0)))
    mfe, mae = 0.0, 0.0
    for c in bars_after[:out["exit_index"] + 1]:      # excursions up to the exit, not past it
        mfe = max(mfe, r_multiple(direction, entry, stop, c.high if direction == "long" else c.low))
        mae = min(mae, r_multiple(direction, entry, stop, c.low if direction == "long" else c.high))
    if out["exit"] == "open":
        return {"status": "tracking", "mfe_r": mfe, "mae_r": mae}
    r = out["r"]
    status = "expired" if out["exit"] == "expired" else ("win" if r > 0 else "loss")
    return {"status": status, "label": 1 if status == "win" else 0, "r_final": r,
            "mfe_r": mfe, "mae_r": mae, "resolved_at": bars_after[out["exit_index"]].t / 1000,
            "exit": out["exit"]}
