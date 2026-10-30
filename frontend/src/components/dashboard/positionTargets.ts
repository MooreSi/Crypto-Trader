import type { Position, Trade } from "@/api/types";

/**
 * The exchange's mark, recovered from its own unrealised P&L:
 * upnl = (mark - entry) * signed size. Signed size is negative for a short.
 */
export function markPrice(p: Position): number | null {
  if (!p.size) return null;
  return p.entry_price + p.unrealised_pnl / p.size;
}

export interface Targets {
  nextTpIndex: number;
  nextTp: number | null;
  /** Price move from the mark to the next TP, % of the mark; negative means price must fall. */
  toTpPct: number | null;
  toStopPct: number;
  /** P&L of the whole open size if price reaches that level, before fees. */
  pnlAtTp: number | null;
  pnlAtStop: number;
  /** Where the mark sits in R, measured from the initial stop. */
  rNow: number;
}

/** Display only: how far the open position is from its next TP and its stop. */
export function targets(t: Trade, mark: number | null, signedSize: number): Targets | null {
  if (mark === null || mark <= 0) return null;
  const next = t.tp_hit < t.take_profits.length ? t.take_profits[t.tp_hit] : null;
  const risk = Math.abs(t.entry_price - t.initial_stop);
  const move = t.direction === "long" ? mark - t.entry_price : t.entry_price - mark;
  return {
    nextTpIndex: t.tp_hit,
    nextTp: next,
    toTpPct: next === null ? null : (next - mark) / mark * 100,
    toStopPct: (t.stop_loss - mark) / mark * 100,
    pnlAtTp: next === null ? null : (next - t.entry_price) * signedSize,
    pnlAtStop: (t.stop_loss - t.entry_price) * signedSize,
    rNow: risk > 0 ? move / risk : 0,
  };
}
