import { describe, expect, it } from "vitest";
import { markPrice, targets } from "../positionTargets";
import type { Position, Trade } from "@/api/types";

const pos = (o: Partial<Position>): Position => ({
  coin: "UNI", size: 3.1, entry_price: 10, unrealised_pnl: 0, leverage: 1,
  liquidation_price: null, margin_used: 31, direction: "long", ...o,
});

const trade = (o: Partial<Trade>): Trade => ({
  id: 7, engine: "reversal", coin: "UNI", direction: "long", status: "open", network: "mainnet",
  entry_price: 10, size: 2, initial_size: 2, stop_loss: 9, initial_stop: 9, take_profits: [11.5, 13],
  tp_hit: 0, leverage: 1, risk_usd: 2, opened_at: 0, closed_at: null, close_price: null,
  close_reason: null, realised_pnl: 0, fees: 0, net_pnl: 0, r_achieved: null, ...o,
});

describe("markPrice", () => {
  it("recovers the mark from the exchange's unrealised P&L for a long", () => {
    // 2 coins up $1 each -> mark 10.5
    expect(markPrice(pos({ size: 2, entry_price: 10, unrealised_pnl: 1 }))).toBeCloseTo(10.5, 10);
  });
  it("recovers the mark for a short, whose size is negative", () => {
    // short 2 coins, +$1 means price fell 0.5
    expect(markPrice(pos({ size: -2, entry_price: 10, unrealised_pnl: 1, direction: "short" }))).toBeCloseTo(9.5, 10);
  });
  it("is null for a zero-size position", () => {
    expect(markPrice(pos({ size: 0 }))).toBeNull();
  });
});

describe("targets", () => {
  it("long: next TP is TP1, the move needed, and what the position is worth there", () => {
    const t = targets(trade({}), 10.5, 2)!;
    expect(t.nextTpIndex).toBe(0);
    expect(t.nextTp).toBe(11.5);
    expect(t.toTpPct).toBeCloseTo((11.5 - 10.5) / 10.5 * 100, 10);   // +9.52%
    expect(t.toStopPct).toBeCloseTo((9 - 10.5) / 10.5 * 100, 10);    // -14.29%
    expect(t.pnlAtTp).toBeCloseTo((11.5 - 10) * 2, 10);              // +$3.00
    expect(t.pnlAtStop).toBeCloseTo((9 - 10) * 2, 10);               // -$2.00
    expect(t.rNow).toBeCloseTo(0.5, 10);
  });

  it("short: the move to TP is negative and P&L at TP is positive", () => {
    const t = targets(trade({ direction: "short", entry_price: 10, stop_loss: 11, initial_stop: 11,
                              take_profits: [8.5] }), 9.5, -2)!;
    expect(t.toTpPct).toBeCloseTo((8.5 - 9.5) / 9.5 * 100, 10);
    expect(t.pnlAtTp).toBeCloseTo(3, 10);
    expect(t.pnlAtStop).toBeCloseTo(-2, 10);
    expect(t.rNow).toBeCloseTo(0.5, 10);
  });

  it("after TP1 fills, the next target is TP2 and R is measured from the initial stop", () => {
    const t = targets(trade({ tp_hit: 1, stop_loss: 11.5 }), 12, 0.4)!;
    expect(t.nextTpIndex).toBe(1);
    expect(t.nextTp).toBe(13);
    expect(t.pnlAtStop).toBeCloseTo((11.5 - 10) * 0.4, 10);  // stop moved into profit
    expect(t.rNow).toBeCloseTo(2, 10);
  });

  it("with every TP hit there is no next TP", () => {
    const t = targets(trade({ tp_hit: 2 }), 12, 0.4)!;
    expect(t.nextTp).toBeNull();
    expect(t.toTpPct).toBeNull();
    expect(t.pnlAtTp).toBeNull();
  });

  it("is null without a mark price", () => {
    expect(targets(trade({}), null, 2)).toBeNull();
  });
});
