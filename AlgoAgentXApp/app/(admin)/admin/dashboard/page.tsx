"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"
import { adminApi, AdminDashboardSummary } from "@/lib/api/admin"
import { Button } from "@/components/ui/button"
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Briefcase,
  CheckCircle2,
  Clock3,
  Coins,
  CreditCard,
  Database,
  IndianRupee,
  Loader2,
  RefreshCw,
  Rocket,
  Server,
  ShieldCheck,
  TrendingUp,
  UserCheck,
  Users,
  Wifi,
  XCircle,
} from "lucide-react"

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })
const numberFmt = new Intl.NumberFormat("en-IN")

const emptySummary: AdminDashboardSummary = {
  users: { total_users: 0, active_users: 0, admin_users: 0, new_users_today: 0, new_users_7d: 0 },
  billing: {
    total_revenue: 0,
    paid_revenue: 0,
    refunded_amount: 0,
    failed_amount: 0,
    total_orders: 0,
    paid_orders: 0,
    failed_orders: 0,
    refunded_orders: 0,
    active_subscriptions: 0,
    expired_subscriptions: 0,
    total_credits_issued: 0,
    total_credits_used: 0,
  },
  strategies: {
    total_strategies: 0,
    published_strategies: 0,
    private_strategies: 0,
    pending_strategy_requests: 0,
    approved_strategy_requests: 0,
    rejected_strategy_requests: 0,
  },
  backtests: { total_backtests: 0, completed_backtests: 0, failed_backtests: 0, running_backtests: 0, backtests_today: 0, backtests_7d: 0 },
  brokers: { total_broker_accounts: 0, connected_broker_accounts: 0, failed_broker_accounts: 0, broker_breakdown: [] },
  live_trading: {
    total_deployments: 0,
    running_deployments: 0,
    paused_deployments: 0,
    stopped_deployments: 0,
    live_sync_enabled_users: 0,
    approval_required_users: 0,
    orders_today: 0,
    orders_total: 0,
    successful_orders: 0,
    failed_orders: 0,
    open_positions: 0,
  },
  system: { market_data_symbols: 0, market_data_rows: 0, last_market_data_sync: null, latest_execution_log_at: null, api_health: "unknown" },
  recent: {
    recent_users: [],
    recent_payments: [],
    recent_orders: [],
    recent_backtests: [],
    recent_live_deployments: [],
    recent_broker_connections: [],
    recent_strategy_requests: [],
  },
}

function formatDate(value?: string | null) {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })
}

function formatNumber(value: number | string | null | undefined) {
  const num = Number(value || 0)
  return numberFmt.format(Number.isFinite(num) ? num : 0)
}

function StatusPill({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "good" | "bad" | "warn" | "neutral" }) {
  const toneClass = {
    good: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
    bad: "border-rose-400/30 bg-rose-400/10 text-rose-200",
    warn: "border-amber-400/30 bg-amber-400/10 text-amber-200",
    neutral: "border-white/15 bg-white/10 text-purple-100",
  }[tone]
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClass}`}>{children}</span>
}

function MetricCard({ title, value, detail, icon, tone = "purple" }: { title: string; value: React.ReactNode; detail?: React.ReactNode; icon: React.ReactNode; tone?: "purple" | "green" | "blue" | "orange" | "rose" }) {
  const toneClass = {
    purple: "from-fuchsia-500/25 to-purple-500/10 text-fuchsia-100",
    green: "from-emerald-500/25 to-teal-500/10 text-emerald-100",
    blue: "from-sky-500/25 to-indigo-500/10 text-sky-100",
    orange: "from-orange-500/25 to-amber-500/10 text-orange-100",
    rose: "from-rose-500/25 to-pink-500/10 text-rose-100",
  }[tone]

  return (
    <div className="group rounded-3xl border border-white/10 bg-white/[0.07] p-5 shadow-xl shadow-purple-950/10 backdrop-blur-xl transition hover:-translate-y-0.5 hover:bg-white/[0.1]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-[0.22em] text-purple-200/80">{title}</div>
          <div className="mt-3 text-3xl font-black text-white">{value}</div>
          {detail && <div className="mt-2 text-xs font-medium text-purple-100/75">{detail}</div>}
        </div>
        <div className={`rounded-2xl bg-gradient-to-br p-3 shadow-lg ${toneClass}`}>{icon}</div>
      </div>
    </div>
  )
}

function SectionCard({ title, subtitle, children, action }: { title: string; subtitle?: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.07] p-5 shadow-xl backdrop-blur-xl">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-black text-white">{title}</h3>
          {subtitle && <p className="mt-1 text-xs font-medium text-purple-100/75">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </div>
  )
}

function MiniBar({ label, value, total, tone = "bg-fuchsia-400" }: { label: string; value: number; total: number; tone?: string }) {
  const pct = total > 0 ? Math.min(100, Math.round((value / total) * 100)) : 0
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-purple-100">
        <span>{label}</span>
        <span className="font-bold text-white">{formatNumber(value)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function SimpleTable({ title, rows, columns, empty, href }: { title: string; rows: any[]; columns: { key: string; label: string; render?: (row: any) => React.ReactNode }[]; empty: string; href?: string }) {
  return (
    <SectionCard title={title} action={href ? <Button asChild size="sm" variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10"><Link href={href}>Open</Link></Button> : null}>
      <div className="admin-table-scroll overflow-auto">
        <table className="admin-data-table w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-purple-200">
              {columns.map((col) => <th key={col.key} className="px-3 py-3 text-xs font-bold uppercase tracking-wider">{col.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td className="px-3 py-8 text-center text-purple-100/70" colSpan={columns.length}>{empty}</td></tr>
            ) : rows.map((row, index) => (
              <tr key={row.id || index} className="border-b border-white/5 text-white/90">
                {columns.map((col) => <td key={col.key} className="px-3 py-3 align-top">{col.render ? col.render(row) : row[col.key] ?? "—"}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  )
}

function QuickAction({ title, subtitle, href, icon }: { title: string; subtitle: string; href: string; icon: React.ReactNode }) {
  return (
    <Link href={href} className="group rounded-3xl border border-white/10 bg-white/[0.07] p-4 shadow-lg backdrop-blur-xl transition hover:-translate-y-0.5 hover:bg-white/[0.1]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="font-black text-white">{title}</div>
          <div className="mt-1 text-xs text-purple-100/70">{subtitle}</div>
        </div>
        <div className="rounded-2xl bg-fuchsia-500/20 p-3 text-fuchsia-100 transition group-hover:bg-fuchsia-500/30">{icon}</div>
      </div>
    </Link>
  )
}

export default function AdminDashboardPage() {
  const [summary, setSummary] = useState<AdminDashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  const load = async (soft = false) => {
    try {
      soft ? setRefreshing(true) : setLoading(true)
      setError(null)
      const data = await adminApi.getDashboardSummary()
      setSummary(data)
      setLastUpdated(new Date().toISOString())
    } catch (e: any) {
      setError(e?.message || e?.response?.data?.detail || "Failed to load admin dashboard summary")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { load() }, [])

  const data = summary || emptySummary
  const orderStatusTotal = Math.max(data.billing.total_orders, 1)
  const backtestTotal = Math.max(data.backtests.total_backtests, 1)
  const brokerTotal = Math.max(data.brokers.total_broker_accounts, 1)
  const deploymentTotal = Math.max(data.live_trading.total_deployments, 1)

  const apiHealthTone = data.system.api_health === "ok" ? "good" : "warn"

  const kpis = useMemo(() => ({
    business: [
      { title: "Total Users", value: formatNumber(data.users.total_users), detail: `${formatNumber(data.users.new_users_7d)} new in 7 days`, icon: <Users className="h-5 w-5" />, tone: "purple" as const },
      { title: "Active Users", value: formatNumber(data.users.active_users), detail: `${formatNumber(data.users.admin_users)} admins`, icon: <UserCheck className="h-5 w-5" />, tone: "green" as const },
      { title: "Total Revenue", value: currency.format(Number(data.billing.total_revenue || 0)), detail: `${currency.format(Number(data.billing.refunded_amount || 0))} refunded`, icon: <IndianRupee className="h-5 w-5" />, tone: "green" as const },
      { title: "Active Subscriptions", value: formatNumber(data.billing.active_subscriptions), detail: `${formatNumber(data.billing.expired_subscriptions)} expired/cancelled`, icon: <CreditCard className="h-5 w-5" />, tone: "blue" as const },
      { title: "Total Orders", value: formatNumber(data.billing.total_orders), detail: `${formatNumber(data.billing.paid_orders)} paid / ${formatNumber(data.billing.failed_orders)} failed`, icon: <Briefcase className="h-5 w-5" />, tone: "orange" as const },
      { title: "Credits Issued", value: formatNumber(data.billing.total_credits_issued), detail: `${formatNumber(data.billing.total_credits_used)} used`, icon: <Coins className="h-5 w-5" />, tone: "purple" as const },
    ],
    trading: [
      { title: "Total Backtests", value: formatNumber(data.backtests.total_backtests), detail: `${formatNumber(data.backtests.backtests_today)} today`, icon: <BarChart3 className="h-5 w-5" />, tone: "blue" as const },
      { title: "Backtests 7D", value: formatNumber(data.backtests.backtests_7d), detail: `${formatNumber(data.backtests.completed_backtests)} completed`, icon: <TrendingUp className="h-5 w-5" />, tone: "green" as const },
      { title: "Total Strategies", value: formatNumber(data.strategies.total_strategies), detail: `${formatNumber(data.strategies.published_strategies)} public`, icon: <ShieldCheck className="h-5 w-5" />, tone: "purple" as const },
      { title: "Pending Requests", value: formatNumber(data.strategies.pending_strategy_requests), detail: `${formatNumber(data.strategies.rejected_strategy_requests)} rejected`, icon: <Clock3 className="h-5 w-5" />, tone: "orange" as const },
      { title: "Broker Accounts", value: formatNumber(data.brokers.total_broker_accounts), detail: `${formatNumber(data.brokers.connected_broker_accounts)} connected`, icon: <Wifi className="h-5 w-5" />, tone: "blue" as const },
      { title: "Connected Brokers", value: formatNumber(data.brokers.connected_broker_accounts), detail: `${formatNumber(data.brokers.failed_broker_accounts)} disconnected/failed`, icon: <CheckCircle2 className="h-5 w-5" />, tone: "green" as const },
    ],
    live: [
      { title: "Deployments", value: formatNumber(data.live_trading.total_deployments), detail: `${formatNumber(data.live_trading.running_deployments)} running`, icon: <Rocket className="h-5 w-5" />, tone: "purple" as const },
      { title: "Paused", value: formatNumber(data.live_trading.paused_deployments), detail: `${formatNumber(data.live_trading.stopped_deployments)} stopped/draft`, icon: <Clock3 className="h-5 w-5" />, tone: "orange" as const },
      { title: "Orders Today", value: formatNumber(data.live_trading.orders_today), detail: `${formatNumber(data.live_trading.orders_total)} total`, icon: <Activity className="h-5 w-5" />, tone: "blue" as const },
      { title: "Successful Orders", value: formatNumber(data.live_trading.successful_orders), detail: `${formatNumber(data.live_trading.failed_orders)} failed`, icon: <CheckCircle2 className="h-5 w-5" />, tone: "green" as const },
      { title: "Failed Orders", value: formatNumber(data.live_trading.failed_orders), detail: "Broker/API failures", icon: <XCircle className="h-5 w-5" />, tone: "rose" as const },
      { title: "Open Positions", value: formatNumber(data.live_trading.open_positions), detail: `${formatNumber(data.live_trading.live_sync_enabled_users)} sync-enabled users`, icon: <Activity className="h-5 w-5" />, tone: "green" as const },
    ],
    system: [
      { title: "Market Symbols", value: formatNumber(data.system.market_data_symbols), detail: "Distinct symbols/instruments", icon: <Database className="h-5 w-5" />, tone: "blue" as const },
      { title: "Market Rows", value: formatNumber(data.system.market_data_rows), detail: "Historical/live rows", icon: <BarChart3 className="h-5 w-5" />, tone: "purple" as const },
      { title: "Last Market Sync", value: formatDate(data.system.last_market_data_sync), detail: "Latest candle timestamp", icon: <RefreshCw className="h-5 w-5" />, tone: "green" as const },
      { title: "Latest Exec Log", value: formatDate(data.system.latest_execution_log_at), detail: "Live trade log heartbeat", icon: <Server className="h-5 w-5" />, tone: "orange" as const },
    ],
  }), [data])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-28 animate-pulse rounded-3xl bg-white/10" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-32 animate-pulse rounded-3xl bg-white/10" />)}</div>
      </div>
    )
  }

  if (error && !summary) {
    return (
      <div className="rounded-3xl border border-rose-400/25 bg-rose-500/10 p-8 text-rose-100 shadow-xl backdrop-blur-xl">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-1 h-5 w-5" />
          <div>
            <h2 className="text-xl font-black">Admin dashboard could not load</h2>
            <p className="mt-2 text-sm text-rose-100/80">{error}</p>
            <Button onClick={() => load()} className="mt-5 bg-rose-500 text-white hover:bg-rose-600">Retry</Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-purple-500/25 via-fuchsia-500/10 to-emerald-500/10 p-6 shadow-2xl shadow-purple-950/20 backdrop-blur-xl">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex rounded-full border border-emerald-300/20 bg-emerald-400/10 px-3 py-1 text-xs font-bold text-emerald-100">Admin command center</div>
            <h1 className="text-3xl font-black text-white md:text-4xl">Admin Dashboard</h1>
            <p className="mt-2 max-w-3xl text-sm font-medium text-purple-100/80">SaaS, billing, trading, broker and system operations in one real-data workspace.</p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <StatusPill tone={apiHealthTone}>API {data.system.api_health?.toUpperCase?.() || "UNKNOWN"}</StatusPill>
              <StatusPill tone={data.live_trading.approval_required_users > 0 ? "warn" : "good"}>{formatNumber(data.live_trading.approval_required_users)} users need approval</StatusPill>
              <StatusPill tone="neutral">Updated {formatDate(lastUpdated || data.generated_at || null)}</StatusPill>
            </div>
          </div>
          <Button onClick={() => load(true)} disabled={refreshing} variant="outline" className="border-white/15 bg-white/10 text-white hover:bg-white/15">
            {refreshing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />} Refresh
          </Button>
        </div>
      </div>

      {!!error && <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-100">Partial data warning: {error}</div>}

      <section className="space-y-4">
        <h2 className="text-xl font-black text-white">SaaS Business</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{kpis.business.map((card) => <MetricCard key={card.title} {...card} />)}</div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-black text-white">Trading Usage</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{kpis.trading.map((card) => <MetricCard key={card.title} {...card} />)}</div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-black text-white">Live Trading Operations</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{kpis.live.map((card) => <MetricCard key={card.title} {...card} />)}</div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-black text-white">System Health</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">{kpis.system.map((card) => <MetricCard key={card.title} {...card} />)}</div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-4">
        <SectionCard title="Orders by Status" subtitle="Billing order health">
          <div className="space-y-4">
            <MiniBar label="Paid" value={data.billing.paid_orders} total={orderStatusTotal} tone="bg-emerald-400" />
            <MiniBar label="Failed" value={data.billing.failed_orders} total={orderStatusTotal} tone="bg-rose-400" />
            <MiniBar label="Refunded" value={data.billing.refunded_orders} total={orderStatusTotal} tone="bg-amber-400" />
          </div>
        </SectionCard>
        <SectionCard title="Backtests" subtitle="Completed vs failed">
          <div className="space-y-4">
            <MiniBar label="Completed" value={data.backtests.completed_backtests} total={backtestTotal} tone="bg-emerald-400" />
            <MiniBar label="Failed" value={data.backtests.failed_backtests} total={backtestTotal} tone="bg-rose-400" />
            <MiniBar label="Running" value={data.backtests.running_backtests} total={backtestTotal} tone="bg-sky-400" />
          </div>
        </SectionCard>
        <SectionCard title="Broker Status" subtitle="Connected vs failed">
          <div className="space-y-4">
            <MiniBar label="Connected" value={data.brokers.connected_broker_accounts} total={brokerTotal} tone="bg-emerald-400" />
            <MiniBar label="Failed/Disconnected" value={data.brokers.failed_broker_accounts} total={brokerTotal} tone="bg-rose-400" />
            <div className="pt-1 text-xs text-purple-100/70">{data.brokers.broker_breakdown?.length ? data.brokers.broker_breakdown.map((b: any) => `${b.broker}: ${b.connected}/${b.total}`).join(" • ") : "No broker accounts yet"}</div>
          </div>
        </SectionCard>
        <SectionCard title="Deployment Status" subtitle="Live strategy operations">
          <div className="space-y-4">
            <MiniBar label="Running" value={data.live_trading.running_deployments} total={deploymentTotal} tone="bg-emerald-400" />
            <MiniBar label="Paused" value={data.live_trading.paused_deployments} total={deploymentTotal} tone="bg-amber-400" />
            <MiniBar label="Stopped/Draft" value={data.live_trading.stopped_deployments} total={deploymentTotal} tone="bg-rose-400" />
          </div>
        </SectionCard>
      </div>

      <section className="space-y-4">
        <h2 className="text-xl font-black text-white">Admin Quick Actions</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <QuickAction title="Manage Users" subtitle="Accounts and roles" href="/admin/users" icon={<Users className="h-5 w-5" />} />
          <QuickAction title="Manage Pricing" subtitle="Plans and credits" href="/admin/pricing" icon={<CreditCard className="h-5 w-5" />} />
          <QuickAction title="View Orders" subtitle="Billing orders" href="/admin/orders" icon={<Briefcase className="h-5 w-5" />} />
          <QuickAction title="View Payments" subtitle="Payment history" href="/admin/payments" icon={<IndianRupee className="h-5 w-5" />} />
          <QuickAction title="Strategy Requests" subtitle="Approve workflow" href="/admin/strategy-requests" icon={<Clock3 className="h-5 w-5" />} />
          <QuickAction title="Manage Strategies" subtitle="IDE and publishing" href="/admin/strategies" icon={<ShieldCheck className="h-5 w-5" />} />
          <QuickAction title="Broker Accounts" subtitle="User broker health" href="/admin/brokers" icon={<Wifi className="h-5 w-5" />} />
          <QuickAction title="Live Trading Admin" subtitle="Deployments/orders" href="/admin/live-trading" icon={<Rocket className="h-5 w-5" />} />
          <QuickAction title="Live Settings" subtitle="Global controls" href="/admin/live-settings" icon={<Server className="h-5 w-5" />} />
          <QuickAction title="Market Data" subtitle="Candles and imports" href="/admin/market-data" icon={<Database className="h-5 w-5" />} />
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <SimpleTable title="Recent Users" rows={data.recent.recent_users || []} href="/admin/users" empty="No users found" columns={[
          { key: "user", label: "User", render: (row) => <div><div className="font-bold">{row.fullname || row.email || "—"}</div><div className="text-xs text-purple-200">{row.email || ""}</div></div> },
          { key: "role", label: "Role", render: (row) => <StatusPill tone={String(row.role).toLowerCase() === "admin" ? "warn" : "neutral"}>{row.role || "user"}</StatusPill> },
          { key: "created_at", label: "Joined", render: (row) => formatDate(row.created_at) },
        ]} />
        <SimpleTable title="Recent Payments" rows={data.recent.recent_payments || []} href="/admin/payments" empty="No payments found" columns={[
          { key: "user", label: "User", render: (row) => <div><div className="font-bold">{row.user_name || row.user_email || "—"}</div><div className="text-xs text-purple-200">{row.user_email || ""}</div></div> },
          { key: "amount", label: "Amount", render: (row) => currency.format(Number(row.amount || row.amount_inr || 0)) },
          { key: "status", label: "Status", render: (row) => <StatusPill tone={String(row.status).toLowerCase().includes("paid") || String(row.status).toLowerCase().includes("success") ? "good" : String(row.status).toLowerCase().includes("fail") ? "bad" : "neutral"}>{row.status || "—"}</StatusPill> },
        ]} />
        <SimpleTable title="Recent Live Orders" rows={data.recent.recent_orders || []} href="/admin/live-trading" empty="No live orders yet" columns={[
          { key: "user", label: "User", render: (row) => <div><div className="font-bold">{row.user_name || row.user_email || "—"}</div><div className="text-xs text-purple-200">{row.symbol || ""}</div></div> },
          { key: "side", label: "Side/Qty", render: (row) => `${row.side || "—"} ${row.qty || ""}` },
          { key: "status", label: "Status", render: (row) => <StatusPill tone={String(row.status).toLowerCase().includes("fail") ? "bad" : "neutral"}>{row.status || "—"}</StatusPill> },
        ]} />
        <SimpleTable title="Recent Backtests" rows={data.recent.recent_backtests || []} href="/admin/backtests" empty="No backtests found" columns={[
          { key: "strategy", label: "Strategy", render: (row) => <div><div className="font-bold">{row.strategy_name || row.strategy_id || "—"}</div><div className="text-xs text-purple-200">{row.user_email || ""}</div></div> },
          { key: "return_pct", label: "Return", render: (row) => `${Number(row.return_pct || 0).toFixed(2)}%` },
          { key: "created_at", label: "Created", render: (row) => formatDate(row.created_at) },
        ]} />
        <SimpleTable title="Recent Live Deployments" rows={data.recent.recent_live_deployments || []} href="/admin/live-trading" empty="No deployments yet" columns={[
          { key: "name", label: "Deployment", render: (row) => <div><div className="font-bold">{row.name || "—"}</div><div className="text-xs text-purple-200">{row.instrument || ""} • {row.timeframe || ""}</div></div> },
          { key: "user", label: "User", render: (row) => row.user_email || "—" },
          { key: "status", label: "Status", render: (row) => <StatusPill tone={String(row.status).toLowerCase() === "running" ? "good" : "neutral"}>{row.status || "—"}</StatusPill> },
        ]} />
        <SimpleTable title="Recent Broker Connections" rows={data.recent.recent_broker_connections || []} href="/admin/brokers" empty="No broker connections yet" columns={[
          { key: "broker", label: "Broker", render: (row) => <div><div className="font-bold">{row.broker_name || "—"}</div><div className="text-xs text-purple-200">{row.account_label || row.user_email || ""}</div></div> },
          { key: "mode", label: "Mode", render: (row) => row.mode || "—" },
          { key: "status", label: "Status", render: (row) => <StatusPill tone={String(row.status).toLowerCase() === "connected" ? "good" : "warn"}>{row.status || "—"}</StatusPill> },
        ]} />
        <SimpleTable title="Recent Strategy Requests" rows={data.recent.recent_strategy_requests || []} href="/admin/strategy-requests" empty="No strategy requests yet" columns={[
          { key: "title", label: "Request", render: (row) => <div><div className="font-bold">{row.title || "—"}</div><div className="text-xs text-purple-200">{row.market || ""} {row.timeframe ? `• ${row.timeframe}` : ""}</div></div> },
          { key: "user", label: "User", render: (row) => row.user_email || "—" },
          { key: "status", label: "Status", render: (row) => <StatusPill tone={String(row.status).toLowerCase().includes("reject") ? "bad" : String(row.status).toLowerCase().includes("pending") ? "warn" : "neutral"}>{row.status || "—"}</StatusPill> },
        ]} />
      </div>
    </div>
  )
}
