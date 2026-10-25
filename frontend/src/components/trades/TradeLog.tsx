import { Fragment } from "react";
import { X } from "lucide-react";
import { api } from "@/api/client";
import type { TradeEvent } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { time } from "@/lib/format";
import { Badge, Button } from "@/components/shared/ui";

const TONE: Record<string, "profit" | "loss" | "warn" | "accent" | "muted"> = {
  opened: "accent", partial: "profit", stop_moved: "warn", closed: "muted", reconciled: "muted",
};

function show(v: unknown): string {
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toPrecision(6);
  if (v === null || v === undefined) return "-";
  return typeof v === "object" ? JSON.stringify(v) : String(v);
}

/** Every recorded change of one trade, as a side drawer. */
export function TradeLog({ id, onClose }: { id: number; onClose: () => void }) {
  const { data } = usePoll(() => api.get<TradeEvent[]>(`/api/trades/${id}/events`), 10000, [id]);
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <aside className="panel fade-up h-full w-full max-w-lg overflow-y-auto rounded-none p-5" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold">Trade #{id}: every change</h2>
          <Button tone="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" />Close</Button>
        </div>
        <ol className="relative space-y-3 border-l border-line-2 pl-5">
          {data?.map((e, i) => (
            <li key={i} className="relative">
              <span className="grad-fill absolute top-1.5 -left-[25px] h-2.5 w-2.5 rounded-full ring-4 ring-panel" />
              <div className="flex items-center justify-between"><Badge tone={TONE[e.kind] ?? "muted"}>{e.kind.replace("_", " ")}</Badge><span className="text-xs text-muted">{time(e.ts)}</span></div>
              <dl className="num mt-1.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
                {Object.entries(e.detail).filter(([k]) => k !== "gates").map(([k, v]) => (
                  <Fragment key={k}><dt className="text-dim">{k}</dt><dd className="truncate text-muted" title={show(v)}>{show(v)}</dd></Fragment>
                ))}
              </dl>
            </li>
          ))}
        </ol>
      </aside>
    </div>
  );
}
