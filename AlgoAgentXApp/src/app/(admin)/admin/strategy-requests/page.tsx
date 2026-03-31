"use client"

import { useEffect, useState } from "react"
import { adminApi, ImplementedStrategy, StrategyRequest } from "@/lib/api/admin"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { RefreshCw } from "lucide-react"
import { toast } from "sonner"

export default function AdminStrategyRequestsPage() {
  const [items, setItems] = useState<StrategyRequest[]>([])
  const [implemented, setImplemented] = useState<ImplementedStrategy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState("")
  const [skip, setSkip] = useState(0)
  const [total, setTotal] = useState(0)
  const [selected, setSelected] = useState<StrategyRequest | null>(null)
  const [adminNotes, setAdminNotes] = useState("")

  const load = async (nextSkip = skip) => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.getStrategies(nextSkip, 20, status || undefined, search || undefined)
      setItems(data.items)
      setImplemented(data.implemented)
      setTotal(data.total)
      setSkip(nextSkip)
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load strategy requests")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(0) }, [])

  const decide = async (requestId: string, nextStatus: string) => {
    try {
      await adminApi.updateStrategy(requestId, { status: nextStatus, admin_notes: adminNotes || undefined })
      toast.success("Strategy request updated")
      setSelected(null)
      setAdminNotes("")
      load(skip)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Unable to update strategy request")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white">Strategy Requests</h1>
          <p className="text-sm text-purple-200">Review requests and track implemented strategies.</p>
        </div>
        <Button onClick={() => load(skip)} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl shadow-xl">
        <div className="mb-4 flex flex-wrap gap-3">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by title, user or type" className="max-w-sm border-white/10 bg-white/5 text-white placeholder:text-purple-200/70" />
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-white">
            <option value="">All statuses</option>
            <option value="UNDER_DEVELOPMENT">UNDER_DEVELOPMENT</option>
            <option value="NEEDS_CLARIFICATION">NEEDS_CLARIFICATION</option>
            <option value="REJECTED">REJECTED</option>
            <option value="DEPLOYED">DEPLOYED</option>
          </select>
          <Button onClick={() => load(0)} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">Apply</Button>
        </div>

        {error ? <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 p-5 text-rose-200">{error}</div> : (
          <div className="overflow-auto rounded-2xl border border-white/10 bg-slate-950/30">
            <table className="w-full min-w-[1100px] text-sm text-white">
              <thead>
                <tr className="border-b border-white/10 text-left text-purple-200">
                  <th className="px-3 py-3">User</th>
                  <th className="px-3 py-3">Strategy Title</th>
                  <th className="px-3 py-3">Description</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Submitted</th>
                  <th className="px-3 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? <tr><td className="px-3 py-8 text-purple-200" colSpan={6}>Loading requests...</td></tr> : items.length === 0 ? <tr><td className="px-3 py-8 text-center text-purple-200" colSpan={6}>No strategy requests found</td></tr> : items.map((item) => (
                  <tr key={item.id} className="border-b border-white/5">
                    <td className="px-3 py-3"><div>{item.user_name || item.user_email || '—'}</div><div className="text-xs text-purple-200">{item.user_email || ''}</div></td>
                    <td className="px-3 py-3"><div>{item.title}</div><div className="text-xs text-purple-200">{item.strategy_type || '—'} / {item.market || '—'} / {item.timeframe || '—'}</div></td>
                    <td className="px-3 py-3 max-w-[360px] truncate">{item.description || '—'}</td>
                    <td className="px-3 py-3"><span className="rounded-full bg-white/10 px-3 py-1 text-xs">{item.status}</span></td>
                    <td className="px-3 py-3">{new Date(item.created_at).toLocaleString()}</td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={() => { setSelected(item); setAdminNotes(item.admin_notes || "") }}>View</Button>
                        <Button size="sm" className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white" onClick={() => decide(item.id, "DEPLOYED")}>Approve</Button>
                        <Button size="sm" className="bg-gradient-to-r from-rose-500 to-orange-500 text-white" onClick={() => decide(item.id, "REJECTED")}>Reject</Button>
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

      <div className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl shadow-xl">
        <h2 className="mb-4 text-xl font-semibold text-white">Implemented Strategies</h2>
        <div className="overflow-auto rounded-2xl border border-white/10 bg-slate-950/30">
          <table className="w-full min-w-[900px] text-sm text-white">
            <thead>
              <tr className="border-b border-white/10 text-left text-purple-200">
                <th className="px-3 py-3">Strategy Name</th>
                <th className="px-3 py-3">Description</th>
                <th className="px-3 py-3">Code</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {implemented.length === 0 ? <tr><td className="px-3 py-8 text-center text-purple-200" colSpan={5}>No implemented strategies found</td></tr> : implemented.map((item) => (
                <tr key={item.id} className="border-b border-white/5">
                  <td className="px-3 py-3">{item.name}</td>
                  <td className="px-3 py-3">{item.description || '—'}</td>
                  <td className="px-3 py-3"><pre className="max-w-[320px] overflow-auto text-xs text-purple-200">{typeof item.code === 'string' ? item.code : JSON.stringify(item.code, null, 2)}</pre></td>
                  <td className="px-3 py-3"><span className="rounded-full bg-white/10 px-3 py-1 text-xs">{item.status}</span></td>
                  <td className="px-3 py-3">{new Date(item.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="border-purple-400/20 bg-gradient-to-br from-purple-950 to-slate-950 text-white">
          <DialogHeader><DialogTitle>Strategy request details</DialogTitle></DialogHeader>
          {selected && <div className="space-y-2 text-sm">
            <div><span className="text-purple-200">User:</span> {selected.user_name || selected.user_email || '—'}</div>
            <div><span className="text-purple-200">Title:</span> {selected.title}</div>
            <div><span className="text-purple-200">Description:</span> {selected.description || '—'}</div>
            <div><span className="text-purple-200">Status:</span> {selected.status}</div>
            <textarea value={adminNotes} onChange={(e) => setAdminNotes(e.target.value)} className="mt-3 min-h-[120px] w-full rounded-xl border border-white/20 bg-white/10 p-3 text-white placeholder:text-purple-200/70" placeholder="Admin notes" />
          </div>}
          <DialogFooter>
            {selected && <>
              <Button variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={() => setSelected(null)}>Close</Button>
              <Button className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white" onClick={() => selected && decide(selected.id, "DEPLOYED")}>Approve</Button>
              <Button className="bg-gradient-to-r from-rose-500 to-orange-500 text-white" onClick={() => selected && decide(selected.id, "REJECTED")}>Reject</Button>
            </>}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
