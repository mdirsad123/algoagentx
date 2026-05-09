"use client"

import { useEffect, useMemo, useState } from "react"
import { adminApi, CreditTransaction, CreditTopupPack } from "@/lib/api/admin"
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
  const [transactionType, setTransactionType] = useState("")
  const [packs, setPacks] = useState<CreditTopupPack[]>([])
  const [packsLoading, setPacksLoading] = useState(false)
  const [packModalOpen, setPackModalOpen] = useState(false)
  const [editingPack, setEditingPack] = useState<CreditTopupPack | null>(null)
  const [packForm, setPackForm] = useState({
    code: "",
    title: "",
    credits: 10,
    price_usd: 1,
    bonus_credits: 0,
    description: "",
    is_popular: false,
    is_active: true,
    sort_order: 100,
  })

  const pageSize = 20
  const canSubmit = useMemo(() => {
    return userId.trim().length > 0 && Number.isFinite(amount) && amount > 0 && reason.trim().length > 0
  }, [userId, amount, reason])

  const formatLedgerSource = (item: CreditTransaction) => {
    const source = String(item.source || item.source_type || item.type || "").toLowerCase();
    if (source.includes("backtest")) return "Backtest Credit Debit";
    if (source.includes("included")) return "Subscription Included Credits";
    if (source.includes("wallet")) return "Wallet Credits";
    return item.source || item.source_type || item.type || "—";
  }

  const loadPacks = async () => {
    try {
      setPacksLoading(true)
      setPacks(await adminApi.getCreditPacks())
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load top-up packs")
    } finally {
      setPacksLoading(false)
    }
  }

  const openCreatePack = () => {
    setEditingPack(null)
    setPackForm({ code: "", title: "", credits: 10, price_usd: 1, bonus_credits: 0, description: "", is_popular: false, is_active: true, sort_order: 100 })
    setPackModalOpen(true)
  }

  const openEditPack = (pack: CreditTopupPack) => {
    setEditingPack(pack)
    setPackForm({
      code: pack.code,
      title: pack.title,
      credits: Number(pack.credits || 0),
      price_usd: Number(pack.price_usd || 0),
      bonus_credits: Number(pack.bonus_credits || 0),
      description: pack.description || "",
      is_popular: Boolean(pack.is_popular),
      is_active: Boolean(pack.is_active),
      sort_order: Number(pack.sort_order || 100),
    })
    setPackModalOpen(true)
  }

  const savePack = async () => {
    try {
      const payload = {
        ...packForm,
        code: packForm.code.trim().toUpperCase().replace(/\s+/g, "_"),
        credits: Number(packForm.credits),
        price_usd: Number(packForm.price_usd),
        bonus_credits: Number(packForm.bonus_credits || 0),
        sort_order: Number(packForm.sort_order || 100),
      }
      if (!payload.code || !payload.title || payload.credits <= 0 || payload.price_usd <= 0 || payload.bonus_credits < 0) {
        toast.error("Please enter valid pack details")
        return
      }
      if (editingPack) await adminApi.updateCreditPack(editingPack.id, payload)
      else await adminApi.createCreditPack(payload)
      toast.success("Top-up pack saved")
      setPackModalOpen(false)
      await loadPacks()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Unable to save top-up pack")
    }
  }

  const togglePackStatus = async (pack: CreditTopupPack, field: "is_active" | "is_popular") => {
    try {
      await adminApi.updateCreditPackStatus(pack.id, { [field]: !pack[field] })
      await loadPacks()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Unable to update pack")
    }
  }

  const load = async (nextSkip = skip) => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.getCredits(nextSkip, pageSize, search || undefined, transactionType || undefined)
      setItems(data.items)
      setTotal(data.total)
      setSkip(nextSkip)
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load credits")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(0); loadPacks() }, [])

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
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-white">Top-up Packs</h2>
            <p className="text-sm text-purple-200">Admin-managed credit packs shown on the user Credits page.</p>
          </div>
          <div className="flex gap-2">
            <Button onClick={loadPacks} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="mr-2 h-4 w-4" />Reload Packs</Button>
            <Button onClick={openCreatePack} className="bg-gradient-to-r from-emerald-500 to-cyan-500 text-white">Create Pack</Button>
          </div>
        </div>
        <div className="admin-table-scroll overflow-auto rounded-2xl border border-white/10 bg-slate-950/30">
          <table className="admin-data-table w-full min-w-[1050px] text-sm text-white">
            <thead>
              <tr className="border-b border-white/10 text-left text-purple-200">
                <th className="px-3 py-3">Code</th>
                <th className="px-3 py-3">Title</th>
                <th className="px-3 py-3">Credits</th>
                <th className="px-3 py-3">Price USD</th>
                <th className="px-3 py-3">Popular</th>
                <th className="px-3 py-3">Active</th>
                <th className="px-3 py-3">Sort</th>
                <th className="px-3 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {packsLoading ? <tr><td className="px-3 py-8 text-purple-200" colSpan={8}>Loading top-up packs...</td></tr> : packs.length === 0 ? <tr><td className="px-3 py-8 text-center text-purple-200" colSpan={8}>No packs found. Run migration or create one.</td></tr> : packs.map((pack) => (
                <tr key={pack.id} className="border-b border-white/5">
                  <td className="px-3 py-3 font-mono text-xs">{pack.code}</td>
                  <td className="px-3 py-3"><div>{pack.title}</div><div className="text-xs text-purple-200/70">{pack.description || "—"}</div></td>
                  <td className="px-3 py-3">{pack.credits.toLocaleString()}{pack.bonus_credits > 0 ? ` + ${pack.bonus_credits.toLocaleString()} bonus` : ""}</td>
                  <td className="px-3 py-3 font-semibold text-emerald-300">${Number(pack.price_usd || 0).toFixed(2)}</td>
                  <td className="px-3 py-3"><Button size="sm" variant="outline" onClick={() => togglePackStatus(pack, "is_popular")} className="border-white/15 bg-white/5 text-white hover:bg-white/10">{pack.is_popular ? "Popular" : "Mark"}</Button></td>
                  <td className="px-3 py-3"><Button size="sm" variant="outline" onClick={() => togglePackStatus(pack, "is_active")} className={pack.is_active ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200" : "border-rose-400/30 bg-rose-500/10 text-rose-200"}>{pack.is_active ? "Active" : "Inactive"}</Button></td>
                  <td className="px-3 py-3">{pack.sort_order}</td>
                  <td className="px-3 py-3"><Button size="sm" onClick={() => openEditPack(pack)} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">Edit</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl shadow-xl">
        <div className="mb-4 flex flex-wrap gap-3">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by user email or reason" className="max-w-sm border-white/10 bg-white/5 text-white placeholder:text-purple-200/70" />
          <select value={transactionType} onChange={(e) => setTransactionType(e.target.value)} className="rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-white">
            <option value="">All types</option>
            <option value="credit">credit</option>
            <option value="debit">debit</option>
            <option value="refund">refund</option>
          </select>
          <Button onClick={() => load(0)} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">Search</Button>
        </div>

        {error ? <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 p-5 text-rose-200">{error}</div> : (
          <div className="admin-table-scroll overflow-auto rounded-2xl border border-white/10 bg-slate-950/30">
            <table className="admin-data-table w-full min-w-[1100px] text-sm text-white">
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
                 {loading ? <tr><td className="px-3 py-8 text-purple-200" colSpan={6}>Loading credits...</td></tr> : items.length === 0 ? <tr><td className="px-3 py-8 text-center text-purple-200" colSpan={6}>No data found</td></tr> : items.map((item) => (
                  <tr key={item.id} className="border-b border-white/5">
                    <td className="px-3 py-3"><div>{item.user_name || item.user_email || '—'}</div><div className="text-xs text-purple-200">{item.user_email}</div></td>
                    <td className="px-3 py-3 text-emerald-300">{item.credits_added ?? ((item.credits ?? 0) > 0 ? item.credits : 0)}</td>
                    <td className="px-3 py-3 text-rose-300">{item.credits_used ?? ((item.credits ?? 0) < 0 ? Math.abs(item.credits || 0) : 0)}</td>
                    <td className="px-3 py-3">{item.remaining_credits ?? item.balance_after ?? 0}</td>
                    <td className="px-3 py-3">
                      <div>{formatLedgerSource(item)}</div>
                      <div className="text-xs text-purple-200">{item.reason || '—'}</div>
                      <div className="text-xs text-purple-200/70">actor: {item.actor_user_id || '—'}</div>
                    </td>
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
            <Button disabled={skip === 0} onClick={() => load(Math.max(0, skip - pageSize))} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10">Previous</Button>
            <Button disabled={skip + pageSize >= total} onClick={() => load(skip + pageSize)} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10">Next</Button>
          </div>
        </div>
      </div>

      <Dialog open={packModalOpen} onOpenChange={setPackModalOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto max-w-2xl border-purple-400/20 bg-gradient-to-br from-purple-950 to-slate-950 text-white">
          <DialogHeader><DialogTitle>{editingPack ? "Edit top-up pack" : "Create top-up pack"}</DialogTitle></DialogHeader>
          <div className="grid gap-3 md:grid-cols-2">
            <Input placeholder="Code e.g. POPULAR_500" value={packForm.code} onChange={(e) => setPackForm({ ...packForm, code: e.target.value.toUpperCase().replace(/\s+/g, "_") })} className="border-white/20 bg-white/10 text-white" />
            <Input placeholder="Title" value={packForm.title} onChange={(e) => setPackForm({ ...packForm, title: e.target.value })} className="border-white/20 bg-white/10 text-white" />
            <Input type="number" placeholder="Credits" value={packForm.credits} onChange={(e) => setPackForm({ ...packForm, credits: Number(e.target.value) })} className="border-white/20 bg-white/10 text-white" />
            <Input type="number" step="0.01" placeholder="Price USD" value={packForm.price_usd} onChange={(e) => setPackForm({ ...packForm, price_usd: Number(e.target.value) })} className="border-white/20 bg-white/10 text-white" />
            <Input type="number" placeholder="Bonus Credits" value={packForm.bonus_credits} onChange={(e) => setPackForm({ ...packForm, bonus_credits: Number(e.target.value) })} className="border-white/20 bg-white/10 text-white" />
            <Input type="number" placeholder="Sort Order" value={packForm.sort_order} onChange={(e) => setPackForm({ ...packForm, sort_order: Number(e.target.value) })} className="border-white/20 bg-white/10 text-white" />
            <Input placeholder="Description" value={packForm.description} onChange={(e) => setPackForm({ ...packForm, description: e.target.value })} className="border-white/20 bg-white/10 text-white md:col-span-2" />
            <label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={packForm.is_popular} onChange={(e) => setPackForm({ ...packForm, is_popular: e.target.checked })} /> Popular badge</label>
            <label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={packForm.is_active} onChange={(e) => setPackForm({ ...packForm, is_active: e.target.checked })} /> Active</label>
          </div>
          <DialogFooter>
            <Button variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={() => setPackModalOpen(false)}>Cancel</Button>
            <Button onClick={savePack} className="bg-gradient-to-r from-emerald-500 to-cyan-500 text-white">Save Pack</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto border-purple-400/20 bg-gradient-to-br from-purple-950 to-slate-950 text-white">
          <DialogHeader><DialogTitle>Adjust credits</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <select value={mode} onChange={(e) => setMode(e.target.value as any)} className="w-full rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-white"><option value="add">Add credits</option><option value="deduct">Deduct credits</option></select>
            <Input placeholder="User ID or user email" value={userId} onChange={(e) => setUserId(e.target.value)} className="border-white/20 bg-white/10 text-white" />
            <Input type="number" value={amount} onChange={(e) => setAmount(Number(e.target.value))} className="border-white/20 bg-white/10 text-white" />
            <Input placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)} className="border-white/20 bg-white/10 text-white placeholder:text-purple-200/70" />
          </div>
          <DialogFooter>
            <Button variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={submit} disabled={!canSubmit} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white disabled:opacity-50">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
