# Trading safety: the parts that move money

## The order-touching surfaces

| Surface | Where | What it can do |
|---|---|---|
| **Every order** | `services/trading/order_service.py` | the ONLY caller of `place_market`, `place_trigger`, `cancel`, `set_leverage` (gate-enforced) |
| **Entry decision** | `services/trading/executor.py` | runs the gates and sizing, then calls `open_trade` |
| **Stop moves** | `services/positions/manager.py` -> `order_service.move_stop` | breakeven, trailing, resize after a TP |
| **Sizing** | `services/risk/sizing.py` | how much money is at risk, and at what leverage |
| **The wire** | `services/exchange/hyperliquid_client.py` | signs and sends to Hyperliquid |

Any change inside these needs owner sign-off and a **testnet** session.

## Three promises the order service keeps

1. **No unprotected position.** The stop is placed straight after the entry
   fills. If it is refused, the position is closed at market at once. If the
   entry fills beyond the stop (slippage), it is closed at once. A stop is
   moved by placing the new one before cancelling the old.
2. **The exchange holds the exits.** Stop and TP ladder are exchange-native,
   reduce-only trigger orders. The app can be closed and the position stays
   protected.
3. **Every change is recorded** in `trade_events`, in the same transaction.

## The close path is frozen

`close_trade`, `partial_close_trade`, `record_close`. Witness:
`tests/trading/test_close_path_characterization.py`, must pass unmodified.

## Test rules for these surfaces

**No test may reach any exchange: mainnet or testnet.** `tests/conftest.py`
replaces the Hyperliquid SDK's `Exchange` and `Info` constructors with ones
that raise, and points the data directory at a temp folder before anything
imports the app. Tests use `tests/fakes.py::FakeExchange`.

Testnet verification is a deliberate, attended act by someone who has just
checked the network badge in the header says TESTNET.

## Things that gate order placement

Changing any of these changes the risk envelope even when the code looks
harmless. Defaults are the owner's "conservative" choice for v0.1:

| Setting | Default | Effect |
|---|---|---|
| `trading_enabled` | **off** | master switch |
| engine `live` toggle | **off** per engine | engine hands signals to the executor |
| `risk_per_trade_pct` | 0.5 | % of equity lost if the stop is hit |
| `max_leverage` | 3 | cap; the market's own max also applies |
| `isolated_margin` | on | a position can only lose its own margin |
| `max_open_positions` | 3 | |
| `max_same_direction` | 2 | correlation cap |
| `daily_loss_limit_pct` | 3 | of the UTC day's starting equity |
| `daily_profit_target_usd` | 0 (off) | stop new entries once reached |
| `min_reward_risk` | 1.5 | weighted R of the TP ladder |
| `tp_ladder` | 1R 50%, 2R 25%, 3R 25% | |
| `breakeven_after_tp` | 1 | |
| `max_funding_rate_pct` | 0.05 %/h | refuse entries paying more |
| event blackout | on, 30 min either side of high impact | |

## Leverage and liquidation

Leverage never sets the risk; the stop does. `sizing.safe_leverage` picks the
highest leverage (up to the cap) at which an isolated position's liquidation
sits at least `LIQ_BUFFER` (1.5) stop-distances from entry, using maintenance
margin = half the initial margin at the market's max leverage.

## Positions the app did not open

Listed on the dashboard as unmanaged and **never touched**: the owner may trade
the same account by hand.

## API wallet only

The app holds a Hyperliquid **API wallet** key (can trade, cannot withdraw),
per network, in the OS keyring. Never a main wallet key.
