import { createChart, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { CHART_BASE, COLORS } from "@/lib/chart";
import { Segmented } from "@/components/shared/ui";

interface Row { t: number; open: number; high: number; low: number; close: number; volume: number }
const INTERVALS = ["5m", "15m", "1h", "4h", "1d"] as const;
type Interval = (typeof INTERVALS)[number];

export function CandleChart({ coin }: { coin: string }) {
  const el = useRef<HTMLDivElement>(null);
  const [interval, setIv] = useState<Interval>("15m");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let remove: (() => void) | undefined;
    api.get<Row[]>(`/api/markets/${encodeURIComponent(coin)}/candles?interval=${interval}&bars=300`)
      .then((rows) => {
        if (cancelled || !el.current) return;
        const c = createChart(el.current, CHART_BASE);
        const s = c.addCandlestickSeries({ upColor: COLORS.profit, downColor: COLORS.loss, wickUpColor: COLORS.profit,
          wickDownColor: COLORS.loss, borderVisible: false });
        s.setData(rows.map((r) => ({ time: Math.floor(r.t / 1000) as UTCTimestamp, open: r.open, high: r.high, low: r.low, close: r.close })));
        const v = c.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "vol", lastValueVisible: false, priceLineVisible: false });
        c.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
        v.setData(rows.map((r) => ({ time: Math.floor(r.t / 1000) as UTCTimestamp, value: r.volume,
          color: r.close >= r.open ? "rgba(16,185,129,0.35)" : "rgba(244,63,94,0.35)" })));
        c.timeScale().fitContent();
        remove = () => c.remove();
        setError("");
      })
      .catch((e) => setError(String(e)));
    return () => { cancelled = true; remove?.(); };
  }, [coin, interval]);

  return (
    <div>
      <div className="mb-3"><Segmented value={interval} options={INTERVALS} onChange={setIv} /></div>
      {error ? <div className="text-sm text-loss">{error}</div> : <div ref={el} style={{ height: 360 }} />}
    </div>
  );
}
