import { useEffect } from "react";
import clsx from "clsx";
import { X } from "lucide-react";
import type { CalendarEvent, JournalDraft, JournalEntry } from "@/api/types";
import { pnlClass } from "@/lib/format";
import { Badge, Button, Side } from "@/components/shared/ui";
import { formatGain, type DayCell } from "./calendarGrid";
import { money, type GoalSettings } from "./calendarStats";
import { DayJournal } from "./DayJournal";
import { DayBreakdown, DayStats } from "./DayStats";

const utcTime = (ts: number) => new Date(ts * 1000).toISOString().slice(11, 16);

/**
 * One day, opened from the calendar: its numbers, its realised curve, the
 * engine, coin and session breakdowns, the events that fell on it, every
 * trade, and the day's journal. Times are UTC, the trading day's clock.
 */
export function DayDetail({ day, gain, dayOpen, risk, events, journal, onSaveJournal, onClose }: {
  day: DayCell; gain: number | null; dayOpen: number | null; risk: GoalSettings;
  events: CalendarEvent[]; journal: JournalEntry | null;
  onSaveJournal: (day: string, draft: JournalDraft) => Promise<void>; onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const traded = day.trades.length > 0;
  const wins = day.trades.filter((t) => t.net_pnl > 0).length;

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-black/50 p-4 backdrop-blur-sm sm:p-8"
      onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={`${day.date} detail`}
        className="panel fade-up w-full max-w-3xl space-y-4 rounded-xl p-5 text-xs" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">
              {day.date} <span className={clsx("num", pnlClass(day.pnl))}>{traded ? money(day.pnl) : ""}</span>
            </h2>
            <p className="mt-0.5 text-[11px] text-muted">
              {traded
                ? `${day.trades.length} ${day.trades.length === 1 ? "trade" : "trades"} · ${Math.round((wins / day.trades.length) * 100)}% win rate`
                : "No trades closed this day"}
              {gain != null && (
                <> · <span data-testid="day-detail-gain" className={clsx("num font-semibold", pnlClass(gain))}>
                  {formatGain(gain)}</span> of the day's opening balance</>
              )}
            </p>
          </div>
          <Button tone="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" />Close</Button>
        </div>

        {traded && <DayStats trades={day.trades} dayOpen={dayOpen} risk={risk} />}
        {traded && <DayBreakdown trades={day.trades} />}

        {events.length > 0 && (
          <section className="space-y-1" data-testid="day-events">
            <p className="text-[10px] uppercase tracking-wider text-dim">Events (UTC)</p>
            <ul className="space-y-0.5">
              {events.map((e) => (
                <li key={e.uid} className="flex items-center gap-2 rounded px-1.5 py-1 odd:bg-panel-2/40">
                  <span className="num text-dim">{utcTime(e.ts)}</span>
                  <span className="truncate text-muted">{e.title}</span>
                  {e.coins && <span className="text-dim">{e.coins}</span>}
                  <span className={clsx("ml-auto shrink-0 text-[10px] uppercase",
                    e.impact === "high" ? "text-loss" : e.impact === "medium" ? "text-warn" : "text-dim")}>
                    {e.impact}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {traded && (
          <section className="space-y-1">
            <p className="text-[10px] uppercase tracking-wider text-dim">Trades (closed, UTC)</p>
            <ul className="max-h-60 space-y-0.5 overflow-auto">
              {day.trades.map((t) => (
                <li key={t.id} data-testid={`trade-${t.id}`}
                  className="flex items-center gap-2 rounded px-1.5 py-1 odd:bg-panel-2/40">
                  <span className="num text-dim">{utcTime(t.closed_at)}</span>
                  <span className="font-semibold">{t.coin}</span>
                  <Side direction={t.direction} />
                  <Badge>{t.engine.replace("_", " ")}</Badge>
                  <span className="truncate text-dim">{t.close_reason ?? "-"}</span>
                  <span className="num ml-auto shrink-0 text-dim">{t.r == null ? "" : `${t.r > 0 ? "+" : ""}${t.r.toFixed(2)}R`}</span>
                  <span className={clsx("num w-20 shrink-0 text-right", pnlClass(t.net_pnl))}>{money(t.net_pnl)}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <DayJournal day={day.date} entry={journal} onSave={onSaveJournal} />
      </div>
    </div>
  );
}
