"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Eye, Pause, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, LivePosition, StrategyCatalogItem, StrategyDeployment } from "@/types/live-trading";

const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");
const money = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
function StatusBadge({ value }: { value?: string }) { return <Badge className="border-lime-400/30 bg-lime-400/20 text-lime-100">{value || "—"}</Badge>; }

export default function AdminLiveTradingPage() {
  const { showToast } = useToast();
  const [deployments, setDeployments] = useState<StrategyDeployment[]>([]);
  const [positions, setPositions] = useState<LivePosition[]>([]);
  const [strategies, setStrategies] = useState<StrategyCatalogItem[]>([]);
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      const [d, p, s, b] = await Promise.all([liveTradingApi.listDeployments(), liveTradingApi.listOpenPositions(), liveTradingApi.listStrategies(), liveTradingApi.listBrokerAccounts()]);
      setDeployments(d); setPositions(p); setStrategies(s); setBrokers(b);
    } catch (error: any) { showToast(error.message || "Failed to load admin monitor", "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const action = async (id: string, type: "pause" | "stop") => {
    try { setBusyId(id); if (type === "pause") await liveTradingApi.pauseDeployment(id); else await liveTradingApi.stopDeployment(id); showToast(`Force ${type} completed`, "success"); await load(); }
    catch (error: any) { showToast(error.message || `Failed to ${type}`, "error"); }
    finally { setBusyId(null); }
  };

  const summary = useMemo(() => ({ running: deployments.filter((d) => d.status === "RUNNING").length, open: positions.length }), [deployments, positions]);
  const strategyName = (id: string) => strategies.find((s) => s.id === id)?.name || id;
  const brokerName = (id?: string | null) => brokers.find((b) => b.id === id)?.account_label || (id ? id : "—");

  return (
    <PageShell>
      <PageHeader title="Admin Live Trading Monitor" subtitle="Monitor all users' PAPER and DEMO live trading deployments." />
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3"><GlassCard className="p-5"><p className="text-sm text-purple-200">Total deployments</p><p className="mt-2 text-3xl font-bold text-white">{deployments.length}</p></GlassCard><GlassCard className="p-5"><p className="text-sm text-purple-200">Running</p><p className="mt-2 text-3xl font-bold text-lime-300">{summary.running}</p></GlassCard><GlassCard className="p-5"><p className="text-sm text-purple-200">Open positions</p><p className="mt-2 text-3xl font-bold text-white">{summary.open}</p></GlassCard></div>
      {loading ? <GlassCard className="p-6 text-purple-100">Loading deployments...</GlassCard> : deployments.length === 0 ? <EmptyState title="No record found" description="No live trading deployments exist yet." /> : (
        <GlassCard className="overflow-hidden" hoverEffect={false}><div className="overflow-x-auto"><table className="w-full min-w-[1100px] text-left text-sm"><thead className="border-b border-white/10 bg-white/5 text-purple-100"><tr><th className="px-4 py-3">User</th><th className="px-4 py-3">Strategy</th><th className="px-4 py-3">Broker</th><th className="px-4 py-3">Instrument</th><th className="px-4 py-3">Timeframe</th><th className="px-4 py-3">Mode</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Last heartbeat</th><th className="px-4 py-3">Open positions</th><th className="px-4 py-3">Today PnL</th><th className="px-4 py-3 text-right">Actions</th></tr></thead><tbody className="divide-y divide-white/10">{deployments.map((d) => { const dPositions = positions.filter((p) => p.deployment_id === d.id); const pnl = dPositions.reduce((sum, p) => sum + Number(p.unrealized_pnl || 0) + Number(p.realized_pnl || 0), 0); return <tr key={d.id} className="text-purple-50 hover:bg-white/5"><td className="px-4 py-4 font-mono text-xs">{d.user_id || "—"}</td><td className="px-4 py-4">{strategyName(d.strategy_id)}</td><td className="px-4 py-4">{brokerName(d.broker_account_id)}</td><td className="px-4 py-4">{d.instrument}</td><td className="px-4 py-4">{d.timeframe}</td><td className="px-4 py-4"><Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">{d.mode}</Badge></td><td className="px-4 py-4"><StatusBadge value={d.status} /></td><td className="px-4 py-4">{date(d.last_heartbeat_at)}</td><td className="px-4 py-4">{dPositions.length}</td><td className="px-4 py-4">₹{money(pnl)}</td><td className="px-4 py-4"><div className="flex justify-end gap-2"><Link href={`/admin/live-trading/${d.id}`}><Button size="sm" variant="outline" className="h-8 gap-1 border-white/10 bg-white/5 text-white hover:bg-white/10"><Eye className="h-3.5 w-3.5" />View</Button></Link><Button size="sm" disabled={busyId === d.id} onClick={() => action(d.id, "pause")} className="h-8 gap-1 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-3.5 w-3.5" />Force Pause</Button><Button size="sm" disabled={busyId === d.id} onClick={() => action(d.id, "stop")} variant="outline" className="h-8 gap-1 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-3.5 w-3.5" />Force Stop</Button></div></td></tr>; })}</tbody></table></div></GlassCard>
      )}
    </PageShell>
  );
}
