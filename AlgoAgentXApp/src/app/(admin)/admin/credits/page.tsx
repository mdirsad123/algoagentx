"use client"

import { useEffect, useState } from "react"
import { adminApi, CreditTransaction } from "@/lib/api/admin"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { RefreshCw } from "lucide-react"
import { toast } from "sonner"

export default function AdminCreditsPage() {
  const [items, setItems] = useState<CreditTransaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [skip, setSkip] = useState(0)
  const [total, setTotal] = useState(0)
  const [modalOpen, setModalOpen] = useState(false)
  const [mode, setMode] = useState<"add" | "deduct">("add")
  const [userId, setUserId] = useState("")
  const [amount, setAmount] = useState(100)
  const [reason, setReason] = useState("")

  const load = async (nextSkip = skip) => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.getCredits(nextSkip, 20, search || undefined)
      setItems(data.items)
      setTotal(data.total)
      setSkip(nextSkip)
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load credits")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(0) }, [])

  const submit = async () => {
    try {
      if (mode === "add") await adminApi.addCredits(userId, amount, reason || "Admin credit add")
      else await adminApi.deductCredits(userId, amount, reason || "Admin credit deduct")
      toast.success("Credits updated")
      setModalOpen(false)
      setUserId("")
      setAmount(100)
      setReason("")
      load(skip)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Unable to update credits")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white">Credits</h1>
          <p className="text-sm text-purple-200">Review credit ledger and adjust balances.</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => load(skip)} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
          <Button onClick={() => setModalOpen(true)} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">Adjust Credits</Button>
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl shadow-xl">
        <div className="mb-4 flex gap-3">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by user email or reason" className="max-w-sm border-white/10 bg-white/5 text-white placeholder:text-purple-200/70" />
          <Button onClick={() => load(0)} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">Search</Button>
        </div>

        {error ? <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 p-5 text-rose-200">{error}</div> : (
          <div className="overflow-auto rounded-2xl border border-white/10 bg-slate-950/30">
            <table className="w-full min-w-[1100px] text-sm text-white">
              <thead>
                <tr className="border-b border-white/10 text-left text-purple-200">
                  <th className="px-3 py-3">User</th>
                  <th className="px-3 py-3">Credits Added</th>
                  <th className="px-3 py-3">Credits Used</th>
                  <th className="px-3 py-3">Remaining Credits</th>
                  <th className="px-3 py-3">Source</th>
                  <th className="px-3 py-3">Date</th>
                </tr>
              </thead>
              <tbody>
                {loading ? <tr><td className="px-3 py-8 text-purple-200" colSpan={6}>Loading credits...</td></tr> : items.length === 0 ? <tr><td className="px-3 py-8 text-center text-purple-200" colSpan={6}>No credit transactions found</td></tr> : items.map((item) => (
                  <tr key={item.id} className="border-b border-white/5">
                    <td className="px-3 py-3"><div>{item.user_name || item.user_email || '—'}</div><div className="text-xs text-purple-200">{item.user_email}</div></td>
                    <td className="px-3 py-3 text-emerald-300">{item.credits_added ?? (item.credits > 0 ? item.credits : 0)}</td>
                    <td className="px-3 py-3 text-rose-300">{item.credits_used ?? (item.credits < 0 ? Math.abs(item.credits) : 0)}</td>
                    <td className="px-3 py-3">{item.remaining_credits ?? item.balance_after ?? 0}</td>
                    <td className="px-3 py-3">{item.source || item.reason || item.type}</td>
                    <td className="px-3 py-3">{new Date(item.created_at).toLocaleString()}</td>
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

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="border-purple-400/20 bg-gradient-to-br from-purple-950 to-slate-950 text-white">
          <DialogHeader><DialogTitle>Adjust credits</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <select value={mode} onChange={(e) => setMode(e.target.value as any)} className="w-full rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-white"><option value="add">Add credits</option><option value="deduct">Deduct credits</option></select>
            <Input placeholder="User ID" value={userId} onChange={(e) => setUserId(e.target.value)} className="border-white/20 bg-white/10 text-white" />
            <Input type="number" value={amount} onChange={(e) => setAmount(Number(e.target.value))} className="border-white/20 bg-white/10 text-white" />
            <Input placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)} className="border-white/20 bg-white/10 text-white placeholder:text-purple-200/70" />
          </div>
          <DialogFooter>
            <Button variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={submit} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
