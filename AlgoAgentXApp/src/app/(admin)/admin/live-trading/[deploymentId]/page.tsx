"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Pause, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, LiveOrder, LivePosition, LiveSignal, LiveTradeLog, StrategyCatalogItem, StrategyDeployment } from "@/types/live-trading";

const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");
const money = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-200">{text}</div>; }

export default function AdminLiveTradingDetailPage() {
  const { deploymentId } = useParams<{ deploymentId: string }>();
  const { showToast } = useToast();
  const [deployment, setDeployment] = useState<StrategyDeployment | null>(null);
  const [broker, setBroker] = useState<BrokerAccount | null>(null);
  const [strategies, setStrategies] = useState<StrategyCatalogItem[]>([]);
  const [signals, setSignals] = useState<LiveSignal[]>([]);
  const [orders, setOrders] = useState<LiveOrder[]>([]);
  const [positions, setPositions] = useState<LivePosition[]>([]);
  const [logs, setLogs] = useState<LiveTradeLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const [d, s, o, p, l, strategyRows, brokerRows] = await Promise.all([
        liveTradingApi.getDeployment(deploymentId),
        liveTradingApi.listSignals(deploymentId),
        liveTradingApi.listOrders(deploymentId),
        liveTradingApi.listPositions(deploymentId),
        liveTradingApi.listLogs(deploymentId),
        liveTradingApi.listStrategies(),
        liveTradingApi.listBrokerAccounts(),
      ]);
      setDeployment(d); setSignals(s); setOrders(o); setPositions(p); setLogs(l); setStrategies(strategyRows); setBroker(brokerRows.find((b) => b.id === d.broker_account_id) || null);
    } catch (error: any) { showToast(error.message || "Failed to load admin detail", "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { if (deploymentId) load(); }, [deploymentId]);

  const action = async (type: "pause" | "stop") => {
    try { setBusy(true); if (type === "pause") await liveTradingApi.pauseDeployment(deploymentId); else await liveTradingApi.stopDeployment(deploymentId); showToast(`Force ${type} completed`, "success"); await load(); }
    catch (error: any) { showToast(error.message || `Failed to ${type}`, "error"); }
    finally { setBusy(false); }
  };

  if (loading) return <PageShell><GlassCard className="p-6 text-purple-100">Loading deployment...</GlassCard></PageShell>;
  if (!deployment) return <PageShell><Empty text="No record found" /></PageShell>;
  const strategy = strategies.find((s) => s.id === deployment.strategy_id);

  return (
    <PageShell>
      <PageHeader title={`Admin: ${deployment.name}`} subtitle="Deployment, user, strategy, broker, signals, orders, positions and logs." actions={<><Link href="/admin/live-trading"><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link><Button disabled={busy} onClick={() => action("pause")} className="gap-2 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-4 w-4" />Force Pause</Button><Button disabled={busy} onClick={() => action("stop")} variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-4 w-4" />Force Stop</Button></>} />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Deployment Details</h2><div className="space-y-2 text-sm text-purple-100"><p>Status: <Badge className="border-lime-400/30 bg-lime-400/20 text-lime-100">{deployment.status}</Badge></p><p>Mode: {deployment.mode}</p><p>Instrument: {deployment.instrument}</p><p>Timeframe: {deployment.timeframe}</p><p>Heartbeat: {date(deployment.last_heartbeat_at)}</p><p>Capital: ₹{money(deployment.capital)}</p></div></GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">User Details</h2><div className="space-y-2 text-sm text-purple-100"><p>User ID</p><p className="break-all font-mono text-xs text-white">{deployment.user_id || "—"}</p></div></GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Strategy Details</h2><div className="space-y-2 text-sm text-purple-100"><p>Name: {strategy?.name || deployment.strategy_id}</p><p>Type: {strategy?.strategyType || "—"}</p><p>Status: {strategy?.status || "—"}</p></div></GlassCard>
        <GlassCard className="p-6 xl:col-span-3" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Broker Account Metadata</h2>{broker ? <pre className="overflow-x-auto rounded-xl border border-white/10 bg-black/30 p-4 text-xs text-purple-100">{JSON.stringify({ account_label: broker.account_label, broker_name: broker.broker_name, mode: broker.mode, status: broker.status, server_name: broker.server_name, login_id: broker.login_id, metadata_json: broker.metadata_json }, null, 2)}</pre> : <Empty text="No broker connected" />}</GlassCard>
      </div>
      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Signals</h2>{signals.length === 0 ? <Empty text="No signals received" /> : <div className="space-y-2">{signals.map((s) => <div key={s.id} className="flex justify-between rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100"><span>{s.signal_type} {s.symbol}</span><span>{s.status}</span></div>)}</div>}</GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Orders</h2>{orders.length === 0 ? <Empty text="No orders yet" /> : <div className="space-y-2">{orders.map((o) => <div key={o.id} className="flex justify-between rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100"><span>{o.side} {o.symbol}</span><span>{o.status}</span></div>)}</div>}</GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Positions</h2>{positions.length === 0 ? <Empty text="No open positions" /> : <div className="space-y-2">{positions.map((p) => <div key={p.id} className="flex justify-between rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100"><span>{p.side} {p.symbol}</span><span>₹{money(p.unrealized_pnl)}</span></div>)}</div>}</GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Logs</h2>{logs.length === 0 ? <Empty text="No logs yet" /> : <div className="max-h-96 space-y-2 overflow-y-auto">{logs.map((l) => <div key={l.id} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100"><div className="flex justify-between"><b className="text-white">{l.event_type}</b><span>{l.level}</span></div><p className="mt-1 text-purple-200">{l.message}</p><p className="mt-1 text-xs text-purple-300">{date(l.created_at)}</p></div>)}</div>}</GlassCard>
      </div>
    </PageShell>
  );
}
