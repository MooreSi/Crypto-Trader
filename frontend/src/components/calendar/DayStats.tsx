import clsx from "clsx";
import { ShieldAlert, Target } from "lucide-react";
import type { CalendarTrade } from "@/api/types";
import { pnlClass } from "@/lib/format";
import { breakdown, type Tally } from "./calendarGrid";
import { dayStats, goalMarks, intradayCurve, money, type GoalSettings } from "./calendarStats";

const W = 300, H = 64, PAD = 4;

/** The day's realised P&L close by close, as a step line with its zero. */
function IntradayCurveView({ trades }: { trades: CalendarTrade[] }) {
  const c = intradayCurve(trades);
  const lo = Math.min(0, c.low), hi = Math.max(0, c.peak);
  const span = hi - lo || 1;
  const n = c.points.length - 1 || 1;
  const x = (i: number) => PAD + (i / n) * (W - 2 * PAD);
  const y = (v: number) => PAD + ((hi - v) / span) * (H - 2 * PAD);
  const path = c.points.map((p, i) => (i === 0 ? `M${x(0)},${y(p.cum)}` : `H${x(i)}V${y(p.cum)}`)).join("");
  const last = c.points[c.points.length - 1]!.cum;
  return (
    <svg data-testid="intraday-curve" viewBox={`0 0 ${W} ${H}`} className="h-16 w-full" role="img"
      aria-label="Realised P&L through the day">
      <line x1={PAD} x2={W - PAD} y1={y(0)} y2={y(0)} stroke="var(--color-line-2)" strokeDasharray="3 3" />
      <path d={path} fill="none" strokeWidth={1.5}
        stroke={last >= 0 ? "var(--color-profit)" : "var(--color-loss)"} />
    </svg>
  );
}

/** Profit factor, averages, best and worst, fees, realised peak and drawdown,
 *  the intraday curve, and whether the target or loss limit was touched. */
export function DayStats({ trades, dayOpen, risk }: {
  trades: CalendarTrade[]; dayOpen: number | null; risk: GoalSettings;
}) {
  const s = dayStats(trades);
  const curve = intradayCurve(trades);
  const marks = goalMarks(trades, dayOpen, risk);
  const m = (v: number | null) => (v == null ? "-" : money(v));
  const cells: [string, string, string, string?][] = [
    ["Profit factor", s.profitFactor == null ? "-" : s.profitFactor.toFixed(2), "stat-pf"],
    ["Avg win", m(s.avgWin), "stat-avg-win", "text-profit"],
    ["Avg loss", m(s.avgLoss), "stat-avg-loss", "text-loss"],
    ["Best", m(s.best), "stat-best", pnlClass(s.best)],
    ["Worst", m(s.worst), "stat-worst", pnlClass(s.worst)],
    ["Fees", `$${s.fees.toFixed(2)}`, "stat-fees"],
    ["Peak", money(curve.peak), "stat-peak", pnlClass(curve.peak)],
    ["Max drawdown", money(-curve.maxDrawdown), "stat-max-dd", curve.maxDrawdown > 0 ? "text-loss" : undefined],
  ];
  return (
    <section className="space-y-2">
      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
        {cells.map(([label, value, testId, tone]) => (
          <div key={testId} data-testid={testId} className="rounded-lg border border-line bg-panel-2/40 px-2 py-1">
            <div className="text-[10px] uppercase tracking-wider text-dim">{label}</div>
            <div className={clsx("num font-semibold text-text", tone)}>{value}</div>
          </div>
        ))}
      </div>
      <IntradayCurveView trades={trades} />
      {(marks.goal || marks.loss) && (
        <div className="flex gap-3 text-[11px]">
          {marks.goal && <span className="flex items-center gap-1 text-profit"><Target size={12} /> Daily profit target reached</span>}
          {marks.loss && <span className="flex items-center gap-1 text-loss"><ShieldAlert size={12} /> Daily loss limit reached</span>}
        </div>
      )}
    </section>
  );
}

function Breakdown({ title, rows, prefix }: { title: string; rows: Tally[]; prefix: string }) {
  return (
    <section className="space-y-1">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-dim">
        <span>{title}</span>
        <span className="ml-auto w-12 text-right">Wins</span>
        <span className="w-10 text-right">Win%</span>
        <span className="w-20 text-right">Net</span>
      </div>
      <ul className="space-y-0.5">
        {rows.map((r) => (
          <li key={r.key} data-testid={`${prefix}-${r.key}`}
            className="flex items-center gap-2 rounded px-1.5 py-1 odd:bg-panel-2/40">
            <span className="truncate capitalize text-muted">{r.key.replace("_", " ")}</span>
            <span className="num ml-auto w-12 shrink-0 text-right text-dim">{r.wins} / {r.n}</span>
            <span className="num w-10 shrink-0 text-right text-dim">{Math.round((r.wins / r.n) * 100)}%</span>
            <span className={clsx("num w-20 shrink-0 text-right font-semibold", pnlClass(r.pnl))}>{money(r.pnl)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The day split three ways: by engine, by coin, and by the liquidity
 *  session the trade closed in (UTC). */
export function DayBreakdown({ trades }: { trades: CalendarTrade[] }) {
  return (
    <div className="space-y-3">
      <Breakdown title="By engine" rows={breakdown(trades, (t) => t.engine)} prefix="engine" />
      <Breakdown title="By coin" rows={breakdown(trades, (t) => t.coin)} prefix="coin" />
      <Breakdown title="By session" rows={breakdown(trades, (t) => t.session)} prefix="session" />
    </div>
  );
}
