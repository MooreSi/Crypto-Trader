import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DashboardPage } from "../DashboardPage";

vi.mock("../EquityChart", () => ({ EquityChart: () => null }));
vi.mock("../MarketPulseCard", () => ({ MarketPulseCard: () => null }));

const ACCOUNT = {
  network: "testnet", equity: 45, available: 4, margin_used: 41, day_start_equity: 45, day_pnl: 0,
  realised_today: 0, open_orders: [],
  positions: [
    { coin: "UNI", size: -3.1, entry_price: 6.6, unrealised_pnl: 0.31, leverage: 1, liquidation_price: 12,
      margin_used: 20.5, direction: "short" },
    { coin: "HYPE", size: 1, entry_price: 30, unrealised_pnl: 0, leverage: 1, liquidation_price: null,
      margin_used: 30, direction: "long" },
  ],
};

const OPEN = [{
  id: 24, engine: "reversal", coin: "UNI", direction: "short", status: "open", network: "testnet",
  entry_price: 6.6, size: 3.1, initial_size: 3.1, stop_loss: 7.2, initial_stop: 7.2, take_profits: [5.7],
  tp_hit: 0, leverage: 1, risk_usd: 1.86, opened_at: 0, closed_at: null, close_price: null,
  close_reason: null, realised_pnl: 0, fees: 0, net_pnl: 0, r_achieved: null,
}];

function mockFetch() {
  const fn = vi.fn().mockImplementation(async (path: string) => {
    const body = path === "/api/account" ? ACCOUNT
      : path === "/api/trades/open" ? OPEN
      : path.endsWith("/close") ? { closed: true }
      : path.startsWith("/api/account/equity") ? [] : {};
    return new Response(JSON.stringify(body), { status: 200 });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

const posted = (fetch: ReturnType<typeof mockFetch>) =>
  fetch.mock.calls.filter((c) => c[1]?.method === "POST").map((c) => c[0]);

afterEach(() => vi.unstubAllGlobals());

describe("Dashboard positions", () => {
  it("shows the next TP and stop with the move needed to reach each", async () => {
    mockFetch();
    render(<DashboardPage status={null} />);
    const row = (await screen.findByText("UNI")).closest("tr")!;
    // mark = 6.6 + 0.31 / -3.1 = 6.5; TP 5.7 is -12.3% away, stop 7.2 is +10.8%
    expect(await within(row).findByText("-12.31%")).toBeInTheDocument();
    expect(within(row).getByText("+10.77%")).toBeInTheDocument();
    expect(within(row).getByText(/TP1/)).toBeInTheDocument();
  });

  it("opens the coin's chart in a new page from the coin link and from the row", async () => {
    mockFetch();
    const open = vi.fn();
    vi.stubGlobal("open", open);
    render(<DashboardPage status={null} />);
    const link = await screen.findByRole("link", { name: "UNI" });
    expect(link).toHaveAttribute("href", "#chart/UNI");
    expect(link).toHaveAttribute("target", "_blank");
    await userEvent.click(screen.getByText("+10.77%"));
    expect(open).toHaveBeenCalledWith("#chart/UNI", "_blank");
  });

  it("closes a managed position after asking, through the trade's close endpoint", async () => {
    const fetch = mockFetch();
    const confirm = vi.fn(() => true);
    vi.stubGlobal("confirm", confirm);
    vi.stubGlobal("open", vi.fn());
    render(<DashboardPage status={null} />);
    const row = (await screen.findByText("UNI")).closest("tr")!;
    await userEvent.click(await within(row).findByRole("button", { name: /close/i }));
    expect(confirm).toHaveBeenCalledOnce();
    expect(posted(fetch)).toEqual(["/api/trades/24/close"]);
  });

  it("does not close when the owner cancels", async () => {
    const fetch = mockFetch();
    vi.stubGlobal("confirm", vi.fn(() => false));
    vi.stubGlobal("open", vi.fn());
    render(<DashboardPage status={null} />);
    const row = (await screen.findByText("UNI")).closest("tr")!;
    await userEvent.click(await within(row).findByRole("button", { name: /close/i }));
    expect(posted(fetch)).toEqual([]);
  });

  it("offers no close for a position the app did not open", async () => {
    mockFetch();
    render(<DashboardPage status={null} />);
    const row = (await screen.findByText("HYPE")).closest("tr")!;
    await screen.findAllByRole("button", { name: /close/i });
    expect(within(row).queryByRole("button", { name: /close/i })).toBeNull();
    expect(within(row).getByText(/not managed/i)).toBeInTheDocument();
  });
});
