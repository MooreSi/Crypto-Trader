import { useMemo, useState } from "react";
import { api } from "@/api/client";
import type { Market, RiskSettings } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { compact, pnlClass, price } from "@/lib/format";
import { Badge, Button, Card, ErrorLine, Table } from "@/components/shared/ui";
import { CandleChart } from "./CandleChart";

export function MarketsPage() {
  const { data, error } = usePoll(() => api.get<Market[]>("/api/markets"), 15000);
  const risk = usePoll(() => api.get<RiskSettings>("/api/risk"), 30000);
  const [filter, setFilter] = useState("");
  const [chart, setChart] = useState("BTC");
  const [msg, setMsg] = useState("");

  const watch = (risk.data?.watchlist as string[]) ?? [];
  const block = (risk.data?.blocklist as string[]) ?? [];
  const rows = useMemo(
    () => (data ?? []).filter((m) => m.coin.toLowerCase().includes(filter.toLowerCase())),
    [data, filter],
  );

  const toggleList = async (key: "watchlist" | "blocklist", coin: string) => {
    const list = key === "watchlist" ? watch : block;
    const next = list.includes(coin) ? list.filter((c) => c !== coin) : [...list, coin];
    try {
      await api.post("/api/risk", { fields: { [key]: next } });
      await risk.reload();
      setMsg("");
    } catch (e) {
      setMsg(String(e));
    }
  };

  return (
    <div className="space-y-4">
      <ErrorLine error={error || msg} />
      <Card title={`${chart} chart`}>
        <CandleChart coin={chart} />
      </Card>
      <Card
        title={`Markets (${data?.length ?? 0} perpetuals)`}
        right={<input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter"
                      className="rounded-md border border-line bg-panel-2 px-2 py-1 text-sm" />}
      >
        <p className="mb-3 text-xs text-muted">
          The engines scan {watch.length ? <>your watchlist ({watch.join(", ")})</> : <>the top {String(risk.data?.auto_top_n ?? 20)} markets by 24h volume</>},
          minus the blocklist. Funding is hourly; positive means longs pay shorts.
        </p>
        <Table head={["Coin", "Price", "24h", "Funding/h", "Open interest", "24h volume", "Max lev", "Scanned", ""]}>
          {rows.map((m) => (
            <tr key={m.coin} className="hover:bg-panel-2">
              <td className="cursor-pointer px-2 py-1.5 font-medium text-accent" onClick={() => setChart(m.coin)}>{m.coin}</td>
              <td className="px-2 py-1.5">{price(m.mark_price)}</td>
              <td className={`px-2 py-1.5 ${pnlClass(m.change_24h_pct)}`}>{m.change_24h_pct.toFixed(2)}%</td>
              <td className={`px-2 py-1.5 ${pnlClass(-m.funding_rate)}`}>{(m.funding_rate * 100).toFixed(4)}%</td>
              <td className="px-2 py-1.5">${compact(m.open_interest * m.mark_price)}</td>
              <td className="px-2 py-1.5">${compact(m.day_notional_volume)}</td>
              <td className="px-2 py-1.5">{m.max_leverage}x{m.only_isolated ? " iso" : ""}</td>
              <td className="px-2 py-1.5">{m.scanned ? <Badge tone="accent">yes</Badge> : <span className="text-muted">-</span>}</td>
              <td className="space-x-1 whitespace-nowrap px-2 py-1.5">
                <Button onClick={() => toggleList("watchlist", m.coin)}>{watch.includes(m.coin) ? "Unwatch" : "Watch"}</Button>
                <Button onClick={() => toggleList("blocklist", m.coin)}>{block.includes(m.coin) ? "Unblock" : "Block"}</Button>
              </td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
