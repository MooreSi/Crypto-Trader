import { useState } from "react";
import { api } from "@/api/client";
import type { GateDecision, Trade, TradeEvent } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { price, pnlClass, signed, time } from "@/lib/format";
import { Badge, Button, Card, ErrorLine, Stat, Table, confirmAction } from "@/components/shared/ui";

export function TradesPage() {
  const open = usePoll(() => api.get<Trade[]>("/api/trades/open"), 5000);
  const hist = usePoll(() => api.get<Trade[]>("/api/trades/history?limit=200"), 15000);
  const stats = usePoll(() => api.get<{ closed: number; net_pnl: number; win_rate: number | null }>("/api/trades/stats"), 15000);
  const [shown, setShown] = useState<number | null>(null);
  const [msg, setMsg] = useState("");

  const close = async (t: Trade) => {
    if (!confirmAction(`Close #${t.id} ${t.direction} ${t.coin} at market now?`)) return;
    try {
      const r = await api.post<{ closed: boolean }>(`/api/trades/${t.id}/close`);
      setMsg(r.closed ? `#${t.id} closed` : `#${t.id}: the exchange refused the close; see the log`);
      open.reload(); hist.reload();
    } catch (e) { setMsg(String(e)); }
  };

  return (
    <div className="space-y-4">
      <ErrorLine error={open.error || hist.error} />
      {msg && <div className="rounded-md border border-line bg-panel-2 px-3 py-2 text-sm">{msg}</div>}
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Closed trades" value={stats.data?.closed ?? "-"} />
        <Stat label="Net P&L (USDC)" value={signed(stats.data?.net_pnl)} tone={pnlClass(stats.data?.net_pnl)} />
        <Stat label="Win rate" value={stats.data?.win_rate == null ? "-" : `${(stats.data.win_rate * 100).toFixed(0)}%`} />
      </div>
      <Card title={`Open trades (${open.data?.length ?? 0})`}>
        <Table head={["#", "Engine", "Coin", "Side", "Entry", "Size", "Stop", "TPs hit", "Lev", "Risk", "Booked", ""]}
               empty={open.data && open.data.length === 0 ? "No open trades" : undefined}>
          {open.data?.map((t) => (
            <tr key={t.id}>
              <td className="px-2 py-1.5">{t.id}</td>
              <td className="px-2 py-1.5">{t.engine}</td>
              <td className="px-2 py-1.5 font-medium">{t.coin}</td>
              <td className="px-2 py-1.5"><Badge tone={t.direction === "long" ? "profit" : "loss"}>{t.direction}</Badge></td>
              <td className="px-2 py-1.5">{price(t.entry_price)}</td>
              <td className="px-2 py-1.5">{t.size}</td>
              <td className="px-2 py-1.5">{price(t.stop_loss)}{t.tp_hit > 0 && Math.abs(t.stop_loss - t.entry_price) <= t.entry_price * 1e-4 && <Badge tone="accent"> BE</Badge>}</td>
              <td className="px-2 py-1.5">{t.tp_hit}/{t.take_profits.length}</td>
              <td className="px-2 py-1.5">{t.leverage}x</td>
              <td className="px-2 py-1.5">${t.risk_usd.toFixed(2)}</td>
              <td className={`px-2 py-1.5 ${pnlClass(t.net_pnl)}`}>{signed(t.net_pnl)}</td>
              <td className="px-2 py-1.5 space-x-1 whitespace-nowrap">
                <Button onClick={() => setShown(t.id)}>Log</Button>
                <Button tone="danger" onClick={() => close(t)}>Close</Button>
              </td>
            </tr>
          ))}
        </Table>
      </Card>
      {shown !== null && <TradeLog id={shown} onClose={() => setShown(null)} />}
      <Card title="History">
        <Table head={["#", "Opened", "Engine", "Coin", "Side", "Entry", "Exit", "Reason", "Net", "R", "Network"]}
               empty={hist.data && hist.data.length === 0 ? "No trades yet" : undefined}>
          {hist.data?.map((t) => (
            <tr key={t.id} className="cursor-pointer hover:bg-panel-2" onClick={() => setShown(t.id)}>
              <td className="px-2 py-1.5">{t.id}</td>
              <td className="whitespace-nowrap px-2 py-1.5">{time(t.opened_at)}</td>
              <td className="px-2 py-1.5">{t.engine}</td>
              <td className="px-2 py-1.5 font-medium">{t.coin}</td>
              <td className="px-2 py-1.5">{t.direction}</td>
              <td className="px-2 py-1.5">{price(t.entry_price)}</td>
              <td className="px-2 py-1.5">{price(t.close_price)}</td>
              <td className="px-2 py-1.5 text-xs">{t.close_reason ?? t.status}</td>
              <td className={`px-2 py-1.5 ${pnlClass(t.net_pnl)}`}>{signed(t.net_pnl)}</td>
              <td className="px-2 py-1.5">{t.r_achieved == null ? "-" : t.r_achieved.toFixed(2)}</td>
              <td className="px-2 py-1.5"><Badge>{t.network}</Badge></td>
            </tr>
          ))}
        </Table>
      </Card>
      <Decisions />
    </div>
  );
}

function TradeLog({ id, onClose }: { id: number; onClose: () => void }) {
  const { data } = usePoll(() => api.get<TradeEvent[]>(`/api/trades/${id}/events`), 10000, [id]);
  return (
    <Card title={`Trade #${id}: every change`} right={<Button onClick={onClose}>Hide</Button>}>
      <ul className="space-y-2 text-sm">
        {data?.map((e, i) => (
          <li key={i} className="rounded border border-line bg-panel-2 px-3 py-2">
            <div className="flex justify-between"><Badge tone="accent">{e.kind}</Badge><span className="text-xs text-muted">{time(e.ts)}</span></div>
            <pre className="mt-1 overflow-x-auto whitespace-pre-wrap text-xs text-muted">{JSON.stringify(e.detail, null, 1)}</pre>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Decisions() {
  const { data } = usePoll(() => api.get<GateDecision[]>("/api/trades/decisions?limit=50"), 15000);
  return (
    <Card title="Risk gate decisions (latest 50)">
      <Table head={["Time", "Engine", "Coin", "Side", "Result", "First refusal"]}
             empty={data && data.length === 0 ? "Nothing reached the gates yet (an engine must be live)" : undefined}>
        {data?.map((d) => {
          const refusal = d.decisions.find((x) => !x.passed);
          return (
            <tr key={d.id}>
              <td className="whitespace-nowrap px-2 py-1.5">{time(d.ts)}</td>
              <td className="px-2 py-1.5">{d.engine}</td>
              <td className="px-2 py-1.5">{d.coin}</td>
              <td className="px-2 py-1.5">{d.direction}</td>
              <td className="px-2 py-1.5">{d.passed ? <Badge tone="profit">placed</Badge> : <Badge tone="warn">refused</Badge>}</td>
              <td className="px-2 py-1.5 text-xs text-muted">{refusal ? `${refusal.gate}: ${refusal.detail}` : "-"}</td>
            </tr>
          );
        })}
      </Table>
    </Card>
  );
}
