/**
 * The settings a strategy owns, grouped as the Strategy page shows them.
 * The server's list (`keys` from /api/strategies) is the authority; these
 * add labels and help. Ranges are enforced server-side (risk/settings.py).
 */
export type StrategyParams = Record<string, number | boolean | number[][]>;

export type NumField = { key: string; label: string; help: string; step?: number };

export const SECTIONS: { title: string; fields: NumField[] }[] = [
  { title: "Sizing", fields: [
    { key: "risk_per_trade_pct", label: "Risk per trade (% of equity)", help: "Lost if the stop is hit.", step: 0.05 },
    { key: "max_leverage", label: "Max leverage", help: "Margin only; the stop sets the risk." },
    { key: "max_position_notional_pct", label: "Max position (% of equity, notional)", help: "Caps size when the stop is very tight." },
    { key: "min_stop_pct", label: "Min stop distance (% of price, 0 = off)", help: "Fees are ~0.09% a round trip; a tight stop starts deep in the red.", step: 0.05 },
    { key: "entry_slippage_pct", label: "Max entry slippage (%)", help: "", step: 0.05 },
  ]},
  { title: "Entry filters", fields: [
    { key: "min_reward_risk", label: "Min reward:risk (ladder)", help: "The TP ladder's weighted R must reach this.", step: 0.1 },
    { key: "ml_min_probability", label: "Min ML probability", help: "Used when an engine has a trained model.", step: 0.05 },
    { key: "max_funding_rate_pct", label: "Max funding paid (%/hour)", help: "", step: 0.005 },
    { key: "blackout_minutes_before", label: "Event blackout before (min)", help: "" },
    { key: "blackout_minutes_after", label: "Event blackout after (min)", help: "" },
  ]},
  { title: "Managing the trade", fields: [
    { key: "breakeven_after_tp", label: "Move the stop after TP n (0 = never)", help: "" },
    { key: "stop_lock_r", label: "...to this many R past entry (0 = breakeven)", help: "1.5 with TP1 at 1.5R locks the stop at TP1. Falls back to breakeven if price is already back below it.", step: 0.25 },
    { key: "trail_atr_mult", label: "Trail at n x ATR(15m) after TP1 (0 = off)", help: "Only ever tightens.", step: 0.25 },
  ]},
  { title: "Portfolio and day", fields: [
    { key: "max_open_positions", label: "Max open positions", help: "" },
    { key: "max_same_direction", label: "Max in one direction", help: "" },
    { key: "daily_loss_limit_pct", label: "Daily loss limit (% of day start)", help: "", step: 0.5 },
    { key: "daily_profit_target_usd", label: "Daily profit target (USDC, 0 = off)", help: "" },
  ]},
];

export const TOGGLES: { key: string; label: string }[] = [
  { key: "blackout_enabled", label: "Event blackout" },
  { key: "blackout_include_medium", label: "Blackout medium-impact events too" },
  { key: "ml_require_model", label: "Require a trained ML model" },
];

const pct = (f: number) => `${Math.round(f * 100)}%`;

/** One line describing how a strategy exits, for the list and the editor. */
export function exitPlan(p: StrategyParams): string {
  const ladder = (p.tp_ladder as number[][]) ?? [];
  const parts = ladder.map(([r, f], i) => `TP${i + 1} ${pct(f)} at ${r}R`);
  const runner = 1 - ladder.reduce((s, [, f]) => s + f, 0);
  if (runner > 1e-6) parts.push(`${pct(runner)} runner`);
  const be = Number(p.breakeven_after_tp);
  const lock = Number(p.stop_lock_r);
  if (be > 0) parts.push(`after TP${be}, stop to ${lock > 0 ? `${lock}R` : "breakeven"}`);
  const trail = Number(p.trail_atr_mult);
  if (trail > 0) parts.push(`trail ${trail} x ATR(15m)`);
  return parts.join("; ");
}
