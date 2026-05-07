"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock3,
  Database,
  DollarSign,
  Loader2,
  Play,
  RefreshCcw,
  SlidersHorizontal,
  Wallet,
  X,
} from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { FieldHelpTooltip } from "@/components/common/FieldHelpTooltip";
import { RuntimeSettingsForm } from "@/components/runtime/RuntimeSettingsForm";
import { EmptyState } from "@/components/shared/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { parseApiError, formatErrorMessage } from "@/lib/api/error";
import { formatCurrency as formatMoney, formatNumber as formatDisplayNumber, formatTradeSize, currencySymbolForCode } from "@/lib/formatters";
import {
  backtestsApi,
  type BacktestDetailResponse,
  type AdvancedBacktestFilters,
  type BacktestRunResponse,
  type CostPreviewResponse,
  type DataAvailabilityResponse,
  type InstrumentOption,
  type RuntimePresetOption,
  type StrategyOption,
} from "@/lib/api/backtests";


const FIELD_HELP: Record<string, string> = {
  "Initial Capital": "Starting capital used for this backtest. It affects risk sizing, equity curve, and drawdown calculations. Example: 100,000. Keep it close to the account size you want to simulate.",
  "Capital Risk %": "Percentage of capital risked per trade when using risk-based sizing. Example: 1% of $100,000 means $1,000 risk per trade. Higher values can create large drawdowns.",
  "Position Size Mode": "Risk Based calculates position size from stop loss and risk percent. Fixed Lot uses the same lot size for every trade. Fixed Quantity is for share/unit based instruments.",
  "Fixed Lot Size": "Manual lot size used for each trade. Example: 0.02 lots. High fixed lots can create unrealistic or dangerous risk.",
  "Fixed Quantity": "Manual quantity used for each trade on non-lot based instruments. Example: 10 shares/contracts. Use with a max quantity cap for safety.",
  "Max Lot Cap": "Maximum allowed lot size. This protects from oversized trades when stop loss distance is small. Example: 0.10 lots.",
  "Max Quantity Cap": "Maximum quantity cap for non-lot based instruments. Example: 100 shares. This protects from oversized orders.",
  "RR Ratio": "Reward-to-risk ratio. Example: 1:2 means target is twice the stop loss distance. Higher RR can reduce win rate but improve payoff.",
  "SL Mode": "Defines how stop loss is calculated: Fixed Percent, ATR volatility, recent swing high/low, or strategy suggested stop. This directly affects trade risk and lot sizing.",
  "ATR Period": "Number of candles used to calculate Average True Range. Example: 14. Higher values make the volatility estimate smoother.",
  "ATR Multiplier": "Multiplier applied to ATR to calculate stop loss distance. Example: 1.5. Higher multiplier means wider stop and usually smaller position size.",
  "Swing Lookback": "Number of candles used to find recent swing high/low for stop loss placement. Example: 5 or 10 candles.",
  "Fixed Price Risk %": "Stop loss distance as a fixed percent of entry price. Example: 0.20% means SL is 0.20% away from entry. Too tight can cause noisy exits.",
  "Entry Mode": "Controls when trade enters after signal. Next Candle Open is safer for realistic backtests because it avoids entering before the candle is complete.",
  "Exit on Opposite Signal": "Closes current trade when an opposite signal appears. This can reduce losses but may exit before the original target.",
  "Allow Long": "Allows buy trades. Turn OFF to test short-only behavior or restrict a strategy.",
  "Allow Short": "Allows sell trades. Turn OFF when the market/account should only take long trades.",
  "Intraday Square Off": "For supported intraday Indian instruments, closes positions near the selected time. It is disabled for forex/metals like XAUUSD.",
  "Square Off Time": "Time used to close intraday Indian market positions. Example: 15:15. Not used for forex/metals.",
  "Max Trades Per Day": "Limits number of trades per day to avoid overtrading. Example: 3 trades/day. Leave as No Limit only for research.",
  "Max Open Positions": "Limits simultaneous open positions. Example: 1 keeps the backtest simple and risk controlled.",
  "Break Even Enabled": "When enabled, stop loss can move to entry after trade reaches selected profit. This can reduce losses but may exit early.",
  "Break Even Trigger R": "Profit multiple required before stop loss moves to entry. Example: 1R means profit equals initial risk.",
  "Trailing Stop Enabled": "When enabled, stop loss can follow price after trade moves in profit. This can protect gains but may cut winners early.",
  "Trailing Mode": "Method used to trail stop. ATR trail uses volatility; swing/EMA trail follows structure or moving average behavior.",
  "Trail Start R": "Profit multiple after which trailing starts. Example: 1.5R means trailing begins after profit reaches 1.5 times initial risk.",
  "Trail ATR Multiplier": "ATR multiplier used for trailing stop distance. Higher values trail wider and may give trades more room.",
  "Partial Exit Enabled": "Closes part of the position at selected profit level. This can lock in gains but reduces the size left for final target.",
  "Partial Exit At R": "R multiple where partial exit happens. Example: 1R closes part when profit equals initial risk.",
  "Partial Exit Percent": "Percent of position closed during partial exit. Example: 50% closes half and lets the remaining position continue.",
  "Runtime Preset": "Saved runtime template for risk, execution, SL/TP and trade management settings. Applying a preset changes this drawer only until you save/run.",
};

const STRATEGY_PARAM_HELP = "Strategy-specific parameter. Changing this may affect signal frequency and trade quality. Example: a larger period usually creates fewer but smoother signals.";

type ParameterField = {
  key: string;
  label: string;
  valueType: "string" | "number" | "boolean";
  value: string;
};






type PresetNumberOption = { label: string; value: number };

const RISK_PERCENT_OPTIONS: PresetNumberOption[] = [
  { label: "0.25%", value: 0.0025 },
  { label: "0.50%", value: 0.005 },
  { label: "1.00%", value: 0.01 },
  { label: "1.50%", value: 0.015 },
  { label: "2.00%", value: 0.02 },
  { label: "3.00%", value: 0.03 },
  { label: "5.00%", value: 0.05 },
];

const RR_RATIO_OPTIONS: PresetNumberOption[] = [1, 1.5, 2, 3, 4, 5].map((value) => ({ label: String(value), value }));
const ATR_PERIOD_OPTIONS: PresetNumberOption[] = [7, 10, 14, 20, 21, 50].map((value) => ({ label: String(value), value }));
const ATR_MULTIPLIER_OPTIONS: PresetNumberOption[] = [1, 1.5, 2, 2.5, 3].map((value) => ({ label: String(value), value }));
const SWING_LOOKBACK_OPTIONS: PresetNumberOption[] = [3, 5, 10, 20].map((value) => ({ label: String(value), value }));
const FIXED_PRICE_RISK_OPTIONS: PresetNumberOption[] = [
  { label: "0.10%", value: 0.001 },
  { label: "0.20%", value: 0.002 },
  { label: "0.50%", value: 0.005 },
  { label: "1.00%", value: 0.01 },
  { label: "2.00%", value: 0.02 },
];
const MAX_OPEN_POSITION_OPTIONS: PresetNumberOption[] = [1, 2, 3, 5].map((value) => ({ label: String(value), value }));
const BREAK_EVEN_R_OPTIONS: PresetNumberOption[] = [0.5, 1, 1.5, 2].map((value) => ({ label: String(value), value }));
const TRAIL_START_R_OPTIONS: PresetNumberOption[] = [1, 1.5, 2, 3].map((value) => ({ label: String(value), value }));
const TRAIL_ATR_MULTIPLIER_OPTIONS: PresetNumberOption[] = [1, 1.5, 2, 2.5, 3].map((value) => ({ label: String(value), value }));
const MAX_TRADES_PER_DAY_OPTIONS: Array<{ label: string; value: string }> = [
  { label: "No Limit", value: "NONE" },
  { label: "1", value: "1" },
  { label: "2", value: "2" },
  { label: "3", value: "3" },
  { label: "5", value: "5" },
  { label: "10", value: "10" },
  { label: "20", value: "20" },
];

type RuntimeFieldSchema = {
  type?: "number" | "boolean" | "select" | "text" | "string";
  label?: string;
  default?: string | number | boolean | null;
  min?: number;
  max?: number;
  step?: number;
  options?: Array<string | { label?: string; value?: string | number | boolean }>;
};

type RuntimeConfig = {
  risk: {
    initial_capital?: number;
    account_currency?: string | null;
    risk_percent?: number;
    position_size_mode?: "RISK_BASED" | "FIXED_LOT" | "FIXED_QUANTITY" | string;
    fixed_lot?: number | null;
    fixed_quantity?: number | null;
    max_lot_cap?: number | null;
    max_quantity_cap?: number | null;
  };
  execution: {
    entry_mode?: string;
    exit_on_opposite_signal?: boolean;
    allow_long?: boolean;
    allow_short?: boolean;
    max_trades_per_day?: number | null;
    max_open_positions?: number | null;
    intraday_square_off?: boolean;
    square_off_time?: string;
  };
  sl_tp: {
    sl_mode?: "ATR" | "SWING" | "FIXED_PERCENT" | "STRATEGY_SUGGESTED" | string;
    rr_ratio?: number;
    atr_period?: number;
    atr_multiplier?: number;
    swing_lookback?: number;
    fixed_price_risk_pct?: number;
    use_strategy_suggested_sl?: boolean;
  };
  trade_management: {
    break_even_enabled?: boolean;
    break_even_trigger_r?: number;
    trailing_enabled?: boolean;
    trailing_mode?: "ATR_TRAIL" | "EMA20_TRAIL" | "SWING_TRAIL" | string;
    trail_start_r?: number;
    trail_atr_multiplier?: number;
    partial_exit_enabled?: boolean;
    partial_exit_at_r?: number;
    partial_exit_percent?: number;
    break_even_offset_points?: number;
  };
  strategy_params: Record<string, string | number | boolean | null>;
};

type RuntimeTab = "risk" | "sl_tp" | "execution" | "trade_management" | "strategy_params";

const SYSTEM_RUNTIME_DEFAULTS: RuntimeConfig = {
  risk: {
    initial_capital: 100000,
    account_currency: null,
    risk_percent: 0.01,
    position_size_mode: "RISK_BASED",
    fixed_lot: null,
    fixed_quantity: null,
    max_lot_cap: null,
    max_quantity_cap: null,
  },
  execution: {
    entry_mode: "NEXT_CANDLE_OPEN",
    exit_on_opposite_signal: true,
    allow_long: true,
    allow_short: true,
    max_trades_per_day: null,
    max_open_positions: 1,
    intraday_square_off: false,
    square_off_time: "15:15",
  },
  sl_tp: {
    sl_mode: "ATR",
    rr_ratio: 2,
    atr_period: 14,
    atr_multiplier: 1.5,
    swing_lookback: 5,
    fixed_price_risk_pct: 0.002,
    use_strategy_suggested_sl: false,
  },
  trade_management: {
    break_even_enabled: false,
    break_even_trigger_r: 1,
    break_even_offset_points: 0,
    trailing_enabled: false,
    trailing_mode: "ATR_TRAIL",
    trail_start_r: 1.5,
    trail_atr_multiplier: 1,
    partial_exit_enabled: false,
    partial_exit_at_r: 1,
    partial_exit_percent: 0.5,
  },
  strategy_params: {},
};

const cloneRuntimeConfig = (config: RuntimeConfig): RuntimeConfig => JSON.parse(JSON.stringify(config)) as RuntimeConfig;

const mergeRuntimeConfig = (base: RuntimeConfig, override?: Partial<RuntimeConfig> | null): RuntimeConfig => ({
  risk: { ...base.risk, ...(override?.risk || {}) },
  execution: { ...base.execution, ...(override?.execution || {}) },
  sl_tp: { ...base.sl_tp, ...(override?.sl_tp || {}) },
  trade_management: { ...base.trade_management, ...(override?.trade_management || {}) },
  strategy_params: { ...base.strategy_params, ...(override?.strategy_params || {}) },
});

const normalizeRuntimeConfig = (config?: Partial<RuntimeConfig> | null): RuntimeConfig =>
  mergeRuntimeConfig(cloneRuntimeConfig(SYSTEM_RUNTIME_DEFAULTS), config || null);

const toOptionalNumber = (value: string): number | null => {
  if (value === "" || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const runtimeChanged = (current: RuntimeConfig, defaults: RuntimeConfig): boolean =>
  JSON.stringify(current) !== JSON.stringify(defaults);

const toggleClass = (enabled: boolean) =>
  `relative inline-flex h-7 w-14 items-center rounded-full border transition ${
    enabled ? "border-primary/60 bg-primary/80" : "border-border/70 bg-card/30"
  }`;

const toggleKnobClass = (enabled: boolean) =>
  `inline-block h-5 w-5 rounded-full bg-white shadow transition ${enabled ? "translate-x-7" : "translate-x-1"}`;

type SessionOption = "ALL" | "ASIAN" | "LONDON" | "NEW_YORK" | "CUSTOM";

type DayOption = {
  value: string;
  label: string;
  short: string;
};

const DAY_OPTIONS: DayOption[] = [
  { value: "MONDAY", label: "Monday", short: "Mon" },
  { value: "TUESDAY", label: "Tuesday", short: "Tue" },
  { value: "WEDNESDAY", label: "Wednesday", short: "Wed" },
  { value: "THURSDAY", label: "Thursday", short: "Thu" },
  { value: "FRIDAY", label: "Friday", short: "Fri" },
  { value: "SATURDAY", label: "Saturday", short: "Sat" },
  { value: "SUNDAY", label: "Sunday", short: "Sun" },
];

const SESSION_OPTIONS: Array<{ value: SessionOption; label: string }> = [
  { value: "ALL", label: "All Sessions" },
  { value: "ASIAN", label: "Asian Session" },
  { value: "LONDON", label: "London Session" },
  { value: "NEW_YORK", label: "New York Session" },
  { value: "CUSTOM", label: "Custom Time Window" },
];

const DEFAULT_TIMEZONE = "Asia/Kolkata";
const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

const isValidTimeValue = (value: string): boolean => TIME_PATTERN.test((value || "").trim());

const META_PARAMETER_KEYS = new Set([
  "performance_metrics",
  "metrics",
  "performance",
  "stats",
  "metricSummary",
  "metric_summary",
  "strategy_type",
  "market",
  "timeframe",
]);

const toDateInput = (value: Date) => value.toISOString().slice(0, 10);

const safeNumber = (value: unknown, fallback = 0): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const formatNumber = (value: number | null | undefined, fractionDigits = 2): string => formatDisplayNumber(value, fractionDigits);

const formatCurrency = (value: number | null | undefined, symbol = "₹"): string => formatMoney(value, symbol);

const formatPercent = (value: number | null | undefined, multiplyBy100 = false): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const display = multiplyBy100 ? value * 100 : value;
  return `${formatNumber(display, 2)}%`;
};

const humanLabel = (key: string): string =>
  key
    .replace(/_/g, " ")
    .replace(/\./g, " · ")
    .replace(/\b\w/g, (match) => match.toUpperCase());

const extractStrategyParameterFields = (strategy: StrategyOption | null): ParameterField[] => {
  const params = strategy?.parameters;
  if (!params || typeof params !== "object") return [];

  const fields: ParameterField[] = [];

  const pushField = (key: string, raw: unknown) => {
    if (raw === null || raw === undefined) return;
    if (META_PARAMETER_KEYS.has(key)) return;

    const primitiveType = typeof raw;
    if (primitiveType === "string" || primitiveType === "number" || primitiveType === "boolean") {
      fields.push({
        key,
        label: humanLabel(key),
        valueType: primitiveType === "number" ? "number" : primitiveType === "boolean" ? "boolean" : "string",
        value: String(raw),
      });
      return;
    }

    if (raw && typeof raw === "object") {
      Object.entries(raw as Record<string, unknown>).forEach(([nestedKey, nestedValue]) => {
        const composedKey = `${key}.${nestedKey}`;
        if (nestedValue === null || nestedValue === undefined) return;
        const nestedType = typeof nestedValue;
        if (nestedType === "string" || nestedType === "number" || nestedType === "boolean") {
          fields.push({
            key: composedKey,
            label: humanLabel(composedKey),
            valueType:
              nestedType === "number"
                ? "number"
                : nestedType === "boolean"
                  ? "boolean"
                  : "string",
            value: String(nestedValue),
          });
        }
      });
    }
  };

  Object.entries(params).forEach(([key, value]) => pushField(key, value));
  return fields.slice(0, 16);
};

const resultStatusTone = (status: string | undefined) => {
  const normalized = (status || "").toLowerCase();
  if (normalized === "completed") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
  if (normalized === "running" || normalized === "pending") return "border-sky-500/40 bg-sky-500/10 text-sky-200";
  if (normalized === "failed") return "border-rose-500/40 bg-rose-500/10 text-rose-200";
  return "border-border/50 bg-card/40 text-muted-foreground";
};

export default function BacktestPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [initialLoading, setInitialLoading] = useState(true);
  const [initialError, setInitialError] = useState<string | null>(null);

  const [strategies, setStrategies] = useState<StrategyOption[]>([]);
  const [instruments, setInstruments] = useState<InstrumentOption[]>([]);
  const [timeframes, setTimeframes] = useState<string[]>([]);

  const [limits, setLimits] = useState<{ max_backtests_per_day?: number; max_date_range_days?: number } | null>(null);
  const [creditSnapshot, setCreditSnapshot] = useState<{
    totalAvailable: number;
    walletBalance: number;
    includedBalance: number;
    deductionOrder: string[];
    subscriptionState?: string | null;
  } | null>(null);

  const [selectedStrategyId, setSelectedStrategyId] = useState<string>("");
  const [selectedInstrumentId, setSelectedInstrumentId] = useState<string>("");
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>("");
  const [initialCapital, setInitialCapital] = useState<string>("100000");

  const [startDate, setStartDate] = useState<string>(() => {
    const now = new Date();
    const start = new Date(now);
    start.setDate(now.getDate() - 90);
    return toDateInput(start);
  });
  const [endDate, setEndDate] = useState<string>(() => toDateInput(new Date()));

  const [parameterValues, setParameterValues] = useState<Record<string, string>>({});
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [runtimeSettingsOpen, setRuntimeSettingsOpen] = useState(false);
  const [runtimeTab, setRuntimeTab] = useState<RuntimeTab>("risk");
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfig>(() => cloneRuntimeConfig(SYSTEM_RUNTIME_DEFAULTS));
  const [runtimeDefaults, setRuntimeDefaults] = useState<RuntimeConfig>(() => cloneRuntimeConfig(SYSTEM_RUNTIME_DEFAULTS));
  const [runtimeSchema, setRuntimeSchema] = useState<Record<string, RuntimeFieldSchema>>({});
  const [runtimePresets, setRuntimePresets] = useState<RuntimePresetOption[]>([]);
  const [selectedRuntimePresetId, setSelectedRuntimePresetId] = useState<string>("DEFAULT");
  const [runtimeConfigLoading, setRuntimeConfigLoading] = useState(false);
  const [runtimeConfigError, setRuntimeConfigError] = useState<string | null>(null);
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false);
  const [advancedFiltersEnabled, setAdvancedFiltersEnabled] = useState(false);
  const [selectedDays, setSelectedDays] = useState<string[]>([]);
  const [selectedSession, setSelectedSession] = useState<SessionOption>("ALL");
  const [customStartTime, setCustomStartTime] = useState("17:00");
  const [customEndTime, setCustomEndTime] = useState("21:00");
  const [advancedTimezone, setAdvancedTimezone] = useState(DEFAULT_TIMEZONE);

  const [isPreviewing, setIsPreviewing] = useState(false);
  const [availability, setAvailability] = useState<DataAvailabilityResponse | null>(null);
  const [costPreview, setCostPreview] = useState<CostPreviewResponse | null>(null);
  const [previewWarnings, setPreviewWarnings] = useState<string[]>([]);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [lastPreviewSignature, setLastPreviewSignature] = useState<string>("");

  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [insufficientCreditsHint, setInsufficientCreditsHint] = useState<
    { needed?: number; walletBalance?: number; includedBalance?: number } | null
  >(null);
  const [runResponse, setRunResponse] = useState<BacktestRunResponse | null>(null);
  const [resultDetail, setResultDetail] = useState<BacktestDetailResponse | null>(null);

  const selectedStrategy = useMemo(
    () => strategies.find((strategy) => strategy.id === selectedStrategyId) || null,
    [strategies, selectedStrategyId],
  );

  const selectedInstrument = useMemo(
    () => instruments.find((instrument) => String(instrument.id) === String(selectedInstrumentId)) || null,
    [instruments, selectedInstrumentId],
  );

  const parameterFields = useMemo(() => extractStrategyParameterFields(selectedStrategy), [selectedStrategy]);
  const runtimeIsCustom = useMemo(() => runtimeChanged(runtimeConfig, runtimeDefaults), [runtimeConfig, runtimeDefaults]);

  const selectedInstrumentMarketCode = useMemo(() => {
    return String(
      selectedInstrument?.asset_class ||
      selectedInstrument?.market ||
      selectedInstrument?.instrument_type ||
      ""
    ).toUpperCase();
  }, [selectedInstrument]);

  const isIntradayTimeframe = useMemo(() => {
    const value = String(selectedTimeframe || "").trim().toLowerCase();
    if (!value) return false;
    if (["1d", "d", "day", "daily", "1w", "w", "week", "weekly", "1mo", "month", "monthly"].includes(value)) {
      return false;
    }
    return /^(\d+)(m|min|minute|minutes|h|hr|hour|hours)$/.test(value);
  }, [selectedTimeframe]);

  const supportsIntradaySquareOff = useMemo(() => {
    const indianAssetClasses = new Set(["INDIAN_EQUITY", "INDIAN_INDEX", "INDIAN_FO", "INDIAN_FUTURES", "INDIAN_OPTIONS"]);
    return indianAssetClasses.has(selectedInstrumentMarketCode) && isIntradayTimeframe;
  }, [isIntradayTimeframe, selectedInstrumentMarketCode]);

  const instrumentCurrency = selectedInstrument?.account_currency || "—";
  const instrumentQuantityMode = selectedInstrument?.quantity_mode || "—";

  const advancedFilterPayload = useMemo<AdvancedBacktestFilters | undefined>(() => {
    if (!advancedFiltersEnabled) return { enabled: false };

    return {
      enabled: true,
      days_of_week: selectedDays,
      session: selectedSession,
      custom_start_time: selectedSession === "CUSTOM" ? customStartTime : null,
      custom_end_time: selectedSession === "CUSTOM" ? customEndTime : null,
      timezone: advancedTimezone || DEFAULT_TIMEZONE,
    };
  }, [advancedFiltersEnabled, selectedDays, selectedSession, customStartTime, customEndTime, advancedTimezone]);

  const advancedFilterSignature = useMemo(
    () => JSON.stringify(advancedFilterPayload || { enabled: false }),
    [advancedFilterPayload],
  );

  const activeFilterSummary = useMemo(() => {
    if (!advancedFiltersEnabled) return "Advanced filters disabled";

    const dayText = selectedDays.length
      ? DAY_OPTIONS.filter((day) => selectedDays.includes(day.value)).map((day) => day.label).join(", ")
      : "All days";
    const sessionLabel = SESSION_OPTIONS.find((item) => item.value === selectedSession)?.label || "All Sessions";
    const sessionText = selectedSession === "CUSTOM"
      ? `${customStartTime || "--:--"}-${customEndTime || "--:--"} ${advancedTimezone || DEFAULT_TIMEZONE}`
      : sessionLabel;

    return `${dayText} · ${sessionText}`;
  }, [advancedFiltersEnabled, selectedDays, selectedSession, customStartTime, customEndTime, advancedTimezone]);

  const toggleTradingDay = useCallback((day: string) => {
    setSelectedDays((prev) => (prev.includes(day) ? prev.filter((item) => item !== day) : [...prev, day]));
  }, []);

  useEffect(() => {
    const nextValues: Record<string, string> = {};
    parameterFields.forEach((field) => {
      nextValues[field.key] = field.value;
    });
    setParameterValues(nextValues);
  }, [parameterFields]);

  useEffect(() => {
    if (!selectedStrategyId) {
      const defaults = normalizeRuntimeConfig({ risk: { initial_capital: safeNumber(initialCapital, 100000) } });
      setRuntimeDefaults(defaults);
      setRuntimeConfig(defaults);
      setRuntimeSchema({});
      setRuntimePresets([]);
      setSelectedRuntimePresetId("DEFAULT");
      return;
    }

    let active = true;
    const loadRuntimeConfig = async () => {
      setRuntimeConfigLoading(true);
      setRuntimeConfigError(null);
      try {
        const response = await backtestsApi.getStrategyRuntimeConfig(selectedStrategyId);
        const resolved = normalizeRuntimeConfig(
          (response.resolved_defaults || response.default_runtime_config || {}) as Partial<RuntimeConfig>,
        );
        resolved.risk.initial_capital = safeNumber(initialCapital, resolved.risk.initial_capital || 100000);
        if (active) {
          setRuntimeDefaults(resolved);
          setRuntimeConfig(cloneRuntimeConfig(resolved));
          const schema = response.runtime_config_schema as Record<string, unknown> | null | undefined;
          const strategyParams = schema?.strategy_params;
          setRuntimeSchema(
            strategyParams && typeof strategyParams === "object"
              ? (strategyParams as Record<string, RuntimeFieldSchema>)
              : {},
          );
          const presets = Array.isArray(response.presets) ? response.presets : [];
          setRuntimePresets(presets);
          setSelectedRuntimePresetId("DEFAULT");
        }
      } catch (error) {
        if (!active) return;
        const fallback = normalizeRuntimeConfig({
          risk: { initial_capital: safeNumber(initialCapital, 100000) },
          strategy_params: Object.fromEntries(parameterFields.map((field) => [field.key, field.value])),
        });
        setRuntimeDefaults(fallback);
        setRuntimeConfig(cloneRuntimeConfig(fallback));
        setRuntimeSchema({});
        setRuntimePresets([]);
        setSelectedRuntimePresetId("DEFAULT");
        setRuntimeConfigError(formatErrorMessage(parseApiError(error)));
      } finally {
        if (active) setRuntimeConfigLoading(false);
      }
    };

    void loadRuntimeConfig();
    return () => {
      active = false;
    };
  }, [selectedStrategyId]);

  useEffect(() => {
    setRuntimeConfig((previous) => ({
      ...previous,
      risk: {
        ...previous.risk,
        initial_capital: safeNumber(initialCapital, previous.risk.initial_capital || 100000),
      },
    }));
  }, [initialCapital]);

  const updateRuntimeSection = useCallback((section: keyof RuntimeConfig, key: string, value: unknown) => {
    setSelectedRuntimePresetId((previous) => previous === "CUSTOM" ? previous : "CUSTOM");
    setRuntimeConfig((previous) => ({
      ...previous,
      [section]: {
        ...(previous[section] as Record<string, unknown>),
        [key]: value,
      },
    }));
  }, []);

  const updateStrategyParam = useCallback((key: string, value: string | number | boolean | null) => {
    setSelectedRuntimePresetId((previous) => previous === "CUSTOM" ? previous : "CUSTOM");
    setRuntimeConfig((previous) => ({
      ...previous,
      strategy_params: {
        ...previous.strategy_params,
        [key]: value,
      },
    }));
  }, []);

  const resetRuntimeSettings = useCallback(() => {
    const nextDefaults = cloneRuntimeConfig(runtimeDefaults);
    nextDefaults.risk.initial_capital = safeNumber(initialCapital, nextDefaults.risk.initial_capital || 100000);
    setRuntimeConfig(nextDefaults);
    setSelectedRuntimePresetId("DEFAULT");
  }, [initialCapital, runtimeDefaults]);

  const applyRuntimePreset = useCallback((presetId: string) => {
    setSelectedRuntimePresetId(presetId);
    if (presetId === "DEFAULT") {
      const nextDefaults = cloneRuntimeConfig(runtimeDefaults);
      nextDefaults.risk.initial_capital = safeNumber(initialCapital, nextDefaults.risk.initial_capital || 100000);
      setRuntimeConfig(nextDefaults);
      return;
    }
    if (presetId === "CUSTOM") return;
    const preset = runtimePresets.find((item) => String(item.id) === String(presetId));
    const presetConfig = (preset?.config_json || preset?.configJson || {}) as Partial<RuntimeConfig>;
    const merged = mergeRuntimeConfig(runtimeDefaults, presetConfig);
    merged.risk.initial_capital = safeNumber(initialCapital, merged.risk.initial_capital || 100000);
    setRuntimeConfig(merged);
  }, [initialCapital, runtimeDefaults, runtimePresets]);

  const buildRuntimeConfigForRequest = useCallback((): Record<string, unknown> => {
    const riskWithoutCurrency = { ...runtimeConfig.risk };
    delete (riskWithoutCurrency as { account_currency?: unknown }).account_currency;
    return {
      ...runtimeConfig,
      risk: {
        ...riskWithoutCurrency,
        initial_capital: safeNumber(initialCapital, runtimeConfig.risk.initial_capital || 100000),
      },
      execution: {
        ...runtimeConfig.execution,
        intraday_square_off: supportsIntradaySquareOff ? Boolean(runtimeConfig.execution.intraday_square_off) : false,
      },
    };
  }, [initialCapital, runtimeConfig, supportsIntradaySquareOff]);

  useEffect(() => {
    if (!supportsIntradaySquareOff && runtimeConfig.execution.intraday_square_off) {
      updateRuntimeSection("execution", "intraday_square_off", false);
    }
  }, [runtimeConfig.execution.intraday_square_off, supportsIntradaySquareOff, updateRuntimeSection]);

  const runtimeRequestSignature = useMemo(() => JSON.stringify(buildRuntimeConfigForRequest()), [buildRuntimeConfigForRequest]);

  const requestSignature = useMemo(
    () =>
      [selectedStrategyId, selectedInstrumentId, selectedTimeframe, startDate, endDate, initialCapital, advancedFilterSignature, selectedRuntimePresetId || "DEFAULT", runtimeRequestSignature]
        .map((item) => (item ?? "").toString().trim())
        .join("|"),
    [selectedStrategyId, selectedInstrumentId, selectedTimeframe, startDate, endDate, initialCapital, advancedFilterSignature, selectedRuntimePresetId, runtimeRequestSignature],
  );

  const validationErrors = useMemo(() => {
    const messages: string[] = [];
    if (!selectedStrategyId) messages.push("Select a strategy.");
    if (!selectedInstrumentId) messages.push("Select an instrument.");
    if (!selectedTimeframe) messages.push("Select a timeframe.");
    if (!startDate || !endDate) messages.push("Select a valid date range.");

    const capitalValue = safeNumber(initialCapital, 0);
    if (capitalValue <= 0) messages.push("Initial capital must be greater than 0.");

    if (startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      if (Number.isFinite(start.getTime()) && Number.isFinite(end.getTime()) && start >= end) {
        messages.push("End date must be after start date.");
      }

      // BF-1A: Date range is credit-based now. max_date_range_days is kept
      // only as a soft preview warning, not as a hard execution blocker.
    }

    if (advancedFiltersEnabled && selectedSession === "CUSTOM") {
      if (!isValidTimeValue(customStartTime) || !isValidTimeValue(customEndTime)) {
        messages.push("Custom time window must use valid HH:mm start and end times.");
      }
    }

    return messages;
  }, [
    selectedStrategyId,
    selectedInstrumentId,
    selectedTimeframe,
    startDate,
    endDate,
    initialCapital,
    limits,
    advancedFiltersEnabled,
    selectedSession,
    customStartTime,
    customEndTime,
  ]);

  const isReadyForRun = validationErrors.length === 0;

  const loadInitialData = useCallback(async () => {
    setInitialLoading(true);
    setInitialError(null);

    try {
      const [configResult, strategyResult] = await Promise.allSettled([
        backtestsApi.getConfig(),
        backtestsApi.getStrategiesCatalog(),
      ]);

      let nextStrategies: StrategyOption[] = [];
      let nextInstruments: InstrumentOption[] = [];
      let nextTimeframes: string[] = [];

      if (configResult.status === "fulfilled") {
        const configData = configResult.value;
        nextInstruments = configData.instruments || [];
        nextTimeframes = configData.timeframes || [];
        setLimits(configData.limits || null);

        setCreditSnapshot({
          totalAvailable: safeNumber(
            configData.credits?.total_available ?? configData.credits?.current_balance ?? configData.credits?.balance,
            0,
          ),
          walletBalance: safeNumber(configData.credits?.wallet_balance, 0),
          includedBalance: safeNumber(configData.credits?.included_balance ?? configData.credits?.included, 0),
          deductionOrder: Array.isArray(configData.credits?.deduction_order)
            ? configData.credits?.deduction_order
            : ["subscription", "wallet"],
          subscriptionState: configData.credits?.subscription_state ?? null,
        });

        nextStrategies = (configData.strategies || []).map((item) => ({
          id: item.id,
          name: item.name,
        }));
      }

      if (strategyResult.status === "fulfilled") {
        const catalog = strategyResult.value;
        const byId = new Map<string, StrategyOption>();

        catalog.forEach((item) => byId.set(item.id, item));
        nextStrategies.forEach((item) => {
          byId.set(item.id, {
            ...byId.get(item.id),
            ...item,
          });
        });

        nextStrategies = Array.from(byId.values());
      }

      if (!nextStrategies.length) {
        throw new Error("Unable to load strategy catalog. Please refresh and try again.");
      }

      try {
        const masterInstruments = await backtestsApi.getInstruments();
        if (masterInstruments.length) {
          if (nextInstruments.length) {
            const masterById = new Map(masterInstruments.map((item) => [String(item.id), item]));
            const masterBySymbol = new Map(masterInstruments.map((item) => [String(item.symbol || "").toUpperCase(), item]));
            nextInstruments = nextInstruments.map((item) => {
              const master = masterById.get(String(item.id)) || masterBySymbol.get(String(item.symbol || "").toUpperCase());
              return master ? { ...item, ...master } : item;
            });
          } else {
            nextInstruments = masterInstruments;
          }
        }
      } catch {
        // Keep config instruments when the Phase 2A master endpoint is unavailable.
      }

      if (!nextTimeframes.length) {
        try {
          nextTimeframes = await backtestsApi.getTimeframes();
        } catch {
          nextTimeframes = ["1d"];
        }
      }

      setStrategies(nextStrategies);
      setInstruments(nextInstruments);
      setTimeframes(nextTimeframes);

      const queryStrategyId = searchParams.get("strategyId");
      const queryInstrumentId = searchParams.get("instrumentId");
      const querySymbol = searchParams.get("symbol");

      if (queryStrategyId && nextStrategies.some((item) => item.id === queryStrategyId)) {
        setSelectedStrategyId(queryStrategyId);
      } else if (nextStrategies.length === 1) {
        setSelectedStrategyId(nextStrategies[0].id);
      }

      if (queryInstrumentId && nextInstruments.some((item) => String(item.id) === queryInstrumentId)) {
        setSelectedInstrumentId(queryInstrumentId);
      } else if (querySymbol) {
        const bySymbol = nextInstruments.find((item) => item.symbol.toLowerCase() === querySymbol.toLowerCase());
        if (bySymbol) setSelectedInstrumentId(String(bySymbol.id));
      }

      if (nextTimeframes.length && !selectedTimeframe) {
        setSelectedTimeframe(nextTimeframes.includes("1d") ? "1d" : nextTimeframes[0]);
      }
    } catch (error) {
      const parsed = parseApiError(error);
      setInitialError(formatErrorMessage(parsed));
    } finally {
      setInitialLoading(false);
    }
  }, [searchParams, selectedTimeframe]);

  useEffect(() => {
    void loadInitialData();
  }, [loadInitialData]);

  useEffect(() => {
    if (!selectedInstrumentId) return;

    let active = true;
    const loadInstrumentTimeframes = async () => {
      try {
        const list = await backtestsApi.getTimeframes(Number(selectedInstrumentId));
        if (!active || !list.length) return;
        setTimeframes(list);
        if (!list.includes(selectedTimeframe)) {
          setSelectedTimeframe(list[0]);
        }
      } catch {
        // Silently keep current timeframes to avoid interrupting UX.
      }
    };

    void loadInstrumentTimeframes();
    return () => {
      active = false;
    };
  }, [selectedInstrumentId, selectedTimeframe]);

  useEffect(() => {
    setPreviewError(null);
    setPreviewWarnings([]);
    setAvailability(null);
    setCostPreview(null);
    setLastPreviewSignature("");
  }, [requestSignature]);

  const runPreview = useCallback(async (): Promise<{ availability: DataAvailabilityResponse; cost: CostPreviewResponse } | null> => {
    if (!isReadyForRun) {
      setPreviewError(validationErrors[0] || "Please complete all required fields.");
      return null;
    }

    setIsPreviewing(true);
    setPreviewError(null);
    setRunError(null);

    try {
      const instrumentId = Number(selectedInstrumentId);
      const [availabilityData, costData] = await Promise.all([
        backtestsApi.getDataAvailability({
          instrument_id: instrumentId,
          timeframe: selectedTimeframe,
          start_date: startDate,
          end_date: endDate,
        }),
        backtestsApi.previewCost({
          strategy_id: selectedStrategyId,
          instrument_id: instrumentId,
          timeframe: selectedTimeframe,
          start_date: startDate,
          end_date: endDate,
          capital: safeNumber(initialCapital, 0),
          advanced_filters: advancedFilterPayload,
        }),
      ]);

      setAvailability(availabilityData);
      setCostPreview(costData);
      setLastPreviewSignature(requestSignature);
      setCreditSnapshot((previous) => ({
        totalAvailable: safeNumber(costData.balances?.total_available, previous?.totalAvailable ?? 0),
        walletBalance: safeNumber(costData.balances?.wallet_balance, previous?.walletBalance ?? 0),
        includedBalance: safeNumber(costData.balances?.included_balance, previous?.includedBalance ?? 0),
        deductionOrder: previous?.deductionOrder || ["subscription", "wallet"],
        subscriptionState: costData.subscription_state ?? previous?.subscriptionState ?? null,
      }));

      const warnings: string[] = [];
      const start = new Date(startDate);
      const end = new Date(endDate);
      const diffDays = Math.floor((end.getTime() - start.getTime()) / (24 * 60 * 60 * 1000));
      if (limits?.max_date_range_days && Number.isFinite(diffDays) && diffDays > limits.max_date_range_days) {
        warnings.push("Large date range selected. Preview will estimate candle count, runtime, and credit cost.");
      }
      if (!availabilityData.available || (availabilityData.requested_candle_count || 0) <= 0) {
        warnings.push(availabilityData.message || "Market data is missing for this instrument/timeframe/date range. Ask admin to import missing candles.");
      }
      const backendWarnings = Array.isArray(costData.warnings) ? costData.warnings.filter(Boolean) : [];
      warnings.push(...backendWarnings);
      const filteredCount = costData.data_coverage?.filtered_candles ?? availabilityData.requested_candle_count;
      if (filteredCount > 100000) {
        warnings.push("Large candle scope detected. Execution may be slower and cost more credits.");
      }
      if (costData.cost_feasible === false) {
        warnings.push("Insufficient credits for this run. Reduce scope or add credits.");
      }
      if (costData.can_run === false && costData.cost_feasible !== false) {
        warnings.push("Preview is not feasible for this filter scope. Review the filtered candle count before running.");
      }
      setPreviewWarnings(warnings);

      return { availability: availabilityData, cost: costData };
    } catch (error) {
      const parsed = parseApiError(error);
      setPreviewError(formatErrorMessage(parsed));
      return null;
    } finally {
      setIsPreviewing(false);
    }
  }, [
    initialCapital,
    isReadyForRun,
    requestSignature,
    selectedInstrumentId,
    selectedStrategyId,
    selectedTimeframe,
    startDate,
    endDate,
    limits,
    validationErrors,
    advancedFilterPayload,
    buildRuntimeConfigForRequest,
    selectedRuntimePresetId,
  ]);

  const loadResultDetail = useCallback(async (backtestId: string) => {
    try {
      const detail = await backtestsApi.getDetail(backtestId);
      setResultDetail(detail);
    } catch {
      // Keep UX stable even if detail endpoint fails.
      setResultDetail(null);
    }
  }, []);

  const runBacktest = useCallback(async () => {
    setRunError(null);
    setRunResponse(null);
    setResultDetail(null);

    if (!isReadyForRun) {
      setRunError(validationErrors[0] || "Please complete all required fields.");
      return;
    }

    if (lastPreviewSignature !== requestSignature || !availability || !costPreview) {
      setRunError("Preview Data First. Preview validates candle availability, estimated cost, filters, and selected instrument before execution.");
      return;
    }

    const previewData = { availability, cost: costPreview } as {
      availability: DataAvailabilityResponse | null;
      cost: CostPreviewResponse | null;
    };

    if (!previewData.availability?.available || (previewData.availability.requested_candle_count || 0) <= 0) {
      setRunError(previewData.availability?.message || "Market data is missing for this instrument/timeframe/date range. Ask admin to import missing candles.");
      return;
    }

    if (!previewData.cost?.can_run) {
      if (previewData.cost?.cost_feasible === false) {
        setRunError("Insufficient credit balance for this run. Adjust scope or add credits.");
        setInsufficientCreditsHint({
          needed: safeNumber(previewData.cost?.total_cost, 0),
          walletBalance: safeNumber(previewData.cost?.balances?.wallet_balance, 0),
          includedBalance: safeNumber(previewData.cost?.balances?.included_balance, 0),
        });
      } else {
        setInsufficientCreditsHint(null);
        setRunError(
          previewData.cost?.warnings?.[0] ||
            "Preview is not feasible for this filter scope. Increase the range or relax advanced filters before running.",
        );
      }
      return;
    }

    setIsRunning(true);
    try {
      const response = await backtestsApi.run({
        strategy_id: selectedStrategyId,
        instrument_id: Number(selectedInstrumentId),
        timeframe: selectedTimeframe,
        start_date: startDate,
        end_date: endDate,
        capital: safeNumber(initialCapital, 0),
        save_result: true,
        advanced_filters: advancedFilterPayload,
        runtime_config: buildRuntimeConfigForRequest(),
        strategy_preset_id: selectedRuntimePresetId && selectedRuntimePresetId !== "DEFAULT" && selectedRuntimePresetId !== "CUSTOM" ? selectedRuntimePresetId : null,
      });

      setRunResponse(response);
      setCreditSnapshot((previous) => {
        const nextWallet = typeof response.credits?.balance_after === "number"
          ? safeNumber(response.credits.balance_after, 0)
          : previous?.walletBalance ?? 0;
        const nextIncluded = typeof response.credits?.included_balance_after === "number"
          ? safeNumber(response.credits.included_balance_after, 0)
          : previous?.includedBalance ?? 0;
        const nextTotal = typeof response.credits?.total_balance_after === "number"
          ? safeNumber(response.credits.total_balance_after, nextWallet + nextIncluded)
          : nextWallet + nextIncluded;

        return {
          totalAvailable: nextTotal,
          walletBalance: nextWallet,
          includedBalance: nextIncluded,
          deductionOrder: response.credits?.deduction_order || previous?.deductionOrder || ["subscription", "wallet"],
          subscriptionState: response.credits?.subscription_state ?? previous?.subscriptionState ?? null,
        };
      });

      const backtestId = response.backtest_id || response.result?.backtest_id;
      if (backtestId) {
        await loadResultDetail(backtestId);
      }
    } catch (error) {
      const parsed = parseApiError(error);
      const detail = parsed.raw?.detail;
      if (detail && typeof detail === "object" && detail.code === "INSUFFICIENT_CREDITS") {
        setInsufficientCreditsHint({
          needed: safeNumber(detail.needed, 0),
          walletBalance: safeNumber(detail.wallet_balance, 0),
          includedBalance: safeNumber(detail.included_balance, 0),
        });
      } else {
        setInsufficientCreditsHint(null);
      }

      if (detail && typeof detail === "object" && detail.code === "MARKET_DATA_UNAVAILABLE") {
        const coverage = [
          detail.record_count !== undefined ? `Records found: ${detail.record_count}` : null,
          detail.available_start && detail.available_end ? `Available: ${new Date(detail.available_start).toLocaleString()} to ${new Date(detail.available_end).toLocaleString()}` : null,
        ].filter(Boolean).join(" · ");
        setRunError(`${detail.message || "Data unavailable. Ask admin to import market data for this instrument/timeframe/date range."}${coverage ? `\n${coverage}` : ""}`);
      } else {
        setRunError(formatErrorMessage(parsed));
      }
    } finally {
      setIsRunning(false);
    }
  }, [
    availability,
    costPreview,
    creditSnapshot,
    initialCapital,
    isReadyForRun,
    lastPreviewSignature,
    loadResultDetail,
    requestSignature,
    runPreview,
    selectedInstrumentId,
    selectedStrategyId,
    selectedTimeframe,
    startDate,
    endDate,
    validationErrors,
    advancedFilterPayload,
    buildRuntimeConfigForRequest,
    selectedRuntimePresetId,
  ]);

  const resultSummary = useMemo(() => {
    if (resultDetail?.summary) return resultDetail.summary;
    return runResponse?.result || null;
  }, [resultDetail, runResponse]);

  const previewCoverage = costPreview?.data_coverage;
  const requestedCandleCount = availability?.requested_candle_count || 0;
  const candlesBeforeFilters = previewCoverage?.total_candles ?? requestedCandleCount;
  const candlesAfterFilters = previewCoverage?.filtered_candles ?? candlesBeforeFilters;
  const candlesRemovedByFilters = previewCoverage?.candles_removed ?? Math.max(candlesBeforeFilters - candlesAfterFilters, 0);
  const filterReductionPct = previewCoverage?.filter_reduction_pct ?? 0;
  const previewFilterSummary = costPreview?.advanced_filters?.summary || activeFilterSummary;
  const estimatedCost = costPreview?.total_cost ?? null;
  const totalAvailableCredits = creditSnapshot?.totalAvailable ?? null;
  const subscriptionCredits = creditSnapshot?.includedBalance ?? 0;
  const walletCredits = creditSnapshot?.walletBalance ?? 0;
  const deductionOrderLabel = (creditSnapshot?.deductionOrder || ["subscription", "wallet"])
    .map((item) => item.charAt(0).toUpperCase() + item.slice(1))
    .join(" → ");
  const postRunBalance =
    totalAvailableCredits !== null && estimatedCost !== null ? Math.max(totalAvailableCredits - estimatedCost, 0) : null;
  const isCreditInsufficient = Boolean(costPreview && costPreview.cost_feasible === false);
  const isPreviewNotFeasible = Boolean(costPreview && costPreview.can_run === false);
  const previewIsCurrent = Boolean(lastPreviewSignature && lastPreviewSignature === requestSignature && availability && costPreview);
  const hasPreviewEverRun = Boolean(lastPreviewSignature);
  const previewStatus: "idle" | "loading" | "success" | "error" | "stale" = isPreviewing
    ? "loading"
    : previewError
      ? "error"
      : previewIsCurrent
        ? "success"
        : hasPreviewEverRun
          ? "stale"
          : "idle";
  const canRunBacktest = isReadyForRun && previewIsCurrent && !isPreviewNotFeasible && !isPreviewing && !isRunning;
  const runButtonLabel = isRunning
    ? "Running Backtest..."
    : isPreviewing
      ? "Previewing..."
    : isCreditInsufficient
      ? "Insufficient Credits"
      : isPreviewNotFeasible
        ? "Preview Not Feasible"
        : previewStatus === "stale"
          ? "Preview Updated Data"
          : previewStatus === "idle" || previewStatus === "error"
            ? "Preview Data First"
            : "Run Backtest";
  const resultCurrencySymbol = resultSummary?.currency_symbol || currencySymbolForCode(resultSummary?.account_currency) || selectedInstrument?.currency_symbol || currencySymbolForCode(selectedInstrument?.account_currency);
  const resultQuantityMode = resultSummary?.quantity_mode || selectedInstrument?.quantity_mode || "SHARES";

  const equityChartRows = useMemo(
    () =>
      (resultDetail?.equity_curve || []).slice(-240).map((point) => ({
        label: point.timestamp ? new Date(point.timestamp).toLocaleDateString() : "",
        equity: safeNumber(point.equity, 0),
      })),
    [resultDetail?.equity_curve],
  );

  if (initialLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <div className="h-8 w-56 animate-pulse rounded-xl bg-card/40" />
          <div className="h-5 w-80 animate-pulse rounded-xl bg-card/40" />
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-xl border border-border/50 bg-card/30 backdrop-blur-xl" />
          ))}
        </div>
        <div className="h-80 animate-pulse rounded-xl border border-border/50 bg-card/30 backdrop-blur-xl" />
      </div>
    );
  }

  if (initialError) {
    return (
      <EmptyState
        title="Unable to load Backtest workspace"
        description={initialError}
        action={
          <Button onClick={() => void loadInitialData()} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
            <RefreshCcw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        }
      />
    );
  }

  const netProfit = safeNumber(resultSummary?.net_profit, 0);
  const initialCap = safeNumber(resultSummary?.initial_capital, safeNumber(initialCapital, 0));
  const finalCap = safeNumber(resultSummary?.final_capital, initialCap + netProfit);
  const returnPct = initialCap > 0 ? ((finalCap - initialCap) / initialCap) * 100 : 0;
  const runtimeCurrency = instrumentCurrency;
  const runtimeQuantityMode = instrumentQuantityMode;
  const strategyParamEntries = Object.entries(runtimeSchema);
  const runtimeTabs: Array<{ value: RuntimeTab; label: string }> = [
    { value: "risk", label: "Risk" },
    { value: "sl_tp", label: "SL / TP" },
    { value: "execution", label: "Execution" },
    { value: "trade_management", label: "Trade Mgmt" },
    { value: "strategy_params", label: "Strategy Params" },
  ];
  const positionSizeMode = runtimeConfig.risk.position_size_mode || "RISK_BASED";
  const slMode = runtimeConfig.sl_tp.sl_mode || "ATR";
  const breakEvenEnabled = Boolean(runtimeConfig.trade_management.break_even_enabled);
  const trailingEnabled = Boolean(runtimeConfig.trade_management.trailing_enabled);
  const partialExitEnabled = Boolean(runtimeConfig.trade_management.partial_exit_enabled);

  const runtimeGuardrailMessages = (() => {
    const messages: string[] = [];
    const capital = safeNumber(initialCapital, 0);
    const riskPct = safeNumber(runtimeConfig.risk.risk_percent, 0);
    const rrRatio = safeNumber(runtimeConfig.sl_tp.rr_ratio, 0);
    const atrPeriod = safeNumber(runtimeConfig.sl_tp.atr_period, 0);
    const atrMultiplier = safeNumber(runtimeConfig.sl_tp.atr_multiplier, 0);
    const swingLookback = safeNumber(runtimeConfig.sl_tp.swing_lookback, 0);
    const fixedPriceRiskPct = safeNumber(runtimeConfig.sl_tp.fixed_price_risk_pct, 0);
    const maxOpenPositions = runtimeConfig.execution.max_open_positions ?? 1;
    const maxTradesPerDay = runtimeConfig.execution.max_trades_per_day;
    const breakEvenTrigger = safeNumber(runtimeConfig.trade_management.break_even_trigger_r, 0);
    const trailStart = safeNumber(runtimeConfig.trade_management.trail_start_r, 0);
    const trailAtrMultiplier = safeNumber(runtimeConfig.trade_management.trail_atr_multiplier, 0);

    if (capital <= 0) messages.push("Initial capital must be greater than 0.");
    if (riskPct < 0.001 || riskPct > 0.05) messages.push("Capital risk must stay between 0.10% and 5.00%.");
    if (rrRatio < 1 || rrRatio > 5) messages.push("RR ratio must stay between 1 and 5.");
    if (slMode === "ATR" && (atrPeriod < 5 || atrPeriod > 100)) messages.push("ATR period must stay between 5 and 100.");
    if (slMode === "ATR" && (atrMultiplier < 0.5 || atrMultiplier > 5)) messages.push("ATR multiplier must stay between 0.5 and 5.");
    if (slMode === "SWING" && (swingLookback < 2 || swingLookback > 50)) messages.push("Swing lookback must stay between 2 and 50.");
    if (slMode === "FIXED_PERCENT" && (fixedPriceRiskPct < 0.001 || fixedPriceRiskPct > 0.05)) messages.push("Fixed price risk must stay between 0.10% and 5.00%.");
    if (positionSizeMode === "FIXED_LOT" && safeNumber(runtimeConfig.risk.fixed_lot, 0) <= 0) messages.push("Fixed lot size must be greater than 0.");
    if (positionSizeMode === "FIXED_QUANTITY" && safeNumber(runtimeConfig.risk.fixed_quantity, 0) <= 0) messages.push("Fixed quantity must be greater than 0.");
    if (positionSizeMode !== "FIXED_QUANTITY" && runtimeConfig.risk.max_lot_cap !== null && runtimeConfig.risk.max_lot_cap !== undefined && safeNumber(runtimeConfig.risk.max_lot_cap, 0) <= 0) messages.push("Max lot cap must be empty or greater than 0.");
    if (positionSizeMode === "FIXED_QUANTITY" && runtimeConfig.risk.max_quantity_cap !== null && runtimeConfig.risk.max_quantity_cap !== undefined && safeNumber(runtimeConfig.risk.max_quantity_cap, 0) <= 0) messages.push("Max quantity cap must be empty or greater than 0.");
    if (maxTradesPerDay !== null && maxTradesPerDay !== undefined && safeNumber(maxTradesPerDay, 0) < 1) messages.push("Max trades per day must be empty or at least 1.");
    if (safeNumber(maxOpenPositions, 0) < 1 || safeNumber(maxOpenPositions, 0) > 5) messages.push("Max open positions must stay between 1 and 5.");
    if (breakEvenEnabled && (breakEvenTrigger < 0.5 || breakEvenTrigger > 5)) messages.push("Break-even trigger must stay between 0.5R and 5R.");
    if (trailingEnabled && (trailStart < 0.5 || trailStart > 5)) messages.push("Trail start must stay between 0.5R and 5R.");
    if (trailingEnabled && (trailAtrMultiplier < 0.5 || trailAtrMultiplier > 5)) messages.push("Trail ATR multiplier must stay between 0.5 and 5.");

    return messages;
  })();

  const runtimeWarningMessages = (() => {
    const messages: string[] = [];
    const riskPct = safeNumber(runtimeConfig.risk.risk_percent, 0);
    const fixedLot = safeNumber(runtimeConfig.risk.fixed_lot, 0);
    if (riskPct > 0.03) messages.push("Risk above 3% is aggressive. Use this only for testing or high-conviction systems.");
    if (positionSizeMode === "FIXED_LOT" && fixedLot >= 1) messages.push("Fixed lot looks high. Confirm broker leverage, margin and account balance before live use.");
    return messages;
  })();

  const runtimeSettingsValid = runtimeGuardrailMessages.length === 0;

  const renderPresetSelect = (
    label: string,
    value: number | null | undefined,
    options: PresetNumberOption[],
    onValueChange: (next: number) => void,
    help?: string,
  ) => (
    <div className="space-y-2">
      <Label className="text-muted-foreground"><FieldLabel label={label} help={help} /></Label>
      <Select value={String(value ?? options[0]?.value ?? "")} onValueChange={(next) => onValueChange(safeNumber(next, options[0]?.value ?? 0))}>
        <SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground"><SelectValue /></SelectTrigger>
        <SelectContent className="z-[130] rounded-xl border-border/60 bg-[#34135c] text-foreground">
          {options.map((option) => <SelectItem key={`${label}-${option.value}`} value={String(option.value)}>{option.label}</SelectItem>)}
        </SelectContent>
      </Select>
      {help ? <p className="text-[11px] leading-relaxed text-muted-foreground">{help}</p> : null}
    </div>
  );

  
const FieldLabel = ({ label, help }: { label: string; help?: string }) => (
  <span className="inline-flex items-center gap-1.5 text-muted-foreground">
    {label}
    <FieldHelpTooltip label={`${label} help`} content={help || FIELD_HELP[label] || STRATEGY_PARAM_HELP} />
  </span>
);

  const runtimeSettingsModal = runtimeSettingsOpen ? (
    <div className="fixed inset-0 z-[120] flex items-stretch justify-end bg-black/55 backdrop-blur-sm">
      <button
        type="button"
        aria-label="Close strategy settings overlay"
        className="absolute inset-0 cursor-default"
        onClick={() => setRuntimeSettingsOpen(false)}
      />
      <aside className="relative z-[121] flex h-full w-full max-w-3xl flex-col border-l border-border/60 bg-[#211042]/95 shadow-2xl backdrop-blur-xl">
        <div className="flex items-start justify-between gap-4 border-b border-border/50 px-5 py-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold text-foreground">Strategy Runtime Settings</h2>
              <Badge className={runtimeIsCustom ? "border-primary/50 bg-primary/20 text-primary-foreground" : "border-border/60 bg-card/30 text-muted-foreground"}>
                {selectedRuntimePresetId === "CUSTOM" || runtimeIsCustom ? "Custom" : selectedRuntimePresetId === "DEFAULT" ? "Default" : (runtimePresets.find((item) => String(item.id) === String(selectedRuntimePresetId))?.name || "Preset")}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">Configure risk, SL/TP, execution and dynamic strategy inputs for this backtest only.</p>
          </div>
          <Button type="button" variant="ghost" size="sm" className="rounded-xl" onClick={() => setRuntimeSettingsOpen(false)}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="border-b border-border/50 px-5 py-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_auto] md:items-end">
            <div className="space-y-2">
              <Label className="text-muted-foreground"><FieldLabel label="Runtime Preset" /></Label>
              <Select value={selectedRuntimePresetId} onValueChange={applyRuntimePreset}>
                <SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground">
                  <SelectValue placeholder="Strategy Default" />
                </SelectTrigger>
                <SelectContent className="z-[130] rounded-xl border-border/60 bg-[#34135c] text-foreground">
                  <SelectItem value="DEFAULT">Strategy Default</SelectItem>
                  {runtimePresets.map((preset) => (
                    <SelectItem key={preset.id} value={String(preset.id)}>
                      {preset.name}{preset.is_default || preset.isDefault ? " · Default" : ""}
                    </SelectItem>
                  ))}
                  <SelectItem value="CUSTOM">Custom</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-[11px] text-muted-foreground">Presets are managed by admin. You can select one and still fine-tune settings for this run.</p>
            </div>
            <Badge className="w-fit border-primary/40 bg-primary/15 text-primary-foreground">Runtime only</Badge>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 border-b border-border/50 px-5 py-4 md:grid-cols-6">
          <div className="rounded-xl border border-border/50 bg-card/20 p-3 md:col-span-2">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Instrument</p>
            <p className="mt-1 text-sm font-semibold text-foreground">{selectedInstrument?.symbol || "—"}</p>
          </div>
          <div className="rounded-xl border border-border/50 bg-card/20 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Currency</p>
            <p className="mt-1 text-sm font-semibold text-foreground">{runtimeCurrency}</p>
          </div>
          <div className="rounded-xl border border-border/50 bg-card/20 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Qty Mode</p>
            <p className="mt-1 text-sm font-semibold text-foreground">{runtimeQuantityMode}</p>
          </div>
          <div className="rounded-xl border border-border/50 bg-card/20 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Risk</p>
            <p className="mt-1 text-sm font-semibold text-foreground">{formatPercent(safeNumber(runtimeConfig.risk.risk_percent, 0), true)}</p>
          </div>
          <div className="rounded-xl border border-border/50 bg-card/20 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">RR / SL</p>
            <p className="mt-1 text-sm font-semibold text-foreground">{runtimeConfig.sl_tp.rr_ratio} · {runtimeConfig.sl_tp.sl_mode}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 border-b border-border/50 px-5 py-3">
          {runtimeTabs.map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => setRuntimeTab(tab.value)}
              className={`rounded-xl border px-3 py-2 text-xs font-medium transition ${
                runtimeTab === tab.value
                  ? "border-primary/60 bg-primary/20 text-primary-foreground"
                  : "border-border/60 bg-card/20 text-muted-foreground hover:bg-card/40 hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5">
          {runtimeConfigLoading && (
            <div className="mb-4 rounded-xl border border-sky-500/40 bg-sky-500/10 px-4 py-3 text-sm text-sky-100">Loading strategy runtime defaults...</div>
          )}
          {runtimeConfigError && (
            <div className="mb-4 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              Runtime config API fallback is active: {runtimeConfigError}
            </div>
          )}
          {runtimeGuardrailMessages.length > 0 && (
            <div className="mb-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              <div className="mb-1 font-semibold">Fix these runtime settings before applying:</div>
              <ul className="list-disc space-y-1 pl-5">
                {runtimeGuardrailMessages.map((message) => <li key={message}>{message}</li>)}
              </ul>
            </div>
          )}
          {runtimeWarningMessages.length > 0 && (
            <div className="mb-4 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              <div className="mb-1 font-semibold">Risk warning</div>
              <ul className="list-disc space-y-1 pl-5">
                {runtimeWarningMessages.map((message) => <li key={message}>{message}</li>)}
              </ul>
            </div>
          )}

          <RuntimeSettingsForm
            activeTab={runtimeTab}
            config={runtimeConfig as any}
            updateSection={updateRuntimeSection as any}
            strategySchema={runtimeSchema as any}
            updateStrategyParam={updateStrategyParam as any}
            initialCapital={initialCapital}
            onInitialCapitalChange={setInitialCapital}
            currency={runtimeCurrency}
            instrumentSymbol={selectedInstrument?.symbol || "this instrument"}
            supportsIntradaySquareOff={supportsIntradaySquareOff}
            mode="backtest"
          />
        </div>

        <div className="flex flex-col gap-3 border-t border-border/50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">Settings are sent with the next backtest request only. Instrument currency, quantity mode, ticks and lot steps are admin controlled.</p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={resetRuntimeSettings} className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">
              Reset to Defaults
            </Button>
            <Button
              type="button"
              disabled={!runtimeSettingsValid}
              onClick={() => setRuntimeSettingsOpen(false)}
              className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Apply Settings
            </Button>
          </div>
        </div>
      </aside>
    </div>
  ) : null;

  return (
    <div className="space-y-6">
      {runtimeSettingsModal}
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">Backtest Studio</h1>
        <p className="text-sm text-muted-foreground">
          Configure strategy, validate data and credits, then run a stable backtest with production market data.
        </p>
        <p className="text-xs text-muted-foreground">
          Tip: run preview before execution to validate coverage, candle scope, and credit impact.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription className="text-muted-foreground">Available Credits</CardDescription>
            <CardTitle className="text-2xl text-foreground">{formatNumber(totalAvailableCredits, 0)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">
            <div className="inline-flex items-center gap-2">
              <Wallet className="h-4 w-4" />
              Deduction order: {deductionOrderLabel}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription className="text-muted-foreground">Subscription Credits</CardDescription>
            <CardTitle className="text-2xl text-foreground">{formatNumber(subscriptionCredits, 0)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">
            Included plan credits remaining in current cycle
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription className="text-muted-foreground">Wallet Credits</CardDescription>
            <CardTitle className="text-2xl text-foreground">{formatNumber(walletCredits, 0)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">
            Manual top-up credits that stay after plan usage
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription className="text-muted-foreground">Estimated Run Cost</CardDescription>
            <CardTitle className="text-2xl text-foreground">{estimatedCost !== null ? formatNumber(estimatedCost, 0) : "—"}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">
            <div className="inline-flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Based on timeframe, range, and candle volume
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription className="text-muted-foreground">Balance After Run</CardDescription>
            <CardTitle className={`text-2xl ${postRunBalance !== null && postRunBalance > 0 ? "text-foreground" : "text-rose-300"}`}>
              {postRunBalance !== null ? formatNumber(postRunBalance, 0) : "—"}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">
            {isCreditInsufficient ? "Insufficient credits for current scope" : "Projected total after deduction"}
          </CardContent>
        </Card>
      </section>

      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardHeader>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <CardTitle className="text-xl text-foreground">Backtest Configuration</CardTitle>
              <CardDescription className="text-muted-foreground">
                Select strategy, market scope, and execution settings before preview.
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() => setRuntimeSettingsOpen(true)}
              className="w-fit rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
            >
              <SlidersHorizontal className="mr-2 h-4 w-4" />
              Strategy Settings
              <Badge className={`ml-2 ${runtimeIsCustom ? "border-primary/50 bg-primary/20 text-primary-foreground" : "border-border/60 bg-card/30 text-muted-foreground"}`}>
                {selectedRuntimePresetId === "CUSTOM" || runtimeIsCustom ? "Custom" : selectedRuntimePresetId === "DEFAULT" ? "Default" : (runtimePresets.find((item) => String(item.id) === String(selectedRuntimePresetId))?.name || "Preset")}
              </Badge>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-2">
              <Label className="text-muted-foreground">Strategy</Label>
              <Select value={selectedStrategyId} onValueChange={setSelectedStrategyId}>
                <SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground data-[placeholder]:text-muted-foreground">
                  <SelectValue placeholder="Select strategy" />
                </SelectTrigger>
                <SelectContent className="z-[90] rounded-xl border-border/60 bg-[#34135c] text-foreground">
                  {strategies.map((strategy) => (
                    <SelectItem key={strategy.id} value={strategy.id}>
                      {strategy.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-muted-foreground">Instrument</Label>
              <Select value={selectedInstrumentId} onValueChange={setSelectedInstrumentId}>
                <SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground data-[placeholder]:text-muted-foreground">
                  <SelectValue placeholder="Select instrument" />
                </SelectTrigger>
                <SelectContent className="z-[90] rounded-xl border-border/60 bg-[#34135c] text-foreground">
                  {instruments.map((instrument) => (
                    <SelectItem key={instrument.id} value={String(instrument.id)}>
                      {instrument.symbol}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-muted-foreground">Timeframe</Label>
              <Select value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
                <SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground data-[placeholder]:text-muted-foreground">
                  <SelectValue placeholder="Select timeframe" />
                </SelectTrigger>
                <SelectContent className="z-[90] rounded-xl border-border/60 bg-[#34135c] text-foreground">
                  {timeframes.map((timeframe) => (
                    <SelectItem key={timeframe} value={timeframe}>
                      {timeframe}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-muted-foreground"><FieldLabel label="Initial Capital" /></Label>
              <Input
                type="number"
                min={1}
                step={1000}
                value={initialCapital}
                onChange={(event) => setInitialCapital(event.target.value)}
                className="rounded-xl border-border/50 bg-card/20 text-foreground placeholder:text-muted-foreground"
                placeholder="100000"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label className="text-muted-foreground">Start Date</Label>
              <Input
                type="date"
                value={startDate}
                max={endDate || undefined}
                onChange={(event) => setStartDate(event.target.value)}
                className="rounded-xl border-border/50 bg-card/20 text-foreground"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-muted-foreground">End Date</Label>
              <Input
                type="date"
                value={endDate}
                min={startDate || undefined}
                max={toDateInput(new Date())}
                onChange={(event) => setEndDate(event.target.value)}
                className="rounded-xl border-border/50 bg-card/20 text-foreground"
              />
            </div>
          </div>

          <div className="rounded-xl border border-border/50 bg-card/20">
            <button
              type="button"
              onClick={() => setAdvancedFiltersOpen((prev) => !prev)}
              className="flex w-full items-center justify-between px-4 py-3 text-left"
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5 rounded-xl border border-primary/30 bg-primary/10 p-2 text-primary">
                  <SlidersHorizontal className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">Advanced Filters</p>
                  <p className="text-xs text-muted-foreground">
                    Optional filters to test strategy performance by weekday, session, or intraday time window.
                  </p>
                </div>
              </div>
              {advancedFiltersOpen ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
            </button>

            {advancedFiltersOpen && (
              <div className="space-y-4 border-t border-border/50 px-4 pb-4 pt-4">
                <div className="flex flex-col gap-3 rounded-xl border border-border/40 bg-card/20 p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-medium text-foreground">Enable Advanced Filters</p>
                    <p className="text-xs text-muted-foreground">Disabled by default. Existing backtests stay unchanged.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setAdvancedFiltersEnabled((prev) => !prev)}
                    className={`relative inline-flex h-7 w-14 items-center rounded-full border transition ${
                      advancedFiltersEnabled
                        ? "border-primary/60 bg-primary/80"
                        : "border-border/70 bg-card/30"
                    }`}
                    aria-pressed={advancedFiltersEnabled}
                  >
                    <span
                      className={`inline-block h-5 w-5 rounded-full bg-white shadow transition ${
                        advancedFiltersEnabled ? "translate-x-7" : "translate-x-1"
                      }`}
                    />
                  </button>
                </div>

                <div className={advancedFiltersEnabled ? "space-y-4" : "pointer-events-none space-y-4 opacity-55"}>
                  <div className="space-y-2">
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                      <div>
                        <Label className="text-muted-foreground">Trading Days</Label>
                        <p className="text-xs text-muted-foreground">Choose All Days or select specific weekdays.</p>
                      </div>
                      <Button
                        type="button"
                        variant={selectedDays.length === 0 ? "default" : "outline"}
                        size="sm"
                        onClick={() => setSelectedDays([])}
                        className="w-fit rounded-xl"
                      >
                        All Days
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {DAY_OPTIONS.map((day) => {
                        const selected = selectedDays.includes(day.value);
                        return (
                          <button
                            key={day.value}
                            type="button"
                            onClick={() => toggleTradingDay(day.value)}
                            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                              selected
                                ? "border-primary/60 bg-primary/20 text-primary-foreground shadow"
                                : "border-border/60 bg-card/20 text-muted-foreground hover:bg-card/40 hover:text-foreground"
                            }`}
                          >
                            {day.short}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label className="text-muted-foreground">Session</Label>
                      <Select value={selectedSession} onValueChange={(value) => setSelectedSession(value as SessionOption)}>
                        <SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground data-[placeholder]:text-muted-foreground">
                          <SelectValue placeholder="Select session" />
                        </SelectTrigger>
                        <SelectContent className="z-[90] rounded-xl border-border/60 bg-[#34135c] text-foreground">
                          {SESSION_OPTIONS.map((session) => (
                            <SelectItem key={session.value} value={session.value}>
                              {session.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground">
                        Session presets are mainly useful for Forex/Crypto. NSE instruments use exchange hours.
                      </p>
                    </div>

                    <div className="rounded-xl border border-border/50 bg-card/20 p-3">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Active Filter Summary</p>
                      <p className="mt-2 text-sm font-medium text-foreground">{activeFilterSummary}</p>
                    </div>
                  </div>

                  {selectedSession === "CUSTOM" && (
                    <div className="grid grid-cols-1 gap-4 rounded-xl border border-border/50 bg-card/20 p-4 md:grid-cols-3">
                      <div className="space-y-2">
                        <Label className="text-muted-foreground">Start Time</Label>
                        <Input
                          type="time"
                          value={customStartTime}
                          onChange={(event) => setCustomStartTime(event.target.value)}
                          className="rounded-xl border-border/50 bg-card/20 text-foreground"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-muted-foreground">End Time</Label>
                        <Input
                          type="time"
                          value={customEndTime}
                          onChange={(event) => setCustomEndTime(event.target.value)}
                          className="rounded-xl border-border/50 bg-card/20 text-foreground"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-muted-foreground">Timezone</Label>
                        <Input
                          value={advancedTimezone}
                          onChange={(event) => setAdvancedTimezone(event.target.value || DEFAULT_TIMEZONE)}
                          placeholder="Asia/Kolkata"
                          className="rounded-xl border-border/50 bg-card/20 text-foreground placeholder:text-muted-foreground"
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-border/50 bg-card/20">
            <button
              type="button"
              onClick={() => setAdvancedOpen((prev) => !prev)}
              className="flex w-full items-center justify-between px-4 py-3 text-left"
            >
              <div>
                <p className="text-sm font-medium text-foreground">Strategy Parameters</p>
                <p className="text-xs text-muted-foreground">
                  Dynamic fields detected from selected strategy configuration.
                </p>
              </div>
              {advancedOpen ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
            </button>

            {advancedOpen && (
              <div className="border-t border-border/50 px-4 pb-4 pt-3">
                {!parameterFields.length ? (
                  <p className="text-sm text-muted-foreground">No dynamic parameters available for this strategy.</p>
                ) : (
                  <>
                    <p className="mb-3 text-xs text-muted-foreground">
                      Preview-only view of strategy parameters. Execution uses the strategy stored on server.
                    </p>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                      {parameterFields.map((field) => (
                        <div key={field.key} className="space-y-1">
                          <Label className="text-xs text-muted-foreground">{field.label}</Label>
                          <Input
                            value={parameterValues[field.key] || ""}
                            onChange={(event) =>
                              setParameterValues((prev) => ({
                                ...prev,
                                [field.key]: event.target.value,
                              }))
                            }
                            className="h-9 rounded-xl border-border/50 bg-card/20 text-foreground"
                          />
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {validationErrors.length > 0 && (
            <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4" />
                <ul className="list-disc space-y-1 pl-4">
                  {validationErrors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardHeader>
          <CardTitle className="text-xl text-foreground">Validation & Preview</CardTitle>
          <CardDescription className="text-muted-foreground">
            Confirm DB coverage, candle scope and credit cost before execution.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Data Coverage</p>
              <p className="mt-2 text-lg font-semibold text-foreground">
                {availability ? (availability.available ? "Available" : "Missing") : "—"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Range: {availability?.min_timestamp ? new Date(availability.min_timestamp).toLocaleDateString() : "—"} →{" "}
                {availability?.max_timestamp ? new Date(availability.max_timestamp).toLocaleDateString() : "—"}
              </p>
            </div>

            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Candles After Filters</p>
              <p className="mt-2 text-lg font-semibold text-foreground">{candlesAfterFilters ? formatNumber(candlesAfterFilters, 0) : "—"}</p>
              <p className="mt-1 text-xs text-muted-foreground">Before filters: {candlesBeforeFilters ? formatNumber(candlesBeforeFilters, 0) : "—"}</p>
            </div>

            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Cost Feasibility</p>
              <p className="mt-2 text-lg font-semibold text-foreground">
                {costPreview ? (costPreview.can_run ? "Ready" : "Insufficient") : "—"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Cost {estimatedCost !== null ? formatNumber(estimatedCost, 0) : "—"} / Balance {formatNumber(totalAvailableCredits, 0)}
              </p>
            </div>
          </div>

          {costPreview && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Candles Before Filters</p>
                <p className="mt-2 text-lg font-semibold text-foreground">{formatNumber(candlesBeforeFilters, 0)}</p>
                <p className="mt-1 text-xs text-muted-foreground">Raw candles matched by instrument, timeframe, and date range.</p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Filter Reduction</p>
                <p className="mt-2 text-lg font-semibold text-foreground">{formatPercent(filterReductionPct)}</p>
                <p className="mt-1 text-xs text-muted-foreground">Removed {formatNumber(candlesRemovedByFilters, 0)} candles.</p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Active Filters</p>
                <p className="mt-2 text-sm font-semibold text-foreground">{previewFilterSummary}</p>
                <p className="mt-1 text-xs text-muted-foreground">Preview cost is based on filtered candles when enabled.</p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/20 p-4 md:col-span-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Credit Rule Used</p>
                <p className="mt-2 text-lg font-semibold text-foreground">{costPreview.pricing_rule || costPreview.breakdown?.rule_set_name || "Default Backtest Candle Rule"}</p>
                <p className="mt-1 text-xs text-muted-foreground">Estimated candles: {formatNumber(costPreview.estimated_candles ?? costPreview.breakdown?.candle_count ?? candlesAfterFilters, 0)} · Cost: {formatNumber(costPreview.credit_cost ?? costPreview.total_cost, 0)} credits · Balance: {formatNumber(costPreview.credit_balance ?? totalAvailableCredits, 0)} credits</p>
              </div>
            </div>
          )}

          {previewError && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              <div>{previewError}</div>
              {insufficientCreditsHint && (
                <div className="mt-2 text-xs text-rose-100/90">
                  Needed: {formatNumber(insufficientCreditsHint.needed || 0, 0)} credits · Included: {formatNumber(insufficientCreditsHint.includedBalance || 0, 0)} · Wallet: {formatNumber(insufficientCreditsHint.walletBalance || 0, 0)}
                </div>
              )}
            </div>
          )}

          {!!previewWarnings.length && (
            <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              <ul className="list-disc space-y-1 pl-4">
                {previewWarnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardContent className="flex flex-col gap-3 p-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">Execution Actions</p>
            <p className="text-xs text-muted-foreground">
              Preview validates candle availability, estimated cost, filters, and selected instrument before execution.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => void runPreview()}
              disabled={isPreviewing || isRunning}
              className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
            >
              {isPreviewing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Clock3 className="mr-2 h-4 w-4" />}
              Preview Data
            </Button>

            <Button
              type="button"
              onClick={() => void runBacktest()}
              disabled={!canRunBacktest}
              className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              {runButtonLabel}
            </Button>
          </div>
        </CardContent>
      </Card>

      {runError && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          <div className="whitespace-pre-line">{runError}</div>
          {insufficientCreditsHint && (
            <div className="mt-2 text-xs text-rose-100/90">
              Needed: {formatNumber(insufficientCreditsHint.needed || 0, 0)} credits · Included: {formatNumber(insufficientCreditsHint.includedBalance || 0, 0)} · Wallet: {formatNumber(insufficientCreditsHint.walletBalance || 0, 0)}
            </div>
          )}
          {insufficientCreditsHint && (
            <div className="mt-3 flex flex-wrap gap-2">
              <Button asChild variant="outline" size="sm" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">
                <Link href="/pricing">Upgrade Plan</Link>
              </Button>
              <Button asChild variant="outline" size="sm" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">
                <Link href="/credits">Top-up Credits</Link>
              </Button>
            </div>
          )}
        </div>
      )}

      {runResponse && (
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-xl text-foreground">Backtest Result</CardTitle>
                <CardDescription className="text-muted-foreground">
                  Execution output and quick analytics. Full details are available in history.
                </CardDescription>
              </div>
              <Badge className={resultStatusTone(runResponse.status)}>{(runResponse.status || "completed").toUpperCase()}</Badge>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">PnL</p>
                <p className={`mt-2 text-xl font-semibold ${netProfit >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                  {formatCurrency(netProfit, resultCurrencySymbol)}
                </p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Return %</p>
                <p className={`mt-2 text-xl font-semibold ${returnPct >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                  {formatPercent(returnPct)}
                </p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Win Rate</p>
                <p className="mt-2 text-xl font-semibold text-foreground">
                  {formatPercent(safeNumber(resultSummary?.win_rate, 0), safeNumber(resultSummary?.win_rate, 0) <= 1)}
                </p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Sharpe</p>
                <p className="mt-2 text-xl font-semibold text-foreground">{formatNumber(safeNumber(resultSummary?.sharpe_ratio, 0), 2)}</p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Drawdown</p>
                <p className="mt-2 text-xl font-semibold text-foreground">
                  {formatPercent(safeNumber(resultSummary?.max_drawdown, 0), safeNumber(resultSummary?.max_drawdown, 0) <= 1)}
                </p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Trades</p>
                <p className="mt-2 text-xl font-semibold text-foreground">{formatNumber(safeNumber(resultSummary?.total_trades, 0), 0)}</p>
              </div>
            </div>

            {equityChartRows.length > 1 && (
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">Equity Curve Preview</p>
                  <p className="text-xs text-muted-foreground">Latest {equityChartRows.length} points</p>
                </div>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={equityChartRows}>
                      <XAxis dataKey="label" hide />
                      <YAxis hide domain={["dataMin", "dataMax"]} />
                      <Tooltip
                        formatter={(value: number) => [formatCurrency(value, resultCurrencySymbol), "Equity"]}
                        labelFormatter={(label) => `Date: ${label}`}
                        contentStyle={{
                          borderRadius: 12,
                          borderColor: "rgba(148, 163, 184, 0.4)",
                          background: "rgba(15, 23, 42, 0.9)",
                        }}
                      />
                      <Line type="monotone" dataKey="equity" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {!!resultDetail?.trades?.length && (
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <p className="mb-3 text-sm font-medium text-foreground">Recent Trades</p>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[760px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-border/50 text-xs uppercase tracking-wide text-muted-foreground">
                        <th className="py-2 pr-3">Entry</th>
                        <th className="py-2 pr-3">Exit</th>
                        <th className="py-2 pr-3">Side</th>
                        <th className="py-2 pr-3">{resultQuantityMode === "LOTS" ? "Lot" : resultQuantityMode === "UNITS" ? "Units" : "Qty"}</th>
                        <th className="py-2 pr-3">Entry Px</th>
                        <th className="py-2 pr-3">Exit Px</th>
                        <th className="py-2 pr-0 text-right">PnL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {resultDetail.trades.slice(0, 8).map((trade, index) => {
                        const pnl = safeNumber(trade.pnl, 0);
                        return (
                          <tr key={`${trade.id || "trade"}-${index}`} className="border-b border-border/30 text-foreground last:border-none">
                            <td className="py-2 pr-3">{trade.entry_time ? new Date(trade.entry_time).toLocaleString() : "—"}</td>
                            <td className="py-2 pr-3">{trade.exit_time ? new Date(trade.exit_time).toLocaleString() : "—"}</td>
                            <td className="py-2 pr-3">{trade.side || "—"}</td>
                            <td className="py-2 pr-3">{formatTradeSize(trade, resultQuantityMode).value}</td>
                            <td className="py-2 pr-3">{formatNumber(safeNumber(trade.entry_price, 0), 2)}</td>
                            <td className="py-2 pr-3">{formatNumber(safeNumber(trade.exit_price, 0), 2)}</td>
                            <td className={`py-2 pr-0 text-right font-medium ${pnl >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                              {formatCurrency(pnl, trade.currency_symbol || resultCurrencySymbol)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                onClick={() => router.push("/backtest-history")}
                className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <BarChart3 className="mr-2 h-4 w-4" />
                Open Backtest History
              </Button>

              {(runResponse.backtest_id || runResponse.result?.backtest_id) && (
                <Button
                  asChild
                  variant="outline"
                  className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                >
                  <Link href={`/backtest-report/${runResponse.backtest_id || runResponse.result?.backtest_id}`}>View Full Detailed Report</Link>
                </Button>
              )}

              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setRunResponse(null);
                  setResultDetail(null);
                }}
                className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
              >
                Run Another Configuration
              </Button>
            </div>

            {runResponse.backtest_id && (
              <div className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-100">
                <CheckCircle2 className="h-4 w-4" />
                Result stored successfully with ID: {runResponse.backtest_id}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
