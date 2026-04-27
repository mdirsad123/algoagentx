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

export interface SafeBrokerStatus {
  id?: string;
  broker_account_id?: string;
  broker_name?: string;
  account_label?: string;
  mode?: LiveMode | string;
  status?: BrokerStatus | string;
  login_id?: string | null;
  server_name?: string | null;
  balance?: number | string | null;
  equity?: number | string | null;
  currency?: string | null;
  last_connected_at?: string | null;
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

export interface BrokerStatusResponse {
  connected: boolean;
  message?: string | null;
  broker?: SafeBrokerStatus | null;
  account_info?: BrokerAccountInfo | null;
}

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
  lifecycle_status?: string | null;
  lifecycleStatus?: string | null;
  is_deployable_paper?: boolean;
  isDeployablePaper?: boolean;
  is_deployable_demo?: boolean;
  isDeployableDemo?: boolean;
  is_live_approved?: boolean;
  isLiveApproved?: boolean;
  verified_at?: string | null;
  sandbox_passed_at?: string | null;
  paper_enabled_at?: string | null;
  demo_enabled_at?: string | null;
  live_approved_at?: string | null;
  approved_by?: string | null;
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

export interface LiveDeploymentSummaryMetrics {
  capital: number | string;
  currency?: string | null;
  equity: number | string;
  realized_pnl: number | string;
  unrealized_pnl: number | string;
  today_pnl: number | string;
  open_positions: number;
  open_positions_count: number;
  orders_today: number;
  orders_count_today: number;
  signals_today: number;
  signals_count_today: number;
  total_orders: number;
  total_signals: number;
}

export interface LiveDeploymentSummaryDeployment {
  id: string;
  name: string;
  strategy_id: string;
  strategy_name: string;
  instrument: string;
  timeframe: string;
  mode: LiveMode;
  status: DeploymentStatus;
  auto_trade_enabled: boolean;
  last_signal_at?: string | null;
  last_heartbeat_at?: string | null;
  webhook_url?: string;
  tradingview_secret?: string | null;
  example_payload?: Record<string, unknown>;
}

export interface LiveDeploymentSummary {
  deployment?: LiveDeploymentSummaryDeployment;
  broker?: SafeBrokerStatus | null;
  metrics?: LiveDeploymentSummaryMetrics;
  latest_signal?: LiveSignal | null;
  latest_order?: LiveOrder | null;
  open_positions?: LivePosition[];
  recent_orders?: LiveOrder[];
  recent_signals?: LiveSignal[];
  recent_logs?: LiveTradeLog[];
  runner?: StrategyRunnerInfo | null;
  status?: string;
  mode?: string;
  today_pnl?: number | string;
  realized_pnl?: number | string;
  unrealized_pnl?: number | string;
  open_positions_count?: number;
  orders_count_today?: number;
  signals_count_today?: number;
  equity?: number | string;
}

export interface ManualSignalResponse {
  signal: LiveSignal;
  order?: LiveOrder | null;
  message?: string;
  status?: string;
}

export interface AdminLiveDeploymentRow {
  deployment_id: string;
  deployment_name: string;
  user_id?: string;
  user_name?: string | null;
  user_email?: string | null;
  strategy_id?: string;
  strategy_name: string;
  broker_account_id?: string | null;
  broker_name?: string | null;
  broker_status?: BrokerStatus | string | null;
  instrument: string;
  timeframe: string;
  mode: LiveMode;
  status: DeploymentStatus;
  auto_trade_enabled: boolean;
  last_signal_at?: string | null;
  last_heartbeat_at?: string | null;
  open_positions_count: number;
  today_pnl: number | string;
  signals_today: number;
  orders_today: number;
}

export interface AdminLiveDeploymentListSummary {
  total_deployments: number;
  running: number;
  paused: number;
  error: number;
  open_positions: number;
  today_total_pnl: number | string;
  signals_today: number;
  orders_today: number;
}

export interface AdminLiveDeploymentListResponse {
  summary: AdminLiveDeploymentListSummary;
  rows: AdminLiveDeploymentRow[];
}

export interface AdminSafeUser {
  id: string;
  email?: string | null;
  fullname?: string | null;
  mobile?: string | null;
  role?: string | null;
  created_at?: string | null;
}

export interface AdminSafeStrategy {
  id: string;
  name?: string | null;
  description?: string | null;
  visibility?: string | null;
  created_by?: string | null;
  published_by?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AdminLiveAuditAction {
  id: string;
  admin_user_id: string;
  deployment_id: string;
  action: string;
  reason?: string | null;
  metadata_json?: Record<string, unknown> | null;
  created_at?: string | null;
}

export interface AdminLiveDeploymentDetail {
  deployment: StrategyDeployment;
  user?: AdminSafeUser | null;
  strategy?: AdminSafeStrategy | null;
  broker?: SafeBrokerStatus | null;
  metrics?: LiveDeploymentSummaryMetrics;
  open_positions?: LivePosition[];
  recent_signals?: LiveSignal[];
  recent_orders?: LiveOrder[];
  recent_logs?: LiveTradeLog[];
  recent_equity_points?: LiveEquityPoint[];
  admin_audit_actions?: AdminLiveAuditAction[];
}

export interface LiveEquityPoint {
  id: string;
  deployment_id: string;
  user_id?: string;
  timestamp?: string;
  equity: number | string;
  balance?: number | string | null;
  unrealized_pnl?: number | string | null;
  realized_pnl?: number | string | null;
  created_at?: string;
}

export type AdminLiveControlAction = "force-pause" | "force-stop" | "disable-auto-trade" | "enable-auto-trade";

export interface LiveMarketCandle {
  id?: string;
  deployment_id?: string | null;
  broker_account_id?: string | null;
  symbol: string;
  timeframe: string;
  candle_time: string;
  open: number | string;
  high: number | string;
  low: number | string;
  close: number | string;
  volume?: number | string | null;
  source?: string;
  is_closed?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface LiveCandleSnapshot {
  source: string;
  symbol: string;
  resolved_symbol?: string | null;
  timeframe: string;
  requested_count?: number;
  stored_count: number;
  upserted_count?: number;
  latest_candle_time?: string | null;
  latest_close?: number | string | null;
  candles: LiveMarketCandle[];
}

export interface StrategyRunnerInfo {
  last_run_at?: string | null;
  last_candle_time?: string | null;
  last_signal?: string | null;
  latest_runner_log?: string | null;
  latest_runner_status?: string | null;
}

export interface RunStrategyResponse {
  success: boolean;
  deployment_id: string;
  latest_candle_time?: string | null;
  signal?: SignalType | string | null;
  executed: boolean;
  order_id?: string | null;
  signal_id?: string | null;
  duplicate?: boolean;
  message: string;
  latest_runner_log?: string | null;
}

export interface PlatformTradingSettings {
  id: string;
  paper_trading_enabled: boolean;
  demo_trading_enabled: boolean;
  live_trading_enabled: boolean;
  global_kill_switch: boolean;
  max_global_demo_orders_per_day?: number | null;
  max_user_demo_orders_per_day?: number | null;
  updated_by?: string | null;
  updated_at?: string | null;
}

export interface PlatformTradingSettingsPayload {
  paper_trading_enabled?: boolean;
  demo_trading_enabled?: boolean;
  live_trading_enabled?: boolean;
  global_kill_switch?: boolean;
  max_global_demo_orders_per_day?: number | null;
  max_user_demo_orders_per_day?: number | null;
}

// Optional safety fields added by Phase 11.
export interface AdminLiveDeploymentListResponseWithSettings extends AdminLiveDeploymentListResponse {
  settings?: PlatformTradingSettings;
}
