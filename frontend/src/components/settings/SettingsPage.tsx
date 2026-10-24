import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { AppSettings } from "@/api/types";
import { Badge, Button, Card, ErrorLine, Switch, confirmAction } from "@/components/shared/ui";

const NETWORK_HELP: Record<string, string> = {
  paper: "Simulated account on live mainnet prices. No wallet needed. No funding or liquidation modelled.",
  testnet: "Hyperliquid's test exchange with test USDC. This is the 'demo account'.",
  mainnet: "Real money.",
};

export function SettingsPage() {
  const [s, setS] = useState<AppSettings | null>(null);
  const [address, setAddress] = useState("");
  const [key, setKey] = useState({ network: "testnet", key: "" });
  const [nick, setNick] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const apply = (v: AppSettings) => { setS(v); setAddress(v.account_address); setNick(v.admin_console_nickname); };
  useEffect(() => { api.get<AppSettings>("/api/settings").then(apply).catch((e) => setError(String(e))); }, []);
  const run = async (p: Promise<AppSettings>, ok: string) => {
    try { apply(await p); setMsg(ok); setError(""); } catch (e) { setError(String(e)); }
  };

  const chooseNetwork = (n: string) => {
    if (n === "mainnet" && !confirmAction("Switch to MAINNET after restart? Orders will use real money.")) return;
    void run(api.post("/api/settings/network", { network: n }), `Network will be ${n} after you restart the app.`);
  };

  if (!s) return <ErrorLine error={error || "Loading..."} />;
  return (
    <div className="space-y-4">
      <ErrorLine error={error} />
      {msg && <div className="rounded-md border border-line bg-panel-2 px-3 py-2 text-sm">{msg}</div>}
      <Card title="Network">
        <div className="space-y-2">
          {s.networks.map((n) => (
            <label key={n} className="flex cursor-pointer items-start gap-3 rounded-md border border-line p-3 hover:border-accent">
              <input type="radio" name="network" checked={s.network_on_restart === n} onChange={() => chooseNetwork(n)} className="mt-1" />
              <div>
                <div className="font-medium capitalize">{n} {s.network === n && <Badge tone="accent">running</Badge>}</div>
                <div className="text-xs text-muted">{NETWORK_HELP[n]}</div>
              </div>
            </label>
          ))}
          {s.network_on_restart !== s.network && (
            <div className="text-sm text-warn">Restart Crypto Trader to switch from {s.network} to {s.network_on_restart}.</div>
          )}
        </div>
      </Card>
      <Card title="Hyperliquid account">
        <p className="mb-2 text-xs text-muted">The address of the account that holds your funds (0x...). Used for testnet and mainnet.</p>
        <div className="flex gap-2">
          <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="0x..."
                 className="flex-1 rounded-md border border-line bg-panel-2 px-2 py-1 font-mono text-sm" />
          <Button tone="accent" onClick={() => run(api.post("/api/settings/account", { address }), "Account address saved")}>Save</Button>
        </div>
      </Card>
      <Card title="API wallet key">
        <div className="mb-3 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
          Enter an <b>API wallet</b> key only (Hyperliquid: More &gt; API). An API wallet can trade but cannot withdraw.
          Never enter your main wallet's private key. The key is stored in your operating system's keychain, not in a file.
        </div>
        <div className="mb-3 flex gap-3 text-sm">
          {Object.entries(s.has_agent_key).map(([n, has]) => (
            <span key={n}>{n}: {has ? <Badge tone="profit">stored</Badge> : <Badge>none</Badge>}
              {has && <button type="button" className="ml-1 text-xs text-loss underline"
                              onClick={() => run(api.del(`/api/settings/agent-key/${n}`), `${n} key removed`)}>remove</button>}
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <select value={key.network} onChange={(e) => setKey({ ...key, network: e.target.value })}
                  className="rounded-md border border-line bg-panel-2 px-2 py-1">
            <option value="testnet">testnet</option><option value="mainnet">mainnet</option>
          </select>
          <input type="password" autoComplete="off" value={key.key} onChange={(e) => setKey({ ...key, key: e.target.value })}
                 placeholder="API wallet private key (64 hex)" className="flex-1 rounded-md border border-line bg-panel-2 px-2 py-1 font-mono text-sm" />
          <Button tone="accent" onClick={() => { void run(api.post("/api/settings/agent-key", key), `${key.network} key stored`); setKey({ ...key, key: "" }); }}>Store</Button>
        </div>
      </Card>
      <Card title="Admin console">
        <div className="mb-3 flex items-center justify-between text-sm">
          <div>
            <div>Report to the admin console</div>
            <div className="text-xs text-muted">Shows this install as "Crypto Trader - {nick || "this machine"}" with version "Crypto Trader". Sends status and logs on request; never keys.</div>
          </div>
          <Switch label="admin console" on={s.admin_console_enabled}
                  onChange={(v) => run(api.post("/api/settings/admin-console", { enabled: v, nickname: nick }), "Saved; takes effect on restart")} />
        </div>
        <div className="flex gap-2">
          <input value={nick} onChange={(e) => setNick(e.target.value)} placeholder="Nickname (optional)"
                 className="flex-1 rounded-md border border-line bg-panel-2 px-2 py-1 text-sm" />
          <Button onClick={() => run(api.post("/api/settings/admin-console", { enabled: s.admin_console_enabled, nickname: nick }), "Saved; takes effect on restart")}>Save</Button>
        </div>
      </Card>
      <Card title="This install">
        <div className="space-y-1 text-sm text-muted">
          <div>Data folder: <span className="font-mono text-text">{s.data_dir}</span></div>
          <div>Dashboard: <span className="font-mono text-text">http://127.0.0.1:{s.dashboard_port}</span> (local only)</div>
        </div>
      </Card>
    </div>
  );
}
