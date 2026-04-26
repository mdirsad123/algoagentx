"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Eye, Pause, Play, Plus, Square, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { LiveOrder, LivePosition, LiveSignal, StrategyCatalogItem, StrategyDeployment } from "@/types/live-trading";

const money = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");

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
  const [deployments, setDeployments] = useState<StrategyDeployment[]>([]);
  const [positions, setPositions] = useState<LivePosition[]>([]);
  const [signals, setSignals] = useState<LiveSignal[]>([]);
  const [orders, setOrders] = useState<LiveOrder[]>([]);
  const [strategies, setStrategies] = useState<StrategyCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const strategyName = (id: string) => strategies.find((s) => s.id === id)?.name || id;

  const load = async () => {
    try {
      setLoading(true);
      const [deploymentRows, positionRows, signalRows, orderRows, strategyRows] = await Promise.all([
        liveTradingApi.listDeployments(),
        liveTradingApi.listOpenPositions(),
        liveTradingApi.listSignals(),
        liveTradingApi.listOrders(),
        liveTradingApi.listStrategies(),
      ]);
      setDeployments(deploymentRows);
      setPositions(positionRows);
      setSignals(signalRows);
      setOrders(orderRows);
      setStrategies(strategyRows);
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
      showToast(error.message || `Failed to ${action} deployment`, "error");
    } finally {
      setBusyId(null);
    }
  };

  const summary = useMemo(() => {
    const today = new Date().toDateString();
    const todaySignals = signals.filter((s) => s.created_at && new Date(s.created_at).toDateString() === today).length;
    const todayOrders = orders.filter((o) => o.created_at && new Date(o.created_at).toDateString() === today).length;
    const todayPnl = positions.reduce((sum, p) => sum + Number(p.unrealized_pnl || 0) + Number(p.realized_pnl || 0), 0);
    return {
      running: deployments.filter((d) => d.status === "RUNNING").length,
      openPositions: positions.length,
      todayPnl,
      todaySignals,
      todayOrders,
    };
  }, [deployments, positions, signals, orders]);

  return (
    <PageShell>
      <PageHeader
        title="Live Trading"
        subtitle="Monitor PAPER and DEMO strategy deployments before real MT5 execution is enabled."
        actions={<Link href="/live-trading/new"><Button className="gap-2 border-0 bg-gradient-to-r from-lime-400 to-emerald-500 text-slate-950 hover:from-lime-300 hover:to-emerald-400"><Plus className="h-4 w-4" />New Deployment</Button></Link>}
      />

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-5">
        <GlassCard className="p-5"><p className="text-sm text-purple-200">Running deployments</p><p className="mt-2 text-3xl font-bold text-lime-300">{summary.running}</p></GlassCard>
        <GlassCard className="p-5"><p className="text-sm text-purple-200">Open positions</p><p className="mt-2 text-3xl font-bold text-white">{summary.openPositions}</p></GlassCard>
        <GlassCard className="p-5"><p className="text-sm text-purple-200">Today PnL</p><p className="mt-2 text-3xl font-bold text-white">₹{money(summary.todayPnl)}</p></GlassCard>
        <GlassCard className="p-5"><p className="text-sm text-purple-200">Signals today</p><p className="mt-2 text-3xl font-bold text-white">{summary.todaySignals}</p></GlassCard>
        <GlassCard className="p-5"><p className="text-sm text-purple-200">Orders today</p><p className="mt-2 text-3xl font-bold text-white">{summary.todayOrders}</p></GlassCard>
      </div>

      {loading ? (
        <GlassCard className="p-6 text-purple-100">Loading live deployments...</GlassCard>
      ) : deployments.length === 0 ? (
        <EmptyState title="No deployments yet" description="Create your first PAPER or DEMO deployment from a published strategy." action={<Link href="/live-trading/new"><Button className="gap-2"><Zap className="h-4 w-4" />Create Deployment</Button></Link>} />
      ) : (
        <GlassCard className="overflow-hidden" hoverEffect={false}>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-left text-sm">
              <thead className="border-b border-white/10 bg-white/5 text-purple-100">
                <tr>
                  <th className="px-4 py-3">Name</th><th className="px-4 py-3">Strategy</th><th className="px-4 py-3">Instrument</th><th className="px-4 py-3">Timeframe</th><th className="px-4 py-3">Mode</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">PnL</th><th className="px-4 py-3">Last Signal</th><th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {deployments.map((deployment) => (
                  <tr key={deployment.id} className="text-purple-50 hover:bg-white/5">
                    <td className="px-4 py-4 font-semibold text-white">{deployment.name}</td>
                    <td className="px-4 py-4">{strategyName(deployment.strategy_id)}</td>
                    <td className="px-4 py-4">{deployment.instrument}</td>
                    <td className="px-4 py-4">{deployment.timeframe}</td>
                    <td className="px-4 py-4"><Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">{deployment.mode}</Badge></td>
                    <td className="px-4 py-4"><StatusBadge status={deployment.status} /></td>
                    <td className="px-4 py-4">₹{money(positions.filter((p) => p.deployment_id === deployment.id).reduce((sum, p) => sum + Number(p.unrealized_pnl || 0) + Number(p.realized_pnl || 0), 0))}</td>
                    <td className="px-4 py-4">{date(deployment.last_signal_at)}</td>
                    <td className="px-4 py-4">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" disabled={busyId === deployment.id} onClick={() => runAction(deployment.id, "start")} className="h-8 gap-1 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-3.5 w-3.5" />Start</Button>
                        <Button size="sm" disabled={busyId === deployment.id} onClick={() => runAction(deployment.id, "pause")} className="h-8 gap-1 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-3.5 w-3.5" />Pause</Button>
                        <Button size="sm" disabled={busyId === deployment.id} onClick={() => runAction(deployment.id, "stop")} variant="outline" className="h-8 gap-1 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-3.5 w-3.5" />Stop</Button>
                        <Link href={`/live-trading/${deployment.id}`}><Button size="sm" variant="outline" className="h-8 gap-1 border-white/10 bg-white/5 text-white hover:bg-white/10"><Eye className="h-3.5 w-3.5" />View</Button></Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}
    </PageShell>
  );
}
