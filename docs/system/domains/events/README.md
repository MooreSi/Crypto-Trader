# Events

**Living file.** Covers `services/events/`.

## Sources

| Source | Impact | Blocks |
|---|---|---|
| US macro (ForexFactory weekly JSON, USD only; FOMC/CPI/NFP/core PCE promoted to high) | as rated | every coin |
| FOMC fallback dates (2026 only; add 2027 when published) | high | every coin |
| Deribit options expiry, Fridays 08:00 UTC: weekly low, monthly medium, quarterly high | | BTC, ETH |
| CME Bitcoin futures weekend close/reopen (Chicago time) | low, never blocks | - |
| Your own: token unlocks, listings, upgrades, maintenance | you choose | the coins you name, or all |

## Constraints

- A blackout blocks only **new** entries, never manages or closes a position.
- The macro feed backs off on failure (5 min doubling to 1 h); it publishes
  weekly, so next week's releases appear only once the new week's file is up.
- The timetable is regenerated hourly 21 days ahead.

## Open questions

- Token-unlock data has no free reliable feed; v0.1 relies on user entries.
