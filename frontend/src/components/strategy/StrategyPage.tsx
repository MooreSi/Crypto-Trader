import { useEffect, useState } from "react";
import clsx from "clsx";
import { Copy, Layers, Plus, Trash2, Zap } from "lucide-react";
import { api } from "@/api/client";
import type { Strategy, StrategyList } from "@/api/types";
import { Badge, Button, Card, ErrorLine, Notice, confirmAction } from "@/components/shared/ui";
import { exitPlan } from "./strategyFields";
import { StrategyEditor, type StrategyDraft } from "./StrategyEditor";

type Editing = { id: string | null; draft: StrategyDraft };

export function StrategyPage() {
  const [list, setList] = useState<StrategyList | null>(null);
  const [editing, setEditing] = useState<Editing | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  const load = async (select?: string | null) => {
    try {
      const l = await api.get<StrategyList>("/api/strategies");
      setList(l);
      const pick = l.items.find((s) => s.id === (select ?? l.active)) ?? l.items[0];
      setEditing(pick ? { id: pick.id, draft: { name: pick.name, notes: pick.notes, params: pick.params } } : null);
      setError("");
    } catch (e) { setError(String(e)); }
  };
  useEffect(() => { void load(); }, []);

  const flash = (msg: string) => { setSaved(msg); window.setTimeout(() => setSaved(""), 2500); };

  const activate = async (s: Strategy) => {
    if (!confirmAction(`Activate "${s.name}"?\n\nIts values replace the Risk settings now. New trades use it, and open trades are managed by its breakeven, lock and trail.`)) return;
    try { await api.post(`/api/strategies/${s.id}/activate`); await load(s.id); flash(`"${s.name}" is active`); }
    catch (e) { setError(String(e)); }
  };

  const remove = async (s: Strategy) => {
    if (!confirmAction(`Delete "${s.name}"?`)) return;
    try { await api.del(`/api/strategies/${s.id}`); await load(); } catch (e) { setError(String(e)); }
  };

  const save = async (d: StrategyDraft) => {
    const id = editing?.id;
    const out = id ? await api.put<Strategy>(`/api/strategies/${id}`, d) : await api.post<Strategy>("/api/strategies", d);
    await load(out.id ?? id);
    flash(id && id === list?.active ? "Saved and applied" : "Saved");
  };

  if (!list) return <ErrorLine error={error || "Loading..."} />;
  const active = list.items.find((s) => s.id === list.active);

  return (
    <div className="space-y-5">
      <ErrorLine error={error} />
      {active && list.drift.length > 0 && (
        <Notice tone="warn">
          The Risk page has changed {list.drift.join(", ")} since "{active.name}" was applied.{" "}
          <button type="button" className="underline" onClick={() => activate(active)}>Re-apply the strategy</button>
        </Notice>
      )}
      {saved && <Notice tone="profit">{saved}</Notice>}
      <div className="grid gap-5 xl:grid-cols-[340px_1fr]">
        <Card title="Strategies" icon={<Layers className="h-4 w-4" />}
              right={<Button size="sm" onClick={() => setEditing({ id: null, draft: { name: "", notes: "", params: list.current } })}>
                <Plus className="h-3.5 w-3.5" />New</Button>}>
          <ul className="space-y-2">
            {list.items.map((s) => {
              const isActive = s.id === list.active;
              return (
                <li key={s.id} className={clsx("rounded-lg border p-3 transition",
                  editing?.id === s.id ? "border-accent/60 bg-panel-2" : "border-line/70 hover:border-line-2")}>
                  <button type="button" className="block w-full text-left"
                          onClick={() => setEditing({ id: s.id, draft: { name: s.name, notes: s.notes, params: s.params } })}>
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{s.name}</span>
                      {isActive && <Badge tone="profit" dot>active</Badge>}
                    </div>
                    <div className="mt-1 text-xs text-muted">{exitPlan(s.params)}</div>
                    <div className="num mt-1 text-xs text-dim">
                      {String(s.params.risk_per_trade_pct)}% risk, {String(s.params.max_leverage)}x max
                    </div>
                  </button>
                  <div className="mt-2 flex gap-1.5">
                    {!isActive && <Button size="sm" tone="accent" onClick={() => activate(s)}><Zap className="h-3.5 w-3.5" />Activate</Button>}
                    <Button size="sm" tone="ghost" title="Copy" onClick={() =>
                      setEditing({ id: null, draft: { name: `${s.name} (copy)`.slice(0, 60), notes: s.notes, params: s.params } })}>
                      <Copy className="h-3.5 w-3.5" />Copy
                    </Button>
                    {!isActive && <Button size="sm" tone="ghost" title="Delete" onClick={() => remove(s)}><Trash2 className="h-3.5 w-3.5" />Delete</Button>}
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-dim">Activating writes the strategy's values into the Risk settings. The master switch, margin mode and watchlist stay on their own pages.</p>
        </Card>
        {editing ? (
          <StrategyEditor key={`${editing.id ?? "new"}-${editing.draft.name}`} initial={editing.draft} isNew={!editing.id}
                          isActive={editing.id === list.active} onSave={save} onCancel={() => load(editing.id)} />
        ) : <Card><p className="text-sm text-muted">Pick a strategy or create one.</p></Card>}
      </div>
    </div>
  );
}
