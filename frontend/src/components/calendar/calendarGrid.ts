import type { CalendarTrade } from "@/api/types";

/**
 * Closed trades arranged as a month, ported from FOREX Trader's Analysis
 * calendar. The day a trade belongs to is the backend's `row.day`: the UTC
 * date it closed on, the same trading day the risk governor resets on
 * (services/risk/day.py). The browser never works it out, so a viewer in
 * another timezone sees the same days as the loss limit.
 */

export interface DayCell {
  /** YYYY-MM-DD, UTC. */
  date: string;
  day: number;
  pnl: number;
  trades: CalendarTrade[];
  /** False for the leading and trailing cells that pad the grid. */
  inMonth: boolean;
}

export interface WeekRow { days: DayCell[]; pnl: number; trades: number }

export interface MonthGrid {
  year: number;
  /** 1-12. */
  month: number;
  weeks: WeekRow[];
  pnl: number;
  trades: number;
}

const net = (t: CalendarTrade) => Number(t.net_pnl) || 0;
const sum = (ts: CalendarTrade[]) => ts.reduce((s, t) => s + net(t), 0);

export function groupByDay(rows: CalendarTrade[]): Map<string, CalendarTrade[]> {
  const out = new Map<string, CalendarTrade[]>();
  for (const row of rows) {
    const bucket = out.get(row.day);
    if (bucket) bucket.push(row);
    else out.set(row.day, [row]);
  }
  return out;
}

/**
 * Each traded day's opening balance: the balance now minus everything realised
 * from that day on. Deposits and withdrawals are not in the trade rows, so a
 * day before one is measured against a balance the account did not have.
 * Empty without a balance; values may be at or below zero, and every reader
 * must check.
 */
export function dayOpenBalances(rows: CalendarTrade[], balance: number | null): Map<string, number> {
  const out = new Map<string, number>();
  if (balance == null || !Number.isFinite(balance)) return out;
  const byDay = groupByDay(rows);
  let after = 0;
  for (const day of [...byDay.keys()].sort().reverse()) {
    const pnl = sum(byDay.get(day)!);
    out.set(day, balance - after - pnl);
    after += pnl;
  }
  return out;
}

/** Each traded day's gain, as a percent of the balance it opened on. A day
 *  whose opening balance is at or below zero has none. */
export function dayGains(rows: CalendarTrade[], balance: number | null): Map<string, number> {
  const out = new Map<string, number>();
  const byDay = groupByDay(rows);
  for (const [day, open] of dayOpenBalances(rows, balance)) {
    if (open > 0) out.set(day, (sum(byDay.get(day)!) / open) * 100);
  }
  return out;
}

/**
 * A run of days' gain (a week, a month, a year) as a percent of the balance
 * the run OPENED on, not the sum of the days' percentages. `from` and `to` are
 * inclusive and compared as strings, so YYYY-MM-31 ends any month.
 */
export function periodGain(
  rows: CalendarTrade[], balance: number | null, from: string, to: string,
): number | null {
  if (balance == null || !Number.isFinite(balance)) return null;
  let pnl = 0, after = 0, n = 0;
  for (const [day, trades] of groupByDay(rows)) {
    if (day > to) after += sum(trades);
    else if (day >= from) { pnl += sum(trades); n += trades.length; }
  }
  const open = balance - after - pnl;
  return n > 0 && open > 0 ? (pnl / open) * 100 : null;
}

export function formatGain(pct: number): string {
  return `${pct > 0 ? "+" : ""}${pct.toFixed(2)}%`;
}

function iso(y: number, m: number, d: number): string {
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

/** A Monday-first month grid, padded to whole weeks. Weekly totals count only
 *  this month's days, so no trade is counted in two months. */
export function monthGrid(rows: CalendarTrade[], year: number, month: number): MonthGrid {
  const byDay = groupByDay(rows);
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const lead = (new Date(Date.UTC(year, month - 1, 1)).getUTCDay() + 6) % 7;

  const cells: DayCell[] = [];
  const push = (y: number, m: number, d: number, inMonth: boolean) => {
    const date = iso(y, m, d);
    const trades = byDay.get(date) ?? [];
    cells.push({ date, day: d, inMonth, trades, pnl: sum(trades) });
  };

  const prevMonth = month === 1 ? 12 : month - 1;
  const prevYear = month === 1 ? year - 1 : year;
  const prevDays = new Date(Date.UTC(prevYear, prevMonth, 0)).getUTCDate();
  for (let i = lead; i > 0; i--) push(prevYear, prevMonth, prevDays - i + 1, false);
  for (let d = 1; d <= daysInMonth; d++) push(year, month, d, true);
  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  let trail = 1;
  while (cells.length % 7 !== 0) push(nextYear, nextMonth, trail++, false);

  const weeks: WeekRow[] = [];
  for (let i = 0; i < cells.length; i += 7) {
    const days = cells.slice(i, i + 7);
    weeks.push({
      days,
      pnl: days.reduce((s, c) => s + (c.inMonth ? c.pnl : 0), 0),
      trades: days.reduce((s, c) => s + (c.inMonth ? c.trades.length : 0), 0),
    });
  }
  const own = cells.filter((c) => c.inMonth);
  return {
    year, month, weeks,
    pnl: own.reduce((s, c) => s + c.pnl, 0),
    trades: own.reduce((s, c) => s + c.trades.length, 0),
  };
}

export interface Tally { key: string; pnl: number; n: number; wins: number }

/** Money and wins per key (engine, coin, session), worst first. */
export function breakdown(trades: CalendarTrade[], keyOf: (t: CalendarTrade) => string): Tally[] {
  const acc = new Map<string, Tally>();
  for (const t of trades) {
    const key = keyOf(t) || "-";
    const cur = acc.get(key) ?? { key, pnl: 0, n: 0, wins: 0 };
    cur.pnl += net(t);
    cur.n += 1;
    if (net(t) > 0) cur.wins += 1;
    acc.set(key, cur);
  }
  return [...acc.values()].sort((a, b) => a.pnl - b.pnl);
}
