"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, RefreshCw, ShieldCheck, ShieldX, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { LiveTradingApproval } from "@/types/live-trading";

const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");
const errorMessage = (error: any, fallback: string) => typeof error?.response?.data?.detail === "string" ? error.response.data.detail : error?.response?.data?.detail?.message || error?.message || fallback;
const statusTone = (status?: string | null) => {
  const value = String(status || "").toUpperCase();
  if (value === "APPROVED" || value === "CONNECTED") return "bg-lime-500/20 text-lime-100 border-lime-400/30";
  if (value === "PENDING") return "bg-amber-500/20 text-amber-100 border-amber-400/30";
  if (value === "REJECTED" || value === "REVOKED" || value === "ERROR" || value === "DISCONNECTED") return "bg-red-500/20 text-red-100 border-red-400/30";
  return "bg-white/10 text-purple-100 border-white/10";
};
const formatMoney = (value?: number | string | null, currency = "USD") => {
  if (value === null || value === undefined || value === "") return "—";
  const amount = Number(value);
  if (Number.isNaN(amount)) return "—";
  const code = String(currency || "USD").toUpperCase();
  if (code === "INR") return `₹${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  if (code === "USD") return `${amount < 0 ? "-" : ""}$${Math.abs(amount).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  return `${code} ${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
};

type DecisionAction = "approve" | "reject" | "revoke";
type DecisionState = {
  row: LiveTradingApproval;
  action: DecisionAction;
  approved_markets: string;
  max_daily_loss: string;
  max_order_value: string;
  max_trades_per_day: string;
  notes: string;
  confirm_revoke: boolean;
};

function ActionModal({ state, setState, onSubmit, busy }: { state: DecisionState; setState: (s: DecisionState | null) => void; onSubmit: () => void; busy: boolean }) {
  const isApprove = state.action === "approve";
  const isReject = state.action === "reject";
  const isRevoke = state.action === "revoke";
  const title = isApprove ? "Approve broker deployment access" : isReject ? "Reject approval request" : "Revoke broker deployment access";
  const icon = isApprove ? <ShieldCheck className="h-5 w-5 text-lime-200" /> : isReject ? <ShieldX className="h-5 w-5 text-red-200" /> : <AlertTriangle className="h-5 w-5 text-amber-200" />;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-3xl border border-white/10 bg-[#211044] p-6 shadow-2xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">{icon}<div><h2 className="text-xl font-bold text-white">{title}</h2><p className="text-sm text-purple-200">{state.row.broker_name || state.row.account_label || "Broker"} • {state.row.broker_mode || state.row.mode || "—"}</p></div></div>
          <button onClick={() => setState(null)} className="rounded-full bg-white/10 p-2 text-purple-100 hover:bg-white/20"><X className="h-4 w-4" /></button>
        </div>

        {isApprove && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-purple-100 md:col-span-2">Approved markets<input value={state.approved_markets} onChange={(e) => setState({ ...state, approved_markets: e.target.value })} className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-3 text-white outline-none" placeholder="ALL" /><span className="block text-xs text-purple-300">Use ALL to allow every instrument. Market restriction is informational unless strict market scope is enabled.</span></label>
            <label className="space-y-2 text-sm text-purple-100">Max daily loss<input value={state.max_daily_loss} onChange={(e) => setState({ ...state, max_daily_loss: e.target.value })} className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-3 text-white outline-none" /></label>
            <label className="space-y-2 text-sm text-purple-100">Max order value<input value={state.max_order_value} onChange={(e) => setState({ ...state, max_order_value: e.target.value })} className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-3 text-white outline-none" /></label>
            <label className="space-y-2 text-sm text-purple-100">Max trades per day<input value={state.max_trades_per_day} onChange={(e) => setState({ ...state, max_trades_per_day: e.target.value })} className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-3 text-white outline-none" /></label>
          </div>
        )}

        <label className="mt-4 block space-y-2 text-sm text-purple-100">{isReject ? "Reject notes (required)" : "Admin notes"}<textarea value={state.notes} onChange={(e) => setState({ ...state, notes: e.target.value })} className="min-h-[110px] w-full rounded-xl border border-white/10 bg-white/10 px-3 py-3 text-white outline-none" placeholder={isReject ? "Explain why this request is rejected" : "Admin notes"} /></label>

        {isRevoke && <label className="mt-4 flex items-start gap-3 rounded-xl border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100"><input className="mt-1" type="checkbox" checked={state.confirm_revoke} onChange={(e) => setState({ ...state, confirm_revoke: e.target.checked })} /><span>I confirm revoke should disable future deployment creation/start for this broker approval. Old deployments are not deleted.</span></label>}

        <div className="mt-6 flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => setState(null)} className="border-white/10 bg-white/5 text-white hover:bg-white/10">Cancel</Button>
          <Button disabled={busy || (isReject && !state.notes.trim()) || (isRevoke && !state.confirm_revoke)} onClick={onSubmit} className={isApprove ? "bg-lime-500 text-slate-950 hover:bg-lime-400" : isReject ? "bg-red-500 text-white hover:bg-red-400" : "bg-amber-500 text-slate-950 hover:bg-amber-400"}>{busy ? "Saving..." : isApprove ? "Approve" : isReject ? "Reject" : "Revoke"}</Button>
        </div>
      </div>
    </div>
  );
}

export default function AdminLiveApprovalsPage() {
  const { showToast } = useToast();
  const [rows, setRows] = useState<LiveTradingApproval[]>([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [decision, setDecision] = useState<DecisionState | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      setRows(await liveTradingApi.adminListLiveApprovals(status || undefined));
    } catch (error: any) {
      showToast(errorMessage(error, "Failed to load live approvals"), "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openDecision = (row: LiveTradingApproval, action: DecisionAction) => {
    setDecision({
      row,
      action,
      approved_markets: (row.approved_markets && row.approved_markets.length ? row.approved_markets : ["ALL"]).join(", "),
      max_daily_loss: String(row.max_daily_loss || ""),
      max_order_value: String(row.max_order_value || ""),
      max_trades_per_day: String(row.max_trades_per_day || ""),
      notes: action === "approve" ? `Approved ${row.broker_mode || row.mode || "broker"} account after review` : "",
      confirm_revoke: false,
    });
  };

  const submitDecision = async () => {
    if (!decision) return;
    if (decision.action === "reject" && !decision.notes.trim()) return showToast("Reject notes are required", "error");
    if (decision.action === "revoke" && !decision.confirm_revoke) return showToast("Confirm revoke before continuing", "error");
    try {
      setBusyId(decision.row.id);
      const payload: Record<string, unknown> = { notes: decision.notes.trim() || "Admin decision" };
      if (decision.action === "approve") {
        payload.approved_markets = decision.approved_markets.split(",").map((m) => m.trim()).filter(Boolean).length ? decision.approved_markets.split(",").map((m) => m.trim()).filter(Boolean) : ["ALL"];
        payload.max_daily_loss = decision.max_daily_loss ? Number(decision.max_daily_loss) : null;
        payload.max_order_value = decision.max_order_value ? Number(decision.max_order_value) : null;
        payload.max_trades_per_day = decision.max_trades_per_day ? Number(decision.max_trades_per_day) : null;
      }
      await liveTradingApi.adminDecideLiveApproval(decision.row.id, decision.action, payload);
      showToast(`Approval ${decision.action} completed`, "success");
      setDecision(null);
      await load();
    } catch (error: any) {
      showToast(errorMessage(error, "Approval action failed"), "error");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <PageShell>
      <PageHeader
        title="Admin Broker Deployment Approvals"
        subtitle="Approve DEMO or LIVE broker deployments, edit risk limits, and revoke future deployment access without deleting old deployments."
        actions={<div className="flex gap-2"><select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-white/10 bg-purple-950 px-3 py-2 text-sm text-white"><option value="">All</option><option value="PENDING">Pending</option><option value="APPROVED">Approved</option><option value="REJECTED">Rejected</option><option value="REVOKED">Revoked</option></select><Button onClick={load} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="h-4 w-4" />Refresh</Button></div>}
      />

      <div className="mb-5 grid grid-cols-1 gap-4 md:grid-cols-3">
        <GlassCard className="p-4" hoverEffect={false}><div className="text-sm text-purple-300">Pending Review</div><div className="mt-1 text-2xl font-bold text-white">{rows.filter((r) => r.status === "PENDING").length}</div></GlassCard>
        <GlassCard className="p-4" hoverEffect={false}><div className="text-sm text-purple-300">Approved</div><div className="mt-1 text-2xl font-bold text-lime-200">{rows.filter((r) => r.status === "APPROVED").length}</div></GlassCard>
        <GlassCard className="p-4" hoverEffect={false}><div className="text-sm text-purple-300">Rejected / Revoked</div><div className="mt-1 text-2xl font-bold text-amber-200">{rows.filter((r) => ["REJECTED", "REVOKED"].includes(String(r.status))).length}</div></GlassCard>
      </div>

      <GlassCard className="p-6" hoverEffect={false}>
        {loading ? <p className="text-purple-100">Loading approvals...</p> : rows.length === 0 ? <p className="text-purple-200">No live approval requests found.</p> : (
          <div className="admin-table-scroll overflow-x-auto">
            <table className="admin-data-table w-full min-w-[1450px] text-left text-sm">
              <thead className="text-purple-200"><tr><th className="py-3">Created</th><th>User</th><th>Broker account</th><th>Broker provider</th><th>Mode</th><th>Broker status</th><th>Requested markets</th><th>Requested limits</th><th>Approval status</th><th>Notes</th><th className="text-right">Actions</th></tr></thead>
              <tbody className="divide-y divide-white/10">{rows.map((row) => {
                const mode = row.broker_mode || row.mode || "—";
                const provider = row.broker_provider || row.broker_code || "—";
                const currency = row.currency || "USD";
                return <tr key={row.id} className="text-purple-50"><td className="py-3">{date(row.created_at)}</td><td><div className="font-semibold text-white">{row.user_name || "User"}</div><div className="text-xs text-purple-300">{row.user_email || row.user_id}</div></td><td><div className="font-semibold text-white">{row.account_label || row.broker_name || "Broker account"}</div><div className="text-xs text-purple-300">{row.login_id || row.server_name || row.broker_account_id || "—"}</div></td><td>{provider}</td><td><Badge className={statusTone(mode)}>{mode}</Badge></td><td><Badge className={statusTone(row.broker_status)}>{row.broker_status || "—"}</Badge></td><td>{(row.approved_markets || []).join(", ") || "—"}</td><td><div>{formatMoney(row.max_daily_loss, currency)} daily</div><div className="text-xs text-purple-300">{formatMoney(row.max_order_value, currency)} / order</div><div className="text-xs text-purple-300">{row.max_trades_per_day || "—"} trades/day</div></td><td><Badge className={statusTone(row.status)}>{row.status}</Badge><div className="mt-1 text-xs text-purple-300">Disclaimer: {date(row.risk_disclaimer_accepted_at)}</div></td><td className="max-w-[220px] truncate">{row.notes || "—"}</td><td><div className="flex justify-end gap-2"><Button size="sm" disabled={busyId === row.id} onClick={() => openDecision(row, "approve")} className="gap-1 bg-lime-500 text-slate-950 hover:bg-lime-400"><CheckCircle2 className="h-3.5 w-3.5" />Approve</Button><Button size="sm" disabled={busyId === row.id} onClick={() => openDecision(row, "reject")} variant="outline" className="gap-1 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><ShieldX className="h-3.5 w-3.5" />Reject</Button><Button size="sm" disabled={busyId === row.id} onClick={() => openDecision(row, "revoke")} variant="outline" className="border-yellow-400/30 bg-yellow-500/10 text-yellow-100 hover:bg-yellow-500/20">Revoke</Button></div></td></tr>;
              })}</tbody>
            </table>
          </div>
        )}
      </GlassCard>

      {decision && <ActionModal state={decision} setState={setDecision} onSubmit={submitDecision} busy={busyId === decision.row.id} />}
    </PageShell>
  );
}
