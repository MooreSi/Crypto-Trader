import clsx from "clsx";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { pnlClass } from "@/lib/format";
import { Card, Empty, ErrorLine, Segmented } from "@/components/shared/ui";
import { MonthGridView } from "./MonthGridView";
import { CalendarSummary } from "./CalendarSummary";
import { CalendarYear } from "./CalendarYear";
import { DayDetail } from "./DayDetail";
import { formatGain } from "./calendarGrid";
import { CELL_METRICS, money } from "./calendarStats";
import { useCalendar } from "./useCalendar";

function monthLabel(year: number, month: number): string {
  return new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString("en-GB", {
    month: "long", year: "numeric", timeZone: "UTC",
  });
}

const VIEWS = ["month", "year"] as const;
const nav = "rounded-lg border border-line p-1.5 text-muted transition hover:bg-panel-2 hover:text-text";

/**
 * The trading calendar, ported from FOREX Trader's Analysis calendar: closed
 * trades day by day on the UTC trading day, with each day's net, % of its
 * opening balance or R, win rate, target and loss-limit marks, events and
 * journal; week and month totals; streaks and weekday totals; a year view;
 * and a day dialog with the day's stats and breakdowns.
 */
export function CalendarPage() {
  const c = useCalendar();
  const { poll, grid, shown } = c;
  const label = (v: (typeof VIEWS)[number]) => (v === "month" ? "Month" : "Year");

  let body;
  if (!poll.data) {
    body = <Empty>{poll.error ? "Could not load the calendar" : "Loading"}</Empty>;
  } else if (!grid || !shown) {
    body = <Empty>No closed trades to put on a calendar yet</Empty>;
  } else if (c.view === "year") {
    body = <CalendarYear initialYear={shown.year} rows={c.rows} balance={c.balance} onPick={c.pickMonth} />;
  } else {
    body = (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" aria-label="Previous month" onClick={() => c.step(-1)} className={nav}>
            <ChevronLeft size={14} />
          </button>
          <h3 data-testid="calendar-month" className="min-w-36 text-center text-sm font-semibold">
            {monthLabel(shown.year, shown.month)}
          </h3>
          <button type="button" aria-label="Next month" onClick={() => c.step(1)} className={nav}>
            <ChevronRight size={14} />
          </button>
          <Segmented value={c.metric} options={CELL_METRICS.map((m) => m.key)} onChange={c.setMetric}
            label={(k) => CELL_METRICS.find((m) => m.key === k)!.label} />
          <span data-testid="calendar-total"
            className="num ml-auto rounded-lg border border-line bg-panel-2/50 px-2.5 py-1 text-[11px] text-muted">
            {grid.trades} {grid.trades === 1 ? "trade" : "trades"} ·{" "}
            <span className={clsx("font-semibold", pnlClass(grid.pnl))}>{money(grid.pnl)}</span>
            {c.monthGain != null && (
              <span data-testid="month-gain" className={clsx("ml-1 font-semibold", pnlClass(c.monthGain))}>
                ({formatGain(c.monthGain)})
              </span>
            )}
          </span>
        </div>
        <MonthGridView c={c} grid={grid} />
        <CalendarSummary cells={grid.weeks.flatMap((w) => w.days)} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <ErrorLine error={poll.error} />
      <Card title="Trading calendar" icon={<CalendarDays className="h-4 w-4" />}
        subtitle="Closed trades by UTC trading day, net of fees. Click a day for its detail and journal."
        right={<Segmented value={c.view} options={VIEWS} onChange={c.setView} label={label} />}>
        {body}
      </Card>
      {c.open && (
        <DayDetail
          day={c.open}
          gain={c.gains.get(c.open.date) ?? null}
          dayOpen={c.opens.get(c.open.date) ?? null}
          risk={c.risk}
          events={c.eventsByDay.get(c.open.date) ?? []}
          journal={c.journalByDay.get(c.open.date) ?? null}
          onSaveJournal={c.saveJournal}
          onClose={() => c.setOpen(null)}
        />
      )}
    </div>
  );
}
