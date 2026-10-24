---
name: new-spec
description: Write a half-page spec before anything bigger than a one-line fix. Use when starting a feature, a behaviour change or a refactor.
---

# New spec

Write it in the PR description (or `docs/specs/<nnn>-<name>.md` for larger work):

- **What changes**, in one paragraph a non-developer can follow.
- **What must not change** (money behaviour, defaults, FOREX Trader isolation).
- **Touches money?** yes/no. If yes: which surface, and the testnet plan.
- **How we will know it worked**: the failing tests you will write first, and
  what you will look at on the dashboard.
- **Open questions** for the owner, each with the safe provisional default you
  will use meanwhile.
