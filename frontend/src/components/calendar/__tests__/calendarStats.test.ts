import { describe, expect, it } from "vitest";
import type { CalendarTrade } from "@/api/types";
import type { DayCell } from "../calendarGrid";
import {
  cellMetric, dayStats, formatMetric, goalMarks, intradayCurve, streaks, weekdayTotals,
} from "../calendarStats";

let next = 1;
function t(pnl: number, closed_at = next * 60, r: number | null = pnl / 10): CalendarTrade {
  return {
    id: next++, engine: "breakout", coin: "BTC", direction: "long", opened_at: 0, closed_at,
    day: "2026-10-01", net_pnl: pnl, fees: 0.5, risk_usd: 10, r, close_reason: null, session: "US",
  };
}

function cell(date: string, pnls: number[], inMonth = true): DayCell {
  const trades = pnls.map((p) => t(p));
  return { date, day: Number(date.slice(8)), inMonth, trades, pnl: pnls.reduce((s, p) => s + p, 0) };
}

describe("dayStats", () => {
  it("profit factor, averages, best, worst and fees", () => {
    const s = dayStats([t(30), t(-10), t(10), t(-5)]);
    expect(s.profitFactor).toBeCloseTo(40 / 15);
    expect(s.avgWin).toBe(20);
    expect(s.avgLoss).toBe(-7.5);
    expect(s.best).toBe(30);
    expect(s.worst).toBe(-10);
    expect(s.fees).toBe(2);
  });

  it("has no profit factor without a loser", () => {
    expect(dayStats([t(5)]).profitFactor).toBeNull();
  });
});

describe("intradayCurve", () => {
  it("walks the closes in time order and measures the fall from the peak", () => {
    const c = intradayCurve([t(-5, 300), t(20, 100), t(-12, 200)]);
    expect(c.points.map((p) => p.cum)).toEqual([0, 20, 8, 3]);
    expect(c.peak).toBe(20);
    expect(c.maxDrawdown).toBe(17);
  });
});

describe("streaks", () => {
  it("skips untraded days, breaks on a flat day and ignores padding", () => {
    const s = streaks([
      cell("2026-09-30", [-9], false),
      cell("2026-10-01", [5]), cell("2026-10-02", []), cell("2026-10-03", [4]),
      cell("2026-10-04", [-1]), cell("2026-10-05", [2, -2]), cell("2026-10-06", [-3]),
    ]);
    expect(s.greenDays).toBe(2);
    expect(s.redDays).toBe(2);
    expect(s.longestGreen).toBe(2);
    expect(s.longestRed).toBe(1);
    expect(s.current).toEqual({ kind: "red", length: 1 });
  });
});

describe("weekdayTotals", () => {
  it("files each in-month day under its UTC weekday, Monday first", () => {
    // 2026-10-05 is a Monday, 2026-10-11 a Sunday.
    const out = weekdayTotals([cell("2026-10-05", [3, -1]), cell("2026-10-11", [7]),
                               cell("2026-09-28", [100], false)]);
    expect(out[0]).toEqual({ label: "Mon", pnl: 2, n: 2, wins: 1 });
    expect(out[6]).toEqual({ label: "Sun", pnl: 7, n: 1, wins: 1 });
  });
});

describe("cell metrics", () => {
  it("$ is the day's net, % its gain, R the sum of trades that carry one", () => {
    const c: DayCell = { ...cell("2026-10-01", []), trades: [t(10, 60, 1), t(-5, 120, null)], pnl: 5 };
    expect(cellMetric(c, "usd", 0.5)).toBe(5);
    expect(cellMetric(c, "pct", 0.5)).toBe(0.5);
    expect(cellMetric(c, "r", null)).toBe(1);
    const none: DayCell = { ...c, trades: [t(1, 60, null)] };
    expect(cellMetric(none, "r", null)).toBeNull();
  });

  it("formats short enough for a cell", () => {
    expect(formatMetric("usd", 12_400)).toBe("+$12.4K");
    expect(formatMetric("usd", -3.5)).toBe("-$3.50");
    expect(formatMetric("r", 1.5)).toBe("+1.50R");
    expect(formatMetric("pct", null)).toBe("-");
  });
});

describe("goalMarks", () => {
  it("marks a touched profit target, even when the day gave some back", () => {
    const trades = [t(60, 100), t(-30, 200)];
    expect(goalMarks(trades, 1000, { daily_profit_target_usd: 50, daily_loss_limit_pct: 3 }))
      .toEqual({ goal: true, loss: false });
    expect(goalMarks(trades, 1000, { daily_profit_target_usd: 0 }).goal).toBe(false);
  });

  it("marks the loss limit against the day's opening balance, and not without one", () => {
    const trades = [t(-31, 100)];
    expect(goalMarks(trades, 1000, { daily_loss_limit_pct: 3 }).loss).toBe(true);
    expect(goalMarks(trades, 2000, { daily_loss_limit_pct: 3 }).loss).toBe(false);
    expect(goalMarks(trades, null, { daily_loss_limit_pct: 3 }).loss).toBe(false);
  });
});
