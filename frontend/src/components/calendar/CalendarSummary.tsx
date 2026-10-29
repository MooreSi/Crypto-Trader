import clsx from "clsx";
import { pnlClass } from "@/lib/format";
import type { DayCell } from "./calendarGrid";
import { money, streaks, weekdayTotals } from "./calendarStats";

/** Under the month: its day streaks and its totals by weekday. */
export function CalendarSummary({ cells }: { cells: DayCell[] }) {
  const s = streaks(cells);
  const byDay = weekdayTotals(cells);
  const stat = (label: string, value: string, testId: string, tone?: string) => (
    <div data-testid={testId} className="rounded-lg border border-line bg-panel-2/50 px-2.5 py-1.5">
      <div className="text-[10px] uppercase tracking-wider text-dim">{label}</div>
      <div className={clsx("num text-[13px] font-semibold text-text", tone)}>{value}</div>
    </div>
  );
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
        {stat("Green / red days", `${s.greenDays} / ${s.redDays}`, "streak-days")}
        {stat("Current streak", s.current ? `${s.current.length} ${s.current.kind}` : "-", "streak-current",
          s.current ? (s.current.kind === "green" ? "text-profit" : "text-loss") : undefined)}
        {stat("Longest green", String(s.longestGreen), "streak-longest-green", "text-profit")}
        {stat("Longest red", String(s.longestRed), "streak-longest-red", "text-loss")}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {byDay.map((d) => (
          <div key={d.label} data-testid={`weekday-${d.label}`}
            className="rounded-lg border border-line bg-panel-2/50 px-1 py-1.5 text-center">
            <div className="text-[10px] uppercase tracking-wider text-dim">{d.label}</div>
            <div className={clsx("num text-[11px] font-semibold", d.n ? pnlClass(d.pnl) : "text-dim")}>
              {d.n ? money(d.pnl) : "-"}
            </div>
            <div className="num text-[10px] text-dim">{d.n ? `${d.wins} / ${d.n}` : ""}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
