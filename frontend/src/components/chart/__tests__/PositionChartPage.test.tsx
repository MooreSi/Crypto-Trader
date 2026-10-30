import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "@/App";

const levels: unknown[] = [];
vi.mock("@/components/markets/CandleChart", () => ({
  CandleChart: ({ levels: l }: { levels: unknown[] }) => { levels.push(l); return null; },
}));

const ACCOUNT = {
  network: "testnet", equity: 45, available: 4, margin_used: 20, day_start_equity: 45, day_pnl: 0,
  realised_today: 0, open_orders: [],
  positions: [{ coin: "UNI", size: -3.1, entry_price: 6.6, unrealised_pnl: 0.31, leverage: 1,
                liquidation_price: 12, margin_used: 20.5, direction: "short" }],
};
const OPEN = [{
  id: 24, engine: "reversal", coin: "UNI", direction: "short", status: "open", network: "testnet",
  entry_price: 6.6, size: 3.1, initial_size: 3.1, stop_loss: 7.2, initial_stop: 7.2, take_profits: [5.7],
  tp_hit: 0, leverage: 1, risk_usd: 1.86, opened_at: 0, closed_at: null, close_price: null,
  close_reason: null, realised_pnl: 0, fees: 0, net_pnl: 0, r_achieved: null,
}];

afterEach(() => { vi.unstubAllGlobals(); window.location.hash = ""; levels.length = 0; });

describe("#chart/<coin>", () => {
  it("opens a page for that coin with the trade's entry, stop and TP drawn on the chart", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (path: string) =>
      new Response(JSON.stringify(path === "/api/account" ? ACCOUNT : path === "/api/trades/open" ? OPEN : {}), { status: 200 })));
    window.location.hash = "chart/UNI";
    render(<App />);
    expect(await screen.findByText("To TP1")).toBeInTheDocument();
    expect(screen.getByText("-12.31%")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /close at market/i })).toBeInTheDocument();
    expect(levels.at(-1)).toEqual([
      { price: 6.6, color: expect.any(String), title: "Entry" },
      { price: 7.2, color: expect.any(String), title: "Stop" },
      { price: 5.7, color: expect.any(String), title: "TP1" },
    ]);
    expect(screen.queryByText("Strategy Lab")).toBeNull();  // no sidebar: a page of its own
  });
});
