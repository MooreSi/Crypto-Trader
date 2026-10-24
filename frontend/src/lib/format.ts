export function usd(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function signed(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return (n > 0 ? "+" : "") + usd(n, digits);
}

/** Price with enough significant figures for any coin, from BTC to a meme. */
export function price(n: number | null | undefined): string {
  if (n === null || n === undefined) return "-";
  const abs = Math.abs(n);
  const digits = abs >= 1000 ? 1 : abs >= 1 ? 3 : abs >= 0.01 ? 5 : 8;
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function compact(n: number): string {
  return Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

export function time(ts: number | null | undefined): string {
  if (!ts) return "-";
  return new Date(ts * 1000).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function ago(ts: number | null | undefined): string {
  if (!ts) return "never";
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 90) return `${Math.round(s)}s ago`;
  if (s < 5400) return `${Math.round(s / 60)}m ago`;
  return `${Math.round(s / 3600)}h ago`;
}

export function pnlClass(n: number | null | undefined): string {
  if (!n) return "text-muted";
  return n > 0 ? "text-profit" : "text-loss";
}
