import clsx from "clsx";
import type { ReactNode } from "react";

export function Card({ title, subtitle, icon, right, children, className, pad = true }: {
  title?: ReactNode; subtitle?: ReactNode; icon?: ReactNode; right?: ReactNode; children: ReactNode;
  className?: string; pad?: boolean;
}) {
  return (
    <section className={clsx("panel fade-up rounded-xl", className)}>
      {(title || right) && (
        <header className="flex items-center justify-between gap-3 border-b border-line/70 px-4 py-3">
          <div className="flex min-w-0 items-center gap-2.5">
            {icon && <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-accent/10 text-accent">{icon}</span>}
            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold tracking-tight text-text">{title}</h2>
              {subtitle && <div className="truncate text-xs text-muted">{subtitle}</div>}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">{right}</div>
        </header>
      )}
      <div className={pad ? "p-4" : ""}>{children}</div>
    </section>
  );
}

export function Stat({ label, value, tone, sub, icon, children }: {
  label: string; value: ReactNode; tone?: string; sub?: ReactNode; icon?: ReactNode; children?: ReactNode;
}) {
  return (
    <div className="panel fade-up relative overflow-hidden rounded-xl px-4 py-3.5">
      <div className="flex items-center justify-between text-[11px] font-medium uppercase tracking-wider text-muted">
        <span>{label}</span>
        {icon && <span className="text-dim">{icon}</span>}
      </div>
      <div className={clsx("num mt-1.5 text-2xl font-semibold tracking-tight", tone)}>{value}</div>
      {sub && <div className="num mt-0.5 text-xs text-muted">{sub}</div>}
      {children}
    </div>
  );
}

export function Button({ children, onClick, tone = "default", disabled, title, size = "md", type = "button" }: {
  children: ReactNode; onClick?: () => void; tone?: "default" | "accent" | "danger" | "ghost";
  disabled?: boolean; title?: string; size?: "sm" | "md"; type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={clsx(
        "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-lg font-medium transition active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40",
        size === "sm" ? "px-2.5 py-1 text-xs" : "px-3.5 py-1.5 text-sm",
        tone === "accent" && "grad-fill text-bg shadow-[0_6px_20px_-8px_rgba(34,211,238,0.7)] hover:brightness-110",
        tone === "danger" && "bg-loss/90 text-white hover:bg-loss",
        tone === "default" && "border border-line-2 bg-panel-2 text-text hover:border-accent/60 hover:bg-panel-3",
        tone === "ghost" && "text-muted hover:bg-panel-2 hover:text-text",
      )}
    >
      {children}
    </button>
  );
}

export function Switch({ on, onChange, label, disabled }: {
  on: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!on)}
      className={clsx("relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition disabled:opacity-40",
        on ? "grad-fill border-transparent" : "border-line-2 bg-panel-3")}
    >
      <span className={clsx("inline-block h-4.5 w-4.5 rounded-full bg-white shadow transition", on ? "translate-x-5.5" : "translate-x-0.5")} />
    </button>
  );
}

export type Tone = "muted" | "profit" | "loss" | "warn" | "accent";

export function Badge({ children, tone = "muted", dot }: { children: ReactNode; tone?: Tone; dot?: boolean }) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide", {
      "bg-line/70 text-muted": tone === "muted",
      "bg-profit/12 text-profit ring-1 ring-profit/20": tone === "profit",
      "bg-loss/12 text-loss ring-1 ring-loss/20": tone === "loss",
      "bg-warn/12 text-warn ring-1 ring-warn/20": tone === "warn",
      "bg-accent/12 text-accent ring-1 ring-accent/20": tone === "accent",
    })}>
      {dot && <span className="live-dot h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

export function Side({ direction }: { direction: string }) {
  return <Badge tone={direction === "long" ? "profit" : "loss"}>{direction}</Badge>;
}

export function ErrorLine({ error }: { error: string }) {
  if (!error) return null;
  return <div className="fade-up rounded-lg border border-loss/30 bg-loss/10 px-3 py-2 text-sm text-loss">{error}</div>;
}

export function Notice({ children, tone = "muted" }: { children: ReactNode; tone?: Tone }) {
  return (
    <div className={clsx("fade-up rounded-lg border px-3 py-2 text-sm", {
      "border-line-2 bg-panel-2 text-text": tone === "muted" || tone === "accent",
      "border-warn/30 bg-warn/10 text-warn": tone === "warn",
      "border-profit/30 bg-profit/10 text-profit": tone === "profit",
      "border-loss/30 bg-loss/10 text-loss": tone === "loss",
    })}>{children}</div>
  );
}

export function Table({ head, children, empty, align }: {
  head: string[]; children: ReactNode; empty?: string; align?: ("l" | "r")[];
}) {
  return (
    <div className="-mx-4 overflow-x-auto">
      <table className="num w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line/70 text-[11px] uppercase tracking-wider text-dim">
            {head.map((h, i) => (
              <th key={`${h}${i}`} className={clsx("whitespace-nowrap px-4 py-2 font-medium", align?.[i] === "r" && "text-right")}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line/50 [&>tr]:transition-colors [&>tr:hover]:bg-panel-2/60 [&_td]:px-4 [&_td]:py-2">{children}</tbody>
      </table>
      {empty && <Empty>{empty}</Empty>}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="px-4 py-8 text-center text-sm text-muted">{children}</div>;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("skeleton rounded-md", className ?? "h-4 w-full")} />;
}

export function Segmented<T extends string>({ value, options, onChange, label }: {
  value: T; options: readonly T[]; onChange: (v: T) => void; label?: (v: T) => string;
}) {
  return (
    <div className="inline-flex rounded-lg border border-line bg-bg-2 p-0.5">
      {options.map((o) => (
        <button key={o} type="button" onClick={() => onChange(o)}
                className={clsx("rounded-md px-2.5 py-1 text-xs font-medium transition",
                  o === value ? "bg-panel-3 text-text shadow" : "text-muted hover:text-text")}>
          {label ? label(o) : o}
        </button>
      ))}
    </div>
  );
}

/** A thin horizontal meter, 0..1. */
export function Meter({ value, tone = "accent" }: { value: number; tone?: Tone }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-line/80">
      <div className={clsx("h-full rounded-full transition-[width] duration-500", {
        "grad-fill": tone === "accent", "bg-profit": tone === "profit", "bg-loss": tone === "loss",
        "bg-warn": tone === "warn", "bg-muted": tone === "muted",
      })} style={{ width: `${pct}%` }} />
    </div>
  );
}

/** A tiny inline line chart for stat cards. */
export function Sparkline({ values, className }: { values: number[]; className?: string }) {
  if (values.length < 2) return null;
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * 100},${30 - ((v - min) / span) * 28 - 1}`);
  const up = values[values.length - 1] >= values[0];
  const color = up ? "var(--color-profit)" : "var(--color-loss)";
  return (
    <svg viewBox="0 0 100 30" preserveAspectRatio="none" className={clsx("h-8 w-full", className)} aria-hidden>
      <defs>
        <linearGradient id={`spark-${up ? "u" : "d"}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.25" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,30 ${pts.join(" ")} 100,30`} fill={`url(#spark-${up ? "u" : "d"})`} />
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

/** A ring showing a 0..1 share, with a label in the middle. */
export function Ring({ value, size = 64, children, tone = "accent" }: {
  value: number | null; size?: number; children?: ReactNode; tone?: Tone;
}) {
  const r = 26, c = 2 * Math.PI * r;
  const v = value == null ? 0 : Math.max(0, Math.min(1, value));
  const color = { accent: "var(--color-accent)", profit: "var(--color-profit)", loss: "var(--color-loss)",
    warn: "var(--color-warn)", muted: "var(--color-muted)" }[tone];
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg viewBox="0 0 64 64" className="absolute inset-0 -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" stroke="var(--color-line)" strokeWidth="6" />
        <circle cx="32" cy="32" r={r} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
                strokeDasharray={`${c * v} ${c}`} style={{ transition: "stroke-dasharray 0.6s ease" }} />
      </svg>
      <div className="num relative text-center text-sm font-semibold">{children}</div>
    </div>
  );
}

export function Field({ label, help, children }: { label: ReactNode; help?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm text-text">{label}</span>
        {children}
      </div>
      {help && <div className="mt-0.5 text-xs text-muted">{help}</div>}
    </label>
  );
}

export const inputCls = "rounded-lg border border-line-2 bg-bg-2 px-2.5 py-1.5 text-sm text-text outline-none transition placeholder:text-dim focus:border-accent/70 focus:ring-2 focus:ring-accent/15";

/** Ask before anything that moves money or can't be undone. */
export function confirmAction(message: string): boolean {
  return window.confirm(message);
}
