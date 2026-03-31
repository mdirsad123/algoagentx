"use client"

import { useEffect, useState } from "react"
import { adminApi, Subscription } from "@/lib/api/admin"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { RefreshCw } from "lucide-react"
import { toast } from "sonner"

export default function AdminSubscriptionsPage() {
  const [items, setItems] = useState<Subscription[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState("")
  const [skip, setSkip] = useState(0)
  const [total, setTotal] = useState(0)

  const load = async (nextSkip = skip) => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.getSubscriptions(nextSkip, 20, status || undefined, search || undefined)
      setItems(data.items)
      setTotal(data.total)
      setSkip(nextSkip)
    } catch (e: any) {
      const msg = e?.response?.data?.detail || "Failed to load subscriptions"
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(0) }, [])

  const updateStatus = async (id: string, nextStatus: string) => {
    try {
      await adminApi.updateSubscription(id, { status: nextStatus })
      toast.success("Subscription updated")
      load(skip)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Unable to update subscription")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white">Subscriptions</h1>
          <p className="text-sm text-purple-200">Review and manage user subscriptions.</p>
        </div>
        <Button onClick={() => load(skip)} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl shadow-xl">
        <div className="mb-4 flex flex-wrap gap-3">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by user or plan" className="max-w-sm border-white/10 bg-white/5 text-white placeholder:text-purple-200/70" />
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-white">
            <option value="">All statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="TRIALING">TRIALING</option>
            <option value="CANCELED">CANCELED</option>
            <option value="EXPIRED">EXPIRED</option>
          </select>
          <Button onClick={() => load(0)} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">Apply</Button>
        </div>

        {error ? <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 p-5 text-rose-200">{error}</div> : (
          <div className="overflow-auto rounded-2xl border border-white/10 bg-slate-950/30">
            <table className="w-full min-w-[980px] text-sm text-white">
              <thead>
                <tr className="border-b border-white/10 text-left text-purple-200">
                  <th className="px-3 py-3">User</th>
                  <th className="px-3 py-3">Plan</th>
                  <th className="px-3 py-3">Period</th>
                  <th className="px-3 py-3">Amount</th>
                  <th className="px-3 py-3">Credits</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Start</th>
                  <th className="px-3 py-3">End</th>
                  <th className="px-3 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? <tr><td className="px-3 py-8 text-purple-200" colSpan={9}>Loading subscriptions...</td></tr> : items.length === 0 ? <tr><td className="px-3 py-8 text-center text-purple-200" colSpan={9}>No subscriptions found</td></tr> : items.map((item) => (
                  <tr key={item.id} className="border-b border-white/5">
                    <td className="px-3 py-3"><div>{item.user_name || item.user_email || '—'}</div><div className="text-xs text-purple-200">{item.user_email || ''}</div></td>
                    <td className="px-3 py-3"><span className="rounded-full bg-purple-500/20 px-3 py-1 text-xs uppercase text-purple-200">{item.plan_code || item.plan || 'free'}</span></td>
                    <td className="px-3 py-3">{item.billing_period}</td>
                    <td className="px-3 py-3">₹{item.price_inr || item.amount || 0}</td>
                    <td className="px-3 py-3">{item.included_credits}</td>
                    <td className="px-3 py-3"><Badge className="bg-white/10 text-white">{item.status}</Badge></td>
                    <td className="px-3 py-3">{new Date(item.start_at || item.start_date || '').toLocaleDateString()}</td>
                    <td className="px-3 py-3">{new Date(item.end_at || item.end_date || '').toLocaleDateString()}</td>
                    <td className="px-3 py-3">
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={() => updateStatus(item.id, "CANCELED")}>Cancel</Button>
                        <Button size="sm" className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white" onClick={() => updateStatus(item.id, "ACTIVE")}>Activate</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between text-sm text-purple-200">
          <div>Showing {items.length} of {total}</div>
          <div className="flex gap-2">
            <Button disabled={skip === 0} onClick={() => load(Math.max(0, skip - 20))} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10">Previous</Button>
            <Button disabled={skip + 20 >= total} onClick={() => load(skip + 20)} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10">Next</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
