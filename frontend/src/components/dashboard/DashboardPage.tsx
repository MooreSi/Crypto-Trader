import { api } from "@/api/client";
import type { Account, SystemStatus } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { price, pnlClass, signed, usd } from "@/lib/format";
import { Badge, Card, ErrorLine, Stat, Table } from "@/components/shared/ui";
import { EquityChart } from "./EquityChart";

export function DashboardPage({ status }: { status: SystemStatus | null }) {
  const { data: acc, error } = usePoll(() => api.get<Account>("/api/account"), 5000);
  return (
    <div className="space-y-4">
      <ErrorLine error={error} />
      {status && status.unmanaged_positions.length > 0 && (
        <div className="rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">
          Positions on this account that Crypto Trader did not open (left untouched): {status.unmanaged_positions.join(", ")}
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat label="Equity (USDC)" value={usd(acc?.equity)} />
        <Stat label="Available" value={usd(acc?.available)} />
        <Stat label="Margin used" value={usd(acc?.margin_used)} />
        <Stat label="Today (equity)" value={signed(acc?.day_pnl)} tone={pnlClass(acc?.day_pnl)} />
        <Stat label="Today (realised)" value={signed(acc?.realised_today)} tone={pnlClass(acc?.realised_today)} />
      </div>
      <Card title="Equity">
        <EquityChart />
      </Card>
      <Card title={`Positions (${acc?.positions.length ?? 0})`}>
        <Table head={["Coin", "Side", "Size", "Entry", "Unrealised", "Leverage", "Liquidation", "Margin"]}
               empty={acc && acc.positions.length === 0 ? "No open positions" : undefined}>
          {acc?.positions.map((p) => (
            <tr key={p.coin}>
              <td className="px-2 py-1.5 font-medium">{p.coin}</td>
              <td className="px-2 py-1.5"><Badge tone={p.direction === "long" ? "profit" : "loss"}>{p.direction}</Badge></td>
              <td className="px-2 py-1.5">{Math.abs(p.size)}</td>
              <td className="px-2 py-1.5">{price(p.entry_price)}</td>
              <td className={`px-2 py-1.5 ${pnlClass(p.unrealised_pnl)}`}>{signed(p.unrealised_pnl)}</td>
              <td className="px-2 py-1.5">{p.leverage}x</td>
              <td className="px-2 py-1.5">{price(p.liquidation_price)}</td>
              <td className="px-2 py-1.5">{usd(p.margin_used)}</td>
            </tr>
          ))}
        </Table>
      </Card>
      <Card title={`Resting orders (${acc?.open_orders.length ?? 0})`}>
        <Table head={["Coin", "Kind", "Side", "Size", "Trigger"]}
               empty={acc && acc.open_orders.length === 0 ? "No resting orders" : undefined}>
          {acc?.open_orders.map((o) => (
            <tr key={o.oid}>
              <td className="px-2 py-1.5">{o.coin}</td>
              <td className="px-2 py-1.5"><Badge tone={o.kind === "stop" ? "loss" : "profit"}>{o.kind.replace("_", " ")}</Badge></td>
              <td className="px-2 py-1.5">{o.is_buy ? "buy" : "sell"}</td>
              <td className="px-2 py-1.5">{o.size}</td>
              <td className="px-2 py-1.5">{price(o.trigger_price ?? o.limit_price)}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
