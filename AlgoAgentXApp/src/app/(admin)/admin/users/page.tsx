"use client"

import { useEffect, useState } from "react"
import { adminApi, User } from "@/lib/api/admin"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { RefreshCw, Trash2, UserPlus, Pencil, Coins } from "lucide-react"
import { toast } from "sonner"

const emptyForm = { email: "", password: "", fullname: "", mobile: "", role: "user", is_active: true }

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [creditModalOpen, setCreditModalOpen] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)
  const [creditUser, setCreditUser] = useState<User | null>(null)
  const [creditMode, setCreditMode] = useState<"add" | "deduct">("add")
  const [creditAmount, setCreditAmount] = useState(100)
  const [creditReason, setCreditReason] = useState("")
  const [form, setForm] = useState<any>(emptyForm)

  const fetchUsers = async (nextSkip = skip) => {
    setLoading(true)
    try {
      const data = await adminApi.getUsers(nextSkip, 20, search)
      setUsers(data.items)
      setTotal(data.total)
      setSkip(nextSkip)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load users")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUsers(0) }, [])

  const submit = async () => {
    try {
      if (editing) {
        await adminApi.updateUser(editing.id, { email: form.email, fullname: form.fullname, mobile: form.mobile, role: form.role })
        toast.success("User updated")
      } else {
        await adminApi.createUser(form)
        toast.success("User created")
      }
      setModalOpen(false)
      setEditing(null)
      setForm(emptyForm)
      fetchUsers(skip)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Action failed")
    }
  }

  const adjustCredits = async () => {
    if (!creditUser) return
    try {
      if (creditMode === "add") await adminApi.addCredits(creditUser.id, creditAmount, creditReason || "Admin credit add")
      else await adminApi.deductCredits(creditUser.id, creditAmount, creditReason || "Admin credit deduct")
      toast.success("Credits updated")
      setCreditModalOpen(false)
      setCreditUser(null)
      setCreditReason("")
      setCreditAmount(100)
      fetchUsers(skip)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Unable to update credits")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white">Users</h1>
          <p className="text-sm text-purple-200">Full admin control for user lifecycle, plans and credits.</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => fetchUsers(skip)} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
          <Button onClick={() => { setEditing(null); setForm(emptyForm); setModalOpen(true) }} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white"><UserPlus className="mr-2 h-4 w-4" />Add User</Button>
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl shadow-xl">
        <div className="mb-4 flex gap-3">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by email or name" className="max-w-sm border-white/10 bg-white/5 text-white placeholder:text-purple-200/70" />
          <Button onClick={() => fetchUsers(0)} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10">Search</Button>
        </div>

        <div className="overflow-auto">
          <table className="w-full min-w-[1080px] text-sm text-white">
            <thead>
              <tr className="border-b border-white/10 text-left text-purple-200">
                <th className="px-3 py-3">User</th>
                <th className="px-3 py-3">Role</th>
                <th className="px-3 py-3">Plan</th>
                <th className="px-3 py-3">Credits</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Mobile</th>
                <th className="px-3 py-3">Joined</th>
                <th className="px-3 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? <tr><td className="px-3 py-8 text-purple-200" colSpan={8}>Loading users...</td></tr> : users.length === 0 ? <tr><td className="px-3 py-8 text-center text-purple-200" colSpan={8}>No users found</td></tr> : users.map((user) => (
                <tr key={user.id} className="border-b border-white/5">
                  <td className="px-3 py-3"><div>{user.fullname || '—'}</div><div className="text-xs text-purple-200">{user.email}</div></td>
                  <td className="px-3 py-3">
                    <select value={user.role} onChange={async (e) => { try { await adminApi.updateUserRole(user.id, e.target.value); toast.success("Role updated"); fetchUsers(skip) } catch (err: any) { toast.error(err?.response?.data?.detail || "Unable to update role") } }} className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-white">
                      <option value="user">user</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td className="px-3 py-3"><span className="rounded-full bg-purple-500/20 px-3 py-1 text-xs text-purple-200 uppercase">{user.plan || 'free'}</span></td>
                  <td className="px-3 py-3">{user.credits ?? 0}</td>
                  <td className="px-3 py-3">
                    <button className={`rounded-full px-3 py-1 text-xs ${user.is_active ? 'bg-emerald-500/15 text-emerald-300' : 'bg-rose-500/15 text-rose-300'}`} onClick={async () => { try { await adminApi.updateUserStatus(user.id, !user.is_active); toast.success("Status updated"); fetchUsers(skip) } catch (err: any) { toast.error(err?.response?.data?.detail || "Unable to update status") } }}>{user.is_active ? 'Active' : 'Inactive'}</button>
                  </td>
                  <td className="px-3 py-3">{user.mobile || '—'}</td>
                  <td className="px-3 py-3">{new Date(user.created_at).toLocaleDateString()}</td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Button variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={() => { setEditing(user); setForm({ ...emptyForm, ...user }); setModalOpen(true) }}><Pencil className="mr-2 h-4 w-4" />Edit</Button>
                      <Button variant="outline" className="border-cyan-400/20 bg-cyan-500/10 text-cyan-200 hover:bg-cyan-500/20" onClick={() => { setCreditUser(user); setCreditMode("add"); setCreditReason(""); setCreditModalOpen(true) }}><Coins className="mr-2 h-4 w-4" />Credits</Button>
                      <Button variant="outline" className="border-rose-400/20 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20" onClick={async () => { if (!window.confirm(`Delete ${user.email}?`)) return; try { await adminApi.deleteUser(user.id); toast.success("User deleted"); fetchUsers(skip) } catch (err: any) { toast.error(err?.response?.data?.detail || "Unable to delete user") } }}><Trash2 className="mr-2 h-4 w-4" />Delete</Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex items-center justify-between text-sm text-purple-200">
          <div>Showing {users.length} of {total}</div>
          <div className="flex gap-2">
            <Button disabled={skip === 0} onClick={() => fetchUsers(Math.max(0, skip - 20))} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10">Previous</Button>
            <Button disabled={skip + 20 >= total} onClick={() => fetchUsers(skip + 20)} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10">Next</Button>
          </div>
        </div>
      </div>

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="border-purple-400/20 bg-gradient-to-br from-purple-950 to-slate-950 p-6 text-white shadow-2xl">
          <DialogHeader><DialogTitle>{editing ? 'Edit user' : 'Create user'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="border-white/20 bg-white/10 text-white placeholder:text-purple-200/70" />
            {!editing && <Input placeholder="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="border-white/20 bg-white/10 text-white placeholder:text-purple-200/70" />}
            <Input placeholder="Full name" value={form.fullname || ''} onChange={(e) => setForm({ ...form, fullname: e.target.value })} className="border-white/20 bg-white/10 text-white placeholder:text-purple-200/70" />
            <Input placeholder="Mobile" value={form.mobile || ''} onChange={(e) => setForm({ ...form, mobile: e.target.value })} className="border-white/20 bg-white/10 text-white placeholder:text-purple-200/70" />
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="w-full rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-white"><option value="user">user</option><option value="admin">admin</option></select>
          </div>
          <DialogFooter>
            <Button variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={submit} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">{editing ? 'Save changes' : 'Create user'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={creditModalOpen} onOpenChange={setCreditModalOpen}>
        <DialogContent className="border-purple-400/20 bg-gradient-to-br from-purple-950 to-slate-950 p-6 text-white shadow-2xl">
          <DialogHeader><DialogTitle>Adjust credits {creditUser ? `for ${creditUser.email}` : ''}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <select value={creditMode} onChange={(e) => setCreditMode(e.target.value as any)} className="w-full rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-white"><option value="add">Add credits</option><option value="deduct">Deduct credits</option></select>
            <Input type="number" value={creditAmount} onChange={(e) => setCreditAmount(Number(e.target.value))} className="border-white/20 bg-white/10 text-white" />
            <Input placeholder="Reason" value={creditReason} onChange={(e) => setCreditReason(e.target.value)} className="border-white/20 bg-white/10 text-white placeholder:text-purple-200/70" />
          </div>
          <DialogFooter>
            <Button variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={() => setCreditModalOpen(false)}>Cancel</Button>
            <Button onClick={adjustCredits} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
