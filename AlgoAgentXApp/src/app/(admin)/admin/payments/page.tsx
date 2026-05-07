"use client"

import { useEffect, useState } from "react"
import { adminApi, Payment } from "@/lib/api/admin"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Eye, RefreshCw, RotateCcw } from "lucide-react"
import { toast } from "sonner"

const formatPaymentAmount = (amount: number, currency?: string) => {
  const cur = currency || "INR";
  if (cur === "USD") return `$${Number(amount || 0).toFixed(2)}`;
  return `₹${Number(amount || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

const PAGE_SIZE = 20

export default function AdminPaymentsPage() {
  const [items, setItems] = useState<Payment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [skip, setSkip] = useState(0)
  const [total, setTotal] = useState(0)
  const [selected, setSelected] = useState<Payment | null>(null)

  const [search, setSearch] = useState("")
  const [status, setStatus] = useState("")
  const [method, setMethod] = useState("")
  const [purpose, setPurpose] = useState("")
  const [fromDate, setFromDate] = useState("")
  const [toDate, setToDate] = useState("")

  const load = async (nextSkip = skip) => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.getPayments(
        nextSkip,
        PAGE_SIZE,
        status || undefined,
        search || undefined,
        method || undefined,
        purpose || undefined,
        fromDate ? new Date(fromDate).toISOString() : undefined,
        toDate ? new Date(toDate).toISOString() : undefined,
      )
      setItems(data.items || [])
      setTotal(data.total || 0)
      setSkip(nextSkip)
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load payments")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load(0)
  }, [])

  const openDetails = async (id: string) => {
    try {
      setSelected(await adminApi.getPayment(id))
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Unable to load payment details")
    }
  }

  const refund = async (id: string) => {
    const note = window.prompt("Refund note (optional):") || undefined
    try {
      await adminApi.refundPayment(id, note)
      toast.success("Payment marked refunded")
      await load(skip)
      if (selected?.id === id) {
        await openDetails(id)
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Unable to refund payment")
    }
  }

  const clearFilters = () => {
    setSearch("")
    setStatus("")
    setMethod("")
    setPurpose("")
    setFromDate("")
    setToDate("")
    load(0)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-foreground text-2xl font-semibold tracking-tight">Payments</h1>
          <p className="text-muted-foreground text-sm">Monitor payment lifecycle, gateway reconciliation, and refunds.</p>
        </div>
        <Button onClick={() => load(skip)} variant="outline" className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/30 p-4 shadow-xl backdrop-blur-xl">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search user / order / payment" className="bg-card/20 border-border/50 text-foreground placeholder:text-muted-foreground" />

          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm text-foreground">
            <option value="">All status</option>
            <option value="CREATED">CREATED</option>
            <option value="PAID">PAID</option>
            <option value="FAILED">FAILED</option>
            <option value="REFUNDED">REFUNDED</option>
          </select>

          <select value={method} onChange={(e) => setMethod(e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm text-foreground">
            <option value="">All methods</option>
            <option value="RAZORPAY">RAZORPAY</option>
          </select>

          <select value={purpose} onChange={(e) => setPurpose(e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm text-foreground">
            <option value="">All source types</option>
            <option value="CREDIT_TOPUP">CREDIT_TOPUP</option>
            <option value="CREDITS_TOPUP">CREDITS_TOPUP</option>
            <option value="SUBSCRIPTION">SUBSCRIPTION</option>
          </select>

          <Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="bg-card/20 border-border/50 text-foreground" />
          <Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="bg-card/20 border-border/50 text-foreground" />
        </div>

        <div className="mt-3 flex gap-2">
          <Button onClick={() => load(0)} className="rounded-xl">Apply Filters</Button>
          <Button onClick={clearFilters} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">
            <RotateCcw className="mr-2 h-4 w-4" />
            Reset
          </Button>
        </div>
      </div>

      <div className="overflow-auto rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <table className="w-full min-w-[1280px] text-sm">
          <thead>
            <tr className="border-b border-border/60 text-left text-muted-foreground">
              <th className="px-3 py-3">User</th>
              <th className="px-3 py-3">Payment</th>
              <th className="px-3 py-3">Order</th>
              <th className="px-3 py-3">Amount</th>
              <th className="px-3 py-3">Source</th>
              <th className="px-3 py-3">Method</th>
              <th className="px-3 py-3">Status</th>
              <th className="px-3 py-3">Reconciliation</th>
              <th className="px-3 py-3">Created</th>
              <th className="px-3 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className="px-3 py-8 text-muted-foreground" colSpan={10}>Loading payments...</td></tr>
            ) : error ? (
              <tr><td className="px-3 py-8 text-rose-300" colSpan={10}>{error}</td></tr>
            ) : items.length === 0 ? (
              <tr><td className="px-3 py-8 text-center text-muted-foreground" colSpan={10}>No data found</td></tr>
            ) : items.map((item) => (
              <tr key={item.id} className="border-b border-border/30 hover:bg-card/50 transition-colors">
                <td className="px-3 py-3">
                  <div className="text-foreground">{item.user_name || item.user_email || "—"}</div>
                  <div className="text-muted-foreground text-xs">{item.user_email || ""}</div>
                </td>
                <td className="px-3 py-3 font-mono text-xs text-muted-foreground">{item.razorpay_payment_id || item.id}</td>
                <td className="px-3 py-3 font-mono text-xs text-muted-foreground">{item.razorpay_order_id || item.billing_order_id || "—"}</td>
                <td className="px-3 py-3 text-foreground font-medium">{formatPaymentAmount(item.amount, item.currency)}</td>
                <td className="px-3 py-3 text-foreground">{item.purpose || "—"}</td>
                <td className="px-3 py-3 text-foreground">{item.payment_method}</td>
                <td className="px-3 py-3">
                  <span className="rounded-full border border-border/60 bg-card/50 px-2 py-1 text-xs text-foreground">{item.status}</span>
                </td>
                <td className="px-3 py-3">
                  <span className={`rounded-full px-2 py-1 text-xs ${item.is_reconciled ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"}`}>
                    {item.is_reconciled ? "Reconciled" : "Pending"}
                  </span>
                </td>
                <td className="px-3 py-3 text-muted-foreground">{new Date(item.created_at).toLocaleString()}</td>
                <td className="px-3 py-3">
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40" onClick={() => openDetails(item.id)}>
                      <Eye className="mr-2 h-4 w-4" />View
                    </Button>
                    {(item.status || "").toUpperCase() !== "REFUNDED" && (
                      <Button size="sm" variant="outline" className="rounded-xl border-rose-500/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20" onClick={() => refund(item.id)}>
                        Refund
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <div>Showing {items.length} of {total}</div>
        <div className="flex gap-2">
          <Button disabled={skip === 0} onClick={() => load(Math.max(0, skip - PAGE_SIZE))} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">Previous</Button>
          <Button disabled={skip + PAGE_SIZE >= total} onClick={() => load(skip + PAGE_SIZE)} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">Next</Button>
        </div>
      </div>

      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="rounded-xl border border-border/60 bg-card/95 text-foreground">
          <DialogHeader><DialogTitle>Payment Details</DialogTitle></DialogHeader>
          {selected && (
            <div className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
              <div><span className="text-muted-foreground">User:</span> {selected.user_name || selected.user_email || "—"}</div>
              <div><span className="text-muted-foreground">Amount:</span> {formatPaymentAmount(selected.amount, selected.currency)}</div>
              <div><span className="text-muted-foreground">Status:</span> {selected.status}</div>
              <div><span className="text-muted-foreground">Purpose:</span> {selected.purpose || "—"}</div>
              <div><span className="text-muted-foreground">Method:</span> {selected.payment_method}</div>
              <div><span className="text-muted-foreground">Payment ID:</span> {selected.razorpay_payment_id || "—"}</div>
              <div><span className="text-muted-foreground">Order ID:</span> {selected.razorpay_order_id || selected.billing_order_id || "—"}</div>
              <div><span className="text-muted-foreground">Verified At:</span> {selected.verified_at ? new Date(selected.verified_at).toLocaleString() : "—"}</div>
              <div className="md:col-span-2"><span className="text-muted-foreground">Failure/Reconciliation Note:</span> {selected.failure_reason || "—"}</div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40" onClick={() => setSelected(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
