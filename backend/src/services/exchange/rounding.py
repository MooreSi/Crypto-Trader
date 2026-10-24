"""Hyperliquid's tick and lot rules, as pure functions.

Perpetuals (from the Hyperliquid docs, "Tick and lot size"):

* a **size** has at most `szDecimals` decimals;
* a **price** has at most 5 significant figures, and at most
  `6 - szDecimals` decimals. An integer price is always valid whatever its
  number of significant figures.

An order that breaks either rule is rejected by the exchange, so every price
and size goes through here before it is sent.

Size is always rounded **down**: rounding up could exceed the risk the
sizing step computed. Prices are rounded to the nearest valid tick, except
stops, which the caller rounds away from entry (`round_stop`) so a rounded
stop never sits closer to the entry than the one that was sized.
"""
from __future__ import annotations

import math

MAX_SIG_FIGS = 5
PERP_MAX_DECIMALS = 6

#: Hyperliquid rejects orders below $10 notional.
MIN_ORDER_NOTIONAL_USD = 10.0


def round_size(size: float, sz_decimals: int) -> float:
    factor = 10 ** sz_decimals
    return math.floor(abs(size) * factor + 1e-9) / factor


def price_decimals(price: float, sz_decimals: int) -> int:
    """How many decimals a valid price may carry at this magnitude."""
    max_dec = max(PERP_MAX_DECIMALS - sz_decimals, 0)
    if price <= 0:
        return max_dec
    int_digits = int(math.floor(math.log10(abs(price)))) + 1
    sig_dec = max(MAX_SIG_FIGS - int_digits, 0)
    return min(max_dec, sig_dec)


def round_price(price: float, sz_decimals: int) -> float:
    if price >= 10 ** MAX_SIG_FIGS:
        return float(round(price))  # integers are always valid
    return round(price, price_decimals(price, sz_decimals))


def round_stop(stop: float, entry: float, sz_decimals: int) -> float:
    """Round a stop to a valid tick, moving it away from entry, never toward."""
    dec = price_decimals(stop, sz_decimals)
    factor = 10 ** dec
    if stop < entry:   # long stop: round down
        return math.floor(stop * factor) / factor
    return math.ceil(stop * factor) / factor


def is_valid_price(price: float, sz_decimals: int) -> bool:
    return math.isclose(round_price(price, sz_decimals), price, rel_tol=0, abs_tol=1e-12)
