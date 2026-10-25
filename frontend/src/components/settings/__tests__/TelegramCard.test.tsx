import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TelegramCard } from "../TelegramCard";
import type { AppSettings } from "@/api/types";

const S = { telegram_enabled: false, telegram_chat_id: "", has_telegram_token: false } as AppSettings;

afterEach(() => vi.unstubAllGlobals());

describe("Telegram alerts", () => {
  it("sends the token once, clears the box, and never shows it back", async () => {
    const posts: [string, unknown][] = [];
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (path: string, init?: RequestInit) => {
      posts.push([path, JSON.parse(String(init?.body ?? "{}"))]);
      return new Response(JSON.stringify({ ...S, telegram_enabled: true, telegram_chat_id: "42", has_telegram_token: true }));
    }));
    const applied: AppSettings[] = [];
    render(<TelegramCard s={S} apply={(v) => applied.push(v)} />);
    await userEvent.type(screen.getByLabelText(/chat id/i), "42");
    const token = screen.getByLabelText(/bot token/i);
    await userEvent.type(token, "123456789:SECRETSECRETSECRETSECRET");
    await userEvent.click(screen.getByRole("button", { name: /save and enable/i }));
    expect(posts[0]).toEqual(["/api/settings/telegram", { enabled: true, chat_id: "42", token: "123456789:SECRETSECRETSECRETSECRET" }]);
    expect((token as HTMLInputElement).value).toBe("");
    expect(applied[0].has_telegram_token).toBe(true);
  });
});
