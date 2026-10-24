---
name: add-tunable
description: Make a hard-coded constant user-editable without changing behaviour. Use when a constant in a risk, sizing, engine or position path should become a setting.
---

# Add a tunable

Follow docs/system/rules/60-adding-a-tunable.md:

1. Add to `services/risk/settings.py` with the **current value as default** and
   an envelope containing it.
2. Pin the default in `tests/services/risk/test_settings.py` (red first: assert
   the key exists before adding it).
3. Replace the constant's use with the setting; delete the constant.
4. Add it to `frontend/src/components/risk/RiskPage.tsx`; `npm run build`.
5. If it gates entries, add it to the table in rules/20-trading-safety.md.
6. `tools.checks all`.
