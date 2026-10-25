import { useMemo, useState } from "react";
import clsx from "clsx";
import { FlaskConical, Play, Sigma } from "lucide-react";
import { api } from "@/api/client";
import type { BacktestResult, Market, StrategyInfo } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { pct, pnlClass, price, r, time } from "@/lib/format";
import { Badge, Button, Card, Empty, ErrorLine, Notice, Segmented, Side, Skeleton, Stat, Table, inputCls } from "@/components/shared/ui";
import { RCurveChart } from "./RCurveChart";
import { TunePanel } from "./TunePanel";

const BARS = ["500", "1500", "3000", "5000"] as const;
const title = (n: string) => n.replace(/_/g, " ");

export function LabPage() {
  const { data: strategies } = usePoll(() => api.get<StrategyInfo[]>("/api/backtest/strategies"), 600000);
  const { data: markets } = usePoll(() => api.get<Market[]>("/api/markets"), 120000);
  const [strategy, setStrategy] = useState("breakout");
  const [coin, setCoin] = useState("BTC");
  const [bars, setBars] = useState<(typeof BARS)[number]>("1500");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<BacktestResult | null>(null);
  const coins = useMemo(() => (markets ?? []).slice(0, 60).map((m) => m.coin), [markets]);

  // The exchange names some coins in mixed case (kPEPE): resolve what was typed.
  const resolveCoin = () => {
    const typed = coin.trim();
    return (markets ?? []).find((m) => m.coin.toUpperCase() === typed.toUpperCase())?.coin ?? typed.toUpperCase();
  };

  const run = async () => {
    const resolved = resolveCoin();
    setBusy(true); setError("");
    try {
      setResult(await api.post<BacktestResult>("/api/backtest", { strategy, coin: resolved, bars: Number(bars) }));
    } catch (e) {
      const m = e instanceof Error ? e.message : String(e);
      setError(m.includes("(429") ? "Hyperliquid is rate-limiting requests from this computer (HTTP 429). " +
        "Wait a minute and run it again; a long history needs several requests." : m);
    } finally {
      setBusy(false);
    }
  };

  const s = result?.summary;
  const exits = useMemo(() => {
    const out: Record<string, number> = {};
    for (const t of result?.trades ?? []) out[t.exit] = (out[t.exit] ?? 0) + 1;
    return out;
  }, [result]);

  return (
    <div className="space-y-5">
      <Notice>
        The Strategy Lab replays a strategy over Hyperliquid history with the app's own exit plan (stop, your TP ladder,
        breakeven) and never places an order. Lab strategies are research only: they have no live switch. Backtests leave
        out funding, slippage beyond the taker fee and the risk gates, so they flatter live results.
      </Notice>
      <Card title="Choose a strategy" icon={<FlaskConical className="h-4 w-4" />}>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {(strategies ?? []).map((st) => (
            <button key={st.name} type="button" onClick={() => setStrategy(st.name)}
                    className={clsx("rounded-xl border p-3 text-left transition",
                      st.name === strategy ? "border-accent/60 bg-accent/5 ring-2 ring-accent/15" : "border-line bg-panel-2/50 hover:border-line-2")}>
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold capitalize">{title(st.name)}</span>
                <span className="flex gap-1">
                  <Badge>{st.interval}{st.htf ? ` + ${st.htf}` : ""}</Badge>
                  <Badge tone={st.kind === "lab" ? "accent" : "muted"}>{st.kind}</Badge>
                </span>
              </div>
              <p className="mt-1.5 text-xs text-muted">{st.about}</p>
            </button>
          ))}
          {!strategies && [0, 1, 2].map((i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
        </div>
        <div className="mt-4 flex flex-wrap items-end gap-3 border-t border-line/60 pt-4">
          <label className="text-xs text-muted">
            <span className="mb-1 block">Coin</span>
            <input aria-label="Coin" value={coin} list="lab-coins" onChange={(e) => setCoin(e.target.value)} className={clsx(inputCls, "w-32 uppercase")} />
            <datalist id="lab-coins">{coins.map((c) => <option key={c} value={c} />)}</datalist>
          </label>
          <div className="text-xs text-muted">
            <span className="mb-1 block">Bars of history</span>
            <Segmented value={bars} options={BARS} onChange={setBars} />
          </div>
          <Button tone="accent" onClick={run} disabled={busy || !coin.trim()}>
            <Play className="h-4 w-4" />{busy ? "Running..." : "Run backtest"}
          </Button>
        </div>
      </Card>
      <ErrorLine error={error} />
      {busy && !result && <Skeleton className="h-40 w-full rounded-xl" />}
      {result && s && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            <Stat label="Trades" value={s.trades} sub={`${result.bars} ${result.interval} bars`} />
            <Stat label="Win rate" value={s.win_rate == null ? "-" : pct(s.win_rate * 100, 0)} sub={`${s.wins} winners`} />
            <Stat label="Total" value={r(s.total_r, 1)} tone={pnlClass(s.total_r)} sub={`avg ${r(s.avg_r)}`} />
            <Stat label="Profit factor" value={s.profit_factor?.toFixed(2) ?? "-"} tone={(s.profit_factor ?? 0) >= 1 ? "text-profit" : "text-loss"} />
            <Stat label="Max drawdown" value={`${s.max_drawdown_r.toFixed(1)}R`} tone="text-loss" />
            <Stat label={`At ${s.risk_pct}% risk`} value={pct(s.compounded_return_pct, 1, true)} tone={pnlClass(s.compounded_return_pct)} sub="compounded" />
          </div>
          <Card title={`${title(result.strategy)} on ${result.coin}`} subtitle={`${time(result.from)} to ${time(result.to)}, cumulative R`}
                icon={<Sigma className="h-4 w-4" />}
                right={<span className="flex gap-1">{Object.entries(exits).map(([k, n]) => <Badge key={k}>{k} {n}</Badge>)}</span>}>
            {s.curve.length ? <RCurveChart curve={s.curve} /> : <Empty>No trades in this window.</Empty>}
          </Card>
          <Card title="Simulated trades" subtitle="Newest first">
            <Table head={["Opened", "Side", "Entry", "Stop", "TPs", "Exit", "R", "Why"]} align={["l", "l", "r", "r", "r", "l", "r", "l"]}
                   empty={result.trades.length === 0 ? "No setups fired" : undefined}>
              {[...result.trades].reverse().slice(0, 200).map((t) => (
                <tr key={t.opened_at}>
                  <td className="whitespace-nowrap">{time(t.opened_at)}</td>
                  <td><Side direction={t.direction} /></td>
                  <td className="text-right">{price(t.entry)}</td>
                  <td className="text-right">{price(t.stop)}</td>
                  <td className="text-right">{t.tp_hits}</td>
                  <td><Badge tone={t.exit === "tp" ? "profit" : t.exit === "stop" ? "loss" : "muted"}>{t.exit}</Badge></td>
                  <td className={`text-right font-medium ${pnlClass(t.r)}`}>{r(t.r)}</td>
                  <td className="max-w-80 truncate text-xs text-muted" title={t.reason}>{t.reason}</td>
                </tr>
              ))}
            </Table>
          </Card>
        </>
      )}
      <TunePanel strategy={strategy} coin={resolveCoin()} bars={Number(bars)} />
    </div>
  );
}
