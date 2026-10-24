import { api } from "@/api/client";
import type { Release } from "@/api/types";
import { usePoll } from "@/hooks/usePoll";
import { Card } from "@/components/shared/ui";

export function AboutPage() {
  const { data } = usePoll(() => api.get<Release[]>("/api/system/releases"), 600000);
  return (
    <div className="space-y-4">
      <Card title="About Crypto Trader">
        <div className="space-y-2 text-sm text-muted">
          <p>Automated trading of Hyperliquid perpetuals, 24 hours a day, 7 days a week, from your own computer.</p>
          <p>Three research engines track every signal they find, learn which ones work, and only trade when you switch
            them live and every risk gate passes. Stops and take-profits sit on the exchange, so positions stay protected
            while the app is closed.</p>
          <p>Licensed under the GNU AGPL v3. Source: github.com/MooreSi/Crypto-Trader. Not financial advice; trading
            leveraged crypto can lose more than you expect, fast.</p>
        </div>
      </Card>
      <Card title="Version history">
        {data?.map((r) => (
          <div key={r.version} className="mb-4">
            <div className="font-semibold">v{r.version} <span className="text-xs font-normal text-muted">{r.date} - {r.title}</span></div>
            <ul className="mt-1 list-disc pl-5 text-sm text-muted">{r.notes.map((n) => <li key={n}>{n}</li>)}</ul>
          </div>
        ))}
      </Card>
    </div>
  );
}
