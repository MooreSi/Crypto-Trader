import { useState } from "react";
import { Pause, Play, RotateCw, Square } from "lucide-react";
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

export function Header({ status, reload, title }: { status: SystemStatus | null; reload: () => void; title?: string }) {
  const [phase, setPhase] = useState<"running" | "stopped" | "restarting">("running");
  const [error, setError] = useState("");

  const toggle = async () => {
    if (!status) return;
    try {
      await api.post("/api/system/pause", { paused: !status.paused });
      setError("");
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
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

  const net = status?.network ?? "";
  return (
    <>
      <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-line/70 bg-bg/75 px-4 py-3 backdrop-blur-md sm:px-6">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          {title && <h1 className="mr-2 text-lg font-semibold tracking-tight">{title}</h1>}
          {status && <Badge tone={NETWORK_TONE[net] ?? "muted"} dot>{net.toUpperCase()}</Badge>}
          {status && <Badge tone={status.exchange_ok ? "profit" : "loss"}>{status.exchange_ok ? "exchange ok" : "exchange offline"}</Badge>}
          {status?.paused && <Badge tone="warn">PAUSED</Badge>}
          <Badge tone="muted">24/7</Badge>
          {status?.admin_console && (
            <span className="hidden text-xs text-dim md:inline" title={status.admin_console.last_error}>
              admin console {status.admin_console.connected ? "connected" : "offline"}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={toggle} title="Pause stops new signals and trades; open trades are still managed">
            {status?.paused ? <><Play className="h-4 w-4" />Resume</> : <><Pause className="h-4 w-4" />Pause</>}
          </Button>
          <Button onClick={() => lifecycle("restart")} disabled={phase !== "running"}
                  title="Shut the app down and start it again">
            <RotateCw className="h-4 w-4" />Restart
          </Button>
          <Button tone="danger" onClick={() => lifecycle("stop")} disabled={phase !== "running"}
                  title="Shut the app down. Start it again with Crypto Start">
            <Square className="h-3.5 w-3.5" />Stop
          </Button>
        </div>
      </header>
      {net === "mainnet" && (
        <div className="border-b border-loss/30 bg-loss/10 px-6 py-1.5 text-center text-xs font-medium text-loss">
          MAINNET: orders placed by live engines use real money.
        </div>
      )}
      {error && <div className="border-b border-line bg-loss/15 px-6 py-2 text-sm">Could not do that: {error}</div>}
      {phase !== "running" && (
        <div className="border-b border-line bg-warn/15 px-6 py-3 text-sm">
          {phase === "stopped"
            ? <>Crypto Trader is stopped. Start it again with Crypto Start (macOS) or Setup &amp; Start Crypto (Windows). {KEPT}</>
            : <>Restarting Crypto Trader. This page reloads when it is back. {KEPT}</>}
        </div>
      )}
    </>
  );
}
