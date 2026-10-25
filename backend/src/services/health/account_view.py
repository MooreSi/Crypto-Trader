"""Read-only views of the account and markets for the dashboard."""
from __future__ import annotations

from dataclasses import asdict

from backend.src.services.exchange import provider
from backend.src.services.market import candles as candle_src
from backend.src.services.market import pulse as market_pulse
from backend.src.services.market import universe
from backend.src.services.positions import trades_repo
from backend.src.services.risk import day, settings as risk_settings
from backend.src.utils import clock


def account() -> dict:
    client = provider.get()
    acc = client.account()
    start = day.start_equity(acc.equity)
    return {
        "network": client.network,
        "equity": acc.equity, "available": acc.available, "margin_used": acc.margin_used,
        "day_start_equity": start, "day_pnl": acc.equity - start,
        "realised_today": trades_repo.realised_since(day.start_ts()),
        "positions": [asdict(p) | {"direction": p.direction} for p in acc.positions],
        "open_orders": [asdict(o) for o in client.open_orders()],
    }


def equity_curve(days: int = 30) -> list[dict]:
    return trades_repo.equity_curve(clock.now() - days * 86400)


def markets() -> list[dict]:
    client = provider.get()
    snaps = client.snapshots()
    meta = {m.coin: m for m in client.markets()}
    selected = set(universe.select(snaps, risk_settings.get()))
    out = []
    for s in sorted(snaps, key=lambda x: x.day_notional_volume, reverse=True):
        m = meta.get(s.coin)
        out.append(asdict(s) | {
            "change_24h_pct": s.change_24h_pct, "scanned": s.coin in selected,
            "max_leverage": m.max_leverage if m else None,
            "only_isolated": m.only_isolated if m else None,
        })
    return out


def chart(coin: str, interval: str, bars: int) -> list[dict]:
    if interval not in candle_src.INTERVAL_MS:
        raise ValueError(f"interval must be one of {list(candle_src.INTERVAL_MS)}")
    rows = candle_src.fetch(provider.get(), coin, interval, min(max(bars, 10), 1000))
    return [asdict(c) for c in rows]


def pulse() -> dict:
    return market_pulse.summarise(provider.get().snapshots(), top_n=30)
