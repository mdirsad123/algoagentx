"use client"

import { useEffect, useState } from "react"
import { adminApi, Payment } from "@/lib/api/admin"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { RefreshCw, Eye } from "lucide-react"
import { toast } from "sonner"

export default function AdminPaymentsPage() {
  const [items, setItems] = useState<Payment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState("")
  const [search, setSearch] = useState("")
  const [skip, setSkip] = useState(0)
  const [total, setTotal] = useState(0)
  const [selected, setSelected] = useState<Payment | null>(null)

  const load = async (nextSkip = skip) => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.getPayments(nextSkip, 20, status || undefined, search || undefined)
      setItems(data.items)
      setTotal(data.total)
      setSkip(nextSkip)
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load payments")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(0) }, [])

  const openDetails = async (id: string) => {
    try {
      setSelected(await adminApi.getPayment(id))
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Unable to load payment details")
    }
  }

  const refund = async (id: string) => {
    try {
      await adminApi.refundPayment(id)
      toast.success("Payment marked refunded")
      load(skip)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Unable to refund payment")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white">Payments</h1>
          <p className="text-sm text-purple-200">Track successful, pending, and refunded payment activity.</p>
        </div>
        <Button onClick={() => load(skip)} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl shadow-xl">
        <div className="mb-4 flex flex-wrap gap-3">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by user, order id, transaction id" className="max-w-sm border-white/10 bg-white/5 text-white placeholder:text-purple-200/70" />
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-white">
            <option value="">All statuses</option>
            <option value="PAID">PAID</option>
            <option value="CREATED">CREATED</option>
            <option value="FAILED">FAILED</option>
            <option value="REFUNDED">REFUNDED</option>
          </select>
          <Button onClick={() => load(0)} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">Apply</Button>
        </div>

        {error ? <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 p-5 text-rose-200">{error}</div> : (
          <div className="overflow-auto rounded-2xl border border-white/10 bg-slate-950/30">
            <table className="w-full min-w-[1100px] text-sm text-white">
              <thead>
                <tr className="border-b border-white/10 text-left text-purple-200">
                  <th className="px-3 py-3">User</th>
                  <th className="px-3 py-3">Payment ID</th>
                  <th className="px-3 py-3">Amount</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Method</th>
                  <th className="px-3 py-3">Transaction</th>
                  <th className="px-3 py-3">Date</th>
                  <th className="px-3 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? <tr><td className="px-3 py-8 text-purple-200" colSpan={8}>Loading payments...</td></tr> : items.length === 0 ? <tr><td className="px-3 py-8 text-center text-purple-200" colSpan={8}>No payments found</td></tr> : items.map((item) => (
                  <tr key={item.id} className="border-b border-white/5">
                    <td className="px-3 py-3"><div>{item.user_name || item.user_email || '—'}</div><div className="text-xs text-purple-200">{item.user_email || ''}</div></td>
                    <td className="px-3 py-3 font-mono text-xs">{item.id}</td>
                    <td className="px-3 py-3">₹{item.amount}</td>
                    <td className="px-3 py-3"><span className="rounded-full bg-white/10 px-3 py-1 text-xs">{item.status}</span></td>
                    <td className="px-3 py-3">{item.payment_method}</td>
                    <td className="px-3 py-3 font-mono text-xs">{item.transaction_id || item.razorpay_payment_id || '—'}</td>
                    <td className="px-3 py-3">{new Date(item.created_at).toLocaleString()}</td>
                    <td className="px-3 py-3">
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={() => openDetails(item.id)}><Eye className="mr-2 h-4 w-4" />View</Button>
                        {item.status !== 'REFUNDED' && <Button size="sm" className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white" onClick={() => refund(item.id)}>Refund</Button>}
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

      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="border-purple-400/20 bg-gradient-to-br from-purple-950 to-slate-950 text-white">
          <DialogHeader><DialogTitle>Payment details</DialogTitle></DialogHeader>
          {selected && <div className="space-y-2 text-sm">
            <div><span className="text-purple-200">User:</span> {selected.user_name || selected.user_email || '—'}</div>
            <div><span className="text-purple-200">Amount:</span> ₹{selected.amount}</div>
            <div><span className="text-purple-200">Status:</span> {selected.status}</div>
            <div><span className="text-purple-200">Method:</span> {selected.payment_method}</div>
            <div><span className="text-purple-200">Order ID:</span> {selected.razorpay_order_id || '—'}</div>
            <div><span className="text-purple-200">Transaction ID:</span> {selected.transaction_id || selected.razorpay_payment_id || '—'}</div>
            <div><span className="text-purple-200">Created:</span> {new Date(selected.created_at).toLocaleString()}</div>
          </div>}
          <DialogFooter><Button className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white" onClick={() => setSelected(null)}>Close</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
