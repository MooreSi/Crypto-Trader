export interface Position {
  coin: string;
  size: number;
  entry_price: number;
  unrealised_pnl: number;
  leverage: number;
  liquidation_price: number | null;
  margin_used: number;
  direction: "long" | "short";
}

export interface OpenOrder {
  coin: string;
  oid: number;
  is_buy: boolean;
  size: number;
  limit_price: number;
  trigger_price: number | null;
  reduce_only: boolean;
  kind: string;
}

export interface Account {
  network: string;
  equity: number;
  available: number;
  margin_used: number;
  day_start_equity: number;
  day_pnl: number;
  realised_today: number;
  positions: Position[];
  open_orders: OpenOrder[];
}

export interface SystemStatus {
  paused: boolean;
  network: string;
  uptime_s: number;
  exchange_ok: boolean;
  last_error: string;
  positions_at: number | null;
  engines_at: number | null;
  unmanaged_positions: string[];
  admin_console: { connected: boolean; host: string; last_error: string; admitted: boolean };
}

export interface Market {
  coin: string;
  mark_price: number;
  funding_rate: number;
  open_interest: number;
  day_notional_volume: number;
  change_24h_pct: number;
  scanned: boolean;
  max_leverage: number | null;
  only_isolated: boolean | null;
}

export interface EngineStatus {
  name: string;
  interval: string;
  enabled: boolean;
  live: boolean;
  last_cycle: number | null;
  last_error: string;
  stats: { total: number; tracking: number; wins: number; losses: number; expired: number; avg_r: number; executed: number };
  model: { trained: boolean; meta: Record<string, unknown>; last_report: Record<string, unknown> };
}

export interface EngineSignal {
  id: number;
  created_at: number;
  coin: string;
  interval: string;
  direction: string;
  entry: number;
  stop: number;
  reason: string;
  ml_score: number | null;
  status: string;
  r_final: number | null;
  mfe_r: number | null;
  live_status: string | null;
}

export interface Trade {
  id: number;
  engine: string;
  coin: string;
  direction: "long" | "short";
  status: "open" | "closed";
  network: string;
  entry_price: number;
  size: number;
  initial_size: number;
  stop_loss: number;
  initial_stop: number;
  take_profits: number[];
  tp_hit: number;
  leverage: number;
  risk_usd: number;
  opened_at: number;
  closed_at: number | null;
  close_price: number | null;
  close_reason: string | null;
  realised_pnl: number;
  fees: number;
  net_pnl: number;
  r_achieved: number | null;
}

export interface TradeEvent {
  ts: number;
  kind: string;
  detail: Record<string, unknown>;
}

export interface GateDecision {
  id: number;
  ts: number;
  engine: string;
  coin: string;
  direction: string;
  passed: number;
  decisions: { gate: string; passed: boolean; detail: string }[];
}

export interface CalendarEvent {
  id: number;
  uid: string;
  ts: number;
  title: string;
  kind: string;
  impact: "low" | "medium" | "high";
  coins: string;
  source: string;
}

export interface AppSettings {
  network: string;
  network_on_restart: string;
  networks: string[];
  account_address: string;
  has_agent_key: Record<string, boolean>;
  admin_console_enabled: boolean;
  admin_console_nickname: string;
  paper_starting_balance: number;
  dashboard_port: number;
  data_dir: string;
}

export type RiskSettings = Record<string, number | boolean | string[] | number[][]>;

export interface Release {
  version: string;
  date: string;
  title: string;
  notes: string[];
}
