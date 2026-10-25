import { useState } from "react";
import { BellRing, Send } from "lucide-react";
import { api } from "@/api/client";
import type { AppSettings } from "@/api/types";
import { Badge, Button, Card, Notice, Switch, inputCls } from "@/components/shared/ui";

/** Trade alerts to the owner's Telegram: opens, TPs, stop moves, closes. */
export function TelegramCard({ s, apply }: { s: AppSettings; apply: (v: AppSettings) => void }) {
  const [chat, setChat] = useState(s.telegram_chat_id);
  const [token, setToken] = useState("");
  const [msg, setMsg] = useState<{ tone: "profit" | "loss"; text: string } | null>(null);

  const save = async (enabled: boolean) => {
    try {
      apply(await api.post<AppSettings>("/api/settings/telegram", { enabled, chat_id: chat, token }));
      setToken("");
      setMsg({ tone: "profit", text: enabled ? "Saved. Alerts start with the next trade event." : "Alerts off." });
    } catch (e) { setMsg({ tone: "loss", text: String(e) }); }
  };
  const test = async () => {
    try {
      await api.post("/api/settings/telegram/test");
      setMsg({ tone: "profit", text: "Test message sent. Check Telegram." });
    } catch (e) { setMsg({ tone: "loss", text: String(e) }); }
  };

  return (
    <Card title="Telegram trade alerts" icon={<BellRing className="h-4 w-4" />}
          right={s.telegram_enabled ? <Badge tone="profit" dot>on</Badge> : <Badge>off</Badge>}>
      <p className="mb-3 text-xs text-muted">
        A message for every open, take-profit, stop move and close. Create a bot with @BotFather, send it /start, and get
        your chat id from @userinfobot. The token is stored in your operating system's keychain and never shown again.
      </p>
      <div className="grid gap-2 sm:grid-cols-[1fr_2fr]">
        <input aria-label="Chat id" value={chat} onChange={(e) => setChat(e.target.value)} placeholder="Chat id, e.g. 123456789"
               className={`${inputCls} num`} />
        <input aria-label="Bot token" type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)}
               placeholder={s.has_telegram_token ? "Token stored (leave blank to keep)" : "Bot token, 123456789:AA..."}
               className={`${inputCls} font-mono`} />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button tone="accent" onClick={() => save(true)}>Save and enable</Button>
        <Button onClick={test} disabled={!s.has_telegram_token}><Send className="h-3.5 w-3.5" />Send test</Button>
        {s.telegram_enabled && (
          <span className="ml-auto flex items-center gap-2 text-sm text-muted">Enabled <Switch label="telegram alerts" on onChange={() => save(false)} /></span>
        )}
      </div>
      {msg && <div className="mt-3"><Notice tone={msg.tone}>{msg.text}</Notice></div>}
    </Card>
  );
}
