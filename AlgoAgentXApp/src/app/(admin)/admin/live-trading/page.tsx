"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Eye, Pause, RefreshCw, Square, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { AdminLiveDeploymentRow, AdminLiveDeploymentListResponse, DeploymentStatus, LiveMode } from "@/types/live-trading";

const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");
const money = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

function StatusBadge({ value }: { value?: string }) {
  const color = value === "RUNNING" ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : value === "PAUSED" ? "border-yellow-400/30 bg-yellow-400/20 text-yellow-100" : value === "ERROR" ? "border-red-400/30 bg-red-400/20 text-red-100" : "border-purple-300/30 bg-purple-400/20 text-purple-100";
  return <Badge className={color}>{value || "—"}</Badge>;
}

function Metric({ label, value, accent = false }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <GlassCard className="p-5" hoverEffect={false}>
      <p className="text-sm text-purple-200">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${accent ? "text-lime-300" : "text-white"}`}>{value}</p>
    </GlassCard>
  );
}

export default function AdminLiveTradingPage() {
  const { showToast } = useToast();
  const [data, setData] = useState<AdminLiveDeploymentListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [filters, setFilters] = useState<{ status: string; mode: string; instrument: string; timeframe: string }>({ status: "", mode: "", instrument: "", timeframe: "" });
  const rows = data?.rows || [];
  const summary = data?.summary;

  const load = async () => {
    try {
      setLoading(true);
      const cleanFilters = Object.fromEntries(Object.entries(filters).filter(([, value]) => Boolean(value)));
      setData(await liveTradingApi.adminListLiveDeployments(cleanFilters));
    } catch (error: any) {
      showToast(error.message || "Failed to load admin live trading monitor", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const action = async (row: AdminLiveDeploymentRow, type: "force-pause" | "force-stop") => {
    const reason = window.prompt(`Reason for ${type.replace("-", " ")}?`, "Admin control center action") || "Admin control center action";
    try {
      setBusyId(row.deployment_id);
      await liveTradingApi.adminControlDeployment(row.deployment_id, type, reason);
      showToast(type === "force-pause" ? "Deployment force paused" : "Deployment force stopped", "success");
      await load();
    } catch (error: any) {
      showToast(error.message || "Admin action failed", "error");
    } finally {
      setBusyId(null);
    }
  };

  const emergencyAction = async (type: "pause-demo" | "stop-all") => {
    const ok = window.confirm(type === "stop-all" ? "Force stop all active deployments?" : "Pause all running MT5 DEMO deployments?");
    if (!ok) return;
    try {
      setLoading(true);
      const result = type === "stop-all" ? await liveTradingApi.forceStopAllLive() : await liveTradingApi.pauseAllDemoLive();
      showToast(`Emergency action completed. Affected: `, "success");
      await load();
    } catch (error: any) {
      showToast(error.message || "Emergency action failed", "error");
    } finally {
      setLoading(false);
    }
  };

  const activeFilterCount = useMemo(() => Object.values(filters).filter(Boolean).length, [filters]);

  return (
    <PageShell>
      <PageHeader
        title="Admin Live Execution Control Center"
        subtitle="Monitor and control all users' PAPER and MT5 DEMO execution. No live chart here."
        actions={<div className="flex flex-wrap gap-2"><Link href="/admin/live-settings"><Button variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><ShieldAlert className="h-4 w-4" />Safety Settings</Button></Link><Button onClick={() => emergencyAction("pause-demo")} className="gap-2 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-4 w-4" />Pause All Demo</Button><Button onClick={() => emergencyAction("stop-all")} variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-4 w-4" />Stop All</Button><Button onClick={load} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="h-4 w-4" />Refresh</Button></div>}
      />

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4 xl:grid-cols-8">
        <Metric label="Total deployments" value={summary?.total_deployments ?? 0} />
        <Metric label="Running" value={summary?.running ?? 0} accent />
        <Metric label="Paused" value={summary?.paused ?? 0} />
        <Metric label="Error" value={summary?.error ?? 0} />
        <Metric label="Open positions" value={summary?.open_positions ?? 0} />
        <Metric label="Today total PnL" value={money(summary?.today_total_pnl)} />
        <Metric label="Signals today" value={summary?.signals_today ?? 0} />
        <Metric label="Orders today" value={summary?.orders_today ?? 0} />
      </div>

      <GlassCard className="mb-6 p-5" hoverEffect={false}>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
          <select value={filters.status} onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))} className="rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-white outline-none focus:border-lime-300">
            <option value="">All Status</option>
            {(["RUNNING", "PAUSED", "STOPPED", "ERROR", "DRAFT"] as DeploymentStatus[]).map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <select value={filters.mode} onChange={(e) => setFilters((prev) => ({ ...prev, mode: e.target.value }))} className="rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-white outline-none focus:border-lime-300">
            <option value="">All Modes</option>
            {(["PAPER", "DEMO"] as LiveMode[]).map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <input value={filters.instrument} onChange={(e) => setFilters((prev) => ({ ...prev, instrument: e.target.value }))} placeholder="Instrument" className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white placeholder:text-purple-300 outline-none focus:border-lime-300" />
          <input value={filters.timeframe} onChange={(e) => setFilters((prev) => ({ ...prev, timeframe: e.target.value }))} placeholder="Timeframe" className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white placeholder:text-purple-300 outline-none focus:border-lime-300" />
          <div className="flex gap-2">
            <Button onClick={load} className="flex-1 bg-lime-500 text-slate-950 hover:bg-lime-400">Apply</Button>
            {activeFilterCount > 0 && <Button onClick={() => setFilters({ status: "", mode: "", instrument: "", timeframe: "" })} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">Clear</Button>}
          </div>
        </div>
      </GlassCard>

      {loading ? <GlassCard className="p-6 text-purple-100">Loading deployments...</GlassCard> : rows.length === 0 ? <EmptyState title="No record found" description="No live trading deployments found for this filter." /> : (
        <GlassCard className="overflow-hidden" hoverEffect={false}>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1400px] text-left text-sm">
              <thead className="border-b border-white/10 bg-white/5 text-purple-100">
                <tr>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Strategy</th>
                  <th className="px-4 py-3">Broker</th>
                  <th className="px-4 py-3">Instrument</th>
                  <th className="px-4 py-3">Timeframe</th>
                  <th className="px-4 py-3">Mode</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Auto Trade</th>
                  <th className="px-4 py-3">Last Signal</th>
                  <th className="px-4 py-3">Last Heartbeat</th>
                  <th className="px-4 py-3">Open Positions</th>
                  <th className="px-4 py-3">Today PnL</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {rows.map((row) => (
                  <tr key={row.deployment_id} className="text-purple-50 hover:bg-white/5">
                    <td className="px-4 py-4"><div className="font-semibold text-white">{row.user_name || "User"}</div><div className="text-xs text-purple-300">{row.user_email || row.user_id}</div></td>
                    <td className="px-4 py-4">{row.strategy_name}</td>
                    <td className="px-4 py-4">{row.broker_name ? `${row.broker_name} (${row.broker_status || "—"})` : "—"}</td>
                    <td className="px-4 py-4">{row.instrument}</td>
                    <td className="px-4 py-4">{row.timeframe}</td>
                    <td className="px-4 py-4"><Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">{row.mode}</Badge></td>
                    <td className="px-4 py-4"><StatusBadge value={row.status} /></td>
                    <td className="px-4 py-4">{row.auto_trade_enabled ? "ON" : "OFF"}</td>
                    <td className="px-4 py-4">{date(row.last_signal_at)}</td>
                    <td className="px-4 py-4">{date(row.last_heartbeat_at)}</td>
                    <td className="px-4 py-4">{row.open_positions_count}</td>
                    <td className="px-4 py-4">{money(row.today_pnl)}</td>
                    <td className="px-4 py-4">
                      <div className="flex justify-end gap-2">
                        <Link href={`/admin/live-trading/${row.deployment_id}`}><Button size="sm" variant="outline" className="h-8 gap-1 border-white/10 bg-white/5 text-white hover:bg-white/10"><Eye className="h-3.5 w-3.5" />View</Button></Link>
                        <Button size="sm" disabled={busyId === row.deployment_id} onClick={() => action(row, "force-pause")} className="h-8 gap-1 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-3.5 w-3.5" />Pause</Button>
                        <Button size="sm" disabled={busyId === row.deployment_id} onClick={() => action(row, "force-stop")} variant="outline" className="h-8 gap-1 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-3.5 w-3.5" />Stop</Button>
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
