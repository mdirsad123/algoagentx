export type LiveMode = "PAPER" | "DEMO" | "LIVE";
export type BrokerStatus = "CONNECTED" | "DISCONNECTED" | "ERROR" | "PENDING_AUTH" | "PENDING_ACCOUNT_SYNC" | "AGENT_OFFLINE" | "COMING_SOON" | "EXPIRED";
export type DeploymentStatus = "DRAFT" | "RUNNING" | "PAUSED" | "STOPPED" | "ERROR";
export type SignalType = "BUY" | "SELL" | "EXIT" | "HOLD";
export type PositionSide = "LONG" | "SHORT";
export type AccountPolicyType = "STANDARD" | "FUNDED";
export type FundedLiveRiskMode = "DYNAMIC" | "FIXED";
export type FundedAttachMode = "NEW_OR_RESET_ACCOUNT" | "EXISTING_IN_PROGRESS";


export interface MT5AgentStatus {
  id: string;
  user_id?: string;
  broker_account_id: string;
  status: string;
  last_heartbeat_at?: string | null;
  terminal_status?: string | null;
  mt5_account_login?: string | null;
  server_name?: string | null;
  trading_mode?: LiveMode | string;
  balance?: number | string | null;
  equity?: number | string | null;
  currency?: string | null;
  algo_trading_enabled?: boolean | null;
  agent_version?: string | null;
  metadata_json?: Record<string, unknown>;
  selected_account?: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
}

export interface MT5AgentRegisterResponse {
  agent: MT5AgentStatus;
  agent_token: string;
  message: string;
}



export interface BrokerAccount {
  id: string;
  broker_provider_id?: string | null;
  user_id?: string;
  broker_name: string;
  broker_code?: string | null;
  auth_type?: string | null;
  account_label: string;
  mode: LiveMode;
  status: BrokerStatus;
  server_name?: string | null;
  login_id?: string | null;
  oauth_client_id?: string | null;
  oauth_redirect_uri?: string | null;
  metadata_json?: Record<string, unknown>;
  last_connection_result?: Record<string, unknown> | null;
  token_expires_at?: string | null;
  last_connected_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface SafeBrokerStatus {
  id?: string;
  broker_account_id?: string;
  broker_name?: string;
  broker_code?: string | null;
  account_label?: string;
  mode?: LiveMode | string;
  status?: BrokerStatus | string;
  login_id?: string | null;
  server_name?: string | null;
  balance?: number | string | null;
  equity?: number | string | null;
  currency?: string | null;
  last_connected_at?: string | null;
  selected_account?: Record<string, unknown> | null;
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

export interface BrokerSymbol {
  symbol: string;
  name?: string;
  path?: string | null;
  description?: string | null;
  visible?: boolean | string | null;
  trade_mode?: number | string | null;
  volume_min?: number | string | null;
  volume_max?: number | string | null;
  volume_step?: number | string | null;
  success?: boolean;
  message?: string;
  [key: string]: unknown;
}


export interface MarketInstrument {
  id?: number | string;
  symbol: string;
  name?: string | null;
  exchange?: string | null;
  market?: string | null;
  instrument_type?: string | null;
  asset_class?: string | null;
  base_currency?: string | null;
  quote_currency?: string | null;
  account_currency?: string | null;
  currency_symbol?: string | null;
  price_unit_name?: string | null;
  quantity_mode?: string | null;
  contract_size?: number | string | null;
  tick_size?: number | string | null;
  tick_value_per_lot?: number | string | null;
  pip_size?: number | string | null;
  min_quantity?: number | string | null;
  max_quantity?: number | string | null;
  quantity_step?: number | string | null;
  min_lot?: number | string | null;
  max_lot?: number | string | null;
  lot_step?: number | string | null;
  lot_size?: number | string | null;
  price_precision?: number | string | null;
  quantity_precision?: number | string | null;
  broker_symbol?: string | null;
  is_tradeable_live?: boolean | null;
  is_active?: boolean | null;
  [key: string]: unknown;
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


export interface CTraderTradingAccount {
  ctrader_account_id?: string | null;
  account_number?: string | null;
  broker_name?: string | null;
  account_type?: string | null;
  balance?: number | string | null;
  equity?: number | string | null;
  margin?: number | string | null;
  free_margin?: number | string | null;
  currency?: string | null;
  leverage?: number | string | null;
  raw?: Record<string, unknown>;
}

export interface CTraderAccountsResponse {
  broker_account: BrokerAccount;
  accounts: CTraderTradingAccount[];
  selected_account?: CTraderTradingAccount | null;
}

export interface BrokerSyncResponse {
  broker_account: BrokerAccount;
  connection?: BrokerConnectionResult;
  accounts?: CTraderTradingAccount[];
  selected_account?: CTraderTradingAccount | null;
  requires_account_selection?: boolean;
  symbols_synced?: number;
  symbols_preview?: Record<string, unknown>[];
}

export interface CTraderDemoOrderRequest {
  symbol: string;
  side: "BUY" | "SELL";
  volume: string;
  stop_loss?: string | null;
  take_profit?: string | null;
  client_order_id?: string | null;
  comment?: string | null;
}

export interface CTraderDemoOrderResponse {
  order_id?: string | null;
  status: string;
  symbol: string;
  side: string;
  volume: string;
  broker_account?: BrokerAccount;
  execution_log_id?: string;
  message?: string;
}

export interface BrokerAccountPayload {
  broker_provider_id?: string | null;
  broker_name?: string;
  broker_code?: string | null;
  auth_type?: string | null;
  account_label: string;
  mode: LiveMode;
  status?: BrokerStatus;
  server_name?: string | null;
  login_id?: string | null;
  oauth_client_id?: string | null;
  encrypted_client_secret?: string | null;
  encrypted_api_key?: string | null;
  encrypted_api_secret?: string | null;
  encrypted_api_passphrase?: string | null;
  oauth_redirect_uri?: string | null;
  encrypted_password?: string | null;
  encrypted_token?: string | null;
  encrypted_refresh_token?: string | null;
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

export interface FundedLiveGuardState {
  status?: string | null;
  reason?: string | null;
  rule_date?: string | null;
  rule_timezone?: string | null;
  daily_reset_time?: string | null;
  balance?: number | string | null;
  equity?: number | string | null;
  daily_floor?: number | string | null;
  max_floor?: number | string | null;
  remaining_daily_capacity?: number | string | null;
  remaining_max_capacity?: number | string | null;
  account_return_pct?: number | string | null;
  risk_tier?: string | null;
  requested_risk_pct?: number | string | null;
  requested_risk_amount?: number | string | null;
  effective_risk_pct?: number | string | null;
  effective_risk_amount?: number | string | null;
  limiting_rule?: string | null;
  trading_days?: number;
  qualifying_days?: number;
  target_balance?: number | string | null;
  target_progress_pct?: number | string | null;
  target_reached_at?: string | null;
  payout_eligible_at?: string | null;
  payout_ready_at?: string | null;
  failed_at?: string | null;
  last_evaluated_at?: string | null;
}

export interface FundedLiveStatus {
  account_policy_type: "FUNDED";
  profile?: { id?: string | null; name?: string | null; provider_name?: string | null; challenge_type?: string | null; account_size?: number | string | null; account_currency?: string | null } | null;
  phase?: Record<string, any> | null;
  phase_number?: number | null;
  risk_mode?: FundedLiveRiskMode | string | null;
  risk_plan?: any[] | Record<string, any> | null;
  fixed_risk_pct?: number | string | null;
  safety_buffer_pct?: number | string | null;
  configured_max_risk_pct?: number | string | null;
  attach_mode?: FundedAttachMode | string | null;
  broker?: { balance?: number | string | null; equity?: number | string | null; free_margin?: number | string | null; currency?: string | null; fresh?: boolean; age_seconds?: number | string | null; synced_at?: string | null } | null;
  guard?: FundedLiveGuardState | null;
}

export interface FundedRiskPlanPayload {
  risk_mode: FundedLiveRiskMode;
  fixed_risk_pct?: number | null;
  safety_buffer_pct: number;
  configured_max_risk_pct?: number | null;
  risk_tiers: Array<{ id?: string | null; name: string; sort_order: number; min_account_return_pct?: number | null; max_account_return_pct?: number | null; risk_percent: number; is_active: boolean }>;
}

export interface StrategyDeployment {
  id: string;
  user_id?: string;
  strategy_id: string;
  broker_account_id?: string | null;
  name: string;
  instrument: string;
  broker_symbol?: string | null;
  instrument_key?: string | null;
  exchange?: string | null;
  segment?: string | null;
  product_type?: string | null;
  order_variety?: string | null;
  quantity_mode?: string | null;
  fixed_quantity?: number | string | null;
  max_quantity?: number | string | null;
  max_order_value?: number | string | null;
  square_off_time?: string | null;
  upstox_order_confirmed?: boolean;
  timeframe: string;
  mode: LiveMode;
  account_policy_type?: AccountPolicyType;
  funded_profile_id?: string | null;
  funded_profile_snapshot?: Record<string, any> | null;
  funded_risk_plan_snapshot?: any[] | Record<string, any> | null;
  funded_risk_mode?: FundedLiveRiskMode | string | null;
  funded_fixed_risk_pct?: number | string | null;
  funded_safety_buffer_pct?: number | string | null;
  funded_configured_max_risk_pct?: number | string | null;
  funded_phase_number?: number | null;
  funded_attach_mode?: FundedAttachMode | string | null;
  funded_initialization_json?: Record<string, any> | null;
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
  auto_runner_enabled?: boolean;
  last_runner_at?: string | null;
  next_run_at?: string | null;
  last_runner_wakeup_at?: string | null;
  last_processed_candle_time?: string | null;
  runner_interval_mode?: string | null;
  broker_delay_seconds?: number | null;
  missed_candle_retry_seconds?: number | null;
  last_broker_sync_at?: string | null;
  live_sync_enabled?: boolean;
  live_sync_interval_seconds?: number;
  last_live_sync_at?: string | null;
  live_sync_error_count?: number;
  live_sync_last_error?: string | null;
  live_approved?: boolean;
  live_approved_at?: string | null;
  runner_error_count?: number;
  runner_last_error?: string | null;
  runner_stale?: boolean;
  mt5_demo_max_lot?: number | string | null;
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
  broker_symbol?: string | null;
  instrument_key?: string | null;
  exchange?: string | null;
  segment?: string | null;
  product_type?: string | null;
  order_variety?: string | null;
  quantity_mode?: string | null;
  fixed_quantity?: number | string | null;
  max_quantity?: number | string | null;
  max_order_value?: number | string | null;
  square_off_time?: string | null;
  upstox_order_confirmed?: boolean;
  timeframe: string;
  mode: LiveMode;
  account_policy_type?: AccountPolicyType;
  funded_profile_id?: string | null;
  funded_phase_number?: number | null;
  funded_risk_mode?: FundedLiveRiskMode | null;
  funded_fixed_risk_pct?: number | null;
  funded_safety_buffer_pct?: number;
  funded_configured_max_risk_pct?: number | null;
  funded_attach_mode?: FundedAttachMode | null;
  funded_initialization_json?: Record<string, any> | null;
  capital?: number;
  risk_per_trade: number;
  rr_ratio: number;
  price_risk_pct: number;
  max_daily_loss: number;
  max_trades_per_day: number;
  max_open_positions: number;
  allow_short: boolean;
  auto_trade_enabled: boolean;
  auto_runner_enabled?: boolean;
  last_runner_at?: string | null;
  next_run_at?: string | null;
  last_runner_wakeup_at?: string | null;
  last_processed_candle_time?: string | null;
  runner_interval_mode?: string | null;
  broker_delay_seconds?: number | null;
  missed_candle_retry_seconds?: number | null;
  last_broker_sync_at?: string | null;
  live_sync_enabled?: boolean;
  live_sync_interval_seconds?: number;
  last_live_sync_at?: string | null;
  live_sync_error_count?: number;
  live_sync_last_error?: string | null;
  live_approved?: boolean;
  live_approved_at?: string | null;
  runner_error_count?: number;
  runner_last_error?: string | null;
  runner_stale?: boolean;
  mt5_demo_max_lot?: number | string | null;
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
  raw_payload?: Record<string, unknown> | null;
  created_at?: string;
}


export interface BrokerOrderEvent {
  id: string;
  broker_provider_code: string;
  broker_account_id?: string | null;
  deployment_id?: string | null;
  broker_order_id?: string | null;
  event_type: string;
  raw_payload?: Record<string, unknown>;
  processed: boolean;
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
  broker_position_id?: string | null;
  broker_opened_at?: string | null;
  broker_opened_at_raw?: string | null;
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
  account_currency?: string | null;
  balance?: number | string | null;
  equity: number | string;
  realized_pnl: number | string;
  unrealized_pnl: number | string;
  free_margin?: number | string | null;
  effective_capital?: number | string | null;
  effective_capital_source?: string | null;
  today_realized_pnl?: number | string;
  today_unrealized_pnl?: number | string;
  today_pnl: number | string;
  open_positions: number;
  open_positions_count: number;
  orders_today: number;
  orders_count_today: number;
  signals_today: number;
  signals_count_today: number;
  total_orders: number;
  total_signals: number;
  source?: string;
  broker_synced?: boolean;
  broker_pnl_source?: string | null;
  broker_deal_count?: number | null;
  broker_sync_warning?: string | null;
}

export interface LiveDeploymentSummaryDeployment {
  id: string;
  name: string;
  strategy_id: string;
  strategy_name: string;
  instrument: string;
  broker_symbol?: string | null;
  instrument_key?: string | null;
  exchange?: string | null;
  segment?: string | null;
  product_type?: string | null;
  order_variety?: string | null;
  quantity_mode?: string | null;
  fixed_quantity?: number | string | null;
  max_quantity?: number | string | null;
  max_order_value?: number | string | null;
  square_off_time?: string | null;
  upstox_order_confirmed?: boolean;
  timeframe: string;
  mode: LiveMode;
  account_policy_type?: AccountPolicyType;
  funded_profile_id?: string | null;
  funded_phase_number?: number | null;
  funded_risk_mode?: FundedLiveRiskMode | string | null;
  funded_fixed_risk_pct?: number | string | null;
  funded_safety_buffer_pct?: number | string | null;
  funded_configured_max_risk_pct?: number | string | null;
  funded_attach_mode?: FundedAttachMode | string | null;
  status: DeploymentStatus;
  auto_trade_enabled: boolean;
  auto_runner_enabled?: boolean;
  last_runner_at?: string | null;
  next_run_at?: string | null;
  last_runner_wakeup_at?: string | null;
  last_processed_candle_time?: string | null;
  runner_interval_mode?: string | null;
  broker_delay_seconds?: number | null;
  missed_candle_retry_seconds?: number | null;
  last_broker_sync_at?: string | null;
  live_sync_enabled?: boolean;
  live_sync_interval_seconds?: number;
  last_live_sync_at?: string | null;
  live_sync_error_count?: number;
  live_sync_last_error?: string | null;
  live_approved?: boolean;
  live_approved_at?: string | null;
  runner_error_count?: number;
  runner_last_error?: string | null;
  runner_stale?: boolean;
  last_signal_at?: string | null;
  last_heartbeat_at?: string | null;
  webhook_url?: string;
  tradingview_secret?: string | null;
  example_payload?: Record<string, unknown>;
}


export interface BrokerSyncSummary {
  mode?: string;
  managed_by?: string;
  last_broker_sync_at?: string | null;
  last_live_sync_at?: string | null;
  live_sync_enabled?: boolean;
  live_sync_interval_seconds?: number;
  live_sync_error_count?: number;
  live_sync_last_error?: string | null;
  broker_connection_status?: string | null;
  open_broker_positions?: number | null;
  local_tracked_positions?: number | null;
  sync_mismatch_warning?: boolean;
  latest_sync_error?: string | null;
  warning?: string | null;
}

export interface LiveDeploymentSummary {
  deployment?: LiveDeploymentSummaryDeployment;
  broker?: SafeBrokerStatus | null;
  funded?: FundedLiveStatus | null;
  metrics?: LiveDeploymentSummaryMetrics;
  latest_signal?: LiveSignal | null;
  latest_order?: LiveOrder | null;
  open_positions?: LivePosition[];
  recent_orders?: LiveOrder[];
  recent_signals?: LiveSignal[];
  recent_logs?: LiveTradeLog[];
  position_events?: LiveTradeLog[];
  broker_sync?: BrokerSyncSummary | null;
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


export type LiveReadinessStatus = "READY" | "NOT_READY" | "WARNING";
export type LiveReadinessCheckStatus = "PASS" | "FAIL" | "WARNING";

export interface LiveReadinessCheck {
  key: string;
  label: string;
  status: LiveReadinessCheckStatus;
  message: string;
  action_label?: string | null;
  action_href?: string | null;
}

export interface LiveReadiness {
  overall_status: LiveReadinessStatus;
  ready_to_auto_trade: boolean;
  summary: string;
  checks: LiveReadinessCheck[];
}


export interface LiveCompatibilityCheck {
  name: string;
  status: LiveReadinessCheckStatus;
  message: string;
  data?: Record<string, unknown>;
}

export interface LiveCompatibilityResult {
  status: LiveReadinessCheckStatus;
  summary: string;
  checks: LiveCompatibilityCheck[];
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
  auto_runner_enabled?: boolean;
  last_runner_at?: string | null;
  next_run_at?: string | null;
  last_runner_wakeup_at?: string | null;
  last_processed_candle_time?: string | null;
  runner_interval_mode?: string | null;
  broker_delay_seconds?: number | null;
  missed_candle_retry_seconds?: number | null;
  last_broker_sync_at?: string | null;
  live_sync_enabled?: boolean;
  live_sync_interval_seconds?: number;
  last_live_sync_at?: string | null;
  live_sync_error_count?: number;
  live_sync_last_error?: string | null;
  live_approved?: boolean;
  live_approved_at?: string | null;
  runner_error_count?: number;
  runner_last_error?: string | null;
  runner_stale?: boolean;
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
  recent_broker_events?: BrokerOrderEvent[];
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
  broker_position_id?: string | null;
  broker_opened_at?: string | null;
  broker_opened_at_raw?: string | null;
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
  broker_symbol?: string | null;
  instrument_key?: string | null;
  timeframe: string;
  requested_count?: number;
  stored_count: number;
  upserted_count?: number;
  latest_candle_time?: string | null;
  latest_candle_close_time?: string | null;
  latest_ingested_at?: string | null;
  ingestion_latency_seconds?: number | null;
  candle_time_semantics?: "OPEN_TIME" | string;
  server_time?: string | null;
  next_closed_candle_expected_at?: string | null;
  latest_close?: number | string | null;
  candles: LiveMarketCandle[];
}

export interface LiveLatencyTrace {
  id: string;
  trace_id: string;
  deployment_id: string;
  broker_account_id?: string | null;
  signal_id?: string | null;
  order_id?: string | null;
  candle_open_time: string;
  expected_close_at: string;
  provider: string;
  environment?: string | null;
  symbol: string;
  timeframe: string;
  source?: string | null;
  status: string;
  signal_type?: string | null;
  error_message?: string | null;
  timeline: Record<string, string | null>;
  metrics: Record<string, number>;
  metadata?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface LiveLatencyRollupItem {
  count: number;
  p50?: number | null;
  p95?: number | null;
  min?: number | null;
  max?: number | null;
}

export interface LiveLatencyResponse {
  latest?: LiveLatencyTrace | null;
  recent: LiveLatencyTrace[];
  rollup: Record<string, LiveLatencyRollupItem>;
  sample_size: number;
}

export interface LiveWorkerHealth {
  role?: string;
  worker_id?: string;
  status?: string;
  heartbeat_at?: string;
  last_error?: string | null;
  feeds?: number;
  feed_deployments?: string[];
  connections?: Record<string, {
    environment?: string;
    state?: string;
    connected?: boolean;
    connected_at?: string | null;
    last_rx_at?: string | null;
    last_tx_at?: string | null;
    reconnect_count?: number;
    last_connection_error?: string | null;
    authorized_accounts?: number;
    trendbar_subscriptions?: number;
  }>;
  [key: string]: unknown;
}

export interface LivePipelineHealth {
  event_pipeline_enabled: boolean;
  market_worker_enabled: boolean;
  strategy_stream_enabled: boolean;
  reconcile_worker_enabled: boolean;
  persistent_ctrader_enabled: boolean;
  legacy_runner_enabled: boolean;
  deployment_running: boolean;
  auto_runner_enabled: boolean;
  auto_trade_enabled: boolean;
  workers: Record<string, LiveWorkerHealth | null>;
  redis_available?: boolean;
  disabled_flags?: string[];
  deployment_environment?: string;
  connection?: {
    environment?: string;
    state?: string;
    connected?: boolean;
    reconnect_count?: number;
    [key: string]: unknown;
  } | null;
  redis_error?: string | null;
  market_data?: {
    stored_count?: number;
    latest_candle_time?: string | null;
    latest_source?: string | null;
  };
}

export interface StrategyRunnerInfo {
  last_run_at?: string | null;
  last_candle_time?: string | null;
  last_signal?: string | null;
  latest_runner_log?: string | null;
  latest_runner_status?: string | null;
  latest_order_status?: string | null;
  latest_order_error?: string | null;
  latest_broker_order_id?: string | null;
  auto_runner_enabled?: boolean;
  last_processed_candle_time?: string | null;
  last_broker_sync_at?: string | null;
  live_sync_enabled?: boolean;
  live_sync_interval_seconds?: number;
  last_live_sync_at?: string | null;
  live_sync_error_count?: number;
  live_sync_last_error?: string | null;
  live_approved?: boolean;
  live_approved_at?: string | null;
  runner_error_count?: number;
  runner_last_error?: string | null;
  runner_stale?: boolean;
  last_entry_plan?: Record<string, unknown> | null;
  last_risk_preview?: Record<string, unknown> | null;
  last_execution_decision?: string | null;
}

export interface FullDryTestStep {
  name: string;
  status: "PASS" | "FAIL" | "WARNING" | string;
  message: string;
  data?: Record<string, unknown>;
}

export interface FullDryTestResponse {
  success: boolean;
  deployment_id: string;
  strategy_name?: string | null;
  latest_candle_time?: string | null;
  signal?: SignalType | string | null;
  steps: FullDryTestStep[];
  entry_plan?: Record<string, unknown> | null;
  risk_preview?: Record<string, unknown> | null;
  duplicate?: boolean;
  final_action: "HOLD" | "WOULD_PLACE_PAPER_ORDER" | "WOULD_PLACE_DEMO_ORDER" | "REJECTED" | string;
  message: string;
}


export interface FinalQaCheck {
  key: string;
  label: string;
  status: "PASS" | "WARNING" | "FAIL" | string;
  message: string;
  data?: Record<string, unknown>;
}

export interface FinalQaResult {
  overall_status: "PASS" | "WARNING" | "FAIL" | string;
  summary: string;
  checks: FinalQaCheck[];
  deployment_id?: string;
  mode?: string;
  last_results?: Record<string, unknown>;
  debug_summary?: Record<string, unknown>;
}

export interface QaOrderTestResult {
  status: string;
  message?: string;
  order_id?: string | null;
  position_id?: string | null;
  broker_order_id?: string | null;
  side?: string;
  lot_or_quantity?: number | string;
  lot_or_quantity_sent?: number | string;
  entry?: number | string;
  SL?: number | string;
  TP?: number | string;
  risk?: number | string | null;
  risk_estimate?: number | string | null;
  expected_reward?: number | string | null;
  warning?: string | null;
  broker_response?: Record<string, unknown>;
  preview?: Record<string, unknown>;
}

export interface RunStrategyResponse {
  success: boolean;
  deployment_id: string;
  strategy_name?: string | null;
  latest_candle_time?: string | null;
  signal?: SignalType | string | null;
  executed: boolean;
  order_id?: string | null;
  broker_order_id?: string | null;
  signal_id?: string | null;
  duplicate?: boolean;
  message: string;
  latest_runner_log?: string | null;
  order_status?: string | null;
  error_message?: string | null;
  symbol?: string | null;
}

export interface PlatformTradingSettings {
  id: string;
  paper_trading_enabled: boolean;
  demo_trading_enabled: boolean;
  live_trading_enabled: boolean;
  global_kill_switch: boolean;
  max_global_demo_orders_per_day?: number | null;
  max_user_demo_orders_per_day?: number | null;
  upstox_order_execution_enabled?: boolean;
  broker_auto_sync_enabled?: boolean;
  min_broker_sync_interval_seconds?: number;
  default_broker_sync_interval_seconds?: number;
  max_broker_sync_interval_seconds?: number;
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
  upstox_order_execution_enabled?: boolean;
  broker_auto_sync_enabled?: boolean;
  min_broker_sync_interval_seconds?: number;
  default_broker_sync_interval_seconds?: number;
  max_broker_sync_interval_seconds?: number;
}

// Optional safety fields added by Phase 11.
export interface AdminLiveDeploymentListResponseWithSettings extends AdminLiveDeploymentListResponse {
  settings?: PlatformTradingSettings;
}

export interface BrokerProvider {
  id: string;
  code: string;
  name: string;
  display_name?: string | null;
  market_type: "FOREX" | "INDIAN_EQUITY" | "CRYPTO" | "MULTI" | string;
  broker_category?: string | null;
  auth_type: "PASSWORD" | "OAUTH2" | "API_KEY" | "API_KEY_SECRET" | "MT5_AGENT" | string;
  supports_paper: boolean;
  supports_demo: boolean;
  supports_live: boolean;
  supports_market_data: boolean;
  supports_orders: boolean;
  supports_websocket: boolean;
  is_enabled: boolean;
  is_live_enabled?: boolean;
  admin_notes?: string | null;
  description?: string | null;
  setup_mode?: string | null;
  config_schema?: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
}

export interface BrokerProviderPayload {
  code: string;
  name: string;
  display_name?: string | null;
  market_type: string;
  auth_type: string;
  supports_paper?: boolean;
  supports_demo?: boolean;
  supports_live?: boolean;
  supports_market_data?: boolean;
  supports_orders?: boolean;
  supports_websocket?: boolean;
  is_enabled?: boolean;
  is_live_enabled?: boolean;
  admin_notes?: string | null;
  description?: string | null;
  setup_mode?: string | null;
  config_schema?: Record<string, unknown> | null;
}


export interface LiveSyncStatus {
  live_sync_enabled: boolean;
  live_sync_interval_seconds: number;
  last_live_sync_at?: string | null;
  last_broker_sync_at?: string | null;
  live_sync_error_count: number;
  live_sync_last_error?: string | null;
  platform_auto_sync_enabled: boolean;
}



export interface LiveOrderPreview {
  validation_status?: string;
  status?: string;
  rejected_reason?: string | null;
  reason?: string | null;
  missing_fields?: string[];
  instrument_not_ready_message?: string | null;
  broker?: string;
  symbol?: string;
  side?: string;
  quantity_mode?: string;
  final_lot_size?: number | string | null;
  final_quantity?: number | string | null;
  risk_amount?: number | string | null;
  actual_risk_amount?: number | string | null;
  entry_price?: number | string | null;
  latest_price?: number | string | null;
  preview_mode?: string | null;
  stop_loss?: number | string | null;
  target?: number | string | null;
  expected_reward_amount?: number | string | null;
  account_currency?: string | null;
  currency_symbol?: string | null;
  broker_symbol?: string | null;
  strategy_stop_loss?: number | string | null;
  strategy_target?: number | string | null;
  strategy_sltp_received?: boolean;
  entry_plan?: Record<string, unknown>;
  risk_metadata?: Record<string, unknown>;
  effective_capital?: number | string | null;
  effective_capital_source?: string | null;
  capital_warning?: string | null;
  broker_payload_preview?: Record<string, unknown>;
  broker_order_payload_preview?: Record<string, unknown>;
  risk_engine?: Record<string, unknown>;
  instrument_spec_snapshot?: Record<string, unknown>;
  runtime_config_snapshot?: Record<string, unknown>;
}
