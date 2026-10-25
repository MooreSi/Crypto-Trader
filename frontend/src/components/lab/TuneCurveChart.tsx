import { createChart, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { CHART_BASE, COLORS } from "@/lib/chart";

type Curve = { t: number; r: number }[];

const series = (curve: Curve) => {
  let last = 0;   // the chart needs strictly rising times
  return curve.map((p) => { last = Math.max(last + 1, Math.floor(p.t)); return { time: last as UTCTimestamp, value: p.r }; });
};

/** Out-of-sample cumulative R: tuned choices against the untuned defaults. */
export function TuneCurveChart({ tuned, base }: { tuned: Curve; base: Curve }) {
  const el = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!el.current) return;
    const c = createChart(el.current, CHART_BASE);
    const fmt = { type: "custom" as const, formatter: (v: number) => `${v.toFixed(1)}R` };
    if (base.length) c.addLineSeries({ color: "#5b6a88", lineWidth: 2, lineStyle: 2, priceFormat: fmt, title: "defaults" }).setData(series(base));
    if (tuned.length) c.addLineSeries({ color: COLORS.accent, lineWidth: 2, priceFormat: fmt, title: "tuned" }).setData(series(tuned));
    c.timeScale().fitContent();
    return () => c.remove();
  }, [tuned, base]);
  return <div ref={el} style={{ height: 240 }} />;
}
