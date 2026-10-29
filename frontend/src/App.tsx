import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { SystemStatus } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { Header } from "@/components/shell/Header";
import { Logo, MobileNav, Sidebar, TABS, tabLabel, type Tab } from "@/components/shell/Sidebar";
import { DashboardPage } from "@/components/dashboard/DashboardPage";
import { MarketsPage } from "@/components/markets/MarketsPage";
import { EnginesPage } from "@/components/engines/EnginesPage";
import { LabPage } from "@/components/lab/LabPage";
import { TradesPage } from "@/components/trades/TradesPage";
import { CalendarPage } from "@/components/calendar/CalendarPage";
import { RiskPage } from "@/components/risk/RiskPage";
import { StrategyPage } from "@/components/strategy/StrategyPage";
import { EventsPage } from "@/components/events/EventsPage";
import { SettingsPage } from "@/components/settings/SettingsPage";
import { AboutPage } from "@/components/about/AboutPage";

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

  useEffect(() => { document.title = `${tabLabel(tab)} - Crypto Trader`; }, [tab]);

  return (
    <div className="flex min-h-full">
      <Sidebar tab={tab} go={go} status={status} />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center border-b border-line/70 bg-bg-2/80 px-4 py-3 lg:hidden"><Logo /></div>
        <MobileNav tab={tab} go={go} />
        <Header status={status} reload={reload} title={tabLabel(tab)} />
        <main key={tab} className="mx-auto w-full max-w-[1400px] flex-1 p-4 sm:p-6">
          {tab === "Dashboard" && <DashboardPage status={status} go={go} />}
          {tab === "Markets" && <MarketsPage />}
          {tab === "Engines" && <EnginesPage />}
          {tab === "Lab" && <LabPage />}
          {tab === "Trades" && <TradesPage />}
          {tab === "Calendar" && <CalendarPage />}
          {tab === "Strategy" && <StrategyPage />}
          {tab === "Risk" && <RiskPage />}
          {tab === "Events" && <EventsPage />}
          {tab === "Settings" && <SettingsPage />}
          {tab === "About" && <AboutPage />}
        </main>
        <footer className="px-6 pb-6 text-center text-[11px] text-dim">
          Not financial advice. Leveraged crypto can lose more than you expect, fast. Backtests and paper results flatter live ones.
        </footer>
      </div>
    </div>
  );
}
