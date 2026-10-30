import { useState } from "react";
import { Layers } from "lucide-react";
import { api } from "@/api/client";
import type { Account, Position, Trade } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { pct, price, pnlClass, r, sameCoin, signed, usd } from "@/lib/format";
import { Button, Card, Notice, Side, Table, confirmAction } from "@/components/shared/ui";
import { markPrice, targets } from "./positionTargets";

export const chartHref = (coin: string) => `#chart/${encodeURIComponent(coin)}`;

/** One price level and the move from the mark needed to reach it. */
function Level({ label, at, movePct, pnl }: { label?: string; at: number | null; movePct: number | null; pnl: number | null }) {
  if (at === null) return <span className="text-dim">-</span>;
  return (
    <div className="leading-tight">
      <div>{label && <span className="mr-1 text-[11px] text-dim">{label}</span>}{price(at)}</div>
      <div className="text-[11px] text-muted">
        <span>{pct(movePct, 2, true)}</span> <span className={pnlClass(pnl)}>{signed(pnl)}</span>
      </div>
    </div>
  );
}

export function PositionsCard({ acc, reload }: { acc: Account | null; reload: () => void }) {
  const open = usePoll(() => api.get<Trade[]>("/api/trades/open"), 5000);
  const [msg, setMsg] = useState("");
  const tradeFor = (p: Position) => open.data?.find((t) => sameCoin(t.coin, p.coin));

  const close = async (t: Trade) => {
    if (!confirmAction(`Close #${t.id} ${t.direction} ${t.coin} at market now?`)) return;
    try {
      const res = await api.post<{ closed: boolean }>(`/api/trades/${t.id}/close`);
      setMsg(res.closed ? `#${t.id} ${t.coin} closed` : `#${t.id}: the exchange refused the close; see the log`);
      open.reload(); reload();
    } catch (e) { setMsg(String(e)); }
  };

  return (
    <Card title="Positions" subtitle={`${acc?.positions.length ?? 0} open. Click one for its chart; moves are from the mark price`}
          icon={<Layers className="h-4 w-4" />}>
      {msg && <div className="mb-3"><Notice>{msg}</Notice></div>}
      <Table head={["Coin", "Side", "Size", "Entry", "Mark", "Unrealised", "Now", "Next TP", "Stop", "Lev", "Liquidation", "Margin", ""]}
             align={["l", "l", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r"]}
             empty={acc && acc.positions.length === 0 ? "No open positions" : undefined}>
        {acc?.positions.map((p) => {
          const t = tradeFor(p);
          const mark = markPrice(p);
          const g = t ? targets(t, mark, p.size) : null;
          return (
            <tr key={p.coin} className="cursor-pointer" onClick={() => window.open(chartHref(p.coin), "_blank")}>
              <td><a href={chartHref(p.coin)} target="_blank" rel="noopener" onClick={(e) => e.stopPropagation()}
                     className="font-semibold text-accent hover:underline">{p.coin}</a></td>
              <td><Side direction={p.direction} /></td>
              <td className="text-right">{Math.abs(p.size)}</td>
              <td className="text-right">{price(p.entry_price)}</td>
              <td className="text-right">{price(mark)}</td>
              <td className={`text-right font-medium ${pnlClass(p.unrealised_pnl)}`}>{signed(p.unrealised_pnl)}</td>
              <td className={`text-right ${pnlClass(g?.rNow)}`}>{g ? r(g.rNow) : "-"}</td>
              <td className="text-right">
                {g ? <Level label={g.nextTp === null ? undefined : `TP${g.nextTpIndex + 1}`} at={g.nextTp}
                            movePct={g.toTpPct} pnl={g.pnlAtTp} /> : "-"}
              </td>
              <td className="text-right">{g && t ? <Level at={t.stop_loss} movePct={g.toStopPct} pnl={g.pnlAtStop} /> : "-"}</td>
              <td className="text-right">{p.leverage}x</td>
              <td className="text-right text-warn">{price(p.liquidation_price)}</td>
              <td className="text-right">{usd(p.margin_used)}</td>
              <td className="whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
                {t ? <Button size="sm" tone="danger" onClick={() => close(t)}>Close</Button>
                   : open.data ? <span className="text-xs text-dim">not managed</span> : null}
              </td>
            </tr>
          );
        })}
      </Table>
    </Card>
  );
}
