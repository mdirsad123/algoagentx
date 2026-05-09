"use client";

import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, LiveTradingApproval } from "@/types/live-trading";

const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");

export default function LiveApprovalPage() {
  const { showToast } = useToast();
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [approvals, setApprovals] = useState<LiveTradingApproval[]>([]);
  const [brokerId, setBrokerId] = useState("");
  const [markets, setMarkets] = useState("FOREX,INDIAN_EQUITY");
  const [maxDailyLoss, setMaxDailyLoss] = useState("1000");
  const [maxOrderValue, setMaxOrderValue] = useState("5000");
  const [maxTrades, setMaxTrades] = useState("10");
  const [accepted, setAccepted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const [b, a] = await Promise.all([liveTradingApi.listBrokerAccounts(), liveTradingApi.listLiveApprovals()]);
      setBrokers(b);
      setApprovals(a);
      if (!brokerId && b[0]) setBrokerId(b[0].id);
    } catch (error: any) {
      showToast(error.message || "Failed to load live approval", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!accepted) {
      showToast("Accept the risk disclaimer first", "error");
      return;
    }
    try {
      setBusy(true);
      await liveTradingApi.requestLiveApproval({
        broker_account_id: brokerId || null,
        requested_markets: markets.split(",").map((m) => m.trim()).filter(Boolean),
        max_daily_loss: Number(maxDailyLoss || 0),
        max_order_value: Number(maxOrderValue || 0),
        max_trades_per_day: Number(maxTrades || 0),
        risk_disclaimer_accepted: accepted,
      });
      showToast("Live approval request submitted", "success");
      await load();
    } catch (error: any) {
      showToast(error.message || "Failed to submit live approval request", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <PageShell>
      <PageHeader title="Live Trading Approval" subtitle="Request admin approval before any real-money trading is enabled." />

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="mb-4 flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-lime-300" /><h2 className="text-xl font-bold text-lime-300">Request Live Approval</h2></div>
        <p className="mb-4 rounded-xl border border-yellow-400/20 bg-yellow-400/10 p-3 text-sm text-yellow-100">LIVE trading is not automatically enabled. Admin review, broker verification, strategy approval, risk limits and disclaimer acceptance are required.</p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="text-sm text-purple-100">Broker account<select value={brokerId} onChange={(e) => setBrokerId(e.target.value)} className="mt-1 w-full rounded-lg border border-white/10 bg-purple-950 px-3 py-2 text-white"><option value="">Any broker account</option>{brokers.map((b) => <option key={b.id} value={b.id}>{b.account_label} • {b.mode} • {b.status}</option>)}</select></label>
          <label className="text-sm text-purple-100">Requested markets<input value={markets} onChange={(e) => setMarkets(e.target.value)} className="mt-1 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white" /></label>
          <label className="text-sm text-purple-100">Max daily loss<input value={maxDailyLoss} onChange={(e) => setMaxDailyLoss(e.target.value)} className="mt-1 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white" /></label>
          <label className="text-sm text-purple-100">Max order value<input value={maxOrderValue} onChange={(e) => setMaxOrderValue(e.target.value)} className="mt-1 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white" /></label>
          <label className="text-sm text-purple-100">Max trades per day<input value={maxTrades} onChange={(e) => setMaxTrades(e.target.value)} className="mt-1 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white" /></label>
          <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100"><input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} /> I accept the live trading risk disclaimer.</label>
        </div>
        <Button disabled={busy} onClick={submit} className="mt-4 bg-lime-500 text-slate-950 hover:bg-lime-400">Submit Live Approval Request</Button>
      </GlassCard>

      <GlassCard className="p-6" hoverEffect={false}>
        <h2 className="mb-4 text-xl font-bold text-white">Approval Status</h2>
        {loading ? <p className="text-purple-100">Loading...</p> : approvals.length === 0 ? <p className="text-purple-200">No live approval requests yet.</p> : <div className="responsive-table-wrapper overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="text-purple-200"><tr><th>Created</th><th>Broker</th><th>Status</th><th>Markets</th><th>Max Daily Loss</th><th>Max Order Value</th><th>Trades/Day</th><th>Notes</th></tr></thead><tbody className="divide-y divide-white/10">{approvals.map((a) => <tr key={a.id} className="text-purple-50"><td className="py-3">{date(a.created_at)}</td><td>{a.broker_name || "Any"}</td><td><Badge>{a.status}</Badge></td><td>{(a.approved_markets || []).join(", ")}</td><td>{a.max_daily_loss || "—"}</td><td>{a.max_order_value || "—"}</td><td>{a.max_trades_per_day || "—"}</td><td>{a.notes || "—"}</td></tr>)}</tbody></table></div>}
      </GlassCard>
    </PageShell>
  );
}
