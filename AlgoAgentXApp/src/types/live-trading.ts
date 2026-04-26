export type LiveMode = "PAPER" | "DEMO" | "LIVE";
export type BrokerStatus = "CONNECTED" | "DISCONNECTED" | "EXPIRED" | "ERROR";
export type DeploymentStatus = "DRAFT" | "RUNNING" | "PAUSED" | "STOPPED" | "ERROR";
export type SignalType = "BUY" | "SELL" | "EXIT" | "HOLD";
export type PositionSide = "LONG" | "SHORT";

export interface BrokerAccount {
  id: string;
  user_id?: string;
  broker_name: string;
  account_label: string;
  mode: LiveMode;
  status: BrokerStatus;
  server_name?: string | null;
  login_id?: string | null;
  metadata_json?: Record<string, unknown>;
  last_connected_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface BrokerConnectionResult {
  connected: boolean;
  message: string;
  account_login?: string | null;
  server?: string | null;
  balance?: number | string | null;
  equity?: number | string | null;
  currency?: string | null;
  raw?: Record<string, unknown>;
}

export interface BrokerAccountInfo extends BrokerConnectionResult {}

export interface BrokerTestResponse {
  broker_account: BrokerAccount;
  connection: BrokerConnectionResult;
}

export interface BrokerMt5Position {
  ticket?: number | string;
  symbol?: string;
  type?: number | string;
  volume?: number | string;
  price_open?: number | string;
  price_current?: number | string;
  profit?: number | string;
  comment?: string;
  success?: boolean;
  message?: string;
  [key: string]: unknown;
}

export interface BrokerAccountPayload {
  broker_name?: string;
  account_label: string;
  mode: LiveMode;
  status?: BrokerStatus;
  server_name?: string | null;
  login_id?: string | null;
  encrypted_password?: string | null;
  encrypted_token?: string | null;
  metadata_json?: Record<string, unknown>;
}

export interface StrategyCatalogItem {
  id: string;
  name: string;
  description?: string | null;
  visibility?: string | null;
  status?: string | null;
  strategyType?: string | null;
  market?: string | null;
  timeframe?: string | null;
}

export interface StrategyDeployment {
  id: string;
  user_id?: string;
  strategy_id: string;
  broker_account_id?: string | null;
  name: string;
  instrument: string;
  timeframe: string;
  mode: LiveMode;
  status: DeploymentStatus;
  capital: number | string;
  risk_per_trade: number | string;
  rr_ratio: number | string;
  price_risk_pct: number | string;
  max_daily_loss: number | string;
  max_trades_per_day: number;
  max_open_positions: number;
  allow_short: boolean;
  auto_trade_enabled: boolean;
  tradingview_secret?: string | null;
  webhook_url?: string;
  example_payload?: Record<string, unknown>;
  last_signal_at?: string | null;
  last_heartbeat_at?: string | null;
  started_at?: string | null;
  stopped_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface DeploymentPayload {
  strategy_id: string;
  broker_account_id?: string | null;
  name: string;
  instrument: string;
  timeframe: string;
  mode: "PAPER" | "DEMO";
  capital: number;
  risk_per_trade: number;
  rr_ratio: number;
  price_risk_pct: number;
  max_daily_loss: number;
  max_trades_per_day: number;
  max_open_positions: number;
  allow_short: boolean;
  auto_trade_enabled: boolean;
  tradingview_secret?: string | null;
}

export interface LiveSignal {
  id: string;
  deployment_id: string;
  user_id?: string;
  strategy_id?: string;
  source: string;
  symbol: string;
  timeframe: string;
  signal_type: SignalType;
  side?: PositionSide | null;
  price?: number | string | null;
  candle_time?: string | null;
  confidence?: number | string | null;
  reason?: string | null;
  status: string;
  rejection_reason?: string | null;
  created_at?: string;
}

export interface LiveOrder {
  id: string;
  deployment_id: string;
  signal_id?: string | null;
  user_id?: string;
  broker_account_id?: string | null;
  broker_order_id?: string | null;
  symbol: string;
  side: "BUY" | "SELL";
  order_type: string;
  qty: number | string;
  entry_price?: number | string | null;
  executed_price?: number | string | null;
  stop_loss?: number | string | null;
  target?: number | string | null;
  status: string;
  error_message?: string | null;
  raw_response?: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
}

export interface LivePosition {
  id: string;
  deployment_id: string;
  user_id?: string;
  broker_account_id?: string | null;
  symbol: string;
  side: PositionSide;
  qty: number | string;
  avg_entry_price: number | string;
  current_price?: number | string | null;
  stop_loss?: number | string | null;
  target?: number | string | null;
  unrealized_pnl: number | string;
  realized_pnl: number | string;
  status: "OPEN" | "CLOSED" | "ERROR";
  opened_at?: string;
  closed_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface LiveTradeLog {
  id: string;
  deployment_id: string;
  user_id?: string;
  event_type: string;
  level: "INFO" | "WARNING" | "ERROR";
  message: string;
  metadata_json?: Record<string, unknown> | null;
  created_at?: string;
}

export interface LiveDeploymentSummary {
  status: string;
  mode: string;
  today_pnl: number | string;
  realized_pnl: number | string;
  unrealized_pnl: number | string;
  open_positions_count: number;
  orders_count_today: number;
  signals_count_today: number;
  equity: number | string;
}
