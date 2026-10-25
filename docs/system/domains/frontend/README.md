# Frontend

**Living file.** Covers `frontend/`.

React 19 + Vite + Tailwind 4, compiled to `frontend/dist`, **which is committed**
and served by the Python app. Node is a developer dependency only.

- All HTTP goes through `src/api/client.ts`, which adds `X-Crypto-Trader: 1` to
  every write (the server refuses writes without it).
- Cyan accent, not FOREX Trader's gold, so the two dashboards are never mixed up.
- Tabs follow the URL hash (`#Markets`), including back/forward.
- Anything that can move money asks first (`confirmAction`): turning trading on,
  making an engine live, closing a trade, choosing mainnet.

`npm test` (vitest), `npm run build` (commit `dist/` with the source change).
- Layout (2026-10-25 redesign): a sidebar (`shell/Sidebar.tsx`, a scrolling
  strip below `lg`), a sticky header with the network badge, and shared
  pieces in `shared/ui.tsx` (Card, Stat, Ring, Meter, Sparkline, Segmented).
  Charts use `lib/chart.ts` with `autoSize`, so they follow the window.
- The running app serves `frontend/dist` from the checkout: a rebuild changes
  a running instance's UI at once, but new API routes only after a restart.
