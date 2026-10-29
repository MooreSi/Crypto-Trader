import clsx from "clsx";
import {
  Activity, BarChart3, CalendarClock, CalendarDays, Cpu, FlaskConical, Info, Layers, LayoutDashboard, ListOrdered,
  Settings, ShieldCheck, type LucideIcon,
} from "lucide-react";
import type { SystemStatus } from "@/api/types";
import { duration } from "@/lib/format";

export const TABS = ["Dashboard", "Markets", "Engines", "Lab", "Trades", "Calendar", "Strategy", "Risk", "Events", "Settings", "About"] as const;
export type Tab = (typeof TABS)[number];

const ICONS: Record<Tab, LucideIcon> = {
  Dashboard: LayoutDashboard, Markets: BarChart3, Engines: Cpu, Lab: FlaskConical, Trades: ListOrdered, Calendar: CalendarDays,
  Strategy: Layers, Risk: ShieldCheck, Events: CalendarClock, Settings, About: Info,
};

const LABELS: Partial<Record<Tab, string>> = { Lab: "Strategy Lab" };
export const tabLabel = (t: Tab) => LABELS[t] ?? t;

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="grad-fill grid h-8 w-8 place-items-center rounded-lg shadow-[0_6px_20px_-6px_rgba(34,211,238,0.6)]">
        <Activity className="h-4.5 w-4.5 text-bg" strokeWidth={2.5} />
      </div>
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-tight">Crypto <span className="grad-text">Trader</span></div>
        <div className="text-[10px] uppercase tracking-[0.18em] text-dim">Hyperliquid perps</div>
      </div>
    </div>
  );
}

export function Sidebar({ tab, go, status }: { tab: Tab; go: (t: Tab) => void; status: SystemStatus | null }) {
  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line/70 bg-bg-2/70 backdrop-blur lg:flex">
      <div className="px-5 py-5"><Logo /></div>
      <nav className="flex-1 space-y-0.5 px-3">
        {TABS.map((t) => {
          const Icon = ICONS[t];
          const active = t === tab;
          return (
            <button key={t} type="button" onClick={() => go(t)}
                    className={clsx("group relative flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
                      active ? "bg-panel-2 text-text" : "text-muted hover:bg-panel/80 hover:text-text")}>
              {active && <span className="grad-fill absolute top-1.5 bottom-1.5 left-0 w-0.5 rounded-full" />}
              <Icon className={clsx("h-4 w-4", active ? "text-accent" : "text-dim group-hover:text-muted")} />
              {tabLabel(t)}
              {t === "Lab" && <span className="ml-auto rounded bg-accent-2/15 px-1.5 text-[10px] font-semibold text-accent-2">NEW</span>}
            </button>
          );
        })}
      </nav>
      <div className="m-3 rounded-xl border border-line/70 bg-panel/70 p-3 text-xs">
        <div className="flex items-center justify-between text-muted">
          <span>Engine loop</span>
          <span className={clsx("flex items-center gap-1.5", status?.paused ? "text-warn" : "text-profit")}>
            <span className="live-dot h-1.5 w-1.5 rounded-full bg-current" />{status?.paused ? "paused" : "running"}
          </span>
        </div>
        <div className="mt-1.5 flex items-center justify-between text-muted">
          <span>Uptime</span><span className="num text-text">{duration(status?.uptime_s)}</span>
        </div>
        <div className="mt-1.5 flex items-center justify-between text-muted">
          <span>Open positions</span><span className="num text-text">{status?.open_positions ?? "-"}</span>
        </div>
      </div>
    </aside>
  );
}

/** The same navigation as a scrolling strip, for narrow screens. */
export function MobileNav({ tab, go }: { tab: Tab; go: (t: Tab) => void }) {
  return (
    <nav className="flex gap-1 overflow-x-auto border-b border-line/70 bg-bg-2/80 px-3 py-2 lg:hidden">
      {TABS.map((t) => {
        const Icon = ICONS[t];
        return (
          <button key={t} type="button" onClick={() => go(t)}
                  className={clsx("flex items-center gap-1.5 whitespace-nowrap rounded-lg px-2.5 py-1.5 text-xs",
                    t === tab ? "bg-panel-2 text-text" : "text-muted")}>
            <Icon className={clsx("h-3.5 w-3.5", t === tab && "text-accent")} />{tabLabel(t)}
          </button>
        );
      })}
    </nav>
  );
}
