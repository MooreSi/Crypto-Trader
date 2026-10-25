import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { RiskSettings } from "@/api/types";
import clsx from "clsx";
import { Power, Save, ShieldCheck, SlidersHorizontal, Target } from "lucide-react";
import { Badge, Button, Card, ErrorLine, Field, Switch, confirmAction, inputCls } from "@/components/shared/ui";

type Field = { key: string; label: string; help: string; step?: number };

const SECTIONS: { title: string; fields: Field[] }[] = [
  { title: "Per trade", fields: [
    { key: "risk_per_trade_pct", label: "Risk per trade (% of equity)", help: "Lost if the stop is hit.", step: 0.05 },
    { key: "max_leverage", label: "Max leverage", help: "Never above the market's own maximum. Leverage sets margin, the stop sets risk." },
    { key: "max_position_notional_pct", label: "Max position size (% of equity, notional)", help: "Caps position size when the stop is very tight." },
    { key: "min_reward_risk", label: "Min reward:risk (ladder)", help: "The TP ladder's weighted R must reach this.", step: 0.1 },
    { key: "entry_slippage_pct", label: "Max entry slippage (%)", help: "The market entry will not fill worse than this.", step: 0.05 },
    { key: "min_stop_pct", label: "Min stop distance (% of price, 0 = off)", help: "Refuses a trade whose stop is so tight that the ~0.09% round-trip fee eats much of the risk.", step: 0.05 },
  ]},
  { title: "Portfolio", fields: [
    { key: "max_open_positions", label: "Max open positions", help: "" },
    { key: "max_same_direction", label: "Max positions in one direction", help: "Crypto moves together; this caps one big bet on BTC." },
    { key: "max_funding_rate_pct", label: "Max funding paid (%/hour)", help: "Refuses entries that pay more than this each hour.", step: 0.005 },
  ]},
  { title: "Daily (UTC day)", fields: [
    { key: "daily_loss_limit_pct", label: "Daily loss limit (% of day start)", help: "No new trades once today is down this much.", step: 0.5 },
    { key: "daily_profit_target_usd", label: "Daily profit target (USDC, 0 = off)", help: "No new trades once today's realised profit reaches it." },
  ]},
  { title: "Managing open trades", fields: [
    { key: "breakeven_after_tp", label: "Move stop to breakeven after TP n (0 = never)", help: "" },
    { key: "trail_atr_mult", label: "Trail stop at n x ATR(15m) after TP1 (0 = off)", help: "Only ever tightens.", step: 0.25 },
  ]},
  { title: "Markets and events", fields: [
    { key: "auto_top_n", label: "Scan top n markets by volume", help: "Used when the watchlist is empty." },
    { key: "min_day_volume_usd", label: "Min 24h volume (USD)", help: "" },
    { key: "blackout_minutes_before", label: "Event blackout before (min)", help: "" },
    { key: "blackout_minutes_after", label: "Event blackout after (min)", help: "" },
    { key: "ml_min_probability", label: "Min ML probability", help: "Used when an engine has a trained model.", step: 0.05 },
  ]},
];

const TOGGLES: Field[] = [
  { key: "isolated_margin", label: "Isolated margin", help: "Each position risks only its own margin." },
  { key: "blackout_enabled", label: "Event blackout", help: "Block new entries around high-impact events." },
  { key: "blackout_include_medium", label: "Blackout medium-impact events too", help: "" },
  { key: "ml_require_model", label: "Require a trained ML model", help: "Off: signals pass the ML gate until a model exists." },
];

export function RiskPage() {
  const [s, setS] = useState<RiskSettings | null>(null);
  const [draft, setDraft] = useState<Record<string, unknown>>({});
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  const load = () => api.get<RiskSettings>("/api/risk").then(setS).catch((e) => setError(String(e)));
  useEffect(() => { void load(); }, []);

  const save = async (fields: Record<string, unknown>) => {
    // A cleared box is not zero: refuse it rather than save the field's minimum.
    const blank = Object.entries(fields).filter(([, v]) => v === "" || (typeof v === "number" && Number.isNaN(v)));
    if (blank.length) { setError(`Enter a number for ${blank.map(([k]) => k).join(", ")}`); return; }
    try {
      setS(await api.post<RiskSettings>("/api/risk", { fields }));
      setDraft({}); setError(""); setSaved("Saved");
      window.setTimeout(() => setSaved(""), 2000);
    } catch (e) { setError(String(e)); }
  };

  const master = async (on: boolean) => {
    if (on && !confirmAction("Turn trading ON?\n\nEngines whose Live switch is on will place real orders " +
      "on the current network (check the badge in the header).")) return;
    await save({ trading_enabled: on });
  };

  if (!s) return <ErrorLine error={error || "Loading..."} />;
  const val = (k: string) => (k in draft ? draft[k] : s[k]) as number | string;
  const ladder = s.tp_ladder as number[][];

  return (
    <div className="space-y-5">
      <ErrorLine error={error} />
      <Card title="Master switch" icon={<Power className="h-4 w-4" />}
            right={s.trading_enabled ? <Badge tone="loss" dot>trading on</Badge> : <Badge>trading off</Badge>}
            className={clsx(Boolean(s.trading_enabled) && "ring-1 ring-loss/30")}>
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium">Trading enabled</div>
            <div className="text-xs text-muted">Off: nothing executes, whatever the engines' Live switches say. Open trades are still managed.</div>
          </div>
          <Switch label="trading enabled" on={Boolean(s.trading_enabled)} onChange={master} />
        </div>
      </Card>
      <div className="grid gap-5 lg:grid-cols-2">
        {SECTIONS.map((sec) => (
          <Card key={sec.title} title={sec.title} icon={<SlidersHorizontal className="h-4 w-4" />}>
            <div className="space-y-3">
              {sec.fields.map((f) => (
                <Field key={f.key} label={f.label} help={f.help}>
                    <input type="number" step={f.step ?? 1} value={String(val(f.key))}
                           onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value === "" ? "" : Number(e.target.value) })}
                           className={clsx(inputCls, "num w-32 text-right", f.key in draft && "border-accent/60")} />
                </Field>
              ))}
            </div>
          </Card>
        ))}
        <Card title="Switches" icon={<ShieldCheck className="h-4 w-4" />}>
          <div className="space-y-3">
            {TOGGLES.map((f) => (
              <div key={f.key} className="flex items-center justify-between text-sm">
                <div><div>{f.label}</div>{f.help && <div className="text-xs text-muted">{f.help}</div>}</div>
                <Switch label={f.key} on={Boolean(s[f.key])} onChange={(v) => save({ [f.key]: v })} />
              </div>
            ))}
          </div>
        </Card>
        <Card title="Take-profit ladder" icon={<Target className="h-4 w-4" />}>
          <p className="mb-3 text-xs text-muted">Each rung closes a share of the original size at a multiple of the risk (R). Exchange-side orders. A rung worth under $11.20 is merged into the one before it.</p>
          <div className="space-y-2">
            {ladder.map(([r, f], i) => (
              <div key={i} className="num flex items-center gap-3 text-sm">
                <span className="w-10 font-semibold text-accent">TP{i + 1}</span>
                <span className="w-12">{r}R</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-line"><span className="grad-fill block h-full" style={{ width: `${f * 100}%` }} /></span>
                <span className="w-12 text-right text-muted">{(f * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <div className={clsx("sticky bottom-4 z-10 flex items-center gap-3 rounded-xl border px-4 py-3 backdrop-blur transition",
        Object.keys(draft).length ? "border-accent/40 bg-panel/90 shadow-lg" : "border-transparent")}>
        <Button tone="accent" disabled={Object.keys(draft).length === 0} onClick={() => save(draft)}><Save className="h-4 w-4" />Save changes</Button>
        {Object.keys(draft).length > 0 && <Button tone="ghost" onClick={() => setDraft({})}>Discard</Button>}
        {Object.keys(draft).length > 0 && <span className="text-xs text-muted">{Object.keys(draft).length} unsaved</span>}
        {saved && <span className="text-sm text-profit">{saved}</span>}
      </div>
    </div>
  );
}
