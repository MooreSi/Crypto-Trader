import clsx from "clsx";
import type { ReactNode } from "react";

export function Card({ title, right, children, className }: {
  title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={clsx("rounded-lg border border-line bg-panel", className)}>
      {(title || right) && (
        <header className="flex items-center justify-between border-b border-line px-4 py-2">
          <h2 className="text-sm font-semibold text-text">{title}</h2>
          <div className="flex items-center gap-2">{right}</div>
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Stat({ label, value, tone }: { label: string; value: ReactNode; tone?: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className={clsx("num mt-1 text-xl font-semibold", tone)}>{value}</div>
    </div>
  );
}

export function Button({ children, onClick, tone = "default", disabled, title }: {
  children: ReactNode; onClick?: () => void; tone?: "default" | "accent" | "danger";
  disabled?: boolean; title?: string;
}) {
  return (
    <button
      type="button"
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={clsx(
        "rounded-md px-3 py-1.5 text-sm font-medium transition disabled:opacity-40",
        tone === "accent" && "bg-accent text-bg hover:brightness-110",
        tone === "danger" && "bg-loss/90 text-white hover:bg-loss",
        tone === "default" && "border border-line bg-panel-2 text-text hover:border-accent",
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
      className={clsx("relative inline-flex h-5 w-9 items-center rounded-full transition disabled:opacity-40",
        on ? "bg-accent" : "bg-line")}
    >
      <span className={clsx("inline-block h-4 w-4 rounded-full bg-white transition", on ? "translate-x-4" : "translate-x-0.5")} />
    </button>
  );
}

export function Badge({ children, tone = "muted" }: {
  children: ReactNode; tone?: "muted" | "profit" | "loss" | "warn" | "accent";
}) {
  return (
    <span className={clsx("rounded px-1.5 py-0.5 text-xs font-medium", {
      "bg-line text-muted": tone === "muted",
      "bg-profit/15 text-profit": tone === "profit",
      "bg-loss/15 text-loss": tone === "loss",
      "bg-warn/15 text-warn": tone === "warn",
      "bg-accent/15 text-accent": tone === "accent",
    })}>
      {children}
    </span>
  );
}

export function ErrorLine({ error }: { error: string }) {
  if (!error) return null;
  return <div className="rounded-md border border-loss/40 bg-loss/10 px-3 py-2 text-sm text-loss">{error}</div>;
}

export function Table({ head, children, empty }: { head: string[]; children: ReactNode; empty?: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="num w-full text-left text-sm">
        <thead className="text-xs uppercase text-muted">
          <tr>{head.map((h) => <th key={h} className="whitespace-nowrap px-2 py-1.5 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-line">{children}</tbody>
      </table>
      {empty && <div className="px-2 py-6 text-center text-sm text-muted">{empty}</div>}
    </div>
  );
}

/** Ask before anything that moves money or can't be undone. */
export function confirmAction(message: string): boolean {
  return window.confirm(message);
}
