"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Download, FileSpreadsheet, FileText, Play } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";
import { backtestsApi, type BacktestDetailResponse } from "@/lib/api/backtests";
import { formatCurrency as formatMoney, formatNumber as formatDisplayNumber } from "@/lib/formatters";
import { parseApiError, formatErrorMessage } from "@/lib/api/error";

type TradeRow = BacktestDetailResponse["trades"][number];

const safeNumber = (value: unknown, fallback = 0): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const formatNumber = (value: number | null | undefined, digits = 2): string => formatDisplayNumber(value, digits);

const formatCurrency = (value: number | null | undefined, symbol?: string | null): string => formatMoney(value, symbol || "₹");

const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const display = Math.abs(value) <= 1 ? value * 100 : value;
  return `${formatNumber(display, 2)}%`;
};

const formatRMultiple = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatNumber(value, 2)}R`;
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

const downloadBlob = (filename: string, blob: Blob) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const toCsvSafe = (value: unknown): string => {
  if (value === null || value === undefined) return "";
  const text = String(value);
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
};

const downloadCsv = (filename: string, headers: string[], rows: Array<Array<unknown>>) => {
  const csv = [headers.map(toCsvSafe).join(","), ...rows.map((row) => row.map(toCsvSafe).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  downloadBlob(filename, blob);
};

const humanize = (value?: string | null): string =>
  String(value || "")
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

const getNestedRecord = (value: unknown, key: string): Record<string, unknown> | null => asRecord(asRecord(value)?.[key]);

const asArray = (value: unknown): Array<Record<string, unknown>> => {
  if (!value) return [];
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed.filter((item) => item && typeof item === "object") as Array<Record<string, unknown>> : [];
    } catch {
      return [];
    }
  }
  return Array.isArray(value) ? value.filter((item) => item && typeof item === "object") as Array<Record<string, unknown>> : [];
};

const getNestedValue = (value: unknown, path: string[]): unknown => {
  let current: unknown = value;
  for (const key of path) {
    const record = asRecord(current);
    if (!record || !(key in record)) return undefined;
    current = record[key];
  }
  return current;
};


const formatRuntimeValue = (value: unknown): string => {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "ON" : "OFF";
  if (typeof value === "number") return Number.isFinite(value) ? formatNumber(value, 4).replace(/\.0+$/, "") : "—";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return humanize(String(value));
};

const percentRuntimeValue = (value: unknown): string => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return formatRuntimeValue(value);
  const pct = Math.abs(parsed) <= 1 ? parsed * 100 : parsed;
  return `${formatNumber(pct, 2)}%`;
};

const compactRuntimeSummary = (runtime: Record<string, unknown> | null, fallback?: string | null): string => {
  if (fallback && fallback.trim()) return fallback;
  if (!runtime) return "Runtime settings snapshot was not available for this older backtest.";
  const risk = getNestedRecord(runtime, "risk") || {};
  const slTp = getNestedRecord(runtime, "sl_tp") || {};
  const tm = getNestedRecord(runtime, "trade_management") || {};
  const parts: string[] = [];
  if (risk.risk_percent !== undefined) parts.push(`Risk ${percentRuntimeValue(risk.risk_percent)}`);
  if (slTp.rr_ratio !== undefined) parts.push(`RR 1:${formatRuntimeValue(slTp.rr_ratio)}`);
  if (slTp.sl_mode) parts.push(`${humanize(String(slTp.sl_mode))} SL`);
  if (risk.position_size_mode) parts.push(humanize(String(risk.position_size_mode)));
  if (tm.break_even_enabled) parts.push("Breakeven ON");
  if (tm.trailing_enabled) parts.push("Trail ON");
  if (tm.partial_exit_enabled) parts.push("Partial Exit ON");
  return parts.length ? parts.join(" · ") : "Runtime settings snapshot captured.";
};

const runtimeSectionRows = (runtime: Record<string, unknown> | null) => {
  if (!runtime) return null;
  const risk = getNestedRecord(runtime, "risk") || {};
  const slTp = getNestedRecord(runtime, "sl_tp") || {};
  const execution = getNestedRecord(runtime, "execution") || {};
  const tradeMgmt = getNestedRecord(runtime, "trade_management") || {};
  const strategyParams = getNestedRecord(runtime, "strategy_params") || {};
  return [
    { title: "Risk", rows: [
      ["Initial Capital", formatRuntimeValue(risk.initial_capital)],
      ["Capital Risk %", percentRuntimeValue(risk.risk_percent)],
      ["Position Size Mode", formatRuntimeValue(risk.position_size_mode)],
      ["Fixed Lot Size", formatRuntimeValue(risk.fixed_lot_size)],
      ["Max Lot Cap", formatRuntimeValue(risk.max_lot_cap)],
      ["Max Quantity Cap", formatRuntimeValue(risk.max_quantity_cap)],
    ]},
    { title: "SL / TP", rows: [
      ["RR Ratio", formatRuntimeValue(slTp.rr_ratio)],
      ["SL Mode", formatRuntimeValue(slTp.sl_mode)],
      ["Fixed Price Risk %", percentRuntimeValue(slTp.fixed_price_risk_pct)],
      ["ATR Period", formatRuntimeValue(slTp.atr_period)],
      ["ATR Multiplier", formatRuntimeValue(slTp.atr_multiplier)],
      ["Swing Lookback", formatRuntimeValue(slTp.swing_lookback)],
    ]},
    { title: "Execution", rows: [
      ["Entry Mode", formatRuntimeValue(execution.entry_mode)],
      ["Exit On Opposite Signal", formatRuntimeValue(execution.exit_on_opposite_signal)],
      ["Allow Long", formatRuntimeValue(execution.allow_long)],
      ["Allow Short", formatRuntimeValue(execution.allow_short)],
      ["Max Trades Per Day", formatRuntimeValue(execution.max_trades_per_day)],
      ["Max Open Positions", formatRuntimeValue(execution.max_open_positions)],
    ]},
    { title: "Trade Management", rows: [
      ["Break Even Enabled", formatRuntimeValue(tradeMgmt.break_even_enabled)],
      ["Break Even Trigger R", formatRuntimeValue(tradeMgmt.break_even_trigger_r)],
      ["Trailing Stop Enabled", formatRuntimeValue(tradeMgmt.trailing_enabled)],
      ["Trailing Mode", formatRuntimeValue(tradeMgmt.trailing_mode)],
      ["Trail Start R", formatRuntimeValue(tradeMgmt.trail_start_r)],
      ["Trail ATR Multiplier", formatRuntimeValue(tradeMgmt.trail_atr_multiplier)],
      ["Partial Exit Enabled", formatRuntimeValue(tradeMgmt.partial_exit_enabled)],
      ["Partial Exit At R", formatRuntimeValue(tradeMgmt.partial_exit_at_r)],
      ["Partial Exit Percent", percentRuntimeValue(tradeMgmt.partial_exit_percent)],
    ]},
    { title: "Strategy Parameters", rows: Object.keys(strategyParams).length ? Object.entries(strategyParams).map(([key, value]) => [humanize(key), formatRuntimeValue(value)]) : [["Parameters", "No custom strategy parameters captured"]] },
  ];
};

const formatFilterSummary = (summary: BacktestDetailResponse["summary"]): string => {
  if (summary.filter_summary && summary.filter_summary.trim()) return summary.filter_summary;
  const filters = asRecord(summary.advanced_filters) || (summary.advanced_filters && typeof summary.advanced_filters === "object" ? summary.advanced_filters : null);
  if (!filters || !filters.enabled) return "Advanced filters were not used for this run.";
  const daysRaw = Array.isArray(filters.days_of_week) ? filters.days_of_week : [];
  const days = daysRaw.length ? daysRaw.map((day) => humanize(String(day))).join(", ") : "All days";
  const sessionValue = String(filters.session || "ALL");
  const session = sessionValue === "CUSTOM"
    ? `${filters.custom_start_time || "—"}-${filters.custom_end_time || "—"} ${filters.timezone || "Asia/Kolkata"}`
    : `${humanize(sessionValue)} Session`;
  return `${days} · ${session.replace("All Session", "All sessions")}`;
};

export default function BacktestReportPage() {
  const params = useParams<{ backtestId: string }>();
  const router = useRouter();
  const backtestId = params?.backtestId;

  const [detail, setDetail] = useState<BacktestDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<"excel" | "pdf" | null>(null);
  const [selectedTrade, setSelectedTrade] = useState<TradeRow | null>(null);

  useEffect(() => {
    if (!backtestId) return;
    setLoading(true);
    setError(null);
    backtestsApi
      .getDetail(backtestId)
      .then(setDetail)
      .catch((err) => setError(formatErrorMessage(parseApiError(err))))
      .finally(() => setLoading(false));
  }, [backtestId]);

  const summary = detail?.summary;
  const firstTrade = detail?.trades?.[0];
  const runtimeSnapshot = asRecord(summary?.runtime_config_snapshot) || asRecord(firstTrade?.runtime_config_snapshot);
  const instrumentSnapshot = asRecord(summary?.instrument_spec_snapshot) || asRecord(firstTrade?.instrument_spec_snapshot);
  const riskSnapshot = getNestedRecord(runtimeSnapshot, "risk");
  const slTpSnapshot = getNestedRecord(runtimeSnapshot, "sl_tp");
  const reportCurrencySymbol = summary?.currency_symbol || firstTrade?.currency_symbol || (summary?.account_currency === "USD" ? "$" : summary?.account_currency === "INR" ? "₹" : undefined);
  const quantityMode = String(summary?.quantity_mode || firstTrade?.quantity_mode || "Legacy").toUpperCase();
  const isLotMode = quantityMode === "LOTS";
  const riskPercent = summary?.risk_percent ?? safeNumber(riskSnapshot?.risk_percent, NaN);
  const displayRiskPercent = Number.isFinite(Number(riskPercent)) ? Number(riskPercent) : null;
  const reportRrRatio = summary?.rr_ratio ?? safeNumber(slTpSnapshot?.rr_ratio, NaN);
  const reportSlMode = summary?.sl_mode || String(slTpSnapshot?.sl_mode || "");
  const positionSizeMode = summary?.position_size_mode || String(riskSnapshot?.position_size_mode || "");
  const runtimeSections = runtimeSectionRows(runtimeSnapshot);
  const runtimeSummary = compactRuntimeSummary(runtimeSnapshot, summary?.runtime_summary);
  const advancedFilters = asRecord(summary?.advanced_filters) || (summary?.advanced_filters && typeof summary.advanced_filters === "object" ? summary.advanced_filters : null);

  const returnPct = useMemo(() => {
    if (!summary) return null;
    const initial = safeNumber(summary.initial_capital, 0);
    const final = safeNumber(summary.final_capital, initial + safeNumber(summary.net_profit, 0));
    if (initial <= 0) return null;
    return ((final - initial) / initial) * 100;
  }, [summary]);

  const equityRows = useMemo(() => {
    return (detail?.equity_curve || []).map((point, index) => ({
      label: point.timestamp ? new Date(point.timestamp).toLocaleDateString() : String(index + 1),
      equity: safeNumber(point.equity, 0),
    }));
  }, [detail?.equity_curve]);

  const drawdownRows = useMemo(() => {
    let peak = 0;
    return equityRows.map((row) => {
      peak = Math.max(peak, row.equity);
      const drawdown = peak > 0 ? ((row.equity - peak) / peak) * 100 : 0;
      return { label: row.label, drawdown };
    });
  }, [equityRows]);

  const pnlCalendarRows = useMemo(() => {
    return (detail?.pnl_calendar || []).map((row) => ({
      date: row.date || "—",
      pnl: safeNumber(row.pnl, 0),
    }));
  }, [detail?.pnl_calendar]);

  const exportTradesCsv = () => {
    if (!detail?.trades?.length || !backtestId) return;
    downloadCsv(
      `backtest-${backtestId}-trades.csv`,
      ["Entry Time", "Exit Time", "Side", "Account Currency", "Quantity Mode", "Lot Size", "Quantity", "Entry Price", "Exit Price", "Stop Loss", "Target / TP", "Risk Amount", "Actual Risk Amount", "Risk Points", "Risk Ticks/Pips", "Reward Points", "Expected Reward Amount", "RR Ratio", "SL Mode", "Position Size Mode", "R Multiple", "PnL", "Exit Reason", "Signal Reason", "Lifecycle Events"],
      detail.trades.map((trade) => [
        trade.entry_time || "",
        trade.exit_time || "",
        trade.side || "",
        trade.account_currency || summary?.account_currency || "",
        trade.quantity_mode || summary?.quantity_mode || "",
        trade.lot_size ?? "",
        trade.quantity ?? "",
        trade.entry_price ?? "",
        trade.exit_price ?? "",
        trade.stop_loss ?? "",
        trade.target ?? "",
        trade.risk_amount ?? "",
        trade.actual_risk_amount ?? "",
        trade.risk_points ?? "",
        trade.risk_ticks ?? trade.risk_pips ?? "",
        trade.reward_points ?? "",
        trade.expected_reward_amount ?? trade.reward_amount ?? "",
        trade.rr_ratio ?? "",
        trade.sl_mode || summary?.sl_mode || "",
        trade.position_size_mode || summary?.position_size_mode || "",
        trade.r_multiple ?? "",
        trade.pnl ?? "",
        trade.exit_reason || trade.exit_type || "",
        trade.signal_reason || "",
        asArray(trade.lifecycle_events).map((event) => `${event.event_type || "EVENT"}@${event.candle_time || ""}`).join(" | "),
      ]),
    );
  };

  const exportFile = async (format: "excel" | "pdf") => {
    if (!backtestId) return;
    try {
      setExporting(format);
      const blob = await backtestsApi.downloadExport(backtestId, format);
      downloadBlob(`backtest-${backtestId}-full-report.${format === "excel" ? "xlsx" : "pdf"}`, blob);
    } catch (err) {
      setError(formatErrorMessage(parseApiError(err)));
    } finally {
      setExporting(null);
    }
  };

  if (loading) {
    return <div className="space-y-4"><div className="h-24 animate-pulse rounded-xl bg-card/30" /><div className="h-80 animate-pulse rounded-xl bg-card/30" /></div>;
  }

  if (error || !summary) {
    return (
      <div className="space-y-4">
        <PageHeader title="Backtest Report" subtitle="Detailed analytics, charts, and trade review." />
        <Card className="rounded-xl border border-rose-500/30 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardContent className="flex flex-col gap-3 py-8 text-sm text-rose-200">
            <p>{error || "Unable to load report."}</p>
            <div className="flex gap-3">
              <Button onClick={() => router.refresh()} className="rounded-xl bg-primary text-primary-foreground">Retry</Button>
              <Button variant="outline" onClick={() => router.push("/backtest-history")} className="rounded-xl">Back to History</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Backtest Report · ${summary.strategy_name || "Strategy"}`}
        subtitle="Deep metrics, transparent lot/quantity risk details, equity analysis, and downloadable reports."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" className="rounded-xl" asChild>
              <Link href="/backtest-history"><ArrowLeft className="mr-2 h-4 w-4" />Back to History</Link>
            </Button>
            <Button variant="outline" onClick={() => router.push(`/backtest?strategyId=${summary.strategy_id || ""}&instrumentId=${summary.instrument_id || ""}`)} className="rounded-xl"><Play className="mr-2 h-4 w-4" />Rerun</Button>
            <Button variant="outline" onClick={exportTradesCsv} className="rounded-xl"><Download className="mr-2 h-4 w-4" />Trades CSV</Button>
            <Button variant="outline" disabled={exporting !== null} onClick={() => void exportFile("excel")} className="rounded-xl"><FileSpreadsheet className="mr-2 h-4 w-4" />{exporting === "excel" ? "Exporting..." : "Export Excel"}</Button>
            <Button disabled={exporting !== null} onClick={() => void exportFile("pdf")} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"><FileText className="mr-2 h-4 w-4" />{exporting === "pdf" ? "Exporting PDF..." : "Export PDF"}</Button>
          </div>
        }
      />

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
        {[
          ["PnL", formatCurrency(safeNumber(summary.net_profit, 0), reportCurrencySymbol)],
          ["Return %", formatPercent(returnPct)],
          ["Win Rate", formatPercent(safeNumber(summary.win_rate, 0))],
          ["Sharpe", formatNumber(safeNumber(summary.sharpe_ratio, 0), 2)],
          ["Drawdown", formatPercent(safeNumber(summary.max_drawdown, 0))],
          ["Trades", formatNumber(safeNumber(summary.total_trades, 0), 0)],
        ].map(([label, value]) => (
          <Card key={label} className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
            <CardHeader className="pb-2"><CardDescription>{label}</CardDescription><CardTitle className="text-2xl text-foreground">{value}</CardTitle></CardHeader>
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          ["Account Currency", summary.account_currency || firstTrade?.account_currency || "Legacy"],
          ["Instrument", summary.instrument_symbol || "—"],
          ["Asset Class", summary.asset_class || firstTrade?.asset_class || String(instrumentSnapshot?.asset_class || "Legacy")],
          ["Quantity Mode", summary.quantity_mode || firstTrade?.quantity_mode || "Legacy"],
          ["Position Size Mode", positionSizeMode || "Legacy"],
          ["SL Mode", reportSlMode || "Legacy"],
          ["RR Ratio", Number.isFinite(Number(reportRrRatio)) ? formatNumber(Number(reportRrRatio), 2) : "Legacy"],
          ["Risk %", displayRiskPercent === null ? "Legacy" : formatPercent(displayRiskPercent)],
          ["Initial Capital", formatCurrency(safeNumber(summary.initial_capital, 0), reportCurrencySymbol)],
          ["Avg Actual Risk", formatCurrency(safeNumber(summary.avg_actual_risk, NaN), reportCurrencySymbol)],
          [isLotMode ? "Avg Lot Size" : "Avg Quantity", isLotMode ? formatNumber(safeNumber(summary.avg_lot_size, NaN), 2) : formatNumber(safeNumber(summary.avg_quantity, NaN), 0)],
          ["Gross P/L", `${formatCurrency(safeNumber(summary.gross_profit, 0), reportCurrencySymbol)} / ${formatCurrency(safeNumber(summary.gross_loss, 0), reportCurrencySymbol)}`],
        ].map(([label, value]) => (
          <Card key={label} className="rounded-xl border border-primary/20 bg-primary/10 shadow-xl backdrop-blur-xl">
            <CardHeader className="pb-2"><CardDescription>{label}</CardDescription><CardTitle className="break-words text-lg text-foreground">{value}</CardTitle></CardHeader>
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Run Metadata</CardTitle><CardDescription>Execution identity and market scope.</CardDescription></CardHeader>
          <CardContent className="grid grid-cols-1 gap-2 text-sm text-muted-foreground md:grid-cols-2">
            <div><span className="text-foreground">Backtest ID:</span> {summary.id}</div>
            <div><span className="text-foreground">Created:</span> {formatDateTime(summary.created_at)}</div>
            <div><span className="text-foreground">Strategy:</span> {summary.strategy_name || "—"}</div>
            <div><span className="text-foreground">Instrument:</span> {summary.instrument_symbol || "—"}</div>
            <div><span className="text-foreground">Timeframe:</span> {summary.timeframe || "—"}</div>
            <div><span className="text-foreground">Range:</span> {summary.start_date || "—"} → {summary.end_date || "—"}</div>
          </CardContent>
        </Card>
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Capital & Trade Quality</CardTitle><CardDescription>Profitability and execution quality metrics.</CardDescription></CardHeader>
          <CardContent className="grid grid-cols-1 gap-2 text-sm text-muted-foreground md:grid-cols-2">
            <div><span className="text-foreground">Initial Capital:</span> {formatCurrency(safeNumber(summary.initial_capital, 0), reportCurrencySymbol)}</div>
            <div><span className="text-foreground">Final Capital:</span> {formatCurrency(safeNumber(summary.final_capital, 0), reportCurrencySymbol)}</div>
            <div><span className="text-foreground">Profit Factor:</span> {formatNumber(safeNumber(summary.profit_factor, 0), 2)}</div>
            <div><span className="text-foreground">Avg Win:</span> {formatCurrency(safeNumber(summary.avg_win, 0), reportCurrencySymbol)}</div>
            <div><span className="text-foreground">Avg Loss:</span> {formatCurrency(safeNumber(summary.avg_loss, 0), reportCurrencySymbol)}</div>
            <div><span className="text-foreground">Expectancy:</span> {formatCurrency(safeNumber(summary.expectancy, 0), reportCurrencySymbol)}</div>
          </CardContent>
        </Card>
      </section>


      <Card className="rounded-xl border border-primary/30 bg-primary/10 shadow-xl backdrop-blur-xl">
        <CardHeader>
          <CardTitle>Runtime Settings Used</CardTitle>
          <CardDescription>Exact risk, SL/TP, execution, trade management, and strategy parameter snapshot used for this backtest.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl border border-primary/30 bg-background/30 p-4 text-sm font-medium text-primary">
            {runtimeSummary}
          </div>
          {runtimeSections ? (
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-3">
              {runtimeSections.map((section) => (
                <div key={section.title} className="rounded-xl border border-border/40 bg-card/25 p-4">
                  <h3 className="text-sm font-semibold text-foreground">{section.title}</h3>
                  <div className="mt-3 space-y-2 text-xs">
                    {section.rows.map(([label, value]) => (
                      <div key={`${section.title}-${label}`} className="flex items-start justify-between gap-3 rounded-lg border border-border/30 bg-background/20 px-3 py-2">
                        <span className="text-muted-foreground">{label}</span>
                        <span className="max-w-[55%] break-words text-right font-medium text-foreground">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-border/40 bg-card/20 p-4 text-sm text-muted-foreground">
              Runtime settings snapshot was not available for this older backtest. New backtests will capture this automatically after the RS-4 migration.
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardHeader><CardTitle>Advanced Filters Used</CardTitle><CardDescription>Saved filter scope for this exact backtest run.</CardDescription></CardHeader>
        <CardContent>
          {advancedFilters?.enabled ? (
            <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2 xl:grid-cols-3">
              <div className="rounded-xl border border-primary/30 bg-primary/10 p-3"><p className="text-xs text-muted-foreground">Summary</p><p className="mt-1 font-medium text-primary">{formatFilterSummary(summary)}</p></div>
              <div className="rounded-xl border border-border/40 bg-card/20 p-3"><p className="text-xs text-muted-foreground">Days</p><p className="mt-1 text-foreground">{Array.isArray(advancedFilters.days_of_week) && advancedFilters.days_of_week.length ? advancedFilters.days_of_week.map((day) => humanize(String(day))).join(", ") : "All days"}</p></div>
              <div className="rounded-xl border border-border/40 bg-card/20 p-3"><p className="text-xs text-muted-foreground">Session</p><p className="mt-1 text-foreground">{humanize(String(advancedFilters.session || "ALL"))}</p></div>
              <div className="rounded-xl border border-border/40 bg-card/20 p-3"><p className="text-xs text-muted-foreground">Custom Time Window</p><p className="mt-1 text-foreground">{advancedFilters.custom_start_time && advancedFilters.custom_end_time ? `${advancedFilters.custom_start_time} → ${advancedFilters.custom_end_time}` : "Not used"}</p></div>
              <div className="rounded-xl border border-border/40 bg-card/20 p-3"><p className="text-xs text-muted-foreground">Timezone</p><p className="mt-1 text-foreground">{String(advancedFilters.timezone || "Asia/Kolkata")}</p></div>
              <div className="rounded-xl border border-border/40 bg-card/20 p-3"><p className="text-xs text-muted-foreground">Filter Impact</p><p className="mt-1 text-foreground">{formatNumber(summary.candles_before_filter, 0)} → {formatNumber(summary.candles_after_filter, 0)} candles · {formatPercent(summary.filter_reduction_pct)} reduction</p></div>
            </div>
          ) : (
            <div className="rounded-xl border border-border/40 bg-card/20 p-4 text-sm text-muted-foreground">Advanced filters were not used for this run.</div>
          )}
        </CardContent>
      </Card>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Equity Curve</CardTitle><CardDescription>{equityRows.length} points captured for this run.</CardDescription></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={equityRows}><CartesianGrid strokeDasharray="3 3" opacity={0.15} /><XAxis dataKey="label" hide /><YAxis hide domain={["auto", "auto"]} /><Tooltip formatter={(value: number) => formatCurrency(value, reportCurrencySymbol)} /><Line type="monotone" dataKey="equity" stroke="#b7ff39" strokeWidth={2} dot={false} /></LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Drawdown Curve</CardTitle><CardDescription>Rolling peak-to-equity decline across the run.</CardDescription></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={drawdownRows}><CartesianGrid strokeDasharray="3 3" opacity={0.15} /><XAxis dataKey="label" hide /><YAxis hide domain={["auto", "auto"]} /><Tooltip formatter={(value: number) => `${formatNumber(value, 2)}%`} /><Area type="monotone" dataKey="drawdown" stroke="#fb7185" fill="#fb7185" fillOpacity={0.18} /></AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl xl:col-span-2">
          <CardHeader><CardTitle>Trade List</CardTitle><CardDescription>{detail.trades.length} trades captured. Click any trade for full risk calculation details.</CardDescription></CardHeader>
          <CardContent>
            <div className="max-h-[520px] overflow-auto rounded-lg border border-border/40">
              <table className="min-w-[1900px] w-full text-sm">
                <thead className="sticky top-0 bg-card/90 text-left text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Entry</th><th className="px-3 py-2">Exit</th><th className="px-3 py-2">Side</th><th className="px-3 py-2">{isLotMode ? "Lot Size" : "Quantity"}</th><th className="px-3 py-2">Entry</th><th className="px-3 py-2">Exit</th><th className="px-3 py-2">SL</th><th className="px-3 py-2">TP</th><th className="px-3 py-2">Risk Amount</th><th className="px-3 py-2">Actual Risk</th><th className="px-3 py-2">Risk Pts</th><th className="px-3 py-2">Ticks/Pips</th><th className="px-3 py-2">Reward Pts</th><th className="px-3 py-2">Expected Reward</th><th className="px-3 py-2">PnL</th><th className="px-3 py-2">R</th><th className="px-3 py-2">Exit Reason</th><th className="px-3 py-2">Signal Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.trades.length ? detail.trades.map((trade, index) => {
                    const tradeCurrency = trade.currency_symbol || reportCurrencySymbol;
                    const mode = String(trade.quantity_mode || quantityMode).toUpperCase();
                    const displaySize = mode === "LOTS" ? formatNumber(safeNumber(trade.lot_size, NaN), 2) : formatNumber(safeNumber(trade.quantity, NaN), 0);
                    const ticksPips = trade.risk_ticks ?? trade.risk_pips;
                    return (
                      <tr key={`${trade.id || index}`} onClick={() => setSelectedTrade(trade)} className="cursor-pointer border-t border-border/30 transition hover:bg-primary/10">
                        <td className="px-3 py-2 text-muted-foreground">{formatDateTime(trade.entry_time)}</td>
                        <td className="px-3 py-2 text-muted-foreground">{formatDateTime(trade.exit_time)}</td>
                        <td className="px-3 py-2 text-foreground">{trade.side || "—"}</td>
                        <td className="px-3 py-2 font-semibold text-primary">{displaySize}</td>
                        <td className="px-3 py-2 text-foreground">{formatNumber(safeNumber(trade.entry_price, NaN), 2)}</td>
                        <td className="px-3 py-2 text-foreground">{formatNumber(safeNumber(trade.exit_price, NaN), 2)}</td>
                        <td className="px-3 py-2 text-rose-200">{formatNumber(safeNumber(trade.stop_loss, NaN), 2)}</td>
                        <td className="px-3 py-2 text-emerald-200">{formatNumber(safeNumber(trade.target, NaN), 2)}</td>
                        <td className="px-3 py-2 text-rose-200">{formatCurrency(safeNumber(trade.risk_amount, NaN), tradeCurrency)}</td>
                        <td className="px-3 py-2 text-rose-100">{formatCurrency(safeNumber(trade.actual_risk_amount, NaN), tradeCurrency)}</td>
                        <td className="px-3 py-2 text-foreground">{formatNumber(safeNumber(trade.risk_points, NaN), 2)}</td>
                        <td className="px-3 py-2 text-foreground">{formatNumber(safeNumber(ticksPips, NaN), 2)}</td>
                        <td className="px-3 py-2 text-foreground">{formatNumber(safeNumber(trade.reward_points, NaN), 2)}</td>
                        <td className="px-3 py-2 text-emerald-200">{formatCurrency(safeNumber(trade.expected_reward_amount ?? trade.reward_amount, NaN), tradeCurrency)}</td>
                        <td className={`px-3 py-2 ${safeNumber(trade.pnl, 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{formatCurrency(safeNumber(trade.pnl, NaN), tradeCurrency)}</td>
                        <td className={`px-3 py-2 font-semibold ${safeNumber(trade.r_multiple, 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{formatRMultiple(safeNumber(trade.r_multiple, NaN))}</td>
                        <td className="px-3 py-2 text-muted-foreground">{trade.exit_reason || trade.exit_type || "—"}</td>
                        <td className="max-w-[260px] px-3 py-2 text-muted-foreground">{trade.signal_reason || "—"}</td>
                      </tr>
                    );
                  }) : (
                    <tr><td className="px-3 py-6 text-center text-muted-foreground" colSpan={18}>No trade rows are available for this run.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>PnL Calendar</CardTitle><CardDescription>Daily closed-trade outcomes for the selected run.</CardDescription></CardHeader>
          <CardContent className="space-y-2">
            <div className="max-h-[520px] overflow-auto rounded-lg border border-border/40 p-2">
              {pnlCalendarRows.length ? pnlCalendarRows.map((row) => (
                <div key={row.date} className={`mb-2 rounded-lg border px-3 py-2 text-sm ${row.pnl >= 0 ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-rose-500/30 bg-rose-500/10 text-rose-200"}`}>
                  <div className="font-medium">{row.date}</div>
                  <div>{formatCurrency(row.pnl, reportCurrencySymbol)}</div>
                </div>
              )) : <div className="py-8 text-center text-sm text-muted-foreground">No daily PnL rows are available for this run.</div>}
            </div>
          </CardContent>
        </Card>
      </section>

      {selectedTrade ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/45 backdrop-blur-sm" onClick={() => setSelectedTrade(null)}>
          <aside className="h-full w-full max-w-2xl overflow-y-auto border-l border-border/50 bg-background/95 p-6 shadow-2xl" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-start justify-between gap-4">
              <div><h2 className="text-2xl font-bold text-foreground">Trade Transparency</h2><p className="text-sm text-muted-foreground">Instrument-aware lot, quantity, risk, and runtime config snapshots.</p></div>
              <Button variant="outline" className="rounded-xl" onClick={() => setSelectedTrade(null)}>Close</Button>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
              {[
                ["Side", selectedTrade.side || "—"],
                ["Mode", selectedTrade.quantity_mode || summary.quantity_mode || "Legacy"],
                ["Lot Size", formatNumber(safeNumber(selectedTrade.lot_size, NaN), 2)],
                ["Quantity", formatNumber(safeNumber(selectedTrade.quantity, NaN), 0)],
                ["Risk", formatCurrency(safeNumber(selectedTrade.risk_amount, NaN), selectedTrade.currency_symbol || reportCurrencySymbol)],
                ["Actual Risk", formatCurrency(safeNumber(selectedTrade.actual_risk_amount, NaN), selectedTrade.currency_symbol || reportCurrencySymbol)],
                ["PnL", formatCurrency(safeNumber(selectedTrade.pnl, NaN), selectedTrade.currency_symbol || reportCurrencySymbol)],
                ["R Multiple", formatRMultiple(safeNumber(selectedTrade.r_multiple, NaN))],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl border border-border/40 bg-card/30 p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-semibold text-foreground">{value}</p></div>
              ))}
            </div>

            <div className="mt-6 space-y-4">
              <Card className="rounded-xl border border-border/50 bg-card/30">
                <CardHeader><CardTitle>Risk Calculation</CardTitle><CardDescription>Values captured when the trade was opened.</CardDescription></CardHeader>
                <CardContent className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
                  <div>Risk Points: <span className="text-foreground">{formatNumber(safeNumber(selectedTrade.risk_points, NaN), 2)}</span></div>
                  <div>Risk Ticks/Pips: <span className="text-foreground">{formatNumber(safeNumber(selectedTrade.risk_ticks ?? selectedTrade.risk_pips, NaN), 2)}</span></div>
                  <div>Reward Points: <span className="text-foreground">{formatNumber(safeNumber(selectedTrade.reward_points, NaN), 2)}</span></div>
                  <div>Expected Reward: <span className="text-foreground">{formatCurrency(safeNumber(selectedTrade.expected_reward_amount ?? selectedTrade.reward_amount, NaN), selectedTrade.currency_symbol || reportCurrencySymbol)}</span></div>
                  <div>RR Ratio: <span className="text-foreground">{formatNumber(safeNumber(selectedTrade.rr_ratio, NaN), 2)}</span></div>
                  <div>SL Mode: <span className="text-foreground">{selectedTrade.sl_mode || summary.sl_mode || "Legacy"}</span></div>
                  <div>Position Size Mode: <span className="text-foreground">{selectedTrade.position_size_mode || summary.position_size_mode || "Legacy"}</span></div>
                  <div>Exit Reason: <span className="text-foreground">{selectedTrade.exit_reason || selectedTrade.exit_type || "—"}</span></div>
                </CardContent>
              </Card>

              <Card className="rounded-xl border border-border/50 bg-card/30">
                <CardHeader><CardTitle>Instrument Spec Snapshot</CardTitle><CardDescription>Stored instrument metadata used for this trade.</CardDescription></CardHeader>
                <CardContent className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
                  {(() => {
                    const spec = asRecord(selectedTrade.instrument_spec_snapshot) || instrumentSnapshot || {};
                    const fields = ["asset_class", "account_currency", "currency_symbol", "quantity_mode", "tick_size", "tick_value_per_lot", "contract_size", "lot_step", "min_lot", "pip_size"];
                    return fields.map((field) => <div key={field}><span className="text-muted-foreground">{humanize(field)}:</span> <span className="text-foreground">{String(spec[field] ?? "—")}</span></div>);
                  })()}
                </CardContent>
              </Card>

              <Card className="rounded-xl border border-border/50 bg-card/30">
                <CardHeader><CardTitle>Trade Lifecycle Timeline</CardTitle><CardDescription>Breakeven, trailing stop, partial exit, and final exit events captured candle-by-candle.</CardDescription></CardHeader>
                <CardContent className="space-y-3 text-sm">
                  {(() => {
                    const events = asArray(selectedTrade.lifecycle_events);
                    if (!events.length) return <p className="text-muted-foreground">No lifecycle events were captured for this trade. This may be a legacy run or trade management was disabled.</p>;
                    return events.map((event, index) => (
                      <div key={`${event.event_type || "event"}-${index}`} className="rounded-xl border border-border/40 bg-background/30 p-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-semibold text-foreground">{humanize(String(event.event_type || "EVENT"))}</p>
                          <p className="text-xs text-muted-foreground">{formatDateTime(String(event.candle_time || ""))}</p>
                        </div>
                        <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                          <div>Price: <span className="text-foreground">{formatNumber(safeNumber(event.price, NaN), 2)}</span></div>
                          <div>R: <span className="text-foreground">{formatNumber(safeNumber(event.r_value, NaN), 2)}</span></div>
                          <div>Old SL: <span className="text-foreground">{formatNumber(safeNumber(event.old_sl, NaN), 2)}</span></div>
                          <div>New SL: <span className="text-foreground">{formatNumber(safeNumber(event.new_sl, NaN), 2)}</span></div>
                        </div>
                        {event.reason ? <p className="mt-2 text-xs text-muted-foreground">{String(event.reason)}</p> : null}
                      </div>
                    ));
                  })()}
                </CardContent>
              </Card>

              <Card className="rounded-xl border border-border/50 bg-card/30">
                <CardHeader><CardTitle>Runtime Config Snapshot</CardTitle><CardDescription>Risk, SL/TP, execution, and trade management config used for this run.</CardDescription></CardHeader>
                <CardContent className="space-y-3 text-xs text-muted-foreground">
                  {(() => {
                    const config = asRecord(selectedTrade.runtime_config_snapshot) || runtimeSnapshot;
                    if (!config) return <p>Legacy run. Runtime config snapshot was not captured.</p>;
                    return ["risk", "sl_tp", "execution", "trade_management"].map((section) => (
                      <div key={section} className="rounded-xl border border-border/40 bg-background/30 p-3"><p className="mb-2 font-semibold text-foreground">{humanize(section)}</p><pre className="whitespace-pre-wrap break-words">{JSON.stringify(getNestedValue(config, [section]) || {}, null, 2)}</pre></div>
                    ));
                  })()}
                </CardContent>
              </Card>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
