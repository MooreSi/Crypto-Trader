"""Paper trading: real Hyperliquid prices, simulated account.

Every read of market data (`markets`, `snapshots`, `mids`, `candles`,
`funding_history`) is passed straight through to a key-less mainnet
`HyperliquidClient`, so the engines see exactly what they would see live.
Orders, positions, stops and fills are simulated here and persisted through
`paper_repo`, so a paper account survives a restart.

What this does NOT simulate, and so where paper results will flatter live
ones -- say so whenever a paper number is quoted:

* **funding** is not charged or paid;
* **liquidation** is not modelled (the risk governor's leverage cap and
  stops are expected to keep a position far from it);
* **fills** are at the current mid plus `PAPER_SLIPPAGE`, with no order-book
  depth: a large order fills as easily as a small one;
* **triggers** are checked when the app polls (every few seconds), not on
  every tick, and fill at the worse of the trigger and the polled mid.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from backend.src.services.exchange import paper_repo, rounding
from backend.src.services.exchange.types import (
    AccountState, Candle, ExchangeError, Fill, Market, MarketSnapshot, OpenOrder,
    OrderResult, Position,
)
from backend.src.utils import clock

log = logging.getLogger(__name__)

#: Hyperliquid's base-tier perpetual taker fee (0.045%). Every paper fill is
#: charged as a taker: market entries and triggered stops both cross the book.
PAPER_TAKER_FEE = 0.00045
#: Adverse price move applied to every paper fill.
PAPER_SLIPPAGE = 0.0005


class PaperExchange:
    network = "paper"

    def __init__(self, data_source, starting_balance: float) -> None:
        self._src = data_source
        self._lock = threading.RLock()
        self._state = paper_repo.load() or self._fresh(starting_balance)
        self._markets: dict[str, Market] = {}

    @staticmethod
    def _fresh(balance: float) -> dict:
        return {"balance": float(balance), "positions": {}, "triggers": [], "fills": [],
                "leverage": {}, "next_oid": 1}

    def _save(self) -> None:
        paper_repo.save(self._state)

    def _new_oid(self) -> int:
        oid = int(self._state.get("next_oid", 1))
        self._state["next_oid"] = oid + 1
        return oid

    def reset(self, balance: float) -> None:
        with self._lock:
            self._state = self._fresh(balance)
            self._save()

    # ── market data: passed through ──────────────────────────────────────────
    def markets(self) -> list[Market]:
        markets = self._src.markets()
        self._markets = {m.coin: m for m in markets}
        return markets

    def snapshots(self) -> list[MarketSnapshot]:
        return self._src.snapshots()

    def mids(self) -> dict[str, float]:
        return self._src.mids()

    def candles(self, coin: str, interval: str, start_ms: int, end_ms: int) -> list[Candle]:
        return self._src.candles(coin, interval, start_ms, end_ms)

    def funding_history(self, coin: str, start_ms: int) -> list[tuple[int, float]]:
        return self._src.funding_history(coin, start_ms)

    def _market(self, coin: str) -> Market:
        if coin not in self._markets:
            self.markets()
        if coin not in self._markets:
            raise ExchangeError(f"unknown market {coin}")
        return self._markets[coin]

    # ── simulated account ────────────────────────────────────────────────────
    def _fill(self, coin: str, is_buy: bool, size: float, price: float, oid: int) -> Fill:
        """Apply one fill to the simulated position; returns the Fill."""
        pos = self._state["positions"].get(coin)
        signed = size if is_buy else -size
        fee = abs(size) * price * PAPER_TAKER_FEE
        closed_pnl = 0.0
        if pos is None or pos["size"] == 0:
            self._state["positions"][coin] = {"size": signed, "entry": price}
        else:
            old = pos["size"]
            if (old > 0) == (signed > 0):          # adding
                new = old + signed
                pos["entry"] = (pos["entry"] * abs(old) + price * abs(signed)) / abs(new)
                pos["size"] = new
            else:                                   # reducing / flipping
                closing = min(abs(old), abs(signed))
                direction = 1 if old > 0 else -1
                closed_pnl = (price - pos["entry"]) * closing * direction
                new = old + signed
                if abs(new) < 1e-12:
                    self._state["positions"].pop(coin, None)
                    self._state["triggers"] = [t for t in self._state["triggers"] if t["coin"] != coin]
                elif (new > 0) != (old > 0):
                    self._state["positions"][coin] = {"size": new, "entry": price}
                else:
                    pos["size"] = new
        self._state["balance"] += closed_pnl - fee
        fill = Fill(coin=coin, oid=oid, price=price, size=abs(size), is_buy=is_buy, fee=fee,
                    closed_pnl=closed_pnl, time_ms=clock.now_ms())
        self._state["fills"].append(fill.__dict__)
        self._state["fills"] = self._state["fills"][-2000:]
        return fill

    def _process_triggers(self, mids: dict[str, float]) -> None:
        remaining = []
        fired = False
        for t in self._state["triggers"]:
            mid = mids.get(t["coin"])
            pos = self._state["positions"].get(t["coin"])
            if mid is None or pos is None:
                remaining.append(t)
                continue
            # A buy trigger protects a short: stop fires on a rise, TP on a fall.
            if t["kind"] == "stop":
                hit = mid >= t["trigger"] if t["is_buy"] else mid <= t["trigger"]
            else:
                hit = mid <= t["trigger"] if t["is_buy"] else mid >= t["trigger"]
            if not hit:
                remaining.append(t)
                continue
            price = max(mid, t["trigger"]) if t["is_buy"] else min(mid, t["trigger"])
            size = min(t["size"], abs(pos["size"]))
            self._fill(t["coin"], t["is_buy"], size, price, t["oid"])
            fired = True
        if fired:
            live = set(self._state["positions"])
            self._state["triggers"] = [t for t in remaining if t["coin"] in live]
            self._save()

    def _refresh(self) -> dict[str, float]:
        mids = self._src.mids()
        with self._lock:
            self._process_triggers(mids)
        return mids

    def account(self) -> AccountState:
        mids = self._refresh()
        with self._lock:
            positions = []
            upnl_total = 0.0
            margin = 0.0
            for coin, p in self._state["positions"].items():
                mark = mids.get(coin, p["entry"])
                upnl = (mark - p["entry"]) * p["size"]
                lev = int(self._state["leverage"].get(coin, 1))
                used = abs(p["size"]) * mark / max(lev, 1)
                upnl_total += upnl
                margin += used
                positions.append(Position(coin=coin, size=p["size"], entry_price=p["entry"],
                                          unrealised_pnl=upnl, leverage=lev,
                                          liquidation_price=None, margin_used=used))
            equity = self._state["balance"] + upnl_total
            return AccountState(equity=equity, available=max(equity - margin, 0.0),
                                margin_used=margin, positions=tuple(positions))

    def open_orders(self) -> list[OpenOrder]:
        self._refresh()
        with self._lock:
            return [OpenOrder(coin=t["coin"], oid=t["oid"], is_buy=t["is_buy"], size=t["size"],
                              limit_price=t["trigger"], trigger_price=t["trigger"],
                              reduce_only=True, kind=t["kind"]) for t in self._state["triggers"]]

    def fills_since(self, start_ms: int) -> list[Fill]:
        self._refresh()
        with self._lock:
            return [Fill(**f) for f in self._state["fills"] if f["time_ms"] >= start_ms]

    # ── simulated orders ─────────────────────────────────────────────────────
    def set_leverage(self, coin: str, leverage: int, cross: bool) -> None:
        with self._lock:
            self._state["leverage"][coin] = int(leverage)
            self._save()

    def place_market(self, coin: str, is_buy: bool, size: float, slippage: float,
                     reduce_only: bool = False) -> OrderResult:
        m = self._market(coin)
        mid = self._src.mids().get(coin)
        if mid is None:
            return OrderResult(ok=False, error=f"no price for {coin}")
        with self._lock:
            pos = self._state["positions"].get(coin)
            if reduce_only:
                if pos is None or (pos["size"] > 0) == is_buy:
                    return OrderResult(ok=False, error="reduce-only order would not reduce")
                size = min(size, abs(pos["size"]))
            sz = rounding.round_size(size, m.sz_decimals)
            if sz <= 0:
                return OrderResult(ok=False, error="size rounds to zero")
            price = mid * (1 + PAPER_SLIPPAGE) if is_buy else mid * (1 - PAPER_SLIPPAGE)
            oid = self._new_oid()
            self._fill(coin, is_buy, sz, price, oid)
            self._save()
            return OrderResult(ok=True, oid=oid, filled_size=sz, avg_price=price)

    def place_trigger(self, coin: str, is_buy: bool, size: float, trigger_price: float,
                      kind: str) -> OrderResult:
        if kind not in ("stop", "take_profit"):
            raise ValueError(kind)
        m = self._market(coin)
        with self._lock:
            oid = self._new_oid()
            self._state["triggers"].append({
                "oid": oid, "coin": coin, "is_buy": is_buy, "kind": kind,
                "size": rounding.round_size(size, m.sz_decimals),
                "trigger": rounding.round_price(trigger_price, m.sz_decimals),
            })
            self._save()
            return OrderResult(ok=True, oid=oid)

    def cancel(self, coin: str, oid: int) -> bool:
        with self._lock:
            before = len(self._state["triggers"])
            self._state["triggers"] = [t for t in self._state["triggers"] if t["oid"] != oid]
            changed = len(self._state["triggers"]) != before
            if changed:
                self._save()
            return changed

    def balance(self) -> Optional[float]:
        return self._state.get("balance")
