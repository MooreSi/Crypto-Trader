import { createChart, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";

interface Row { t: number; open: number; high: number; low: number; close: number; volume: number }
const INTERVALS = ["5m", "15m", "1h", "4h", "1d"];

export function CandleChart({ coin }: { coin: string }) {
  const el = useRef<HTMLDivElement>(null);
  const [interval, setInterval] = useState("15m");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let remove: (() => void) | undefined;
    api.get<Row[]>(`/api/markets/${encodeURIComponent(coin)}/candles?interval=${interval}&bars=300`)
      .then((rows) => {
        if (cancelled || !el.current) return;
        const c = createChart(el.current, {
          height: 320, layout: { background: { color: "transparent" }, textColor: "#8a9bb8" },
          grid: { vertLines: { color: "#1b2742" }, horzLines: { color: "#1b2742" } },
          timeScale: { timeVisible: true },
        });
        const s = c.addCandlestickSeries({ upColor: "#10b981", downColor: "#f43f5e", wickUpColor: "#10b981", wickDownColor: "#f43f5e", borderVisible: false });
        s.setData(rows.map((r) => ({ time: Math.floor(r.t / 1000) as UTCTimestamp, open: r.open, high: r.high, low: r.low, close: r.close })));
        c.timeScale().fitContent();
        remove = () => c.remove();
        setError("");
      })
      .catch((e) => setError(String(e)));
    return () => { cancelled = true; remove?.(); };
  }, [coin, interval]);

  return (
    <div>
      <div className="mb-2 flex gap-1">
        {INTERVALS.map((i) => (
          <button key={i} type="button" onClick={() => setInterval(i)}
                  className={`rounded px-2 py-0.5 text-xs ${i === interval ? "bg-accent text-bg" : "bg-panel-2 text-muted"}`}>{i}</button>
        ))}
      </div>
      {error ? <div className="text-sm text-loss">{error}</div> : <div ref={el} />}
    </div>
  );
}
