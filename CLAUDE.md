# CLAUDE.md

**This app can place real orders on Hyperliquid with real money.**

Read **[docs/system/rules/10-golden-rules.md](docs/system/rules/10-golden-rules.md)**
before changing anything. It is short and it is not optional.

Crypto Trader is the sister app of FOREX Trader (`MooreSi/forex-gold`,
`~/Forex-Gold`). It was built from that app's rules and engines. **Never change
anything in `~/Forex-Gold`, `~/Forex-Update` or `~/forex-admin` from here**, and
never let this app touch FOREX Trader's ports, data folder, lock or processes
([rules/80](docs/system/rules/80-running-beside-forex-gold.md)).

**A question you can't answer** (trading policy, risk numbers, money behaviour):
the owner answers those. Choose a safe provisional default (never more
aggressive than today), proceed, and say what you chose and what changes if
the answer differs.

---

## The five rules that matter most

1. **Never place, close or modify a trade on mainnet as a test.** Paper and
   testnet (the demo account) are allowed. The automated suite touches no
   exchange at all.
2. **Never edit a test to make a change pass.**
3. **Write the test first and watch it fail.**
4. **The close path is frozen.** `close_trade`, `partial_close_trade`,
   `record_close` may be moved verbatim, never reshaped, without owner sign-off
   and a testnet session.
5. **Report what you actually did**, including what you skipped and any number
   that came out worse than intended.

## Before you commit, all of it

```bash
.venv/bin/python -m tools.checks all
cd frontend && npm test
```

Suite, gates, coverage ratchet, boot smoke, doc links. **A failing gate is not
noise.** Use `.venv/bin/python`, never bare `python`.

## The knowledge base: docs/system/

- [docs/system/vision/000-goal.md](docs/system/vision/000-goal.md): what the system is for
- [docs/system/rules/](docs/system/rules/): the non-negotiables
- [docs/system/domains/](docs/system/domains/README.md): one living README per part

Before changing a domain, read its README. After a change teaches you something
non-obvious, record it there in the same change. If a domain file and the code
disagree, the code is the fact: fix the file and say so.

| Topic | File |
|---|---|
| Start here | [00-start-here.md](docs/system/rules/00-start-here.md) |
| **Golden rules** | [10-golden-rules.md](docs/system/rules/10-golden-rules.md) |
| What can cost money | [20-trading-safety.md](docs/system/rules/20-trading-safety.md) |
| Layers and boundaries | [30-architecture.md](docs/system/rules/30-architecture.md) |
| Testing protocol | [40-testing.md](docs/system/rules/40-testing.md) |
| How to make a change | [50-workflow.md](docs/system/rules/50-workflow.md) |
| Making a constant configurable | [60-adding-a-tunable.md](docs/system/rules/60-adding-a-tunable.md) |
| Splitting a big file | [70-file-organisation.md](docs/system/rules/70-file-organisation.md) |
| **Running beside FOREX Trader** | [80-running-beside-forex-gold.md](docs/system/rules/80-running-beside-forex-gold.md) |

## Skills

| Skill | Use when |
|---|---|
| `/verify` | before every commit |
| `/test` | writing or reviewing any test |
| `/safe-change` | any change near orders, sizing, stops or the close path |
| `/add-tunable` | a hard-coded constant should be user-editable |
| `/split-file` | a file nears 800 lines |
| `/new-spec` | anything bigger than a one-line fix |

## Layers point downward, never up

```
frontend/ (React, compiled to frontend/dist, committed)
    | HTTP/JSON, 127.0.0.1:8890
backend/src/api/ -> controllers/ -> services/ -> db/
                        utils/, config/ -> nothing above them
```

Routers forward; controllers route; services decide; repos hold the SQL. Only
`services/trading/order_service.py` places, cancels or re-leverages orders.
All enforced by `tools/refactor_audit/`; see
[rules/30](docs/system/rules/30-architecture.md).

## Session mechanics

- **`.venv/bin/python` always.** Bare `python` on the owner's Mac is a
  different interpreter; FOREX Trader once reported 20 fabricated failures
  from it.
- **A `frontend/src` change that is not rebuilt is not shipped.** Commit
  `frontend/dist` with it.
- **Never edit tracked files while the suite runs.**
- **After restoring a mutated file, delete `__pycache__`.** A same-length swap
  restored in the same second reuses the mutated bytecode.
- **Start shell commands from an absolute path**; the folder name has a space
  (`"/Users/simon/Crypto Trader"`), so quote it.
- **To preview the app**, use a scratch data dir and turn the admin console off
  (`.claude/launch.json` does both), so a test run never registers a throwaway
  client on the owner's console.

## Do not

- `git push --force` to a shared branch
- commit secrets, keys, `config.yaml`, `.env`
- enter or store a main-wallet private key (API wallets only)
- lower a ratchet baseline to get CI green
- run two full test suites at once
- `pip install` a new runtime dependency without asking
- mention which AI model made a change, in any commit, PR or code comment

## Stop and ask when

- the change touches order placement, closing, sizing or stop movement
- a test would have to be modified to pass
- a ratchet baseline would have to rise
- verifying it needs **mainnet** (testnet is yours to use)
- you are about to say "this should be fine" about money

## Running it

```bash
.venv/bin/python run.py                 # http://127.0.0.1:8890
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m tools.checks all

cd frontend && npm install && npm test && npm run build
```

Green output is not evidence. That is what these rules exist to fix.
