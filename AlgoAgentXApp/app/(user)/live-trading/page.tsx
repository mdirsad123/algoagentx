"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Eye, Pause, Play, Plus, ShieldAlert, ShieldCheck, Square, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { LiveDeploymentSummary, StrategyCatalogItem, StrategyDeployment } from "@/types/live-trading";

const money = (value: unknown, currency?: string | null) => {
  const amount = Number(value || 0);
  const code = currency?.toUpperCase();
  if (code === "USD" || code === "INR" || code === "EUR" || code === "GBP") {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: code, maximumFractionDigits: 2 }).format(amount);
  }
  const formatted = amount.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return code ? `${formatted} ${code}` : formatted;
};
const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");

type LiveAccessStatus = {
  allowed: boolean;
  requires_subscription: boolean;
  code?: string | null;
  message?: string;
  recommended_coupon?: string | null;
  subscription?: Record<string, unknown> | null;
};

const extractGateDetail = (error: any): LiveAccessStatus | null => {
  const detail = error?.response?.data?.detail;
  if (detail && typeof detail === "object" && detail.code === "SUBSCRIPTION_REQUIRED") {
    return {
      allowed: false,
      requires_subscription: true,
      code: detail.code,
      message: detail.message || "Active subscription required to deploy live strategies.",
      recommended_coupon: detail.recommended_coupon || null,
    };
  }
  return null;
};

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    RUNNING: "border-lime-400/30 bg-lime-400/20 text-lime-100",
    PAUSED: "border-yellow-400/30 bg-yellow-400/20 text-yellow-100",
    STOPPED: "border-slate-400/30 bg-slate-400/20 text-slate-100",
    ERROR: "border-red-400/30 bg-red-400/20 text-red-100",
    DRAFT: "border-purple-300/30 bg-purple-400/20 text-purple-100",
  };
  return <Badge className={map[status] || map.DRAFT}>{status}</Badge>;
}

export default function LiveTradingPage() {
  const { showToast } = useToast();
  const router = useRouter();
  const [deployments, setDeployments] = useState<StrategyDeployment[]>([]);
  const [summaries, setSummaries] = useState<Record<string, LiveDeploymentSummary>>({});
  const [strategies, setStrategies] = useState<StrategyCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [accessStatus, setAccessStatus] = useState<LiveAccessStatus | null>(null);
  const [showSubscribeModal, setShowSubscribeModal] = useState(false);

  const strategyName = (id: string) => strategies.find((s) => s.id === id)?.name || summaries[id]?.deployment?.strategy_name || id;

  const load = async () => {
    try {
      setLoading(true);
      const [deploymentRows, strategyRows, access] = await Promise.all([
        liveTradingApi.listDeployments(),
        liveTradingApi.listStrategies(),
        liveTradingApi.getLiveAccessStatus().catch(() => null),
      ]);
      if (access) setAccessStatus(access);
      setDeployments(deploymentRows);
      setStrategies(strategyRows);
      const pairs = await Promise.all(deploymentRows.map(async (d) => [d.id, await liveTradingApi.getDeploymentSummary(d.id)] as const));
      setSummaries(Object.fromEntries(pairs));
    } catch (error: any) {
      showToast(error.message || "Failed to load live trading dashboard", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const runAction = async (id: string, action: "start" | "pause" | "stop") => {
    try {
      setBusyId(id);
      if (action === "start") await liveTradingApi.startDeployment(id);
      if (action === "pause") await liveTradingApi.pauseDeployment(id);
      if (action === "stop") await liveTradingApi.stopDeployment(id);
      showToast(`Deployment ${action} action completed`, "success");
      await load();
    } catch (error: any) {
      const gate = extractGateDetail(error);
      if (gate) {
        setAccessStatus(gate);
        setShowSubscribeModal(true);
      } else {
        showToast(error.message || `Failed to ${action} deployment`, "error");
      }
    } finally {
      setBusyId(null);
    }
  };

  const summary = useMemo(() => {
    const rows = Object.values(summaries);
    return {
      running: deployments.filter((d) => d.status === "RUNNING").length,
      openPositions: rows.reduce((sum, s) => sum + Number(s.metrics?.open_positions || 0), 0),
      todayPnl: rows.reduce((sum, s) => sum + Number(s.metrics?.today_pnl || 0), 0),
      currency: rows.find((s) => s.metrics?.currency)?.metrics?.currency || null,
      todaySignals: rows.reduce((sum, s) => sum + Number(s.metrics?.signals_today || 0), 0),
      todayOrders: rows.reduce((sum, s) => sum + Number(s.metrics?.orders_today || 0), 0),
    };
  }, [deployments, summaries]);

  return (
    <PageShell>
      <PageHeader
        title="Live Trading"
        subtitle="Monitor PAPER and DEMO strategy deployments before real LIVE execution is enabled."
        actions={accessStatus?.allowed === false ? (
          <Button onClick={() => setShowSubscribeModal(true)} className="gap-2 border-0 bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white hover:from-fuchsia-400 hover:to-blue-400"><Plus className="h-4 w-4" />New Deployment</Button>
        ) : (
          <Link href="/live-trading/new"><Button className="gap-2 border-0 bg-gradient-to-r from-lime-400 to-emerald-500 text-slate-950 hover:from-lime-300 hover:to-emerald-400"><Plus className="h-4 w-4" />New Deployment</Button></Link>
        )}
      />


      <GlassCard className={`mb-6 rounded-3xl border p-5 ${accessStatus?.allowed === false ? "border-amber-300/25 bg-amber-400/10" : "border-lime-300/20 bg-lime-400/10"}`} hoverEffect={false}>
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            {accessStatus?.allowed === false ? <ShieldAlert className="mt-1 h-5 w-5 text-amber-200" /> : <ShieldCheck className="mt-1 h-5 w-5 text-lime-200" />}
            <div>
              <h3 className="font-semibold text-white">{accessStatus?.allowed === false ? "Subscription required for deployment" : "Live trading access enabled"}</h3>
              <p className="mt-1 text-sm text-purple-100/75">
                {accessStatus?.allowed === false
                  ? `Live trading deployment is available for active subscribers.${accessStatus.recommended_coupon ? ` Use coupon ${accessStatus.recommended_coupon} for discount.` : ""}`
                  : "Your live trading controls are available. Viewing, pausing, stopping, logs, and broker status remain safe at all times."}
              </p>
            </div>
          </div>
          {accessStatus?.allowed === false && <Button onClick={() => router.push("/pricing")} className="rounded-xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">View Plans</Button>}
        </div>
      </GlassCard>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-5">
        <GlassCard className="p-5"><p className="text-sm text-purple-200">Running deployments</p><p className="mt-2 text-3xl font-bold text-lime-300">{summary.running}</p></GlassCard>
        <GlassCard className="p-5"><p className="text-sm text-purple-200">Open positions</p><p className="mt-2 text-3xl font-bold text-white">{summary.openPositions}</p></GlassCard>
        <GlassCard className="p-5"><p className="text-sm text-purple-200">Today PnL</p><p className="mt-2 text-3xl font-bold text-white">{money(summary.todayPnl, summary.currency)}</p></GlassCard>
        <GlassCard className="p-5"><p className="text-sm text-purple-200">Signals today</p><p className="mt-2 text-3xl font-bold text-white">{summary.todaySignals}</p></GlassCard>
        <GlassCard className="p-5"><p className="text-sm text-purple-200">Orders today</p><p className="mt-2 text-3xl font-bold text-white">{summary.todayOrders}</p></GlassCard>
      </div>

      {loading ? <GlassCard className="p-6 text-purple-100">Loading live deployments...</GlassCard> : deployments.length === 0 ? <EmptyState title="No deployments yet" description="Create your first PAPER or DEMO deployment from a published strategy." action={accessStatus?.allowed === false ? <Button onClick={() => setShowSubscribeModal(true)} className="gap-2"><Zap className="h-4 w-4" />Create Deployment</Button> : <Link href="/live-trading/new"><Button className="gap-2"><Zap className="h-4 w-4" />Create Deployment</Button></Link>} /> : (
        <GlassCard className="overflow-hidden" hoverEffect={false}>
          <div className="overflow-x-auto"><table className="w-full min-w-[1250px] text-left text-sm"><thead className="border-b border-white/10 bg-white/5 text-purple-100"><tr><th className="px-4 py-3">Name</th><th className="px-4 py-3">Strategy</th><th className="px-4 py-3">Instrument</th><th className="px-4 py-3">Timeframe</th><th className="px-4 py-3">Mode</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Broker</th><th className="px-4 py-3">PnL</th><th className="px-4 py-3">Auto Runner</th><th className="px-4 py-3">Last Signal</th><th className="px-4 py-3 text-right">Actions</th></tr></thead><tbody className="divide-y divide-white/10">{deployments.map((deployment) => {
            const sm = summaries[deployment.id];
            return <tr key={deployment.id} className="text-purple-50 hover:bg-white/5"><td className="px-4 py-4 font-semibold text-white">{deployment.name}</td><td className="px-4 py-4">{strategyName(deployment.strategy_id)}</td><td className="px-4 py-4">{deployment.instrument}</td><td className="px-4 py-4">{deployment.timeframe}</td><td className="px-4 py-4"><Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">{deployment.mode}</Badge></td><td className="px-4 py-4"><StatusBadge status={deployment.status} /></td><td className="px-4 py-4">{sm?.broker ? `${sm.broker.account_label || "MT5"} (${sm.broker.status || "—"})` : "—"}</td><td className="px-4 py-4">{money(sm?.metrics?.today_pnl, sm?.metrics?.currency || sm?.broker?.currency)}</td><td className="px-4 py-4"><Badge className={deployment.auto_runner_enabled ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : "border-slate-400/30 bg-slate-400/20 text-slate-100"}>{deployment.auto_runner_enabled ? "ON" : "OFF"}</Badge><div className="mt-1 text-xs text-purple-300">{date(deployment.last_processed_candle_time)}</div></td><td className="px-4 py-4">{date(deployment.last_signal_at)}</td><td className="px-4 py-4"><div className="flex justify-end gap-2"><Button size="sm" disabled={busyId === deployment.id} onClick={() => runAction(deployment.id, "start")} className="h-8 gap-1 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-3.5 w-3.5" />Start</Button><Button size="sm" disabled={busyId === deployment.id} onClick={() => runAction(deployment.id, "pause")} className="h-8 gap-1 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-3.5 w-3.5" />Pause</Button><Button size="sm" disabled={busyId === deployment.id} onClick={() => runAction(deployment.id, "stop")} variant="outline" className="h-8 gap-1 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-3.5 w-3.5" />Stop</Button><Link href={`/live-trading/${deployment.id}`}><Button size="sm" variant="outline" className="h-8 gap-1 border-white/10 bg-white/5 text-white hover:bg-white/10"><Eye className="h-3.5 w-3.5" />View</Button></Link></div></td></tr>;
          })}</tbody></table></div>
        </GlassCard>
      )}


      {showSubscribeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-3xl border border-white/10 bg-gradient-to-br from-slate-950 via-purple-950 to-slate-900 p-6 shadow-2xl shadow-fuchsia-950/40">
            <div className="flex items-start gap-3">
              <div className="rounded-2xl bg-fuchsia-500/20 p-3 text-fuchsia-100"><ShieldAlert className="h-6 w-6" /></div>
              <div>
                <h2 className="text-2xl font-bold text-white">Subscription required</h2>
                <p className="mt-2 text-sm leading-6 text-purple-100/80">
                  Live trading deployment is available for active subscribers.
                  {accessStatus?.recommended_coupon ? ` Subscribe now and use coupon ${accessStatus.recommended_coupon} for discount.` : " Subscribe now to unlock deployment and start controls."}
                </p>
              </div>
            </div>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end">
              <Button variant="outline" onClick={() => setShowSubscribeModal(false)} className="border-white/10 bg-white/5 text-white hover:bg-white/10">Cancel</Button>
              {accessStatus?.recommended_coupon && (
                <Button onClick={() => router.push(`/billing/checkout?type=subscription&plan=PRO&period=MONTHLY&coupon=${encodeURIComponent(accessStatus.recommended_coupon || "")}`)} className="bg-gradient-to-r from-lime-400 to-emerald-500 text-slate-950">Apply Coupon</Button>
              )}
              <Button onClick={() => router.push("/pricing")} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">View Plans</Button>
            </div>
          </div>
        </div>
      )}

    </PageShell>
  );
}
