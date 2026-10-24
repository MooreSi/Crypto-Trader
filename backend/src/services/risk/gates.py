"""The gates a signal must pass before it may become a real order.

Run in order; the first failure stops the run, and every result -- passes
included -- is recorded with the decision, so any refusal can be explained
afterwards. Pure functions over a `GateContext`: no I/O here, which is what
lets every gate be tested on its own.

Order matters only for the explanation (the first reason given), never for
the outcome: a signal is placed only if all pass.

1. master switch      `trading_enabled`
2. freshness          the signal is from the latest closed bar
3. ML                 the engine's model scores it at least `ml_min_probability`
4. reward:risk        the TP ladder's weighted R is at least `min_reward_risk`
5. one per coin       no open trade on this coin already
6. max positions      fewer than `max_open_positions` open
7. correlation cap    fewer than `max_same_direction` open the same way
                      (crypto moves together: five longs are one bet on BTC)
8. funding            not paying more than `max_funding_rate_pct` an hour
9. event blackout     no high-impact event for this coin inside the window
10. daily loss limit  today's P&L is above -`daily_loss_limit_pct` of the day's start
11. daily target      today's realised P&L is below `daily_profit_target_usd` (0 = off)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.src.services.engines.base import Signal

#: How old a signal may be when it reaches the gates, in bars of its interval.
MAX_SIGNAL_AGE_BARS = 1.5


@dataclass
class GateContext:
    now: float
    settings: dict
    open_trades: list[dict]
    interval_seconds: float
    funding_rate: Optional[float]          # hourly, signed (+ longs pay)
    blackout_event: Optional[dict]
    day_start_equity: float
    equity: float
    realised_today: float
    ml_has_model: bool


@dataclass
class GateResult:
    passed: bool
    decisions: list[dict] = field(default_factory=list)

    @property
    def reason(self) -> str:
        for d in self.decisions:
            if not d["passed"]:
                return f"{d['gate']}: {d['detail']}"
        return ""


def weighted_r(ladder: list[list[float]]) -> float:
    """Expected R if every TP fills: sum(R x fraction) / sum(fraction)."""
    total = sum(f for _, f in ladder)
    return sum(r * f for r, f in ladder) / total if total else 0.0


def _checks(sig: Signal, ctx: GateContext):
    s = ctx.settings
    yield "trading enabled", bool(s.get("trading_enabled")), "master switch is off"

    age = ctx.now - sig.created_at
    yield ("fresh", age <= MAX_SIGNAL_AGE_BARS * ctx.interval_seconds,
           f"signal is {age / 60:.0f} min old")

    threshold = float(s["ml_min_probability"])
    if sig.ml_score is None:
        ok = not s.get("ml_require_model") or ctx.ml_has_model
        yield "ML", ok, "no trained model and ml_require_model is on"
    else:
        yield "ML", sig.ml_score >= threshold, f"score {sig.ml_score:.2f} < {threshold:.2f}"

    rr = weighted_r(s["tp_ladder"])
    yield "reward:risk", rr >= float(s["min_reward_risk"]), \
        f"ladder pays {rr:.2f}R < {float(s['min_reward_risk']):.2f}R"

    coins = [t["coin"] for t in ctx.open_trades]
    yield "one per coin", sig.coin not in coins, f"{sig.coin} already has an open trade"

    yield ("max positions", len(ctx.open_trades) < int(s["max_open_positions"]),
           f"{len(ctx.open_trades)} open (max {s['max_open_positions']})")

    same = sum(1 for t in ctx.open_trades if t["direction"] == sig.direction)
    yield ("correlation cap", same < int(s["max_same_direction"]),
           f"{same} {sig.direction}s open (max {s['max_same_direction']})")

    limit = float(s["max_funding_rate_pct"]) / 100.0
    rate = ctx.funding_rate or 0.0
    paying = rate if sig.direction == "long" else -rate
    yield "funding", paying <= limit, f"would pay {paying * 100:.4f}%/h"

    ev = ctx.blackout_event
    yield "event blackout", ev is None, f"{ev['title']}" if ev else ""

    floor = -ctx.day_start_equity * float(s["daily_loss_limit_pct"]) / 100.0
    day_pnl = ctx.equity - ctx.day_start_equity
    yield "daily loss limit", day_pnl > floor, \
        f"today {day_pnl:+.2f} USDC, limit {floor:.2f}"

    target = float(s["daily_profit_target_usd"])
    yield ("daily target", target <= 0 or ctx.realised_today < target,
           f"target {target:.2f} reached ({ctx.realised_today:+.2f})")


def evaluate(sig: Signal, ctx: GateContext) -> GateResult:
    result = GateResult(passed=True)
    for name, ok, detail in _checks(sig, ctx):
        result.decisions.append({"gate": name, "passed": bool(ok), "detail": "" if ok else detail})
        if not ok:
            result.passed = False
            break
    return result
