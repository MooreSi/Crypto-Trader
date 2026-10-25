import { Gauge } from "lucide-react";
import { api } from "@/api/client";
import type { MarketPulse, PulseRow } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { compact, pct, pnlClass } from "@/lib/format";
import { Badge, Card, Meter, Skeleton } from "@/components/shared/ui";

const MOOD_TONE = { "risk-on": "profit", "risk-off": "loss", mixed: "warn" } as const;

function List({ title, rows, value }: { title: string; rows: PulseRow[]; value: (r: PulseRow) => React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-dim">{title}</div>
      {rows.length === 0 && <div className="text-xs text-dim">none</div>}
      <ul className="num space-y-1">
        {rows.map((r) => (
          <li key={r.coin} className="flex items-center justify-between text-xs">
            <span className="font-medium text-text">{r.coin}</span>{value(r)}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function MarketPulseCard() {
  const { data: p } = usePoll(() => api.get<MarketPulse>("/api/markets/pulse"), 30000);
  return (
    <Card title="Market pulse" subtitle={p ? `Top ${p.markets} perps by volume` : "Loading"} icon={<Gauge className="h-4 w-4" />}
          right={p && <Badge tone={MOOD_TONE[p.mood]} dot>{p.mood}</Badge>}>
      {!p ? <div className="space-y-2"><Skeleton /><Skeleton /><Skeleton className="h-16 w-full" /></div> : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div>
              <div className="text-[11px] uppercase tracking-wider text-dim">Breadth</div>
              <div className="num text-lg font-semibold">{pct(p.breadth_pct, 0)}</div>
              <Meter value={p.breadth_pct / 100} tone={p.breadth_pct >= 60 ? "profit" : p.breadth_pct <= 40 ? "loss" : "warn"} />
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wider text-dim">BTC 24h</div>
              <div className={`num text-lg font-semibold ${pnlClass(p.btc_change_pct)}`}>{pct(p.btc_change_pct, 2, true)}</div>
            </div>
            <div title="Volume-weighted hourly funding. Positive: longs pay shorts, the market leans long.">
              <div className="text-[11px] uppercase tracking-wider text-dim">Funding / h</div>
              <div className="num text-lg font-semibold">{pct(p.funding_pct_h, 4, true)}</div>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wider text-dim">Open interest</div>
              <div className="num text-lg font-semibold">${compact(p.open_interest_usd)}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 border-t border-line/60 pt-3 md:grid-cols-4">
            <List title="Top gainers" rows={p.gainers} value={(r) => <span className="text-profit">{pct(r.change_pct, 1, true)}</span>} />
            <List title="Top losers" rows={p.losers} value={(r) => <span className="text-loss">{pct(r.change_pct, 1, true)}</span>} />
            <List title="Crowded longs" rows={p.crowded_longs} value={(r) => <span className="text-warn">{pct(r.funding_pct_h, 4, true)}</span>} />
            <List title="Crowded shorts" rows={p.crowded_shorts} value={(r) => <span className="text-accent">{pct(r.funding_pct_h, 4, true)}</span>} />
          </div>
        </div>
      )}
    </Card>
  );
}
