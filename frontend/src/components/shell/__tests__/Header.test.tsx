import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Header } from "../Header";
import type { SystemStatus } from "@/api/types";

const STATUS = {
  paused: false, network: "testnet", started_at: 100, uptime_s: 5, exchange_ok: true,
} as unknown as SystemStatus;

function mockFetch() {
  const fn = vi.fn().mockImplementation(async (path: string) =>
    new Response(JSON.stringify(path.endsWith("/status") ? STATUS : { action: "ok" }), { status: 200 }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

const posted = (fetch: ReturnType<typeof mockFetch>) =>
  fetch.mock.calls.filter((c) => c[1]?.method === "POST").map((c) => c[0]);

afterEach(() => vi.unstubAllGlobals());

describe("Header stop and restart", () => {
  it("asks first, then asks the server to stop and says it has stopped", async () => {
    const fetch = mockFetch();
    vi.stubGlobal("confirm", vi.fn(() => true));
    render(<Header status={STATUS} reload={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /stop/i }));
    expect(posted(fetch)).toEqual(["/api/system/stop"]);
    expect(await screen.findByText(/Crypto Trader is stopped/i)).toBeInTheDocument();
  });

  it("asks the server to restart and shows that it is restarting", async () => {
    const fetch = mockFetch();
    vi.stubGlobal("confirm", vi.fn(() => true));
    render(<Header status={STATUS} reload={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /restart/i }));
    expect(posted(fetch)).toEqual(["/api/system/restart"]);
    expect(await screen.findByText(/restarting/i)).toBeInTheDocument();
  });

  it("does nothing when the confirmation is cancelled", async () => {
    const fetch = mockFetch();
    vi.stubGlobal("confirm", vi.fn(() => false));
    render(<Header status={STATUS} reload={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /stop/i }));
    await userEvent.click(screen.getByRole("button", { name: /restart/i }));
    expect(posted(fetch)).toEqual([]);
  });
});
