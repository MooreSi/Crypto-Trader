import { CircleDollarSign, Layers, Lock, TrendingUp, Wallet } from "lucide-react";
import { api } from "@/api/client";
import type { Account, Analytics, SystemStatus } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { pct, price, pnlClass, signed, usd } from "@/lib/format";
import { Badge, Card, ErrorLine, Meter, Notice, Side, Sparkline, Stat, Table } from "@/components/shared/ui";
import type { Tab } from "@/components/shell/Sidebar";
import { EquityChart, type EquityPoint } from "./EquityChart";
import { MarketPulseCard } from "./MarketPulseCard";
import { PerformanceCard } from "./PerformanceCard";

export function DashboardPage({ status, go }: { status: SystemStatus | null; go?: (t: Tab) => void }) {
  const { data: acc, error } = usePoll(() => api.get<Account>("/api/account"), 5000);
  const { data: curve } = usePoll(() => api.get<EquityPoint[]>("/api/account/equity?days=30"), 60000);
  const { data: perf } = usePoll(() => api.get<Analytics>("/api/trades/analytics"), 60000);
  const spark = (curve ?? []).slice(-96).map((p) => p.equity);
  const dayPct = acc && acc.day_start_equity ? (acc.day_pnl / acc.day_start_equity) * 100 : null;
  const marginUse = acc && acc.equity > 0 ? acc.margin_used / acc.equity : 0;

  return (
    <div className="space-y-5">
      <ErrorLine error={error} />
      {status && status.unmanaged_positions.length > 0 && (
        <Notice tone="warn">Positions on this account that Crypto Trader did not open (left untouched): {status.unmanaged_positions.join(", ")}</Notice>
      )}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Stat label="Equity (USDC)" value={usd(acc?.equity)} icon={<Wallet className="h-4 w-4" />}
              sub={`available ${usd(acc?.available)}`}>
          <Sparkline values={spark} className="mt-2" />
        </Stat>
        <Stat label="Today" value={signed(acc?.day_pnl)} tone={pnlClass(acc?.day_pnl)} icon={<TrendingUp className="h-4 w-4" />}
              sub={dayPct === null ? "since 00:00 UTC" : `${pct(dayPct, 2, true)} since 00:00 UTC`} />
        <Stat label="Realised today" value={signed(acc?.realised_today)} tone={pnlClass(acc?.realised_today)}
              icon={<CircleDollarSign className="h-4 w-4" />} sub="partials and closes, net of fees" />
        <Stat label="Margin used" value={usd(acc?.margin_used)} icon={<Lock className="h-4 w-4" />}
              sub={`${pct(marginUse * 100, 1)} of equity`}>
          <div className="mt-2"><Meter value={marginUse} tone={marginUse > 0.6 ? "loss" : marginUse > 0.3 ? "warn" : "accent"} /></div>
        </Stat>
      </div>
      <div className="grid gap-5 xl:grid-cols-3">
        <Card title="Equity" subtitle="Last 30 days" className="xl:col-span-2" icon={<TrendingUp className="h-4 w-4" />}>
          <EquityChart data={curve} />
        </Card>
        <PerformanceCard a={perf} onOpen={go ? () => go("Trades") : undefined} />
      </div>
      <MarketPulseCard />
      <Card title="Positions" subtitle={`${acc?.positions.length ?? 0} open`} icon={<Layers className="h-4 w-4" />}>
        <Table head={["Coin", "Side", "Size", "Entry", "Unrealised", "Leverage", "Liquidation", "Margin"]}
               align={["l", "l", "r", "r", "r", "r", "r", "r"]}
               empty={acc && acc.positions.length === 0 ? "No open positions" : undefined}>
          {acc?.positions.map((p) => (
            <tr key={p.coin}>
              <td className="font-semibold">{p.coin}</td>
              <td><Side direction={p.direction} /></td>
              <td className="text-right">{Math.abs(p.size)}</td>
              <td className="text-right">{price(p.entry_price)}</td>
              <td className={`text-right font-medium ${pnlClass(p.unrealised_pnl)}`}>{signed(p.unrealised_pnl)}</td>
              <td className="text-right">{p.leverage}x</td>
              <td className="text-right text-warn">{price(p.liquidation_price)}</td>
              <td className="text-right">{usd(p.margin_used)}</td>
            </tr>
          ))}
        </Table>
      </Card>
      <Card title="Resting orders" subtitle="Exchange-side stops and take-profits" icon={<Lock className="h-4 w-4" />}>
        <Table head={["Coin", "Kind", "Side", "Size", "Trigger"]} align={["l", "l", "l", "r", "r"]}
               empty={acc && acc.open_orders.length === 0 ? "No resting orders" : undefined}>
          {acc?.open_orders.map((o) => (
            <tr key={o.oid}>
              <td className="font-medium">{o.coin}</td>
              <td><Badge tone={o.kind === "stop" ? "loss" : o.kind === "take_profit" ? "profit" : "muted"}>{o.kind.replace("_", " ")}</Badge></td>
              <td className="text-muted">{o.is_buy ? "buy" : "sell"}</td>
              <td className="text-right">{o.size}</td>
              <td className="text-right">{price(o.trigger_price ?? o.limit_price)}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
