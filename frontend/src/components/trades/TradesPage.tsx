import { useState } from "react";
import { History, ListChecks, ShieldAlert, Timer } from "lucide-react";
import { api } from "@/api/client";
import type { Analytics, GateDecision, Trade } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { pct, price, pnlClass, r, signed, time } from "@/lib/format";
import { Badge, Button, Card, ErrorLine, Notice, Side, Stat, Table, confirmAction } from "@/components/shared/ui";
import { AnalyticsCard } from "./AnalyticsCard";
import { TradeLog } from "./TradeLog";

export function TradesPage() {
  const open = usePoll(() => api.get<Trade[]>("/api/trades/open"), 5000);
  const hist = usePoll(() => api.get<Trade[]>("/api/trades/history?limit=200"), 15000);
  const stats = usePoll(() => api.get<{ closed: number; net_pnl: number; win_rate: number | null }>("/api/trades/stats"), 15000);
  const analytics = usePoll(() => api.get<Analytics>("/api/trades/analytics"), 30000);
  const [shown, setShown] = useState<number | null>(null);
  const [msg, setMsg] = useState("");

  const close = async (t: Trade) => {
    if (!confirmAction(`Close #${t.id} ${t.direction} ${t.coin} at market now?`)) return;
    try {
      const res = await api.post<{ closed: boolean }>(`/api/trades/${t.id}/close`);
      setMsg(res.closed ? `#${t.id} closed` : `#${t.id}: the exchange refused the close; see the log`);
      open.reload(); hist.reload();
    } catch (e) { setMsg(String(e)); }
  };

  return (
    <div className="space-y-5">
      <ErrorLine error={open.error || hist.error} />
      {msg && <Notice>{msg}</Notice>}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Closed trades" value={stats.data?.closed ?? "-"} />
        <Stat label="Net P&L (USDC)" value={signed(stats.data?.net_pnl)} tone={pnlClass(stats.data?.net_pnl)} />
        <Stat label="Win rate" value={stats.data?.win_rate == null ? "-" : pct(stats.data.win_rate * 100, 0)} />
        <Stat label="Open now" value={open.data?.length ?? "-"} />
      </div>
      <AnalyticsCard a={analytics.data} />
      <Card title="Open trades" subtitle="Managed by the app; exits sit on the exchange" icon={<Timer className="h-4 w-4" />}>
        <Table head={["#", "Engine", "Coin", "Side", "Entry", "Size", "Stop", "TPs hit", "Lev", "Risk", "Booked", ""]}
               align={["l", "l", "l", "l", "r", "r", "r", "r", "r", "r", "r", "r"]}
               empty={open.data && open.data.length === 0 ? "No open trades" : undefined}>
          {open.data?.map((t) => (
            <tr key={t.id}>
              <td className="text-dim">{t.id}</td>
              <td className="capitalize">{t.engine.replace("_", " ")}</td>
              <td className="font-semibold">{t.coin}</td>
              <td><Side direction={t.direction} /></td>
              <td className="text-right">{price(t.entry_price)}</td>
              <td className="text-right">{t.size}</td>
              <td className="text-right">{price(t.stop_loss)}{t.tp_hit > 0 && Math.abs(t.stop_loss - t.entry_price) <= t.entry_price * 1e-4 && <> <Badge tone="accent">BE</Badge></>}</td>
              <td className="text-right">{t.tp_hit}/{t.take_profits.length}</td>
              <td className="text-right">{t.leverage}x</td>
              <td className="text-right">${t.risk_usd.toFixed(2)}</td>
              <td className={`text-right ${pnlClass(t.net_pnl)}`}>{signed(t.net_pnl)}</td>
              <td className="whitespace-nowrap text-right">
                <span className="inline-flex gap-1">
                  <Button size="sm" tone="ghost" onClick={() => setShown(t.id)}>Log</Button>
                  <Button size="sm" tone="danger" onClick={() => close(t)}>Close</Button>
                </span>
              </td>
            </tr>
          ))}
        </Table>
      </Card>
      {shown !== null && <TradeLog id={shown} onClose={() => setShown(null)} />}
      <Card title="History" subtitle="Click a row for its full audit trail" icon={<History className="h-4 w-4" />}>
        <Table head={["#", "Opened", "Engine", "Coin", "Side", "Entry", "Exit", "Reason", "Net", "R", "Network"]}
               align={["l", "l", "l", "l", "l", "r", "r", "l", "r", "r", "l"]}
               empty={hist.data && hist.data.length === 0 ? "No trades yet" : undefined}>
          {hist.data?.map((t) => (
            <tr key={t.id} className="cursor-pointer" onClick={() => setShown(t.id)}>
              <td className="text-dim">{t.id}</td>
              <td className="whitespace-nowrap">{time(t.opened_at)}</td>
              <td className="capitalize">{t.engine.replace("_", " ")}</td>
              <td className="font-semibold">{t.coin}</td>
              <td><Side direction={t.direction} /></td>
              <td className="text-right">{price(t.entry_price)}</td>
              <td className="text-right">{price(t.close_price)}</td>
              <td className="text-xs text-muted">{t.close_reason ?? t.status}</td>
              <td className={`text-right font-medium ${pnlClass(t.net_pnl)}`}>{signed(t.net_pnl)}</td>
              <td className={`text-right ${pnlClass(t.r_achieved)}`}>{r(t.r_achieved)}</td>
              <td><Badge>{t.network}</Badge></td>
            </tr>
          ))}
        </Table>
      </Card>
      <Decisions />
    </div>
  );
}

function Decisions() {
  const { data } = usePoll(() => api.get<GateDecision[]>("/api/trades/decisions?limit=50"), 15000);
  return (
    <Card title="Risk gate decisions" subtitle="Latest 50 signals that reached the gates" icon={<ShieldAlert className="h-4 w-4" />}
          right={<ListChecks className="h-4 w-4 text-dim" />}>
      <Table head={["Time", "Engine", "Coin", "Side", "Result", "First refusal"]}
             empty={data && data.length === 0 ? "Nothing reached the gates yet (an engine must be live)" : undefined}>
        {data?.map((d) => {
          const refusal = d.decisions.find((x) => !x.passed);
          return (
            <tr key={d.id}>
              <td className="whitespace-nowrap">{time(d.ts)}</td>
              <td className="capitalize">{d.engine.replace("_", " ")}</td>
              <td className="font-medium">{d.coin}</td>
              <td><Side direction={d.direction} /></td>
              <td>{d.passed ? <Badge tone="profit">placed</Badge> : <Badge tone="warn">refused</Badge>}</td>
              <td className="text-xs text-muted">{refusal ? `${refusal.gate}: ${refusal.detail}` : "-"}</td>
            </tr>
          );
        })}
      </Table>
    </Card>
  );
}
