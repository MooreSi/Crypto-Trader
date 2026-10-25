import { BarChart3 } from "lucide-react";
import type { Analytics } from "@/api/types";
import { pct, pnlClass, r, signed } from "@/lib/format";
import { Card, Empty, Table } from "@/components/shared/ui";

function Kv({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) {
  return (
    <div className="rounded-lg border border-line/60 bg-bg-2/50 px-3 py-2">
      <div className="text-[11px] uppercase tracking-wider text-dim">{k}</div>
      <div className={`num mt-0.5 text-base font-semibold ${tone ?? ""}`}>{v}</div>
    </div>
  );
}

export function AnalyticsCard({ a }: { a: Analytics | null }) {
  return (
    <Card title="Performance analytics" subtitle="Closed trades; drawdown and Sharpe from equity snapshots" icon={<BarChart3 className="h-4 w-4" />}>
      {!a || a.closed === 0 ? <Empty>Analytics appear after the first closed trade.</Empty> : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-8">
            <Kv k="Profit factor" v={a.profit_factor?.toFixed(2) ?? "-"} tone={(a.profit_factor ?? 0) >= 1 ? "text-profit" : "text-loss"} />
            <Kv k="Expectancy" v={r(a.expectancy_r)} tone={pnlClass(a.expectancy_r)} />
            <Kv k="Avg win" v={signed(a.avg_win)} tone="text-profit" />
            <Kv k="Avg loss" v={signed(a.avg_loss)} tone="text-loss" />
            <Kv k="Sharpe (ann.)" v={a.sharpe?.toFixed(2) ?? "-"} />
            <Kv k="Max drawdown" v={pct(a.max_drawdown_pct, 1)} tone="text-loss" />
            <Kv k="Losing streak" v={a.longest_losing_streak} />
            <Kv k="Avg hold" v={a.avg_hold_hours == null ? "-" : `${a.avg_hold_hours.toFixed(1)}h`} />
          </div>
          <Table head={["Engine", "Trades", "Win rate", "Net P&L", "Profit factor", "Expectancy"]} align={["l", "r", "r", "r", "r", "r"]}>
            {Object.entries(a.by_engine).map(([name, b]) => (
              <tr key={name}>
                <td className="font-medium capitalize">{name.replace("_", " ")}</td>
                <td className="text-right">{b.trades}</td>
                <td className="text-right">{b.win_rate == null ? "-" : pct(b.win_rate * 100, 0)}</td>
                <td className={`text-right ${pnlClass(b.net_pnl)}`}>{signed(b.net_pnl)}</td>
                <td className="text-right">{b.profit_factor?.toFixed(2) ?? "-"}</td>
                <td className={`text-right ${pnlClass(b.expectancy_r)}`}>{r(b.expectancy_r)}</td>
              </tr>
            ))}
          </Table>
        </div>
      )}
    </Card>
  );
}
