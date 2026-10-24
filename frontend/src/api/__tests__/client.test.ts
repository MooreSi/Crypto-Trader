import { afterEach, describe, expect, it, vi } from "vitest";
import { api, CSRF_HEADER } from "../client";

function mockFetch(status = 200, body: unknown = {}) {
  const fn = vi.fn().mockImplementation(async () => new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("adds the CSRF header to every write", async () => {
    const fetch = mockFetch();
    await api.post("/api/system/pause", { paused: true });
    await api.del("/api/events/1");
    for (const call of fetch.mock.calls) {
      expect(call[1].headers[CSRF_HEADER]).toBe("1");
    }
  });

  it("does not add it to reads", async () => {
    const fetch = mockFetch();
    await api.get("/api/account");
    expect(fetch.mock.calls[0][1].headers[CSRF_HEADER]).toBeUndefined();
  });

  it("surfaces the server's refusal message verbatim", async () => {
    mockFetch(400, { detail: "unknown risk setting 'x'" });
    await expect(api.post("/api/risk", {})).rejects.toThrow("unknown risk setting 'x'");
  });
});
