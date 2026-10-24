"""Position size from risk, deterministically.

    size = (equity * risk_pct) / |entry - stop|

then capped so the position's notional never exceeds `max_position_notional_pct`
of equity, rounded DOWN to the market's lot size, and refused if the result
is below Hyperliquid's $10 minimum order value.

**Leverage does not set the risk -- the stop does.** Leverage only sets how
much margin is locked and how close liquidation sits. So the leverage chosen
is the highest allowed (by the setting and the market) at which the isolated
position's liquidation price stays beyond the stop with `LIQ_BUFFER` to
spare, and the margin it locks must fit in the free balance.

Liquidation distance at leverage L is approximated as `1/L - mm`, with the
maintenance margin `mm = 1 / (2 * market max leverage)` (Hyperliquid sets
maintenance margin at half the initial margin at max leverage). Fees and
funding move the real liquidation price slightly, which the buffer absorbs.

A cap can only make a position smaller, so the risk actually taken is at
most the risk asked for -- never more. **Golden rule 5: no clever maths
here.** Do not reorder, "tidy" or re-round this; a change shows up as
missing cents that compound.
"""
from __future__ import annotations


from dataclasses import dataclass

from backend.src.services.exchange import rounding
from backend.src.services.exchange.types import Market

#: Liquidation must sit at least this many stop-distances from entry.
LIQ_BUFFER = 1.5


@dataclass(frozen=True)
class SizeDecision:
    ok: bool
    size: float = 0.0
    leverage: int = 1
    risk_usd: float = 0.0
    notional: float = 0.0
    margin: float = 0.0
    reason: str = ""


def safe_leverage(market: Market, stop_fraction: float, cap: int) -> int:
    """Highest leverage <= cap whose liquidation stays LIQ_BUFFER stops away."""
    mm = 1.0 / (2.0 * max(market.max_leverage, 1))
    top = max(1, min(int(cap), int(market.max_leverage)))
    for lev in range(top, 0, -1):
        if 1.0 / lev - mm >= stop_fraction * LIQ_BUFFER:
            return lev
    return 0


def compute(market: Market, equity: float, available: float, entry: float, stop: float,
            settings: dict) -> SizeDecision:
    if equity <= 0:
        return SizeDecision(False, reason="no equity")
    distance = abs(entry - stop)
    if distance <= 0 or entry <= 0:
        return SizeDecision(False, reason="stop distance is zero")
    leverage = safe_leverage(market, distance / entry, int(settings["max_leverage"]))
    if leverage == 0:
        return SizeDecision(False, reason="stop is too wide for any leverage to keep "
                                          "liquidation beyond it")

    risk_usd = equity * float(settings["risk_per_trade_pct"]) / 100.0
    size = risk_usd / distance

    max_notional = equity * float(settings["max_position_notional_pct"]) / 100.0
    if size * entry > max_notional:
        size = max_notional / entry

    size = rounding.round_size(size, market.sz_decimals)
    notional = size * entry
    if size <= 0 or notional < rounding.MIN_ORDER_NOTIONAL_USD:
        return SizeDecision(False, reason=f"size below the ${rounding.MIN_ORDER_NOTIONAL_USD:.0f} "
                                          f"minimum order (notional ${notional:.2f})")
    margin = notional / leverage
    if margin > available:
        return SizeDecision(False, reason=f"needs ${margin:.2f} margin, ${available:.2f} free")
    return SizeDecision(True, size=size, leverage=leverage, risk_usd=size * distance,
                        notional=notional, margin=margin)


def r_multiple(direction: str, entry: float, stop: float, price: float) -> float:
    risk = abs(entry - stop)
    if risk == 0:
        return 0.0
    move = (price - entry) if direction == "long" else (entry - price)
    return move / risk


def tp_price(direction: str, entry: float, stop: float, r: float) -> float:
    risk = abs(entry - stop)
    return entry + r * risk if direction == "long" else entry - r * risk


