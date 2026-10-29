import { useMemo, useState } from "react";
import clsx from "clsx";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { CalendarTrade } from "@/api/types";
import { pnlClass } from "@/lib/format";
import { formatGain, monthGrid, periodGain } from "./calendarGrid";
import { money } from "./calendarStats";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * A year at a glance: twelve small months, each day shaded by its result
 * relative to the year's biggest day, with each month's money and return.
 * Clicking a month opens it. Drawn from the same two-year read as the month
 * view; older than that shows as quiet.
 */
export function CalendarYear({ initialYear, rows, balance, onPick }: {
  initialYear: number; rows: CalendarTrade[]; balance: number | null;
  onPick: (year: number, month: number) => void;
}) {
  const [year, setYear] = useState(initialYear);
  const months = useMemo(() => MONTHS.map((_, i) => monthGrid(rows, year, i + 1)), [rows, year]);
  const biggest = Math.max(1, ...months.flatMap((m) =>
    m.weeks.flatMap((w) => w.days.filter((d) => d.inMonth).map((d) => Math.abs(d.pnl)))));
  const total = months.reduce((s, m) => s + m.pnl, 0);
  const yearGain = periodGain(rows, balance, `${year}-01-01`, `${year}-12-31`);
  const nav = "rounded-lg border border-line p-1.5 text-muted transition hover:bg-panel-2 hover:text-text";

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1">
        <button type="button" aria-label="Previous year" onClick={() => setYear(year - 1)} className={nav}>
          <ChevronLeft size={14} />
        </button>
        <h3 data-testid="calendar-year" className="min-w-20 px-2 text-center text-sm font-semibold">{year}</h3>
        <button type="button" aria-label="Next year" onClick={() => setYear(year + 1)} className={nav}>
          <ChevronRight size={14} />
        </button>
        <span data-testid="year-total" className="num ml-auto text-xs text-muted">
          <span className={clsx("font-semibold", pnlClass(total))}>{money(total)}</span>
          {yearGain != null && <span className={clsx("ml-1 font-semibold", pnlClass(yearGain))}>({formatGain(yearGain)})</span>}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {months.map((m, i) => {
          const mm = String(i + 1).padStart(2, "0");
          const gain = periodGain(rows, balance, `${year}-${mm}-01`, `${year}-${mm}-31`);
          return (
            <button key={i} type="button" data-testid={`year-month-${i + 1}`} onClick={() => onPick(year, i + 1)}
              className="rounded-lg border border-line bg-panel-2/40 p-2 text-left transition hover:bg-panel-2">
              <div className="mb-1 flex items-baseline gap-1 text-[11px]">
                <span className="font-semibold text-muted">{MONTHS[i]}</span>
                <span className={clsx("num ml-auto font-semibold", m.trades ? pnlClass(m.pnl) : "text-dim")}>
                  {m.trades ? money(m.pnl) : "-"}
                </span>
              </div>
              <div className="grid grid-cols-7 gap-0.5">
                {m.weeks.flatMap((w) => w.days).map((d) => (
                  <span key={d.date}
                    className={clsx("aspect-square rounded-[2px]",
                      !d.inMonth ? "bg-transparent" : !d.trades.length ? "bg-panel-3"
                        : d.pnl >= 0 ? "bg-profit" : "bg-loss")}
                    style={d.inMonth && d.trades.length
                      ? { opacity: 0.25 + 0.75 * Math.min(1, Math.abs(d.pnl) / biggest) } : undefined} />
                ))}
              </div>
              <div data-testid={`year-month-gain-${i + 1}`}
                className={clsx("num mt-1 text-[10px]", gain != null ? pnlClass(gain) : "text-dim")}>
                {gain != null ? formatGain(gain) : m.trades ? "" : "quiet"}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
