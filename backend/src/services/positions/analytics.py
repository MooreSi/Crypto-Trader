"""Performance analytics for closed trades: the numbers serious bots report.

Profit factor, expectancy in R, win rate, average win and loss, longest
losing streak and holding time, per engine and overall; maximum drawdown and
an annualised Sharpe ratio from the equity snapshots.

* Net P&L of a trade is `realised_pnl - fees` (fees include the entry fee).
* R of a trade is net / `risk_usd` (the money at risk when it opened).
* Sharpe uses the last equity of each UTC day, daily returns, sample
  standard deviation, x sqrt(365) (crypto trades every day). It needs at
  least two daily returns; deposits and withdrawals are not separated out,
  so a transfer reads as a return.

Pure: the caller passes the rows.
"""
from __future__ import annotations

import math
from typing import Optional


def _net(t: dict) -> float:
    return (t.get("realised_pnl") or 0.0) - (t.get("fees") or 0.0)


def _block(trades: list[dict]) -> dict:
    nets = [_net(t) for t in trades]
    n = len(nets)
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x <= 0]
    gain, loss = sum(wins), -sum(x for x in losses if x < 0)
    rs = [_net(t) / t["risk_usd"] for t in trades if t.get("risk_usd")]
    return {
        "trades": n, "wins": len(wins), "win_rate": len(wins) / n if n else None,
        "net_pnl": sum(nets),
        "profit_factor": gain / loss if gain > 0 and loss > 0 else None,
        "expectancy_r": sum(rs) / len(rs) if rs else None,
    }


def _max_drawdown_pct(equity: list[dict]) -> float:
    peak, worst = 0.0, 0.0
    for p in equity:
        e = float(p["equity"])
        peak = max(peak, e)
        if peak > 0:
            worst = max(worst, (peak - e) / peak * 100.0)
    return worst


def _sharpe(equity: list[dict]) -> Optional[float]:
    by_day: dict[int, float] = {}
    for p in sorted(equity, key=lambda x: x["ts"]):
        by_day[int(p["ts"] // 86400)] = float(p["equity"])
    closes = [by_day[d] for d in sorted(by_day)]
    rets = [b / a - 1.0 for a, b in zip(closes, closes[1:]) if a > 0]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1))
    return mean / sd * math.sqrt(365) if sd > 0 else None


def _losing_streak(trades: list[dict]) -> int:
    best = cur = 0
    for t in sorted(trades, key=lambda x: x.get("closed_at") or 0):
        cur = cur + 1 if _net(t) <= 0 else 0
        best = max(best, cur)
    return best


def compute(trades: list[dict], equity: list[dict]) -> dict:
    closed = [t for t in trades if t.get("status") == "closed"]
    head = _block(closed)
    nets = [_net(t) for t in closed]
    wins, losses = [x for x in nets if x > 0], [x for x in nets if x <= 0]
    holds = [(t["closed_at"] - t["opened_at"]) / 3600 for t in closed
             if t.get("closed_at") is not None and t.get("opened_at") is not None]
    engines = sorted({t.get("engine") or "?" for t in closed})
    return {
        "closed": head["trades"], "net_pnl": head["net_pnl"], "win_rate": head["win_rate"],
        "profit_factor": head["profit_factor"], "expectancy_r": head["expectancy_r"],
        "avg_win": sum(wins) / len(wins) if wins else None,
        "avg_loss": sum(losses) / len(losses) if losses else None,
        "best": max(nets) if nets else None, "worst": min(nets) if nets else None,
        "longest_losing_streak": _losing_streak(closed),
        "avg_hold_hours": sum(holds) / len(holds) if holds else None,
        "max_drawdown_pct": _max_drawdown_pct(equity), "sharpe": _sharpe(equity),
        "by_engine": {e: _block([t for t in closed if (t.get("engine") or "?") == e])
                      for e in engines},
    }
