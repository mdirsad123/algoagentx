import axiosInstance from "@/lib/axios";
import { HEAVY_API_TIMEOUT_MS, POLLING_API_TIMEOUT_MS } from "@/lib/api-timeouts";
import type { AdvancedBacktestFilters } from "@/lib/api/backtests";

type ApiEnvelope<T> = { success?: boolean; data?: T; message?: string };
const unwrap = <T,>(payload: ApiEnvelope<T> | T): T => {
  if (payload && typeof payload === "object" && "success" in (payload as Record<string, unknown>)) {
    return ((payload as ApiEnvelope<T>).data ?? null) as T;
  }
  return payload as T;
};

export type ChallengeType = "ONE_STEP" | "TWO_STEP" | "INSTANT" | "CUSTOM" | string;
export type DailyDdMode = "STATIC_INITIAL_BALANCE" | "START_OF_DAY_BALANCE" | "START_OF_DAY_EQUITY";
export type MaxDdMode = "STATIC_INITIAL_BALANCE" | "TRAILING_BALANCE" | "TRAILING_EQUITY" | "HIGH_WATER_MARK";
export type QualifyingDayMode = "ANY_TRADE_DAY" | "MIN_PROFIT_DAY";
export type FundedRiskMode = "FIXED" | "DYNAMIC";

export interface FundedPayoutRules {
  profit_target_pct?: number | null;
  profit_target_amount?: number | null;
  minimum_payout_amount?: number | null;
  minimum_trading_days?: number | null;
  minimum_qualifying_profitable_days?: number | null;
  qualifying_day_minimum_profit_pct?: number | null;
  consistency_rule_enabled?: boolean;
  consistency_maximum_pct?: number | null;
  consistency_calculation_mode?: string;
  payout_waiting_calendar_days?: number | null;
  payout_profit_split_pct?: number | null;
  stop_simulation_when_payout_ready?: boolean;
}

export interface FundedAccountPhase {
  phase_number: number;
  phase_name: string;
  profit_target_pct?: number | null;
  daily_drawdown_pct: number;
  daily_drawdown_mode: DailyDdMode | string;
  max_drawdown_pct: number;
  max_drawdown_mode: MaxDdMode | string;
  minimum_trading_days: number;
  minimum_qualifying_day_profit_pct?: number | null;
  qualifying_day_mode: QualifyingDayMode | string;
  profit_target_required: boolean;
  reset_balance_after_pass: boolean;
  sequence: number;
}

export interface FundedRiskTier {
  name: string;
  sort_order: number;
  min_account_return_pct?: number | null;
  max_account_return_pct?: number | null;
  risk_percent: number;
  is_active: boolean;
}

export interface FundedAccountProfile {
  id: string;
  user_id?: string | null;
  name: string;
  provider_name?: string | null;
  challenge_type: ChallengeType;
  account_size: number;
  account_currency: string;
  is_template: boolean;
  is_active: boolean;
  description?: string | null;
  payout_config?: FundedPayoutRules | null;
  rules_json?: Record<string, unknown> | null;
  phases: FundedAccountPhase[];
  risk_tiers: FundedRiskTier[];
  created_at?: string;
  updated_at?: string;
}

export type FundedProfilePayload = Omit<FundedAccountProfile, "id" | "user_id" | "created_at" | "updated_at">;

export interface FundedRunRequest {
  profile_id: string;
  strategy_id: string;
  instrument_id: number;
  timeframe: string;
  start_date: string;
  end_date: string;
  runtime_config?: Record<string, unknown>;
  strategy_preset_id?: string | null;
  advanced_filters?: AdvancedBacktestFilters;
  risk_mode: FundedRiskMode;
  fixed_risk_pct?: number | null;
  safety_buffer_pct?: number;
  configured_max_risk_pct?: number | null;
}

export interface FundedPreviewResponse {
  valid: boolean;
  rule_engine_version?: string;
  profile_id: string;
  strategy_id: string;
  instrument_id: number;
  account_name: string;
  challenge_type: string;
  initial_capital: number;
  risk_mode: FundedRiskMode;
  fixed_risk_pct?: number | null;
  safety_buffer_pct?: number;
  market_data?: { candles?: number; from?: string; to?: string };
  snapshot_preview?: Record<string, any>;
  warnings?: string[];
  credit_policy?: string;
}

export interface FundedRunResponse {
  funded_backtest_id: string;
  status: string;
  current_phase?: number | null;
  final_balance?: number | null;
  final_equity?: number | null;
  trades_processed?: number;
  summary?: Record<string, any>;
  job_id?: string;
}

export interface FundedRunStatus {
  id: string;
  status: string;
  current_phase?: number | null;
  trades_processed?: number;
  current_balance?: number | null;
  current_equity?: number | null;
  target_progress?: Record<string, any> | number | null;
  trading_days?: number;
  qualifying_days?: number;
  failure_reason?: string | null;
  payout?: Record<string, any> | null;
  technical_error?: string | null;
}

export interface FundedRunDetail extends FundedRunStatus {
  profile_id?: string;
  strategy_id?: string;
  instrument_id?: number;
  timeframe?: string;
  start_date?: string;
  end_date?: string;
  initial_capital?: number;
  final_balance?: number | null;
  final_equity?: number | null;
  passed_at?: string | null;
  failed_at?: string | null;
  payout_eligible_at?: string | null;
  calendar_days?: number;
  summary?: Record<string, any>;
  phase_summaries?: Array<Record<string, any>>;
  account_snapshot?: Record<string, any>;
  runtime_snapshot?: Record<string, any>;
  risk_plan_snapshot?: Record<string, any>;
}

export const fundedBacktestsApi = {
  async listProfiles(): Promise<FundedAccountProfile[]> {
    const response = await axiosInstance.get<ApiEnvelope<FundedAccountProfile[]> | FundedAccountProfile[]>("/api/v1/funded-backtests/profiles");
    const data = unwrap(response.data);
    return Array.isArray(data) ? data : [];
  },
  async getProfile(id: string): Promise<FundedAccountProfile> {
    const response = await axiosInstance.get<ApiEnvelope<FundedAccountProfile> | FundedAccountProfile>(`/api/v1/funded-backtests/profiles/${id}`);
    return unwrap(response.data);
  },
  async createProfile(payload: FundedProfilePayload): Promise<FundedAccountProfile> {
    const response = await axiosInstance.post<ApiEnvelope<FundedAccountProfile> | FundedAccountProfile>("/api/v1/funded-backtests/profiles", payload);
    return unwrap(response.data);
  },
  async updateProfile(id: string, payload: FundedProfilePayload): Promise<FundedAccountProfile> {
    const response = await axiosInstance.put<ApiEnvelope<FundedAccountProfile> | FundedAccountProfile>(`/api/v1/funded-backtests/profiles/${id}`, payload);
    return unwrap(response.data);
  },
  async deactivateProfile(id: string): Promise<{ id: string; is_active: boolean }> {
    const response = await axiosInstance.delete<ApiEnvelope<{ id: string; is_active: boolean }> | { id: string; is_active: boolean }>(`/api/v1/funded-backtests/profiles/${id}`);
    return unwrap(response.data);
  },
  async preview(payload: FundedRunRequest): Promise<FundedPreviewResponse> {
    const response = await axiosInstance.post<ApiEnvelope<FundedPreviewResponse> | FundedPreviewResponse>("/api/v1/funded-backtests/preview", payload, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },
  async run(payload: FundedRunRequest): Promise<FundedRunResponse> {
    const response = await axiosInstance.post<ApiEnvelope<FundedRunResponse> | FundedRunResponse>("/api/v1/funded-backtests/run", payload, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },
  async getStatus(id: string): Promise<FundedRunStatus> {
    const response = await axiosInstance.get<ApiEnvelope<FundedRunStatus> | FundedRunStatus>(`/api/v1/funded-backtests/${id}/status`, { timeout: POLLING_API_TIMEOUT_MS });
    return unwrap(response.data);
  },
  async getRun(id: string): Promise<FundedRunDetail> {
    const response = await axiosInstance.get<ApiEnvelope<FundedRunDetail> | FundedRunDetail>(`/api/v1/funded-backtests/${id}`, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },
};
