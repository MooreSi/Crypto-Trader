---
name: verify
description: Run every check before committing: the Python suite, the structural gates, the coverage ratchet, the boot smoke and the dashboard tests. Use before any commit, and whenever asked "is this ready", "is it green", "can I commit", or "run the checks".
---

# Verify

```bash
.venv/bin/python -m tools.checks all      # suite + gates + coverage + boot + doc links
cd frontend && npm test                   # dashboard tests
cd frontend && npm run build              # only if frontend/src changed; commit dist/
```

`.venv/bin/python`, never bare `python` (a different interpreter reports
missing packages as failures that are not yours).

Faster while iterating: `.venv/bin/python -m tools.checks gates`.

## Before you commit, all of this is true

- test suite: 0 failed
- structure gates, import contracts, orphan modules, doc links: 0 problems
- coverage ratchet: not below the baseline
- boot smoke: `import backend.src.app` works
- frontend: `npm test` green; `dist/` rebuilt if `src/` changed

**A failing gate is not noise.** Never run two suites at once. Never edit
tracked files while the suite runs.
