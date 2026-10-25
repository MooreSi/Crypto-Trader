import { useMemo, useState } from "react";
import clsx from "clsx";
import { ArrowDown, ArrowUp, Ban, CandlestickChart, Eye, EyeOff, Search, Undo2 } from "lucide-react";
import { api } from "@/api/client";
import type { Market, RiskSettings } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { compact, pct, pnlClass, price, sameCoin } from "@/lib/format";
import { Badge, Button, Card, ErrorLine, Table, inputCls } from "@/components/shared/ui";
import { CandleChart } from "./CandleChart";

type SortKey = "day_notional_volume" | "change_24h_pct" | "funding_rate" | "oi";
const SORTS: { key: SortKey; label: string }[] = [
  { key: "day_notional_volume", label: "Volume" }, { key: "change_24h_pct", label: "24h" },
  { key: "funding_rate", label: "Funding" }, { key: "oi", label: "OI" },
];

const val = (m: Market, k: SortKey) => (k === "oi" ? m.open_interest * m.mark_price : m[k]);

export function MarketsPage() {
  const { data, error } = usePoll(() => api.get<Market[]>("/api/markets"), 15000);
  const risk = usePoll(() => api.get<RiskSettings>("/api/risk"), 30000);
  const [filter, setFilter] = useState("");
  const [chart, setChart] = useState("BTC");
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: "day_notional_volume", desc: true });
  const [msg, setMsg] = useState("");

  const watch = (risk.data?.watchlist as string[]) ?? [];
  const block = (risk.data?.blocklist as string[]) ?? [];
  const has = (list: string[], coin: string) => list.some((c) => sameCoin(c, coin));
  const rows = useMemo(() => {
    const f = filter.toLowerCase();
    const out = (data ?? []).filter((m) => m.coin.toLowerCase().includes(f));
    return out.sort((a, b) => (val(a, sort.key) - val(b, sort.key)) * (sort.desc ? -1 : 1));
  }, [data, filter, sort]);
  const current = data?.find((m) => m.coin === chart);

  const toggleList = async (key: "watchlist" | "blocklist", coin: string) => {
    const list = key === "watchlist" ? watch : block;
    const next = has(list, coin) ? list.filter((c) => !sameCoin(c, coin)) : [...list, coin];
    try {
      await api.post("/api/risk", { fields: { [key]: next } });
      await risk.reload();
      setMsg("");
    } catch (e) {
      setMsg(String(e));
    }
  };

  return (
    <div className="space-y-5">
      <ErrorLine error={error || msg} />
      <Card title={<span className="flex items-center gap-2">{chart}<span className="num text-muted">{price(current?.mark_price)}</span>
                     {current && <span className={clsx("num text-xs", pnlClass(current.change_24h_pct))}>{pct(current.change_24h_pct, 2, true)}</span>}</span>}
            subtitle="Click a market below to chart it" icon={<CandlestickChart className="h-4 w-4" />}>
        <CandleChart coin={chart} />
      </Card>
      <Card title={`Markets`} subtitle={`${data?.length ?? 0} perpetuals, ${data?.filter((m) => m.scanned).length ?? 0} scanned`}
            right={
              <div className="relative">
                <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-dim" />
                <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Search coin"
                       className={clsx(inputCls, "w-40 pl-8")} />
              </div>}>
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-muted">
          <span>Sort</span>
          {SORTS.map((s) => (
            <button key={s.key} type="button"
                    onClick={() => setSort((p) => ({ key: s.key, desc: p.key === s.key ? !p.desc : true }))}
                    className={clsx("flex items-center gap-1 rounded-md border px-2 py-0.5",
                      sort.key === s.key ? "border-accent/50 text-text" : "border-line text-muted hover:text-text")}>
              {s.label}{sort.key === s.key && (sort.desc ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />)}
            </button>
          ))}
          <span className="ml-auto">
            Engines scan {watch.length ? <>your watchlist ({watch.join(", ")})</> : <>the top {String(risk.data?.auto_top_n ?? 20)} by 24h volume</>}, minus the blocklist.
            Funding is hourly; positive means longs pay.
          </span>
        </div>
        <Table head={["Coin", "Price", "24h", "Funding/h", "Open interest", "24h volume", "Max lev", "Scanned", ""]}
               align={["l", "r", "r", "r", "r", "r", "r", "l", "r"]}>
          {rows.map((m) => {
            const watched = has(watch, m.coin), blocked = has(block, m.coin);
            return (
              <tr key={m.coin} className={clsx(m.coin === chart && "bg-accent/5")}>
                <td><button type="button" className="font-semibold text-accent hover:underline" onClick={() => setChart(m.coin)}>{m.coin}</button>
                  {watched && <Eye className="ml-1.5 inline h-3 w-3 text-accent" />}{blocked && <Ban className="ml-1.5 inline h-3 w-3 text-loss" />}</td>
                <td className="text-right">{price(m.mark_price)}</td>
                <td className={`text-right ${pnlClass(m.change_24h_pct)}`}>{pct(m.change_24h_pct, 2, true)}</td>
                <td className={`text-right ${pnlClass(-m.funding_rate)}`}>{(m.funding_rate * 100).toFixed(4)}%</td>
                <td className="text-right">${compact(m.open_interest * m.mark_price)}</td>
                <td className="text-right">${compact(m.day_notional_volume)}</td>
                <td className="text-right text-muted">{m.max_leverage}x{m.only_isolated ? " iso" : ""}</td>
                <td>{m.scanned ? <Badge tone="accent">yes</Badge> : <span className="text-dim">-</span>}</td>
                <td className="whitespace-nowrap text-right">
                  <span className="inline-flex gap-1">
                    <Button size="sm" tone="ghost" onClick={() => toggleList("watchlist", m.coin)}>
                      {watched ? <><EyeOff className="h-3.5 w-3.5" />Unwatch</> : <><Eye className="h-3.5 w-3.5" />Watch</>}
                    </Button>
                    <Button size="sm" tone="ghost" onClick={() => toggleList("blocklist", m.coin)}>
                      {blocked ? <><Undo2 className="h-3.5 w-3.5" />Unblock</> : <><Ban className="h-3.5 w-3.5" />Block</>}
                    </Button>
                  </span>
                </td>
              </tr>
            );
          })}
        </Table>
      </Card>
    </div>
  );
}
