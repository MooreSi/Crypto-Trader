"""The exchange's vocabulary, independent of which exchange answers.

Everything above `services/exchange/` speaks these types and the
`ExchangeClient` protocol, never the Hyperliquid SDK directly. That is what
lets the paper simulator and the test fakes stand in for the real exchange
without a single `if paper:` anywhere in the trading code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass(frozen=True)
class Market:
    """One perpetual listed on the exchange."""
    coin: str
    sz_decimals: int
    max_leverage: int
    only_isolated: bool = False
    delisted: bool = False


@dataclass(frozen=True)
class MarketSnapshot:
    """The live context for one market (from metaAndAssetCtxs)."""
    coin: str
    mark_price: float
    mid_price: Optional[float]
    oracle_price: float
    funding_rate: float          # hourly rate, as Hyperliquid pays it
    open_interest: float         # in coins
    day_notional_volume: float   # USD
    prev_day_price: float

    @property
    def change_24h_pct(self) -> float:
        if not self.prev_day_price:
            return 0.0
        return (self.mark_price - self.prev_day_price) / self.prev_day_price * 100.0


@dataclass(frozen=True)
class Candle:
    t: int          # open time, ms
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Position:
    coin: str
    size: float              # signed: + long, - short
    entry_price: float
    unrealised_pnl: float
    leverage: int
    liquidation_price: Optional[float]
    margin_used: float

    @property
    def direction(self) -> str:
        return "long" if self.size > 0 else "short"


@dataclass(frozen=True)
class AccountState:
    equity: float            # account value, USDC
    available: float         # withdrawable / free margin
    margin_used: float
    positions: tuple[Position, ...] = ()

    def position(self, coin: str) -> Optional[Position]:
        for p in self.positions:
            if p.coin == coin and p.size != 0:
                return p
        return None


@dataclass(frozen=True)
class OpenOrder:
    coin: str
    oid: int
    is_buy: bool
    size: float
    limit_price: float
    trigger_price: Optional[float]
    reduce_only: bool
    kind: str               # "limit", "stop", "take_profit"


@dataclass(frozen=True)
class Fill:
    coin: str
    oid: int
    price: float
    size: float
    is_buy: bool
    fee: float
    closed_pnl: float
    time_ms: int


@dataclass
class OrderResult:
    """What came back from placing one order."""
    ok: bool
    oid: Optional[int] = None
    filled_size: float = 0.0
    avg_price: Optional[float] = None
    error: str = ""
    raw: dict = field(default_factory=dict)


class ExchangeError(RuntimeError):
    """The exchange refused or could not be reached."""


class ExchangeClient(Protocol):
    """Everything the app asks of an exchange.

    `place_*`, `cancel` and `set_leverage` are the only methods that can cost
    money. Only `services/trading/order_service.py` calls them (enforced by
    the import-contract gate).
    """
    network: str

    def markets(self) -> list[Market]: ...
    def snapshots(self) -> list[MarketSnapshot]: ...
    def mids(self) -> dict[str, float]: ...
    def candles(self, coin: str, interval: str, start_ms: int, end_ms: int) -> list[Candle]: ...
    def funding_history(self, coin: str, start_ms: int) -> list[tuple[int, float]]: ...
    def account(self) -> AccountState: ...
    def open_orders(self) -> list[OpenOrder]: ...
    def fills_since(self, start_ms: int) -> list[Fill]: ...

    def set_leverage(self, coin: str, leverage: int, cross: bool) -> None: ...
    def place_market(self, coin: str, is_buy: bool, size: float, slippage: float,
                     reduce_only: bool = False) -> OrderResult: ...
    def place_trigger(self, coin: str, is_buy: bool, size: float, trigger_price: float,
                      kind: str) -> OrderResult: ...
    def cancel(self, coin: str, oid: int) -> bool: ...
