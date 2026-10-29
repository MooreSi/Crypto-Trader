import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import type { Account, CalendarEvent, CalendarTrade, JournalDraft, JournalEntry } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { dayGains, dayOpenBalances, monthGrid, periodGain, type DayCell } from "./calendarGrid";
import type { CellMetric, GoalSettings } from "./calendarStats";

/** Two years: enough for the year view and the month before it, one read. */
export const CALENDAR_DAYS = 730;

const METRIC_KEY = "calendar/metric";
const METRICS: CellMetric[] = ["usd", "pct", "r"];

// Per-viewer convenience, so browser storage, not a setting. Either call can
// throw (private window, blocked storage); the calendar still works.
function storedMetric(): CellMetric {
  try {
    const v = localStorage.getItem(METRIC_KEY) as CellMetric | null;
    return v && METRICS.includes(v) ? v : "usd";
  } catch {
    return "usd";
  }
}

export interface Shown { year: number; month: number }

/** The 31st for every month: compared as strings, no real date sorts after it. */
export function monthSpan(s: Shown): { start: string; end: string } {
  const mm = String(s.month).padStart(2, "0");
  return { start: `${s.year}-${mm}-01`, end: `${s.year}-${mm}-31` };
}

/**
 * Everything the Calendar shows. The trades are polled; the balance, the risk
 * settings, the month's events and its journal are read when the page or the
 * month changes, because they change when someone acts, not on a clock.
 */
export function useCalendar() {
  const poll = usePoll(
    () => api.get<{ today: string; rows: CalendarTrade[] }>(`/api/calendar/trades?days=${CALENDAR_DAYS}`),
    15_000);
  const [balance, setBalance] = useState<number | null>(null);
  const [risk, setRisk] = useState<GoalSettings>({});
  const [cursor, setCursor] = useState<Shown | null>(null);
  const [view, setView] = useState<"month" | "year">("month");
  const [metric, setMetricState] = useState<CellMetric>(storedMetric);
  const [open, setOpen] = useState<DayCell | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [journal, setJournal] = useState<JournalEntry[]>([]);

  useEffect(() => {
    let cancelled = false;
    // No balance means no percentages, which is honest: a failed read must not
    // blank the month.
    void api.get<Account>("/api/account")
      .then((a) => !cancelled && setBalance(Number.isFinite(a?.equity) ? a.equity : null))
      .catch(() => undefined);
    // Goal marks only. A failed read marks nothing.
    void api.get<GoalSettings>("/api/risk")
      .then((r) => !cancelled && setRisk(r ?? {}))
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  const rows = poll.data?.rows ?? [];
  const today = poll.data?.today ?? null;
  // Opens on the newest close's month, else today's: early in a month with
  // nothing closed yet, last month is the one worth seeing.
  const newest = rows[0]?.day ?? today;
  const shown: Shown | null = cursor ?? (newest
    ? { year: Number(newest.slice(0, 4)), month: Number(newest.slice(5, 7)) } : null);
  const span = shown ? monthSpan(shown) : null;

  const loadMonth = useCallback(async (s: { start: string; end: string }) => {
    const q = `start=${s.start}&end=${s.end}`;
    const [e, j] = await Promise.all([
      api.get<{ events: CalendarEvent[] }>(`/api/calendar/events?${q}`).catch(() => null),
      api.get<{ entries: JournalEntry[] }>(`/api/calendar/journal?${q}`).catch(() => null),
    ]);
    setEvents(e?.events ?? []);
    setJournal(j?.entries ?? []);
  }, []);

  useEffect(() => {
    if (span) void loadMonth(span);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [span?.start, loadMonth]);

  const grid = useMemo(
    () => (shown ? monthGrid(rows, shown.year, shown.month) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [rows, shown?.year, shown?.month]);
  const gains = useMemo(() => dayGains(rows, balance), [rows, balance]);
  const opens = useMemo(() => dayOpenBalances(rows, balance), [rows, balance]);
  const monthGain = span ? periodGain(rows, balance, span.start, span.end) : null;

  const eventsByDay = useMemo(() => {
    const out = new Map<string, CalendarEvent[]>();
    for (const e of events) out.set(e.day, [...(out.get(e.day) ?? []), e]);
    return out;
  }, [events]);
  const journalByDay = useMemo(() => new Map(journal.map((e) => [e.day, e])), [journal]);

  const setMetric = (m: CellMetric) => {
    setMetricState(m);
    try { localStorage.setItem(METRIC_KEY, m); } catch { /* per-viewer only */ }
  };

  const step = (by: number) => {
    if (!shown) return;
    const m = shown.month + by;
    setCursor({ year: shown.year + (m < 1 ? -1 : m > 12 ? 1 : 0), month: m < 1 ? 12 : m > 12 ? 1 : m });
  };

  const pickMonth = (year: number, month: number) => {
    setCursor({ year, month });
    setView("month");
  };

  /** Saves, then re-reads the month, so what is shown is what was stored. */
  const saveJournal = async (day: string, draft: JournalDraft) => {
    await api.post(`/api/calendar/journal/${day}`, draft);
    if (span) await loadMonth(span);
  };

  return {
    poll, today, shown, grid, rows, balance, gains, opens, monthGain, risk,
    view, setView, metric, setMetric, step, pickMonth,
    open, setOpen, eventsByDay, journalByDay, saveJournal,
  };
}

export type CalendarController = ReturnType<typeof useCalendar>;
