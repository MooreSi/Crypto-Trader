# Making a constant configurable

Golden rule 3: **an upgrade must never change how the system trades.**

1. Add the setting to `services/risk/settings.py` (`NUMERIC`, `BOOLEAN` or
   `LISTS`) with its **current hard-coded value as the default** and a
   `[min, max]` envelope that contains it.
2. Pin the default in `tests/services/risk/test_settings.py` in the same change.
3. Read it from the settings dict where the constant was used. Do not keep the
   old constant as a fallback.
4. Add it to the Risk page (`frontend/src/components/risk/RiskPage.tsx`) with a
   one-line explanation, and rebuild `frontend/dist`.
5. If it changes how a trade is gated, add it to the table in
   [20-trading-safety.md](20-trading-safety.md).

Every write is clamped to the envelope (`settings.normalise`), so neither the
dashboard nor a hand-edited database can push a value outside it.
