import { useEffect, useState } from "react";
import { CandlestickChart } from "lucide-react";
import { api } from "@/api/client";
import type { Account, Trade } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { pct, price, pnlClass, r, sameCoin, signed } from "@/lib/format";
import { Button, Card, ErrorLine, Notice, Side, Stat, confirmAction } from "@/components/shared/ui";
import { CandleChart, type PriceLevel } from "@/components/markets/CandleChart";
import { COLORS } from "@/lib/chart";
import { markPrice, targets } from "@/components/dashboard/positionTargets";

/** `#chart/<coin>` opened from a dashboard position: the coin's chart with the trade's levels on it. */
export function PositionChartPage({ coin }: { coin: string }) {
  const acc = usePoll(() => api.get<Account>("/api/account"), 5000);
  const open = usePoll(() => api.get<Trade[]>("/api/trades/open"), 5000);
  const [msg, setMsg] = useState("");
  const p = acc.data?.positions.find((x) => sameCoin(x.coin, coin));
  const t = open.data?.find((x) => sameCoin(x.coin, coin));
  const mark = p ? markPrice(p) : null;
  const g = t && p ? targets(t, mark, p.size) : null;

  useEffect(() => { document.title = `${coin} chart - Crypto Trader`; }, [coin]);

  const levels: PriceLevel[] = t ? [
    { price: t.entry_price, color: COLORS.accent2, title: "Entry" },
    { price: t.stop_loss, color: COLORS.loss, title: "Stop" },
    ...t.take_profits.map((tp, i) => ({ price: tp, color: COLORS.profit, title: `TP${i + 1}${i < t.tp_hit ? " hit" : ""}` })),
  ] : [];

  const close = async () => {
    if (!t || !confirmAction(`Close #${t.id} ${t.direction} ${t.coin} at market now?`)) return;
    try {
      const res = await api.post<{ closed: boolean }>(`/api/trades/${t.id}/close`);
      setMsg(res.closed ? `#${t.id} ${t.coin} closed` : `#${t.id}: the exchange refused the close; see the log`);
      open.reload(); acc.reload();
    } catch (e) { setMsg(String(e)); }
  };

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-5 p-4 sm:p-6">
      <ErrorLine error={acc.error || open.error} />
      {msg && <Notice>{msg}</Notice>}
      {acc.data && !p && <Notice tone="warn">No open position in {coin} now. The chart is still live.</Notice>}
      {p && !t && open.data && <Notice tone="warn">Crypto Trader did not open this {coin} position, so it has no stop or TP here and is left untouched.</Notice>}
      {p && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <Stat label="Side" value={<Side direction={p.direction} />} sub={`${Math.abs(p.size)} ${coin} at ${price(p.entry_price)}`} />
          <Stat label="Unrealised" value={signed(p.unrealised_pnl)} tone={pnlClass(p.unrealised_pnl)} sub={g ? r(g.rNow) : undefined} />
          <Stat label={g?.nextTp != null ? `To TP${g.nextTpIndex + 1}` : "To TP"} value={g?.nextTp != null ? pct(g.toTpPct, 2, true) : "-"}
                sub={g?.nextTp != null ? `${price(g.nextTp)}, ${signed(g.pnlAtTp)} there` : t ? "every TP hit" : undefined} />
          <Stat label="To stop" value={g ? pct(g.toStopPct, 2, true) : "-"}
                sub={g && t ? `${price(t.stop_loss)}, ${signed(g.pnlAtStop)} there` : undefined} />
          <Stat label="Close" value={t ? <Button tone="danger" onClick={close}>Close at market</Button> : "-"}
                sub={t ? `trade #${t.id}, ${t.engine.replace("_", " ")}` : undefined} />
        </div>
      )}
      <Card title={<span className="flex items-center gap-2">{coin}<span className="num text-muted">{price(mark)}</span></span>}
            subtitle="Dashed lines: entry, stop and take-profits" icon={<CandlestickChart className="h-4 w-4" />}>
        <CandleChart coin={coin} levels={levels} height={560} />
      </Card>
    </div>
  );
}
