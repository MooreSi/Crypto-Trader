import { useState } from "react";
import { SlidersHorizontal, Wand2 } from "lucide-react";
import { api } from "@/api/client";
import type { BacktestSummary, TuneResult } from "@/api/types";
import { pct, pnlClass, r, time } from "@/lib/format";
import { Badge, Button, Card, Empty, ErrorLine, Notice, Segmented, Skeleton, Table } from "@/components/shared/ui";
import { TuneCurveChart } from "./TuneCurveChart";

const FOLDS = ["2", "3", "4", "6"] as const;

function Col({ title, s, accent }: { title: string; s: Omit<BacktestSummary, "curve">; accent?: boolean }) {
  return (
    <div className={`rounded-xl border p-3 ${accent ? "border-accent/40 bg-accent/5" : "border-line/70 bg-bg-2/50"}`}>
      <div className="mb-2 text-[11px] font-medium uppercase tracking-wider text-dim">{title}</div>
      <dl className="num grid grid-cols-2 gap-y-1 text-sm">
        <dt className="text-muted">Total</dt><dd className={`text-right font-semibold ${pnlClass(s.total_r)}`}>{r(s.total_r, 1)}</dd>
        <dt className="text-muted">Trades</dt><dd className="text-right">{s.trades}</dd>
        <dt className="text-muted">Win rate</dt><dd className="text-right">{s.win_rate == null ? "-" : pct(s.win_rate * 100, 0)}</dd>
        <dt className="text-muted">Profit factor</dt><dd className="text-right">{s.profit_factor?.toFixed(2) ?? "-"}</dd>
        <dt className="text-muted">Max drawdown</dt><dd className="text-right text-loss">{s.max_drawdown_r.toFixed(1)}R</dd>
      </dl>
    </div>
  );
}

const show = (v: unknown) => (Array.isArray(v) ? v.map((x) => `${x[0]}R ${Math.round(x[1] * 100)}%`).join(", ") : String(v));

/** Walk-forward tuning of the chosen strategy: a report and a proposal, never a change. */
export function TunePanel({ strategy, coin, bars }: { strategy: string; coin: string; bars: number }) {
  const [folds, setFolds] = useState<(typeof FOLDS)[number]>("4");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [res, setRes] = useState<TuneResult | null>(null);

  const tune = async () => {
    setBusy(true); setError("");
    try {
      setRes(await api.post<TuneResult>("/api/backtest/tune", { strategy, coin, bars, folds: Number(folds) }));
    } catch (e) {
      const m = e instanceof Error ? e.message : String(e);
      setError(m.includes("(429") ? "Hyperliquid is rate-limiting requests from this computer (HTTP 429). Wait a minute and try again." : m);
    } finally { setBusy(false); }
  };

  const k = res?.folds.length ?? 0;
  const diff = res ? res.oos.total_r - res.oos_default.total_r : 0;
  return (
    <Card title="Walk-forward tuning" subtitle="Choose settings on the past, judge them on bars they never saw" icon={<Wand2 className="h-4 w-4" />}
          right={<span className="flex items-center gap-2"><span className="text-xs text-muted">folds</span>
            <Segmented value={folds} options={FOLDS} onChange={setFolds} />
            <Button size="sm" tone="accent" onClick={tune} disabled={busy}><SlidersHorizontal className="h-3.5 w-3.5" />{busy ? "Tuning..." : "Tune"}</Button></span>}>
      <p className="mb-3 text-xs text-muted">
        History is cut into {Number(folds) + 1} segments. In each fold every candidate (the strategy's own settings, four exit
        ladders, breakeven on or off) is backtested on one segment, and the best by profit factor is then scored on the next
        segment only. Proposal only: nothing changes until you change it yourself.
      </p>
      <ErrorLine error={error} />
      {busy && !res && <Skeleton className="h-32 w-full rounded-xl" />}
      {!res && !busy && <Empty>Pick a strategy and coin above, then Tune. A 3000-bar run takes a few seconds to a minute.</Empty>}
      {res && (
        <div className="space-y-4">
          {res.beats_default && res.profitable
            ? <Notice tone="profit">Tuned settings beat your defaults out of sample by {r(diff, 1)} over {res.oos.trades} trades. Still a small sample: treat it as a lead, not proof.</Notice>
            : res.beats_default
              ? <Notice tone="warn">Tuned settings lost {r(diff, 1)} less than your defaults out of sample, but still lost money ({r(res.oos.total_r, 1)}). Neither is worth trading on this coin.</Notice>
              : <Notice tone="warn">Tuning did not beat your defaults out of sample ({r(diff, 1)}). Keep the defaults; the in-sample winners did not hold up.</Notice>}
          <div className="grid gap-3 md:grid-cols-3">
            <Col title="Tuned, out of sample" s={res.oos} accent />
            <Col title="Your defaults, same bars" s={res.oos_default} />
            <div className="rounded-xl border border-line/70 bg-bg-2/50 p-3">
              <div className="mb-2 flex items-center justify-between text-[11px] font-medium uppercase tracking-wider text-dim">
                Proposal <Badge tone={res.stability >= 0.75 ? "profit" : res.stability >= 0.5 ? "warn" : "loss"}>
                  <span>{pct(res.stability * 100, 0)} stable, chosen in {Math.round(res.stability * k)} of {k} folds</span>
                </Badge>
              </div>
              <dl className="num space-y-1 text-sm">
                {Object.entries(res.proposal).filter(([key]) => key !== "ladder").map(([key, v]) => (
                  <div key={key} className="flex justify-between gap-2">
                    <dt className="text-muted">{key}</dt>
                    <dd className="text-right">{show(v)}{key in res.defaults && res.defaults[key] !== v && <span className="text-dim"> (was {String(res.defaults[key])})</span>}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-2 text-[11px] text-dim">To try the ladder live, set it on the Risk page yourself. Strategy settings apply to the Lab only.</p>
            </div>
          </div>
          <TuneCurveChart tuned={res.oos.curve} base={res.oos_default.curve} />
          <Table head={["Test window", "Chosen on the train segment", "Train", "Test (tuned)", "Test (defaults)"]} align={["l", "l", "r", "r", "r"]}>
            {res.folds.map((f) => (
              <tr key={f.test_from}>
                <td className="whitespace-nowrap">{time(f.test_from)} to {time(f.test_to)}</td>
                <td className="text-xs text-muted">
                  {f.fallback && <span className="mr-1.5"><Badge tone="warn">kept defaults</Badge></span>}
                  {Object.entries(f.chosen).map(([a, b]) => `${a} ${b}`).join(", ")}
                </td>
                <td className={`text-right ${pnlClass(f.train.total_r)}`}>{r(f.train.total_r, 1)} <span className="text-dim">({f.train.trades})</span></td>
                <td className={`text-right font-medium ${pnlClass(f.test.total_r)}`}>{r(f.test.total_r, 1)} <span className="text-dim">({f.test.trades})</span></td>
                <td className={`text-right ${pnlClass(f.test_default.total_r)}`}>{r(f.test_default.total_r, 1)} <span className="text-dim">({f.test_default.trades})</span></td>
              </tr>
            ))}
          </Table>
          <p className="text-[11px] text-dim">{res.candidates} candidates per fold, at least {res.min_trades} train trades to qualify; a fold where none did keeps your defaults and is marked. Same caveats as a backtest: no funding, slippage or risk gates.</p>
        </div>
      )}
    </Card>
  );
}
