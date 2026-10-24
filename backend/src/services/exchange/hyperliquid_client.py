"""The real exchange: Hyperliquid perpetuals, through the official Python SDK.

Read calls go through `hyperliquid.info.Info` and need no key. Order calls go
through `hyperliquid.exchange.Exchange`, signed with an **API wallet** key
(see config/secrets.py) on behalf of `account_address`, the main account that
holds the funds. An API wallet can trade but cannot withdraw.

The `Exchange` object is built lazily, on the first call that needs it, so a
read-only session (dashboard open, no key entered yet) never touches a key.

Response shapes are the SDK's own docstrings (hyperliquid-python-sdk 0.24.0,
`info.py`); order statuses are `{"resting": {"oid"}}`, `{"filled": {"totalSz",
"avgPx", "oid"}}` or `{"error": str}` per order, inside
`response.data.statuses`.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.src.services.exchange import rounding
from backend.src.services.exchange.types import (
    AccountState, Candle, ExchangeError, Fill, Market, MarketSnapshot, OpenOrder,
    OrderResult, Position,
)

log = logging.getLogger(__name__)

MAINNET_URL = "https://api.hyperliquid.xyz"
TESTNET_URL = "https://api.hyperliquid-testnet.xyz"

#: How far past the trigger a stop's limit price sits. A Hyperliquid trigger
#: order with `isMarket: True` still carries a limit price, which acts as the
#: worst fill it will accept. 10% matches the exchange UI's market-trigger
#: default; a tighter cap risks a stop that triggers and then does not fill
#: in a fast move, which is the one moment a stop exists for.
TRIGGER_SLIPPAGE = 0.10


def base_url(network: str) -> str:
    if network == "mainnet":
        return MAINNET_URL
    if network == "testnet":
        return TESTNET_URL
    raise ValueError(f"no Hyperliquid endpoint for network {network!r}")


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_markets(meta: dict) -> list[Market]:
    return [
        Market(
            coin=u["name"],
            sz_decimals=int(u["szDecimals"]),
            max_leverage=int(u.get("maxLeverage", 1)),
            only_isolated=bool(u.get("onlyIsolated", False)),
            delisted=bool(u.get("isDelisted", False)),
        )
        for u in meta.get("universe", [])
    ]


def parse_snapshots(meta_and_ctxs: list) -> list[MarketSnapshot]:
    meta, ctxs = meta_and_ctxs[0], meta_and_ctxs[1]
    out = []
    for u, c in zip(meta.get("universe", []), ctxs):
        if u.get("isDelisted"):
            continue
        mid = c.get("midPx")
        out.append(MarketSnapshot(
            coin=u["name"],
            mark_price=_f(c.get("markPx")),
            mid_price=_f(mid) if mid is not None else None,
            oracle_price=_f(c.get("oraclePx")),
            funding_rate=_f(c.get("funding")),
            open_interest=_f(c.get("openInterest")),
            day_notional_volume=_f(c.get("dayNtlVlm")),
            prev_day_price=_f(c.get("prevDayPx")),
        ))
    return out


def parse_account(state: dict) -> AccountState:
    summary = state.get("marginSummary", {})
    positions = []
    for ap in state.get("assetPositions", []):
        p = ap.get("position", {})
        size = _f(p.get("szi"))
        if size == 0:
            continue
        liq = p.get("liquidationPx")
        positions.append(Position(
            coin=p["coin"],
            size=size,
            entry_price=_f(p.get("entryPx")),
            unrealised_pnl=_f(p.get("unrealizedPnl")),
            leverage=int(_f((p.get("leverage") or {}).get("value"), 1)),
            liquidation_price=_f(liq) if liq is not None else None,
            margin_used=_f(p.get("marginUsed")),
        ))
    return AccountState(
        equity=_f(summary.get("accountValue")),
        available=_f(state.get("withdrawable")),
        margin_used=_f(summary.get("totalMarginUsed")),
        positions=tuple(positions),
    )


def parse_open_orders(rows: list) -> list[OpenOrder]:
    out = []
    for o in rows:
        order_type = str(o.get("orderType", ""))
        if o.get("isTrigger"):
            kind = "take_profit" if "Take Profit" in order_type else "stop"
        else:
            kind = "limit"
        trig = o.get("triggerPx")
        out.append(OpenOrder(
            coin=o["coin"], oid=int(o["oid"]), is_buy=o.get("side") == "B",
            size=_f(o.get("sz")), limit_price=_f(o.get("limitPx")),
            trigger_price=_f(trig) if o.get("isTrigger") and trig is not None else None,
            reduce_only=bool(o.get("reduceOnly")), kind=kind,
        ))
    return out


def parse_order_response(resp: Any) -> OrderResult:
    """One order's outcome from an `/exchange` order response."""
    if not isinstance(resp, dict) or resp.get("status") != "ok":
        return OrderResult(ok=False, error=str(resp.get("response") if isinstance(resp, dict) else resp),
                           raw=resp if isinstance(resp, dict) else {})
    try:
        status = resp["response"]["data"]["statuses"][0]
    except (KeyError, IndexError, TypeError):
        return OrderResult(ok=False, error="unrecognised order response", raw=resp)
    if "error" in status:
        return OrderResult(ok=False, error=str(status["error"]), raw=resp)
    if "filled" in status:
        f = status["filled"]
        return OrderResult(ok=True, oid=int(f["oid"]), filled_size=_f(f.get("totalSz")),
                           avg_price=_f(f.get("avgPx")), raw=resp)
    if "resting" in status:
        return OrderResult(ok=True, oid=int(status["resting"]["oid"]), raw=resp)
    return OrderResult(ok=False, error=f"unexpected status {status}", raw=resp)


class HyperliquidClient:
    def __init__(self, network: str, account_address: str, agent_key: Optional[str]) -> None:
        self.network = network
        self.account_address = account_address
        self._agent_key = agent_key
        self._url = base_url(network)
        self._info = None
        self._exchange = None
        self._markets: dict[str, Market] = {}

    # ── plumbing ─────────────────────────────────────────────────────────────
    def _i(self):
        if self._info is None:
            from hyperliquid.info import Info
            self._info = Info(self._url, skip_ws=True)
        return self._info

    def _x(self):
        if self._exchange is None:
            if not self._agent_key:
                raise ExchangeError("no API wallet key stored for this network")
            if not self.account_address:
                raise ExchangeError("no Hyperliquid account address configured")
            import eth_account
            from hyperliquid.exchange import Exchange
            wallet = eth_account.Account.from_key(self._agent_key)
            self._exchange = Exchange(wallet, self._url, account_address=self.account_address)
        return self._exchange

    def _call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ExchangeError:
            raise
        except Exception as exc:
            raise ExchangeError(f"{getattr(fn, '__name__', 'call')}: {exc}") from exc

    def _market(self, coin: str) -> Market:
        if coin not in self._markets:
            self.markets()
        try:
            return self._markets[coin]
        except KeyError:
            raise ExchangeError(f"unknown market {coin}") from None

    # ── reads ────────────────────────────────────────────────────────────────
    def markets(self) -> list[Market]:
        markets = parse_markets(self._call(self._i().meta))
        self._markets = {m.coin: m for m in markets}
        return markets

    def snapshots(self) -> list[MarketSnapshot]:
        return parse_snapshots(self._call(self._i().meta_and_asset_ctxs))

    def mids(self) -> dict[str, float]:
        return {k: _f(v) for k, v in self._call(self._i().all_mids).items() if not k.startswith("@")}

    def candles(self, coin: str, interval: str, start_ms: int, end_ms: int) -> list[Candle]:
        rows = self._call(self._i().candles_snapshot, coin, interval, start_ms, end_ms)
        return [Candle(int(r["t"]), _f(r["o"]), _f(r["h"]), _f(r["l"]), _f(r["c"]), _f(r["v"]))
                for r in rows]

    def funding_history(self, coin: str, start_ms: int) -> list[tuple[int, float]]:
        rows = self._call(self._i().funding_history, coin, start_ms)
        return [(int(r["time"]), _f(r["fundingRate"])) for r in rows]

    def account(self) -> AccountState:
        if not self.account_address:
            raise ExchangeError("no Hyperliquid account address configured")
        return parse_account(self._call(self._i().user_state, self.account_address))

    def open_orders(self) -> list[OpenOrder]:
        return parse_open_orders(self._call(self._i().frontend_open_orders, self.account_address))

    def fills_since(self, start_ms: int) -> list[Fill]:
        rows = self._call(self._i().user_fills_by_time, self.account_address, start_ms)
        return [Fill(coin=r["coin"], oid=int(r["oid"]), price=_f(r["px"]), size=_f(r["sz"]),
                     is_buy=r.get("side") == "B", fee=_f(r.get("fee")),
                     closed_pnl=_f(r.get("closedPnl")), time_ms=int(r["time"])) for r in rows]

    # ── writes (order_service only) ──────────────────────────────────────────
    def set_leverage(self, coin: str, leverage: int, cross: bool) -> None:
        resp = self._call(self._x().update_leverage, int(leverage), coin, cross)
        if not isinstance(resp, dict) or resp.get("status") != "ok":
            raise ExchangeError(f"leverage update refused: {resp}")

    def place_market(self, coin: str, is_buy: bool, size: float, slippage: float,
                     reduce_only: bool = False) -> OrderResult:
        m = self._market(coin)
        sz = rounding.round_size(size, m.sz_decimals)
        if reduce_only:
            resp = self._call(self._x().market_close, coin, sz, None, slippage)
        else:
            resp = self._call(self._x().market_open, coin, is_buy, sz, None, slippage)
        return parse_order_response(resp)

    def place_trigger(self, coin: str, is_buy: bool, size: float, trigger_price: float,
                      kind: str) -> OrderResult:
        if kind not in ("stop", "take_profit"):
            raise ValueError(kind)
        m = self._market(coin)
        sz = rounding.round_size(size, m.sz_decimals)
        trig = rounding.round_price(trigger_price, m.sz_decimals)
        worst = trig * (1 + TRIGGER_SLIPPAGE) if is_buy else trig * (1 - TRIGGER_SLIPPAGE)
        limit = rounding.round_price(worst, m.sz_decimals)
        order_type = {"trigger": {"triggerPx": trig, "isMarket": True,
                                  "tpsl": "sl" if kind == "stop" else "tp"}}
        resp = self._call(self._x().order, coin, is_buy, sz, limit, order_type, True)
        return parse_order_response(resp)

    def cancel(self, coin: str, oid: int) -> bool:
        resp = self._call(self._x().cancel, coin, int(oid))
        return isinstance(resp, dict) and resp.get("status") == "ok"
