# The golden rules

**Read this before changing anything. It applies to every AI agent and every
human, on every change, without exception.**

This app can place real-money orders on Hyperliquid. These rules come from
FOREX Trader, where most of them were paid for by an incident; they are kept
here unchanged in spirit and re-aimed at crypto.

---

## The five that can cost money

### 1. Never place, close or modify a real trade on mainnet as a test

Test on **paper** or **testnet** (Hyperliquid's test exchange is this app's
demo account). The automated suite uses fakes and sentinels and touches no
exchange at all, not even testnet: it runs unattended, on CI and on other
people's machines.

### 2. The close path does not get "improved"

`close_trade`, `partial_close_trade` and `record_close`
(`services/trading/order_service.py`) may be renamed or relocated verbatim.
They may **not** be reshaped: no argument added, removed, reordered or
defaulted, no branch restructured: without explicit sign-off from the owner
plus a testnet session watching real trades open and close.

`tests/trading/test_close_path_characterization.py` is the witness. It must
pass **unmodified**.

### 3. Defaults never change silently

Any behaviour constant that becomes configurable keeps its exact previous value
as the default; `services/risk/settings.py` defaults are pinned by
`tests/services/risk/test_settings.py`. An upgrade must never change how the
system trades. See [60-adding-a-tunable.md](60-adding-a-tunable.md).

### 4. A failing test is information, not an obstacle

Never delete, skip, `xfail`, loosen or rewrite a test to make a change pass.
The only legitimate edit to a characterization test is a mock-target
relocation, named in the commit.

### 5. Money maths is not a place to be clever

Balances, P&L and prices are floats. Do not "tidy" rounding, change an epsilon,
or reorder arithmetic in a sizing or P&L path. Sizes always round **down**;
stops round **away** from entry (`services/exchange/rounding.py`).

## The five that keep the codebase alive

### 6. Test-first, and watch the test fail

A test that has never failed has never proved anything.

### 7. Every claim gets a negative control

If you assert "zero violations", also assert the scanner can find one.
`tests/refactor/test_gates_catch_violations.py` does this for every gate.

### 8. Layers only point downward

```
frontend  ->  api/  ->  controllers/  ->  services/  ->  db/
                              utils/, config/  ->  nothing above them
```

Enforced by `tools/refactor_audit/import_contracts.py`, together with the
**single real-money surface**: only `services/trading/order_service.py` may
place, cancel or re-leverage. See [30-architecture.md](30-architecture.md).

### 9. Delete code, don't comment it out

The orphan-module gate fails on a module nothing imports.

### 10. Say what you actually did

If you skipped part of the task, say which and why. If a number is worse than
the target, report the number. A report that overstates completion is the most
expensive thing an agent can produce here.

### 11. Never break FOREX Trader

This app runs beside FOREX Trader on the same machine. Never bind its ports,
read or write its data folder, take its lock, use its keyring entries, or kill
its processes. Never change `~/Forex-Gold`, `~/Forex-Update` or the admin
console's code from this repository. See
[80-running-beside-forex-gold.md](80-running-beside-forex-gold.md).

---

## Hard "do not" list

| Never | Because |
|---|---|
| Enter or store a **main wallet** private key | an API wallet can trade but cannot withdraw; that is the whole protection |
| Commit secrets, keys, tokens, `.env`, `config.yaml` | they end up in the remote permanently |
| Log a private key | diagnostics are sent to the admin console; `scrub_log_secrets` is a backstop, not a licence |
| `git push --force` to a shared branch | rewrites history others hold |
| Weaken a ratchet baseline to make CI pass | the baseline is the record |
| Run two full test suites at once | phantom failures |
| `pip install` a new runtime dependency without asking | it ships to every install |
| Kill a process by name or by port 8888/9000 | that can be FOREX Trader mid-trade |
| Mention which AI model made a change, in any commit, PR or code comment | owner's rule |

## When to stop and ask

- the change touches order placement, closing, or position sizing
- a test would have to be modified to pass
- a ratchet baseline would have to rise
- verifying it needs **mainnet**
- you are about to say "this should be fine" about money

**A "yes, go ahead" to a plan that includes any of the above is not sign-off
for the money-touching part.** Say which part needs a testnet session, do the
rest, and leave that piece.
