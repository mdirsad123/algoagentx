import axiosInstance from "@/lib/axios";
import { HEAVY_API_TIMEOUT_MS } from "@/lib/api-timeouts";

type ApiEnvelope<T> = {
  success?: boolean;
  data?: T;
  message?: string;
};

const unwrap = <T>(payload: ApiEnvelope<T> | T): T => {
  if (payload && typeof payload === "object" && "success" in (payload as Record<string, unknown>)) {
    return ((payload as ApiEnvelope<T>).data ?? null) as T;
  }
  return payload as T;
};

export interface ReportPerformanceCard {
  key: "today" | "week" | "month" | "year" | string;
  label: string;
  net_profit: number;
  total_trades: number;
  win_rate: number;
  max_drawdown: number;
  backtest_count: number;
}

export interface BacktestReportSummary {
  total_net_profit_ytd: number;
  average_win_rate_ytd: number;
  max_drawdown_ytd: number;
  max_drawdown_type?: "amount" | "percent" | string;
  total_backtests_ytd: number;
  total_trades_ytd: number;
  best_strategy_name: string | null;
  best_instrument_symbol: string | null;
}

export interface ReportSummary extends BacktestReportSummary {
  account_currency: string;
  currency_symbol: string;
}

export interface LiveReportSummary {
  total_net_profit: number;
  today_profit: number;
  open_positions: number;
  closed_trades: number;
  win_rate: number;
  max_drawdown: number;
  max_drawdown_type?: "amount" | "percent" | string;
  active_deployments: number;
  connected_brokers: number;
  last_trade_at: string | null;
}

export interface RecentReportBacktest {
  id: string;
  created_at: string | null;
  strategy_name: string | null;
  instrument_symbol: string | null;
  timeframe: string | null;
  net_profit: number;
  win_rate: number;
  max_drawdown: number;
  max_drawdown_type?: "amount" | "percent" | string;
  total_trades: number;
  status: string | null;
  account_currency: string | null;
  currency_symbol: string | null;
}

export interface UserReportSummaryResponse {
  report_mode: "live" | "backtest_research";
  has_live_data: boolean;
  has_backtest_data: boolean;
  currency_symbol: string;
  account_currency: string;
  live_summary: LiveReportSummary;
  backtest_summary: BacktestReportSummary;
  summary: ReportSummary;
  performance_cards: ReportPerformanceCard[];
  recent_backtests: RecentReportBacktest[];
}

export interface UserReportSummaryQuery {
  range_from?: string;
  range_to?: string;
  page_size?: number;
}

export interface ReportActivityItem {
  id: string;
  type: "notification" | "backtest" | "strategy" | "broker" | "billing" | "live" | string;
  title: string;
  message: string;
  created_at: string | null;
  status: "info" | "success" | "warning" | "error" | string;
  source: string;
}

export interface UserReportActivityResponse {
  items: ReportActivityItem[];
}

export interface CreditEvent {
  id: string;
  type: "debit" | "credit" | string;
  amount: number;
  reason: string;
  created_at: string | null;
}

export interface PaymentEvent {
  id: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string | null;
}

export interface BillingCreditsReport {
  credit_balance: number;
  credits_used_this_month: number;
  credits_added_this_month: number;
  active_plan: string | null;
  subscription_status: string | null;
  recent_credit_events: CreditEvent[];
  recent_payments: PaymentEvent[];
}

const DEFAULT_LIVE_SUMMARY: LiveReportSummary = {
  total_net_profit: 0,
  today_profit: 0,
  open_positions: 0,
  closed_trades: 0,
  win_rate: 0,
  max_drawdown: 0,
  max_drawdown_type: "amount",
  active_deployments: 0,
  connected_brokers: 0,
  last_trade_at: null,
};

const DEFAULT_BACKTEST_SUMMARY: BacktestReportSummary = {
  total_net_profit_ytd: 0,
  average_win_rate_ytd: 0,
  max_drawdown_ytd: 0,
  max_drawdown_type: "amount",
  total_backtests_ytd: 0,
  total_trades_ytd: 0,
  best_strategy_name: null,
  best_instrument_symbol: null,
};

export const DEFAULT_REPORT_SUMMARY: UserReportSummaryResponse = {
  report_mode: "backtest_research",
  has_live_data: false,
  has_backtest_data: false,
  currency_symbol: "₹",
  account_currency: "INR",
  live_summary: DEFAULT_LIVE_SUMMARY,
  backtest_summary: DEFAULT_BACKTEST_SUMMARY,
  summary: {
    ...DEFAULT_BACKTEST_SUMMARY,
    account_currency: "INR",
    currency_symbol: "₹",
  },
  performance_cards: [],
  recent_backtests: [],
};

export const reportsApi = {
  async getUserReportSummary(params?: UserReportSummaryQuery): Promise<UserReportSummaryResponse> {
    const response = await axiosInstance.get<ApiEnvelope<UserReportSummaryResponse> | UserReportSummaryResponse>(
      "/api/v1/reports/user-summary",
      { params, timeout: HEAVY_API_TIMEOUT_MS }
    );
    const data = unwrap<UserReportSummaryResponse>(response.data) || DEFAULT_REPORT_SUMMARY;
    const summary = data.summary || DEFAULT_REPORT_SUMMARY.summary;
    const backtestSummary = data.backtest_summary || {
      total_net_profit_ytd: summary.total_net_profit_ytd || 0,
      average_win_rate_ytd: summary.average_win_rate_ytd || 0,
      max_drawdown_ytd: summary.max_drawdown_ytd || 0,
      max_drawdown_type: summary.max_drawdown_type || "amount",
      total_backtests_ytd: summary.total_backtests_ytd || 0,
      total_trades_ytd: summary.total_trades_ytd || 0,
      best_strategy_name: summary.best_strategy_name || null,
      best_instrument_symbol: summary.best_instrument_symbol || null,
    };
    return {
      report_mode: data.report_mode || "backtest_research",
      has_live_data: Boolean(data.has_live_data),
      has_backtest_data: Boolean(data.has_backtest_data || data.recent_backtests?.length),
      currency_symbol: data.currency_symbol || summary.currency_symbol || "₹",
      account_currency: data.account_currency || summary.account_currency || "INR",
      live_summary: data.live_summary || DEFAULT_LIVE_SUMMARY,
      backtest_summary: backtestSummary,
      summary: {
        ...DEFAULT_REPORT_SUMMARY.summary,
        ...summary,
      },
      performance_cards: Array.isArray(data.performance_cards) ? data.performance_cards : [],
      recent_backtests: Array.isArray(data.recent_backtests) ? data.recent_backtests : [],
    };
  },

  async getUserReportActivity(params?: { page_size?: number }): Promise<UserReportActivityResponse> {
    const response = await axiosInstance.get<ApiEnvelope<UserReportActivityResponse> | UserReportActivityResponse>(
      "/api/v1/reports/activity",
      { params, timeout: HEAVY_API_TIMEOUT_MS }
    );
    const data = unwrap<UserReportActivityResponse>(response.data);
    return { items: Array.isArray(data?.items) ? data.items : [] };
  },

  async getUserBillingCreditsReport(params?: { page_size?: number }): Promise<BillingCreditsReport> {
    const response = await axiosInstance.get<ApiEnvelope<BillingCreditsReport> | BillingCreditsReport>(
      "/api/v1/reports/billing-credits",
      { params, timeout: HEAVY_API_TIMEOUT_MS }
    );
    const data = unwrap<BillingCreditsReport>(response.data);
    return {
      credit_balance: Number(data?.credit_balance || 0),
      credits_used_this_month: Number(data?.credits_used_this_month || 0),
      credits_added_this_month: Number(data?.credits_added_this_month || 0),
      active_plan: data?.active_plan || null,
      subscription_status: data?.subscription_status || null,
      recent_credit_events: Array.isArray(data?.recent_credit_events) ? data.recent_credit_events : [],
      recent_payments: Array.isArray(data?.recent_payments) ? data.recent_payments : [],
    };
  },
};
