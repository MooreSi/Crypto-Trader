import { createChart, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { CHART_BASE, COLORS } from "@/lib/chart";
import { Empty } from "@/components/shared/ui";

export type EquityPoint = { ts: number; equity: number };

export function EquityChart({ data, height = 240 }: { data: EquityPoint[] | null; height?: number }) {
  const el = useRef<HTMLDivElement>(null);
  const enough = !!data && data.length >= 2;

  useEffect(() => {
    if (!el.current || !data || data.length < 2) return;
    const c = createChart(el.current, CHART_BASE);
    const s = c.addAreaSeries({ lineColor: COLORS.accent, lineWidth: 2, topColor: "rgba(34,211,238,0.28)",
      bottomColor: "rgba(34,211,238,0)", priceLineVisible: false });
    s.setData(data.map((d) => ({ time: Math.floor(d.ts) as UTCTimestamp, value: d.equity })));
    c.timeScale().fitContent();
    return () => c.remove();
  }, [data]);

  if (!enough) return <Empty>The equity curve fills in as the app runs (a point every 5 minutes).</Empty>;
  return <div ref={el} style={{ height }} />;
}
