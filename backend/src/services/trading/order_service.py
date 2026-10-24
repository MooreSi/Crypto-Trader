"""THE real-money surface. Every order this app sends starts here.

Nothing else may call an `ExchangeClient`'s `place_*`, `cancel` or
`set_leverage` -- enforced by the import-contract gate, which allows only
this module to name them.

Three promises this file keeps, in this order of importance:

1. **No unprotected position.** The stop is placed straight after the entry
   fills. If it cannot be placed, the position is closed at market at once.
   A stop is moved by placing the new one BEFORE cancelling the old, so there
   is never a moment with no stop (both are reduce-only, so two firing
   together cannot open a position the other way).
2. **The exchange holds the exits.** Stop and take-profits are
   exchange-native trigger orders, so a position is protected while the app
   is closed, asleep or crashed. The app only adds what the exchange cannot:
   breakeven and trailing moves.
3. **Every change is recorded** in `trade_events` in the same transaction as
   the trade row it changes.

**The close path is frozen from v0.1:** `close_trade`, `partial_close_trade`
and `record_close` may be moved verbatim, never reshaped (no argument added,
removed, reordered or defaulted, no branch restructured) without the owner's
sign-off and a testnet session. tests/trading/test_close_path_characterization.py
is the witness and must pass unmodified. Golden rule 2.
"""
from __future__ import annotations

import logging
from typing import Optional

from backend.src.services.engines.base import Signal
from backend.src.services.exchange import rounding
from backend.src.services.exchange.types import ExchangeClient, Market, OrderResult
from backend.src.services.positions import trades_repo
from backend.src.services.risk.sizing import SizeDecision, tp_price
from backend.src.utils import clock

log = logging.getLogger(__name__)

#: Fee estimate when the exchange's own fill record cannot be read back:
#: Hyperliquid's base-tier taker fee. Reconciliation replaces it with the
#: real fee whenever the fill is found.
TAKER_FEE_ESTIMATE = 0.00045
#: Max adverse slippage for app-initiated market closes.
CLOSE_SLIPPAGE = 0.02


class OrderRefused(RuntimeError):
    pass


def _dir_sign(direction: str) -> int:
    return 1 if direction == "long" else -1


def _fill_cost(client: ExchangeClient, coin: str, result: OrderResult, since_ms: int) -> tuple[float, Optional[float]]:
    """(fee, closed_pnl) for one market order, from the exchange's fills when possible."""
    try:
        fills = [f for f in client.fills_since(since_ms) if f.coin == coin and f.oid == result.oid]
    except Exception:
        fills = []
    if fills:
        return sum(f.fee for f in fills), sum(f.closed_pnl for f in fills)
    est = (result.avg_price or 0.0) * result.filled_size * TAKER_FEE_ESTIMATE
    return est, None


def _place_stop(client: ExchangeClient, coin: str, direction: str, size: float, stop: float) -> OrderResult:
    return client.place_trigger(coin, direction == "short", size, stop, "stop")


def _place_tps(client: ExchangeClient, market: Market, direction: str, size: float,
               entry: float, stop: float, ladder: list[list[float]]) -> tuple[list[float], list[Optional[int]]]:
    """Place one reduce-only TP trigger per ladder rung. The last rung takes the
    remainder so rounding never leaves a sliver with no exit but the stop."""
    prices, oids = [], []
    remaining = size
    for i, (r, frac) in enumerate(ladder):
        price = rounding.round_price(tp_price(direction, entry, stop, r), market.sz_decimals)
        part = remaining if i == len(ladder) - 1 else rounding.round_size(size * frac, market.sz_decimals)
        part = min(part, remaining)
        prices.append(price)
        if part <= 0:
            oids.append(None)
            continue
        res = client.place_trigger(market.coin, direction == "short", part, price, "take_profit")
        oids.append(res.oid if res.ok else None)
        if not res.ok:
            log.warning("[Orders] TP%d for %s refused: %s", i + 1, market.coin, res.error)
        remaining = rounding.round_size(remaining - part, market.sz_decimals)
    return prices, oids


def open_trade(client: ExchangeClient, market: Market, sig: Signal, decision: SizeDecision,
               settings: dict, gate_decisions: list[dict]) -> int:
    """Enter at market, protect with a stop, ladder the take-profits, record it."""
    coin, direction = sig.coin, sig.direction
    client.set_leverage(coin, decision.leverage, cross=not settings.get("isolated_margin", True))
    started_ms = clock.now_ms()
    entry_res = client.place_market(coin, direction == "long", decision.size,
                                    float(settings["entry_slippage_pct"]) / 100.0)
    if not entry_res.ok or entry_res.filled_size <= 0:
        raise OrderRefused(f"entry not filled: {entry_res.error or 'IOC expired unfilled'}")

    size = entry_res.filled_size
    fill = float(entry_res.avg_price or sig.entry)
    stop = rounding.round_stop(sig.stop, fill, market.sz_decimals)
    if (direction == "long" and stop >= fill) or (direction == "short" and stop <= fill):
        _emergency_close(client, coin, direction, size, "fill slipped past the stop")
        raise OrderRefused("entry filled beyond the stop; closed at once")

    sl = _place_stop(client, coin, direction, size, stop)
    if not sl.ok:
        _emergency_close(client, coin, direction, size, f"stop refused: {sl.error}")
        raise OrderRefused(f"stop could not be placed ({sl.error}); position closed at once")

    tp_prices, tp_oids = _place_tps(client, market, direction, size, fill, stop, settings["tp_ladder"])
    fee, _ = _fill_cost(client, coin, entry_res, started_ms)
    trade = {
        "engine": sig.engine, "coin": coin, "direction": direction, "status": "open",
        "network": client.network, "signal_id": sig.id, "entry_price": fill, "size": size,
        "initial_size": size, "stop_loss": stop, "initial_stop": stop,
        "take_profits": tp_prices, "leverage": decision.leverage,
        "risk_usd": abs(fill - stop) * size, "sl_oid": sl.oid, "tp_oids": tp_oids,
        "opened_at": clock.now(), "fees": fee,
    }
    detail = {"signal_reason": sig.reason, "ml_score": sig.ml_score, "signal_entry": sig.entry,
              "fill": fill, "size": size, "leverage": decision.leverage,
              "risk_usd": trade["risk_usd"], "gates": gate_decisions, "fee": fee}
    trade_id = trades_repo.insert(trade, detail)
    log.info("[Orders] opened #%d %s %s %.6g @ %.6g stop %.6g (%s)", trade_id, direction, coin,
             size, fill, stop, sig.engine)
    return trade_id


def _emergency_close(client: ExchangeClient, coin: str, direction: str, size: float, why: str) -> None:
    log.error("[Orders] EMERGENCY close %s %s %.6g: %s", direction, coin, size, why)
    res = client.place_market(coin, direction == "short", size, CLOSE_SLIPPAGE, reduce_only=True)
    if not res.ok:
        log.critical("[Orders] emergency close of %s FAILED: %s -- position is UNPROTECTED",
                     coin, res.error)


def move_stop(client: ExchangeClient, trade: dict, new_stop: float, size: float, reason: str) -> bool:
    """Replace the stop: new one first, then cancel the old. False if refused."""
    res = _place_stop(client, trade["coin"], trade["direction"], size, new_stop)
    if not res.ok:
        log.warning("[Orders] stop move on #%d refused: %s", trade["id"], res.error)
        return False
    if trade.get("sl_oid"):
        client.cancel(trade["coin"], int(trade["sl_oid"]))
    trades_repo.update(trade["id"], {"stop_loss": new_stop, "sl_oid": res.oid}, "stop_moved",
                       {"from": trade["stop_loss"], "to": new_stop, "size": size, "reason": reason})
    return True


def cancel_exits(client: ExchangeClient, trade: dict) -> None:
    oids = [trade.get("sl_oid")] + list(trade.get("tp_oids") or [])
    for oid in oids:
        if oid:
            try:
                client.cancel(trade["coin"], int(oid))
            except Exception as exc:
                log.warning("[Orders] cancel %s on %s failed: %s", oid, trade["coin"], exc)


# ── the close path (frozen) ───────────────────────────────────────────────────

def close_trade(client: ExchangeClient, trade: dict, reason: str) -> bool:
    """Close everything left of `trade` at market and record it."""
    started_ms = clock.now_ms()
    res = client.place_market(trade["coin"], trade["direction"] == "short", trade["size"],
                              CLOSE_SLIPPAGE, reduce_only=True)
    if not res.ok or res.filled_size <= 0:
        log.error("[Orders] close of #%d refused: %s", trade["id"], res.error)
        return False
    cancel_exits(client, trade)
    price = float(res.avg_price or trade["entry_price"])
    fee, closed = _fill_cost(client, trade["coin"], res, started_ms)
    pnl = closed if closed is not None else \
        (price - trade["entry_price"]) * res.filled_size * _dir_sign(trade["direction"])
    record_close(trade, price, pnl, fee, reason)
    return True


def partial_close_trade(client: ExchangeClient, trade: dict, fraction: float, market: Market,
                        reason: str) -> bool:
    """Close `fraction` of the remaining size at market and resize the stop."""
    size = rounding.round_size(trade["size"] * fraction, market.sz_decimals)
    if size <= 0 or size >= trade["size"]:
        return close_trade(client, trade, reason)
    started_ms = clock.now_ms()
    res = client.place_market(trade["coin"], trade["direction"] == "short", size,
                              CLOSE_SLIPPAGE, reduce_only=True)
    if not res.ok or res.filled_size <= 0:
        log.error("[Orders] partial close of #%d refused: %s", trade["id"], res.error)
        return False
    price = float(res.avg_price or trade["entry_price"])
    fee, closed = _fill_cost(client, trade["coin"], res, started_ms)
    pnl = closed if closed is not None else \
        (price - trade["entry_price"]) * res.filled_size * _dir_sign(trade["direction"])
    remaining = rounding.round_size(trade["size"] - res.filled_size, market.sz_decimals)
    trades_repo.update(trade["id"], {"size": remaining,
                                     "realised_pnl": trade["realised_pnl"] + pnl,
                                     "fees": trade["fees"] + fee},
                       "partial", {"price": price, "size": res.filled_size, "pnl": pnl,
                                   "fee": fee, "reason": reason})
    fresh = trades_repo.get(trade["id"])
    move_stop(client, fresh, fresh["stop_loss"], remaining, "resize after partial")
    return True


def record_close(trade: dict, price: float, pnl: float, fee: float, reason: str) -> None:
    """Mark `trade` closed. `pnl` and `fee` are for the size closed by THIS exit only."""
    trades_repo.update(trade["id"], {
        "status": "closed", "closed_at": clock.now(), "close_price": price,
        "close_reason": reason, "size": 0.0,
        "realised_pnl": trade["realised_pnl"] + pnl, "fees": trade["fees"] + fee,
    }, "closed", {"price": price, "pnl": pnl, "fee": fee, "reason": reason})
    log.info("[Orders] closed #%d %s @ %.6g pnl %+.2f (%s)", trade["id"], trade["coin"], price,
             pnl - fee, reason)
