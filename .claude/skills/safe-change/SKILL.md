---
name: safe-change
description: Procedure for any change near orders, sizing, stops, leverage, the risk gates or the close path. Use before editing services/trading/, services/positions/, services/risk/sizing.py, services/risk/gates.py or services/exchange/.
---

# Safe change (money paths)

1. **Stop and say so.** Changes to order placement, closing, sizing or stop
   movement need the owner's sign-off and a **testnet** session. A "yes, go
   ahead" to a plan is not that sign-off.
2. Read docs/system/rules/20-trading-safety.md and the domain README
   (positions, risk or exchange).
3. The close path (`close_trade`, `partial_close_trade`, `record_close`) is
   frozen: move verbatim only. `tests/trading/test_close_path_characterization.py`
   must pass unmodified.
4. Write the failing test against `FakeExchange`, including the refusal case
   (exchange says no) and the "never unprotected" case (stop refused -> closed).
5. Mutation-check the new test.
6. `tools.checks all`.
7. Testnet session, attended: header badge shows TESTNET, one small trade, watch
   entry, stop, TP ladder, a stop move and the close on the Hyperliquid testnet UI.
   Record what you saw in the commit.
