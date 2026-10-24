import { createChart, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { api } from "@/api/client";
import { usePoll } from "@/hooks/usePoll";

export function EquityChart() {
  const { data } = usePoll(() => api.get<{ ts: number; equity: number }[]>("/api/account/equity?days=30"), 60000);
  const el = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!el.current || !data || data.length < 2) return;
    chart.current?.remove();
    const c = createChart(el.current, {
      height: 220, layout: { background: { color: "transparent" }, textColor: "#8a9bb8" },
      grid: { vertLines: { color: "#1b2742" }, horzLines: { color: "#1b2742" } },
      timeScale: { timeVisible: true }, rightPriceScale: { borderColor: "#22304d" },
    });
    const s = c.addAreaSeries({ lineColor: "#22d3ee", topColor: "rgba(34,211,238,0.25)", bottomColor: "rgba(34,211,238,0)" });
    s.setData(data.map((d) => ({ time: Math.floor(d.ts) as UTCTimestamp, value: d.equity })));
    c.timeScale().fitContent();
    chart.current = c;
    return () => { c.remove(); chart.current = null; };
  }, [data]);

  if (!data || data.length < 2) {
    return <div className="py-8 text-center text-sm text-muted">The equity curve fills in as the app runs (a point every 5 minutes).</div>;
  }
  return <div ref={el} />;
}
