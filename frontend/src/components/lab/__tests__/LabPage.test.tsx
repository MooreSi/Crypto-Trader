import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LabPage } from "../LabPage";

vi.mock("../RCurveChart", () => ({ RCurveChart: () => null }));

const STRATS = [
  { name: "breakout", interval: "15m", htf: null, kind: "engine", about: "Range break." },
  { name: "donchian_trend", interval: "4h", htf: "1d", kind: "lab", about: "Donchian ensemble." },
];
const RESULT = {
  strategy: "donchian_trend", coin: "ETH", interval: "4h", bars: 1500, from: 1, to: 2, ladder: [[1, 0.5]],
  summary: { trades: 4, wins: 3, win_rate: 0.75, total_r: 2.5, avg_r: 0.625, profit_factor: 3.5, best_r: 1.75,
    worst_r: -1, max_drawdown_r: 1, risk_pct: 0.5, compounded_return_pct: 1.26, curve: [] },
  trades: [{ opened_at: 1, closed_at: 2, direction: "long", entry: 100, stop: 95, r: 1.75, exit: "tp", tp_hits: 3, reason: "x" }],
};

afterEach(() => vi.unstubAllGlobals());

describe("Strategy Lab", () => {
  it("runs a backtest of the chosen strategy and coin and shows the result", async () => {
    const posts: unknown[] = [];
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (path: string, init?: RequestInit) => {
      if (init?.method === "POST") { posts.push(JSON.parse(String(init.body))); return new Response(JSON.stringify(RESULT)); }
      return new Response(JSON.stringify(path.includes("strategies") ? STRATS : []));
    }));
    render(<LabPage />);
    await userEvent.click(await screen.findByRole("button", { name: /donchian trend/i }));
    const coin = screen.getByLabelText(/coin/i);
    await userEvent.clear(coin);
    await userEvent.type(coin, "eth");
    await userEvent.click(screen.getByRole("button", { name: /run backtest/i }));
    expect(posts).toEqual([{ strategy: "donchian_trend", coin: "ETH", bars: 1500 }]);
    expect(await screen.findByText("75%")).toBeInTheDocument();
    expect(screen.getByText(/never places an order/i)).toBeInTheDocument();
  });
});
