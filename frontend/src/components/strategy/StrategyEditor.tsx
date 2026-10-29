import { useState } from "react";
import clsx from "clsx";
import { Save, SlidersHorizontal, Target } from "lucide-react";
import { Button, Card, Field, Switch, inputCls } from "@/components/shared/ui";
import { SECTIONS, TOGGLES, exitPlan, type StrategyParams } from "./strategyFields";
import { LadderEditor, fromDraft, toDraft, type LadderDraft } from "./LadderEditor";

export type StrategyDraft = { name: string; notes: string; params: StrategyParams };

/** Edit one strategy. Numbers are kept as typed until save, so a cleared box is refused, not zero. */
export function StrategyEditor({ initial, isNew, isActive, onSave, onCancel }: {
  initial: StrategyDraft; isNew: boolean; isActive: boolean;
  onSave: (d: StrategyDraft) => Promise<void>; onCancel: () => void;
}) {
  const [name, setName] = useState(initial.name);
  const [notes, setNotes] = useState(initial.notes);
  const [nums, setNums] = useState<Record<string, string>>(() =>
    Object.fromEntries(SECTIONS.flatMap((s) => s.fields).map((f) => [f.key, String(initial.params[f.key] ?? "")])));
  const [flags, setFlags] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(TOGGLES.map((t) => [t.key, Boolean(initial.params[t.key])])));
  const [ladder, setLadder] = useState<LadderDraft>(() => toDraft(initial.params.tp_ladder as number[][]));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const parsedLadder = fromDraft(ladder);
  const preview: StrategyParams = {
    ...initial.params, ...Object.fromEntries(Object.entries(nums).map(([k, v]) => [k, Number(v)])),
    tp_ladder: parsedLadder ?? (initial.params.tp_ladder as number[][]),
  };

  const save = async () => {
    const blank = Object.entries(nums).filter(([, v]) => v.trim() === "" || Number.isNaN(Number(v))).map(([k]) => k);
    if (!name.trim()) return setError("Give the strategy a name");
    if (blank.length) return setError(`Enter a number for ${blank.join(", ")}`);
    if (!parsedLadder) return setError("Each TP needs an R above 0 and a share between 0 and 100%");
    setBusy(true);
    try {
      await onSave({ name, notes, params: { ...Object.fromEntries(Object.entries(nums).map(([k, v]) => [k, Number(v)])),
        ...flags, tp_ladder: parsedLadder } });
      setError("");
    } catch (e) { setError(String(e instanceof Error ? e.message : e)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-5">
      <Card title={isNew ? "New strategy" : "Edit strategy"} icon={<SlidersHorizontal className="h-4 w-4" />}
            subtitle={isActive ? "Active: saving applies it at once" : "Saving does not apply it; Activate does"}>
        <div className="grid gap-3 sm:grid-cols-[1fr_2fr]">
          <label className="block text-sm">Name
            <input aria-label="Strategy name" value={name} maxLength={60} onChange={(e) => setName(e.target.value)}
                   className={clsx(inputCls, "mt-1 w-full")} />
          </label>
          <label className="block text-sm">Notes
            <input aria-label="Strategy notes" value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)}
                   className={clsx(inputCls, "mt-1 w-full")} />
          </label>
        </div>
        <p className="mt-3 text-xs text-muted"><span className="text-text">Exit plan:</span> {exitPlan(preview)}</p>
      </Card>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Take-profit ladder" icon={<Target className="h-4 w-4" />}>
          <LadderEditor value={ladder} onChange={setLadder} />
        </Card>
        {SECTIONS.map((sec) => (
          <Card key={sec.title} title={sec.title} icon={<SlidersHorizontal className="h-4 w-4" />}>
            <div className="space-y-3">
              {sec.fields.map((f) => (
                <Field key={f.key} label={f.label} help={f.help}>
                  <input type="number" step={f.step ?? 1} value={nums[f.key]} aria-label={f.label}
                         onChange={(e) => setNums({ ...nums, [f.key]: e.target.value })}
                         className={clsx(inputCls, "num w-28 text-right")} />
                </Field>
              ))}
              {sec.title === "Entry filters" && TOGGLES.map((t) => (
                <div key={t.key} className="flex items-center justify-between text-sm">
                  <span>{t.label}</span>
                  <Switch label={t.key} on={flags[t.key]} onChange={(v) => setFlags({ ...flags, [t.key]: v })} />
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
      <div className="sticky bottom-4 z-10 flex flex-wrap items-center gap-3 rounded-xl border border-accent/40 bg-panel/90 px-4 py-3 shadow-lg backdrop-blur">
        <Button tone="accent" disabled={busy} onClick={save}><Save className="h-4 w-4" />Save strategy</Button>
        <Button tone="ghost" onClick={onCancel}>Cancel</Button>
        {error && <span className="text-sm text-loss">{error}</span>}
      </div>
    </div>
  );
}
