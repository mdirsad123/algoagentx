"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, BarChart3, Download, FileSpreadsheet, FileText, Loader2, Play, SlidersHorizontal, X } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";
import { useToast } from "@/components/shared/toast";
import { backtestsApi, type BacktestDetailResponse, type TradeChartContextResponse } from "@/lib/api/backtests";
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

const formatDateOnly = (value?: string | null): string => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
};


type NormalizedEquityPoint = {
  label: string;
  timestamp?: string | null;
  equity: number;
  pnl: number | null;
  index: number;
};

type NormalizedDrawdownPoint = {
  label: string;
  timestamp?: string | null;
  drawdown: number;
  index: number;
};

const getNumericField = (value: unknown, keys: string[]): number | null => {
  const record = value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
  if (!record) return null;
  for (const key of keys) {
    if (record[key] === null || record[key] === undefined || record[key] === "") continue;
    const parsed = Number(record[key]);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
};

const getStringField = (value: unknown, keys: string[]): string | null => {
  const record = value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
  if (!record) return null;
  for (const key of keys) {
    const raw = record[key];
    if (raw !== null && raw !== undefined && String(raw).trim()) return String(raw);
  }
  return null;
};

const formatChartLabel = (timestamp: string | null | undefined, index: number): string => {
  if (!timestamp) return `Point ${index + 1}`;
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return String(timestamp);
  return parsed.toLocaleString(undefined, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
};

const formatAxisCurrency = (value: number, symbol?: string | null): string => {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${symbol || "₹"}${formatNumber(value / 1_000_000, 1)}M`;
  if (abs >= 1_000) return `${symbol || "₹"}${formatNumber(value / 1_000, 1)}K`;
  return formatCurrency(value, symbol);
};

const normalizeEquityCurve = (points: unknown[] | undefined, initialCapital?: number | null): NormalizedEquityPoint[] => {
  const initial = Number(initialCapital);
  const hasInitial = Number.isFinite(initial) && initial > 0;
  return (points || []).map((point, index) => {
    const timestamp = getStringField(point, ["timestamp", "time", "date", "datetime", "created_at"]);
    const explicitEquity = getNumericField(point, ["equity", "equity_value", "balance", "capital"]);
    const pnlValue = getNumericField(point, ["pnl", "net_pnl", "profit", "net_profit"]);
    const genericValue = getNumericField(point, ["value"]);
    let equity: number | null = explicitEquity;
    if (equity === null && pnlValue !== null && hasInitial) equity = initial + pnlValue;
    if (equity === null && genericValue !== null) {
      const looksLikePnl = hasInitial && (genericValue < 0 || Math.abs(genericValue) < Math.max(Math.abs(initial) * 0.5, 1));
      equity = looksLikePnl ? initial + genericValue : genericValue;
    }
    if (equity !== null && equity < 0 && hasInitial && pnlValue === null && explicitEquity === null) {
      equity = initial + equity;
    }
    const finalEquity = Number.isFinite(Number(equity)) ? Number(equity) : 0;
    return {
      label: formatChartLabel(timestamp, index),
      timestamp,
      equity: finalEquity,
      pnl: hasInitial ? finalEquity - initial : pnlValue,
      index,
    };
  });
};

const normalizeDrawdownCurve = (points: unknown[] | undefined, equityRows: NormalizedEquityPoint[]): NormalizedDrawdownPoint[] => {
  const source = points && points.length ? points : [];
  if (source.length) {
    return source.map((point, index) => {
      const timestamp = getStringField(point, ["timestamp", "time", "date", "datetime", "created_at"]);
      const raw = getNumericField(point, ["drawdown", "drawdown_pct", "max_drawdown", "value"]);
      const display = raw === null ? 0 : Math.abs(raw) <= 1 ? raw * 100 : raw;
      return { label: formatChartLabel(timestamp, index), timestamp, drawdown: display, index };
    });
  }
  let peak: number | null = null;
  return equityRows.map((row) => {
    peak = peak === null ? row.equity : Math.max(peak, row.equity);
    const drawdown = peak && peak > 0 ? ((row.equity - peak) / peak) * 100 : 0;
    return { label: row.label, timestamp: row.timestamp, drawdown, index: row.index };
  });
};

const EquityTooltip = ({ active, payload, currencySymbol }: { active?: boolean; payload?: Array<{ payload?: NormalizedEquityPoint }>; currencySymbol?: string | null }) => {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="rounded-xl border border-border/50 bg-background/95 px-3 py-2 text-xs shadow-xl backdrop-blur">
      <p className="font-semibold text-foreground">{point.label}</p>
      <p className="mt-1 text-primary">Equity: {formatCurrency(point.equity, currencySymbol)}</p>
      {point.pnl !== null && <p className={point.pnl >= 0 ? "text-emerald-300" : "text-rose-300"}>PnL: {formatCurrency(point.pnl, currencySymbol)}</p>}
    </div>
  );
};

const DrawdownTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload?: NormalizedDrawdownPoint }> }) => {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="rounded-xl border border-border/50 bg-background/95 px-3 py-2 text-xs shadow-xl backdrop-blur">
      <p className="font-semibold text-foreground">{point.label}</p>
      <p className="mt-1 text-rose-300">Drawdown: {formatPercent(point.drawdown)}</p>
    </div>
  );
};

const getDateKey = (value?: string | null): string => {
  if (!value) return "—";
  const raw = String(value);
  const isoMatch = raw.match(/^\d{4}-\d{2}-\d{2}/);
  if (isoMatch) return isoMatch[0];
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, "0");
  const day = String(parsed.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const shortenId = (value?: string | null): string => {
  if (!value) return "—";
  return value.length > 14 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value;
};

const getStatusValue = (summary?: BacktestDetailResponse["summary"] | null): string => {
  const record = asRecord(summary);
  const raw = record?.status || record?.state || record?.run_status || record?.execution_status;
  return raw ? humanize(String(raw)) : "Completed";
};

const numericOrNull = (value: unknown): number | null => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const isNearZero = (value: number, epsilon = 0.000001): boolean => Math.abs(value) <= epsilon;

const getTradeExitLabel = (trade: TradeRow): string =>
  `${trade.exit_reason || ""} ${trade.exit_type || ""}`.toUpperCase();

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

const blobLooksLikeJson = (blob: Blob): boolean => {
  const type = String(blob.type || "").toLowerCase();
  return type.includes("application/json") || type.includes("text/json");
};

const readErrorBlob = async (blob: Blob): Promise<string | null> => {
  if (!blob || blob.size === 0) return null;
  try {
    const text = await blob.text();
    if (!text.trim()) return null;
    try {
      const parsed = JSON.parse(text) as Record<string, unknown>;
      const message = parsed.detail || parsed.message || parsed.error || parsed.title;
      return message ? String(message) : text.slice(0, 500);
    } catch {
      return text.slice(0, 500);
    }
  } catch {
    return null;
  }
};

const getAxiosErrorBlob = (error: unknown): Blob | null => {
  const responseData = (error as { response?: { data?: unknown } })?.response?.data;
  return responseData instanceof Blob ? responseData : null;
};

const isTimeoutLikeError = (error: unknown): boolean => {
  const record = error as { code?: string; message?: string };
  const message = String(record?.message || "").toLowerCase();
  return record?.code === "ECONNABORTED" || message.includes("timeout") || message.includes("timed out");
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


const priceToY = (price: number, minPrice: number, maxPrice: number, height: number, padding: number): number => {
  if (!Number.isFinite(price) || maxPrice <= minPrice) return height / 2;
  return padding + ((maxPrice - price) / (maxPrice - minPrice)) * (height - padding * 2);
};

const findNearestCandleIndex = (candles: TradeChartContextResponse["candles"], timestamp?: string | null): number => {
  if (!candles.length || !timestamp) return -1;
  const target = new Date(timestamp).getTime();
  if (!Number.isFinite(target)) return -1;
  let bestIndex = 0;
  let bestDistance = Number.POSITIVE_INFINITY;
  candles.forEach((candle, index) => {
    const current = new Date(candle.timestamp).getTime();
    const distance = Math.abs(current - target);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  });
  return bestIndex;
};

function TradeVerificationChart({ context, currencySymbol }: { context: TradeChartContextResponse; currencySymbol?: string | null }) {
  const candles = context.candles || [];
  const overlays = context.overlays || {};
  const width = 1040;
  const height = 440;
  const padding = 38;
  const plotWidth = width - padding * 2;
  const plotHeight = height - padding * 2;
  const candleGap = candles.length > 1 ? plotWidth / Math.max(candles.length - 1, 1) : 16;
  const candleWidth = Math.max(3, Math.min(12, candleGap * 0.58));
  const priceCandidates = candles.flatMap((candle) => [safeNumber(candle.high, NaN), safeNumber(candle.low, NaN)]);
  [overlays.entry_price, overlays.exit_price, overlays.stop_loss, overlays.target].forEach((value) => {
    const parsed = numericOrNull(value);
    if (parsed !== null) priceCandidates.push(parsed);
  });
  const validPrices = priceCandidates.filter(Number.isFinite);
  const rawMin = validPrices.length ? Math.min(...validPrices) : 0;
  const rawMax = validPrices.length ? Math.max(...validPrices) : 1;
  const range = Math.max(rawMax - rawMin, 0.0001);
  const minPrice = rawMin - range * 0.08;
  const maxPrice = rawMax + range * 0.08;
  const xForIndex = (index: number) => padding + index * candleGap;
  const entryIndex = findNearestCandleIndex(candles, overlays.entry_time);
  const exitIndex = findNearestCandleIndex(candles, overlays.exit_time);
  const side = String(overlays.side || "").toUpperCase();
  const exitLabel = String(overlays.exit_reason || "EXIT").toUpperCase();
  const pnl = safeNumber(overlays.pnl, 0);
  const isTp = exitLabel.includes("TAKE_PROFIT") || exitLabel.includes("TARGET") || /\bTP\b/.test(exitLabel) || pnl > 0;
  const isSl = exitLabel.includes("STOP_LOSS") || exitLabel.includes("STOPLOSS") || /\bSL\b/.test(exitLabel) || pnl < 0;
  const entryPrice = numericOrNull(overlays.entry_price);
  const slPrice = numericOrNull(overlays.stop_loss);
  const tpPrice = numericOrNull(overlays.target);

  const priceLines = [
    { label: side ? `ENTRY ${side}` : "ENTRY", value: entryPrice, color: "#38bdf8", key: "ENTRY" },
    { label: "SL", value: slPrice, color: "#fb7185", key: "SL" },
    { label: "TP", value: tpPrice, color: "#34d399", key: "TP" },
    { label: isTp ? "TP HIT" : isSl ? "EXIT SL" : "EXIT", value: numericOrNull(overlays.exit_price), color: isTp ? "#34d399" : isSl ? "#fb7185" : "#facc15", key: "EXIT" },
  ].filter((line) => line.value !== null) as Array<{ label: string; value: number; color: string; key: string }>;

  const legendItems = [
    ["Entry", "bg-sky-400"],
    ["Exit", "bg-amber-300"],
    ["SL", "bg-rose-400"],
    ["TP", "bg-emerald-400"],
  ];

  if (!candles.length) {
    return (
      <div className="flex h-[340px] items-center justify-center rounded-2xl border border-border/40 bg-background/25 p-6 text-center text-sm text-muted-foreground md:h-[420px] xl:h-[460px]">
        <div>
          <BarChart3 className="mx-auto mb-3 h-10 w-10 text-primary" />
          <p className="font-semibold text-foreground">No candle data found for this trade window.</p>
          <p className="mt-1">Please ensure market data exists for this instrument/timeframe.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="self-start rounded-2xl border border-border/40 bg-[#12071f]/80 p-3 shadow-inner">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2">
        <div className="flex flex-wrap items-center gap-3 text-xs font-semibold text-muted-foreground">
          {legendItems.map(([label, tone]) => (
            <span key={label} className="inline-flex items-center gap-1.5">
              <span className={`h-2.5 w-2.5 rounded-full ${tone}`} />
              {label}
            </span>
          ))}
        </div>
        <span className="text-[11px] text-muted-foreground">{formatDateTime(candles[0]?.timestamp)} → {formatDateTime(candles[candles.length - 1]?.timestamp)}</span>
      </div>
      <svg id="trade-verification-chart-svg" viewBox={`0 0 ${width} ${height}`} className="block h-[340px] w-full md:h-[420px] xl:h-[500px]" role="img" aria-label="Trade candlestick verification chart">
        <defs>
          <linearGradient id="chartBg" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#1e0b34" />
            <stop offset="100%" stopColor="#37145f" />
          </linearGradient>
          <linearGradient id="rewardZone" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="rgba(52,211,153,0.16)" />
            <stop offset="100%" stopColor="rgba(52,211,153,0.04)" />
          </linearGradient>
          <linearGradient id="riskZone" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="rgba(251,113,133,0.17)" />
            <stop offset="100%" stopColor="rgba(251,113,133,0.04)" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width={width} height={height} rx="18" fill="url(#chartBg)" />
        {entryPrice !== null && slPrice !== null ? (() => {
          const yEntry = priceToY(entryPrice, minPrice, maxPrice, height, padding);
          const ySl = priceToY(slPrice, minPrice, maxPrice, height, padding);
          return <rect x={padding} y={Math.min(yEntry, ySl)} width={plotWidth} height={Math.max(2, Math.abs(yEntry - ySl))} fill="url(#riskZone)" />;
        })() : null}
        {entryPrice !== null && tpPrice !== null ? (() => {
          const yEntry = priceToY(entryPrice, minPrice, maxPrice, height, padding);
          const yTp = priceToY(tpPrice, minPrice, maxPrice, height, padding);
          return <rect x={padding} y={Math.min(yEntry, yTp)} width={plotWidth} height={Math.max(2, Math.abs(yEntry - yTp))} fill="url(#rewardZone)" />;
        })() : null}
        {[0, 1, 2, 3, 4].map((tick) => {
          const y = padding + tick * (plotHeight / 4);
          const price = maxPrice - tick * ((maxPrice - minPrice) / 4);
          return (
            <g key={tick}>
              <line x1={padding} x2={width - padding} y1={y} y2={y} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 6" />
              <text x={width - padding + 8} y={y + 4} fill="rgba(255,255,255,0.55)" fontSize="11">{formatNumber(price, 2)}</text>
            </g>
          );
        })}
        {candles.map((candle, index) => {
          const open = safeNumber(candle.open, 0);
          const high = safeNumber(candle.high, 0);
          const low = safeNumber(candle.low, 0);
          const close = safeNumber(candle.close, 0);
          const x = xForIndex(index);
          const yHigh = priceToY(high, minPrice, maxPrice, height, padding);
          const yLow = priceToY(low, minPrice, maxPrice, height, padding);
          const yOpen = priceToY(open, minPrice, maxPrice, height, padding);
          const yClose = priceToY(close, minPrice, maxPrice, height, padding);
          const bullish = close >= open;
          const bodyY = Math.min(yOpen, yClose);
          const bodyHeight = Math.max(2, Math.abs(yClose - yOpen));
          const color = bullish ? "#34d399" : "#fb7185";
          return (
            <g key={`${candle.timestamp}-${index}`}>
              <line x1={x} x2={x} y1={yHigh} y2={yLow} stroke={color} strokeWidth="1.4" opacity="0.9" />
              <rect x={x - candleWidth / 2} y={bodyY} width={candleWidth} height={bodyHeight} rx="1.5" fill={bullish ? "rgba(52,211,153,0.75)" : "rgba(251,113,133,0.75)"} stroke={color} strokeWidth="1" />
            </g>
          );
        })}
        {priceLines.map((line, index) => {
          const y = priceToY(line.value, minPrice, maxPrice, height, padding);
          const labelX = padding + 8 + (index % 2) * 132;
          const labelWidth = line.label.length > 8 ? 122 : 94;
          return (
            <g key={line.key}>
              <line x1={padding} x2={width - padding} y1={y} y2={y} stroke={line.color} strokeWidth="1.9" strokeDasharray={line.key === "ENTRY" ? "0" : "8 6"} opacity="0.92" />
              <rect x={labelX} y={y - 13} width={labelWidth} height="22" rx="11" fill="#160921" opacity="0.88" stroke={line.color} strokeWidth="1" />
              <text x={labelX + 10} y={y + 4} fill={line.color} fontSize="11" fontWeight="700">{line.label} {formatNumber(line.value, 2)}</text>
            </g>
          );
        })}
        {entryIndex >= 0 ? (() => {
          const x = xForIndex(entryIndex);
          const y = priceToY(safeNumber(overlays.entry_price, candles[entryIndex]?.close || 0), minPrice, maxPrice, height, padding);
          const markerY = Math.max(padding + 18, Math.min(height - padding - 10, side === "SHORT" ? y - 24 : y + 30));
          return (
            <g>
              <line x1={x} x2={x} y1={padding} y2={height - padding} stroke="rgba(56,189,248,0.28)" strokeDasharray="3 5" />
              <circle cx={x} cy={y} r="6" fill="#38bdf8" stroke="#ffffff" strokeWidth="2" />
              <rect x={Math.min(x + 8, width - padding - 112)} y={markerY - 16} width="112" height="22" rx="11" fill="#0c2536" stroke="#38bdf8" strokeWidth="1" />
              <text x={Math.min(x + 18, width - padding - 102)} y={markerY} fill="#7dd3fc" fontSize="11" fontWeight="700">ENTRY {side || "TRADE"}</text>
            </g>
          );
        })() : null}
        {exitIndex >= 0 ? (() => {
          const x = xForIndex(exitIndex);
          const y = priceToY(safeNumber(overlays.exit_price, candles[exitIndex]?.close || 0), minPrice, maxPrice, height, padding);
          const color = isTp ? "#34d399" : isSl ? "#fb7185" : "#c084fc";
          const label = isTp ? "TP HIT" : isSl ? "SL" : "EXIT";
          const labelX = Math.max(padding + 6, Math.min(x + 10, width - padding - 74));
          const labelY = Math.max(padding + 22, y - 10);
          return (
            <g>
              <line x1={x} x2={x} y1={padding} y2={height - padding} stroke={color} strokeDasharray="3 5" opacity="0.45" />
              <rect x={x - 7} y={y - 7} width="14" height="14" rx="3" fill={color} stroke="#ffffff" strokeWidth="2" />
              <rect x={labelX} y={labelY - 16} width="70" height="22" rx="11" fill="#160921" stroke={color} strokeWidth="1" />
              <text x={labelX + 10} y={labelY} fill={color} fontSize="11" fontWeight="700">{label}</text>
            </g>
          );
        })() : null}
        <text x={padding} y={height - 12} fill="rgba(255,255,255,0.55)" fontSize="11">
          {formatDateTime(candles[0]?.timestamp)} → {formatDateTime(candles[candles.length - 1]?.timestamp)} · {currencySymbol || ""}
        </text>
      </svg>
    </div>
  );
}

export default function BacktestReportPage() {
  const params = useParams<{ backtestId: string }>();
  const router = useRouter();
  const { showToast } = useToast();
  const backtestId = params?.backtestId;

  const [detail, setDetail] = useState<BacktestDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<"csv" | "excel" | "pdf" | "pdf-executive" | "pdf-full-audit" | null>(null);
  const [pdfModeModalOpen, setPdfModeModalOpen] = useState(false);
  const [selectedTrade, setSelectedTrade] = useState<TradeRow | null>(null);
  const [runtimeOpen, setRuntimeOpen] = useState(false);
  const [chartTrade, setChartTrade] = useState<TradeRow | null>(null);
  const [chartOpen, setChartOpen] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartContext, setChartContext] = useState<TradeChartContextResponse | null>(null);
  const [chartError, setChartError] = useState<string | null>(null);

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

  const openTradeChart = async (trade: TradeRow, rowIndex?: number) => {
    setChartTrade(trade);
    setChartOpen(true);
    setChartContext(null);
    setChartError(null);

    const fallbackIndex = Number.isFinite(Number(trade.trade_index))
      ? Number(trade.trade_index)
      : Number.isFinite(Number(trade.row_index))
        ? Number(trade.row_index)
        : Number.isFinite(Number(rowIndex))
          ? Number(rowIndex)
          : null;

    if (!backtestId || (!trade.id && fallbackIndex === null)) {
      setChartError("Unable to load chart context for this trade. Market candles may be missing for this instrument/timeframe.");
      return;
    }

    setChartLoading(true);
    try {
      const context = trade.id
        ? await backtestsApi.getTradeChartContext(backtestId, trade.id)
        : await backtestsApi.getTradeChartContextByIndex(backtestId, fallbackIndex as number);
      setChartContext(context);
    } catch (err) {
      const parsed = parseApiError(err);
      const message = formatErrorMessage(parsed);
      setChartError(
        message?.toLowerCase().includes("timeout")
          ? "Unable to load chart context for this trade. The request timed out. Please retry."
          : "Unable to load chart context for this trade. Market candles may be missing for this instrument/timeframe.",
      );
    } finally {
      setChartLoading(false);
    }
  };

  const downloadChartSnapshot = () => {
    const svg = document.getElementById("trade-verification-chart-svg") as SVGSVGElement | null;
    if (!svg || !chartContext?.candles?.length) {
      showToast("Chart snapshot is available after candles load.", "error");
      return;
    }

    try {
      const serializer = new XMLSerializer();
      const svgText = serializer.serializeToString(svg);
      const svgBlob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(svgBlob);
      const image = new Image();
      image.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1040, image.naturalWidth || 1040);
        canvas.height = Math.max(440, image.naturalHeight || 440);
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          URL.revokeObjectURL(url);
          showToast("Unable to create chart snapshot.", "error");
          return;
        }
        ctx.fillStyle = "#12071f";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        canvas.toBlob((blob) => {
          if (!blob) {
            showToast("Unable to create chart snapshot.", "error");
            return;
          }
          const tradeRef = chartTrade?.id || chartTrade?.trade_index || chartTrade?.row_index || "trade";
          downloadBlob(`trade-chart-${shortBacktestId}-${tradeRef}.png`, blob);
        }, "image/png");
      };
      image.onerror = () => {
        URL.revokeObjectURL(url);
        showToast("Unable to create chart snapshot.", "error");
      };
      image.src = url;
    } catch {
      showToast("Unable to create chart snapshot.", "error");
    }
  };

  const summary = detail?.summary;
  const shortBacktestId = shortenId(backtestId || summary?.id || "backtest").replace(/[^a-zA-Z0-9-]/g, "");
  const firstTrade = detail?.trades?.[0];
  const runtimeSnapshot = asRecord(summary?.runtime_config_snapshot) || asRecord(firstTrade?.runtime_config_snapshot);
  const instrumentSnapshot = asRecord(summary?.instrument_spec_snapshot) || asRecord(firstTrade?.instrument_spec_snapshot);
  const riskSnapshot = getNestedRecord(runtimeSnapshot, "risk");
  const slTpSnapshot = getNestedRecord(runtimeSnapshot, "sl_tp");
  const reportCurrencySymbol = summary?.currency_symbol || firstTrade?.currency_symbol || (summary?.account_currency === "USD" ? "$" : summary?.account_currency === "INR" ? "₹" : undefined);
  const quantityMode = String(summary?.quantity_mode || firstTrade?.quantity_mode || "Legacy").toUpperCase();
  const riskPercent = summary?.risk_percent ?? safeNumber(riskSnapshot?.risk_percent, NaN);
  const displayRiskPercent = Number.isFinite(Number(riskPercent)) ? Number(riskPercent) : null;
  const reportRrRatio = summary?.rr_ratio ?? safeNumber(slTpSnapshot?.rr_ratio, NaN);
  const reportSlMode = summary?.sl_mode || String(slTpSnapshot?.sl_mode || "");
  const positionSizeMode = summary?.position_size_mode || String(riskSnapshot?.position_size_mode || "");
  const runtimeSections = runtimeSectionRows(runtimeSnapshot);
  const runtimeSummary = compactRuntimeSummary(runtimeSnapshot, summary?.runtime_summary);
  const advancedFilters = asRecord(summary?.advanced_filters) || (summary?.advanced_filters && typeof summary.advanced_filters === "object" ? summary.advanced_filters : null);
  const advancedFiltersEnabled = Boolean(advancedFilters?.enabled);
  const advancedFilterDays = Array.isArray(advancedFilters?.days_of_week) ? advancedFilters.days_of_week : [];

  const tradeOutcome = useMemo(() => {
    const trades = detail?.trades || [];
    const total = trades.length;
    let winning = 0;
    let losing = 0;
    let breakeven = 0;
    let tpHits = 0;
    let slHits = 0;
    let bestTrade: number | null = null;
    let worstTrade: number | null = null;
    const rValues: number[] = [];

    trades.forEach((trade) => {
      const pnl = safeNumber(trade.pnl, 0);
      if (pnl > 0) winning += 1;
      else if (pnl < 0) losing += 1;
      else if (isNearZero(pnl)) breakeven += 1;

      const exitLabel = getTradeExitLabel(trade);
      if (exitLabel.includes("TAKE_PROFIT") || /\bTP\b/.test(exitLabel)) tpHits += 1;
      else if (exitLabel.includes("STOP_LOSS") || /\bSL\b/.test(exitLabel)) slHits += 1;

      bestTrade = bestTrade === null ? pnl : Math.max(bestTrade, pnl);
      worstTrade = worstTrade === null ? pnl : Math.min(worstTrade, pnl);

      const rMultiple = numericOrNull(trade.r_multiple);
      if (rMultiple !== null) rValues.push(rMultiple);
    });

    const avgR = rValues.length ? rValues.reduce((sum, value) => sum + value, 0) / rValues.length : null;
    const backend = detail?.summary;
    const backendWinning = numericOrNull(backend?.winning_trades_count);
    const backendLosing = numericOrNull(backend?.losing_trades_count);
    const backendBreakeven = numericOrNull(backend?.breakeven_trades_count);
    const backendTpHits = numericOrNull(backend?.tp_hit_count);
    const backendSlHits = numericOrNull(backend?.sl_hit_count);
    const backendOtherExits = numericOrNull(backend?.other_exit_count);
    const backendBestTrade = numericOrNull(backend?.best_trade_pnl);
    const backendWorstTrade = numericOrNull(backend?.worst_trade_pnl);
    const backendAvgR = numericOrNull(backend?.avg_r_multiple);

    return {
      total,
      winning: backendWinning ?? winning,
      losing: backendLosing ?? losing,
      breakeven: backendBreakeven ?? breakeven,
      tpHits: backendTpHits ?? tpHits,
      slHits: backendSlHits ?? slHits,
      otherExits: backendOtherExits ?? Math.max(total - tpHits - slHits, 0),
      bestTrade: backendBestTrade ?? bestTrade,
      worstTrade: backendWorstTrade ?? worstTrade,
      avgR: backendAvgR ?? avgR,
    };
  }, [detail?.summary, detail?.trades]);

  const returnPct = useMemo(() => {
    if (!summary) return null;
    const initial = safeNumber(summary.initial_capital, 0);
    const final = safeNumber(summary.final_capital, initial + safeNumber(summary.net_profit, 0));
    if (initial <= 0) return null;
    return ((final - initial) / initial) * 100;
  }, [summary]);

  const initialCapitalForCharts = numericOrNull(summary?.initial_capital);

  const equityRows = useMemo(() => {
    return normalizeEquityCurve(detail?.equity_curve as unknown[] | undefined, initialCapitalForCharts);
  }, [detail?.equity_curve, initialCapitalForCharts]);

  const drawdownRows = useMemo(() => {
    const detailRecord = detail as unknown as { drawdown_curve?: unknown[] } | null;
    return normalizeDrawdownCurve(detailRecord?.drawdown_curve, equityRows);
  }, [detail, equityRows]);

  const dailyTradeStats = useMemo(() => {
    const map = new Map<string, { trades: number; wins: number; losses: number; breakeven: number }>();
    (detail?.trades || []).forEach((trade) => {
      const key = getDateKey(trade.exit_time || trade.entry_time);
      if (!key || key === "—") return;
      const stats = map.get(key) || { trades: 0, wins: 0, losses: 0, breakeven: 0 };
      const pnl = safeNumber(trade.pnl, 0);
      stats.trades += 1;
      if (pnl > 0) stats.wins += 1;
      else if (pnl < 0) stats.losses += 1;
      else stats.breakeven += 1;
      map.set(key, stats);
    });
    return map;
  }, [detail?.trades]);

  const pnlCalendarRows = useMemo(() => {
    return (detail?.pnl_calendar || []).map((row) => {
      const date = row.date || "—";
      const key = getDateKey(date);
      const tradeStats = dailyTradeStats.get(key) || { trades: 0, wins: 0, losses: 0, breakeven: 0 };
      return {
        date,
        key,
        pnl: safeNumber(row.pnl, 0),
        tradeCount: tradeStats.trades,
        winCount: tradeStats.wins,
        lossCount: tradeStats.losses,
        breakevenCount: tradeStats.breakeven,
      };
    });
  }, [dailyTradeStats, detail?.pnl_calendar]);

  const pnlCalendarStats = useMemo(() => {
    let greenDays = 0;
    let redDays = 0;
    let neutralDays = 0;
    let totalDailyPnl = 0;
    let bestDay: (typeof pnlCalendarRows)[number] | null = null;
    let worstDay: (typeof pnlCalendarRows)[number] | null = null;

    pnlCalendarRows.forEach((row) => {
      totalDailyPnl += row.pnl;
      if (row.pnl > 0) greenDays += 1;
      else if (row.pnl < 0) redDays += 1;
      else neutralDays += 1;
      bestDay = bestDay === null || row.pnl > bestDay.pnl ? row : bestDay;
      worstDay = worstDay === null || row.pnl < worstDay.pnl ? row : worstDay;
    });

    return {
      totalDays: pnlCalendarRows.length,
      greenDays,
      redDays,
      neutralDays,
      totalDailyPnl,
      bestDay,
      worstDay,
    };
  }, [pnlCalendarRows]);

  const exportTradesCsv = () => {
    if (exporting || !backtestId) return;
    if (!detail?.trades?.length) {
      showToast("No trades are available to export.", "warning");
      return;
    }
    try {
      setExporting("csv");
      downloadCsv(
        `backtest-${shortBacktestId}-trades.csv`,
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
      showToast("Trades CSV download started.", "success");
    } catch {
      showToast("CSV export failed. Please retry.", "error");
    } finally {
      setExporting(null);
    }
  };

  const exportFile = async (format: "excel" | "pdf", mode?: "executive" | "full_audit") => {
    if (!backtestId || exporting) return;
    const exportKey: "excel" | "pdf-executive" | "pdf-full-audit" = format === "pdf" ? (mode === "full_audit" ? "pdf-full-audit" : "pdf-executive") : "excel";
    try {
      setExporting(exportKey);
      setError(null);
      const blob = await backtestsApi.downloadExport(backtestId, format, mode ? { mode } : undefined);
      if (!blob || blob.size <= 0) {
        throw new Error("The export returned an empty file. Please retry.");
      }
      if (blobLooksLikeJson(blob)) {
        const message = await readErrorBlob(blob);
        throw new Error(message || "The export returned an error response.");
      }
      const filename = format === "pdf"
        ? `backtest-${shortBacktestId}-${mode === "full_audit" ? "full-audit-report" : "executive-report"}.pdf`
        : `backtest-${shortBacktestId}-full-audit.xlsx`;
      downloadBlob(filename, blob);
      showToast(`${format === "pdf" ? (mode === "full_audit" ? "Full Audit PDF" : "Executive PDF") : "Excel"} download started.`, "success");
      if (format === "pdf") setPdfModeModalOpen(false);
    } catch (err) {
      const errorBlob = getAxiosErrorBlob(err);
      const blobMessage = errorBlob ? await readErrorBlob(errorBlob) : null;
      const fallbackMessage = format === "excel"
        ? "Excel export failed or timed out. Please retry. Large backtests may take longer."
        : mode === "full_audit"
          ? "Full Audit PDF is taking too long. Please use Excel export for complete trade data or try again."
          : "Export is taking longer than expected. Please try Excel for full trade data or reduce report size.";
      const parsedMessage = err instanceof Error ? err.message : formatErrorMessage(parseApiError(err));
      const cleanMessage = isTimeoutLikeError(err) ? fallbackMessage : (blobMessage || parsedMessage || fallbackMessage);
      showToast(cleanMessage, "error");
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
            <div className="flex flex-col gap-1">
              <Button variant="outline" disabled={exporting !== null} onClick={exportTradesCsv} title="Raw trade list" className="rounded-xl">
                {exporting === "csv" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                {exporting === "csv" ? "Preparing CSV..." : "Trades CSV"}
              </Button>
              <span className="px-1 text-[10px] leading-none text-muted-foreground">Raw trade list</span>
            </div>
            <div className="flex flex-col gap-1">
              <Button variant="outline" disabled={exporting !== null} onClick={() => void exportFile("excel")} title="Full audit workbook with trades and daily PnL" className="rounded-xl">
                {exporting === "excel" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileSpreadsheet className="mr-2 h-4 w-4" />}
                {exporting === "excel" ? "Preparing Excel..." : "Export Excel"}
              </Button>
              <span className="px-1 text-[10px] leading-none text-muted-foreground">Full audit workbook</span>
            </div>
            <div className="flex flex-col gap-1">
              <Button disabled={exporting !== null} onClick={() => setPdfModeModalOpen(true)} title="Choose executive or full audit PDF" className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
                {exporting === "pdf-executive" || exporting === "pdf-full-audit" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
                {exporting === "pdf-executive" ? "Preparing PDF..." : exporting === "pdf-full-audit" ? "Preparing Audit PDF..." : "Export PDF"}
              </Button>
              <span className="px-1 text-[10px] leading-none text-muted-foreground">Choose PDF type</span>
            </div>
          </div>
        }
      />


      {pdfModeModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm" onClick={() => exporting ? undefined : setPdfModeModalOpen(false)}>
          <div className="w-full max-w-3xl rounded-2xl border border-border/60 bg-card/95 p-5 shadow-2xl" onClick={(event) => event.stopPropagation()}>
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-foreground">Choose PDF Export Type</h2>
                <p className="mt-1 text-sm text-muted-foreground">Select a short executive report or a complete trade verification PDF.</p>
              </div>
              <Button variant="ghost" size="icon" disabled={exporting !== null} onClick={() => setPdfModeModalOpen(false)} className="rounded-xl">
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="rounded-2xl border border-primary/30 bg-primary/10 shadow-xl">
                <CardHeader>
                  <div className="flex flex-wrap items-center gap-2">
                    <CardTitle className="text-lg">Executive PDF</CardTitle>
                    <span className="rounded-full border border-emerald-400/40 bg-emerald-500/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-200">Recommended for sharing</span>
                  </div>
                  <CardDescription>
                    Short, shareable report with KPI summary, run summary, performance breakdown, trade outcome, runtime snapshot, monthly PnL, equity summary, and best/worst trade samples.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button disabled={exporting !== null} onClick={() => void exportFile("pdf", "executive")} className="w-full rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
                    {exporting === "pdf-executive" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
                    {exporting === "pdf-executive" ? "Preparing Executive PDF..." : "Download Executive PDF"}
                  </Button>
                </CardContent>
              </Card>

              <Card className="rounded-2xl border border-border/60 bg-card/40 shadow-xl">
                <CardHeader>
                  <div className="flex flex-wrap items-center gap-2">
                    <CardTitle className="text-lg">Full Audit PDF</CardTitle>
                    <span className="rounded-full border border-sky-400/40 bg-sky-500/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-sky-200">Best for trade verification</span>
                  </div>
                  <CardDescription>
                    Includes complete trade list for manual verification of entry, exit, SL, TP, PnL, R, exit reason, and signal reason.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="rounded-xl border border-amber-400/30 bg-amber-500/10 p-3 text-xs text-amber-100">
                    This report includes all trades and may generate many pages. For very large backtests, Excel is faster and easier to analyze.
                  </p>
                  <Button variant="outline" disabled={exporting !== null} onClick={() => void exportFile("pdf", "full_audit")} className="w-full rounded-xl">
                    {exporting === "pdf-full-audit" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
                    {exporting === "pdf-full-audit" ? "Preparing Full Audit PDF..." : "Download Full Audit PDF"}
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      ) : null}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {[
          {
            label: "PnL",
            value: formatCurrency(safeNumber(summary.net_profit, 0), reportCurrencySymbol),
            tone: safeNumber(summary.net_profit, 0) >= 0 ? "text-emerald-300" : "text-rose-300",
          },
          {
            label: "Return %",
            value: formatPercent(returnPct),
            tone: safeNumber(returnPct, 0) >= 0 ? "text-emerald-300" : "text-rose-300",
          },
          { label: "Win Rate", value: formatPercent(safeNumber(summary.win_rate, 0)), tone: "text-foreground" },
          { label: "Sharpe", value: formatNumber(safeNumber(summary.sharpe_ratio, 0), 2), tone: "text-foreground" },
          {
            label: "Drawdown",
            value: formatPercent(safeNumber(summary.max_drawdown, 0)),
            tone: "text-rose-200",
          },
          { label: "Trades", value: formatNumber(safeNumber(summary.total_trades, 0), 0), tone: "text-foreground" },
        ].map((card) => (
          <Card key={card.label} className="flex min-h-[118px] rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
            <CardHeader className="flex flex-1 justify-between pb-3">
              <CardDescription className="text-xs font-medium uppercase tracking-wide">{card.label}</CardDescription>
              <CardTitle className={`break-words text-2xl leading-tight ${card.tone}`}>{card.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-3">
            <CardTitle>Run Summary</CardTitle>
            <CardDescription>Clean execution identity and market scope.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {[
              ["Backtest ID", shortenId(summary.id), summary.id],
              ["Strategy", summary.strategy_name || "—"],
              ["Instrument", summary.instrument_symbol || "—"],
              ["Timeframe", summary.timeframe || "—"],
              ["Date Range", `${formatDateOnly(summary.start_date)} → ${formatDateOnly(summary.end_date)}`],
              ["Created", formatDateTime(summary.created_at)],
              ["Status", getStatusValue(summary)],
            ].map(([label, value, title]) => (
              <div key={label} className="flex items-start justify-between gap-4 rounded-lg border border-border/30 bg-background/20 px-3 py-2">
                <span className="text-muted-foreground">{label}</span>
                <span title={title || value} className="max-w-[62%] break-words text-right font-medium text-foreground">{value}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-3">
            <CardTitle>Performance Breakdown</CardTitle>
            <CardDescription>Capital, profit quality, and expectancy.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {[
              ["Initial Capital", formatCurrency(safeNumber(summary.initial_capital, 0), reportCurrencySymbol)],
              ["Final Capital", formatCurrency(safeNumber(summary.final_capital, 0), reportCurrencySymbol)],
              ["Gross Profit", formatCurrency(safeNumber(summary.gross_profit, 0), reportCurrencySymbol), "text-emerald-300"],
              ["Gross Loss", formatCurrency(safeNumber(summary.gross_loss, 0), reportCurrencySymbol), "text-rose-300"],
              ["Net PnL", formatCurrency(safeNumber(summary.net_profit, 0), reportCurrencySymbol), safeNumber(summary.net_profit, 0) >= 0 ? "text-emerald-300" : "text-rose-300"],
              ["Profit Factor", formatNumber(safeNumber(summary.profit_factor, 0), 2)],
              ["Expectancy", formatCurrency(safeNumber(summary.expectancy, 0), reportCurrencySymbol)],
              ["Avg Win", formatCurrency(safeNumber(summary.avg_win, 0), reportCurrencySymbol), "text-emerald-300"],
              ["Avg Loss", formatCurrency(safeNumber(summary.avg_loss, 0), reportCurrencySymbol), "text-rose-300"],
            ].map(([label, value, tone]) => (
              <div key={label} className="flex items-start justify-between gap-4 rounded-lg border border-border/30 bg-background/20 px-3 py-2">
                <span className="text-muted-foreground">{label}</span>
                <span className={`max-w-[62%] break-words text-right font-medium ${tone || "text-foreground"}`}>{value}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-3">
            <CardTitle>Trade Outcome</CardTitle>
            <CardDescription>Frontend-calculated outcome mix from saved trades.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {[
              ["Total Trades", formatNumber(tradeOutcome.total, 0)],
              ["Winning Trades", formatNumber(tradeOutcome.winning, 0), "text-emerald-300"],
              ["Losing Trades", formatNumber(tradeOutcome.losing, 0), "text-rose-300"],
              ["Breakeven Trades", formatNumber(tradeOutcome.breakeven, 0)],
              ["TP Hits", formatNumber(tradeOutcome.tpHits, 0), "text-emerald-300"],
              ["SL Hits", formatNumber(tradeOutcome.slHits, 0), "text-rose-300"],
              ["Other Exits", formatNumber(tradeOutcome.otherExits, 0)],
              ["Best Trade", tradeOutcome.bestTrade === null ? "—" : formatCurrency(tradeOutcome.bestTrade, reportCurrencySymbol), "text-emerald-300"],
              ["Worst Trade", tradeOutcome.worstTrade === null ? "—" : formatCurrency(tradeOutcome.worstTrade, reportCurrencySymbol), "text-rose-300"],
              ["Avg R", tradeOutcome.avgR === null ? "—" : formatRMultiple(tradeOutcome.avgR)],
            ].map(([label, value, tone]) => (
              <div key={label} className="flex items-start justify-between gap-4 rounded-lg border border-border/30 bg-background/20 px-3 py-2">
                <span className="text-muted-foreground">{label}</span>
                <span className={`max-w-[62%] break-words text-right font-medium ${tone || "text-foreground"}`}>{value}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <Card className="rounded-xl border border-primary/30 bg-primary/10 shadow-xl backdrop-blur-xl">
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle>Runtime Settings Snapshot</CardTitle>
            <CardDescription>Exact config used for this backtest.</CardDescription>
          </div>
          <Button onClick={() => setRuntimeOpen(true)} className="w-full rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto">
            <SlidersHorizontal className="mr-2 h-4 w-4" />View Runtime Details
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl border border-primary/30 bg-background/30 p-4 text-sm font-medium text-primary">
            {runtimeSummary}
          </div>
          {runtimeSnapshot ? (
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="rounded-full border border-border/40 bg-background/30 px-3 py-1.5 text-muted-foreground">Risk % <strong className="ml-1 text-foreground">{displayRiskPercent === null ? "—" : percentRuntimeValue(displayRiskPercent)}</strong></span>
              <span className="rounded-full border border-border/40 bg-background/30 px-3 py-1.5 text-muted-foreground">RR <strong className="ml-1 text-foreground">{Number.isFinite(Number(reportRrRatio)) ? `1:${formatRuntimeValue(reportRrRatio)}` : "—"}</strong></span>
              <span className="rounded-full border border-border/40 bg-background/30 px-3 py-1.5 text-muted-foreground">SL Mode <strong className="ml-1 text-foreground">{reportSlMode ? formatRuntimeValue(reportSlMode) : "—"}</strong></span>
              <span className="rounded-full border border-border/40 bg-background/30 px-3 py-1.5 text-muted-foreground">Position Size <strong className="ml-1 text-foreground">{positionSizeMode ? formatRuntimeValue(positionSizeMode) : "—"}</strong></span>
              <span className={`rounded-full border px-3 py-1.5 ${advancedFiltersEnabled ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-border/40 bg-background/30 text-muted-foreground"}`}>Advanced Filters <strong className="ml-1">{advancedFiltersEnabled ? "Used" : "Not used"}</strong></span>
            </div>
          ) : (
            <div className="rounded-xl border border-border/40 bg-card/20 p-4 text-sm text-muted-foreground">
              Runtime settings snapshot was not available for this older backtest.
            </div>
          )}
        </CardContent>
      </Card>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Equity Curve</CardTitle><CardDescription>{equityRows.length} points captured for this run.</CardDescription></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={equityRows}><CartesianGrid strokeDasharray="3 3" opacity={0.15} /><XAxis dataKey="label" hide /><YAxis tickFormatter={(value) => formatAxisCurrency(Number(value), reportCurrencySymbol)} width={64} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} /><Tooltip content={<EquityTooltip currencySymbol={reportCurrencySymbol} />} /><Line type="monotone" dataKey="equity" stroke="#b7ff39" strokeWidth={2} dot={false} /></LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Drawdown Curve</CardTitle><CardDescription>Rolling peak-to-equity decline across the run.</CardDescription></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={drawdownRows}><CartesianGrid strokeDasharray="3 3" opacity={0.15} /><XAxis dataKey="label" hide /><YAxis tickFormatter={(value) => formatPercent(Number(value))} width={56} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} /><Tooltip content={<DrawdownTooltip />} /><Area type="monotone" dataKey="drawdown" stroke="#fb7185" fill="#fb7185" fillOpacity={0.18} /></AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl xl:col-span-2">
          <CardHeader>
            <CardTitle>Trade List</CardTitle>
            <CardDescription>{detail.trades.length} trades captured. Use View for risk details or Chart for visual verification.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-3 xl:grid-cols-6">
              {[
                ["TP Hits", formatNumber(tradeOutcome.tpHits, 0), "text-emerald-300"],
                ["SL Hits", formatNumber(tradeOutcome.slHits, 0), "text-rose-300"],
                ["Other Exits", formatNumber(tradeOutcome.otherExits, 0), "text-foreground"],
                ["Avg R", tradeOutcome.avgR === null ? "—" : formatRMultiple(tradeOutcome.avgR), "text-foreground"],
                ["Best Trade", tradeOutcome.bestTrade === null ? "—" : formatCurrency(tradeOutcome.bestTrade, reportCurrencySymbol), "text-emerald-300"],
                ["Worst Trade", tradeOutcome.worstTrade === null ? "—" : formatCurrency(tradeOutcome.worstTrade, reportCurrencySymbol), "text-rose-300"],
              ].map(([label, value, tone]) => (
                <div key={label} className="rounded-xl border border-border/40 bg-background/20 p-3">
                  <p className="text-muted-foreground">{label}</p>
                  <p className={`mt-1 font-semibold ${tone}`}>{value}</p>
                </div>
              ))}
            </div>

            <div className="responsive-table-wrapper max-h-[560px] overflow-auto rounded-lg border border-border/40">
              <table className="min-w-[1100px] w-full text-sm">
                <thead className="sticky top-0 z-10 bg-card/95 text-left text-xs uppercase tracking-wide text-muted-foreground backdrop-blur-xl">
                  <tr>
                    <th className="px-3 py-3">Entry Time</th>
                    <th className="px-3 py-3">Exit Time</th>
                    <th className="px-3 py-3">Side</th>
                    <th className="px-3 py-3">Size</th>
                    <th className="px-3 py-3">Entry</th>
                    <th className="px-3 py-3">Exit</th>
                    <th className="px-3 py-3">SL</th>
                    <th className="px-3 py-3">TP</th>
                    <th className="px-3 py-3">PnL</th>
                    <th className="px-3 py-3">R</th>
                    <th className="px-3 py-3">Exit Reason</th>
                    <th className="px-3 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.trades.length ? detail.trades.map((trade, index) => {
                    const tradeCurrency = trade.currency_symbol || reportCurrencySymbol;
                    const mode = String(trade.quantity_mode || quantityMode).toUpperCase();
                    const displaySize = mode === "LOTS" ? formatNumber(safeNumber(trade.lot_size, NaN), 2) : formatNumber(safeNumber(trade.quantity, NaN), 0);
                    const side = String(trade.side || "—").toUpperCase();
                    const exitLabel = trade.exit_reason || trade.exit_type || "—";
                    const exitKey = getTradeExitLabel(trade);
                    const isTp = exitKey.includes("TAKE_PROFIT") || /\bTP\b/.test(exitKey);
                    const isSl = exitKey.includes("STOP_LOSS") || /\bSL\b/.test(exitKey);
                    return (
                      <tr key={`${trade.id || index}`} onClick={() => setSelectedTrade(trade)} className="cursor-pointer border-t border-border/30 transition hover:bg-primary/10">
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">{formatDateTime(trade.entry_time)}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">{formatDateTime(trade.exit_time)}</td>
                        <td className="px-3 py-3">
                          <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${side === "SHORT" ? "border-rose-500/30 bg-rose-500/10 text-rose-200" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"}`}>{side}</span>
                        </td>
                        <td className="px-3 py-3 font-semibold text-primary">{displaySize}</td>
                        <td className="px-3 py-3 text-foreground">{formatNumber(safeNumber(trade.entry_price, NaN), 2)}</td>
                        <td className="px-3 py-3 text-foreground">{formatNumber(safeNumber(trade.exit_price, NaN), 2)}</td>
                        <td className="px-3 py-3 text-rose-200">{formatNumber(safeNumber(trade.stop_loss, NaN), 2)}</td>
                        <td className="px-3 py-3 text-emerald-200">{formatNumber(safeNumber(trade.target, NaN), 2)}</td>
                        <td className={`px-3 py-3 font-semibold ${safeNumber(trade.pnl, 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{formatCurrency(safeNumber(trade.pnl, NaN), tradeCurrency)}</td>
                        <td className={`px-3 py-3 font-semibold ${safeNumber(trade.r_multiple, 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{formatRMultiple(safeNumber(trade.r_multiple, NaN))}</td>
                        <td className="px-3 py-3">
                          <span className={`inline-flex max-w-[170px] rounded-full border px-2.5 py-1 text-xs font-medium ${isTp ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : isSl ? "border-rose-500/30 bg-rose-500/10 text-rose-200" : "border-border/40 bg-background/30 text-muted-foreground"}`}>{exitLabel}</span>
                        </td>
                        <td className="px-3 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              className="rounded-xl"
                              onClick={(event) => {
                                event.stopPropagation();
                                setSelectedTrade(trade);
                              }}
                            >
                              View
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="rounded-xl border-cyan-400/30 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20"
                              onClick={(event) => {
                                event.stopPropagation();
                                void openTradeChart(trade, index);
                              }}
                            >
                              <BarChart3 className="mr-1.5 h-3.5 w-3.5" /> Chart
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  }) : (
                    <tr><td className="px-3 py-8 text-center text-muted-foreground" colSpan={12}>No trade rows are available for this run.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-3">
            <CardTitle>PnL Calendar</CardTitle>
            <CardDescription>Daily closed-trade outcomes with win/loss counts and day-level stats.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {pnlCalendarRows.length ? (
              <>
                <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
                  {[
                    ["Total Days", formatNumber(pnlCalendarStats.totalDays, 0), "text-foreground"],
                    ["Green Days", formatNumber(pnlCalendarStats.greenDays, 0), "text-emerald-300"],
                    ["Red Days", formatNumber(pnlCalendarStats.redDays, 0), "text-rose-300"],
                    ["Best Day", pnlCalendarStats.bestDay ? formatCurrency(pnlCalendarStats.bestDay.pnl, reportCurrencySymbol) : "—", "text-emerald-300"],
                    ["Worst Day", pnlCalendarStats.worstDay ? formatCurrency(pnlCalendarStats.worstDay.pnl, reportCurrencySymbol) : "—", "text-rose-300"],
                    ["Total Daily PnL", formatCurrency(pnlCalendarStats.totalDailyPnl, reportCurrencySymbol), pnlCalendarStats.totalDailyPnl >= 0 ? "text-emerald-300" : "text-rose-300"],
                  ].map(([label, value, tone]) => (
                    <div key={label} className="rounded-xl border border-border/40 bg-background/20 p-3">
                      <p className="text-muted-foreground">{label}</p>
                      <p className={`mt-1 break-words font-semibold ${tone}`}>{value}</p>
                    </div>
                  ))}
                </div>

                <div className="max-h-[520px] overflow-auto rounded-xl border border-border/40 p-2">
                  {pnlCalendarRows.map((row) => {
                    const isGreen = row.pnl > 0;
                    const isRed = row.pnl < 0;
                    const tone = isGreen
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                      : isRed
                        ? "border-rose-500/30 bg-rose-500/10 text-rose-200"
                        : "border-border/40 bg-background/25 text-muted-foreground";
                    return (
                      <div key={`${row.key}-${row.date}`} className={`mb-2 rounded-xl border px-3 py-3 text-sm last:mb-0 ${tone}`}>
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-semibold text-foreground">{formatDateOnly(row.date)}</p>
                            <p className="mt-1 text-xs opacity-80">
                              {formatNumber(row.tradeCount, 0)} trades · W/L {formatNumber(row.winCount, 0)}/{formatNumber(row.lossCount, 0)}
                              {row.breakevenCount ? ` · BE ${formatNumber(row.breakevenCount, 0)}` : ""}
                            </p>
                          </div>
                          <p className={`whitespace-nowrap text-right font-bold ${isGreen ? "text-emerald-300" : isRed ? "text-rose-300" : "text-muted-foreground"}`}>
                            {formatCurrency(row.pnl, reportCurrencySymbol)}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="rounded-xl border border-dashed border-border/50 bg-background/20 px-4 py-10 text-center">
                <p className="font-semibold text-foreground">No daily PnL data available</p>
                <p className="mt-1 text-sm text-muted-foreground">This report does not include pnl_calendar rows yet, so daily stats cannot be shown.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {runtimeOpen ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/45 backdrop-blur-sm" onClick={() => setRuntimeOpen(false)}>
          <aside className="h-full w-full max-w-[720px] overflow-y-auto border-l border-border/50 bg-background/95 p-5 shadow-2xl sm:p-6" onClick={(event) => event.stopPropagation()}>
            <div className="sticky top-0 z-10 -mx-5 -mt-5 flex items-start justify-between gap-4 border-b border-border/40 bg-background/95 px-5 py-4 backdrop-blur-xl sm:-mx-6 sm:-mt-6 sm:px-6">
              <div>
                <h2 className="text-2xl font-bold text-foreground">Runtime Settings Used</h2>
                <p className="text-sm text-muted-foreground">Exact risk, execution, trade management, strategy, and filter snapshot.</p>
              </div>
              <Button variant="outline" size="sm" className="rounded-xl" onClick={() => setRuntimeOpen(false)}>
                <X className="mr-2 h-4 w-4" />Close
              </Button>
            </div>

            <div className="mt-6 space-y-5">
              <div className="rounded-xl border border-primary/30 bg-primary/10 p-4 text-sm font-medium text-primary">
                {runtimeSummary}
              </div>

              {runtimeSections ? (
                runtimeSections.map((section) => (
                  <Card key={section.title} className="rounded-xl border border-border/50 bg-card/30">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">{section.title}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm">
                      {section.rows.map(([label, value]) => (
                        <div key={`${section.title}-${label}`} className="flex items-start justify-between gap-3 rounded-lg border border-border/30 bg-background/20 px-3 py-2">
                          <span className="text-muted-foreground">{label}</span>
                          <span className="max-w-[58%] break-words text-right font-medium text-foreground">{value}</span>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                ))
              ) : (
                <Card className="rounded-xl border border-border/50 bg-card/30">
                  <CardContent className="p-4 text-sm text-muted-foreground">Runtime settings snapshot was not available for this older backtest.</CardContent>
                </Card>
              )}

              <Card className="rounded-xl border border-border/50 bg-card/30">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Advanced Filters Used</CardTitle>
                  <CardDescription>Saved filter scope for this exact backtest run.</CardDescription>
                </CardHeader>
                <CardContent>
                  {advancedFiltersEnabled ? (
                    <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                      <div className="rounded-xl border border-primary/30 bg-primary/10 p-3 sm:col-span-2"><p className="text-xs text-muted-foreground">Summary</p><p className="mt-1 font-medium text-primary">{formatFilterSummary(summary)}</p></div>
                      <div className="rounded-xl border border-border/40 bg-background/20 p-3"><p className="text-xs text-muted-foreground">Days</p><p className="mt-1 text-foreground">{advancedFilterDays.length ? advancedFilterDays.map((day) => humanize(String(day))).join(", ") : "All days"}</p></div>
                      <div className="rounded-xl border border-border/40 bg-background/20 p-3"><p className="text-xs text-muted-foreground">Session</p><p className="mt-1 text-foreground">{humanize(String(advancedFilters?.session || "ALL"))}</p></div>
                      <div className="rounded-xl border border-border/40 bg-background/20 p-3"><p className="text-xs text-muted-foreground">Custom Time Window</p><p className="mt-1 text-foreground">{advancedFilters?.custom_start_time && advancedFilters?.custom_end_time ? `${advancedFilters.custom_start_time} → ${advancedFilters.custom_end_time}` : "Not used"}</p></div>
                      <div className="rounded-xl border border-border/40 bg-background/20 p-3"><p className="text-xs text-muted-foreground">Timezone</p><p className="mt-1 text-foreground">{String(advancedFilters?.timezone || "Asia/Kolkata")}</p></div>
                      <div className="rounded-xl border border-border/40 bg-background/20 p-3 sm:col-span-2"><p className="text-xs text-muted-foreground">Filter Impact</p><p className="mt-1 text-foreground">{formatNumber(summary.candles_before_filter, 0)} → {formatNumber(summary.candles_after_filter, 0)} candles · {formatPercent(summary.filter_reduction_pct)} reduction</p></div>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-border/40 bg-background/20 p-4 text-sm text-muted-foreground">Advanced filters were not used for this run.</div>
                  )}
                </CardContent>
              </Card>
            </div>
          </aside>
        </div>
      ) : null}


      {chartOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-3 backdrop-blur-sm" onClick={() => { if (!chartLoading) setChartOpen(false); }}>
          <div className="max-h-[94vh] w-full max-w-[1100px] overflow-y-auto rounded-2xl border border-border/50 bg-background/95 p-4 shadow-2xl sm:p-6" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-start justify-between gap-4 border-b border-border/40 pb-4">
              <div>
                <h2 className="text-2xl font-bold text-foreground">Trade Chart Verification</h2>
                <p className="mt-1 text-sm text-muted-foreground">Visual candle context for entry, exit, SL, TP, and signal reason.</p>
              </div>
              <div className="flex shrink-0 flex-wrap justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-xl"
                  disabled={chartLoading || !chartContext?.candles?.length}
                  onClick={downloadChartSnapshot}
                  title="Download visible chart as PNG"
                >
                  <Download className="mr-2 h-4 w-4" />Snapshot
                </Button>
                <Button variant="outline" size="sm" className="rounded-xl" disabled={chartLoading} onClick={() => setChartOpen(false)}>
                  <X className="mr-2 h-4 w-4" />Close
                </Button>
              </div>
            </div>

            <div className="mt-4 space-y-4">
              {chartTrade ? (() => {
                const tradeCurrency = chartTrade.currency_symbol || reportCurrencySymbol;
                const mode = String(chartTrade.quantity_mode || quantityMode).toUpperCase();
                const displaySize = mode === "LOTS" ? formatNumber(safeNumber(chartTrade.lot_size, NaN), 2) : formatNumber(safeNumber(chartTrade.quantity, NaN), 0);
                return (
                  <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 xl:grid-cols-8">
                    {[
                      ["Side", String(chartTrade.side || "—").toUpperCase(), String(chartTrade.side || "").toUpperCase() === "SHORT" ? "text-rose-200" : "text-emerald-200"],
                      ["Size", displaySize, "text-primary"],
                      ["Entry", formatNumber(safeNumber(chartTrade.entry_price, NaN), 2), "text-foreground"],
                      ["Exit", formatNumber(safeNumber(chartTrade.exit_price, NaN), 2), "text-foreground"],
                      ["SL", formatNumber(safeNumber(chartTrade.stop_loss, NaN), 2), "text-rose-200"],
                      ["TP", formatNumber(safeNumber(chartTrade.target, NaN), 2), "text-emerald-200"],
                      ["PnL", formatCurrency(safeNumber(chartTrade.pnl, NaN), tradeCurrency), safeNumber(chartTrade.pnl, 0) >= 0 ? "text-emerald-300" : "text-rose-300"],
                      ["R", formatRMultiple(safeNumber(chartTrade.r_multiple, NaN)), safeNumber(chartTrade.r_multiple, 0) >= 0 ? "text-emerald-300" : "text-rose-300"],
                    ].map(([label, value, tone]) => (
                      <div key={label} className="rounded-xl border border-border/40 bg-card/30 p-3">
                        <p className="text-muted-foreground">{label}</p>
                        <p className={`mt-1 break-words font-semibold ${tone}`}>{value}</p>
                      </div>
                    ))}
                  </div>
                );
              })() : null}

              {chartLoading ? (
                <div className="flex h-[360px] items-center justify-center rounded-2xl border border-border/40 bg-card/25 text-muted-foreground md:h-[480px]">
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading chart context...
                </div>
              ) : chartError ? (
                <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-100">
                  {chartError || "Unable to load trade chart context. Please retry."}
                </div>
              ) : chartContext ? (
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_320px]">
                  <TradeVerificationChart context={chartContext} currencySymbol={chartTrade?.currency_symbol || reportCurrencySymbol} />
                  <div className="space-y-3">
                    {(chartContext.meta.source === "index" || chartContext.meta.source === "legacy_index") ? (
                      <div className="rounded-xl border border-cyan-400/25 bg-cyan-500/10 p-3 text-sm text-cyan-100">
                        Loaded using trade row reference for this older backtest.
                      </div>
                    ) : null}
                    {chartContext.meta.warning ? (
                      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">{chartContext.meta.warning}</div>
                    ) : null}
                    <Card className="rounded-xl border border-border/50 bg-card/30">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">Signal Reason</CardTitle>
                        <CardDescription>Strategy note captured for this entry.</CardDescription>
                      </CardHeader>
                      <CardContent className="text-sm leading-relaxed text-foreground whitespace-pre-wrap break-words">
                        {chartContext.overlays.signal_reason || chartTrade?.signal_reason || "No signal reason was captured for this trade."}
                      </CardContent>
                    </Card>
                    <Card className="rounded-xl border border-border/50 bg-card/30">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">Trade Window</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2 text-sm">
                        {[
                          ["Instrument", chartContext.meta.instrument_symbol || summary?.instrument_symbol || "—"],
                          ["Timeframe", chartContext.meta.timeframe || summary?.timeframe || "—"],
                          ["Entry Time", formatDateTime(chartContext.overlays.entry_time || chartTrade?.entry_time)],
                          ["Exit Time", formatDateTime(chartContext.overlays.exit_time || chartTrade?.exit_time)],
                          ["Exit Reason", chartContext.overlays.exit_reason || chartTrade?.exit_reason || chartTrade?.exit_type || "—"],
                          ["Candles", `${chartContext.candles.length} loaded`],
                        ].map(([label, value]) => (
                          <div key={label} className="flex items-start justify-between gap-3 rounded-lg border border-border/30 bg-background/20 px-3 py-2">
                            <span className="text-muted-foreground">{label}</span>
                            <span className="max-w-[62%] break-words text-right font-medium text-foreground">{value}</span>
                          </div>
                        ))}
                      </CardContent>
                    </Card>
                    <div className="rounded-xl border border-cyan-400/30 bg-cyan-500/10 p-3 text-xs leading-relaxed text-cyan-100">
                      Horizontal lines mark entry, SL, TP, and exit. The ENTRY marker aligns to the nearest candle around entry time; the EXIT marker uses the saved exit reason and PnL tone.
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      {selectedTrade ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/45 backdrop-blur-sm" onClick={() => setSelectedTrade(null)}>
          <aside className="h-full w-full max-w-2xl overflow-y-auto border-l border-border/50 bg-background/95 p-5 shadow-2xl sm:p-6" onClick={(event) => event.stopPropagation()}>
            <div className="sticky top-0 z-10 -mx-5 -mt-5 flex items-start justify-between gap-4 border-b border-border/40 bg-background/95 px-5 py-4 backdrop-blur-xl sm:-mx-6 sm:-mt-6 sm:px-6">
              <div>
                <h2 className="text-2xl font-bold text-foreground">Trade Transparency</h2>
                <p className="text-sm text-muted-foreground">Clean trade summary with full risk, signal, and snapshot details.</p>
              </div>
              <Button variant="outline" size="sm" className="rounded-xl" onClick={() => setSelectedTrade(null)}>
                <X className="mr-2 h-4 w-4" />Close
              </Button>
            </div>

            <div className="mt-6 space-y-4">
              <Card className="rounded-xl border border-primary/30 bg-primary/10">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Trade Summary</CardTitle>
                  <CardDescription>Side, size, prices, and final outcome.</CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
                  {(() => {
                    const mode = String(selectedTrade.quantity_mode || summary.quantity_mode || quantityMode).toUpperCase();
                    const displaySize = mode === "LOTS" ? formatNumber(safeNumber(selectedTrade.lot_size, NaN), 2) : formatNumber(safeNumber(selectedTrade.quantity, NaN), 0);
                    return [
                      ["Side", selectedTrade.side || "—"],
                      ["Size", displaySize],
                      ["Entry", formatNumber(safeNumber(selectedTrade.entry_price, NaN), 2)],
                      ["Exit", formatNumber(safeNumber(selectedTrade.exit_price, NaN), 2)],
                      ["PnL", formatCurrency(safeNumber(selectedTrade.pnl, NaN), selectedTrade.currency_symbol || reportCurrencySymbol), safeNumber(selectedTrade.pnl, 0) >= 0 ? "text-emerald-300" : "text-rose-300"],
                      ["R", formatRMultiple(safeNumber(selectedTrade.r_multiple, NaN)), safeNumber(selectedTrade.r_multiple, 0) >= 0 ? "text-emerald-300" : "text-rose-300"],
                    ].map(([label, value, tone]) => (
                      <div key={label} className="rounded-xl border border-border/40 bg-background/25 p-3">
                        <p className="text-xs text-muted-foreground">{label}</p>
                        <p className={`mt-1 break-words font-semibold ${tone || "text-foreground"}`}>{value}</p>
                      </div>
                    ));
                  })()}
                </CardContent>
              </Card>

              <Card className="rounded-xl border border-border/50 bg-card/30">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Risk Calculation</CardTitle>
                  <CardDescription>Removed table fields remain available here.</CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
                  {[
                    ["Risk Amount", formatCurrency(safeNumber(selectedTrade.risk_amount, NaN), selectedTrade.currency_symbol || reportCurrencySymbol)],
                    ["Actual Risk", formatCurrency(safeNumber(selectedTrade.actual_risk_amount, NaN), selectedTrade.currency_symbol || reportCurrencySymbol)],
                    ["Risk Points", formatNumber(safeNumber(selectedTrade.risk_points, NaN), 2)],
                    ["Ticks/Pips", formatNumber(safeNumber(selectedTrade.risk_ticks ?? selectedTrade.risk_pips, NaN), 2)],
                    ["Reward Points", formatNumber(safeNumber(selectedTrade.reward_points, NaN), 2)],
                    ["Expected Reward", formatCurrency(safeNumber(selectedTrade.expected_reward_amount ?? selectedTrade.reward_amount, NaN), selectedTrade.currency_symbol || reportCurrencySymbol)],
                    ["RR Ratio", formatNumber(safeNumber(selectedTrade.rr_ratio, NaN), 2)],
                    ["Position Size Mode", selectedTrade.position_size_mode || summary.position_size_mode || "Legacy"],
                    ["SL Mode", selectedTrade.sl_mode || summary.sl_mode || "Legacy"],
                    ["Exit Reason", selectedTrade.exit_reason || selectedTrade.exit_type || "—"],
                  ].map(([label, value]) => (
                    <div key={label} className="flex items-start justify-between gap-3 rounded-lg border border-border/30 bg-background/20 px-3 py-2">
                      <span className="text-muted-foreground">{label}</span>
                      <span className="max-w-[58%] break-words text-right font-medium text-foreground">{value}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="rounded-xl border border-border/50 bg-card/30">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Price Levels</CardTitle>
                  <CardDescription>Entry, exit, stop loss, and target captured for this trade.</CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                  {[
                    ["Entry", formatNumber(safeNumber(selectedTrade.entry_price, NaN), 2), "text-foreground"],
                    ["Exit", formatNumber(safeNumber(selectedTrade.exit_price, NaN), 2), "text-foreground"],
                    ["SL", formatNumber(safeNumber(selectedTrade.stop_loss, NaN), 2), "text-rose-200"],
                    ["TP", formatNumber(safeNumber(selectedTrade.target, NaN), 2), "text-emerald-200"],
                  ].map(([label, value, tone]) => (
                    <div key={label} className="rounded-xl border border-border/40 bg-background/20 p-3">
                      <p className="text-xs text-muted-foreground">{label}</p>
                      <p className={`mt-1 font-semibold ${tone}`}>{value}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="rounded-xl border border-border/50 bg-card/30">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Signal Reason</CardTitle>
                  <CardDescription>Strategy explanation saved when this trade was generated.</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="rounded-xl border border-border/40 bg-background/20 p-4 text-sm leading-relaxed text-foreground whitespace-pre-wrap break-words">
                    {selectedTrade.signal_reason || "No signal reason was captured for this trade."}
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-xl border border-border/50 bg-card/30">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Trade Lifecycle Timeline</CardTitle>
                  <CardDescription>Breakeven, trailing stop, partial exit, and final exit events captured candle-by-candle.</CardDescription>
                </CardHeader>
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

              <details className="rounded-xl border border-border/50 bg-card/30 p-4">
                <summary className="cursor-pointer text-sm font-semibold text-foreground">Instrument Spec Snapshot</summary>
                <div className="mt-4 grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
                  {(() => {
                    const spec = asRecord(selectedTrade.instrument_spec_snapshot) || instrumentSnapshot || {};
                    const fields = ["asset_class", "account_currency", "currency_symbol", "quantity_mode", "tick_size", "tick_value_per_lot", "contract_size", "lot_step", "min_lot", "pip_size"];
                    return fields.map((field) => <div key={field} className="rounded-lg border border-border/30 bg-background/20 px-3 py-2"><span className="text-muted-foreground">{humanize(field)}:</span> <span className="text-foreground">{String(spec[field] ?? "—")}</span></div>);
                  })()}
                </div>
              </details>

              <details className="rounded-xl border border-border/50 bg-card/30 p-4">
                <summary className="cursor-pointer text-sm font-semibold text-foreground">Runtime Config Snapshot</summary>
                <div className="mt-4 space-y-3 text-xs text-muted-foreground">
                  {(() => {
                    const config = asRecord(selectedTrade.runtime_config_snapshot) || runtimeSnapshot;
                    if (!config) return <p>Legacy run. Runtime config snapshot was not captured.</p>;
                    return ["risk", "sl_tp", "execution", "trade_management"].map((section) => (
                      <div key={section} className="rounded-xl border border-border/40 bg-background/30 p-3"><p className="mb-2 font-semibold text-foreground">{humanize(section)}</p><pre className="whitespace-pre-wrap break-words">{JSON.stringify(getNestedValue(config, [section]) || {}, null, 2)}</pre></div>
                    ));
                  })()}
                </div>
              </details>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
