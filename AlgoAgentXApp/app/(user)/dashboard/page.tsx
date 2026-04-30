"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bot,
  Briefcase,
  CircleDollarSign,
  Clock,
  CreditCard,
  FileText,
  History,
  PlayCircle,
  PlugZap,
  RefreshCw,
  Rocket,
  ShieldCheck,
  TrendingUp,
  Wallet,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { useUser } from "@/contexts/user-context";
import { apiGet } from "@/lib/axios";

interface BrokerAccountItem {
  id: string;
  broker_name: string;
  account_label: string;
  mode: string;
  status: string;
  last_sync_at: string | null;
}

interface RecentBacktestItem {
  id: string;
  strategy_name: string;
  timeframe: string;
  status: string;
  return_pct: number;
  net_profit: number;
  total_trades: number;
  created_at: string | null;
}

interface RecentOrderItem {
  id: string;
  symbol: string;
  side: string;
  qty: number;
  price: number;
  status: string;
  created_at: string | null;
}

interface RecentSignalItem {
  id: string;
  symbol: string;
  signal: string;
  price: number;
  confidence: number;
  status: string;
  reason?: string | null;
  created_at: string | null;
}

interface RecentBrokerLogItem {
  id: string;
  event_type: string;
  level: string;
  message: string;
  created_at: string | null;
}

interface DashboardSummary {
  generated_at?: string;
  portfolio: {
    total_broker_accounts: number;
    connected_brokers: number;
    active_broker_accounts: number;
    accounts?: BrokerAccountItem[];
  };
  strategies: {
    total_strategies: number;
    my_strategies: number;
    published_strategies: number;
    deployed_strategies: number;
    running_strategies: number;
    paused_strategies: number;
  };
  backtests: {
    total_backtests: number;
    completed_backtests: number;
    failed_backtests: number;
    best_return_pct: number;
    best_strategy_name: string | null;
    last_backtest_at: string | null;
  };
  live_trading: {
    total_deployments: number;
    running_deployments: number;
    paused_deployments: number;
    live_sync_enabled: boolean;
    approval_required: boolean;
    open_positions: number;
    today_orders: number;
    today_pnl: number;
    total_pnl: number;
  };
  billing: {
    credit_balance: number;
    active_subscription: boolean;
    subscription_plan: string | null;
  };
  recent: {
    recent_signals: RecentSignalItem[];
    recent_backtests: RecentBacktestItem[];
    recent_orders: RecentOrderItem[];
    recent_broker_logs: RecentBrokerLogItem[];
  };
}

const emptySummary: DashboardSummary = {
  portfolio: {
    total_broker_accounts: 0,
    connected_brokers: 0,
    active_broker_accounts: 0,
    accounts: [],
  },
  strategies: {
    total_strategies: 0,
    my_strategies: 0,
    published_strategies: 0,
    deployed_strategies: 0,
    running_strategies: 0,
    paused_strategies: 0,
  },
  backtests: {
    total_backtests: 0,
    completed_backtests: 0,
    failed_backtests: 0,
    best_return_pct: 0,
    best_strategy_name: null,
    last_backtest_at: null,
  },
  live_trading: {
    total_deployments: 0,
    running_deployments: 0,
    paused_deployments: 0,
    live_sync_enabled: false,
    approval_required: true,
    open_positions: 0,
    today_orders: 0,
    today_pnl: 0,
    total_pnl: 0,
  },
  billing: {
    credit_balance: 0,
    active_subscription: false,
    subscription_plan: null,
  },
  recent: {
    recent_signals: [],
    recent_backtests: [],
    recent_orders: [],
    recent_broker_logs: [],
  },
};

const numberFormatter = new Intl.NumberFormat("en-IN");
const percentFormatter = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 0,
});
const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

function formatNumber(value?: number | null) {
  return numberFormatter.format(Number(value || 0));
}

function formatPercent(value?: number | null) {
  const numeric = Number(value || 0);
  return `${numeric > 0 ? "+" : ""}${percentFormatter.format(numeric)}%`;
}

function formatMoney(value?: number | null) {
  const numeric = Number(value || 0);
  return `${numeric > 0 ? "+" : ""}${currencyFormatter.format(numeric)}`;
}

function formatDate(value?: string | null) {
  if (!value) return "No data yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "No data yet";
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusBadgeClass(status?: string) {
  const normalized = String(status || "").toUpperCase();
  if (["CONNECTED", "ACTIVE", "RUNNING", "COMPLETED", "SUCCESS", "APPROVED", "READY"].includes(normalized)) {
    return "border-emerald-400/40 bg-emerald-500/15 text-emerald-200";
  }
  if (["PAUSED", "PENDING", "RECEIVED", "DRAFT"].includes(normalized)) {
    return "border-amber-400/40 bg-amber-500/15 text-amber-200";
  }
  if (["FAILED", "ERROR", "DISCONNECTED", "REJECTED", "CANCELLED"].includes(normalized)) {
    return "border-rose-400/40 bg-rose-500/15 text-rose-200";
  }
  return "border-white/20 bg-white/10 text-purple-100";
}

function KpiCard({
  label,
  value,
  helper,
  icon: Icon,
  tone = "purple",
}: {
  label: string;
  value: React.ReactNode;
  helper: string;
  icon: React.ElementType;
  tone?: "purple" | "green" | "blue" | "amber" | "pink";
}) {
  const toneMap = {
    purple: "from-purple-500 to-fuchsia-500 shadow-purple-500/25",
    green: "from-emerald-500 to-green-500 shadow-emerald-500/25",
    blue: "from-blue-500 to-cyan-500 shadow-blue-500/25",
    amber: "from-amber-500 to-orange-500 shadow-amber-500/25",
    pink: "from-pink-500 to-rose-500 shadow-pink-500/25",
  };

  return (
    <GlassCard className="col-span-12 sm:col-span-6 xl:col-span-3" depth={2}>
      <div className="flex h-full items-start justify-between gap-4 p-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-purple-100/80">{label}</p>
          <div className="mt-3 text-3xl font-black tracking-tight text-white">{value}</div>
          <p className="mt-2 text-sm font-medium text-purple-100/75">{helper}</p>
        </div>
        <div className={`rounded-2xl bg-gradient-to-br p-3 text-white shadow-xl ${toneMap[tone]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </GlassCard>
  );
}

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-5">
      <h2 className="text-xl font-black tracking-tight text-white md:text-2xl">{title}</h2>
      {subtitle ? <p className="mt-1 text-sm font-medium text-purple-100/75">{subtitle}</p> : null}
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.06] px-4 py-3">
      <span className="text-sm font-semibold text-purple-100/75">{label}</span>
      <span className="text-sm font-black text-white">{value}</span>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-dashed border-white/20 bg-white/[0.04] p-5 text-center text-sm font-semibold text-purple-100/70">
      {message}
    </div>
  );
}

function ActionCard({ href, title, subtitle, icon: Icon }: { href: string; title: string; subtitle: string; icon: React.ElementType }) {
  return (
    <Link
      href={href}
      className="group rounded-2xl border border-white/15 bg-white/[0.07] p-5 transition-all duration-300 hover:-translate-y-1 hover:border-purple-300/50 hover:bg-white/[0.10] hover:shadow-2xl hover:shadow-purple-950/30"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-black text-white transition-colors group-hover:text-purple-100">{title}</h3>
          <p className="mt-1 text-sm font-medium text-purple-100/70">{subtitle}</p>
        </div>
        <div className="rounded-2xl bg-gradient-to-br from-purple-500 to-fuchsia-500 p-3 text-white shadow-lg shadow-purple-500/25 transition-transform group-hover:scale-110">
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </Link>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-40 animate-pulse rounded-3xl border border-white/10 bg-white/[0.07]" />
      <div className="grid grid-cols-12 gap-5">
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className="col-span-12 h-32 animate-pulse rounded-2xl border border-white/10 bg-white/[0.07] sm:col-span-6 xl:col-span-3" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="h-80 animate-pulse rounded-3xl border border-white/10 bg-white/[0.07]" />
        <div className="h-80 animate-pulse rounded-3xl border border-white/10 bg-white/[0.07]" />
      </div>
    </div>
  );
}

export default function UserDashboardPage() {
  const { user } = useUser();
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const displayName = useMemo(() => {
    const raw = user?.displayName || user?.fullname || user?.username || user?.email || "Trader";
    return raw.includes("@") ? raw.split("@")[0] : raw;
  }, [user]);

  const fetchSummary = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiGet<DashboardSummary>("/api/v1/dashboard/user-summary");
      setSummary({ ...emptySummary, ...data, recent: { ...emptySummary.recent, ...(data?.recent || {}) } });
    } catch (err: any) {
      setSummary(emptySummary);
      setError(err?.message || "Dashboard summary could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const connectedBrokerText = `${formatNumber(summary.portfolio.connected_brokers)} connected broker${summary.portfolio.connected_brokers === 1 ? "" : "s"}`;
  const pnlPositive = Number(summary.live_trading.today_pnl || 0) >= 0;

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Manage your trading workspace" />

      {loading ? (
        <DashboardSkeleton />
      ) : error ? (
        <GlassCard depth={2}>
          <div className="flex flex-col items-start gap-4 p-6 md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-4">
              <div className="rounded-2xl bg-rose-500/20 p-3 text-rose-200">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-xl font-black text-white">Unable to load dashboard</h2>
                <p className="mt-1 text-sm font-medium text-purple-100/75">{error}</p>
              </div>
            </div>
            <Button onClick={fetchSummary} className="bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white hover:opacity-90">
              <RefreshCw className="mr-2 h-4 w-4" /> Retry
            </Button>
          </div>
        </GlassCard>
      ) : (
        <div className="space-y-6">
          <GlassCard className="overflow-hidden" depth={3}>
            <div className="relative p-6 md:p-8">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(168,85,247,0.28),transparent_28%),radial-gradient(circle_at_85%_10%,rgba(16,185,129,0.20),transparent_30%)]" />
              <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <Badge className="mb-4 border-emerald-400/30 bg-emerald-500/15 text-emerald-100">
                    Real data workspace
                  </Badge>
                  <h1 className="text-3xl font-black tracking-tight text-white md:text-4xl">Welcome back, {displayName}</h1>
                  <p className="mt-2 max-w-2xl text-base font-medium text-purple-100/80">
                    Monitor brokers, deployments, backtests, credits, and recent trading activity from one user workspace.
                  </p>
                </div>

                <div className="grid min-w-full grid-cols-1 gap-3 sm:grid-cols-3 lg:min-w-[520px]">
                  <div className="rounded-2xl border border-white/15 bg-white/[0.08] p-4">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-purple-100/70">
                      <Zap className="h-4 w-4" /> Live Sync
                    </div>
                    <p className={`mt-2 text-lg font-black ${summary.live_trading.live_sync_enabled ? "text-emerald-300" : "text-amber-200"}`}>
                      {summary.live_trading.live_sync_enabled ? "ON" : "OFF"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/15 bg-white/[0.08] p-4">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-purple-100/70">
                      <ShieldCheck className="h-4 w-4" /> Execution
                    </div>
                    <p className="mt-2 text-lg font-black text-white">
                      {summary.live_trading.approval_required ? "Approval Required" : "Approved"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/15 bg-white/[0.08] p-4">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-purple-100/70">
                      <PlugZap className="h-4 w-4" /> Brokers
                    </div>
                    <p className="mt-2 text-lg font-black text-white">{connectedBrokerText}</p>
                  </div>
                </div>
              </div>
            </div>
          </GlassCard>

          <div className="grid grid-cols-12 gap-5">
            <KpiCard label="Connected Brokers" value={formatNumber(summary.portfolio.connected_brokers)} helper={`${formatNumber(summary.portfolio.total_broker_accounts)} total accounts`} icon={PlugZap} tone="green" />
            <KpiCard label="Total Strategies" value={formatNumber(summary.strategies.total_strategies)} helper={`${formatNumber(summary.strategies.my_strategies)} custom / ${formatNumber(summary.strategies.published_strategies)} published`} icon={Bot} tone="purple" />
            <KpiCard label="Deployed Strategies" value={formatNumber(summary.strategies.deployed_strategies)} helper="Linked to live/paper execution" icon={Rocket} tone="blue" />
            <KpiCard label="Running Strategies" value={formatNumber(summary.strategies.running_strategies)} helper={`${formatNumber(summary.strategies.paused_strategies)} paused`} icon={Activity} tone="green" />
            <KpiCard label="Total Backtests" value={formatNumber(summary.backtests.total_backtests)} helper={`${formatNumber(summary.backtests.completed_backtests)} completed / ${formatNumber(summary.backtests.failed_backtests)} failed`} icon={BarChart3} tone="blue" />
            <KpiCard label="Best Return" value={formatPercent(summary.backtests.best_return_pct)} helper={summary.backtests.best_strategy_name || "No best strategy yet"} icon={TrendingUp} tone="green" />
            <KpiCard label="Today P&L" value={<span className={pnlPositive ? "text-emerald-300" : "text-rose-300"}>{formatMoney(summary.live_trading.today_pnl)}</span>} helper={`Total P&L ${formatMoney(summary.live_trading.total_pnl)}`} icon={CircleDollarSign} tone={pnlPositive ? "green" : "pink"} />
            <KpiCard label="Credit Balance" value={formatNumber(summary.billing.credit_balance)} helper={summary.billing.active_subscription ? `${summary.billing.subscription_plan || "Active"} subscription` : "No active subscription"} icon={Wallet} tone="amber" />
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <GlassCard depth={2}>
              <div className="p-6">
                <SectionTitle title="Live Trading Status" subtitle="Execution controls and live workspace health" />
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <MetricRow label="Running deployments" value={formatNumber(summary.live_trading.running_deployments)} />
                  <MetricRow label="Paused deployments" value={formatNumber(summary.live_trading.paused_deployments)} />
                  <MetricRow label="Open positions" value={formatNumber(summary.live_trading.open_positions)} />
                  <MetricRow label="Today orders" value={formatNumber(summary.live_trading.today_orders)} />
                  <MetricRow label="Live sync" value={summary.live_trading.live_sync_enabled ? "Enabled" : "Disabled"} />
                  <MetricRow label="Approval mode" value={summary.live_trading.approval_required ? "Required" : "Approved"} />
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <Button asChild className="bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white hover:opacity-90">
                    <Link href="/live-trading"><PlayCircle className="mr-2 h-4 w-4" /> Go to Live Trading</Link>
                  </Button>
                  <Button asChild variant="outline" className="border-white/20 bg-white/[0.07] text-white hover:bg-white/[0.12]">
                    <Link href="/live-trading">Manage Live Settings</Link>
                  </Button>
                  <Button asChild variant="outline" className="border-white/20 bg-white/[0.07] text-white hover:bg-white/[0.12]">
                    <Link href="/live-trading">View Execution Logs</Link>
                  </Button>
                </div>
              </div>
            </GlassCard>

            <GlassCard depth={2}>
              <div className="p-6">
                <SectionTitle title="Backtest Performance" subtitle="Real backtest summary from your account" />
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <MetricRow label="Total backtests" value={formatNumber(summary.backtests.total_backtests)} />
                  <MetricRow label="Completed" value={formatNumber(summary.backtests.completed_backtests)} />
                  <MetricRow label="Failed" value={formatNumber(summary.backtests.failed_backtests)} />
                  <MetricRow label="Best return" value={formatPercent(summary.backtests.best_return_pct)} />
                  <MetricRow label="Best strategy" value={summary.backtests.best_strategy_name || "No data yet"} />
                  <MetricRow label="Last backtest" value={formatDate(summary.backtests.last_backtest_at)} />
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <Button asChild className="bg-gradient-to-r from-emerald-500 to-green-500 text-white hover:opacity-90">
                    <Link href="/backtest"><BarChart3 className="mr-2 h-4 w-4" /> Run Backtest</Link>
                  </Button>
                  <Button asChild variant="outline" className="border-white/20 bg-white/[0.07] text-white hover:bg-white/[0.12]">
                    <Link href="/backtest-history"><History className="mr-2 h-4 w-4" /> View Backtest History</Link>
                  </Button>
                </div>
              </div>
            </GlassCard>
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <GlassCard depth={2}>
              <div className="p-6">
                <SectionTitle title="Broker Accounts" subtitle="Connected and configured brokers for your login" />
                <div className="space-y-3">
                  {(summary.portfolio.accounts || []).length === 0 ? (
                    <EmptyState message="No broker connected yet. Add MT5, Upstox, or paper account from Brokers." />
                  ) : (
                    (summary.portfolio.accounts || []).map((account) => (
                      <div key={account.id} className="flex flex-col gap-3 rounded-2xl border border-white/12 bg-white/[0.06] p-4 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="text-base font-black text-white">{account.broker_name} · {account.account_label}</p>
                          <p className="mt-1 text-sm font-medium text-purple-100/70">{account.mode} • Last sync: {formatDate(account.last_sync_at)}</p>
                        </div>
                        <Badge className={statusBadgeClass(account.status)}>{account.status}</Badge>
                      </div>
                    ))
                  )}
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <Button asChild className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white hover:opacity-90">
                    <Link href="/brokers"><PlugZap className="mr-2 h-4 w-4" /> Add Broker</Link>
                  </Button>
                  <Button asChild variant="outline" className="border-white/20 bg-white/[0.07] text-white hover:bg-white/[0.12]">
                    <Link href="/brokers">Manage Brokers</Link>
                  </Button>
                </div>
              </div>
            </GlassCard>

            <GlassCard depth={2}>
              <div className="p-6">
                <SectionTitle title="Strategy Workspace" subtitle="Your templates, published strategies, and deployments" />
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <MetricRow label="My strategies" value={formatNumber(summary.strategies.my_strategies)} />
                  <MetricRow label="Published strategies" value={formatNumber(summary.strategies.published_strategies)} />
                  <MetricRow label="Deployed strategies" value={formatNumber(summary.strategies.deployed_strategies)} />
                  <MetricRow label="Running strategies" value={formatNumber(summary.strategies.running_strategies)} />
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <Button asChild className="bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white hover:opacity-90">
                    <Link href="/strategies"><Bot className="mr-2 h-4 w-4" /> View Strategies</Link>
                  </Button>
                  <Button asChild variant="outline" className="border-white/20 bg-white/[0.07] text-white hover:bg-white/[0.12]">
                    <Link href="/strategies">Request Strategy</Link>
                  </Button>
                </div>
              </div>
            </GlassCard>
          </div>

          <GlassCard depth={2}>
            <div className="p-6">
              <SectionTitle title="Recent Activity" subtitle="Latest backtests, orders, signals, and broker logs from your account" />
              <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                <div>
                  <h3 className="mb-3 flex items-center gap-2 text-sm font-black uppercase tracking-wide text-purple-100/80"><BarChart3 className="h-4 w-4" /> Recent Backtests</h3>
                  <div className="space-y-3">
                    {summary.recent.recent_backtests.length === 0 ? <EmptyState message="No backtests yet." /> : summary.recent.recent_backtests.map((item) => (
                      <div key={item.id} className="rounded-2xl border border-white/12 bg-white/[0.06] p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-black text-white">{item.strategy_name}</p>
                            <p className="text-xs font-semibold text-purple-100/65">{item.timeframe} • {formatDate(item.created_at)}</p>
                          </div>
                          <Badge className={statusBadgeClass(item.status)}>{item.status}</Badge>
                        </div>
                        <div className="mt-3 flex items-center justify-between text-sm font-bold text-purple-100/80">
                          <span>Return {formatPercent(item.return_pct)}</span>
                          <span>{formatNumber(item.total_trades)} trades</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="mb-3 flex items-center gap-2 text-sm font-black uppercase tracking-wide text-purple-100/80"><Briefcase className="h-4 w-4" /> Recent Orders</h3>
                  <div className="space-y-3">
                    {summary.recent.recent_orders.length === 0 ? <EmptyState message="No live orders yet." /> : summary.recent.recent_orders.map((item) => (
                      <div key={item.id} className="rounded-2xl border border-white/12 bg-white/[0.06] p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-black text-white">{item.symbol} · {item.side}</p>
                            <p className="text-xs font-semibold text-purple-100/65">Qty {formatNumber(item.qty)} • {formatMoney(item.price)}</p>
                          </div>
                          <Badge className={statusBadgeClass(item.status)}>{item.status}</Badge>
                        </div>
                        <p className="mt-2 text-xs font-semibold text-purple-100/65">{formatDate(item.created_at)}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="mb-3 flex items-center gap-2 text-sm font-black uppercase tracking-wide text-purple-100/80"><Activity className="h-4 w-4" /> Signals & Logs</h3>
                  <div className="space-y-3">
                    {summary.recent.recent_signals.length === 0 && summary.recent.recent_broker_logs.length === 0 ? <EmptyState message="No recent signals or logs." /> : null}
                    {summary.recent.recent_signals.map((item) => (
                      <div key={item.id} className="rounded-2xl border border-white/12 bg-white/[0.06] p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-black text-white">{item.symbol} · {item.signal}</p>
                            <p className="text-xs font-semibold text-purple-100/65">{formatMoney(item.price)} • Confidence {formatPercent(item.confidence)}</p>
                          </div>
                          <Badge className={statusBadgeClass(item.status)}>{item.status}</Badge>
                        </div>
                        <p className="mt-2 text-xs font-semibold text-purple-100/65">{formatDate(item.created_at)}</p>
                      </div>
                    ))}
                    {summary.recent.recent_signals.length === 0 ? summary.recent.recent_broker_logs.slice(0, 3).map((item) => (
                      <div key={item.id} className="rounded-2xl border border-white/12 bg-white/[0.06] p-4">
                        <div className="flex items-start justify-between gap-3">
                          <p className="font-black text-white">{item.event_type}</p>
                          <Badge className={statusBadgeClass(item.level)}>{item.level}</Badge>
                        </div>
                        <p className="mt-2 text-sm font-medium text-purple-100/75">{item.message}</p>
                        <p className="mt-2 text-xs font-semibold text-purple-100/65">{formatDate(item.created_at)}</p>
                      </div>
                    )) : null}
                  </div>
                </div>
              </div>
            </div>
          </GlassCard>

          <GlassCard depth={2}>
            <div className="p-6">
              <SectionTitle title="Quick Actions" subtitle="Continue your trading workflow" />
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                <ActionCard href="/brokers" title="Connect Broker" subtitle="Add or test broker accounts" icon={PlugZap} />
                <ActionCard href="/backtest" title="Run Backtest" subtitle="Validate strategy performance" icon={BarChart3} />
                <ActionCard href="/live-trading" title="Deploy Strategy" subtitle="Manage live/paper deployments" icon={Rocket} />
                <ActionCard href="/reports" title="View Reports" subtitle="Open analytics and summaries" icon={FileText} />
                <ActionCard href="/pricing" title="Buy Credits / Pricing" subtitle="Upgrade plan or recharge credits" icon={CreditCard} />
                <ActionCard href="/support-tickets" title="Support Ticket" subtitle="Ask support for help" icon={Clock} />
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </>
  );
}
