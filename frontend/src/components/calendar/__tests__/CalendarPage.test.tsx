import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CalendarPage } from "../CalendarPage";

const ts = (iso: string) => Date.parse(iso) / 1000;
const ROWS = [
  { id: 2, engine: "reversal", coin: "ETH", direction: "short", opened_at: ts("2026-10-22T09:00:00Z"),
    closed_at: ts("2026-10-22T15:00:00Z"), day: "2026-10-22", net_pnl: -40, fees: 1, risk_usd: 80, r: -0.5,
    close_reason: "sl", session: "EU/US overlap" },
  { id: 1, engine: "breakout", coin: "BTC", direction: "long", opened_at: ts("2026-10-22T01:00:00Z"),
    closed_at: ts("2026-10-22T03:00:00Z"), day: "2026-10-22", net_pnl: 100, fees: 2, risk_usd: 50, r: 2,
    close_reason: "tp", session: "Asia" },
];

function mockFetch() {
  const posts: { path: string; body: unknown }[] = [];
  const fn = vi.fn().mockImplementation(async (path: string, init?: RequestInit) => {
    if (init?.method === "POST") {
      const body = JSON.parse(String(init.body));
      posts.push({ path, body });
      return new Response(JSON.stringify({ entry: { day: "2026-10-22", ...body, updated_at: 1 } }));
    }
    const body = path.startsWith("/api/calendar/trades") ? { today: "2026-10-24", rows: ROWS }
      : path.startsWith("/api/calendar/events") ? { events: [{ id: 1, uid: "u", ts: ts("2026-10-22T12:30:00Z"),
          day: "2026-10-22", title: "CPI", kind: "macro", impact: "high", coins: "", source: "feed" }] }
      : path.startsWith("/api/calendar/journal") ? { entries: [] }
      : path.startsWith("/api/account") ? { equity: 1060 }
      : path.startsWith("/api/risk") ? { daily_profit_target_usd: 80, daily_loss_limit_pct: 3 }
      : {};
    return new Response(JSON.stringify(body), { status: 200 });
  });
  vi.stubGlobal("fetch", fn);
  return posts;
}

// This Node's jsdom has no working localStorage; the page must cope either way,
// and this test checks the metric is remembered, so give it a plain one.
beforeEach(() => {
  const store = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
  });
});

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("Calendar", () => {
  it("opens on the month of the newest close, with the day's net, gain and marks", async () => {
    mockFetch();
    render(<CalendarPage />);
    expect(await screen.findByTestId("calendar-month")).toHaveTextContent("October 2026");
    const day = await screen.findByTestId("day-2026-10-22");
    expect(within(day).getByTestId("day-metric-2026-10-22")).toHaveTextContent("+$60.00");
    // Opened on 1060 - 60 = 1000, so +6.00%.
    expect(within(day).getByTestId("day-gain-2026-10-22")).toHaveTextContent("+6.00%");
    expect(within(day).getByTestId("goal-mark-2026-10-22")).toBeInTheDocument();   // peak +100 >= 80
    // Its low was 0 (the win closed first), nowhere near 3% of 1000.
    expect(within(day).queryByTestId("loss-mark-2026-10-22")).toBeNull();
    expect(await within(day).findByTestId("news-mark-2026-10-22")).toBeInTheDocument();
    expect(screen.getByTestId("day-2026-10-24").className).toMatch(/ring-2/);       // today
  });

  it("switches the cell figure to R and remembers it", async () => {
    mockFetch();
    render(<CalendarPage />);
    await screen.findByTestId("day-2026-10-22");
    await userEvent.click(screen.getByRole("button", { name: "R" }));
    expect(screen.getByTestId("day-metric-2026-10-22")).toHaveTextContent("+1.50R");
    expect(localStorage.getItem("calendar/metric")).toBe("r");
  });

  it("opens a day with its stats, breakdowns, events and trades, and saves the journal", async () => {
    const posts = mockFetch();
    render(<CalendarPage />);
    await userEvent.click(await screen.findByTestId("day-2026-10-22"));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByTestId("stat-pf")).toHaveTextContent("2.50");
    expect(within(dialog).getByTestId("engine-breakout")).toHaveTextContent("+$100.00");
    expect(within(dialog).getByTestId("coin-ETH")).toHaveTextContent("-$40.00");
    expect(within(dialog).getByTestId("session-Asia")).toBeInTheDocument();
    expect(within(dialog).getByText("CPI")).toBeInTheDocument();
    expect(within(dialog).getByTestId("trade-1")).toHaveTextContent("BTC");
    await userEvent.type(within(dialog).getByLabelText("Journal note"), "good patience");
    await userEvent.type(within(dialog).getByLabelText("Tags"), "a, b, a");
    await userEvent.click(within(dialog).getByRole("button", { name: "Mood 4 of 5" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(posts).toEqual([{ path: "/api/calendar/journal/2026-10-22",
                             body: { note: "good patience", tags: ["a", "b"], mood: 4 } }]);
  });

  it("shows the year with each month's total and opens a month from it", async () => {
    mockFetch();
    render(<CalendarPage />);
    await screen.findByTestId("day-2026-10-22");
    await userEvent.click(screen.getByRole("button", { name: "Year" }));
    expect(screen.getByTestId("calendar-year")).toHaveTextContent("2026");
    expect(screen.getByTestId("year-month-10")).toHaveTextContent("+$60.00");
    await userEvent.click(screen.getByTestId("year-month-9"));
    expect(screen.getByTestId("calendar-month")).toHaveTextContent("September 2026");
  });
});
