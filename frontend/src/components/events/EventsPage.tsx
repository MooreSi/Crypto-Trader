import { useState } from "react";
import { api } from "@/api/client";
import type { CalendarEvent } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { time } from "@/lib/format";
import { Badge, Button, Card, ErrorLine, Table } from "@/components/shared/ui";

const KINDS = ["token_unlock", "listing", "upgrade", "maintenance", "other"];

export function EventsPage() {
  const { data, error, reload } = usePoll(() => api.get<CalendarEvent[]>("/api/events?days=14"), 60000);
  const [form, setForm] = useState({ when: "", title: "", impact: "high", kind: "token_unlock", coins: "" });
  const [msg, setMsg] = useState("");

  const add = async () => {
    try {
      const ts = new Date(form.when).getTime() / 1000;
      if (!ts) throw new Error("pick a date and time");
      await api.post("/api/events", { ts, title: form.title, impact: form.impact, kind: form.kind,
        coins: form.coins.split(",").map((c) => c.trim()).filter(Boolean) });
      setForm({ ...form, title: "", coins: "" }); setMsg("");
      reload();
    } catch (e) { setMsg(String(e)); }
  };
  const remove = async (id: number) => { await api.del(`/api/events/${id}`); reload(); };
  const refresh = async () => { await api.post("/api/events/refresh"); reload(); };

  return (
    <div className="space-y-4">
      <ErrorLine error={error || msg} />
      <Card title="Add your own event" right={<Button onClick={refresh}>Refresh feeds</Button>}>
        <p className="mb-3 text-xs text-muted">
          Token unlocks, listings, network upgrades, exchange maintenance. With coins, a high-impact event blocks new
          entries on those coins only; without, on every coin. Times are your local time.
        </p>
        <div className="grid gap-2 md:grid-cols-6">
          <input type="datetime-local" value={form.when} onChange={(e) => setForm({ ...form, when: e.target.value })}
                 className="rounded-md border border-line bg-panel-2 px-2 py-1 md:col-span-2" />
          <input placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
                 className="rounded-md border border-line bg-panel-2 px-2 py-1 md:col-span-2" />
          <select value={form.impact} onChange={(e) => setForm({ ...form, impact: e.target.value })}
                  className="rounded-md border border-line bg-panel-2 px-2 py-1">
            <option value="high">high</option><option value="medium">medium</option><option value="low">low</option>
          </select>
          <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}
                  className="rounded-md border border-line bg-panel-2 px-2 py-1">
            {KINDS.map((k) => <option key={k} value={k}>{k.replace("_", " ")}</option>)}
          </select>
          <input placeholder="Coins, e.g. ARB, OP (blank = all)" value={form.coins} onChange={(e) => setForm({ ...form, coins: e.target.value })}
                 className="rounded-md border border-line bg-panel-2 px-2 py-1 md:col-span-4" />
          <div className="md:col-span-2"><Button tone="accent" onClick={add}>Add event</Button></div>
        </div>
      </Card>
      <Card title="Next 14 days">
        <Table head={["When", "Impact", "Event", "Kind", "Coins", "Source", ""]}
               empty={data && data.length === 0 ? "Nothing scheduled" : undefined}>
          {data?.map((e) => (
            <tr key={e.id} className={e.ts < Date.now() / 1000 ? "opacity-50" : ""}>
              <td className="whitespace-nowrap px-2 py-1.5">{time(e.ts)}</td>
              <td className="px-2 py-1.5"><Badge tone={e.impact === "high" ? "loss" : e.impact === "medium" ? "warn" : "muted"}>{e.impact}</Badge></td>
              <td className="px-2 py-1.5">{e.title}</td>
              <td className="px-2 py-1.5 text-xs">{e.kind.replace("_", " ")}</td>
              <td className="px-2 py-1.5 text-xs">{e.coins || "all"}</td>
              <td className="px-2 py-1.5 text-xs text-muted">{e.source}</td>
              <td className="px-2 py-1.5">{e.source === "user" && <Button onClick={() => remove(e.id)}>Delete</Button>}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
