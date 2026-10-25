import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MarketsPage } from "../MarketsPage";

// lightweight-charts needs a real canvas; the chart is not under test here.
vi.mock("../CandleChart", () => ({ CandleChart: () => null }));

const MARKETS = [
  { coin: "BTC", mark_price: 80000, funding_rate: 0.00001, open_interest: 10, day_notional_volume: 9e9,
    change_24h_pct: 1, scanned: true, max_leverage: 40, only_isolated: false },
  { coin: "kPEPE", mark_price: 0.01, funding_rate: 0.00002, open_interest: 1e9, day_notional_volume: 1e8,
    change_24h_pct: -2, scanned: true, max_leverage: 10, only_isolated: false },
];

function mockFetch(watchlist: string[]) {
  const posts: unknown[] = [];
  const fn = vi.fn().mockImplementation(async (path: string, init?: RequestInit) => {
    if (init?.method === "POST") posts.push(JSON.parse(String(init.body)));
    const body = path.startsWith("/api/markets") ? MARKETS
      : path.startsWith("/api/risk") ? { watchlist, blocklist: [], auto_top_n: 20 } : {};
    return new Response(JSON.stringify(body), { status: 200 });
  });
  vi.stubGlobal("fetch", fn);
  return posts;
}

afterEach(() => vi.unstubAllGlobals());

describe("Markets watchlist", () => {
  it("shows a mixed-case coin stored upper-cased as watched, and unwatching removes it", async () => {
    const posts = mockFetch(["KPEPE"]);
    render(<MarketsPage />);
    const row = (await screen.findByText("kPEPE")).closest("tr")!;
    const unwatch = within(row).getByRole("button", { name: /unwatch/i });
    await userEvent.click(unwatch);
    expect(posts).toEqual([{ fields: { watchlist: [] } }]);
  });
});
