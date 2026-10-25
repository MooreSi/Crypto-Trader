import { Trophy } from "lucide-react";
import type { Analytics } from "@/api/types";
import { pct, pnlClass, r, signed } from "@/lib/format";
import { Card, Empty, Ring } from "@/components/shared/ui";

export function PerformanceCard({ a, onOpen }: { a: Analytics | null; onOpen?: () => void }) {
  return (
    <Card title="Performance" subtitle="All closed trades" icon={<Trophy className="h-4 w-4" />}
          right={onOpen && <button type="button" onClick={onOpen} className="text-xs text-accent hover:underline">Details</button>}>
      {!a || a.closed === 0 ? <Empty>No closed trades yet.</Empty> : (
        <div className="flex items-center gap-5">
          <Ring value={a.win_rate} size={84} tone={(a.win_rate ?? 0) >= 0.5 ? "profit" : "warn"}>
            <div>{pct((a.win_rate ?? 0) * 100, 0)}</div>
            <div className="text-[10px] font-normal text-muted">win rate</div>
          </Ring>
          <dl className="num grid flex-1 grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt className="text-muted">Net P&amp;L</dt><dd className={`text-right font-semibold ${pnlClass(a.net_pnl)}`}>{signed(a.net_pnl)}</dd>
            <dt className="text-muted">Profit factor</dt><dd className="text-right">{a.profit_factor?.toFixed(2) ?? "-"}</dd>
            <dt className="text-muted">Expectancy</dt><dd className={`text-right ${pnlClass(a.expectancy_r)}`}>{r(a.expectancy_r)}</dd>
            <dt className="text-muted">Max drawdown</dt><dd className="text-right text-loss">{pct(a.max_drawdown_pct, 1)}</dd>
          </dl>
        </div>
      )}
    </Card>
  );
}
