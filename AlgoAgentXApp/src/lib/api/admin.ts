import axiosInstance from "../axios";
import { HEAVY_API_TIMEOUT_MS } from "../api-timeouts";

const unwrap = <T>(response: any): T => {
  const payload = response?.data;
  return payload?.success ? payload.data : payload;
};

export interface AdminMetrics {
  users?: { total: number; active: number; recent: any[] };
  payments?: { total: number; revenue: number; recent: any[] };
  credits?: { total: number; active_subscriptions: number; used?: number; available?: number };
  subscriptions?: { total: number; active: number };
  strategies?: { pending: number };
  backtests?: { total: number };
  orders?: { total: number; recent: any[] };
}

export interface AdminDashboardSummary {
  users: {
    total_users: number;
    active_users: number;
    admin_users: number;
    new_users_today: number;
    new_users_7d: number;
  };
  billing: {
    total_revenue: number;
    paid_revenue: number;
    refunded_amount: number;
    failed_amount: number;
    total_orders: number;
    paid_orders: number;
    failed_orders: number;
    refunded_orders: number;
    active_subscriptions: number;
    expired_subscriptions: number;
    total_credits_issued: number;
    total_credits_used: number;
  };
  strategies: {
    total_strategies: number;
    published_strategies: number;
    private_strategies: number;
    pending_strategy_requests: number;
    approved_strategy_requests: number;
    rejected_strategy_requests: number;
  };
  backtests: {
    total_backtests: number;
    completed_backtests: number;
    failed_backtests: number;
    running_backtests: number;
    backtests_today: number;
    backtests_7d: number;
  };
  brokers: {
    total_broker_accounts: number;
    connected_broker_accounts: number;
    failed_broker_accounts: number;
    broker_breakdown: any[];
  };
  live_trading: {
    total_deployments: number;
    running_deployments: number;
    paused_deployments: number;
    stopped_deployments: number;
    live_sync_enabled_users: number;
    approval_required_users: number;
    orders_today: number;
    orders_total: number;
    successful_orders: number;
    failed_orders: number;
    open_positions: number;
  };
  system: {
    market_data_symbols: number;
    market_data_rows: number;
    last_market_data_sync: string | null;
    latest_execution_log_at: string | null;
    api_health: string;
  };
  recent: {
    recent_users: any[];
    recent_payments: any[];
    recent_orders: any[];
    recent_backtests: any[];
    recent_live_deployments: any[];
    recent_broker_connections: any[];
    recent_strategy_requests: any[];
  };
  generated_at?: string;
}

export interface BacktestPricingDateRangeBucket {
  max_days: number | null;
  multiplier: number;
}

export interface BacktestPricingTimeframeBucket {
  max_minutes: number | null;
  multiplier: number;
}

export interface BacktestPricingRuleSetSummary {
  id: string;
  name: string;
  version: string;
  description?: string | null;
  is_active: boolean;
  is_locked: boolean;
  base_cost: number;
  min_credit_charge: number;
  max_credit_charge?: number | null;
  updated_at?: string | null;
  created_at?: string | null;
}

export interface BacktestPricingActiveRuleSet extends BacktestPricingRuleSetSummary {
  range_days_step: number;
  date_range_buckets: BacktestPricingDateRangeBucket[];
  timeframe_multipliers: BacktestPricingTimeframeBucket[];
  strategy_complexity_enabled: boolean;
  strategy_complexity_step: number;
  strategy_complexity_cap: number;
  plan_discounts: Record<string, number>;
  is_db_configured?: boolean;
}

export interface BacktestPricingConfigResponse {
  active: BacktestPricingActiveRuleSet;
  items: BacktestPricingRuleSetSummary[];
  notes?: string;
}

export interface BacktestPricingUpdatePayload {
  name?: string;
  version?: string;
  description?: string;
  base_cost?: number;
  range_days_step?: number;
  min_credit_charge?: number;
  max_credit_charge?: number | null;
  date_range_buckets?: BacktestPricingDateRangeBucket[];
  timeframe_multipliers?: BacktestPricingTimeframeBucket[];
  strategy_complexity_enabled?: boolean;
  strategy_complexity_step?: number;
  strategy_complexity_cap?: number;
  plan_discounts?: Record<string, number>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip?: number;
  limit?: number;
  page?: number;
  page_size?: number;
}

export interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  fullname?: string;
  mobile?: string;
  plan?: string;
  billing_period?: string;
  subscription_status?: string;
  credits?: number;
}

export interface Payment {
  id: string;
  user_id: string;
  user_email?: string;
  user_name?: string;
  amount: number;
  currency: string;
  status: string;
  payment_method: string;
  purpose?: string;
  transaction_id?: string;
  billing_order_id?: string;
  razorpay_order_id?: string;
  razorpay_payment_id?: string;
  verified_at?: string;
  failure_reason?: string;
  is_reconciled?: boolean;
  reconciliation?: {
    is_reconciled?: boolean;
    status?: string;
    provider?: string;
    purpose?: string;
  };
  created_at: string;
  updated_at?: string;
}

export interface Subscription {
  id: string;
  user_id: string;
  plan_id: string;
  plan_code: string;
  billing_period: string;
  price_inr: number;
  included_credits: number;
  included_credits_total?: number;
  included_credits_remaining?: number;
  status: string;
  start_at: string;
  end_at: string;
  next_credit_refill_at?: string;
  last_credit_refill_at?: string;
  user_email?: string;
  user_name?: string;
  renews?: boolean;
  created_at: string;
  updated_at?: string;
}

export interface CreditBalance {
  user_id: string;
  user_email?: string;
  user_name?: string;
  balance: number;
  updated_at?: string;
}

export interface CreditTransaction {
  id: string;
  user_id: string;
  user_email?: string;
  user_name?: string;
  credits?: number;
  type: string;
  source?: string;
  source_type?: string;
  actor_user_id?: string;
  reason?: string;
  balance_after?: number;
  credits_added?: number;
  credits_used?: number;
  remaining_credits?: number;
  created_at: string;
}

export interface SupportTicketReply {
  id: string;
  ticket_id: string;
  user_id?: string | null;
  admin_id?: string | null;
  message: string;
  created_at: string;
}

export interface SupportTicket {
  id: string;
  user_id: string;
  user_email: string;
  title: string;
  message: string;
  status: string;
  category?: string | null;
  priority?: string | null;
  created_at: string;
  updated_at: string;
  replies?: SupportTicketReply[];
}

export interface Order {
  id: string;
  user_id: string;
  order_number: string;
  order_type?: string;
  source_type?: string;
  status: string;
  linked_payment_id?: string;
  linked_payment_status?: string;
  reconciliation_status?: string;
  total_amount: number;
  currency: string;
  payment_method: string;
  transaction_id?: string;
  created_at: string;
  updated_at?: string;
  user_email: string;
  user_name: string;
}


export interface AdminBacktestEngineSource {
  engine_path: string;
  source_code: string;
  supporting_files: Array<{ path: string; content: string }>;
}

export interface AdminBacktest {
  id: string;
  strategy_id?: string;
  strategy_name?: string;
  instrument_symbol?: string;
  user_id: string;
  user_email?: string;
  user_name?: string;
  timeframe?: string;
  total_return?: number;
  net_profit?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
  total_trades?: number;
  credit_cost?: number;
  effective_credit_cost?: number;
  included_debited?: number;
  wallet_debited?: number;
  included_refunded?: number;
  wallet_refunded?: number;
  refund_total?: number;
  charge_status?: "not_charged" | "charged" | "partially_refunded" | "refunded" | string;
  debit_transaction_id?: string | null;
  refund_transaction_ids?: string[];
  status?: string;
  created_at: string;
}

export interface AdminBacktestListResponse {
  items: AdminBacktest[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface OrderItem {
  id: string;
  order_id: string;
  product_type: string;
  product_id: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  product_name?: string;
  product_description?: string;
}

export type StrategyRequestStatus =
  | "UNDER_DEVELOPMENT"
  | "NEEDS_CLARIFICATION"
  | "REJECTED"
  | "DEPLOYED";

export type StrategyVisibility = "PUBLIC" | "PRIVATE";

export interface StrategyRequest {
  id: string;
  title: string;
  name?: string;
  strategy_type?: string | null;
  strategyType?: string | null;
  market?: string | null;
  timeframe?: string | null;
  indicators?: Record<string, any> | null;
  entry_rules?: string | null;
  exit_rules?: string | null;
  risk_rules?: string | null;
  notes?: string | null;
  source_code?: string | null;
  sourceCode?: string | null;
  description?: string | null;
  status: StrategyRequestStatus | string;
  user_id?: string;
  user_email?: string | null;
  user_name?: string | null;
  admin_notes?: string | null;
  assigned_to?: string | null;
  deployed_strategy_id?: string | null;
  deployedStrategyId?: string | null;
  created_at: string;
  createdAt?: string | null;
  updated_at?: string | null;
  updatedAt?: string | null;
  workflow?: StrategyWorkflowStatus | null;
  version_count?: number | null;
  lifecycle_status?: string | null;
  lifecycleStatus?: string | null;
  is_deployable_paper?: boolean;
  isDeployablePaper?: boolean;
  is_deployable_demo?: boolean;
  isDeployableDemo?: boolean;
  is_live_approved?: boolean;
  isLiveApproved?: boolean;
  verified_at?: string | null;
  verifiedAt?: string | null;
  sandbox_passed_at?: string | null;
  sandboxPassedAt?: string | null;
  paper_enabled_at?: string | null;
  paperEnabledAt?: string | null;
  demo_enabled_at?: string | null;
  demoEnabledAt?: string | null;
  live_approved_at?: string | null;
  liveApprovedAt?: string | null;
  approved_by?: string | null;
  approvedBy?: string | null;
}


export interface AdminStrategySandboxResult {
  strategy_id: string;
  strategy_name?: string;
  summary: {
    initial_capital: number;
    final_capital: number;
    net_profit: number;
    return_pct: number;
    win_rate: number;
    max_drawdown: number;
    sharpe_ratio: number;
    profit_factor: number;
    avg_win: number;
    avg_loss: number;
    expectancy: number;
    total_trades: number;
  };
  trades: Array<{
    entry_time?: string;
    exit_time?: string;
    side?: string;
    quantity?: number;
    entry_price?: number;
    exit_price?: number;
    pnl?: number;
    exit_type?: string;
    stop_loss?: number | null;
    target?: number | null;
    risk_points?: number | null;
    reward_points?: number | null;
    rr_ratio?: number | null;
    risk_amount?: number | null;
    reward_amount?: number | null;
    r_multiple?: number | null;
    signal_reason?: string | null;
  }>;
  equity_curve: Array<{ timestamp?: string; equity: number }>;
  pnl_calendar: Array<{ date?: string; pnl: number }>;
}

export interface StrategyWorkflowCheck {
  ok?: boolean;
  message?: string;
  checked_at?: string;
  source_hash?: string;
  sample_result?: any;
  summary?: any;
}

export interface StrategyWorkflowStatus {
  validation?: StrategyWorkflowCheck;
  sandbox?: StrategyWorkflowCheck;
}

export interface StrategyVersion {
  version_id: string;
  captured_at: string;
  editor_user_id?: string | null;
  reason?: string | null;
  name?: string | null;
  description?: string | null;
  visibility?: string | null;
  payload?: Record<string, any> | null;
}

export interface StrategyPreset {
  key: string;
  name: string;
  config: Record<string, any>;
}

export interface StrategyRuntimePreset {
  id: string;
  strategy_id?: string;
  strategyId?: string;
  name: string;
  description?: string | null;
  config_json?: Record<string, any>;
  configJson?: Record<string, any>;
  risk_label?: string | null;
  riskLabel?: string | null;
  is_default?: boolean;
  isDefault?: boolean;
  is_active?: boolean;
  isActive?: boolean;
  created_at?: string | null;
  createdAt?: string | null;
  updated_at?: string | null;
  updatedAt?: string | null;
}

export interface ImplementedStrategy {
  id: string;
  name: string;
  description?: string | null;
  default_runtime_config?: Record<string, any> | null;
  defaultRuntimeConfig?: Record<string, any> | null;
  runtime_config_schema?: Record<string, any> | null;
  runtimeConfigSchema?: Record<string, any> | null;
  supports_runtime_config?: boolean;
  supportsRuntimeConfig?: boolean;
  config_version?: number;
  configVersion?: number;
  strategy_type?: string | null;
  strategyType?: string | null;
  market?: string | null;
  timeframe?: string | null;
  entry_rules?: string | null;
  exit_rules?: string | null;
  confirmation_rules?: string | null;
  risk_rules?: string | null;
  invalidation_rules?: string | null;
  trade_management_rules?: string | null;
  notes?: string | null;
  source_code?: string | null;
  sourceCode?: string | null;
  winRate?: number | null;
  sharpeRatio?: number | null;
  maxDrawdown?: number | null;
  totalTrades?: number | null;
  profitFactor?: number | null;
  parameters?: Record<string, any> | null;
  visibility?: string | null;
  status?: string | null;
  source_request_id?: string | null;
  sourceRequestId?: string | null;
  created_by?: string | null;
  published_by?: string | null;
  created_at: string;
  createdAt?: string | null;
  updated_at?: string | null;
  updatedAt?: string | null;
  workflow?: StrategyWorkflowStatus | null;
  version_count?: number | null;
  lifecycle_status?: string | null;
  lifecycleStatus?: string | null;
  is_deployable_paper?: boolean;
  isDeployablePaper?: boolean;
  is_deployable_demo?: boolean;
  isDeployableDemo?: boolean;
  is_live_approved?: boolean;
  isLiveApproved?: boolean;
  verified_at?: string | null;
  verifiedAt?: string | null;
  sandbox_passed_at?: string | null;
  sandboxPassedAt?: string | null;
  paper_enabled_at?: string | null;
  paperEnabledAt?: string | null;
  demo_enabled_at?: string | null;
  demoEnabledAt?: string | null;
  live_approved_at?: string | null;
  liveApprovedAt?: string | null;
  approved_by?: string | null;
  approvedBy?: string | null;
}

export interface StrategyRequestsResponse {
  items: StrategyRequest[];
  implemented: ImplementedStrategy[];
  total: number;
  skip: number;
  limit: number;
  strategy_total?: number;
  strategy_skip?: number;
  strategy_limit?: number;
}

export interface StrategyListResponse {
  items: ImplementedStrategy[];
  total: number;
  skip: number;
  limit: number;
}

export type MarketDataFreshnessStatus = "fresh" | "warning" | "stale" | "no_data";

export interface AdminMarketDataInstrument {
  id: number;
  symbol: string;
  exchange: string;
  market: string;
  instrument_type?: string | null;
  broker_symbol?: string | null;
  upstox_instrument_key?: string | null;
}

export interface AdminMarketDataCatalog {
  instruments: AdminMarketDataInstrument[];
  timeframes: string[];
}

export interface AdminMarketDataDatasetSummary {
  total_datasets: number;
  total_records: number;
  fresh_count: number;
  warning_count: number;
  stale_count: number;
  no_data_count: number;
}

export interface AdminMarketDataDataset {
  instrument_id: number;
  instrument_symbol: string;
  exchange: string;
  market: string;
  timeframe: string;
  first_candle_at?: string | null;
  last_candle_at?: string | null;
  latest_candle_at?: string | null;
  latest_candle_date?: string | null;
  total_records: number;
  record_count?: number;
  freshness_status: MarketDataFreshnessStatus;
  status?: "FRESH" | "WARNING" | "STALE" | "NO_DATA";
  freshness_age_hours?: number | null;
  expected_freshness_status?: "FRESH" | "WARNING" | "STALE" | "NO_DATA";
  expected_fresh_hours?: number | null;
  warning_after_hours?: number | null;
  missing_from_date?: string | null;
  market_rule?: string | null;
  is_stale: boolean;
}

export interface AdminMarketDataDatasetListResponse {
  items: AdminMarketDataDataset[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: AdminMarketDataDatasetSummary;
}

export interface AdminMarketDataJobRecord {
  job_id: string;
  job_type: "market_data_import" | "market_data_upload" | "market_data_refresh" | string;
  status: string;
  progress: number;
  message?: string | null;
  retry_count: number;
  max_retries: number;
  created_at?: string | null;
  updated_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  instrument_id?: number | null;
  timeframe?: string | null;
  source?: string | null;
  dataset_uri?: string | null;
  imported_rows?: number | null;
  invalid_rows?: number | null;
  has_invalid_data: boolean;
  error_message?: string | null;
}

export interface AdminMarketDataJobListResponse {
  items: AdminMarketDataJobRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminMarketDataImportPayload {
  instrument_id?: number;
  timeframe?: string;
  source?: string;
  dataset_uri?: string;
  note?: string;
  dry_run?: boolean;
  force?: boolean;
  metadata?: Record<string, any>;
}

export interface AdminMarketDataRefreshPayload {
  instrument_id?: number;
  timeframe?: string;
  source?: string;
  note?: string;
  force?: boolean;
  metadata?: Record<string, any>;
}

export interface AdminMarketDataJobEnqueueResponse {
  job_id: string;
  status: string;
  job_type: string;
  pipeline_ready: boolean;
  message: string;
  payload: Record<string, any>;
}

export interface AdminMarketDataFetchPayload {
  provider: string;
  instrument_id: number;
  symbol: string;
  instrument_key?: string;
  broker_account_id?: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  dry_run?: boolean;
}

export interface AdminMarketDataImportSummary {
  total_input_rows?: number;
  valid_rows?: number;
  invalid_rows?: number;
  duplicate_rows?: number;
  inserted_rows?: number;
  updated_rows?: number;
  skipped_rows?: number;
  min_timestamp?: string | null;
  max_timestamp?: string | null;
  errors_sample?: any[];
  errors?: any[];
  [key: string]: any;
}

export interface AdminMarketDataFetchResponse {
  provider: string;
  symbol: string;
  instrument_key?: string | null;
  instrument_id: number;
  timeframe: string;
  start_date?: string;
  end_date?: string;
  dry_run?: boolean;
  saved?: boolean;
  note?: string;
  summary: AdminMarketDataImportSummary;
}

export interface AdminMarketDataRefreshMissingPayload {
  provider: string;
  instrument_id: number;
  symbol: string;
  instrument_key?: string;
  broker_account_id?: string;
  timeframe: string;
  end_date?: string;
  dry_run?: boolean;
}

export interface AdminMarketDataRefreshMissingResponse extends AdminMarketDataFetchResponse {
  latest_existing_candle_at?: string;
  refresh_start_date?: string;
  refresh_end_date?: string;
}


export interface AdminMarketDataCsvUploadPayload {
  instrument_id: number;
  timeframe: string;
  source?: string;
  dry_run?: boolean;
  file: File;
}

export interface AdminMarketDataCsvUploadResponse {
  status: string;
  job_id?: string | null;
  instrument_id: number;
  timeframe: string;
  source: string;
  dry_run: boolean;
  filename?: string | null;
  summary: AdminMarketDataImportSummary;
}

export interface AdminStrategyCreatePayload {
  name: string;
  description?: string | null;
  strategy_type?: string | null;
  market?: string | null;
  timeframe?: string | null;
  entry_rules?: string | null;
  exit_rules?: string | null;
  confirmation_rules?: string | null;
  risk_rules?: string | null;
  invalidation_rules?: string | null;
  trade_management_rules?: string | null;
  notes?: string | null;
  source_code?: string | null;
  visibility?: StrategyVisibility;
  source_request_id?: string | null;
  created_by?: string | null;
  performance_metrics?: {
    winRate?: number | null;
    sharpeRatio?: number | null;
    maxDrawdown?: number | null;
    totalTrades?: number | null;
    profitFactor?: number | null;
  } | null;
  parameters?: Record<string, any> | null;
}

export interface AdminStrategyUpdatePayload {
  name?: string;
  description?: string | null;
  strategy_type?: string | null;
  market?: string | null;
  timeframe?: string | null;
  entry_rules?: string | null;
  exit_rules?: string | null;
  confirmation_rules?: string | null;
  risk_rules?: string | null;
  invalidation_rules?: string | null;
  trade_management_rules?: string | null;
  notes?: string | null;
  source_code?: string | null;
  visibility?: StrategyVisibility;
  source_request_id?: string | null;
  performance_metrics?: {
    winRate?: number | null;
    sharpeRatio?: number | null;
    maxDrawdown?: number | null;
    totalTrades?: number | null;
    profitFactor?: number | null;
  } | null;
  parameters?: Record<string, any> | null;
}

export interface DeployStrategyRequestPayload {
  strategy_id?: string;
  strategy_name?: string;
  strategy_description?: string;
  publish?: boolean;
  visibility?: StrategyVisibility;
  admin_notes?: string;
}

// Add these interfaces near the other admin interfaces
export interface AdminPricingPlan {
  id: string;
  code: string;
  billing_period: "NONE" | "MONTHLY" | "YEARLY";
  price_inr: number;
  included_credits: number;
  summary: string;
  daily_backtests: number;
  daily_ai_screener_runs: number;
  max_date_range_days: number;
  export_results: boolean;
  advanced_strategies: boolean;
  ai_screener_access: boolean;
  priority_support: boolean;
  dedicated_account_manager: boolean;
  features: Record<string, any>;
  is_active: boolean;
  created_at?: string;
}

export interface AdminPricingPlanPayload {
  code: string;
  billing_period: "NONE" | "MONTHLY" | "YEARLY";
  price_inr: number;
  included_credits: number;
  summary: string;
  daily_backtests: number;
  daily_ai_screener_runs: number;
  max_date_range_days: number;
  export_results: boolean;
  advanced_strategies: boolean;
  ai_screener_access: boolean;
  priority_support: boolean;
  dedicated_account_manager: boolean;
  is_active: boolean;
}


export interface MarketMasterAssetClass {
  id: number;
  code: string;
  label: string;
  description?: string | null;
  is_active: boolean;
}

export interface MarketMasterTimeframe {
  id: number;
  code: string;
  label: string;
  minutes?: number | null;
  is_intraday: boolean;
  is_active: boolean;
  display_order: number;
}

export type QuantityMode = "SHARES" | "LOTS" | "UNITS" | "CONTRACTS";

export interface MarketMasterInstrument {
  id: number;
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
  quantity_mode?: QuantityMode | string | null;
  contract_size?: number | null;
  tick_size?: number | null;
  tick_value_per_lot?: number | null;
  pip_size?: number | null;
  min_quantity?: number | null;
  max_quantity?: number | null;
  quantity_step?: number | null;
  min_lot?: number | null;
  max_lot?: number | null;
  lot_step?: number | null;
  lot_size?: number | null;
  price_precision?: number | null;
  quantity_precision?: number | null;
  broker_symbol?: string | null;
  is_tradeable_backtest: boolean;
  is_tradeable_live: boolean;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export type MarketMasterInstrumentPayload = Partial<Omit<MarketMasterInstrument, "id" | "created_at" | "updated_at">> & {
  symbol?: string;
};

export const adminApi = {

  getMarketMasterAssetClasses: async (): Promise<MarketMasterAssetClass[]> =>
    unwrap(await axiosInstance.get("/api/v1/admin/market-master/asset-classes")),

  getMarketMasterTimeframes: async (): Promise<MarketMasterTimeframe[]> =>
    unwrap(await axiosInstance.get("/api/v1/admin/market-master/timeframes")),

  getMarketMasterInstruments: async (search?: string): Promise<MarketMasterInstrument[]> =>
    unwrap(await axiosInstance.get("/api/v1/admin/market-master/instruments", { params: { ...(search ? { search } : {}) } })),

  getMarketMasterInstrument: async (instrumentId: number): Promise<MarketMasterInstrument> =>
    unwrap(await axiosInstance.get(`/api/v1/admin/market-master/instruments/${instrumentId}`)),

  createMarketMasterInstrument: async (payload: MarketMasterInstrumentPayload): Promise<MarketMasterInstrument> =>
    unwrap(await axiosInstance.post("/api/v1/admin/market-master/instruments", payload)),

  updateMarketMasterInstrument: async (instrumentId: number, payload: MarketMasterInstrumentPayload): Promise<MarketMasterInstrument> =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/market-master/instruments/${instrumentId}`, payload)),

  getDashboardSummary: async (): Promise<AdminDashboardSummary> =>
    unwrap(await axiosInstance.get("/api/v1/admin/dashboard/summary")),

  getMetrics: async (): Promise<AdminMetrics> =>
    unwrap(await axiosInstance.get("/api/v1/admin/metrics")),

  getUsers: async (skip = 0, limit = 20, search?: string): Promise<PaginatedResponse<User>> =>
    unwrap(await axiosInstance.get("/api/v1/admin/users", { params: { skip, limit, ...(search && { search }) } })),

  createUser: async (payload: any) =>
    unwrap(await axiosInstance.post("/api/v1/admin/users", payload)),

  updateUser: async (userId: string, payload: any) =>
    unwrap(await axiosInstance.put(`/api/v1/admin/users/${userId}`, payload)),

  deleteUser: async (userId: string) =>
    unwrap(await axiosInstance.delete(`/api/v1/admin/users/${userId}`)),

  updateUserStatus: async (userId: string, isActive: boolean) =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/users/${userId}/status`, { is_active: isActive })),

  updateUserRole: async (userId: string, role: string) =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/users/${userId}/role`, { role })),

  getPayments: async (
    skip = 0,
    limit = 20,
    status?: string,
    search?: string,
    method?: string,
    purpose?: string,
    from_date?: string,
    to_date?: string,
  ): Promise<PaginatedResponse<Payment>> =>
    unwrap(
      await axiosInstance.get("/api/v1/admin/payments", {
        params: {
          skip,
          limit,
          ...(status && { status }),
          ...(search && { search }),
          ...(method && { method }),
          ...(purpose && { purpose }),
          ...(from_date && { from_date }),
          ...(to_date && { to_date }),
        },
      }),
    ),

  getSubscriptions: async (skip = 0, limit = 20, status?: string, search?: string): Promise<PaginatedResponse<Subscription>> =>
    unwrap(await axiosInstance.get("/api/v1/admin/subscriptions", { params: { skip, limit, ...(status && { status }), ...(search && { search }) } })),

  getCreditBalances: async (skip = 0, limit = 20, search?: string): Promise<PaginatedResponse<CreditBalance>> =>
    unwrap(await axiosInstance.get("/api/v1/admin/credits/balances", { params: { skip, limit, ...(search && { search }) } })),

  getCredits: async (skip = 0, limit = 20, search?: string, transaction_type?: string): Promise<PaginatedResponse<CreditTransaction>> =>
    unwrap(await axiosInstance.get("/api/v1/admin/credits/ledger", { params: { skip, limit, ...(search && { search }), ...(transaction_type && { transaction_type }) } })),

  getSupportTickets: async (skip = 0, limit = 20, status?: string): Promise<PaginatedResponse<SupportTicket>> =>
    unwrap(await axiosInstance.get("/api/v1/admin/support-tickets", { params: { skip, limit, ...(status && { status }) } })),

  updateTicketStatus: async (ticketId: string, status: string) =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/support-tickets/${ticketId}`, { status })),

  replyToTicket: async (ticketId: string, message: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/support-tickets/${ticketId}/reply`, { message })),

  getOrders: async (
    page = 1,
    page_size = 20,
    status?: string,
    search?: string,
    source_type?: string,
    method?: string,
    from_date?: string,
    to_date?: string,
  ): Promise<PaginatedResponse<Order>> =>
    unwrap(
      await axiosInstance.get("/api/v1/admin/orders", {
        params: {
          page,
          page_size,
          ...(status && { status }),
          ...(search && { search }),
          ...(source_type && { source_type }),
          ...(method && { method }),
          ...(from_date && { from_date }),
          ...(to_date && { to_date }),
        },
      }),
    ),

  getBacktests: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
    from_date?: string;
    to_date?: string;
  }): Promise<AdminBacktestListResponse> =>
    unwrap(
      await axiosInstance.get("/api/v1/admin/backtests", {
        params: {
          page: params?.page ?? 1,
          page_size: params?.page_size ?? 20,
          ...(params?.search && { search: params.search }),
          ...(params?.status && { status: params.status }),
          ...(params?.from_date && { from_date: params.from_date }),
          ...(params?.to_date && { to_date: params.to_date }),
        },
      }),
    ),


  getBacktestDetail: async (backtestId: string) =>
    unwrap(await axiosInstance.get(`/api/v1/admin/backtests/${backtestId}/detail`)),

  getOrder: async (orderId: string): Promise<Order> =>
    unwrap(await axiosInstance.get(`/api/v1/admin/orders/${orderId}`)),

  updateOrderStatus: async (orderId: string, status: string) =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/orders/${orderId}/status`, { status })),

  getBacktestPricingConfig: async (): Promise<BacktestPricingConfigResponse> =>
    unwrap(await axiosInstance.get("/api/v1/admin/backtests/pricing-config")),

  updateBacktestPricingConfig: async (payload: BacktestPricingUpdatePayload): Promise<BacktestPricingActiveRuleSet> =>
    unwrap(await axiosInstance.put("/api/v1/admin/backtests/pricing-config", payload)),

  activateBacktestPricingRuleSet: async (ruleSetId: string): Promise<{ id: string; name: string; version: string; is_active: boolean }> =>
    unwrap(await axiosInstance.post("/api/v1/admin/backtests/pricing-config/activate", { rule_set_id: ruleSetId })),

  updateSubscription: async (subscriptionId: string, payload: { status?: string; renews?: boolean; end_at?: string }) =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/subscriptions/${subscriptionId}`, payload)),

  getPayment: async (paymentId: string): Promise<Payment> =>
    unwrap(await axiosInstance.get(`/api/v1/admin/payments/${paymentId}`)),

  refundPayment: async (paymentId: string, note?: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/payments/${paymentId}/refund`, note ? { note } : {})),

  addCredits: async (userId: string, amount: number, reason: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/credits/add`, { user_id: userId, amount, reason })),

  deductCredits: async (userId: string, amount: number, reason: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/credits/deduct`, { user_id: userId, amount, reason })),

  getStrategies: async (skip = 0, limit = 20, status?: string, search?: string): Promise<StrategyRequestsResponse> =>
    unwrap(await axiosInstance.get("/api/v1/admin/strategy-requests", { params: { skip, limit, ...(status && { status }), ...(search && { search }) } })),

  getStrategyManagementData: async (params?: {
    requestSkip?: number;
    requestLimit?: number;
    requestStatus?: string;
    requestSearch?: string;
    strategySkip?: number;
    strategyLimit?: number;
    strategySearch?: string;
    strategyVisibility?: StrategyVisibility | "";
    strategySource?: "MANUAL" | "REQUESTED" | "";
  }): Promise<StrategyRequestsResponse> =>
    unwrap(
      await axiosInstance.get("/api/v1/admin/strategy-requests", {
        params: {
          skip: params?.requestSkip ?? 0,
          limit: params?.requestLimit ?? 20,
          ...(params?.requestStatus ? { status: params.requestStatus } : {}),
          ...(params?.requestSearch ? { search: params.requestSearch } : {}),
          strategy_skip: params?.strategySkip ?? 0,
          strategy_limit: params?.strategyLimit ?? 100,
          ...(params?.strategySearch ? { strategy_search: params.strategySearch } : {}),
          ...(params?.strategyVisibility ? { strategy_visibility: params.strategyVisibility } : {}),
          ...(params?.strategySource ? { strategy_source: params.strategySource } : {}),
        },
      }),
    ),

  getStrategy: async (requestId: string): Promise<StrategyRequest> =>
    unwrap(await axiosInstance.get(`/api/v1/admin/strategy-requests/${requestId}`)),

  updateStrategy: async (requestId: string, payload: Partial<StrategyRequest>): Promise<StrategyRequest> =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/strategy-requests/${requestId}`, payload)),

  deployStrategy: async (requestId: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/${requestId}/deploy`)),

  deployStrategyWithPayload: async (requestId: string, payload: DeployStrategyRequestPayload) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/${requestId}/deploy`, payload)),

  publishStrategy: async (requestId: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/${requestId}/publish`)),

  publishStrategyWithPayload: async (requestId: string, payload: DeployStrategyRequestPayload) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/${requestId}/publish`, payload)),


  validateAdminStrategyById: async (strategyId: string, payload?: {
    instrument_id?: number;
    timeframe?: string;
    start_date?: string;
    end_date?: string;
    capital?: number;
  }): Promise<any> =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/strategies/${strategyId}/validate`, payload || {}, { timeout: HEAVY_API_TIMEOUT_MS })),


  getAdminStrategyById: async (strategyId: string): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.get(`/api/v1/admin/strategy-requests/strategies/${strategyId}`)),

  listAdminStrategyVersions: async (strategyId: string): Promise<{ items: StrategyVersion[]; current_hash?: string; workflow?: StrategyWorkflowStatus }> =>
    unwrap(await axiosInstance.get(`/api/v1/admin/strategy-requests/strategies/${strategyId}/versions`)),

  rollbackAdminStrategyVersion: async (strategyId: string, versionId: string): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/strategies/${strategyId}/rollback/${versionId}`)),

  listAdminStrategyPresets: async (): Promise<{ items: StrategyPreset[] }> =>
    unwrap(await axiosInstance.get(`/api/v1/admin/strategy-requests/strategy-presets`)),


  listStrategyRuntimePresets: async (strategyId: string): Promise<{ items: StrategyRuntimePreset[] }> =>
    unwrap(await axiosInstance.get(`/api/v1/admin/strategies/${strategyId}/runtime-presets`)),

  createStrategyRuntimePreset: async (strategyId: string, payload: Partial<StrategyRuntimePreset>): Promise<StrategyRuntimePreset> =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategies/${strategyId}/runtime-presets`, payload)),

  updateStrategyRuntimePreset: async (presetId: string, payload: Partial<StrategyRuntimePreset>): Promise<StrategyRuntimePreset> =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/strategy-runtime-presets/${presetId}`, payload)),

  deactivateStrategyRuntimePreset: async (presetId: string): Promise<StrategyRuntimePreset> =>
    unwrap(await axiosInstance.delete(`/api/v1/admin/strategy-runtime-presets/${presetId}`)),

  makeStrategyRuntimePresetDefault: async (presetId: string): Promise<StrategyRuntimePreset> =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-runtime-presets/${presetId}/make-default`)),

  runAdminStrategySandboxBacktest: async (
    strategyId: string,
    payload: { instrument_id: number; timeframe: string; start_date: string; end_date: string; capital?: number },
  ): Promise<AdminStrategySandboxResult> =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/strategies/${strategyId}/sandbox-backtest`, payload, { timeout: HEAVY_API_TIMEOUT_MS })),

  getAdminBacktestEngineSource: async (): Promise<AdminBacktestEngineSource> =>
    unwrap(await axiosInstance.get(`/api/v1/admin/backtest-engine/source`)),

  updateAdminBacktestEngineSource: async (source_code: string): Promise<AdminBacktestEngineSource> =>
    unwrap(await axiosInstance.put(`/api/v1/admin/backtest-engine/source`, { source_code })),

  listAdminStrategies: async (params?: {
    skip?: number;
    limit?: number;
    search?: string;
    visibility?: StrategyVisibility | "";
    source?: "MANUAL" | "REQUESTED" | "";
  }): Promise<StrategyListResponse> =>
    unwrap(
      await axiosInstance.get("/api/v1/admin/strategy-requests/strategies", {
        params: {
          skip: params?.skip ?? 0,
          limit: params?.limit ?? 20,
          ...(params?.search ? { search: params.search } : {}),
          ...(params?.visibility ? { visibility: params.visibility } : {}),
          ...(params?.source ? { source: params.source } : {}),
        },
      }),
    ),

  createAdminStrategy: async (payload: AdminStrategyCreatePayload): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.post("/api/v1/admin/strategy-requests/strategies", payload)),

  updateAdminStrategyById: async (strategyId: string, payload: AdminStrategyUpdatePayload): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/strategy-requests/strategies/${strategyId}`, payload)),

  deleteAdminStrategyById: async (strategyId: string): Promise<{ id: string; released_request_count: number }> =>
    unwrap(await axiosInstance.delete(`/api/v1/admin/strategy-requests/strategies/${strategyId}`)),

  publishAdminStrategyById: async (strategyId: string): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/strategies/${strategyId}/publish`)),

  unpublishAdminStrategyById: async (strategyId: string): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/strategies/${strategyId}/unpublish`)),

  updateAdminStrategyDeploymentGate: async (strategyId: string, payload: { is_deployable_paper?: boolean; is_deployable_demo?: boolean; is_live_approved?: boolean; reason?: string }): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategies/${strategyId}/deployment-gate`, payload)),

  getMarketDataCatalog: async (): Promise<AdminMarketDataCatalog> =>
    unwrap(await axiosInstance.get("/api/v1/admin/market-data/catalog")),

  getMarketDataDatasets: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    instrument_id?: number;
    timeframe?: string;
    freshness_status?: MarketDataFreshnessStatus;
    stale_after_hours?: number;
  }): Promise<AdminMarketDataDatasetListResponse> =>
    unwrap(
      await axiosInstance.get("/api/v1/admin/market-data/datasets", {
        params: {
          page: params?.page ?? 1,
          page_size: params?.page_size ?? 20,
          ...(params?.search ? { search: params.search } : {}),
          ...(params?.instrument_id ? { instrument_id: params.instrument_id } : {}),
          ...(params?.timeframe ? { timeframe: params.timeframe } : {}),
          ...(params?.freshness_status ? { freshness_status: params.freshness_status } : {}),
          ...(params?.stale_after_hours ? { stale_after_hours: params.stale_after_hours } : {}),
        },
      }),
    ),

  getMarketDataJobs: async (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    failed_only?: boolean;
    has_invalid?: boolean;
    search?: string;
    job_type?: "market_data_import" | "market_data_upload" | "market_data_refresh";
  }): Promise<AdminMarketDataJobListResponse> =>
    unwrap(
      await axiosInstance.get("/api/v1/admin/market-data/jobs", {
        params: {
          page: params?.page ?? 1,
          page_size: params?.page_size ?? 20,
          ...(params?.status ? { status: params.status } : {}),
          ...(params?.failed_only !== undefined ? { failed_only: params.failed_only } : {}),
          ...(params?.has_invalid !== undefined ? { has_invalid: params.has_invalid } : {}),
          ...(params?.search ? { search: params.search } : {}),
          ...(params?.job_type ? { job_type: params.job_type } : {}),
        },
      }),
    ),

  triggerMarketDataImport: async (payload: AdminMarketDataImportPayload): Promise<AdminMarketDataJobEnqueueResponse> =>
    unwrap(await axiosInstance.post("/api/v1/admin/market-data/hooks/import", payload)),

  triggerMarketDataUpload: async (payload: AdminMarketDataImportPayload): Promise<AdminMarketDataJobEnqueueResponse> =>
    unwrap(await axiosInstance.post("/api/v1/admin/market-data/hooks/upload", payload)),

  triggerMarketDataRefresh: async (payload: AdminMarketDataRefreshPayload): Promise<AdminMarketDataJobEnqueueResponse> =>
    unwrap(await axiosInstance.post("/api/v1/admin/market-data/hooks/refresh", payload)),

  fetchMarketDataPreview: async (payload: AdminMarketDataFetchPayload): Promise<AdminMarketDataFetchResponse> =>
    unwrap(await axiosInstance.post("/api/v1/admin/market-data/fetch-preview", payload, { timeout: HEAVY_API_TIMEOUT_MS })),

  fetchMarketDataImport: async (payload: AdminMarketDataFetchPayload): Promise<AdminMarketDataFetchResponse> =>
    unwrap(await axiosInstance.post("/api/v1/admin/market-data/fetch-import", payload, { timeout: HEAVY_API_TIMEOUT_MS })),

  refreshMissingMarketData: async (payload: AdminMarketDataRefreshMissingPayload): Promise<AdminMarketDataRefreshMissingResponse> =>
    unwrap(await axiosInstance.post("/api/v1/admin/market-data/refresh-missing", payload, { timeout: HEAVY_API_TIMEOUT_MS })),

  uploadMarketDataCsv: async (payload: AdminMarketDataCsvUploadPayload): Promise<AdminMarketDataCsvUploadResponse> => {
    const formData = new FormData();
    formData.append("instrument_id", String(payload.instrument_id));
    formData.append("timeframe", payload.timeframe);
    formData.append("source", payload.source || "CSV");
    formData.append("dry_run", String(Boolean(payload.dry_run)));
    formData.append("file", payload.file);
    return unwrap(
      await axiosInstance.post("/api/v1/admin/market-data/upload-csv", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: HEAVY_API_TIMEOUT_MS,
      }),
    );
  },

  getPricingPlans: async (): Promise<AdminPricingPlan[]> =>
    unwrap(await axiosInstance.get("/api/v1/admin/pricing/plans")),

  createPricingPlan: async (payload: AdminPricingPlanPayload): Promise<AdminPricingPlan> =>
    unwrap(await axiosInstance.post("/api/v1/admin/pricing/plans", payload)),

  updatePricingPlan: async (
    planId: string,
    payload: Partial<AdminPricingPlanPayload>,
  ): Promise<AdminPricingPlan> =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/pricing/plans/${planId}`, payload)),

  togglePricingPlan: async (planId: string, is_active: boolean): Promise<AdminPricingPlan> =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/pricing/plans/${planId}`, { is_active })),


};

