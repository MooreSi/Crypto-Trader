import type { DeepPartial, ChartOptions } from "lightweight-charts";

/** One look for every chart: transparent, hairline grid, the theme's muted text. */
export const CHART_BASE: DeepPartial<ChartOptions> = {
  autoSize: true,
  layout: { background: { color: "transparent" }, textColor: "#8494b2", fontSize: 11,
    fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif" },
  grid: { vertLines: { color: "rgba(31,42,68,0.45)" }, horzLines: { color: "rgba(31,42,68,0.45)" } },
  rightPriceScale: { borderColor: "#1f2a44" },
  timeScale: { borderColor: "#1f2a44", timeVisible: true },
  crosshair: { vertLine: { color: "#2a3858", labelBackgroundColor: "#141d33" },
    horzLine: { color: "#2a3858", labelBackgroundColor: "#141d33" } },
};

export const COLORS = { accent: "#22d3ee", accent2: "#818cf8", profit: "#10b981", loss: "#f43f5e" };
