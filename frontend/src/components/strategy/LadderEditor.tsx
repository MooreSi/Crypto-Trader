import clsx from "clsx";
import { Plus, X } from "lucide-react";
import { Button, inputCls } from "@/components/shared/ui";

/** Rungs as typed: [R, share %] strings, so a cleared box is not zero. */
export type LadderDraft = [string, string][];

export const toDraft = (ladder: number[][]): LadderDraft =>
  ladder.map(([r, f]) => [String(r), String(Math.round(f * 1000) / 10)]);

export const fromDraft = (d: LadderDraft): number[][] | null => {
  const rows = d.map(([r, p]) => [Number(r), Number(p) / 100]);
  return rows.every(([r, f]) => r > 0 && f > 0 && f <= 1 && Number.isFinite(r) && Number.isFinite(f)) && rows.length
    ? rows : null;
};

export function LadderEditor({ value, onChange }: { value: LadderDraft; onChange: (v: LadderDraft) => void }) {
  const total = value.reduce((s, [, p]) => s + (Number(p) || 0), 0);
  const runner = 100 - total;
  const set = (i: number, j: 0 | 1, v: string) =>
    onChange(value.map((row, k) => (k === i ? (j === 0 ? [v, row[1]] : [row[0], v]) : row)) as LadderDraft);
  return (
    <div className="space-y-2">
      {value.map(([r, p], i) => (
        <div key={i} className="num flex items-center gap-2 text-sm">
          <span className="w-9 font-semibold text-accent">TP{i + 1}</span>
          <input aria-label={`TP${i + 1} R`} type="number" step={0.25} value={r} onChange={(e) => set(i, 0, e.target.value)}
                 className={clsx(inputCls, "w-20 text-right")} />
          <span className="text-muted">R, close</span>
          <input aria-label={`TP${i + 1} share %`} type="number" step={5} value={p} onChange={(e) => set(i, 1, e.target.value)}
                 className={clsx(inputCls, "w-20 text-right")} />
          <span className="text-muted">%</span>
          <button type="button" aria-label={`remove TP${i + 1}`} onClick={() => onChange(value.filter((_, k) => k !== i))}
                  className="ml-auto rounded p-1 text-dim hover:bg-panel-2 hover:text-loss" disabled={value.length === 1}>
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
      <div className="flex items-center justify-between pt-1">
        <Button size="sm" tone="ghost" onClick={() => onChange([...value, ["", ""]])} disabled={value.length >= 8}>
          <Plus className="h-3.5 w-3.5" />Add rung
        </Button>
        <span className={clsx("text-xs", runner < -0.01 ? "text-loss" : "text-muted")}>
          {runner < -0.01 ? `Shares add up to ${total.toFixed(0)}%: at most 100%`
            : runner > 0.01 ? `${runner.toFixed(0)}% runner: no TP, exits on the stop or trail` : "No runner"}
        </span>
      </div>
      <p className="text-xs text-dim">A runner or rung worth under $11.20 is closed with the rung before it (Hyperliquid's $10 minimum).</p>
    </div>
  );
}
