import { Activity, Pause, Play } from "lucide-react";
import { api } from "@/api/client";
import type { SystemStatus } from "@/api/types";
import { Badge, Button } from "@/components/shared/ui";

export const NETWORK_TONE: Record<string, "warn" | "accent" | "loss"> = {
  paper: "accent", testnet: "warn", mainnet: "loss",
};

export function Header({ status, reload }: { status: SystemStatus | null; reload: () => void }) {
  const toggle = async () => {
    if (!status) return;
    await api.post("/api/system/pause", { paused: !status.paused });
    reload();
  };
  return (
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
      </div>
    </header>
  );
}
