import { useEffect, useState } from "react";
import clsx from "clsx";
import { api } from "@/api/client";
import type { SystemStatus } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { Header } from "@/components/shell/Header";
import { DashboardPage } from "@/components/dashboard/DashboardPage";
import { MarketsPage } from "@/components/markets/MarketsPage";
import { EnginesPage } from "@/components/engines/EnginesPage";
import { TradesPage } from "@/components/trades/TradesPage";
import { RiskPage } from "@/components/risk/RiskPage";
import { EventsPage } from "@/components/events/EventsPage";
import { SettingsPage } from "@/components/settings/SettingsPage";
import { AboutPage } from "@/components/about/AboutPage";

const TABS = ["Dashboard", "Markets", "Engines", "Trades", "Risk", "Events", "Settings", "About"] as const;
type Tab = (typeof TABS)[number];

function initialTab(): Tab {
  const h = decodeURIComponent(window.location.hash.slice(1));
  return (TABS as readonly string[]).includes(h) ? (h as Tab) : "Dashboard";
}

export default function App() {
  const [tab, setTab] = useState<Tab>(initialTab);
  const { data: status, reload } = usePoll(() => api.get<SystemStatus>("/api/system/status"), 5000);
  const go = (t: Tab) => { setTab(t); window.location.hash = t; };

  // Back/forward and pasted links change only the hash; follow them.
  useEffect(() => {
    const onHash = () => setTab(initialTab());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div className="flex min-h-full flex-col">
      <Header status={status} reload={reload} />
      <nav className="flex gap-1 overflow-x-auto border-b border-line bg-panel px-4">
        {TABS.map((t) => (
          <button key={t} type="button" onClick={() => go(t)}
                  className={clsx("whitespace-nowrap border-b-2 px-3 py-2 text-sm",
                    t === tab ? "border-accent text-text" : "border-transparent text-muted hover:text-text")}>
            {t}
          </button>
        ))}
      </nav>
      <main className="mx-auto w-full max-w-7xl flex-1 p-4">
        {tab === "Dashboard" && <DashboardPage status={status} />}
        {tab === "Markets" && <MarketsPage />}
        {tab === "Engines" && <EnginesPage />}
        {tab === "Trades" && <TradesPage />}
        {tab === "Risk" && <RiskPage />}
        {tab === "Events" && <EventsPage />}
        {tab === "Settings" && <SettingsPage />}
        {tab === "About" && <AboutPage />}
      </main>
    </div>
  );
}
