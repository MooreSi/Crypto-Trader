import { describe, expect, it } from "vitest";
import type { CalendarTrade } from "@/api/types";
import {
  breakdown, dayGains, dayOpenBalances, formatGain, groupByDay, monthGrid, periodGain,
} from "../calendarGrid";

let next = 1;
function t(day: string, pnl: number, extra: Partial<CalendarTrade> = {}): CalendarTrade {
  const ts = Date.parse(`${day}T12:00:00Z`) / 1000;
  return {
    id: next++, engine: "breakout", coin: "BTC", direction: "long", opened_at: ts - 3600,
    closed_at: ts, day, net_pnl: pnl, fees: 1, risk_usd: 10, r: pnl / 10, close_reason: "tp",
    session: "US", ...extra,
  };
}

describe("monthGrid", () => {
  it("is Monday-first, padded to whole weeks, and totals only its own days", () => {
    // October 2026 starts on a Thursday.
    const rows = [t("2026-09-30", 50), t("2026-10-01", 10), t("2026-10-01", -4), t("2026-10-31", 7)];
    const g = monthGrid(rows, 2026, 10);
    expect(g.weeks[0]!.days.map((d) => d.date).slice(0, 4))
      .toEqual(["2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01"]);
    expect(g.weeks.every((w) => w.days.length === 7)).toBe(true);
    expect(g.pnl).toBe(13);
    expect(g.trades).toBe(3);
    expect(g.weeks[0]!.pnl).toBe(6);          // September's 50 is padding, not counted
    expect(g.weeks[0]!.days[2]!.inMonth).toBe(false);
  });
});

describe("gains", () => {
  it("measures each day against the balance it opened on", () => {
    // Balance now 1100: +100 on the 2nd, so the 2nd opened on 1000 and the 1st on 1050.
    const rows = [t("2026-10-02", 100), t("2026-10-01", -50)];
    const opens = dayOpenBalances(rows, 1100);
    expect(opens.get("2026-10-02")).toBe(1000);
    expect(opens.get("2026-10-01")).toBe(1050);
    expect(dayGains(rows, 1100).get("2026-10-02")).toBeCloseTo(10);
    expect(dayGains(rows, 1100).get("2026-10-01")).toBeCloseTo(-50 / 1050 * 100);
  });

  it("gives no percentages without a balance or from a balance at or below zero", () => {
    expect(dayGains([t("2026-10-02", 100)], null).size).toBe(0);
    expect(dayGains([t("2026-10-02", 100)], 50).size).toBe(0);
  });

  it("a period's gain is of the balance the period opened on, not a sum of days", () => {
    const rows = [t("2026-10-03", 30), t("2026-10-02", 100), t("2026-10-01", -50)];
    // Balance 1080. After the 2nd: +30. Period 1st-2nd: +50 on 1080-30-50 = 1000.
    expect(periodGain(rows, 1080, "2026-10-01", "2026-10-02")).toBeCloseTo(5);
    expect(periodGain(rows, 1080, "2026-11-01", "2026-11-31")).toBeNull();
    expect(periodGain(rows, null, "2026-10-01", "2026-10-31")).toBeNull();
  });

  it("formats signed to two places", () => {
    expect(formatGain(1.234)).toBe("+1.23%");
    expect(formatGain(-0.4)).toBe("-0.40%");
  });
});

describe("breakdown", () => {
  it("tallies money and wins by a key, worst first", () => {
    const rows = [t("2026-10-01", 10, { coin: "ETH" }), t("2026-10-01", -20, { coin: "BTC" }),
                  t("2026-10-01", 5, { coin: "ETH" })];
    expect(breakdown(rows, (x) => x.coin)).toEqual([
      { key: "BTC", pnl: -20, n: 1, wins: 0 },
      { key: "ETH", pnl: 15, n: 2, wins: 2 },
    ]);
  });

  it("groups by day", () => {
    expect([...groupByDay([t("2026-10-01", 1), t("2026-10-01", 2)]).values()][0]).toHaveLength(2);
  });
});
