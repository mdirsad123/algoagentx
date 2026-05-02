"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Download, FileSpreadsheet, FileText, Play, RefreshCcw } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";
import { backtestsApi, type BacktestDetailResponse } from "@/lib/api/backtests";
import { parseApiError, formatErrorMessage } from "@/lib/api/error";

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

const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const display = Math.abs(value) <= 1 ? value * 100 : value;
  return `${formatNumber(display, 2)}%`;
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

const formatFilterSummary = (summary: BacktestDetailResponse["summary"]): string => {
  if (summary.filter_summary && summary.filter_summary.trim()) return summary.filter_summary;
  const filters = summary.advanced_filters;
  if (!filters || !filters.enabled) return "Advanced filters were not used for this run.";
  const days = filters.days_of_week?.length ? filters.days_of_week.map(humanize).join(", ") : "All days";
  const session = filters.session === "CUSTOM"
    ? `${filters.custom_start_time || "—"}-${filters.custom_end_time || "—"} ${filters.timezone || "Asia/Kolkata"}`
    : `${humanize(filters.session || "ALL")} Session`;
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
        subtitle="Deep metrics, full trade list, equity analysis, and downloadable reports."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" className="rounded-xl" asChild>
              <Link href="/backtest-history"><ArrowLeft className="mr-2 h-4 w-4" />Back to History</Link>
            </Button>
            <Button variant="outline" onClick={() => router.push(`/backtest?strategyId=${summary.strategy_id || ""}&instrumentId=${summary.instrument_id || ""}`)} className="rounded-xl"><Play className="mr-2 h-4 w-4" />Rerun</Button>
            <Button variant="outline" onClick={exportTradesCsv} className="rounded-xl"><Download className="mr-2 h-4 w-4" />Trades CSV</Button>
            <Button variant="outline" onClick={() => void exportFile("excel")} className="rounded-xl"><FileSpreadsheet className="mr-2 h-4 w-4" />{exporting === "excel" ? "Exporting..." : "Export Excel"}</Button>
            <Button onClick={() => void exportFile("pdf")} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"><FileText className="mr-2 h-4 w-4" />{exporting === "pdf" ? "Exporting..." : "Export PDF"}</Button>
          </div>
        }
      />

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
        {[
          ["PnL", formatCurrency(safeNumber(summary.net_profit, 0))],
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
            <div><span className="text-foreground">Initial Capital:</span> {formatCurrency(safeNumber(summary.initial_capital, 0))}</div>
            <div><span className="text-foreground">Final Capital:</span> {formatCurrency(safeNumber(summary.final_capital, 0))}</div>
            <div><span className="text-foreground">Profit Factor:</span> {formatNumber(safeNumber(summary.profit_factor, 0), 2)}</div>
            <div><span className="text-foreground">Avg Win:</span> {formatCurrency(safeNumber(summary.avg_win, 0))}</div>
            <div><span className="text-foreground">Avg Loss:</span> {formatCurrency(safeNumber(summary.avg_loss, 0))}</div>
            <div><span className="text-foreground">Expectancy:</span> {formatCurrency(safeNumber(summary.expectancy, 0))}</div>
          </CardContent>
        </Card>
      </section>


      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardHeader>
          <CardTitle>Advanced Filters Used</CardTitle>
          <CardDescription>Saved filter scope for this exact backtest run.</CardDescription>
        </CardHeader>
        <CardContent>
          {summary.advanced_filters?.enabled ? (
            <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2 xl:grid-cols-3">
              <div className="rounded-xl border border-primary/30 bg-primary/10 p-3">
                <p className="text-xs text-muted-foreground">Summary</p>
                <p className="mt-1 font-medium text-primary">{formatFilterSummary(summary)}</p>
              </div>
              <div className="rounded-xl border border-border/40 bg-card/20 p-3">
                <p className="text-xs text-muted-foreground">Days</p>
                <p className="mt-1 text-foreground">{summary.advanced_filters.days_of_week?.length ? summary.advanced_filters.days_of_week.map(humanize).join(", ") : "All days"}</p>
              </div>
              <div className="rounded-xl border border-border/40 bg-card/20 p-3">
                <p className="text-xs text-muted-foreground">Session</p>
                <p className="mt-1 text-foreground">{humanize(summary.advanced_filters.session || "ALL")}</p>
              </div>
              <div className="rounded-xl border border-border/40 bg-card/20 p-3">
                <p className="text-xs text-muted-foreground">Custom Time Window</p>
                <p className="mt-1 text-foreground">{summary.advanced_filters.custom_start_time && summary.advanced_filters.custom_end_time ? `${summary.advanced_filters.custom_start_time} → ${summary.advanced_filters.custom_end_time}` : "Not used"}</p>
              </div>
              <div className="rounded-xl border border-border/40 bg-card/20 p-3">
                <p className="text-xs text-muted-foreground">Timezone</p>
                <p className="mt-1 text-foreground">{summary.advanced_filters.timezone || "Asia/Kolkata"}</p>
              </div>
              <div className="rounded-xl border border-border/40 bg-card/20 p-3">
                <p className="text-xs text-muted-foreground">Filter Impact</p>
                <p className="mt-1 text-foreground">
                  {formatNumber(summary.candles_before_filter, 0)} → {formatNumber(summary.candles_after_filter, 0)} candles · {formatPercent(summary.filter_reduction_pct)} reduction
                </p>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-border/40 bg-card/20 p-4 text-sm text-muted-foreground">
              Advanced filters were not used for this run.
            </div>
          )}
        </CardContent>
      </Card>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Equity Curve</CardTitle><CardDescription>{equityRows.length} points captured for this run.</CardDescription></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={equityRows}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="label" hide />
                <YAxis hide domain={["auto", "auto"]} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Line type="monotone" dataKey="equity" stroke="#b7ff39" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Drawdown Curve</CardTitle><CardDescription>Rolling peak-to-equity decline across the run.</CardDescription></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={drawdownRows}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="label" hide />
                <YAxis hide domain={["auto", "auto"]} />
                <Tooltip formatter={(value: number) => `${formatNumber(value, 2)}%`} />
                <Area type="monotone" dataKey="drawdown" stroke="#fb7185" fill="#fb7185" fillOpacity={0.18} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2 rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Trade List</CardTitle><CardDescription>{detail.trades.length} trades captured for this report.</CardDescription></CardHeader>
          <CardContent>
            <div className="max-h-[520px] overflow-auto rounded-lg border border-border/40">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-card/90 text-left text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Entry</th><th className="px-3 py-2">Exit</th><th className="px-3 py-2">Side</th><th className="px-3 py-2">Qty</th><th className="px-3 py-2">Entry Price</th><th className="px-3 py-2">Exit Price</th><th className="px-3 py-2">PnL</th><th className="px-3 py-2">Exit Type</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.trades.length ? detail.trades.map((trade, index) => (
                    <tr key={`${trade.id || index}`} className="border-t border-border/30">
                      <td className="px-3 py-2 text-muted-foreground">{formatDateTime(trade.entry_time)}</td>
                      <td className="px-3 py-2 text-muted-foreground">{formatDateTime(trade.exit_time)}</td>
                      <td className="px-3 py-2 text-foreground">{trade.side || "—"}</td>
                      <td className="px-3 py-2 text-foreground">{formatNumber(safeNumber(trade.quantity, 0), 0)}</td>
                      <td className="px-3 py-2 text-foreground">{formatNumber(safeNumber(trade.entry_price, 0), 2)}</td>
                      <td className="px-3 py-2 text-foreground">{formatNumber(safeNumber(trade.exit_price, 0), 2)}</td>
                      <td className={`px-3 py-2 ${safeNumber(trade.pnl, 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{formatCurrency(safeNumber(trade.pnl, 0))}</td>
                      <td className="px-3 py-2 text-muted-foreground">{trade.exit_type || "—"}</td>
                    </tr>
                  )) : (
                    <tr><td className="px-3 py-6 text-center text-muted-foreground" colSpan={8}>No trade rows are available for this run.</td></tr>
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
                  <div>{formatCurrency(row.pnl)}</div>
                </div>
              )) : <div className="py-8 text-center text-sm text-muted-foreground">No daily PnL rows are available for this run.</div>}
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
