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

const formatNumber = (value: number | null | undefined, digits = 2): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
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

export default function BacktestHistoryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [strategies, setStrategies] = useState<StrategyOption[]>([]);
  const [instruments, setInstruments] = useState<InstrumentOption[]>([]);
  const [timeframes, setTimeframes] = useState<string[]>([]);

  const [draftFilters, setDraftFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [quickRange, setQuickRange] = useState<QuickRange>(null);
  const [advancedOpen, setAdvancedOpen] = useState(true);

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
      ["Entry Time", "Exit Time", "Side", "Quantity", "Entry Price", "Exit Price", "PnL", "Exit Type"],
      detail.trades.map((trade) => [
        trade.entry_time || "",
        trade.exit_time || "",
        trade.side || "",
        trade.quantity ?? "",
        trade.entry_price ?? "",
        trade.exit_price ?? "",
        trade.pnl ?? "",
        trade.exit_type || "",
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

    const totalProfit = rows.reduce((sum, item) => sum + safeNumber(item.net_profit, 0), 0);

    return {
      totalRuns: pagination?.total_count ?? rows.length,
      profitableRuns,
      avgReturn,
      avgDrawdown,
      totalProfit,
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
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Total Runs</CardDescription>
            <CardTitle className="text-2xl text-foreground">{formatNumber(summaryStats.totalRuns, 0)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">Across current filter scope</CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Profitable Runs</CardDescription>
            <CardTitle className="text-2xl text-emerald-300">{formatNumber(summaryStats.profitableRuns, 0)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">Calculated on visible results</CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Avg Return</CardDescription>
            <CardTitle className="text-2xl text-foreground">{formatPercentAuto(summaryStats.avgReturn)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">Visible result set average</CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Avg Drawdown</CardDescription>
            <CardTitle className="text-2xl text-foreground">{formatPercentAuto(summaryStats.avgDrawdown)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">Lower is better</CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Total PnL</CardDescription>
            <CardTitle className={`text-2xl ${summaryStats.totalProfit >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
              {formatCurrency(summaryStats.totalProfit)}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">Sum of visible runs</CardContent>
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
                onClick={clearAllFilters}
                className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                Clear Filters
              </Button>
            </div>
          </div>

          <div className="rounded-xl border border-border/50 bg-card/20">
            <button
              type="button"
              onClick={() => setAdvancedOpen((prev) => !prev)}
              className="flex w-full items-center justify-between px-4 py-3 text-left"
            >
              <div>
                <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <SlidersHorizontal className="h-4 w-4 text-primary" />
                  Advanced Filters
                </p>
                <p className="text-xs text-muted-foreground">
                  Strategy, instrument, timeframe, date, profitability, drawdown, and status.
                </p>
              </div>
              <span className="text-xs text-muted-foreground">
                {activeFilterCount > 0 ? `${activeFilterCount} active` : "No active filters"}
              </span>
            </button>

            {advancedOpen && (
              <div className="space-y-4 border-t border-border/50 p-4">
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
                    <Label className="text-muted-foreground">Min Profit (₹)</Label>
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
              <div className="hidden overflow-x-auto rounded-xl border border-border/50 md:block">
                <Table className="min-w-[1280px]">
                  <TableHeader>
                    <TableRow className="border-border/50 hover:bg-transparent">
                      <TableHead>Strategy</TableHead>
                      <TableHead>Instrument</TableHead>
                      <TableHead>Timeframe</TableHead>
                      <TableHead className="text-right">Capital</TableHead>
                      <TableHead className="text-right">PnL</TableHead>
                      <TableHead className="text-right">Return %</TableHead>
                      <TableHead className="text-right">Win Rate</TableHead>
                      <TableHead className="text-right">Sharpe</TableHead>
                      <TableHead className="text-right">Drawdown</TableHead>
                      <TableHead className="text-right">Trades</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>

                  <TableBody>
                    {loading
                      ? Array.from({ length: 6 }).map((_, idx) => (
                          <TableRow key={`skeleton-${idx}`} className="border-border/30 hover:bg-transparent">
                            <TableCell colSpan={13} className="py-4">
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
                              <TableCell className="font-medium">{item.strategy_name || "—"}</TableCell>
                              <TableCell>{item.instrument_symbol || "—"}</TableCell>
                              <TableCell>{item.timeframe || "—"}</TableCell>
                              <TableCell className="text-right">{formatCurrency(item.initial_capital)}</TableCell>
                              <TableCell className={`text-right font-medium ${pnl >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                                {formatCurrency(item.net_profit)}
                              </TableCell>
                              <TableCell className={`text-right ${safeNumber(returnPct, 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                                {formatPercentAuto(returnPct)}
                              </TableCell>
                              <TableCell className="text-right">{formatPercentAuto(item.win_rate)}</TableCell>
                              <TableCell className="text-right">{formatNumber(item.sharpe_ratio, 2)}</TableCell>
                              <TableCell className="text-right">{formatPercentAuto(item.max_drawdown)}</TableCell>
                              <TableCell className="text-right">{formatNumber(item.total_trades, 0)}</TableCell>
                              <TableCell>{formatDateTime(item.created_at)}</TableCell>
                              <TableCell>
                                <span className={`inline-flex rounded-full border px-2 py-1 text-xs ${statusTone(item.status)}`}>
                                  {humanize(item.status || "unknown")}
                                </span>
                              </TableCell>
                              <TableCell>
                                <div className="flex justify-end gap-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => void openDetail(item)}
                                    className="rounded-lg border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                                  >
                                    <Eye className="h-3.5 w-3.5" />
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => rerunBacktest(item)}
                                    className="rounded-lg border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                                  >
                                    <Play className="h-3.5 w-3.5" />
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
                          <p className="text-muted-foreground">Capital</p>
                          <p className="font-medium text-foreground">{formatCurrency(item.initial_capital)}</p>
                        </div>
                        <div className="rounded-lg border border-border/40 bg-card/20 p-2">
                          <p className="text-muted-foreground">PnL</p>
                          <p className={`font-medium ${pnl >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                            {formatCurrency(item.net_profit)}
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
