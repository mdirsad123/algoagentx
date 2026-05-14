"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { ResponsiveTableWrapper } from "@/components/ui/ResponsiveTableWrapper";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/EmptyState";
import { parseApiError, formatErrorMessage } from "@/lib/api/error";
import { backtestsApi } from "@/lib/api/backtests";
import {
  BillingCreditsReport,
  CreditEvent,
  DEFAULT_REPORT_SUMMARY,
  PaymentEvent,
  RecentReportBacktest,
  ReportActivityItem,
  ReportPerformanceCard,
  reportsApi,
  UserReportSummaryResponse,
} from "@/lib/api/reports";
import {
  Activity,
  Bell,
  CalendarDays,
  CreditCard,
  Download,
  Eye,
  FileSpreadsheet,
  History,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  WalletCards,
  Zap,
} from "lucide-react";

const orderedCards = ["today", "week", "month", "year"];

const safeNumber = (value: unknown, fallback = 0): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

function formatReportPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "0%";
  const numeric = Number(value);
  const percent = Math.abs(numeric) <= 1 ? numeric * 100 : numeric;
  return `${percent.toFixed(2).replace(/\.00$/, "")}%`;
}

function formatReportMoney(value: number | null | undefined, currencySymbol = "$") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return `${currencySymbol}0`;
  }
  const numeric = Number(value);
  const sign = numeric < 0 ? "-" : "";
  return `${sign}${currencySymbol}${Math.abs(numeric).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatReportDrawdown(value: number | null | undefined, currencySymbol = "$", drawdownType?: string | null) {
  if (drawdownType === "percent") return formatReportPercent(value);
  if (value === null || value === undefined || Number.isNaN(Number(value))) return `${currencySymbol}0`;
  return `${currencySymbol}${Math.abs(Number(value)).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

const formatCount = (value: unknown): string => safeNumber(value).toLocaleString(undefined, { maximumFractionDigits: 0 });

const formatDate = (value?: string | null): string => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
};

const toCsvSafe = (value: unknown): string => {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
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

const exportRecentBacktestsCsv = (rows: RecentReportBacktest[]) => {
  if (typeof window === "undefined" || rows.length === 0) return;
  const headers = ["Date", "Strategy", "Instrument", "Timeframe", "Net P&L", "Win Rate", "Max DD", "Trades", "Status"];
  const csvRows = rows.map((row) => [
    row.created_at || "",
    row.strategy_name || "",
    row.instrument_symbol || "",
    row.timeframe || "",
    row.net_profit,
    formatReportPercent(row.win_rate),
    row.max_drawdown,
    row.total_trades,
    row.status || "",
  ]);
  const csv = [headers.map(toCsvSafe).join(","), ...csvRows.map((row) => row.map(toCsvSafe).join(","))].join("\n");
  downloadBlob("algoagentx-reports-recent-backtests.csv", new Blob([csv], { type: "text/csv;charset=utf-8;" }));
};

const statusClassName = (status?: string | null): string => {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "completed" || normalized === "success" || normalized === "paid" || normalized === "active") return "border-emerald-300/30 bg-emerald-500/15 text-emerald-100";
  if (["failed", "error", "declined", "cancelled"].includes(normalized)) return "border-rose-300/30 bg-rose-500/15 text-rose-100";
  if (["running", "pending", "queued", "warning"].includes(normalized)) return "border-amber-300/30 bg-amber-500/15 text-amber-100";
  return "border-white/10 bg-white/10 text-purple-100";
};

const activityIcon = (type?: string | null) => {
  const normalized = String(type || "").toLowerCase();
  if (normalized.includes("billing") || normalized.includes("credit") || normalized.includes("payment")) return <WalletCards className="h-4 w-4" />;
  if (normalized.includes("broker") || normalized.includes("live")) return <Zap className="h-4 w-4" />;
  if (normalized.includes("backtest")) return <History className="h-4 w-4" />;
  return <Bell className="h-4 w-4" />;
};

function MetricBox({ label, value, tone = "white" }: { label: string; value: string | number; tone?: "white" | "lime" | "rose" | "sky" }) {
  const toneClass = tone === "lime" ? "text-lime-300" : tone === "rose" ? "text-rose-200" : tone === "sky" ? "text-sky-200" : "text-white";
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className={`text-2xl font-black ${toneClass}`}>{value}</div>
      <div className="mt-1 text-sm text-purple-100/70">{label}</div>
    </div>
  );
}

function PerformanceCard({ card, symbol }: { card: ReportPerformanceCard; symbol: string }) {
  const pnl = safeNumber(card.net_profit);
  return (
    <GlassCard className="p-5" hoverEffect={false}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-purple-100/70">{card.label}</p>
          <p className={pnl >= 0 ? "mt-2 text-3xl font-black text-lime-300" : "mt-2 text-3xl font-black text-rose-300"}>
            {formatReportMoney(pnl, symbol)}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/10 p-3 text-purple-100">
          <CalendarDays className="h-5 w-5" />
        </div>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-2 text-xs text-purple-100/70 lg:grid-cols-4">
        <div className="rounded-xl bg-white/5 p-2"><span className="block text-white">{formatCount(card.total_trades)}</span>Trades</div>
        <div className="rounded-xl bg-white/5 p-2"><span className="block text-white">{formatReportPercent(card.win_rate)}</span>Win Rate</div>
        <div className="rounded-xl bg-white/5 p-2"><span className="block text-rose-200">{formatReportDrawdown(card.max_drawdown, symbol, "amount")}</span>Max DD</div>
        <div className="rounded-xl bg-white/5 p-2"><span className="block text-white">{formatCount(card.backtest_count)}</span>Backtests</div>
      </div>
    </GlassCard>
  );
}

function LiveSummaryCards({ data, symbol }: { data: UserReportSummaryResponse; symbol: string }) {
  const live = data.live_summary;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricBox label="Today Live P&L" value={formatReportMoney(live.today_profit, symbol)} tone={safeNumber(live.today_profit) >= 0 ? "lime" : "rose"} />
      <MetricBox label="Total Live P&L" value={formatReportMoney(live.total_net_profit, symbol)} tone={safeNumber(live.total_net_profit) >= 0 ? "lime" : "rose"} />
      <MetricBox label="Open Positions" value={formatCount(live.open_positions)} />
      <MetricBox label="Closed Trades" value={formatCount(live.closed_trades)} />
      <MetricBox label="Win Rate" value={formatReportPercent(live.win_rate)} tone="sky" />
      <MetricBox label="Max Drawdown" value={formatReportDrawdown(live.max_drawdown, symbol, live.max_drawdown_type)} tone="rose" />
      <MetricBox label="Active Deployments" value={formatCount(live.active_deployments)} />
      <MetricBox label="Connected Brokers" value={formatCount(live.connected_brokers)} />
    </div>
  );
}

function BacktestMobileCard({ row, onDownload, downloading }: { row: RecentReportBacktest; onDownload: (row: RecentReportBacktest, format: "pdf" | "excel") => void; downloading: string | null }) {
  const symbol = row.currency_symbol || "₹";
  const pnl = safeNumber(row.net_profit);
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-xl shadow-black/10 md:hidden">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-white">{row.strategy_name || "Unknown Strategy"}</p>
          <p className="text-sm text-purple-100/60">{row.instrument_symbol || "—"} · {row.timeframe || "—"}</p>
        </div>
        <Badge className={statusClassName(row.status)}>{row.status || "unknown"}</Badge>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-xl bg-white/5 p-3 text-purple-100/70"><span className={pnl >= 0 ? "block font-semibold text-lime-300" : "block font-semibold text-rose-300"}>{formatReportMoney(pnl, symbol)}</span>Net P&amp;L</div>
        <div className="rounded-xl bg-white/5 p-3 text-purple-100/70"><span className="block font-semibold text-white">{formatReportPercent(row.win_rate)}</span>Win Rate</div>
        <div className="rounded-xl bg-white/5 p-3 text-purple-100/70"><span className="block font-semibold text-rose-200">{formatReportDrawdown(row.max_drawdown, symbol, row.max_drawdown_type || "amount")}</span>Max DD</div>
        <div className="rounded-xl bg-white/5 p-3 text-purple-100/70"><span className="block font-semibold text-white">{formatCount(row.total_trades)}</span>Trades</div>
      </div>
      <p className="mt-3 text-xs text-purple-100/45">{formatDate(row.created_at)}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button asChild size="sm" variant="outline" className="border-white/10 bg-white/5 text-purple-100 hover:bg-white/10">
          <Link href={`/backtest-report/${row.id}`}><Eye className="mr-2 h-4 w-4" /> View</Link>
        </Button>
        <Button size="sm" variant="outline" className="border-white/10 bg-white/5 text-purple-100 hover:bg-white/10" disabled={downloading === `${row.id}:pdf`} onClick={() => onDownload(row, "pdf")}>
          <Download className="mr-2 h-4 w-4" /> PDF
        </Button>
        <Button size="sm" variant="outline" className="border-white/10 bg-white/5 text-purple-100 hover:bg-white/10" disabled={downloading === `${row.id}:excel`} onClick={() => onDownload(row, "excel")}>
          <FileSpreadsheet className="mr-2 h-4 w-4" /> Excel
        </Button>
      </div>
    </div>
  );
}

function ActivityList({ items }: { items: ReportActivityItem[] }) {
  if (!items.length) {
    return (
      <EmptyState
        title="No activity yet"
        description="Your report activity will appear after backtests, broker events, strategy updates, and billing events."
        action={<Activity className="mx-auto h-8 w-8 text-purple-100/50" />}
      />
    );
  }
  return (
    <GlassCard className="p-6" hoverEffect={false}>
      <div className="mb-5">
        <h2 className="workspace-section-title">Recent Activity</h2>
        <p className="workspace-muted-text">Real account events collected from notifications and reports.</p>
      </div>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={`${item.source}-${item.id}-${item.created_at}`} className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex gap-3">
              <div className="mt-1 rounded-xl border border-white/10 bg-white/10 p-2 text-purple-100">{activityIcon(item.type)}</div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-white">{item.title || "Activity"}</p>
                  <Badge className={statusClassName(item.status)}>{item.status || "info"}</Badge>
                </div>
                <p className="mt-1 text-sm text-purple-100/70">{item.message || "—"}</p>
                <p className="mt-2 text-xs text-purple-100/45">{item.source || "Reports"} · {formatDate(item.created_at)}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

function CreditEventRow({ event }: { event: CreditEvent }) {
  const isDebit = String(event.type).toLowerCase() === "debit";
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
      <div>
        <p className="font-semibold text-white">{event.reason || "Credit transaction"}</p>
        <p className="text-xs text-purple-100/45">{formatDate(event.created_at)}</p>
      </div>
      <div className={isDebit ? "font-black text-rose-200" : "font-black text-lime-300"}>{isDebit ? "-" : "+"}{Math.abs(safeNumber(event.amount)).toLocaleString()}</div>
    </div>
  );
}

function PaymentRow({ payment }: { payment: PaymentEvent }) {
  const symbol = String(payment.currency || "INR").toUpperCase() === "USD" ? "$" : "₹";
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
      <div>
        <p className="font-semibold text-white">{formatReportMoney(payment.amount, symbol)}</p>
        <p className="text-xs text-purple-100/45">{formatDate(payment.created_at)}</p>
      </div>
      <Badge className={statusClassName(payment.status)}>{payment.status || "unknown"}</Badge>
    </div>
  );
}

function BillingCreditsView({ report }: { report: BillingCreditsReport | null }) {
  const billing = report || {
    credit_balance: 0,
    credits_used_this_month: 0,
    credits_added_this_month: 0,
    active_plan: null,
    subscription_status: null,
    recent_credit_events: [],
    recent_payments: [],
  };
  const hasAnyData = billing.credit_balance > 0 || billing.credits_added_this_month > 0 || billing.credits_used_this_month > 0 || Boolean(billing.active_plan) || billing.recent_credit_events.length > 0 || billing.recent_payments.length > 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricBox label="Current Credits" value={formatCount(billing.credit_balance)} tone="lime" />
        <MetricBox label="Used This Month" value={formatCount(billing.credits_used_this_month)} tone="rose" />
        <MetricBox label="Added This Month" value={formatCount(billing.credits_added_this_month)} tone="sky" />
        <MetricBox label="Active Plan" value={billing.active_plan || "No active plan"} />
      </div>

      {!hasAnyData ? (
        <EmptyState title="No billing activity yet" description="Your credit usage, plan status, and payment history will appear here once available." action={<WalletCards className="mx-auto h-8 w-8 text-purple-100/50" />} />
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <GlassCard className="p-6" hoverEffect={false}>
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="workspace-section-title">Recent Credit Events</h2>
                <p className="workspace-muted-text">Credits added and used by your account.</p>
              </div>
              <CreditCard className="h-5 w-5 text-purple-100/60" />
            </div>
            {billing.recent_credit_events.length ? <div className="space-y-3">{billing.recent_credit_events.map((event) => <CreditEventRow key={event.id} event={event} />)}</div> : <p className="text-sm text-purple-100/60">No credit events found.</p>}
          </GlassCard>

          <GlassCard className="p-6" hoverEffect={false}>
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="workspace-section-title">Recent Payments</h2>
                <p className="workspace-muted-text">Latest subscription and top-up payments.</p>
              </div>
              <WalletCards className="h-5 w-5 text-purple-100/60" />
            </div>
            {billing.subscription_status && <Badge className={`${statusClassName(billing.subscription_status)} mb-4`}>Subscription: {billing.subscription_status}</Badge>}
            {billing.recent_payments.length ? <div className="space-y-3">{billing.recent_payments.map((payment) => <PaymentRow key={payment.id} payment={payment} />)}</div> : <p className="text-sm text-purple-100/60">No payments found.</p>}
          </GlassCard>
        </div>
      )}
    </div>
  );
}

export default function ReportsPage() {
  const [data, setData] = useState<UserReportSummaryResponse>(DEFAULT_REPORT_SUMMARY);
  const [activityItems, setActivityItems] = useState<ReportActivityItem[]>([]);
  const [billingReport, setBillingReport] = useState<BillingCreditsReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summary, activity, billing] = await Promise.all([
        reportsApi.getUserReportSummary({ page_size: 10 }),
        reportsApi.getUserReportActivity({ page_size: 20 }),
        reportsApi.getUserBillingCreditsReport({ page_size: 10 }),
      ]);
      setData(summary);
      setActivityItems(activity.items);
      setBillingReport(billing);
    } catch (err) {
      setError(formatErrorMessage(parseApiError(err)));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadReports();
  }, [loadReports]);

  const currencySymbol = data.currency_symbol || data.summary.currency_symbol || "₹";
  const isLiveMode = data.report_mode === "live";
  const performanceCards = useMemo(() => {
    return [...data.performance_cards].sort((a, b) => orderedCards.indexOf(a.key) - orderedCards.indexOf(b.key));
  }, [data.performance_cards]);

  const handleDownload = async (row: RecentReportBacktest, format: "pdf" | "excel") => {
    setDownloading(`${row.id}:${format}`);
    try {
      const blob = await backtestsApi.downloadExport(row.id, format);
      downloadBlob(`backtest-${row.id}.${format === "excel" ? "xlsx" : "pdf"}`, blob);
    } catch (err) {
      setError(formatErrorMessage(parseApiError(err)));
    } finally {
      setDownloading(null);
    }
  };

  return (
    <PageShell>
      <PageHeader
        title="Reports"
        subtitle="Performance summaries, backtest exports, and account insights in one workspace."
        actions={
          <>
            <Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10" onClick={loadReports} disabled={loading}>
              <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
            </Button>
            <Button className="gap-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90" onClick={() => exportRecentBacktestsCsv(data.recent_backtests)} disabled={!data.recent_backtests.length}>
              <FileSpreadsheet className="h-4 w-4" /> Export All CSV
            </Button>
          </>
        }
      />

      {error && (
        <GlassCard className="border-rose-300/20 bg-rose-500/10 p-5" hoverEffect={false}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="whitespace-pre-line text-sm text-rose-100">{error}</p>
            <Button variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10" onClick={loadReports}>Retry</Button>
          </div>
        </GlassCard>
      )}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <GlassCard key={index} className="h-40 animate-pulse bg-white/5 p-5" hoverEffect={false} />
          ))}
        </div>
      ) : (
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="flex h-auto flex-wrap justify-start gap-2 rounded-2xl border border-white/10 bg-white/5 p-2 backdrop-blur-xl">
            <TabsTrigger value="overview" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Overview</TabsTrigger>
            <TabsTrigger value="backtests" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Backtest Reports</TabsTrigger>
            <TabsTrigger value="activity" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Activity</TabsTrigger>
            <TabsTrigger value="billing" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Billing &amp; Credits</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="flex flex-wrap items-center gap-3">
              <Badge className={isLiveMode ? "border-emerald-300/30 bg-emerald-500/15 px-3 py-1 text-emerald-100" : "border-sky-300/30 bg-sky-500/15 px-3 py-1 text-sky-100"}>
                {isLiveMode ? "Live Trading Performance" : "Backtest Research Mode"}
              </Badge>
              {!isLiveMode && (
                <span className="text-sm text-purple-100/65">These numbers are based on completed backtests and are for research purposes, not live account performance.</span>
              )}
            </div>

            {isLiveMode ? (
              <LiveSummaryCards data={data} symbol={currencySymbol} />
            ) : performanceCards.length ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {performanceCards.map((card) => <PerformanceCard key={card.key} card={card} symbol={currencySymbol} />)}
              </div>
            ) : (
              <EmptyState
                title="No reports yet"
                description="Run your first backtest to generate performance reports and exports."
                action={<Button asChild className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"><Link href="/backtest">Run Backtest</Link></Button>}
              />
            )}

            <GlassCard className="p-6" hoverEffect={false}>
              <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="workspace-section-title">{isLiveMode ? "Live Trading Summary" : "Backtest Research Summary"}</h2>
                  <p className="workspace-muted-text">{isLiveMode ? "Real trading overview from connected deployments and positions." : "Year-to-date research overview from completed backtests."}</p>
                </div>
                {isLiveMode ? <ShieldCheck className="h-5 w-5 text-emerald-300" /> : <TrendingUp className="h-5 w-5 text-lime-300" />}
              </div>

              {isLiveMode ? (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricBox label="Total Live P&L" value={formatReportMoney(data.live_summary.total_net_profit, currencySymbol)} tone={safeNumber(data.live_summary.total_net_profit) >= 0 ? "lime" : "rose"} />
                  <MetricBox label="Win Rate" value={formatReportPercent(data.live_summary.win_rate)} tone="sky" />
                  <MetricBox label="Max Drawdown" value={formatReportDrawdown(data.live_summary.max_drawdown, currencySymbol, data.live_summary.max_drawdown_type)} tone="rose" />
                  <MetricBox label="Last Trade" value={formatDate(data.live_summary.last_trade_at)} />
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <MetricBox label="Total P&L YTD" value={formatReportMoney(data.backtest_summary.total_net_profit_ytd, currencySymbol)} tone={safeNumber(data.backtest_summary.total_net_profit_ytd) >= 0 ? "lime" : "rose"} />
                    <MetricBox label="Average Win Rate" value={formatReportPercent(data.backtest_summary.average_win_rate_ytd)} tone="sky" />
                    <MetricBox label="Max Drawdown" value={formatReportDrawdown(data.backtest_summary.max_drawdown_ytd, currencySymbol, data.backtest_summary.max_drawdown_type || "amount")} tone="rose" />
                    <MetricBox label="Total Backtests" value={formatCount(data.backtest_summary.total_backtests_ytd)} />
                  </div>
                  <div className="mt-4 grid gap-4 md:grid-cols-3">
                    <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-100/70">Total Trades</p><p className="mt-1 text-xl font-bold text-white">{formatCount(data.backtest_summary.total_trades_ytd)}</p></div>
                    <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-100/70">Best Strategy</p><p className="mt-1 text-xl font-bold text-white">{data.backtest_summary.best_strategy_name || "—"}</p></div>
                    <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-100/70">Best Instrument</p><p className="mt-1 text-xl font-bold text-white">{data.backtest_summary.best_instrument_symbol || "—"}</p></div>
                  </div>
                </>
              )}
            </GlassCard>
          </TabsContent>

          <TabsContent value="backtests" className="space-y-6">
            <GlassCard className="p-6" hoverEffect={false}>
              <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="workspace-section-title">Recent Backtest Reports</h2>
                  <p className="workspace-muted-text">Research/testing reports. Open detailed reports or download existing PDF and Excel exports.</p>
                </div>
                <Button asChild variant="outline" className="border-white/10 bg-white/5 text-purple-100 hover:bg-white/10"><Link href="/backtest-history">Open History</Link></Button>
              </div>

              {data.recent_backtests.length === 0 ? (
                <EmptyState
                  title="No reports yet"
                  description="Run your first backtest to generate performance reports and exports."
                  action={<Button asChild className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"><Link href="/backtest">Run Backtest</Link></Button>}
                />
              ) : (
                <>
                  <div className="space-y-3 md:hidden">
                    {data.recent_backtests.map((row) => <BacktestMobileCard key={row.id} row={row} onDownload={handleDownload} downloading={downloading} />)}
                  </div>
                  <ResponsiveTableWrapper className="hidden md:block">
                    <table className="min-w-[980px] text-sm">
                      <thead>
                        <tr className="text-left text-purple-100/60">
                          <th className="px-4 py-3 font-medium">Strategy</th>
                          <th className="px-4 py-3 font-medium">Instrument</th>
                          <th className="px-4 py-3 font-medium">Timeframe</th>
                          <th className="px-4 py-3 font-medium">Date</th>
                          <th className="px-4 py-3 font-medium">Net P&amp;L</th>
                          <th className="px-4 py-3 font-medium">Win Rate</th>
                          <th className="px-4 py-3 font-medium">Max DD</th>
                          <th className="px-4 py-3 font-medium">Trades</th>
                          <th className="px-4 py-3 font-medium">Status</th>
                          <th className="px-4 py-3 font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.recent_backtests.map((row) => {
                          const symbol = row.currency_symbol || currencySymbol;
                          const pnl = safeNumber(row.net_profit);
                          return (
                            <tr key={row.id} className="border-t border-white/10 text-purple-100/80">
                              <td className="px-4 py-4 font-medium text-white">{row.strategy_name || "Unknown Strategy"}</td>
                              <td className="px-4 py-4">{row.instrument_symbol || "—"}</td>
                              <td className="px-4 py-4">{row.timeframe || "—"}</td>
                              <td className="px-4 py-4">{formatDate(row.created_at)}</td>
                              <td className={pnl >= 0 ? "px-4 py-4 font-semibold text-lime-300" : "px-4 py-4 font-semibold text-rose-300"}>{formatReportMoney(pnl, symbol)}</td>
                              <td className="px-4 py-4">{formatReportPercent(row.win_rate)}</td>
                              <td className="px-4 py-4 text-rose-200">{formatReportDrawdown(row.max_drawdown, symbol, row.max_drawdown_type || "amount")}</td>
                              <td className="px-4 py-4">{formatCount(row.total_trades)}</td>
                              <td className="px-4 py-4"><Badge className={statusClassName(row.status)}>{row.status || "unknown"}</Badge></td>
                              <td className="px-4 py-4">
                                <div className="flex flex-wrap gap-2">
                                  <Button asChild size="sm" variant="outline" className="border-white/10 bg-white/5 text-purple-100 hover:bg-white/10"><Link href={`/backtest-report/${row.id}`}>View</Link></Button>
                                  <Button size="sm" variant="outline" className="border-white/10 bg-white/5 text-purple-100 hover:bg-white/10" disabled={downloading === `${row.id}:pdf`} onClick={() => handleDownload(row, "pdf")}>PDF</Button>
                                  <Button size="sm" variant="outline" className="border-white/10 bg-white/5 text-purple-100 hover:bg-white/10" disabled={downloading === `${row.id}:excel`} onClick={() => handleDownload(row, "excel")}>Excel</Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </ResponsiveTableWrapper>
                </>
              )}
            </GlassCard>
          </TabsContent>

          <TabsContent value="activity">
            <ActivityList items={activityItems} />
          </TabsContent>

          <TabsContent value="billing">
            <BillingCreditsView report={billingReport} />
          </TabsContent>
        </Tabs>
      )}
    </PageShell>
  );
}
