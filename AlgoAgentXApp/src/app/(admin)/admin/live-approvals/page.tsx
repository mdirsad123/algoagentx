"use client";

import { useEffect, useState } from "react";
import { RefreshCw, ShieldCheck, ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { LiveTradingApproval } from "@/types/live-trading";

const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");

export default function AdminLiveApprovalsPage() {
  const { showToast } = useToast();
  const [rows, setRows] = useState<LiveTradingApproval[]>([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      setRows(await liveTradingApi.adminListLiveApprovals(status || undefined));
    } catch (error: any) {
      showToast(error.message || "Failed to load live approvals", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const decide = async (row: LiveTradingApproval, action: "approve" | "reject" | "revoke") => {
    const notes = window.prompt(`Notes for ${action}?`, action === "approve" ? "Admin approved after review" : "Admin decision") || "Admin decision";
    try {
      setBusyId(row.id);
      await liveTradingApi.adminDecideLiveApproval(row.id, action, {
        notes,
        approved_markets: row.approved_markets || [],
        max_daily_loss: row.max_daily_loss,
        max_order_value: row.max_order_value,
        max_trades_per_day: row.max_trades_per_day,
      });
      showToast(`Live approval ${action} completed`, "success");
      await load();
    } catch (error: any) {
      showToast(error.message || "Approval action failed", "error");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <PageShell>
      <PageHeader title="Admin Live Approvals" subtitle="Review, approve, reject or revoke real-money trading access." actions={<div className="flex gap-2"><select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-white/10 bg-purple-950 px-3 py-2 text-sm text-white"><option value="">All</option><option value="PENDING">Pending</option><option value="APPROVED">Approved</option><option value="REJECTED">Rejected</option><option value="REVOKED">Revoked</option></select><Button onClick={load} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="h-4 w-4" />Refresh</Button></div>} />
      <GlassCard className="p-6" hoverEffect={false}>
        {loading ? <p className="text-purple-100">Loading approvals...</p> : rows.length === 0 ? <p className="text-purple-200">No live approval requests found.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[1200px] text-left text-sm"><thead className="text-purple-200"><tr><th>Created</th><th>User</th><th>Broker</th><th>Status</th><th>Markets</th><th>Daily Loss</th><th>Order Value</th><th>Trades/Day</th><th>Disclaimer</th><th>Notes</th><th className="text-right">Actions</th></tr></thead><tbody className="divide-y divide-white/10">{rows.map((row) => <tr key={row.id} className="text-purple-50"><td className="py-3">{date(row.created_at)}</td><td><div className="font-semibold text-white">{row.user_name || "User"}</div><div className="text-xs text-purple-300">{row.user_email || row.user_id}</div></td><td>{row.broker_name || "Any"}<div className="text-xs text-purple-300">{row.broker_mode || "—"} • {row.broker_status || "—"}</div></td><td><Badge>{row.status}</Badge></td><td>{(row.approved_markets || []).join(", ")}</td><td>{row.max_daily_loss || "—"}</td><td>{row.max_order_value || "—"}</td><td>{row.max_trades_per_day || "—"}</td><td>{date(row.risk_disclaimer_accepted_at)}</td><td>{row.notes || "—"}</td><td><div className="flex justify-end gap-2"><Button size="sm" disabled={busyId === row.id} onClick={() => decide(row, "approve")} className="gap-1 bg-lime-500 text-slate-950 hover:bg-lime-400"><ShieldCheck className="h-3.5 w-3.5" />Approve</Button><Button size="sm" disabled={busyId === row.id} onClick={() => decide(row, "reject")} variant="outline" className="gap-1 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><ShieldX className="h-3.5 w-3.5" />Reject</Button><Button size="sm" disabled={busyId === row.id} onClick={() => decide(row, "revoke")} variant="outline" className="border-yellow-400/30 bg-yellow-500/10 text-yellow-100 hover:bg-yellow-500/20">Revoke</Button></div></td></tr>)}</tbody></table></div>}
      </GlassCard>
    </PageShell>
  );
}
