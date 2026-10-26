import { useState } from "react";
import clsx from "clsx";
import { Brain, Cpu, RefreshCw, Radio } from "lucide-react";
import { api } from "@/api/client";
import type { EngineSignal, EngineStatus } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { ago, pct, price, r, time } from "@/lib/format";
import { Badge, Button, Card, ErrorLine, Notice, Ring, Side, Skeleton, Switch, Table, confirmAction } from "@/components/shared/ui";

const ABOUT: Record<string, string> = {
  breakout: "15m. Breaks out of a tight range on volume, or breaks and retests it.",
  reversal: "15m. ICT: liquidity sweep of a key level, then a market structure shift. Notes FVG / unicorn.",
  trend_pa: "1h. Pullback to EMA20 in an EMA20/50/200 trend, with a rejection candle. 4h trend as a feature.",
};

function Model({ e }: { e: EngineStatus }) {
  const rep = e.model.trained ? e.model.meta : e.model.last_report;
  const feats = rep?.top_features ?? [];
  const top = feats[0]?.[1] ?? 1;
  return (
    <div className="rounded-lg border border-line/70 bg-bg-2/60 p-3">
      <div className="mb-2 flex items-center justify-between text-xs">
        <span className="flex items-center gap-1.5 font-medium"><Brain className="h-3.5 w-3.5 text-accent-2" />ML model</span>
        {e.model.trained ? <Badge tone="accent">trained{e.model.meta?.handover ? " (handover)" : ""}</Badge> : <Badge>no model yet</Badge>}
      </div>
      {rep?.holdout_auc != null && (
        <div className="num mb-2 text-xs text-muted">
          holdout AUC <span className="text-text">{rep.holdout_auc.toFixed(3)}</span> (needs {rep.auc_needed?.toFixed(3)}), {rep.samples} signals
        </div>
      )}
      {!e.model.trained && rep?.reason && <div className="text-xs text-muted">{rep.reason}</div>}
      {feats.length > 0 && (
        <ul className="space-y-1">
          {feats.slice(0, 5).map(([n, v]) => (
            <li key={n} className="flex items-center gap-2 text-[11px]">
              <span className="w-28 truncate text-muted">{n}</span>
              <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-line"><span className="grad-fill block h-full" style={{ width: `${(v / top) * 100}%` }} /></span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

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
    try {
      const res = await api.post<Record<string, unknown>>(`/api/engines/${name}/retrain`);
      setMsg(res.accepted ? `${name}: new model accepted (holdout AUC ${res.holdout_auc})` : `${name}: ${res.reason ?? "not retrained"}`);
      reload();
    } catch (e) { setMsg(String(e)); }
  };

  return (
    <div className="space-y-5">
      <ErrorLine error={error} />
      {msg && <Notice>{msg}</Notice>}
      <div className="grid gap-5 lg:grid-cols-3">
        {!data && [0, 1, 2].map((i) => <Skeleton key={i} className="h-96 w-full rounded-xl" />)}
        {data?.map((e) => {
          const decided = e.stats.wins + e.stats.losses + e.stats.expired;
          const wr = decided ? e.stats.wins / decided : null;
          return (
            <Card key={e.name} title={<span className="capitalize">{e.name.replace("_", " ")}</span>} subtitle={`${e.interval} bars, cycle ${ago(e.last_cycle)}`}
                  icon={<Cpu className="h-4 w-4" />}
                  right={e.live ? <Badge tone="loss" dot>LIVE</Badge> : <Badge>research</Badge>}
                  className={clsx(e.live && "ring-1 ring-loss/30")}>
              <p className="mb-4 text-xs text-muted">{ABOUT[e.name]}</p>
              <div className="mb-4 flex items-center gap-4">
                <Ring value={wr} size={76} tone={(wr ?? 0) >= 0.5 ? "profit" : "warn"}>
                  <div>{wr == null ? "-" : pct(wr * 100, 0)}</div><div className="text-[9px] font-normal text-muted">net win</div>
                </Ring>
                <div className="num grid flex-1 grid-cols-3 gap-2 text-center text-[11px] text-muted">
                  <div><div className="text-base font-semibold text-text">{e.stats.total}</div>signals</div>
                  <div><div className="text-base font-semibold text-profit">{e.stats.wins}</div>wins</div>
                  <div><div className="text-base font-semibold text-loss">{e.stats.losses}</div>losses</div>
                  <div><div className="text-base font-semibold text-text">{e.stats.tracking}</div>tracking</div>
                  <div><div className="text-base font-semibold text-text">{r(e.stats.avg_r)}</div>avg</div>
                  <div><div className="text-base font-semibold text-text">{e.stats.executed}</div>traded</div>
                </div>
              </div>
              <div className="mb-4 space-y-2.5 text-sm">
                <label className="flex items-center justify-between">Generate signals <Switch label="generate" on={e.enabled} onChange={(v) => set(e.name, "enabled", v)} /></label>
                <label className="flex items-center justify-between"><span className="flex items-center gap-1.5"><Radio className="h-3.5 w-3.5 text-loss" />Live execution</span>
                  <Switch label="live" on={e.live} onChange={(v) => set(e.name, "live", v)} /></label>
              </div>
              <Model e={e} />
              {e.last_error && <div className="mt-2 text-xs text-loss">{e.last_error}</div>}
              <div className="mt-4 flex gap-2">
                <Button size="sm" onClick={() => setOpen(open === e.name ? null : e.name)}>{open === e.name ? "Hide signals" : "Signals"}</Button>
                <Button size="sm" tone="ghost" onClick={() => retrain(e.name)}><RefreshCw className="h-3.5 w-3.5" />Retrain</Button>
              </div>
            </Card>
          );
        })}
      </div>
      {open && <Signals name={open} />}
    </div>
  );
}

function Signals({ name }: { name: string }) {
  const { data } = usePoll(() => api.get<EngineSignal[]>(`/api/engines/${name}/signals?limit=100`), 15000, [name]);
  return (
    <Card title={`${name.replace("_", " ")} signals`} subtitle="Latest 100, tracked through your exit plan, net of fees">
      <Table head={["Time", "Coin", "Side", "Entry", "Stop", "ML", "Outcome", "MFE", "Live", "Why"]}
             align={["l", "l", "l", "r", "r", "r", "l", "r", "l", "l"]}
             empty={data && data.length === 0 ? "No signals yet" : undefined}>
        {data?.map((s) => (
          <tr key={s.id}>
            <td className="whitespace-nowrap">{time(s.created_at)}</td>
            <td className="font-semibold">{s.coin}</td>
            <td><Side direction={s.direction} /></td>
            <td className="text-right">{price(s.entry)}</td>
            <td className="text-right">{price(s.stop)}</td>
            <td className="text-right">{s.ml_score === null ? "-" : s.ml_score.toFixed(2)}</td>
            <td><Badge tone={s.status === "win" ? "profit" : s.status === "loss" ? "loss" : "muted"}>{s.status}</Badge></td>
            <td className="text-right">{s.mfe_r == null ? "-" : `${s.mfe_r.toFixed(2)}R`}</td>
            <td className="max-w-48 truncate text-xs" title={s.live_status ?? ""}>{s.live_status ?? "-"}</td>
            <td className="max-w-72 truncate text-xs text-muted" title={s.reason}>{s.reason}</td>
          </tr>
        ))}
      </Table>
    </Card>
  );
}
