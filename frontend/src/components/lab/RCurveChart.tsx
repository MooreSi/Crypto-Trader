import { createChart, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { CHART_BASE, COLORS } from "@/lib/chart";

/** Cumulative R over the backtest's trades. */
export function RCurveChart({ curve }: { curve: { t: number; r: number }[] }) {
  const el = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!el.current || curve.length < 1) return;
    const c = createChart(el.current, CHART_BASE);
    const s = c.addBaselineSeries({ baseValue: { type: "price", price: 0 }, lineWidth: 2,
      topLineColor: COLORS.profit, topFillColor1: "rgba(16,185,129,0.25)", topFillColor2: "rgba(16,185,129,0)",
      bottomLineColor: COLORS.loss, bottomFillColor1: "rgba(244,63,94,0)", bottomFillColor2: "rgba(244,63,94,0.25)",
      priceLineVisible: false, priceFormat: { type: "custom", formatter: (v: number) => `${v.toFixed(1)}R` } });
    // Two trades can close in the same second; the chart needs strictly rising times.
    let last = 0;
    s.setData(curve.map((p) => {
      last = Math.max(last + 1, Math.floor(p.t));
      return { time: last as UTCTimestamp, value: p.r };
    }));
    c.timeScale().fitContent();
    return () => c.remove();
  }, [curve]);
  return <div ref={el} style={{ height: 260 }} />;
}
