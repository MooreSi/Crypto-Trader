import { useState } from "react";
import { Activity, Pause, Play, RotateCw, Square } from "lucide-react";
import { api } from "@/api/client";
import type { SystemStatus } from "@/api/types";
import { Badge, Button } from "@/components/shared/ui";

export const NETWORK_TONE: Record<string, "warn" | "accent" | "loss"> = {
  paper: "accent", testnet: "warn", mainnet: "loss",
};

const KEPT = "Open positions keep their exchange-side stop and take-profits.";

/** Poll until a process with a new start time answers, then reload the page. */
async function reloadWhenBack(previousStart: number | undefined) {
  for (let i = 0; i < 120; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    try {
      const s = await api.get<SystemStatus>("/api/system/status");
      if (s.started_at !== previousStart) { window.location.reload(); return; }
    } catch {
      /* still down */
    }
  }
}

export function Header({ status, reload }: { status: SystemStatus | null; reload: () => void }) {
  const [phase, setPhase] = useState<"running" | "stopped" | "restarting">("running");
  const [error, setError] = useState("");

  const toggle = async () => {
    if (!status) return;
    await api.post("/api/system/pause", { paused: !status.paused });
    reload();
  };

  const lifecycle = async (action: "stop" | "restart") => {
    const ask = action === "stop"
      ? `Stop Crypto Trader? Nothing will be scanned or managed until you start it again. ${KEPT}`
      : `Restart Crypto Trader? It will be back in a few seconds. ${KEPT}`;
    if (!window.confirm(ask)) return;
    try {
      await api.post(`/api/system/${action}`);
      setError("");
      setPhase(action === "stop" ? "stopped" : "restarting");
      if (action === "restart") void reloadWhenBack(status?.started_at);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <>
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-panel px-5 py-3">
        <div className="flex items-center gap-3">
          <Activity className="h-5 w-5 text-accent" />
          <span className="text-lg font-semibold">Crypto Trader</span>
          <span className="text-xs text-muted">Hyperliquid</span>
          {status && <Badge tone={NETWORK_TONE[status.network] ?? "muted"}>{status.network.toUpperCase()}</Badge>}
          {status && <Badge tone={status.exchange_ok ? "profit" : "loss"}>{status.exchange_ok ? "exchange ok" : "exchange offline"}</Badge>}
          {status?.paused && <Badge tone="warn">PAUSED</Badge>}
          <Badge tone="muted">24/7</Badge>
        </div>
        <div className="flex items-center gap-2">
          {status?.admin_console && (
            <span className="text-xs text-muted" title={status.admin_console.last_error}>
              admin console: {status.admin_console.connected ? "connected" : "offline"}
            </span>
          )}
          <Button onClick={toggle} title="Pause stops new signals and trades; open trades are still managed">
            {status?.paused ? <><Play className="mr-1 inline h-4 w-4" />Resume</> : <><Pause className="mr-1 inline h-4 w-4" />Pause</>}
          </Button>
          <Button onClick={() => lifecycle("restart")} disabled={phase !== "running"}
                  title="Shut the app down and start it again">
            <RotateCw className="mr-1 inline h-4 w-4" />Restart
          </Button>
          <Button tone="danger" onClick={() => lifecycle("stop")} disabled={phase !== "running"}
                  title="Shut the app down. Start it again with Crypto Start">
            <Square className="mr-1 inline h-4 w-4" />Stop
          </Button>
        </div>
      </header>
      {error && <div className="border-b border-line bg-loss/15 px-5 py-2 text-sm">Could not do that: {error}</div>}
      {phase !== "running" && (
        <div className="border-b border-line bg-warn/15 px-5 py-3 text-sm">
          {phase === "stopped"
            ? <>Crypto Trader is stopped. Start it again with Crypto Start (macOS) or Setup &amp; Start Crypto (Windows). {KEPT}</>
            : <>Restarting Crypto Trader. This page reloads when it is back. {KEPT}</>}
        </div>
      )}
    </>
  );
}
