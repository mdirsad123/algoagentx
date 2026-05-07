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
  const PAGE_SIZE = 20

  const load = async (nextSkip = skip) => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.getSubscriptions(nextSkip, PAGE_SIZE, status || undefined, search || undefined)
      setItems(data.items || [])
      setTotal(data.total || 0)
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
          <h1 className="text-foreground text-2xl font-semibold tracking-tight">Subscriptions</h1>
          <p className="text-muted-foreground text-sm">Inspect plan lifecycle, included credits, and refill windows.</p>
        </div>
        <Button onClick={() => load(skip)} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/30 p-4 shadow-xl backdrop-blur-xl">
        <div className="mb-4 flex flex-wrap gap-3">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by user, plan, or status" className="max-w-sm bg-card/20 border-border/50 text-foreground placeholder:text-muted-foreground" />
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm text-foreground">
            <option value="">All statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="TRIALING">TRIALING</option>
            <option value="CANCELED">CANCELED</option>
            <option value="EXPIRED">EXPIRED</option>
          </select>
          <Button onClick={() => load(0)} className="rounded-xl">Apply</Button>
        </div>

        {error ? <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-rose-200">{error}</div> : (
          <div className="overflow-auto rounded-xl border border-border/50 bg-card/20">
            <table className="w-full min-w-[1240px] text-sm">
              <thead>
                <tr className="border-b border-border/60 text-left text-muted-foreground">
                  <th className="px-3 py-3">User</th>
                  <th className="px-3 py-3">Plan</th>
                  <th className="px-3 py-3">Period</th>
                  <th className="px-3 py-3">Paid Amount</th>
                  <th className="px-3 py-3">Coupon</th>
                  <th className="px-3 py-3">Source Order</th>
                  <th className="px-3 py-3">Included Credits</th>
                  <th className="px-3 py-3">Remaining</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Renews</th>
                  <th className="px-3 py-3">Next Refill</th>
                  <th className="px-3 py-3">Start</th>
                  <th className="px-3 py-3">End</th>
                  <th className="px-3 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? <tr><td className="px-3 py-8 text-muted-foreground" colSpan={14}>Loading subscriptions...</td></tr> : items.length === 0 ? <tr><td className="px-3 py-8 text-center text-muted-foreground" colSpan={14}>No data found</td></tr> : items.map((item) => (
                  <tr key={item.id} className="border-b border-border/30 hover:bg-card/50 transition-colors">
                    <td className="px-3 py-3"><div className="text-foreground">{item.user_name || item.user_email || '—'}</div><div className="text-xs text-muted-foreground">{item.user_email || ''}</div></td>
                    <td className="px-3 py-3"><span className="rounded-full border border-border/60 bg-card/50 px-2 py-1 text-xs uppercase text-foreground">{item.plan_code || 'free'}</span></td>
                    <td className="px-3 py-3 text-foreground">{item.billing_period}</td>
                    <td className="px-3 py-3 text-foreground font-medium">{(item as any).paid_currency === "USD" ? `$${Number((item as any).paid_amount || (item as any).final_usd || 0).toFixed(2)}` : `₹${Number((item as any).paid_amount || item.price_inr || 0).toLocaleString("en-IN")}`}</td>
                    <td className="px-3 py-3 text-foreground">{(item as any).coupon_code ? <span className="rounded-full bg-emerald-500/15 px-2 py-1 text-xs text-emerald-200">{(item as any).coupon_code} · -${Number((item as any).discount_usd || 0).toFixed(2)}</span> : "—"}</td>
                    <td className="px-3 py-3 font-mono text-xs text-muted-foreground">{(item as any).source_order_id || (item as any).source_payment_id || "—"}</td>
                    <td className="px-3 py-3 text-foreground">{item.included_credits_total ?? item.included_credits ?? 0}</td>
                    <td className="px-3 py-3 text-foreground">{item.included_credits_remaining ?? 0}</td>
                    <td className="px-3 py-3"><Badge className="bg-card/60 text-foreground border border-border/60">{item.status}</Badge></td>
                    <td className="px-3 py-3 text-foreground">{item.renews ? "Yes" : "No"}</td>
                    <td className="px-3 py-3 text-muted-foreground">{item.next_credit_refill_at ? new Date(item.next_credit_refill_at).toLocaleString() : "—"}</td>
                    <td className="px-3 py-3 text-muted-foreground">{item.start_at ? new Date(item.start_at).toLocaleDateString() : '—'}</td>
                    <td className="px-3 py-3 text-muted-foreground">{item.end_at ? new Date(item.end_at).toLocaleDateString() : '—'}</td>
                    <td className="px-3 py-3">
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40" onClick={() => updateStatus(item.id, "CANCELED")}>Cancel</Button>
                        <Button size="sm" className="rounded-xl" onClick={() => updateStatus(item.id, "ACTIVE")}>Activate</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <div>Showing {items.length} of {total}</div>
          <div className="flex gap-2">
            <Button disabled={skip === 0} onClick={() => load(Math.max(0, skip - PAGE_SIZE))} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">Previous</Button>
            <Button disabled={skip + PAGE_SIZE >= total} onClick={() => load(skip + PAGE_SIZE)} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">Next</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
