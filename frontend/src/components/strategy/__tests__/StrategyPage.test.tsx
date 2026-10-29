import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrategyPage } from "../StrategyPage";
import { exitPlan } from "../strategyFields";

const PARAMS = {
  risk_per_trade_pct: 5, max_leverage: 1, max_position_notional_pct: 45, min_stop_pct: 1.5, entry_slippage_pct: 0.5,
  min_reward_risk: 1.5, ml_min_probability: 0.5, ml_require_model: false, max_funding_rate_pct: 0.05,
  blackout_enabled: true, blackout_include_medium: false, blackout_minutes_before: 30, blackout_minutes_after: 30,
  tp_ladder: [[1.5, 0.8]], breakeven_after_tp: 1, stop_lock_r: 1.5, trail_atr_mult: 1.5,
  max_open_positions: 2, max_same_direction: 2, daily_loss_limit_pct: 20, daily_profit_target_usd: 0,
};
const LIST = {
  active: "a1", drift: [], keys: Object.keys(PARAMS), current: PARAMS,
  items: [
    { id: "a1", name: "TP1 80% at 1.5R + trailed runner", notes: "", params: PARAMS, created_at: 1, updated_at: 1 },
    { id: "b2", name: "Two TPs", notes: "", params: { ...PARAMS, tp_ladder: [[1, 0.5], [2, 0.5]], stop_lock_r: 0, trail_atr_mult: 0 },
      created_at: 2, updated_at: 2 },
  ],
};

function mockFetch() {
  const calls: { method: string; path: string; body?: unknown }[] = [];
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async (path: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    calls.push({ method, path, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    const body = method === "POST" && path === "/api/strategies" ? { ...LIST.items[1], id: "c3", name: "Copy" } : LIST;
    return new Response(JSON.stringify(body), { status: 200 });
  }));
  vi.stubGlobal("confirm", () => true);
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe("exitPlan", () => {
  it("describes TP1, the runner, the lock and the trail", () => {
    const text = exitPlan(PARAMS);
    expect(text).toContain("80% at 1.5R");
    expect(text).toContain("20% runner");
    expect(text).toContain("stop to 1.5R");
    expect(text).toContain("1.5 x ATR");
  });
  it("says breakeven when there is no lock", () => {
    expect(exitPlan({ ...PARAMS, stop_lock_r: 0, tp_ladder: [[1, 1]], trail_atr_mult: 0 })).toContain("stop to breakeven");
  });
});

describe("Strategy page", () => {
  it("marks the active strategy and activates another", async () => {
    const calls = mockFetch();
    render(<StrategyPage />);
    const active = (await screen.findAllByText("TP1 80% at 1.5R + trailed runner"))[0].closest("li")!;
    expect(within(active).getByText(/active/i)).toBeTruthy();
    const other = screen.getByText("Two TPs").closest("li")!;
    await userEvent.click(within(other).getByRole("button", { name: /activate/i }));
    expect(calls.some((c) => c.method === "POST" && c.path === "/api/strategies/b2/activate")).toBe(true);
  });

  it("saves an edited ladder rung", async () => {
    const calls = mockFetch();
    render(<StrategyPage />);
    await screen.findAllByText("TP1 80% at 1.5R + trailed runner");
    const share = screen.getByLabelText("TP1 share %");
    await userEvent.clear(share);
    await userEvent.type(share, "70");
    await userEvent.click(screen.getByRole("button", { name: /save strategy/i }));
    const put = calls.find((c) => c.method === "PUT");
    expect(put?.path).toBe("/api/strategies/a1");
    expect((put?.body as { params: { tp_ladder: number[][] } }).params.tp_ladder).toEqual([[1.5, 0.7]]);
  });
});
