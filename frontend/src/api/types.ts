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
  started_at: number;
  uptime_s: number;
  exchange_ok: boolean;
  last_error: string;
  positions_at: number | null;
  engines_at: number | null;
  unmanaged_positions: string[];
  open_positions?: number;
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
  model: { trained: boolean; meta: EngineModelReport; last_report: EngineModelReport };
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
  telegram_enabled: boolean;
  telegram_chat_id: string;
  has_telegram_token: boolean;
}

export type RiskSettings = Record<string, number | boolean | string[] | number[][]>;

export interface Release {
  version: string;
  date: string;
  title: string;
  notes: string[];
}

export interface EngineModelReport {
  holdout_auc?: number;
  auc_needed?: number;
  base_rate?: number;
  samples?: number;
  accepted?: boolean;
  reason?: string;
  top_features?: [string, number][];
  handover?: boolean;
}

export interface PulseRow {
  coin: string;
  price: number;
  change_pct: number;
  funding_pct_h: number;
  volume_usd: number;
}

export interface MarketPulse {
  markets: number;
  breadth_pct: number;
  mood: "risk-on" | "risk-off" | "mixed";
  btc_change_pct: number;
  avg_change_pct: number;
  funding_pct_h: number;
  open_interest_usd: number;
  volume_usd: number;
  crowded_longs: PulseRow[];
  crowded_shorts: PulseRow[];
  gainers: PulseRow[];
  losers: PulseRow[];
}

export interface PerfBlock {
  trades: number;
  wins: number;
  win_rate: number | null;
  net_pnl: number;
  profit_factor: number | null;
  expectancy_r: number | null;
}

export interface Analytics {
  closed: number;
  net_pnl: number;
  win_rate: number | null;
  profit_factor: number | null;
  expectancy_r: number | null;
  avg_win: number | null;
  avg_loss: number | null;
  best: number | null;
  worst: number | null;
  longest_losing_streak: number;
  avg_hold_hours: number | null;
  max_drawdown_pct: number;
  sharpe: number | null;
  by_engine: Record<string, PerfBlock>;
}

export interface StrategyInfo {
  name: string;
  interval: string;
  htf: string | null;
  kind: "engine" | "lab";
  about: string;
}

export interface BacktestTrade {
  opened_at: number;
  closed_at: number;
  direction: "long" | "short";
  entry: number;
  stop: number;
  r: number;
  exit: string;
  tp_hits: number;
  reason: string;
}

export interface BacktestResult {
  strategy: string;
  coin: string;
  interval: string;
  bars: number;
  from: number | null;
  to: number | null;
  ladder: number[][];
  summary: {
    trades: number;
    wins: number;
    win_rate: number | null;
    total_r: number;
    avg_r: number | null;
    profit_factor: number | null;
    best_r: number | null;
    worst_r: number | null;
    max_drawdown_r: number;
    risk_pct: number;
    compounded_return_pct: number;
    curve: { t: number; r: number }[];
  };
  trades: BacktestTrade[];
}

export type BacktestSummary = BacktestResult["summary"];

export interface TuneFold {
  train_from: number;
  test_from: number;
  test_to: number;
  chosen: Record<string, number | string>;
  train: Omit<BacktestSummary, "curve">;
  test: Omit<BacktestSummary, "curve">;
  test_default: Omit<BacktestSummary, "curve">;
  fallback: boolean;
}

export interface TuneResult {
  strategy: string;
  coin: string;
  interval: string;
  bars: number;
  from: number | null;
  to: number | null;
  grid: Record<string, number[]>;
  defaults: Record<string, number>;
  folds: TuneFold[];
  oos: BacktestSummary;
  oos_default: BacktestSummary;
  proposal: Record<string, unknown> & { ladder: string; tp_ladder: number[][]; breakeven_after_tp: number };
  stability: number;
  beats_default: boolean;
  profitable: boolean;
  candidates: number;
  min_trades: number;
}

/** One closed trade as the Calendar files it: under the UTC day it closed on. */
export interface CalendarTrade {
  id: number;
  engine: string;
  coin: string;
  direction: "long" | "short";
  opened_at: number;
  closed_at: number;
  /** YYYY-MM-DD, UTC: the risk governor's trading day. */
  day: string;
  net_pnl: number;
  fees: number;
  risk_usd: number;
  r: number | null;
  close_reason: string | null;
  /** Liquidity session at the close (services/market/sessions.py). */
  session: string;
}

export interface CalendarEvent {
  id: number; uid: string; ts: number; day: string; title: string; kind: string;
  impact: "low" | "medium" | "high"; coins: string; source: string;
}

export interface JournalEntry {
  day: string; note: string; tags: string[]; mood: number | null; updated_at: number;
}

export type JournalDraft = Pick<JournalEntry, "note" | "tags" | "mood">;
