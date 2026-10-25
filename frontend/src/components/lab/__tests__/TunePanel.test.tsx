import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TunePanel } from "../TunePanel";

vi.mock("../TuneCurveChart", () => ({ TuneCurveChart: () => null }));

const S = (trades: number, total: number, pf: number | null) => ({ trades, wins: 1, win_rate: 0.5, total_r: total, avg_r: 0,
  profit_factor: pf, best_r: 1, worst_r: -1, max_drawdown_r: 2, risk_pct: 0.5, compounded_return_pct: 0, curve: [] });
const RESULT = {
  strategy: "donchian_trend", coin: "BTC", interval: "4h", bars: 3000, from: 1, to: 2,
  grid: { ENTRY_N: [20, 30, 55] }, defaults: { ENTRY_N: 20 },
  folds: [{ train_from: 1, test_from: 2, test_to: 3, chosen: { ENTRY_N: 55, ladder: "trend", breakeven_after_tp: 0 },
    train: S(20, 6, 1.6), test: S(12, 3.2, 1.4), test_default: S(14, -2, 0.8), fallback: false }],
  oos: S(12, 3.2, 1.4), oos_default: S(14, -2, 0.8),
  proposal: { ENTRY_N: 55, ladder: "trend", tp_ladder: [[2, 0.3], [4, 0.3], [8, 0.4]], breakeven_after_tp: 0 },
  stability: 0.75, beats_default: true, profitable: true, candidates: 24, min_trades: 8,
};

afterEach(() => vi.unstubAllGlobals());

describe("Walk-forward tuning panel", () => {
  it("asks the server to tune, then shows out-of-sample results as a proposal only", async () => {
    const posts: [string, unknown][] = [];
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (path: string, init?: RequestInit) => {
      posts.push([path, JSON.parse(String(init?.body ?? "{}"))]);
      return new Response(JSON.stringify(RESULT));
    }));
    render(<TunePanel strategy="donchian_trend" coin="BTC" bars={3000} />);
    await userEvent.click(screen.getByRole("button", { name: /tune/i }));
    expect(posts).toEqual([["/api/backtest/tune", { strategy: "donchian_trend", coin: "BTC", bars: 3000, folds: 4 }]]);
    expect(await screen.findByText(/beat your defaults/i)).toBeInTheDocument();
    expect(screen.getByText(/proposal only/i)).toBeInTheDocument();
    expect(screen.getByText(/3 of 4|75%/)).toBeInTheDocument();
  });

  it("does not call losing less than the defaults a win, and marks folds that kept the defaults", async () => {
    const losing = { ...RESULT, oos: S(45, -7.2, 0.73), oos_default: S(74, -12.1, 0.72), profitable: false,
      folds: [{ ...RESULT.folds[0], fallback: true }] };
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => new Response(JSON.stringify(losing))));
    render(<TunePanel strategy="donchian_trend" coin="BTC" bars={3000} />);
    await userEvent.click(screen.getByRole("button", { name: /tune/i }));
    expect(await screen.findByText(/still lost money/i)).toBeInTheDocument();
    expect(screen.queryByText(/beat your defaults/i)).not.toBeInTheDocument();
    expect(screen.getByText(/kept defaults/i)).toBeInTheDocument();
  });
});
