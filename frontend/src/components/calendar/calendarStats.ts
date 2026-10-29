import type { CalendarTrade } from "@/api/types";
import { usd } from "@/lib/format";
import { formatGain, type DayCell } from "./calendarGrid";

/**
 * The Calendar's statistics beyond money and win rate, as FOREX Trader's
 * calendar shows them. All from the closed-trade rows the calendar already
 * holds, so none of it can disagree with the grid.
 */

const net = (t: CalendarTrade) => Number(t.net_pnl) || 0;
const total = (xs: number[]) => xs.reduce((s, x) => s + x, 0);

/** "+$12.40" / "-$3.50". */
export function money(v: number): string {
  return `${v > 0 ? "+" : v < 0 ? "-" : ""}$${usd(Math.abs(v))}`;
}

export interface DayStats {
  /** Gross profit over gross loss; null with no losers. */
  profitFactor: number | null;
  avgWin: number | null;
  /** Negative. */
  avgLoss: number | null;
  best: number | null;
  worst: number | null;
  fees: number;
}

export function dayStats(trades: CalendarTrade[]): DayStats {
  const pnls = trades.map(net);
  const wins = pnls.filter((p) => p > 0);
  const losses = pnls.filter((p) => p < 0);
  const grossLoss = -total(losses);
  return {
    profitFactor: grossLoss > 0 ? total(wins) / grossLoss : null,
    avgWin: wins.length ? total(wins) / wins.length : null,
    avgLoss: losses.length ? total(losses) / losses.length : null,
    best: pnls.length ? Math.max(...pnls) : null,
    worst: pnls.length ? Math.min(...pnls) : null,
    fees: total(trades.map((t) => Number(t.fees) || 0)),
  };
}

export interface IntradayCurve {
  /** Starts at {ts: first close, cum: 0}; one point per close after it. */
  points: { ts: number; cum: number }[];
  peak: number;
  low: number;
  /** Largest fall from a running peak (the start counts as a peak of 0). */
  maxDrawdown: number;
}

/** The day's realised P&L, close by close. Realised only: an open position's
 *  float is not in the rows, so this is not an equity curve. */
export function intradayCurve(trades: CalendarTrade[]): IntradayCurve {
  const sorted = [...trades].sort((a, b) => a.closed_at - b.closed_at);
  const points = [{ ts: sorted[0]?.closed_at ?? 0, cum: 0 }];
  let cum = 0, peak = 0, low = 0, maxDrawdown = 0;
  for (const t of sorted) {
    cum += net(t);
    points.push({ ts: t.closed_at, cum });
    peak = Math.max(peak, cum);
    low = Math.min(low, cum);
    maxDrawdown = Math.max(maxDrawdown, peak - cum);
  }
  return { points, peak, low, maxDrawdown };
}

export interface Streaks {
  current: { kind: "green" | "red"; length: number } | null;
  longestGreen: number;
  longestRed: number;
  greenDays: number;
  redDays: number;
}

/** Runs of winning and losing days in the month shown. An untraded day
 *  neither breaks nor extends a run; a flat day breaks both; padding days
 *  belong to their own months. */
export function streaks(cells: DayCell[]): Streaks {
  const days = cells.filter((c) => c.inMonth && c.trades.length)
    .sort((a, b) => a.date.localeCompare(b.date));
  const out: Streaks = { current: null, longestGreen: 0, longestRed: 0, greenDays: 0, redDays: 0 };
  let run: Streaks["current"] = null;
  for (const d of days) {
    const kind = d.pnl > 0 ? "green" : d.pnl < 0 ? "red" : null;
    if (kind === "green") out.greenDays++;
    if (kind === "red") out.redDays++;
    run = kind === null ? null
      : run && run.kind === kind ? { kind, length: run.length + 1 } : { kind, length: 1 };
    if (run?.kind === "green") out.longestGreen = Math.max(out.longestGreen, run.length);
    if (run?.kind === "red") out.longestRed = Math.max(out.longestRed, run.length);
  }
  out.current = run;
  return out;
}

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export interface WeekdayTotal { label: string; pnl: number; n: number; wins: number }

/** The month's in-month days totalled by UTC weekday, Monday first. Crypto
 *  trades the weekend, so Saturday and Sunday are real columns here. */
export function weekdayTotals(cells: DayCell[]): WeekdayTotal[] {
  const out = WEEKDAYS.map((label) => ({ label, pnl: 0, n: 0, wins: 0 }));
  for (const c of cells) {
    if (!c.inMonth) continue;
    const [y, m, d] = c.date.split("-").map(Number);
    const slot = out[(new Date(Date.UTC(y!, m! - 1, d!)).getUTCDay() + 6) % 7]!;
    for (const t of c.trades) {
      slot.pnl += net(t);
      slot.n += 1;
      if (net(t) > 0) slot.wins += 1;
    }
  }
  return out;
}

/** What a cell shows. FOREX Trader's pips have no meaning for perps, so the
 *  choices here are money, percent of the opening balance, and R. */
export type CellMetric = "usd" | "pct" | "r";

export const CELL_METRICS: readonly { key: CellMetric; label: string }[] = [
  { key: "usd", label: "$" },
  { key: "pct", label: "%" },
  { key: "r", label: "R" },
];

/** A cell's figure. R sums only the trades that carry one (risk recorded);
 *  a day where none does is null, not a 0 that reads as flat. */
export function cellMetric(cell: DayCell, metric: CellMetric, gain: number | null): number | null {
  if (metric === "usd") return cell.pnl;
  if (metric === "pct") return gain;
  const have = cell.trades.map((t) => t.r)
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  return have.length ? total(have) : null;
}

export function formatMetric(metric: CellMetric, value: number | null): string {
  if (value == null || !Number.isFinite(value)) return "-";
  if (metric === "usd") {
    if (Math.abs(value) < 10_000) return money(value);
    return `${value > 0 ? "+" : "-"}$${Math.abs(value / 1000).toFixed(1)}K`;
  }
  if (metric === "pct") return formatGain(value);
  return `${value > 0 ? "+" : value < 0 ? "-" : ""}${Math.abs(value).toFixed(2)}R`;
}

/** The risk settings a goal mark reads. Absent is "off". */
export interface GoalSettings {
  daily_profit_target_usd?: unknown;
  daily_loss_limit_pct?: unknown;
}

const num = (v: unknown) => (typeof v === "number" ? v : Number(v)) || 0;

/**
 * Whether the day's running realised P&L touched the daily profit target or
 * the daily loss limit. DERIVED, not recorded: it applies TODAY's settings to
 * the day's closes, and the real loss limit also counts open positions'
 * float, which the rows do not hold. Touching counts: a day that reached +60
 * against a 50 target and closed at +30 reached it. The loss limit is a
 * percent of `dayOpen`; without one it is not marked.
 */
export function goalMarks(
  trades: CalendarTrade[], dayOpen: number | null, rs: GoalSettings,
): { goal: boolean; loss: boolean } {
  const curve = intradayCurve(trades);
  const target = num(rs.daily_profit_target_usd);
  const limitPct = num(rs.daily_loss_limit_pct);
  return {
    goal: target > 0 && curve.peak >= target,
    loss: limitPct > 0 && !!dayOpen && dayOpen > 0 && curve.low <= -(dayOpen * limitPct / 100),
  };
}
