import clsx from "clsx";
import { CalendarClock, NotebookPen, ShieldAlert, Target } from "lucide-react";
import { pnlClass } from "@/lib/format";
import { formatGain, periodGain, type DayCell, type MonthGrid, type WeekRow } from "./calendarGrid";
import { cellMetric, formatMetric, goalMarks } from "./calendarStats";
import type { CalendarController } from "./useCalendar";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function winRate(cell: DayCell): number {
  const wins = cell.trades.filter((t) => t.net_pnl > 0).length;
  return cell.trades.length ? Math.round((wins / cell.trades.length) * 100) : 0;
}

/** A week's gain over its days in this month. */
function weekGain(c: CalendarController, week: WeekRow): number | null {
  const own = week.days.filter((d) => d.inMonth);
  return own.length ? periodGain(c.rows, c.balance, own[0]!.date, own[own.length - 1]!.date) : null;
}

/**
 * One day. The figure is the chosen metric; the colour is always the day's
 * money, so switching to R cannot repaint a losing day green. Marks along the
 * top: profit target touched, loss limit touched, events, a journal note.
 */
function DayButton({ cell, c }: { cell: DayCell; c: CalendarController }) {
  const traded = cell.trades.length > 0;
  const gain = c.gains.get(cell.date) ?? null;
  const marks = traded ? goalMarks(cell.trades, c.opens.get(cell.date) ?? null, c.risk)
    : { goal: false, loss: false };
  const events = cell.inMonth ? c.eventsByDay.get(cell.date) ?? [] : [];
  const note = cell.inMonth ? c.journalByDay.get(cell.date) : undefined;
  return (
    <button type="button" data-testid={`day-${cell.date}`} disabled={!cell.inMonth}
      onClick={() => c.setOpen(cell)}
      className={clsx(
        "flex min-h-[5.5rem] flex-col rounded-lg border p-2 text-left transition",
        cell.inMonth ? "border-line bg-panel-2/40" : "border-transparent opacity-30",
        traded && cell.pnl > 0 && "border-profit/40 bg-profit/10",
        traded && cell.pnl < 0 && "border-loss/40 bg-loss/10",
        cell.inMonth && "cursor-pointer hover:brightness-125",
        cell.date === c.today && "ring-2 ring-accent",
      )}>
      <div className="flex items-center gap-1">
        <span className={clsx("num text-[11px] font-semibold", cell.date === c.today ? "text-accent" : "text-muted")}>
          {cell.day}
        </span>
        {marks.goal && <Target size={10} data-testid={`goal-mark-${cell.date}`} className="text-profit"
          aria-label="Daily profit target reached" />}
        {marks.loss && <ShieldAlert size={10} data-testid={`loss-mark-${cell.date}`} className="text-loss"
          aria-label="Daily loss limit reached" />}
        {events.length > 0 && (
          <span data-testid={`news-mark-${cell.date}`} title={events.map((e) => e.title).join("\n")}
            className={clsx("flex", events.some((e) => e.impact === "high") ? "text-loss" : "text-dim")}>
            <CalendarClock size={10} aria-label={`${events.length} events`} />
          </span>
        )}
        {note && <NotebookPen size={10} data-testid={`note-mark-${cell.date}`} className="text-accent"
          aria-label="Journal note" />}
        {traded && <span className="num ml-auto text-[10px] text-dim">{winRate(cell)}%</span>}
      </div>
      {traded && (
        <>
          <span data-testid={`day-metric-${cell.date}`}
            className={clsx("num mt-auto block text-[13px] font-bold", pnlClass(cell.pnl))}>
            {formatMetric(c.metric, cellMetric(cell, c.metric, gain))}
          </span>
          <div className="flex items-baseline gap-1">
            <span className="num text-[10px] text-dim">
              {cell.trades.length} {cell.trades.length === 1 ? "trade" : "trades"}
            </span>
            {gain !== null && c.metric !== "pct" && (
              <span data-testid={`day-gain-${cell.date}`}
                className={clsx("num ml-auto text-[10px] font-semibold", pnlClass(gain))}>
                {formatGain(gain)}
              </span>
            )}
          </div>
        </>
      )}
    </button>
  );
}

/** Eight columns: the week, Monday first (UTC), then its total. */
export function MonthGridView({ c, grid }: { c: CalendarController; grid: MonthGrid }) {
  return (
    <div className="overflow-x-auto">
      <div className="grid min-w-[640px] grid-cols-8 gap-1.5 text-[11px]">
        {[...WEEKDAYS, "Week"].map((d) => (
          <div key={d} className="pb-1 text-center text-[10px] font-semibold uppercase tracking-wider text-dim">{d}</div>
        ))}
        {grid.weeks.map((week, wi) => {
          const wGain = weekGain(c, week);
          return (
            <div key={wi} className="contents">
              {week.days.map((cell) => <DayButton key={cell.date} cell={cell} c={c} />)}
              <div data-testid={`week-total-${wi}`}
                className="flex min-h-[5.5rem] flex-col justify-end rounded-lg border border-line bg-panel-3/60 p-2">
                <span className={clsx("num block text-[13px] font-bold", pnlClass(week.pnl))}>
                  {week.trades ? formatMetric("usd", week.pnl) : "-"}
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="num text-[10px] text-dim">
                    {week.trades ? `${week.trades} ${week.trades === 1 ? "trade" : "trades"}` : "quiet"}
                  </span>
                  {wGain != null && (
                    <span data-testid={`week-gain-${wi}`}
                      className={clsx("num ml-auto text-[10px] font-semibold", pnlClass(wGain))}>
                      {formatGain(wGain)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
