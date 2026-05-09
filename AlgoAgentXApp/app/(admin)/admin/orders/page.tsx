"use client"

import { useEffect, useState } from "react"
import { adminApi, BillingAuditOrder, BillingSummary } from "@/lib/api/admin"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Eye, RefreshCw, RotateCcw } from "lucide-react"

const money = (amount?: number, currency = "USD") => currency === "INR"
  ? `₹${Number(amount || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`
  : `$${Number(amount || 0).toFixed(2)}`
const inr = (amount?: number) => `₹${Number(amount || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`

const emptySummary: BillingSummary = {
  total_revenue_usd: 0, total_revenue_inr: 0, total_gst_collected_inr: 0, total_discounts_usd: 0,
  total_paid_orders: 0, pending_orders: 0, failed_orders: 0, coupon_redemptions: 0, credit_topup_revenue_usd: 0, subscription_revenue_usd: 0,
}

export default function AdminOrdersPage() {
  const [summary, setSummary] = useState<BillingSummary>(emptySummary)
  const [items, setItems] = useState<BillingAuditOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [selected, setSelected] = useState<BillingAuditOrder | null>(null)
  const [status, setStatus] = useState("")
  const [purchaseType, setPurchaseType] = useState("")
  const [method, setMethod] = useState("")
  const [coupon, setCoupon] = useState("")
  const [email, setEmail] = useState("")
  const [fromDate, setFromDate] = useState("")
  const [toDate, setToDate] = useState("")
  const pageSize = 20

  const load = async (nextPage = page) => {
    try {
      setLoading(true); setError(null)
      const [sum, data] = await Promise.all([
        adminApi.getBillingSummary().catch(() => emptySummary),
        adminApi.getBillingAuditOrders({
          page: nextPage, page_size: pageSize,
          status: status || undefined,
          purchase_type: purchaseType || undefined,
          payment_method: method || undefined,
          coupon_code: coupon || undefined,
          user_email: email || undefined,
          from_date: fromDate ? new Date(fromDate).toISOString() : undefined,
          to_date: toDate ? new Date(toDate).toISOString() : undefined,
        }),
      ])
      setSummary(sum); setItems(data.items || []); setTotal(data.total || 0); setPage(nextPage)
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load billing orders")
    } finally { setLoading(false) }
  }

  useEffect(() => { load(1) }, [])
  const reset = () => { setStatus(""); setPurchaseType(""); setMethod(""); setCoupon(""); setEmail(""); setFromDate(""); setToDate(""); setTimeout(() => load(1), 0) }

  return <div className="space-y-6">
    <div className="flex items-center justify-between">
      <div><h1 className="text-foreground text-2xl font-semibold tracking-tight">Orders</h1><p className="text-muted-foreground text-sm">Audit USD/INR orders, GST, coupon discounts, provider references, and payment status.</p></div>
      <Button onClick={() => load(page)} variant="outline" className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
    </div>

    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
      {[
        ["Revenue USD", money(summary.total_revenue_usd)], ["Revenue INR", inr(summary.total_revenue_inr)], ["GST INR", inr(summary.total_gst_collected_inr)],
        ["Discounts USD", money(summary.total_discounts_usd)], ["Paid orders", summary.total_paid_orders], ["Coupon redemptions", summary.coupon_redemptions],
      ].map(([label, value]) => <div key={String(label)} className="rounded-xl border border-border/50 bg-card/30 p-4 shadow-xl backdrop-blur-xl"><div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div><div className="mt-2 text-2xl font-bold text-foreground">{value}</div></div>)}
    </div>

    <div className="rounded-xl border border-border/50 bg-card/30 p-4 shadow-xl backdrop-blur-xl">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-7">
        <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="User email" className="bg-card/20 border-border/50 text-foreground placeholder:text-muted-foreground" />
        <Input value={coupon} onChange={(e) => setCoupon(e.target.value.toUpperCase())} placeholder="Coupon code" className="bg-card/20 border-border/50 text-foreground placeholder:text-muted-foreground" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm text-foreground"><option value="">All statuses</option><option value="PENDING">PENDING</option><option value="PAID">PAID</option><option value="FAILED">FAILED</option><option value="CANCELLED">CANCELLED</option></select>
        <select value={purchaseType} onChange={(e) => setPurchaseType(e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm text-foreground"><option value="">All purchases</option><option value="SUBSCRIPTION">SUBSCRIPTION</option><option value="CREDITS">CREDITS</option></select>
        <select value={method} onChange={(e) => setMethod(e.target.value)} className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm text-foreground"><option value="">All methods</option><option value="RAZORPAY_UPI">RAZORPAY UPI</option><option value="CARD">CARD</option><option value="CRYPTO">CRYPTO</option></select>
        <Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="bg-card/20 border-border/50 text-foreground" />
        <Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="bg-card/20 border-border/50 text-foreground" />
      </div>
      <div className="mt-3 flex gap-2"><Button onClick={() => load(1)} className="rounded-xl">Apply Filters</Button><Button onClick={reset} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"><RotateCcw className="mr-2 h-4 w-4" />Reset</Button></div>
    </div>

    {error ? <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-rose-200">{error}</div> : <div className="admin-table-scroll overflow-auto rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
      <table className="admin-data-table w-full min-w-[1600px] text-sm"><thead><tr className="border-b border-border/60 text-left text-muted-foreground">
        <th className="px-3 py-3">Date</th><th className="px-3 py-3">User</th><th className="px-3 py-3">Purchase</th><th className="px-3 py-3">Subtotal</th><th className="px-3 py-3">Coupon</th><th className="px-3 py-3">Discount</th><th className="px-3 py-3">Final USD</th><th className="px-3 py-3">Method</th><th className="px-3 py-3">Payable</th><th className="px-3 py-3">GST INR</th><th className="px-3 py-3">Provider</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Reference</th><th className="px-3 py-3">Action</th>
      </tr></thead><tbody>
        {loading ? <tr><td colSpan={14} className="px-3 py-8 text-muted-foreground">Loading orders...</td></tr> : items.length === 0 ? <tr><td colSpan={14} className="px-3 py-8 text-center text-muted-foreground">No data found</td></tr> : items.map(item => <tr key={item.id} className="border-b border-border/30 hover:bg-card/50 transition-colors">
          <td className="px-3 py-3 text-muted-foreground">{item.order_date ? new Date(item.order_date).toLocaleString() : "—"}</td>
          <td className="px-3 py-3"><div className="text-foreground">{item.user_name || item.user_email || "—"}</div><div className="text-xs text-muted-foreground">{item.user_email || ""}</div></td>
          <td className="px-3 py-3 text-foreground"><div>{item.purchase_type || "—"}</div><div className="text-xs text-muted-foreground">{item.plan_code || `${item.credit_amount || ""} credits`} {item.billing_period || ""}</div></td>
          <td className="px-3 py-3 text-foreground">{money(item.subtotal_usd)}</td>
          <td className="px-3 py-3">{item.coupon_code ? <span className="rounded-full bg-emerald-500/15 px-2 py-1 text-xs text-emerald-200">{item.coupon_code}</span> : "—"}</td>
          <td className="px-3 py-3 text-rose-200">-{money(item.discount_usd)}</td><td className="px-3 py-3 font-semibold text-foreground">{money(item.final_usd)}</td>
          <td className="px-3 py-3 text-foreground">{item.payment_method || "—"}</td><td className="px-3 py-3 font-semibold text-foreground">{money(item.payment_amount, item.payment_currency || "USD")}</td><td className="px-3 py-3 text-foreground">{inr(item.gst_inr)}</td>
          <td className="px-3 py-3 text-foreground">{item.provider || "—"}</td><td className="px-3 py-3"><span className="rounded-full border border-border/60 bg-card/50 px-2 py-1 text-xs text-foreground">{item.status || "—"}</span></td>
          <td className="px-3 py-3 font-mono text-xs text-muted-foreground">{item.provider_payment_id || item.provider_order_id || item.billing_order_id || "—"}</td>
          <td className="px-3 py-3"><Button size="sm" variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40" onClick={() => setSelected(item)}><Eye className="mr-2 h-4 w-4" />View</Button></td>
        </tr>)}
      </tbody></table>
    </div>}

    <div className="flex items-center justify-between text-sm text-muted-foreground"><div>Showing {items.length} of {total}</div><div className="flex gap-2"><Button disabled={page <= 1} onClick={() => load(page - 1)} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">Previous</Button><Button disabled={page * pageSize >= total} onClick={() => load(page + 1)} variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">Next</Button></div></div>

    <Dialog open={!!selected} onOpenChange={() => setSelected(null)}><DialogContent className="max-h-[90vh] overflow-y-auto max-w-2xl rounded-xl border border-border/60 bg-card/95 text-foreground"><DialogHeader><DialogTitle>Order audit details</DialogTitle></DialogHeader>{selected && <div className="grid gap-2 text-sm md:grid-cols-2">
      {Object.entries(selected).map(([key, value]) => <div key={key} className="rounded-lg border border-border/40 bg-card/30 p-2"><div className="text-xs text-muted-foreground">{key}</div><div className="break-words text-foreground">{String(value ?? "—")}</div></div>)}
    </div>}<DialogFooter><Button variant="outline" onClick={() => setSelected(null)}>Close</Button></DialogFooter></DialogContent></Dialog>
  </div>
}
