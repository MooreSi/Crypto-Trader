import { Activity, BellRing, BookOpen, Brain, FlaskConical, ShieldCheck } from "lucide-react";
import { api } from "@/api/client";
import type { Release } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { Card } from "@/components/shared/ui";

const PILLARS = [
  { icon: Activity, title: "Three live-capable engines", text: "Breakout, ICT reversal and trend pullback, scanning the most traded Hyperliquid perps 24/7." },
  { icon: Brain, title: "Self-learning, with a gate", text: "Every signal is tracked to +1R or the stop. Each engine retrains daily and a model is used only if it beats chance on data it never saw." },
  { icon: FlaskConical, title: "Strategy Lab", text: "Backtest any engine or Lab strategy (Donchian trend, Bollinger-RSI reversion, Supertrend) with the app's own exit plan." },
  { icon: ShieldCheck, title: "Exchange-side protection", text: "Stops and take-profits sit on the exchange, so positions stay protected while the app is closed." },
  { icon: BellRing, title: "Alerts", text: "Optional Telegram messages for every open, take-profit, stop move and close." },
];

export function AboutPage() {
  const { data } = usePoll(() => api.get<Release[]>("/api/system/releases"), 600000);
  return (
    <div className="space-y-5">
      <section className="panel fade-up relative overflow-hidden rounded-2xl p-6 sm:p-8">
        <div className="grad-fill pointer-events-none absolute -top-24 -right-24 h-64 w-64 rounded-full opacity-20 blur-3xl" />
        <h2 className="text-2xl font-semibold tracking-tight">Crypto <span className="grad-text">Trader</span></h2>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          Automated trading of Hyperliquid perpetuals, 24 hours a day, 7 days a week, from your own computer. Engines only
          trade when you switch them live and every risk gate passes.
        </p>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {PILLARS.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-xl border border-line/70 bg-bg-2/50 p-3">
              <Icon className="h-4 w-4 text-accent" />
              <div className="mt-2 text-sm font-medium">{title}</div>
              <div className="mt-1 text-xs text-muted">{text}</div>
            </div>
          ))}
        </div>
        <p className="mt-6 text-xs text-dim">
          Licensed under the GNU AGPL v3. Source: github.com/MooreSi/Crypto-Trader. Not financial advice; trading leveraged
          crypto can lose more than you expect, fast.
        </p>
      </section>
      <Card title="Version history" icon={<BookOpen className="h-4 w-4" />}>
        {data?.map((r) => (
          <div key={r.version} className="mb-5 last:mb-0">
            <div className="flex items-baseline gap-2"><span className="font-semibold">v{r.version}</span><span className="text-xs text-muted">{r.date} - {r.title}</span></div>
            <ul className="mt-1.5 list-disc space-y-0.5 pl-5 text-sm text-muted">{r.notes.map((n) => <li key={n}>{n}</li>)}</ul>
          </div>
        ))}
      </Card>
    </div>
  );
}
