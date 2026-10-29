"""Babysits open trades: notices exchange-side exits, moves stops.

Runs every few seconds. For each open trade it compares the database with
the exchange:

* **position gone** -- the stop, the last TP, a liquidation or a manual close
  on the exchange closed it. The exits are read back from the exchange's
  fills and the trade is recorded closed (`reconciled`), leftover triggers
  cancelled.
* **position smaller** -- a TP trigger filled. The partial is recorded from
  the fills, the stop is resized to what is left, and after
  `breakeven_after_tp` TPs the stop moves to the entry price, or
  `stop_lock_r` x the initial risk past it when that is on the safe side of
  the mid, unless it is already tighter (a trailed stop is never loosened).
  A TP ladder adding up to less than 1 leaves a runner with no TP, which
  only the stop and the trail exit.
* **trailing** -- once TP1 has filled and `trail_atr_mult` > 0, the stop
  follows price at that many ATRs, and only ever tightens.

Positions on the account that this app did not open are listed on the
dashboard and NEVER touched: the owner may trade the same account by hand.
"""
from __future__ import annotations

import logging
from typing import Optional

from backend.src.services.exchange import rounding
from backend.src.services.exchange.types import AccountState, ExchangeClient, Fill, Market
from backend.src.services.market import candles, indicators
from backend.src.services.positions import trades_repo
from backend.src.services.risk import settings as risk_settings
from backend.src.services.trading import order_service
from backend.src.utils import clock

log = logging.getLogger(__name__)

TRAIL_INTERVAL = "15m"


def _exit_fills(client: ExchangeClient, trade: dict) -> list[Fill]:
    """Fills that reduced this trade's position since it opened."""
    closing_buy = trade["direction"] == "short"
    start_ms = int(trade["opened_at"] * 1000)
    return [f for f in client.fills_since(start_ms)
            if f.coin == trade["coin"] and f.is_buy == closing_buy]


def _book_from_fills(fills: list[Fill], trade: dict, size: float) -> tuple[float, float, float]:
    """(avg price, gross pnl, fee) for `size` of exits, newest fills last."""
    take, remaining = [], size
    for f in reversed(fills):
        if remaining <= 1e-12:
            break
        part = min(f.size, remaining)
        take.append((f, part))
        remaining -= part
    if not take:
        return 0.0, 0.0, 0.0
    sign = 1 if trade["direction"] == "long" else -1
    qty = sum(p for _, p in take)
    avg = sum(f.price * p for f, p in take) / qty
    pnl = sum((f.price - trade["entry_price"]) * p * sign for f, p in take)
    fee = sum(f.fee * (p / f.size) for f, p in take if f.size)
    return avg, pnl, fee


def _exit_reason(trade: dict, fills: list[Fill]) -> str:
    oids = {f.oid for f in fills}
    if trade.get("sl_oid") in oids:
        at_entry = abs(trade["stop_loss"] - trade["entry_price"]) <= trade["entry_price"] * 1e-4
        if trade["tp_hit"] and at_entry:
            return "breakeven stop"
        sign = 1 if trade["direction"] == "long" else -1
        in_profit = (trade["stop_loss"] - trade["entry_price"]) * sign > 0
        return "stop in profit" if trade["tp_hit"] and in_profit else "stop loss"
    hit = [i + 1 for i, o in enumerate(trade.get("tp_oids") or []) if o and o in oids]
    if hit:
        return f"TP{max(hit)}"
    return "closed on exchange"


def _reconcile_gone(client: ExchangeClient, trade: dict) -> None:
    fills = _exit_fills(client, trade)
    price, pnl, fee = _book_from_fills(fills, trade, trade["size"])
    reason = _exit_reason(trade, fills)
    order_service.cancel_exits(client, trade)
    if not price:
        price = trade["stop_loss"]
        reason = "closed on exchange (no fill found)"
    trades_repo.update(trade["id"], {
        "status": "closed",
        "closed_at": max(f.time_ms for f in fills) / 1000 if fills else clock.now(),
        "close_price": price, "close_reason": reason, "size": 0.0,
        "realised_pnl": trade["realised_pnl"] + pnl, "fees": trade["fees"] + fee,
    }, "reconciled", {"price": price, "pnl": pnl, "fee": fee, "reason": reason})
    log.info("[Positions] #%d %s closed on exchange: %s pnl %+.2f", trade["id"], trade["coin"],
             reason, pnl - fee)


def _reconcile_partial(client: ExchangeClient, trade: dict, live_size: float,
                       market: Market, settings: dict, mid: Optional[float]) -> dict:
    filled = trade["size"] - live_size
    fills = _exit_fills(client, trade)
    price, pnl, fee = _book_from_fills(fills, trade, filled)
    open_oids = {o.oid for o in client.open_orders() if o.coin == trade["coin"]}
    tp_hit = sum(1 for o in trade["tp_oids"] if o and o not in open_oids)
    trades_repo.update(trade["id"], {"size": live_size, "tp_hit": tp_hit,
                                     "realised_pnl": trade["realised_pnl"] + pnl,
                                     "fees": trade["fees"] + fee},
                       "partial", {"price": price, "size": filled, "pnl": pnl, "fee": fee,
                                   "reason": f"TP{tp_hit}"})
    fresh = trades_repo.get(trade["id"])
    be_after = int(settings["breakeven_after_tp"])
    new_stop = fresh["stop_loss"]
    reason = "breakeven"
    if be_after and tp_hit >= be_after:
        # The fill price is rarely a valid tick (an average of several fills);
        # the stop must be one, or the exchange refuses it.
        be = rounding.round_price(fresh["entry_price"], market.sz_decimals)
        lock = _lock_price(fresh, market, mid, float(settings["stop_lock_r"]))
        if lock is not None:
            be, reason = lock, f"lock {float(settings['stop_lock_r']):g}R"
        # Only ever tighten: a stop the trail already moved into profit stays.
        if _tighter(fresh["direction"], be, fresh["stop_loss"]):
            new_stop = be
    order_service.move_stop(client, fresh, new_stop, live_size,
                            reason if new_stop != fresh["stop_loss"] else "resize after TP")
    return trades_repo.get(trade["id"])


def _lock_price(trade: dict, market: Market, mid: Optional[float], lock_r: float) -> Optional[float]:
    """The stop `lock_r` x the initial risk past entry, or None to use entry.

    None when the lock is off, or when the price is not strictly on the safe
    side of the mid: a stop there would fire at once."""
    if lock_r <= 0 or mid is None:
        return None
    sign = 1 if trade["direction"] == "long" else -1
    target = trade["entry_price"] + sign * lock_r * abs(trade["entry_price"] - trade["initial_stop"])
    price = rounding.round_stop(target, mid, market.sz_decimals)   # rounded away from the mid
    safe = price < mid if trade["direction"] == "long" else price > mid
    return price if safe else None


def _tighter(direction: str, candidate: float, current: float) -> bool:
    """Is `candidate` a tighter stop than `current` (closer to price, less risk)?"""
    return candidate > current if direction == "long" else candidate < current


def _trail(client: ExchangeClient, trade: dict, market: Market, mid: Optional[float],
           settings: dict) -> None:
    mult = float(settings["trail_atr_mult"])
    if mult <= 0 or trade["tp_hit"] < 1 or mid is None:
        return
    a = indicators.atr(candles.closed(client, trade["coin"], TRAIL_INTERVAL, 60), 14)
    if not a:
        return
    if trade["direction"] == "long":
        cand = rounding.round_stop(mid - mult * a, mid, market.sz_decimals)
        better = cand > trade["stop_loss"]
    else:
        cand = rounding.round_stop(mid + mult * a, mid, market.sz_decimals)
        better = cand < trade["stop_loss"]
    if better:
        order_service.move_stop(client, trade, cand, trade["size"], f"trail {mult}xATR")


def manage(client: ExchangeClient, account: Optional[AccountState] = None) -> dict:
    """One pass over every open trade. Returns a small summary for the status page."""
    trades = trades_repo.open_trades()
    if not trades:
        return {"managed": 0, "unmanaged_positions": _unmanaged(account, trades)}
    settings = risk_settings.get()
    account = account or client.account()
    markets = {m.coin: m for m in client.markets()}
    mids = client.mids()
    for trade in trades:
        try:
            pos = account.position(trade["coin"])
            if pos is None or (pos.size > 0) != (trade["direction"] == "long"):
                _reconcile_gone(client, trade)
                continue
            market = markets[trade["coin"]]
            live = rounding.round_size(abs(pos.size), market.sz_decimals)
            if live < trade["size"] - 10 ** -market.sz_decimals / 2:
                trade = _reconcile_partial(client, trade, live, market, settings,
                                           mids.get(trade["coin"]))
            _trail(client, trade, market, mids.get(trade["coin"]), settings)
        except Exception as exc:
            log.exception("[Positions] managing #%s failed: %s", trade.get("id"), exc)
    return {"managed": len(trades), "unmanaged_positions": _unmanaged(account, trades)}


def _unmanaged(account: Optional[AccountState], trades: list[dict]) -> list[str]:
    if account is None:
        return []
    mine = {t["coin"] for t in trades}
    return [p.coin for p in account.positions if p.coin not in mine]
