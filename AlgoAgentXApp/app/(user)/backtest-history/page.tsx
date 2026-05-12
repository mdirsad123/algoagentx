"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Calendar,
  Clock3,
  Download,
  Eye,
  Filter,
  Play,
  RefreshCcw,
  RotateCcw,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";

import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { parseApiError, formatErrorMessage } from "@/lib/api/error";
import { formatCurrency as formatMoney, formatNumber as formatDisplayNumber, currencySymbolForCode } from "@/lib/formatters";
import {
  backtestsApi,
  type BacktestDetailResponse,
  type BacktestHistoryItem,
  type BacktestHistoryPagination,
  type InstrumentOption,
  type StrategyOption,
} from "@/lib/api/backtests";

type FilterState = {
  strategy_id: string;
  instrument_id: string;
  timeframe: string;
  status: string;
  start_date_from: string;
  start_date_to: string;
  min_profit: string;
  max_drawdown: string;
};

type QuickRange = "today" | "last7" | "last30" | null;

const PAGE_SIZE = 20;
const DEFAULT_STATUSES = ["completed", "running", "pending", "failed"];

const EMPTY_FILTERS: FilterState = {
  strategy_id: "",
  instrument_id: "",
  timeframe: "",
  status: "",
  start_date_from: "",
  start_date_to: "",
  min_profit: "",
  max_drawdown: "",
};

const toDateInput = (date: Date) => date.toISOString().slice(0, 10);

const safeNumber = (value: unknown, fallback = 0): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const formatNumber = (value: number | null | undefined, digits = 2): string => formatDisplayNumber(value, digits);

const rowCurrencySymbol = (item: BacktestHistoryItem): string => item.currency_symbol || currencySymbolForCode(item.account_currency) || "₹";
const formatCurrency = (value: number | null | undefined, symbol = "₹"): string => formatMoney(value, symbol);

const toDisplayPercent = (value: number): number => (Math.abs(value) <= 1 ? value * 100 : value);

const formatPercentAuto = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${formatNumber(toDisplayPercent(value), 2)}%`;
};

const formatDateTime = (value?: string | null): string => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const statusTone = (status?: string | null): string => {
  const normalized = (status || "").toLowerCase();
  if (normalized === "completed") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
  if (normalized === "running") return "border-sky-500/40 bg-sky-500/10 text-sky-200";
  if (normalized === "pending") return "border-amber-500/40 bg-amber-500/10 text-amber-200";
  if (normalized === "failed") return "border-rose-500/40 bg-rose-500/10 text-rose-200";
  return "border-border/50 bg-card/40 text-muted-foreground";
};

const humanize = (value: string) =>
  value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase())
    .trim();



const asRecord = (value: unknown): Record<string, unknown> | null => {
  if (!value) return null;
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : null;
    } catch {
      return null;
    }
  }
  return typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
};

const getRuntimeSection = (runtime: Record<string, unknown> | null, key: string): Record<string, unknown> => {
  const section = runtime?.[key];
  return section && typeof section === "object" && !Array.isArray(section) ? (section as Record<string, unknown>) : {};
};

const formatRuntimePercent = (value: unknown): string | null => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  const pct = Math.abs(parsed) <= 1 ? parsed * 100 : parsed;
  return `${formatNumber(pct, 2)}%`;
};

const formatRuntimeSummary = (item: BacktestHistoryItem): string => {
  if (item.runtime_summary && item.runtime_summary.trim()) return item.runtime_summary;
  const runtime = asRecord(item.runtime_config_snapshot);
  if (!runtime) return "Runtime snapshot unavailable";
  const risk = getRuntimeSection(runtime, "risk");
  const slTp = getRuntimeSection(runtime, "sl_tp");
  const tm = getRuntimeSection(runtime, "trade_management");
  const parts: string[] = [];
  const riskPct = formatRuntimePercent(risk.risk_percent);
  if (riskPct) parts.push(`Risk ${riskPct}`);
  if (slTp.rr_ratio !== undefined && slTp.rr_ratio !== null) parts.push(`RR 1:${slTp.rr_ratio}`);
  if (slTp.sl_mode) parts.push(`${humanize(String(slTp.sl_mode))} SL`);
  if (risk.position_size_mode) {
    const mode = String(risk.position_size_mode).toUpperCase();
    if (mode === "FIXED_LOT" && risk.fixed_lot_size !== undefined) parts.push(`Fixed Lot ${risk.fixed_lot_size}`);
    else parts.push(humanize(String(risk.position_size_mode)));
  }
  if (tm.break_even_enabled) parts.push("Breakeven ON");
  if (tm.trailing_enabled) parts.push("Trail ON");
  if (tm.partial_exit_enabled) parts.push("Partial Exit ON");
  return parts.length ? parts.join(" · ") : "Runtime snapshot captured";
};

const formatFilterSummary = (item: Pick<BacktestHistoryItem, "filter_summary" | "advanced_filters">): string => {
  if (item.filter_summary && item.filter_summary.trim()) return item.filter_summary;
  const filters = asRecord(item.advanced_filters) || (item.advanced_filters && typeof item.advanced_filters === "object" ? item.advanced_filters : null);
  if (!filters || !filters.enabled) return "Advanced filters not used";
  const daysRaw = Array.isArray(filters.days_of_week) ? filters.days_of_week : [];
  const days = daysRaw.length ? daysRaw.map((day) => humanize(String(day))).join(", ") : "All days";
  const sessionValue = String(filters.session || "ALL");
  const session = sessionValue === "CUSTOM"
    ? `${filters.custom_start_time || "—"}-${filters.custom_end_time || "—"} ${filters.timezone || "Asia/Kolkata"}`
    : `${humanize(sessionValue)} Session`;
  return `${days} · ${session.replace("All Session", "All sessions")}`;
};

const computeReturnPercent = (item: BacktestHistoryItem): number | null => {
  const initial = safeNumber(item.initial_capital, NaN);
  const final = safeNumber(item.final_capital, NaN);
  const pnl = safeNumber(item.net_profit, NaN);

  if (Number.isFinite(initial) && initial > 0 && Number.isFinite(final)) {
    return ((final - initial) / initial) * 100;
  }

  if (Number.isFinite(initial) && initial > 0 && Number.isFinite(pnl)) {
    return (pnl / initial) * 100;
  }

  return null;
};

const normalizeDrawdownForApi = (value: string): number | undefined => {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return undefined;
  const absolute = Math.abs(parsed);
  return absolute > 1 ? absolute / 100 : absolute;
};

const toCsvSafe = (value: unknown): string => {
  if (value === null || value === undefined) return "";
  const text = String(value);
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
};

const downloadCsv = (filename: string, headers: string[], rows: Array<Array<unknown>>) => {
  if (typeof window === "undefined") return;
  const csv = [headers.map(toCsvSafe).join(","), ...rows.map((row) => row.map(toCsvSafe).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
};

const downloadBlob = (filename: string, blob: Blob) => {
  if (typeof window === "undefined") return;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export default function BacktestHistoryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [strategies, setStrategies] = useState<StrategyOption[]>([]);
  const [instruments, setInstruments] = useState<InstrumentOption[]>([]);
  const [timeframes, setTimeframes] = useState<string[]>([]);

  const [draftFilters, setDraftFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [quickRange, setQuickRange] = useState<QuickRange>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const [rows, setRows] = useState<BacktestHistoryItem[]>([]);
  const [pagination, setPagination] = useState<BacktestHistoryPagination | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const [initialLoading, setInitialLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedRun, setSelectedRun] = useState<BacktestHistoryItem | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detail, setDetail] = useState<BacktestDetailResponse | null>(null);

  const activeFilterCount = useMemo(
    () =>
      Object.values(appliedFilters).filter((item) => typeof item === "string" && item.trim().length > 0)
        .length,
    [appliedFilters],
  );

  const statusOptions = useMemo(() => {
    const discovered = rows
      .map((item) => (item.status || "").trim().toLowerCase())
      .filter(Boolean);
    return Array.from(new Set([...DEFAULT_STATUSES, ...discovered]));
  }, [rows]);

  const loadReferenceData = useCallback(async () => {
    try {
      const [configResult, catalogResult, instrumentsResult, timeframesResult] = await Promise.allSettled([
        backtestsApi.getConfig(),
        backtestsApi.getStrategiesCatalog(),
        backtestsApi.getInstruments(),
        backtestsApi.getTimeframes(),
      ]);

      const strategyMap = new Map<string, StrategyOption>();
      const instrumentMap = new Map<number, InstrumentOption>();
      const timeframeSet = new Set<string>();

      if (configResult.status === "fulfilled") {
        const config = configResult.value;
        (config.strategies || []).forEach((item) => {
          strategyMap.set(item.id, {
            id: item.id,
            name: item.name,
          });
        });

        (config.instruments || []).forEach((item) => instrumentMap.set(item.id, item));
        (config.timeframes || []).forEach((item) => item && timeframeSet.add(item));
      }

      if (catalogResult.status === "fulfilled") {
        catalogResult.value.forEach((item) => {
          strategyMap.set(item.id, {
            ...strategyMap.get(item.id),
            ...item,
          });
        });
      }

      if (instrumentsResult.status === "fulfilled") {
        instrumentsResult.value.forEach((item) => instrumentMap.set(item.id, item));
      }

      if (timeframesResult.status === "fulfilled") {
        timeframesResult.value.forEach((item) => item && timeframeSet.add(item));
      }

      setStrategies(Array.from(strategyMap.values()));
      setInstruments(Array.from(instrumentMap.values()));
      setTimeframes(Array.from(timeframeSet.values()));
    } catch {
      // Soft-fail: history list still loads independently.
    }
  }, []);

  const loadHistory = useCallback(async (page: number, filters: FilterState) => {
    setLoading(true);
    setError(null);

    try {
      const minProfit = filters.min_profit.trim().length ? Number(filters.min_profit) : NaN;
      const query = {
        page,
        page_size: PAGE_SIZE,
        strategy_id: filters.strategy_id || undefined,
        instrument_id: filters.instrument_id ? Number(filters.instrument_id) : undefined,
        timeframe: filters.timeframe || undefined,
        status: filters.status || undefined,
        start_date_from: filters.start_date_from || undefined,
        start_date_to: filters.start_date_to || undefined,
        min_profit: Number.isFinite(minProfit) ? minProfit : undefined,
        max_drawdown: normalizeDrawdownForApi(filters.max_drawdown),
      };

      const response = await backtestsApi.getHistory(query);
      setRows(Array.isArray(response.backtests) ? response.backtests : []);
      setPagination(
        response.pagination || {
          page,
          page_size: PAGE_SIZE,
          total_count: 0,
          total_pages: 1,
        },
      );
    } catch (err) {
      const parsed = parseApiError(err);
      setRows([]);
      setPagination(null);
      setError(formatErrorMessage(parsed));
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadReferenceData();
  }, [loadReferenceData]);

  useEffect(() => {
    void loadHistory(currentPage, appliedFilters);
  }, [appliedFilters, currentPage, loadHistory]);

  const applyFilters = () => {
    setAppliedFilters({ ...draftFilters });
    setQuickRange(null);
    setCurrentPage(1);
  };

  const clearAllFilters = () => {
    setDraftFilters({ ...EMPTY_FILTERS });
    setAppliedFilters({ ...EMPTY_FILTERS });
    setQuickRange(null);
    setCurrentPage(1);
  };

  const applyQuickRange = (range: Exclude<QuickRange, null>) => {
    const today = new Date();
    const start = new Date(today);

    if (range === "last7") {
      start.setDate(today.getDate() - 6);
    } else if (range === "last30") {
      start.setDate(today.getDate() - 29);
    }

    const next = {
      ...draftFilters,
      start_date_from: toDateInput(start),
      start_date_to: toDateInput(today),
    };

    setQuickRange(range);
    setDraftFilters(next);
    setAppliedFilters(next);
    setCurrentPage(1);
  };

  const rerunBacktest = (item: BacktestHistoryItem) => {
    const params = new URLSearchParams();
    if (item.strategy_id) params.set("strategyId", item.strategy_id);
    if (item.instrument_id !== null && item.instrument_id !== undefined) {
      params.set("instrumentId", String(item.instrument_id));
    }
    router.push(`/backtest?${params.toString()}`);
  };

  const exportRunSummary = (item: BacktestHistoryItem) => {
    const returns = computeReturnPercent(item);
    downloadCsv(
      `backtest-summary-${item.id}.csv`,
      [
        "Backtest ID",
        "Strategy",
        "Instrument",
        "Timeframe",
        "Initial Capital",
        "Net PnL",
        "Return %",
        "Win Rate",
        "Sharpe",
        "Drawdown",
        "Total Trades",
        "Status",
        "Created At",
      ],
      [
        [
          item.id,
          item.strategy_name || "",
          item.instrument_symbol || "",
          item.timeframe || "",
          item.initial_capital ?? "",
          item.net_profit ?? "",
          returns ?? "",
          item.win_rate ?? "",
          item.sharpe_ratio ?? "",
          item.max_drawdown ?? "",
          item.total_trades ?? "",
          item.status || "",
          item.created_at || "",
        ],
      ],
    );
  };

  const openDetail = async (item: BacktestHistoryItem) => {
    router.push(`/backtest-report/${item.id}`);
  };

  const exportDetailTrades = () => {
    if (!selectedRun || !detail?.trades?.length) return;

    downloadCsv(
      `backtest-trades-${selectedRun.id}.csv`,
      ["Entry Time", "Exit Time", "Side", "Quantity", "Entry Price", "Exit Price", "Stop Loss", "Target / TP", "Risk Points", "Reward Points", "RR Ratio", "Risk Amount", "Reward Amount", "R Multiple", "PnL", "Exit Type", "Signal Reason"],
      detail.trades.map((trade) => [
        trade.entry_time || "",
        trade.exit_time || "",
        trade.side || "",
        trade.quantity ?? "",
        trade.entry_price ?? "",
        trade.exit_price ?? "",
        trade.stop_loss ?? "",
        trade.target ?? "",
        trade.risk_points ?? "",
        trade.reward_points ?? "",
        trade.rr_ratio ?? "",
        trade.risk_amount ?? "",
        trade.reward_amount ?? "",
        trade.r_multiple ?? "",
        trade.pnl ?? "",
        trade.exit_type || "",
        trade.signal_reason || "",
      ]),
    );
  };


  const exportDetailFile = async (format: "excel" | "pdf") => {
    if (!selectedRun) return;
    const blob = await backtestsApi.downloadExport(selectedRun.id, format);
    downloadBlob(`backtest-${selectedRun.id}.${format === "excel" ? "xlsx" : "pdf"}`, blob);
  };

  useEffect(() => {
    const requestedId = searchParams.get("backtestId");
    if (!requestedId || detailOpen) return;
    const existing = rows.find((item) => item.id === requestedId);
    if (existing) {
      router.replace(`/backtest-report/${requestedId}`);
      return;
    }
    router.replace(`/backtest-report/${requestedId}`);
  }, [searchParams, rows, detailOpen]);

  const summaryStats = useMemo(() => {
    const profitableRuns = rows.filter((item) => safeNumber(item.net_profit, 0) > 0).length;
    const returnSeries = rows
      .map((item) => computeReturnPercent(item))
      .filter((value): value is number => value !== null && Number.isFinite(value));
    const drawdownSeries = rows
      .map((item) => item.max_drawdown)
      .filter((value): value is number => value !== null && value !== undefined && Number.isFinite(Number(value)));

    const avgReturn =
      returnSeries.length > 0
        ? returnSeries.reduce((sum, value) => sum + value, 0) / returnSeries.length
        : null;

    const avgDrawdown =
      drawdownSeries.length > 0
        ? drawdownSeries.reduce((sum, value) => sum + value, 0) / drawdownSeries.length
        : null;

    const profitByCurrency = rows.reduce<Record<string, { symbol: string; total: number }>>((acc, item) => {
      const code = item.account_currency || "INR";
      const symbol = item.currency_symbol || currencySymbolForCode(code);
      acc[code] = acc[code] || { symbol, total: 0 };
      acc[code].total += safeNumber(item.net_profit, 0);
      return acc;
    }, {});
    const currencyGroups = Object.values(profitByCurrency);
    const totalProfit = currencyGroups.length === 1 ? currencyGroups[0].total : 0;

    return {
      totalRuns: pagination?.total_count ?? rows.length,
      profitableRuns,
      avgReturn,
      avgDrawdown,
      totalProfit,
      currencyGroups,
    };
  }, [pagination?.total_count, rows]);

  const detailSummary = detail?.summary;
  const detailReturn = detailSummary
    ? computeReturnPercent({
        id: detailSummary.id,
        initial_capital: detailSummary.initial_capital,
        final_capital: detailSummary.final_capital,
        net_profit: detailSummary.net_profit,
      })
    : null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backtest History"
        subtitle="Premium analytics archive for every run with fast filtering, deep metrics, and export-ready results."
        actions={
          <Button
            onClick={() => router.push("/backtest")}
            className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Play className="mr-2 h-4 w-4" />
            New Backtest
          </Button>
        }
      />

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Card className="h-full min-h-[116px] rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Total Runs</CardDescription>
            <CardTitle className="text-2xl text-foreground">{formatNumber(summaryStats.totalRuns, 0)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">Across current filter scope</CardContent>
        </Card>

        <Card className="h-full min-h-[116px] rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Profitable Runs</CardDescription>
            <CardTitle className="text-2xl text-emerald-300">{formatNumber(summaryStats.profitableRuns, 0)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">Calculated on visible results</CardContent>
        </Card>

        <Card className="h-full min-h-[116px] rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Avg Return</CardDescription>
            <CardTitle className="text-2xl text-foreground">{formatPercentAuto(summaryStats.avgReturn)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">Visible result set average</CardContent>
        </Card>

        <Card className="h-full min-h-[116px] rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Avg Drawdown</CardDescription>
            <CardTitle className="text-2xl text-foreground">{formatPercentAuto(summaryStats.avgDrawdown)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">Lower is better</CardContent>
        </Card>

        <Card className="h-full min-h-[116px] rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Total PnL</CardDescription>
            <CardTitle className={`text-2xl ${summaryStats.totalProfit >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
              {summaryStats.currencyGroups.length === 1 ? formatCurrency(summaryStats.totalProfit, summaryStats.currencyGroups[0].symbol) : "Mixed"}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">{summaryStats.currencyGroups.length > 1 ? summaryStats.currencyGroups.map((g) => `${g.symbol}${formatNumber(Math.abs(g.total), 2)}`).join(" · ") : "Sum of visible runs"}</CardContent>
        </Card>
      </section>

      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardHeader className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-foreground">
                <Filter className="h-5 w-5 text-primary" />
                Quick Filters
              </CardTitle>
              <CardDescription>Instant date presets for faster analysis.</CardDescription>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={() => applyQuickRange("today")}
                className={`rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40 ${
                  quickRange === "today" ? "border-primary/50 bg-primary/15 text-primary" : ""
                }`}
              >
                Today
              </Button>
              <Button
                variant="outline"
                onClick={() => applyQuickRange("last7")}
                className={`rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40 ${
                  quickRange === "last7" ? "border-primary/50 bg-primary/15 text-primary" : ""
                }`}
              >
                Last 7 Days
              </Button>
              <Button
                variant="outline"
                onClick={() => applyQuickRange("last30")}
                className={`rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40 ${
                  quickRange === "last30" ? "border-primary/50 bg-primary/15 text-primary" : ""
                }`}
              >
                Last 30 Days
              </Button>
              <Button
                variant="outline"
                onClick={() => setAdvancedOpen((prev) => !prev)}
                className={`rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40 ${
                  advancedOpen ? "border-primary/50 bg-primary/15 text-primary" : ""
                }`}
              >
                <SlidersHorizontal className="mr-2 h-4 w-4" />
                {advancedOpen ? "Hide Advanced" : "Advanced Filters"}
                {activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}
              </Button>
              <Button
                variant="outline"
                onClick={clearAllFilters}
                className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                Clear Filters
              </Button>
            </div>
          </div>

          <div className="rounded-xl border border-border/50 bg-card/20">
            {advancedOpen ? (
              <div className="space-y-4 p-4">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="space-y-2">
                    <Label className="text-muted-foreground">Strategy</Label>
                    <Select
                      value={draftFilters.strategy_id || "all"}
                      onValueChange={(value) =>
                        setDraftFilters((prev) => ({
                          ...prev,
                          strategy_id: value === "all" ? "" : value,
                        }))
                      }
                    >
                      <SelectTrigger className="rounded-xl border-border/50 bg-card/20 text-foreground">
                        <SelectValue placeholder="All strategies" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All strategies</SelectItem>
                        {strategies.map((item) => (
                          <SelectItem key={item.id} value={item.id}>
                            {item.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground">Instrument</Label>
                    <Select
                      value={draftFilters.instrument_id || "all"}
                      onValueChange={(value) =>
                        setDraftFilters((prev) => ({
                          ...prev,
                          instrument_id: value === "all" ? "" : value,
                        }))
                      }
                    >
                      <SelectTrigger className="rounded-xl border-border/50 bg-card/20 text-foreground">
                        <SelectValue placeholder="All instruments" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All instruments</SelectItem>
                        {instruments.map((item) => (
                          <SelectItem key={item.id} value={String(item.id)}>
                            {item.symbol}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground">Timeframe</Label>
                    <Select
                      value={draftFilters.timeframe || "all"}
                      onValueChange={(value) =>
                        setDraftFilters((prev) => ({
                          ...prev,
                          timeframe: value === "all" ? "" : value,
                        }))
                      }
                    >
                      <SelectTrigger className="rounded-xl border-border/50 bg-card/20 text-foreground">
                        <SelectValue placeholder="All timeframes" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All timeframes</SelectItem>
                        {timeframes.map((item) => (
                          <SelectItem key={item} value={item}>
                            {item}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground">Status</Label>
                    <Select
                      value={draftFilters.status || "all"}
                      onValueChange={(value) =>
                        setDraftFilters((prev) => ({
                          ...prev,
                          status: value === "all" ? "" : value,
                        }))
                      }
                    >
                      <SelectTrigger className="rounded-xl border-border/50 bg-card/20 text-foreground">
                        <SelectValue placeholder="All statuses" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All statuses</SelectItem>
                        {statusOptions.map((item) => (
                          <SelectItem key={item} value={item}>
                            {humanize(item)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="space-y-2">
                    <Label className="text-muted-foreground">Date From</Label>
                    <Input
                      type="date"
                      value={draftFilters.start_date_from}
                      onChange={(event) =>
                        setDraftFilters((prev) => ({
                          ...prev,
                          start_date_from: event.target.value,
                        }))
                      }
                      className="rounded-xl border-border/50 bg-card/20 text-foreground"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground">Date To</Label>
                    <Input
                      type="date"
                      value={draftFilters.start_date_to}
                      onChange={(event) =>
                        setDraftFilters((prev) => ({
                          ...prev,
                          start_date_to: event.target.value,
                        }))
                      }
                      className="rounded-xl border-border/50 bg-card/20 text-foreground"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground">Min Profit</Label>
                    <Input
                      type="number"
                      value={draftFilters.min_profit}
                      onChange={(event) =>
                        setDraftFilters((prev) => ({
                          ...prev,
                          min_profit: event.target.value,
                        }))
                      }
                      placeholder="e.g. 5000"
                      className="rounded-xl border-border/50 bg-card/20 text-foreground placeholder:text-muted-foreground"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground">Max Drawdown (%)</Label>
                    <Input
                      type="number"
                      value={draftFilters.max_drawdown}
                      onChange={(event) =>
                        setDraftFilters((prev) => ({
                          ...prev,
                          max_drawdown: event.target.value,
                        }))
                      }
                      placeholder="e.g. 20"
                      className="rounded-xl border-border/50 bg-card/20 text-foreground placeholder:text-muted-foreground"
                    />
                  </div>
                </div>

                <div className="flex flex-wrap justify-end gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setDraftFilters(appliedFilters)}
                    className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                  >
                    <X className="mr-2 h-4 w-4" />
                    Revert Changes
                  </Button>
                  <Button
                    variant="outline"
                    onClick={clearAllFilters}
                    className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                  >
                    Clear All
                  </Button>
                  <Button
                    onClick={applyFilters}
                    className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    <Search className="mr-2 h-4 w-4" />
                    Apply Filters
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-2 px-4 py-3 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
                <span>Advanced filters are hidden to keep this page compact.</span>
                <span>{activeFilterCount > 0 ? `${activeFilterCount} active filters applied` : "No active filters"}</span>
              </div>
            )}
          </div>
        </CardHeader>
      </Card>

      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardHeader>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle className="text-foreground">Backtest Archive</CardTitle>
              <CardDescription>Performance archive with filter-aware listing and actionable controls.</CardDescription>
            </div>

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Calendar className="h-4 w-4" />
              {pagination
                ? `Showing ${rows.length} of ${formatNumber(pagination.total_count, 0)} runs`
                : `${rows.length} runs`}
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {error && !loading && (
            <div className="mb-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              <div className="flex items-start justify-between gap-3">
                <p>{error}</p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void loadHistory(currentPage, appliedFilters)}
                  className="rounded-lg border-rose-400/50 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20"
                >
                  <RefreshCcw className="mr-1 h-3.5 w-3.5" />
                  Retry
                </Button>
              </div>
            </div>
          )}

          {loading && initialLoading ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                {Array.from({ length: 4 }).map((_, idx) => (
                  <div key={idx} className="h-20 animate-pulse rounded-xl border border-border/50 bg-card/30" />
                ))}
              </div>
              <div className="h-[320px] animate-pulse rounded-xl border border-border/50 bg-card/30" />
            </div>
          ) : !loading && !rows.length ? (
            <EmptyState
              title="No backtest runs found"
              description="Try widening filters or run a new backtest to build your analytics archive."
              action={
                <Button
                  onClick={() => router.push("/backtest")}
                  className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <Play className="mr-2 h-4 w-4" />
                  Run Backtest
                </Button>
              }
            />
          ) : (
            <>
              <div className="responsive-table-wrapper hidden overflow-x-auto md:block">
                <Table className="min-w-[1040px]">
                  <TableHeader>
                    <TableRow className="border-border/50 hover:bg-transparent">
                      <TableHead className="w-[220px]">Strategy</TableHead>
                      <TableHead>Instrument</TableHead>
                      <TableHead>Timeframe</TableHead>
                      <TableHead className="text-right">PnL</TableHead>
                      <TableHead className="text-right">Return %</TableHead>
                      <TableHead className="text-right">Win Rate</TableHead>
                      <TableHead className="text-right">Drawdown</TableHead>
                      <TableHead className="text-right">Trades</TableHead>
                      <TableHead className="w-[145px]">Created</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-[260px] text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>

                  <TableBody>
                    {loading
                      ? Array.from({ length: 6 }).map((_, idx) => (
                          <TableRow key={`skeleton-${idx}`} className="border-border/30 hover:bg-transparent">
                            <TableCell colSpan={11} className="py-4">
                              <div className="h-6 animate-pulse rounded-lg bg-card/40" />
                            </TableCell>
                          </TableRow>
                        ))
                      : rows.map((item) => {
                          const pnl = safeNumber(item.net_profit, 0);
                          const returnPct = computeReturnPercent(item);

                          return (
                            <TableRow
                              key={item.id}
                              className="border-border/30 text-foreground transition-colors hover:bg-card/30"
                            >
                              <TableCell className="max-w-[220px]">
                                <div className="truncate font-medium" title={item.strategy_name || ""}>{item.strategy_name || "—"}</div>
                                <div className="mt-1 flex flex-wrap gap-1.5 text-[11px] text-muted-foreground">
                                  <span title="Initial capital" className="rounded-full border border-border/40 bg-card/20 px-2 py-0.5">
                                    Cap {formatCurrency(item.initial_capital, rowCurrencySymbol(item))}
                                  </span>
                                  <span title="Sharpe ratio" className="rounded-full border border-border/40 bg-card/20 px-2 py-0.5">
                                    Sharpe {formatNumber(item.sharpe_ratio, 2)}
                                  </span>
                                </div>
                                <div className="mt-1 flex flex-wrap gap-1.5">
                                  <span title={formatRuntimeSummary(item)} className="rounded-full border border-violet-400/40 bg-violet-500/10 px-2 py-0.5 text-[11px] font-medium text-violet-100">
                                    Runtime
                                  </span>
                                  <span title={formatFilterSummary(item)} className="rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                                    Filters
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell className="whitespace-nowrap">{item.instrument_symbol || "—"}</TableCell>
                              <TableCell>{item.timeframe || "—"}</TableCell>
                              <TableCell className={`text-right font-medium ${pnl >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                                {formatCurrency(item.net_profit, rowCurrencySymbol(item))}
                              </TableCell>
                              <TableCell className={`text-right ${safeNumber(returnPct, 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                                {formatPercentAuto(returnPct)}
                              </TableCell>
                              <TableCell className="text-right">{formatPercentAuto(item.win_rate)}</TableCell>
                              <TableCell className="text-right">{formatPercentAuto(item.max_drawdown)}</TableCell>
                              <TableCell className="text-right">{formatNumber(item.total_trades, 0)}</TableCell>
                              <TableCell className="whitespace-nowrap text-xs text-muted-foreground">{formatDateTime(item.created_at)}</TableCell>
                              <TableCell>
                                <span className={`inline-flex rounded-full border px-2 py-1 text-xs ${statusTone(item.status)}`}>
                                  {humanize(item.status || "unknown")}
                                </span>
                              </TableCell>
                              <TableCell>
                                <div className="flex flex-wrap justify-end gap-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => void openDetail(item)}
                                    className="rounded-lg border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                                  >
                                    <Eye className="mr-1.5 h-3.5 w-3.5" />
                                    View Report
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => rerunBacktest(item)}
                                    className="rounded-lg border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                                  >
                                    <Play className="mr-1.5 h-3.5 w-3.5" />
                                    Rerun
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => exportRunSummary(item)}
                                    className="rounded-lg border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                                  >
                                    <Download className="mr-1.5 h-3.5 w-3.5" />
                                    Export
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                  </TableBody>
                </Table>
              </div>

              <div className="space-y-3 md:hidden">
                {rows.map((item) => {
                  const pnl = safeNumber(item.net_profit, 0);
                  const returnPct = computeReturnPercent(item);

                  return (
                    <div key={item.id} className="rounded-xl border border-border/50 bg-card/20 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-foreground">{item.strategy_name || "—"}</p>
                          <p className="text-xs text-muted-foreground">
                            {item.instrument_symbol || "—"} • {item.timeframe || "—"}
                          </p>
                        </div>
                        <span className={`inline-flex rounded-full border px-2 py-1 text-[11px] ${statusTone(item.status)}`}>
                          {humanize(item.status || "unknown")}
                        </span>
                      </div>

                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                        <div className="rounded-lg border border-border/40 bg-card/20 p-2">
                          <p className="text-muted-foreground">Drawdown</p>
                          <p className="font-medium text-foreground">{formatPercentAuto(item.max_drawdown)}</p>
                        </div>
                        <div className="rounded-lg border border-border/40 bg-card/20 p-2">
                          <p className="text-muted-foreground">PnL</p>
                          <p className={`font-medium ${pnl >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                            {formatCurrency(item.net_profit, rowCurrencySymbol(item))}
                          </p>
                        </div>
                        <div className="rounded-lg border border-border/40 bg-card/20 p-2">
                          <p className="text-muted-foreground">Return</p>
                          <p className={`font-medium ${safeNumber(returnPct, 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                            {formatPercentAuto(returnPct)}
                          </p>
                        </div>
                        <div className="rounded-lg border border-border/40 bg-card/20 p-2">
                          <p className="text-muted-foreground">Win Rate</p>
                          <p className="font-medium text-foreground">{formatPercentAuto(item.win_rate)}</p>
                        </div>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-1.5 text-[11px] text-muted-foreground">
                        <span className="rounded-full border border-border/40 bg-card/20 px-2 py-0.5">Cap {formatCurrency(item.initial_capital, rowCurrencySymbol(item))}</span>
                        <span className="rounded-full border border-border/40 bg-card/20 px-2 py-0.5">Sharpe {formatNumber(item.sharpe_ratio, 2)}</span>
                      </div>

                      <div className="mt-3 rounded-lg border border-violet-400/40 bg-violet-500/10 px-3 py-2 text-xs text-violet-100">
                        <span className="font-semibold">Runtime Settings:</span> {formatRuntimeSummary(item)}
                      </div>

                      <div className="mt-3 rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-xs text-primary">
                        <span className="font-semibold">Advanced Filters:</span> {formatFilterSummary(item)}
                      </div>

                      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
                        <span className="inline-flex items-center gap-1">
                          <Clock3 className="h-3.5 w-3.5" />
                          {formatDateTime(item.created_at)}
                        </span>
                        <span>{formatNumber(item.total_trades, 0)} trades</span>
                      </div>

                      <div className="mt-3 flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => void openDetail(item)}
                          className="flex-1 rounded-lg border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                        >
                          <Eye className="mr-1.5 h-3.5 w-3.5" />
                          View
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => rerunBacktest(item)}
                          className="flex-1 rounded-lg border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                        >
                          <Play className="mr-1.5 h-3.5 w-3.5" />
                          Rerun
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => exportRunSummary(item)}
                          className="rounded-lg border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                        >
                          <Download className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {!!pagination && pagination.total_pages > 1 && (
                <div className="mt-4 flex flex-col gap-3 rounded-xl border border-border/50 bg-card/20 p-3 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-xs text-muted-foreground">
                    Page {pagination.page} of {pagination.total_pages} • {formatNumber(pagination.total_count, 0)} total runs
                  </p>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={loading || pagination.page <= 1}
                      onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                      className="rounded-lg border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                    >
                      Previous
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={loading || pagination.page >= pagination.total_pages}
                      onClick={() => setCurrentPage((prev) => prev + 1)}
                      className="rounded-lg border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

    </div>
  );
}
