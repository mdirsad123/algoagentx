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
  Wallet,
} from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

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
import {
  backtestsApi,
  type BacktestDetailResponse,
  type BacktestRunResponse,
  type CostPreviewResponse,
  type DataAvailabilityResponse,
  type InstrumentOption,
  type StrategyOption,
} from "@/lib/api/backtests";

type ParameterField = {
  key: string;
  label: string;
  valueType: "string" | "number" | "boolean";
  value: string;
};

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

const formatNumber = (value: number | null | undefined, fractionDigits = 2): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  }).format(value);
};

const formatCurrency = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value);
};

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

  const parameterFields = useMemo(() => extractStrategyParameterFields(selectedStrategy), [selectedStrategy]);

  useEffect(() => {
    const nextValues: Record<string, string> = {};
    parameterFields.forEach((field) => {
      nextValues[field.key] = field.value;
    });
    setParameterValues(nextValues);
  }, [parameterFields]);

  const requestSignature = useMemo(
    () =>
      [selectedStrategyId, selectedInstrumentId, selectedTimeframe, startDate, endDate, initialCapital]
        .map((item) => (item ?? "").toString().trim())
        .join("|"),
    [selectedStrategyId, selectedInstrumentId, selectedTimeframe, startDate, endDate, initialCapital],
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

    return messages;
  }, [selectedStrategyId, selectedInstrumentId, selectedTimeframe, startDate, endDate, initialCapital, limits]);

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

      if (!nextInstruments.length) {
        try {
          nextInstruments = await backtestsApi.getInstruments();
        } catch {
          nextInstruments = [];
        }
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
      if (availabilityData.requested_candle_count > 100000) {
        warnings.push("Large candle scope detected. Execution may be slower and cost more credits.");
      }
      if (!costData.can_run) {
        warnings.push("Insufficient credits for this run. Reduce scope or add credits.");
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

    let previewData = { availability, cost: costPreview } as {
      availability: DataAvailabilityResponse | null;
      cost: CostPreviewResponse | null;
    };

    if (lastPreviewSignature !== requestSignature || !previewData.availability || !previewData.cost) {
      const freshPreview = await runPreview();
      if (!freshPreview) return;
      previewData = freshPreview;
    }

    if (!previewData.availability?.available || (previewData.availability.requested_candle_count || 0) <= 0) {
      setRunError(previewData.availability?.message || "Market data is missing for this instrument/timeframe/date range. Ask admin to import missing candles.");
      return;
    }

    if (!previewData.cost?.can_run) {
      setRunError("Insufficient credit balance for this run. Adjust scope or add credits.");
      setInsufficientCreditsHint({
        needed: safeNumber(previewData.cost?.total_cost, 0),
        walletBalance: safeNumber(previewData.cost?.balances?.wallet_balance, 0),
        includedBalance: safeNumber(previewData.cost?.balances?.included_balance, 0),
      });
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
  ]);

  const resultSummary = useMemo(() => {
    if (resultDetail?.summary) return resultDetail.summary;
    return runResponse?.result || null;
  }, [resultDetail, runResponse]);

  const requestedCandleCount = availability?.requested_candle_count || 0;
  const estimatedCost = costPreview?.total_cost ?? null;
  const totalAvailableCredits = creditSnapshot?.totalAvailable ?? null;
  const subscriptionCredits = creditSnapshot?.includedBalance ?? 0;
  const walletCredits = creditSnapshot?.walletBalance ?? 0;
  const deductionOrderLabel = (creditSnapshot?.deductionOrder || ["subscription", "wallet"])
    .map((item) => item.charAt(0).toUpperCase() + item.slice(1))
    .join(" → ");
  const postRunBalance =
    totalAvailableCredits !== null && estimatedCost !== null ? Math.max(totalAvailableCredits - estimatedCost, 0) : null;
  const isCreditInsufficient = Boolean(costPreview && !costPreview.can_run);

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

  return (
    <div className="space-y-6">
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
          <CardTitle className="text-xl text-foreground">Backtest Configuration</CardTitle>
          <CardDescription className="text-muted-foreground">
            Select strategy, market scope, and execution settings before preview.
          </CardDescription>
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
              <Label className="text-muted-foreground">Initial Capital</Label>
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
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Requested Candles</p>
              <p className="mt-2 text-lg font-semibold text-foreground">{requestedCandleCount ? formatNumber(requestedCandleCount, 0) : "—"}</p>
              <p className="mt-1 text-xs text-muted-foreground">Larger scopes increase runtime and credit usage.</p>
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
              Preview validates data/cost. Run executes and stores the result in history.
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
              disabled={isRunning || isPreviewing || !isReadyForRun || isCreditInsufficient}
              className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              {isRunning ? "Running Backtest..." : isCreditInsufficient ? "Insufficient Credits" : "Run Backtest"}
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
                  {formatCurrency(netProfit)}
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
                        formatter={(value: number) => [formatCurrency(value), "Equity"]}
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
                        <th className="py-2 pr-3">Qty</th>
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
                            <td className="py-2 pr-3">{formatNumber(safeNumber(trade.quantity, 0), 0)}</td>
                            <td className="py-2 pr-3">{formatNumber(safeNumber(trade.entry_price, 0), 2)}</td>
                            <td className="py-2 pr-3">{formatNumber(safeNumber(trade.exit_price, 0), 2)}</td>
                            <td className={`py-2 pr-0 text-right font-medium ${pnl >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                              {formatCurrency(pnl)}
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
