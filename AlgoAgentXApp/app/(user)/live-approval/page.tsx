"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, RefreshCw, ShieldCheck, WalletCards } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, LiveTradingApproval } from "@/types/live-trading";

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
const brokerLabel = (broker: BrokerAccount) => `${broker.broker_name || broker.broker_code || "Broker"} • ${broker.account_label || "Account"} • ${broker.mode || "—"} • ${broker.status || "—"}`;

export default function LiveApprovalPage() {
  const { showToast } = useToast();
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [approvals, setApprovals] = useState<LiveTradingApproval[]>([]);
  const [brokerId, setBrokerId] = useState("");
  const [markets, setMarkets] = useState("ALL");
  const [maxDailyLoss, setMaxDailyLoss] = useState("1000");
  const [maxOrderValue, setMaxOrderValue] = useState("5000");
  const [maxTrades, setMaxTrades] = useState("10");
  const [accepted, setAccepted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const connectedBrokers = useMemo(() => brokers.filter((b) => String(b.status).toUpperCase() === "CONNECTED"), [brokers]);
  const selectedBroker = connectedBrokers.find((b) => b.id === brokerId);
  const existingForBroker = approvals.find((a) => a.broker_account_id === brokerId && ["PENDING", "APPROVED"].includes(String(a.status).toUpperCase()));
  const currency = selectedBroker ? "USD" : "USD";
  const submitDisabled = busy || !brokerId || !accepted || existingForBroker?.status === "PENDING" || existingForBroker?.status === "APPROVED";

  const load = async () => {
    try {
      setLoading(true);
      const [brokerRows, approvalRows] = await Promise.all([liveTradingApi.listBrokerAccounts(), liveTradingApi.listLiveApprovals()]);
      setBrokers(brokerRows);
      setApprovals(approvalRows);
      const firstConnected = brokerRows.find((row) => String(row.status).toUpperCase() === "CONNECTED");
      if (!brokerId && firstConnected) setBrokerId(firstConnected.id);
    } catch (error: any) {
      showToast(errorMessage(error, "Failed to load broker approval data"), "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!brokerId) return showToast("Select a connected broker account first", "error");
    if (existingForBroker?.status === "APPROVED") return showToast("This broker is already approved for deployment", "error");
    if (existingForBroker?.status === "PENDING") return showToast("Approval already pending for this broker", "error");
    if (!accepted) return showToast("Accept the risk disclaimer first", "error");
    try {
      setBusy(true);
      await liveTradingApi.requestLiveApproval({
        broker_account_id: brokerId,
        requested_markets: markets.split(",").map((m) => m.trim()).filter(Boolean),
        max_daily_loss: Number(maxDailyLoss || 0),
        max_order_value: Number(maxOrderValue || 0),
        max_trades_per_day: Number(maxTrades || 0),
        risk_disclaimer_accepted: accepted,
      });
      showToast("Broker approval request submitted", "success");
      setAccepted(false);
      await load();
    } catch (error: any) {
      showToast(errorMessage(error, "Failed to submit broker approval request"), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <PageShell>
      <PageHeader
        title="Broker Deployment Approval"
        subtitle="Request approval before using broker-based DEMO or LIVE execution."
        actions={<Button onClick={load} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="h-4 w-4" />Refresh</Button>}
      />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[0.85fr_1.15fr]">
        <div className="space-y-5">
          <GlassCard className="p-6" hoverEffect={false}>
            <div className="flex items-start gap-3">
              <div className="rounded-2xl bg-lime-400/15 p-3 text-lime-200"><ShieldCheck className="h-6 w-6" /></div>
              <div>
                <h2 className="text-xl font-bold text-white">Approval requirement</h2>
                <p className="mt-2 text-sm leading-6 text-purple-100/80">Approval unlocks DEMO or LIVE broker deployments depending on broker account mode. LIVE execution requires stricter admin approval, broker connection verification, risk limits, and risk disclaimer acceptance.</p>
              </div>
            </div>
            <div className="mt-5 grid grid-cols-1 gap-3 text-sm md:grid-cols-3 xl:grid-cols-1">
              <div className="rounded-xl border border-white/10 bg-white/5 p-3"><div className="text-purple-300">PAPER</div><div className="font-semibold text-white">No approval needed</div></div>
              <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/10 p-3"><div className="text-cyan-200">DEMO</div><div className="font-semibold text-white">Approved connected demo broker</div></div>
              <div className="rounded-xl border border-lime-400/20 bg-lime-400/10 p-3"><div className="text-lime-200">LIVE</div><div className="font-semibold text-white">Approved connected live broker</div></div>
            </div>
          </GlassCard>

          <GlassCard className="p-6" hoverEffect={false}>
            <div className="mb-4 flex items-center gap-3"><WalletCards className="h-5 w-5 text-lime-300" /><h2 className="text-xl font-bold text-white">Broker account selector</h2></div>
            <label className="space-y-2 text-sm text-purple-100">
              <span>Connected broker account</span>
              <select value={brokerId} onChange={(e) => setBrokerId(e.target.value)} className="w-full rounded-xl border border-white/10 bg-purple-950 px-3 py-3 text-white outline-none">
                <option value="">Select connected broker account</option>
                {connectedBrokers.map((b) => <option key={b.id} value={b.id}>{brokerLabel(b)}</option>)}
              </select>
            </label>
            {!loading && connectedBrokers.length === 0 && <p className="mt-3 rounded-xl border border-amber-400/25 bg-amber-400/10 p-3 text-sm text-amber-100">Connect broker first. Disconnected brokers cannot be submitted for approval.</p>}
            {selectedBroker && <div className="mt-3 flex flex-wrap gap-2"><Badge className={statusTone(selectedBroker.mode)}>{selectedBroker.mode}</Badge><Badge className={statusTone(selectedBroker.status)}>{selectedBroker.status}</Badge>{existingForBroker?.status && <Badge className={statusTone(existingForBroker.status)}>{existingForBroker.status}</Badge>}</div>}
            {existingForBroker?.status === "PENDING" && <p className="mt-3 rounded-xl border border-amber-400/25 bg-amber-400/10 p-3 text-sm text-amber-100">Approval already pending for this broker.</p>}
            {existingForBroker?.status === "APPROVED" && <p className="mt-3 rounded-xl border border-lime-400/25 bg-lime-400/10 p-3 text-sm text-lime-100">This broker is already approved for deployment.</p>}
          </GlassCard>
        </div>

        <GlassCard className="p-6" hoverEffect={false}>
          <h2 className="text-xl font-bold text-white">Risk limits request form</h2>
          <p className="mt-1 text-sm text-purple-200">Admin can approve these values or reduce them during review.</p>
          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-purple-100">Requested markets<input value={markets} onChange={(e) => setMarkets(e.target.value)} className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-3 text-white outline-none" placeholder="ALL" /><span className="block text-xs text-purple-300">ALL allows every instrument for this broker account. Admin can still control risk limits.</span></label>
            <label className="space-y-2 text-sm text-purple-100">Max daily loss<input value={maxDailyLoss} onChange={(e) => setMaxDailyLoss(e.target.value)} className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-3 text-white outline-none" /></label>
            <label className="space-y-2 text-sm text-purple-100">Max order value<input value={maxOrderValue} onChange={(e) => setMaxOrderValue(e.target.value)} className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-3 text-white outline-none" /></label>
            <label className="space-y-2 text-sm text-purple-100">Max trades per day<input value={maxTrades} onChange={(e) => setMaxTrades(e.target.value)} className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-3 text-white outline-none" /></label>
          </div>
          <label className="mt-5 flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100"><input className="mt-1" type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} /><span>I accept the broker execution risk disclaimer and understand losses can occur in DEMO or LIVE broker mode.</span></label>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Button disabled={submitDisabled} onClick={submit} className="bg-lime-500 text-slate-950 hover:bg-lime-400">{busy ? "Submitting..." : "Submit Approval Request"}</Button>
            <Link href="/live-trading/new" className="text-sm font-semibold text-lime-200 underline">Back to deployment form</Link>
          </div>
          {existingForBroker?.status === "PENDING" && <p className="mt-3 flex gap-2 text-sm text-amber-100"><AlertTriangle className="h-4 w-4" />Submit is disabled because approval is already pending for this broker.</p>}
          {existingForBroker?.status === "APPROVED" && <p className="mt-3 flex gap-2 text-sm text-lime-100"><CheckCircle2 className="h-4 w-4" />Submit is disabled because this broker is already approved.</p>}
        </GlassCard>
      </div>

      <GlassCard className="mt-6 p-6" hoverEffect={false}>
        <h2 className="mb-4 text-xl font-bold text-white">Approval Status</h2>
        {loading ? <p className="text-purple-100">Loading...</p> : approvals.length === 0 ? <p className="text-purple-200">No broker approval requests yet.</p> : (
          <div className="responsive-table-wrapper overflow-x-auto">
            <table className="w-full min-w-[1100px] text-left text-sm">
              <thead className="text-purple-200"><tr><th className="py-3">Created</th><th>Broker</th><th>Mode</th><th>Broker Status</th><th>Approval Status</th><th>Markets</th><th>Max Daily Loss</th><th>Max Order Value</th><th>Trades/Day</th><th>Notes</th></tr></thead>
              <tbody className="divide-y divide-white/10">{approvals.map((a) => {
                const rowCurrency = a.currency || currency || "USD";
                return <tr key={a.id} className="text-purple-50"><td className="py-3">{date(a.created_at)}</td><td><div className="font-semibold text-white">{a.broker_name || a.account_label || "Broker"}</div><div className="text-xs text-purple-300">{a.broker_code || a.broker_provider || "—"}</div></td><td>{a.broker_mode || a.mode || "—"}</td><td><Badge className={statusTone(a.broker_status)}>{a.broker_status || "—"}</Badge></td><td><Badge className={statusTone(a.status)}>{a.status}</Badge></td><td>{(a.approved_markets || []).join(", ") || "—"}</td><td>{formatMoney(a.max_daily_loss, rowCurrency)}</td><td>{formatMoney(a.max_order_value, rowCurrency)}</td><td>{a.max_trades_per_day || "—"}</td><td>{a.notes || "—"}</td></tr>;
              })}</tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </PageShell>
  );
}
