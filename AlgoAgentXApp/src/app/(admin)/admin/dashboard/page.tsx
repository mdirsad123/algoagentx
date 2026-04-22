"use client"

import { useEffect, useState } from "react"
import { adminApi, AdminMetrics } from "@/lib/api/admin"
import { Button } from "@/components/ui/button"
import { RefreshCw, Users, UserCheck, IndianRupee, Coins, CreditCard, Clock3, BarChart3, Briefcase } from "lucide-react"

function MetricCard({ label, value, icon }: { label: string; value: string | number; icon: React.ReactNode }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl backdrop-blur-xl">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-purple-200">{label}</div>
          <div className="mt-3 text-3xl font-semibold text-white">{value}</div>
        </div>
        <div className="rounded-2xl bg-fuchsia-500/15 p-3 text-fuchsia-200">{icon}</div>
      </div>
    </div>
  )
}

function SimpleTable({ title, rows, columns }: { title: string; rows: any[]; columns: { key: string; label: string; render?: (row: any) => React.ReactNode }[] }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl backdrop-blur-xl">
      <div className="mb-4 text-lg font-semibold text-white">{title}</div>
      <div className="overflow-auto">
        <table className="w-full min-w-[520px] text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-purple-200">
              {columns.map((col) => <th key={col.key} className="px-3 py-3 font-medium">{col.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td className="px-3 py-8 text-center text-purple-200" colSpan={columns.length}>No data found</td></tr>
            ) : rows.map((row, idx) => (
              <tr key={idx} className="border-b border-white/5 text-white/90">
                {columns.map((col) => <td key={col.key} className="px-3 py-3">{col.render ? col.render(row) : row[col.key]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function AdminDashboardPage() {
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      setLoading(true)
      setError(null)
      setMetrics(await adminApi.getMetrics())
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load admin metrics")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return <div className="text-white">Loading dashboard...</div>
  if (error && !metrics) return <div className="rounded-3xl border border-rose-400/20 bg-rose-500/10 p-6 text-rose-200">{error}</div>

  const safeMetrics = metrics || {}
  const users = safeMetrics.users || { total: 0, active: 0, recent: [] as any[] }
  const payments = safeMetrics.payments || { total: 0, revenue: 0, recent: [] as any[] }
  const credits = safeMetrics.credits || { total: 0, active_subscriptions: 0 }
  const subscriptions = safeMetrics.subscriptions || { total: 0, active: 0 }
  const strategies = safeMetrics.strategies || { pending: 0 }
  const backtests = safeMetrics.backtests || { total: 0 }
  const orders = safeMetrics.orders || { total: 0, recent: [] as any[] }

  const revenue = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(payments.revenue || 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white">Admin Dashboard</h1>
          <p className="mt-1 text-sm text-purple-200">Live SaaS metrics and recent business activity.</p>
        </div>
        <Button onClick={load} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
      </div>

      {!!error && <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-amber-100 text-sm">Partial data warning: {error}</div>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total Users" value={users.total} icon={<Users className="h-5 w-5" />} />
        <MetricCard label="Active Users" value={users.active} icon={<UserCheck className="h-5 w-5" />} />
        <MetricCard label="Total Revenue" value={revenue} icon={<IndianRupee className="h-5 w-5" />} />
        <MetricCard label="Total Credits Issued" value={credits.total} icon={<Coins className="h-5 w-5" />} />
        <MetricCard label="Active Subscriptions" value={subscriptions.active} icon={<CreditCard className="h-5 w-5" />} />
        <MetricCard label="Pending Strategy Requests" value={strategies.pending || 0} icon={<Clock3 className="h-5 w-5" />} />
        <MetricCard label="Total Backtests" value={backtests.total || 0} icon={<BarChart3 className="h-5 w-5" />} />
        <MetricCard label="Orders" value={orders.total || 0} icon={<Briefcase className="h-5 w-5" />} />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <SimpleTable title="Recent Users" rows={users.recent || []} columns={[
          { key: "user", label: "User", render: (row) => <div><div>{row.fullname || row.email}</div><div className="text-xs text-purple-200">{row.email}</div></div> },
          { key: "role", label: "Role" },
          { key: "created_at", label: "Joined", render: (row) => new Date(row.created_at).toLocaleDateString() },
        ]} />
        <SimpleTable title="Recent Payments" rows={payments.recent || []} columns={[
          { key: "user", label: "User", render: (row) => <div><div>{row.user_name || row.user_email || "—"}</div><div className="text-xs text-purple-200">{row.user_email || ""}</div></div> },
          { key: "amount", label: "Amount", render: (row) => `₹${row.amount}` },
          { key: "status", label: "Status" },
        ]} />
        <SimpleTable title="Recent Orders" rows={orders.recent || []} columns={[
          { key: "user", label: "User", render: (row) => <div><div>{row.user_name || row.user_email || "—"}</div><div className="text-xs text-purple-200">{row.order_number}</div></div> },
          { key: "total_amount", label: "Amount", render: (row) => `₹${row.total_amount}` },
          { key: "status", label: "Status" },
        ]} />
      </div>
    </div>
  )
}
