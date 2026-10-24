"""A scripted exchange for tests: records every order, fills at a set price.

Implements `ExchangeClient`. Behaviour is set per test by assigning to its
attributes (`mid`, `refuse_stop`, `entry_fill_price`, ...); every write is
appended to `calls` so a test can assert exactly what was sent.
"""
from __future__ import annotations

from typing import Optional

from backend.src.services.exchange.types import (
    AccountState, Candle, Fill, Market, MarketSnapshot, OpenOrder, OrderResult, Position,
)


class FakeExchange:
    network = "paper"

    def __init__(self) -> None:
        self.market_list = [Market("BTC", 5, 40), Market("ETH", 4, 25), Market("SOL", 2, 20)]
        self.mid = {"BTC": 80_000.0, "ETH": 3_000.0, "SOL": 150.0}
        self.equity = 10_000.0
        self.available = 10_000.0
        self.positions: dict[str, Position] = {}
        self.orders: list[OpenOrder] = []
        self.fills: list[Fill] = []
        self.candle_rows: dict[tuple[str, str], list[Candle]] = {}
        self.funding = {"BTC": 0.00001, "ETH": 0.00001, "SOL": 0.00001}
        self.calls: list[tuple] = []
        self.refuse_stop = False
        self.refuse_entry = False
        self.entry_fill_price: Optional[float] = None
        self._oid = 100

    def _next(self) -> int:
        self._oid += 1
        return self._oid

    # reads
    def markets(self): return list(self.market_list)

    def snapshots(self):
        return [MarketSnapshot(m.coin, self.mid[m.coin], self.mid[m.coin], self.mid[m.coin],
                               self.funding.get(m.coin, 0.0), 1000.0, 1e9, self.mid[m.coin])
                for m in self.market_list]

    def mids(self): return dict(self.mid)

    def candles(self, coin, interval, start_ms, end_ms):
        return [c for c in self.candle_rows.get((coin, interval), []) if start_ms <= c.t <= end_ms]

    def funding_history(self, coin, start_ms): return []

    def account(self):
        return AccountState(self.equity, self.available, 0.0, tuple(self.positions.values()))

    def open_orders(self): return list(self.orders)

    def fills_since(self, start_ms): return [f for f in self.fills if f.time_ms >= start_ms]

    # writes
    def set_leverage(self, coin, leverage, cross):
        self.calls.append(("leverage", coin, leverage, cross))

    def place_market(self, coin, is_buy, size, slippage, reduce_only=False):
        self.calls.append(("market", coin, is_buy, size, reduce_only))
        if self.refuse_entry and not reduce_only:
            return OrderResult(ok=False, error="refused")
        price = self.entry_fill_price if (self.entry_fill_price and not reduce_only) else self.mid[coin]
        oid = self._next()
        signed = size if is_buy else -size
        old = self.positions.get(coin)
        new = (old.size if old else 0.0) + signed
        if abs(new) < 1e-12:
            self.positions.pop(coin, None)
        else:
            self.positions[coin] = Position(coin, new, old.entry_price if old else price, 0.0, 1,
                                            None, 0.0)
        return OrderResult(ok=True, oid=oid, filled_size=size, avg_price=price)

    def place_trigger(self, coin, is_buy, size, trigger_price, kind):
        self.calls.append(("trigger", coin, is_buy, size, trigger_price, kind))
        if kind == "stop" and self.refuse_stop:
            return OrderResult(ok=False, error="stop refused")
        oid = self._next()
        self.orders.append(OpenOrder(coin, oid, is_buy, size, trigger_price, trigger_price, True, kind))
        return OrderResult(ok=True, oid=oid)

    def cancel(self, coin, oid):
        self.calls.append(("cancel", coin, oid))
        before = len(self.orders)
        self.orders = [o for o in self.orders if o.oid != oid]
        return len(self.orders) != before

    # test helpers
    def fire(self, oid: int, price: float, time_ms: int, fee: float = 0.5) -> None:
        """Simulate the exchange filling a resting trigger."""
        order = next(o for o in self.orders if o.oid == oid)
        self.orders.remove(order)
        pos = self.positions[order.coin]
        size = min(order.size, abs(pos.size))
        new = pos.size + (size if order.is_buy else -size)
        sign = 1 if pos.size > 0 else -1
        self.fills.append(Fill(order.coin, oid, price, size, order.is_buy, fee,
                               (price - pos.entry_price) * size * sign, time_ms))
        if abs(new) < 1e-12:
            del self.positions[order.coin]
        else:
            self.positions[order.coin] = Position(order.coin, new, pos.entry_price, 0.0, 1, None, 0.0)


def make_candles(closes: list[float], start_ms: int = 1_792_000_000_000, step_ms: int = 900_000,
                 spread: float = 0.002, volume: float = 100.0) -> list[Candle]:
    out = []
    prev = closes[0]
    for i, c in enumerate(closes):
        hi = max(prev, c) * (1 + spread)
        lo = min(prev, c) * (1 - spread)
        out.append(Candle(start_ms + i * step_ms, prev, hi, lo, c, volume))
        prev = c
    return out
