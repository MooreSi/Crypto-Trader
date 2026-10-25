"""Account, positions and market views."""
from __future__ import annotations

from backend.src.services.health import account_view


def account() -> dict:
    return account_view.account()


def equity_curve(days: int) -> list[dict]:
    return account_view.equity_curve(days)


def markets() -> list[dict]:
    return account_view.markets()


def chart(coin: str, interval: str, bars: int) -> list[dict]:
    return account_view.chart(coin, interval, bars)


def pulse() -> dict:
    return account_view.pulse()
