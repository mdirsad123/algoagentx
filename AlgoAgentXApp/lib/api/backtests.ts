import axiosInstance from "@/lib/axios";
import { HEAVY_API_TIMEOUT_MS, POLLING_API_TIMEOUT_MS } from "@/lib/api-timeouts";

type ApiEnvelope<T> = {
  success?: boolean;
  data?: T;
  message?: string;
};

const unwrap = <T>(payload: ApiEnvelope<T> | T): T | undefined => {
  if (payload && typeof payload === "object" && "success" in (payload as Record<string, unknown>)) {
    const envelope = payload as ApiEnvelope<T>;
    return envelope.data as T | undefined;
  }
  return payload as T;
};

export interface StrategyOption {
  id: string;
  name: string;
  description?: string | null;
  strategyType?: string | null;
  timeframe?: string | null;
  market?: string | null;
  visibility?: string | null;
  status?: string | null;
  lifecycle_status?: string | null;
  lifecycleStatus?: string | null;
  sourceRequestId?: string | null;
  request_kind?: string | null;
  requestKind?: string | null;
  code_attached?: boolean | null;
  codeAttached?: boolean | null;
  parameters?: Record<string, unknown> | null;
}

export interface InstrumentOption {
  id: number;
  symbol: string;
  name?: string | null;
  exchange?: string | null;
  market?: string | null;
  instrument_type?: string | null;
  asset_class?: string | null;
  account_currency?: string | null;
  currency_symbol?: string | null;
  quantity_mode?: string | null;
  tick_size?: number | null;
  lot_step?: number | null;
  min_lot?: number | null;
  is_active?: boolean | null;
}

export interface RuntimePresetOption {
  id: string;
  strategy_id?: string;
  strategyId?: string;
  name: string;
  description?: string | null;
  config_json?: Record<string, unknown>;
  configJson?: Record<string, unknown>;
  risk_label?: string | null;
  riskLabel?: string | null;
  is_default?: boolean;
  isDefault?: boolean;
  is_active?: boolean;
  isActive?: boolean;
}

export interface RuntimeConfigResponse {
  default_runtime_config?: Record<string, unknown> | null;
  runtime_config_schema?: Record<string, unknown> | null;
  presets?: RuntimePresetOption[];
  resolved_defaults?: Record<string, unknown> | null;
}

export interface AdvancedBacktestFilters {
  enabled: boolean;
  days_of_week?: string[];
  session?: "ALL" | "ASIAN" | "LONDON" | "NEW_YORK" | "CUSTOM" | string;
  custom_start_time?: string | null;
  custom_end_time?: string | null;
  timezone?: string;
}

export interface AdvancedFilterPreview {
  enabled?: boolean;
  days_of_week?: string[];
  session?: string;
  custom_start_time?: string | null;
  custom_end_time?: string | null;
  timezone?: string;
  summary?: string;
  total_candles_before_filter?: number;
  total_candles_after_filter?: number;
  candles_removed?: number;
  filter_reduction_pct?: number;
  warnings?: string[];
}

export interface BacktestPreviewCoverage {
  status?: "ok" | "warning" | "error" | string;
  range_start?: string | null;
  range_end?: string | null;
  total_candles?: number;
  filtered_candles?: number;
  candles_removed?: number;
  filter_reduction_pct?: number;
}

export interface BacktestConfigResponse {
  strategies: Array<{ id: string; name: string }>;
  instruments: InstrumentOption[];
  timeframes: string[];
  credits?: {
    balance?: number;
    current_balance?: number;
    wallet_balance?: number;
    included?: number;
    included_balance?: number;
    total_available?: number;
    subscription_state?: string;
    next_refill_at?: string | null;
    deduction_order?: string[];
  };
  limits?: {
    max_backtests_per_day?: number;
    max_date_range_days?: number;
  };
}

export interface DataAvailabilityResponse {
  instrument_id: number;
  timeframe: string;
  available: boolean;
  coverage_status?: "AVAILABLE" | "BLOCKED" | string;
  message?: string;
  candle_count: number;
  min_timestamp: string | null;
  max_timestamp: string | null;
  available_start?: string | null;
  available_end?: string | null;
  requested_start?: string | null;
  requested_end?: string | null;
  missing_before?: boolean;
  missing_after?: boolean;
  requested_candle_count: number;
  total_candles?: number;
  matched_candles?: number;
  expected_candle_count?: number | null;
  missing_candles_estimate?: number | null;
  coverage_pct?: number | null;
  has_large_intraday_gap?: boolean;
  dataset_start?: string | null;
  dataset_end?: string | null;
  status?: "ok" | "warning" | "error" | string;
}

export interface CostPreviewResponse {
  total_cost: number;
  current_balance: number;
  can_run: boolean;
  estimated_candles?: number;
  credit_cost?: number;
  credit_balance?: number;
  has_enough_credits?: boolean;
  pricing_rule?: string | null;
  subscription_state?: string;
  cost_feasible?: boolean;
  estimated_run_cost?: number;
  data_coverage?: BacktestPreviewCoverage;
  advanced_filters?: AdvancedFilterPreview;
  warnings?: string[];
  balances?: {
    wallet_balance?: number;
    included_balance?: number;
    total_available?: number;
  };
  breakdown?: {
    base_cost?: number;
    per_1000_candles_credits?: number;
    candle_units?: number;
    advanced_filter_multiplier?: number;
    min_credits?: number;
    max_credits?: number | null;
    rule_set_name?: string | null;
    date_range_days?: number;
    timeframe?: string;
    candle_count?: number;
    multipliers?: {
      volume?: number;
      complexity?: number;
    };
    complexity?: Record<string, unknown>;
  };
}

export interface BacktestRunPayload {
  strategy_id: string;
  instrument_id: number;
  timeframe: string;
  start_date: string;
  end_date: string;
  capital: number;
  save_result?: boolean;
  advanced_filters?: AdvancedBacktestFilters;
  runtime_config?: Record<string, unknown>;
  strategy_preset_id?: string | null;
}

export interface BacktestRunResult {
  backtest_id?: string;
  strategy_name?: string;
  instrument_symbol?: string;
  timeframe?: string;
  start_date?: string;
  end_date?: string;
  initial_capital?: number;
  final_capital?: number;
  net_profit?: number;
  max_drawdown?: number;
  sharpe_ratio?: number;
  win_rate?: number;
  profit_factor?: number;
  total_trades?: number;
  credit_cost?: number;
  debit_transaction_id?: string;
  advanced_filters?: AdvancedFilterPreview | null;
  advanced_filter_impact?: AdvancedFilterPreview | null;
  pricing?: {
    pricing_version?: string;
    date_range_days?: number;
    timeframe?: string;
    timeframe_minutes?: number;
    candle_count?: number;
    candle_count_mode?: "estimated" | "actual" | string;
    base_cost?: number;
    range_units?: number;
    multipliers?: {
      timeframe?: number;
      volume?: number;
      complexity?: number;
      premium?: number;
    };
    complexity?: Record<string, unknown>;
  };
  account_currency?: string | null;
  currency_symbol?: string | null;
  asset_class?: string | null;
  quantity_mode?: string | null;
  position_size_mode?: string | null;
  sl_mode?: string | null;
  rr_ratio?: number | null;
  risk_percent?: number | null;
  avg_lot_size?: number | null;
  avg_quantity?: number | null;
  signal_count?: number | null;
  generated_buy_signals?: number | null;
  generated_sell_signals?: number | null;
  rejected_trade_count?: number | null;
  rejection_reasons?: Record<string, number> | null;
  forced_end_of_backtest_exits?: number | null;
  warnings?: string[];
  equity_curve?: Array<{
    timestamp?: string;
    equity?: number;
  }>;
  saved?: boolean;
}


export interface BacktestJobStatusResponse {
  id?: string;
  job_id?: string;
  job_type?: string;
  status?: "pending" | "queued" | "running" | "completed" | "failed" | "retry" | string;
  progress?: number;
  message?: string | null;
  warning?: string | null;
  retry_count?: number;
  max_retries?: number;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  result_data?: BacktestRunResult & {
    backtest_id?: string;
    credit_cost?: number;
    included_credits_used?: number;
    wallet_credits_used?: number;
    wallet_balance_after?: number;
    included_balance_after?: number;
    total_balance_after?: number;
    subscription_state?: string;
    charge_idempotent?: boolean;
    included_debit_transaction_id?: string;
    debit_transaction_id?: string;
    error?: string;
    stage?: string;
  };
  job_data?: Record<string, unknown> | null;
  debit_txn_id?: string | null;
}

export interface BacktestRunResponse {
  job_id?: string;
  status?: string;
  progress?: number;
  backtest_id?: string;
  result?: BacktestRunResult;
  poll_url?: string;
  message?: string;
  estimated_credit_cost?: number;
  credits?: {
    debited?: number;
    included_debited?: number;
    wallet_debited?: number;
    charge_idempotent?: boolean;
    included_debit_transaction_id?: string;
    wallet_debit_transaction_id?: string;
    balance_after?: number;
    included_balance_after?: number;
    total_balance_after?: number;
    subscription_state?: string;
    deduction_order?: string[];
  };
}

export interface BacktestDetailResponse {
  summary: {
    id: string;
    strategy_name?: string;
    instrument_symbol?: string;
    timeframe?: string;
    net_profit?: number;
    max_drawdown?: number;
    sharpe_ratio?: number;
    win_rate?: number;
    total_trades?: number;
    final_capital?: number;
    initial_capital?: number;
    created_at?: string;
    updated_at?: string | null;
    strategy_id?: string | null;
    instrument_id?: number | null;
    start_date?: string | null;
    end_date?: string | null;
    profit_factor?: number | null;
    avg_win?: number | null;
    avg_loss?: number | null;
    expectancy?: number | null;
    account_currency?: string | null;
    currency_symbol?: string | null;
    asset_class?: string | null;
    quantity_mode?: string | null;
    position_size_mode?: string | null;
    sl_mode?: string | null;
    rr_ratio?: number | null;
    risk_percent?: number | null;
    avg_actual_risk?: number | null;
    avg_lot_size?: number | null;
    avg_quantity?: number | null;
    gross_profit?: number | null;
    gross_loss?: number | null;
    runtime_config_snapshot?: Record<string, unknown> | string | null;
    instrument_spec_snapshot?: Record<string, unknown> | string | null;
    runtime_summary?: string | null;
    is_legacy_currency?: boolean | null;
    advanced_filters?: AdvancedBacktestFilters | null;
    filter_summary?: string | null;
    candles_before_filter?: number | null;
    candles_after_filter?: number | null;
    filter_reduction_pct?: number | null;
    winning_trades_count?: number | null;
    losing_trades_count?: number | null;
    breakeven_trades_count?: number | null;
    tp_hit_count?: number | null;
    sl_hit_count?: number | null;
    other_exit_count?: number | null;
    best_trade_pnl?: number | null;
    worst_trade_pnl?: number | null;
    avg_r_multiple?: number | null;
    total_r_multiple?: number | null;
    best_r_multiple?: number | null;
    worst_r_multiple?: number | null;
  };
  trades: Array<{
    id?: string | number | null;
    trade_index?: number | null;
    row_index?: number | null;
    sequence?: number | null;
    backtest_id?: string | null;
    instrument_id?: number | null;
    entry_time?: string;
    exit_time?: string | null;
    side?: string;
    quantity?: number | null;
    lot_size?: number | null;
    account_currency?: string | null;
    currency_symbol?: string | null;
    asset_class?: string | null;
    quantity_mode?: string | null;
    entry_price?: number;
    exit_price?: number | null;
    pnl?: number;
    final_capital_after_trade?: number | null;
    running_capital?: number | null;
    capital_after_trade?: number | null;
    exit_type?: string | null;
    stop_loss?: number | null;
    target?: number | null;
    risk_points?: number | null;
    risk_ticks?: number | null;
    risk_pips?: number | null;
    reward_points?: number | null;
    reward_ticks?: number | null;
    rr_ratio?: number | null;
    risk_amount?: number | null;
    actual_risk_amount?: number | null;
    reward_amount?: number | null;
    expected_reward_amount?: number | null;
    r_multiple?: number | null;
    sl_mode?: string | null;
    position_size_mode?: string | null;
    exit_reason?: string | null;
    signal_reason?: string | null;
    runtime_config_snapshot?: Record<string, unknown> | string | null;
    instrument_spec_snapshot?: Record<string, unknown> | string | null;
    lifecycle_events?: Array<Record<string, unknown>> | string | null;
  }>;
  equity_curve: Array<{
    timestamp?: string;
    equity?: number;
  }>;
  pnl_calendar: Array<{
    date?: string;
    pnl?: number;
  }>;
}


export interface TradeChartCandle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number | null;
}

export interface TradeChartContextResponse {
  trade: BacktestDetailResponse["trades"][number];
  candles: TradeChartCandle[];
  overlays: {
    side?: string | null;
    entry_price?: number | null;
    exit_price?: number | null;
    stop_loss?: number | null;
    target?: number | null;
    entry_time?: string | null;
    exit_time?: string | null;
    exit_reason?: string | null;
    signal_reason?: string | null;
    pnl?: number | null;
    r_multiple?: number | null;
  };
  meta: {
    instrument_symbol?: string | null;
    timeframe?: string | null;
    backtest_id?: string | null;
    candles_before?: number;
    candles_after?: number;
    warning?: string | null;
    source?: "id" | "index" | "funded_trade" | string | null;
    trade_index?: number | null;
    funded_backtest_id?: string | null;
    funded_trade_id?: string | null;
    source_trade_id?: string | null;
    market_timestamp_storage?: string | null;
    lookup_shift_minutes?: number | null;
    lookup_entry_time?: string | null;
    lookup_exit_time?: string | null;
  };
}

export interface BacktestHistoryItem {
  id: string;
  strategy_id?: string | null;
  strategy_name?: string | null;
  instrument_id?: number | null;
  instrument_symbol?: string | null;
  timeframe?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  initial_capital?: number | null;
  final_capital?: number | null;
  net_profit?: number | null;
  max_drawdown?: number | null;
  sharpe_ratio?: number | null;
  win_rate?: number | null;
  total_trades?: number | null;
  winning_trades?: number | null;
  losing_trades?: number | null;
  credit_cost?: number | null;
  debit_transaction_id?: string | null;
  profit_factor?: number | null;
  status?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  account_currency?: string | null;
  currency_symbol?: string | null;
  asset_class?: string | null;
  quantity_mode?: string | null;
  is_legacy_currency?: boolean | null;
  advanced_filters?: AdvancedBacktestFilters | null;
  filter_summary?: string | null;
  candles_before_filter?: number | null;
  candles_after_filter?: number | null;
  filter_reduction_pct?: number | null;
  runtime_config_snapshot?: Record<string, unknown> | string | null;
  instrument_spec_snapshot?: Record<string, unknown> | string | null;
  runtime_summary?: string | null;
}

export interface BacktestHistoryPagination {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface BacktestHistoryResponse {
  backtests: BacktestHistoryItem[];
  pagination: BacktestHistoryPagination;
}

export interface BacktestHistoryQuery {
  page?: number;
  page_size?: number;
  strategy_id?: string;
  instrument_id?: number;
  timeframe?: string;
  status?: string;
  start_date_from?: string;
  start_date_to?: string;
  min_profit?: number;
  max_drawdown?: number;
}

export const backtestsApi = {
  async downloadExport(backtestId: string, format: "excel" | "pdf", options?: { mode?: "executive" | "full_audit" }): Promise<Blob> {
    const response = await axiosInstance.get(`/api/v1/backtests/${backtestId}/export/${format}`, {
      responseType: "blob",
      timeout: HEAVY_API_TIMEOUT_MS,
      params: format === "pdf" && options?.mode ? { mode: options.mode } : undefined,
    });
    return response.data as Blob;
  },
  async getConfig(): Promise<BacktestConfigResponse> {
    const response = await axiosInstance.get<ApiEnvelope<BacktestConfigResponse> | BacktestConfigResponse>("/api/v1/backtests/config");
    return (unwrap(response.data) || {
      strategies: [],
      instruments: [],
      timeframes: [],
    }) as BacktestConfigResponse;
  },

  async getStrategiesCatalog(): Promise<StrategyOption[]> {
    try {
      const response = await axiosInstance.get<ApiEnvelope<StrategyOption[]> | StrategyOption[]>("/api/v1/strategies/backtest-eligible");
      const data = unwrap(response.data);
      return Array.isArray(data) ? data : [];
    } catch {
      const response = await axiosInstance.get<ApiEnvelope<StrategyOption[]> | StrategyOption[]>("/api/v1/strategies");
      const data = unwrap(response.data);
      return Array.isArray(data) ? data : [];
    }
  },

  async getInstruments(): Promise<InstrumentOption[]> {
    try {
      const response = await axiosInstance.get<ApiEnvelope<InstrumentOption[]> | InstrumentOption[]>("/api/v1/market-master/instruments");
      const data = unwrap(response.data);
      if (Array.isArray(data)) return data;
    } catch {
      // Phase 2E keeps compatibility with older APIs.
    }

    const response = await axiosInstance.get<ApiEnvelope<InstrumentOption[]> | InstrumentOption[]>("/api/v1/instruments");
    const data = unwrap(response.data);
    return Array.isArray(data) ? data : [];
  },

  async getStrategyRuntimeConfig(strategyId: string): Promise<RuntimeConfigResponse> {
    const response = await axiosInstance.get<ApiEnvelope<RuntimeConfigResponse> | RuntimeConfigResponse>(
      `/api/v1/strategies/${strategyId}/runtime-config`,
    );
    return (unwrap(response.data) || {}) as RuntimeConfigResponse;
  },

  async getTimeframes(instrumentId?: number): Promise<string[]> {
    const response = await axiosInstance.get<ApiEnvelope<{ timeframes: string[] }> | { timeframes: string[] }>(
      "/api/v1/backtests/timeframes",
      {
        params: instrumentId ? { instrument_id: instrumentId } : undefined,
      },
    );
    const data = unwrap(response.data);
    return Array.isArray(data?.timeframes) ? data.timeframes : [];
  },

  async getDataAvailability(params: {
    instrument_id: number;
    timeframe: string;
    start_date?: string;
    end_date?: string;
  }): Promise<DataAvailabilityResponse> {
    const response = await axiosInstance.get<ApiEnvelope<DataAvailabilityResponse> | DataAvailabilityResponse>(
      "/api/v1/backtests/data-availability",
      { params, timeout: HEAVY_API_TIMEOUT_MS },
    );
    return (unwrap(response.data) || {
      instrument_id: params.instrument_id,
      timeframe: params.timeframe,
      available: false,
      candle_count: 0,
      min_timestamp: null,
      max_timestamp: null,
      requested_candle_count: 0,
    }) as DataAvailabilityResponse;
  },

  async previewCost(payload: {
    strategy_id?: string;
    instrument_id?: number;
    timeframe: string;
    start_date: string;
    end_date: string;
    capital?: number;
    advanced_filters?: AdvancedBacktestFilters;
  }): Promise<CostPreviewResponse> {
    const response = await axiosInstance.post<ApiEnvelope<CostPreviewResponse> | CostPreviewResponse>(
      "/api/v1/backtests/cost-preview",
      payload,
      { timeout: HEAVY_API_TIMEOUT_MS },
    );
    return (unwrap(response.data) || {
      total_cost: 0,
      current_balance: 0,
      can_run: false,
    }) as CostPreviewResponse;
  },

  async run(payload: BacktestRunPayload): Promise<BacktestRunResponse> {
    const response = await axiosInstance.post<ApiEnvelope<BacktestRunResponse> | BacktestRunResponse>(
      "/api/v1/backtests/run",
      payload,
      { timeout: HEAVY_API_TIMEOUT_MS },
    );
    return (unwrap(response.data) || {}) as BacktestRunResponse;
  },

  async getJobStatus(jobId: string): Promise<BacktestJobStatusResponse> {
    const response = await axiosInstance.get<ApiEnvelope<BacktestJobStatusResponse> | BacktestJobStatusResponse>(
      `/api/v1/jobs/${jobId}`,
      { timeout: POLLING_API_TIMEOUT_MS },
    );
    return (unwrap(response.data) || {}) as BacktestJobStatusResponse;
  },


  async getTradeChartContext(backtestId: string, tradeId: string | number): Promise<TradeChartContextResponse> {
    const response = await axiosInstance.get<ApiEnvelope<TradeChartContextResponse> | TradeChartContextResponse>(
      `/api/v1/backtests/${backtestId}/trades/${tradeId}/chart-context`,
      { timeout: HEAVY_API_TIMEOUT_MS },
    );
    return (unwrap(response.data) || {
      trade: {} as BacktestDetailResponse["trades"][number],
      candles: [],
      overlays: {},
      meta: { backtest_id: backtestId, warning: "No chart context returned." },
    }) as TradeChartContextResponse;
  },

  async getTradeChartContextByIndex(backtestId: string, tradeIndex: number): Promise<TradeChartContextResponse> {
    const response = await axiosInstance.get<ApiEnvelope<TradeChartContextResponse> | TradeChartContextResponse>(
      `/api/v1/backtests/${backtestId}/trades/by-index/${tradeIndex}/chart-context`,
      { timeout: HEAVY_API_TIMEOUT_MS },
    );
    return (unwrap(response.data) || {
      trade: {} as BacktestDetailResponse["trades"][number],
      candles: [],
      overlays: {},
      meta: { backtest_id: backtestId, source: "index", trade_index: tradeIndex, warning: "No chart context returned." },
    }) as TradeChartContextResponse;
  },

  async getDetail(backtestId: string): Promise<BacktestDetailResponse> {
    const response = await axiosInstance.get<ApiEnvelope<BacktestDetailResponse> | BacktestDetailResponse>(
      `/api/v1/backtests/${backtestId}/detail`,
      { timeout: HEAVY_API_TIMEOUT_MS },
    );
    return (unwrap(response.data) || {
      summary: { id: backtestId },
      trades: [],
      equity_curve: [],
      pnl_calendar: [],
    }) as BacktestDetailResponse;
  },

  async getHistory(params: BacktestHistoryQuery = {}): Promise<BacktestHistoryResponse> {
    const response = await axiosInstance.get<ApiEnvelope<BacktestHistoryResponse> | BacktestHistoryResponse>(
      "/api/v1/backtests/history",
      { params, timeout: HEAVY_API_TIMEOUT_MS },
    );
    return (unwrap(response.data) || {
      backtests: [],
      pagination: {
        page: params.page || 1,
        page_size: params.page_size || 20,
        total_count: 0,
        total_pages: 1,
      },
    }) as BacktestHistoryResponse;
  },
};
