import { useState } from "react";
import { api } from "@/api/client";
import type { EngineSignal, EngineStatus } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { ago, price, time } from "@/lib/format";
import { Badge, Button, Card, ErrorLine, Switch, Table, confirmAction } from "@/components/shared/ui";

const ABOUT: Record<string, string> = {
  breakout: "15m. Breaks out of a tight range on volume, or breaks and retests it.",
  reversal: "15m. ICT: liquidity sweep of a key level, then a market structure shift. Notes FVG / unicorn.",
  trend_pa: "1h. Pullback to EMA20 in an EMA20/50/200 trend, with a rejection candle. 4h trend as a feature.",
};

export function EnginesPage() {
  const { data, error, reload } = usePoll(() => api.get<EngineStatus[]>("/api/engines"), 10000);
  const [open, setOpen] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  const set = async (name: string, what: "enabled" | "live", on: boolean) => {
    if (what === "live" && on && !confirmAction(
      `Let ${name} hand its signals to the executor?\n\nOrders are only placed if the master switch ` +
      `(Risk > Trading enabled) is also on, and every risk gate passes.`)) return;
    try {
      await api.post(`/api/engines/${name}/${what}`, { on });
      setMsg("");
      reload();
    } catch (e) { setMsg(String(e)); }
  };
  const retrain = async (name: string) => {
    const r = await api.post<Record<string, unknown>>(`/api/engines/${name}/retrain`);
    setMsg(r.accepted ? `${name}: new model accepted (holdout AUC ${r.holdout_auc})` : `${name}: ${r.reason ?? "not retrained"}`);
    reload();
  };

  return (
    <div className="space-y-4">
      <ErrorLine error={error} />
      {msg && <div className="rounded-md border border-line bg-panel-2 px-3 py-2 text-sm">{msg}</div>}
      <div className="grid gap-4 lg:grid-cols-3">
        {data?.map((e) => (
          <Card key={e.name} title={<span className="capitalize">{e.name.replace("_", " ")}</span>}
                right={e.live ? <Badge tone="loss">LIVE</Badge> : <Badge>research</Badge>}>
            <p className="mb-3 text-xs text-muted">{ABOUT[e.name]}</p>
            <div className="mb-3 space-y-2 text-sm">
              <label className="flex items-center justify-between">Generate signals <Switch label="generate" on={e.enabled} onChange={(v) => set(e.name, "enabled", v)} /></label>
              <label className="flex items-center justify-between">Live execution <Switch label="live" on={e.live} onChange={(v) => set(e.name, "live", v)} /></label>
            </div>
            <div className="num grid grid-cols-3 gap-2 text-center text-xs">
              <div><div className="text-lg font-semibold">{e.stats.total}</div>signals</div>
              <div><div className="text-lg font-semibold text-profit">{e.stats.wins}</div>wins</div>
              <div><div className="text-lg font-semibold text-loss">{e.stats.losses}</div>losses</div>
              <div><div className="text-lg font-semibold">{e.stats.tracking}</div>tracking</div>
              <div><div className="text-lg font-semibold">{e.stats.expired}</div>expired</div>
              <div><div className="text-lg font-semibold">{e.stats.executed}</div>traded</div>
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-muted">
              <span>ML: {e.model.trained ? <Badge tone="accent">trained{e.model.meta?.handover ? " (handover)" : ""}</Badge> : <Badge>no model yet</Badge>}</span>
              <span>cycle {ago(e.last_cycle)}</span>
            </div>
            {e.last_error && <div className="mt-2 text-xs text-loss">{e.last_error}</div>}
            <div className="mt-3 flex gap-2">
              <Button onClick={() => setOpen(open === e.name ? null : e.name)}>{open === e.name ? "Hide" : "Signals"}</Button>
              <Button onClick={() => retrain(e.name)}>Retrain</Button>
            </div>
          </Card>
        ))}
      </div>
      {open && <Signals name={open} />}
    </div>
  );
}

function Signals({ name }: { name: string }) {
  const { data } = usePoll(() => api.get<EngineSignal[]>(`/api/engines/${name}/signals?limit=100`), 15000, [name]);
  return (
    <Card title={`${name} signals`}>
      <Table head={["Time", "Coin", "Side", "Entry", "Stop", "ML", "Outcome", "MFE R", "Live", "Why"]}
             empty={data && data.length === 0 ? "No signals yet" : undefined}>
        {data?.map((s) => (
          <tr key={s.id}>
            <td className="whitespace-nowrap px-2 py-1.5">{time(s.created_at)}</td>
            <td className="px-2 py-1.5 font-medium">{s.coin}</td>
            <td className="px-2 py-1.5"><Badge tone={s.direction === "long" ? "profit" : "loss"}>{s.direction}</Badge></td>
            <td className="px-2 py-1.5">{price(s.entry)}</td>
            <td className="px-2 py-1.5">{price(s.stop)}</td>
            <td className="px-2 py-1.5">{s.ml_score === null ? "-" : s.ml_score.toFixed(2)}</td>
            <td className="px-2 py-1.5"><Badge tone={s.status === "win" ? "profit" : s.status === "loss" ? "loss" : "muted"}>{s.status}</Badge></td>
            <td className="px-2 py-1.5">{s.mfe_r?.toFixed(2) ?? "-"}</td>
            <td className="max-w-48 truncate px-2 py-1.5 text-xs" title={s.live_status ?? ""}>{s.live_status ?? "-"}</td>
            <td className="max-w-72 truncate px-2 py-1.5 text-xs text-muted" title={s.reason}>{s.reason}</td>
          </tr>
        ))}
      </Table>
    </Card>
  );
}
