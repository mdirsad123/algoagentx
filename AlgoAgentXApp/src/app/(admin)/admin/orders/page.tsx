"use client"

import { useEffect, useState } from "react"
import { adminApi, Order } from "@/lib/api/admin"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { RefreshCw, Eye, RotateCcw } from "lucide-react"
import { toast } from "sonner"

export default function AdminOrdersPage() {
  const [items, setItems] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState("")
  const [sourceType, setSourceType] = useState("")
  const [method, setMethod] = useState("")
  const [search, setSearch] = useState("")
  const [fromDate, setFromDate] = useState("")
  const [toDate, setToDate] = useState("")
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [selected, setSelected] = useState<any>(null)

  const load = async (nextPage = page) => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.getOrders(
        nextPage,
        pageSize,
        status || undefined,
        search || undefined,
        sourceType || undefined,
        method || undefined,
        fromDate ? new Date(fromDate).toISOString() : undefined,
        toDate ? new Date(toDate).toISOString() : undefined,
      )
      setItems(data.items || [])
      setTotal(data.total || 0)
      setPage(nextPage)
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load orders")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(1) }, [])

  const openDetails = async (id: string) => {
    try { setSelected(await adminApi.getOrder(id)) } catch (e: any) { toast.error(e?.response?.data?.detail || "Unable to load order") }
  }
  const updateStatus = async (id: string, nextStatus: string) => {
    try { await adminApi.updateOrderStatus(id, nextStatus); toast.success("Order status updated"); load(page) } catch (e: any) { toast.error(e?.response?.data?.detail || "Unable to update order") }
  }

  const clearFilters = () => {
    setStatus("")
    setSourceType("")
    setMethod("")
    setSearch("")
    setFromDate("")
    setToDate("")
    load(1)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-foreground text-2xl font-semibold tracking-tight">Orders</h1>
          <p className="text-muted-foreground text-sm">Review order source, linked payment state, and reconciliation trail.</p>
        </div>
        <Button onClick={() => load(page)} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/30 p-4 shadow-xl backdrop-blur-xl">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search user / order / payment" className="bg-card/20 border-border/50 text-foreground placeholder:text-muted-foreground" />
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm text-foreground">
            <option value="">All statuses</option>
            <option value="CREATED">CREATED</option>
            <option value="PAID">PAID</option>
            <option value="FAILED">FAILED</option>
            <option value="REFUNDED">REFUNDED</option>
          </select>
          <select value={sourceType} onChange={(e) => setSourceType(e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm text-foreground">
            <option value="">All source types</option>
            <option value="CREDITS_TOPUP">CREDITS_TOPUP</option>
            <option value="SUBSCRIPTION">SUBSCRIPTION</option>
          </select>
          <select value={method} onChange={(e) => setMethod(e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm text-foreground">
            <option value="">All methods</option>
            <option value="RAZORPAY">RAZORPAY</option>
          </select>
          <Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="bg-card/20 border-border/50 text-foreground" />
          <Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="bg-card/20 border-border/50 text-foreground" />
        </div>

        <div className="mt-3 flex gap-2">
          <Button onClick={() => load(1)} className="rounded-xl">Apply Filters</Button>
          <Button onClick={clearFilters} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"><RotateCcw className="mr-2 h-4 w-4" />Reset</Button>
        </div>
      </div>

      {error ? <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-rose-200">{error}</div> : (
        <div className="overflow-auto rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
            <table className="w-full min-w-[1250px] text-sm">
              <thead>
                <tr className="border-b border-border/60 text-left text-muted-foreground">
                  <th className="px-3 py-3">User</th>
                  <th className="px-3 py-3">Order</th>
                  <th className="px-3 py-3">Source Type</th>
                  <th className="px-3 py-3">Amount</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Linked Payment</th>
                  <th className="px-3 py-3">Reconciliation</th>
                  <th className="px-3 py-3">Method</th>
                  <th className="px-3 py-3">Created At</th>
                  <th className="px-3 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? <tr><td className="px-3 py-8 text-muted-foreground" colSpan={10}>Loading orders...</td></tr> : items.length === 0 ? <tr><td className="px-3 py-8 text-center text-muted-foreground" colSpan={10}>No data found</td></tr> : items.map((item) => (
                  <tr key={item.id} className="border-b border-border/30 hover:bg-card/50 transition-colors">
                    <td className="px-3 py-3"><div className="text-foreground">{item.user_name || item.user_email || '—'}</div><div className="text-xs text-muted-foreground">{item.user_email || ''}</div></td>
                    <td className="px-3 py-3 font-mono text-xs text-muted-foreground">{item.order_number}</td>
                    <td className="px-3 py-3 text-foreground">{item.source_type || item.order_type || '—'}</td>
                    <td className="px-3 py-3 text-foreground font-medium">₹{item.total_amount}</td>
                    <td className="px-3 py-3"><span className="rounded-full border border-border/60 bg-card/50 px-2 py-1 text-xs text-foreground">{item.status}</span></td>
                    <td className="px-3 py-3 font-mono text-xs text-muted-foreground">{item.linked_payment_id || '—'} ({item.linked_payment_status || item.status})</td>
                    <td className="px-3 py-3">
                      <span className={`rounded-full px-2 py-1 text-xs ${(item.reconciliation_status || '').toLowerCase() === 'reconciled' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-amber-500/15 text-amber-300'}`}>
                        {item.reconciliation_status || 'pending'}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-foreground">{item.payment_method}</td>
                    <td className="px-3 py-3 text-muted-foreground">{new Date(item.created_at).toLocaleString()}</td>
                    <td className="px-3 py-3">
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40" onClick={() => openDetails(item.id)}><Eye className="mr-2 h-4 w-4" />View</Button>
                        <select value={item.status} onChange={(e) => updateStatus(item.id, e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-xs text-foreground"><option value="CREATED">CREATED</option><option value="PAID">PAID</option><option value="FAILED">FAILED</option><option value="REFUNDED">REFUNDED</option></select>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
      )}

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <div>Showing {items.length} of {total}</div>
        <div className="flex gap-2">
          <Button disabled={page <= 1} onClick={() => load(page - 1)} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">Previous</Button>
          <Button disabled={page * pageSize >= total} onClick={() => load(page + 1)} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">Next</Button>
        </div>
      </div>

      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="rounded-xl border border-border/60 bg-card/95 text-foreground">
          <DialogHeader><DialogTitle>Order details</DialogTitle></DialogHeader>
          {selected && <div className="space-y-2 text-sm">
            <div><span className="text-muted-foreground">User:</span> {selected.user_name || selected.user_email || '—'}</div>
            <div><span className="text-muted-foreground">Order Number:</span> {selected.order_number}</div>
            <div><span className="text-muted-foreground">Source:</span> {selected.source_type || selected.order_type || '—'}</div>
            <div><span className="text-muted-foreground">Amount:</span> ₹{selected.total_amount}</div>
            <div><span className="text-muted-foreground">Status:</span> {selected.status}</div>
            <div><span className="text-muted-foreground">Method:</span> {selected.payment_method}</div>
            <div><span className="text-muted-foreground">Linked Payment:</span> {selected.linked_payment_id || '—'} ({selected.linked_payment_status || selected.status})</div>
            <div><span className="text-muted-foreground">Reconciliation:</span> {selected.reconciliation?.status || selected.reconciliation_status || 'pending'}</div>
            <div><span className="text-muted-foreground">Created:</span> {new Date(selected.created_at).toLocaleString()}</div>
          </div>}
          <DialogFooter><Button variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40" onClick={() => setSelected(null)}>Close</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
