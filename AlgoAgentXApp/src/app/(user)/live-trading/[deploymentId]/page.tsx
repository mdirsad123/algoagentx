"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Copy, Pause, Play, RefreshCw, Send, Settings, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, BrokerAccountInfo, BrokerMt5Position, LiveDeploymentSummary, LiveOrder, LivePosition, LiveSignal, LiveTradeLog, SignalType, StrategyDeployment } from "@/types/live-trading";

const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");
const money = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
const prettyJson = (value: unknown) => JSON.stringify(value, null, 2);

function NoRows({ label }: { label: string }) { return <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-200">{label}</div>; }
function StatusBadge({ value }: { value?: string }) { return <Badge className="border-lime-400/30 bg-lime-400/20 text-lime-100">{value || "—"}</Badge>; }
function MetricCard({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-xs text-purple-300">{label}</p><p className="mt-2 text-2xl font-bold text-white">{value}</p></div>; }

export default function LiveDeploymentDetailPage() {
  const { deploymentId } = useParams<{ deploymentId: string }>();
  const { showToast } = useToast();
  const [deployment, setDeployment] = useState<StrategyDeployment | null>(null);
  const [summary, setSummary] = useState<LiveDeploymentSummary | null>(null);
  const [positions, setPositions] = useState<LivePosition[]>([]);
  const [signals, setSignals] = useState<LiveSignal[]>([]);
  const [orders, setOrders] = useState<LiveOrder[]>([]);
  const [logs, setLogs] = useState<LiveTradeLog[]>([]);
  const [broker, setBroker] = useState<BrokerAccount | null>(null);
  const [brokerInfo, setBrokerInfo] = useState<BrokerAccountInfo | null>(null);
  const [brokerPositions, setBrokerPositions] = useState<BrokerMt5Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [brokerBusy, setBrokerBusy] = useState(false);
  const [manualPrice, setManualPrice] = useState("");
  const [manualReason, setManualReason] = useState("Manual paper test");

  const loadBroker = async (row: StrategyDeployment) => {
    if (!row.broker_account_id) { setBroker(null); setBrokerInfo(null); setBrokerPositions([]); return; }
    try {
      const [b, info, mt5Positions] = await Promise.all([
        liveTradingApi.getBrokerAccount(row.broker_account_id),
        liveTradingApi.getBrokerAccountInfo(row.broker_account_id),
        liveTradingApi.getBrokerPositions(row.broker_account_id),
      ]);
      setBroker(b); setBrokerInfo(info); setBrokerPositions(mt5Positions);
    } catch {
      setBroker(null); setBrokerInfo(null); setBrokerPositions([]);
    }
  };

  const load = async () => {
    if (!deploymentId) return;
    try {
      setLoading(true);
      const [d, sm, p, s, o, l] = await Promise.all([
        liveTradingApi.getDeployment(deploymentId),
        liveTradingApi.getDeploymentSummary(deploymentId),
        liveTradingApi.listPositions(deploymentId),
        liveTradingApi.listSignals(deploymentId),
        liveTradingApi.listOrders(deploymentId),
        liveTradingApi.listLogs(deploymentId),
      ]);
      setDeployment(d); setSummary(sm); setPositions(p); setSignals(s); setOrders(o); setLogs(l);
      await loadBroker(d);
    } catch (error: any) { showToast(error.message || "Failed to load deployment", "error"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [deploymentId]);

  const refreshBroker = async () => {
    if (!deployment?.broker_account_id) return;
    try {
      setBrokerBusy(true);
      const [info, mt5Positions] = await Promise.all([
        liveTradingApi.getBrokerAccountInfo(deployment.broker_account_id),
        liveTradingApi.getBrokerPositions(deployment.broker_account_id),
      ]);
      setBrokerInfo(info); setBrokerPositions(mt5Positions);
      showToast("Broker data refreshed", "success");
    } catch (error: any) { showToast(error.message || "Failed to refresh broker data", "error"); }
    finally { setBrokerBusy(false); }
  };

  const action = async (type: "start" | "pause" | "stop") => {
    if (!deploymentId) return;
    try {
      setBusy(true);
      if (type === "start") await liveTradingApi.startDeployment(deploymentId);
      if (type === "pause") await liveTradingApi.pauseDeployment(deploymentId);
      if (type === "stop") await liveTradingApi.stopDeployment(deploymentId);
      showToast(`Deployment ${type} action completed`, "success");
      await load();
    } catch (error: any) { showToast(error.message || `Failed to ${type}`, "error"); }
    finally { setBusy(false); }
  };

  const sendManualSignal = async (signalType: SignalType) => {
    if (!deploymentId) return;
    const price = Number(manualPrice);
    if (!price || price <= 0) { showToast("Enter a valid signal price", "error"); return; }
    try {
      setBusy(true);
      await liveTradingApi.createDeploymentManualSignal(deploymentId, { signal_type: signalType, price, reason: manualReason || "Manual paper test" });
      showToast(`${signalType} manual signal processed`, "success");
      await load();
    } catch (error: any) { showToast(error.message || "Manual signal failed", "error"); }
    finally { setBusy(false); }
  };

  const copyToClipboard = async (value: string, label: string) => {
    try { await navigator.clipboard.writeText(value); showToast(`${label} copied`, "success"); }
    catch { showToast(`Unable to copy ${label}`, "error"); }
  };

  if (loading) return <PageShell><GlassCard className="p-6 text-purple-100">Loading deployment...</GlassCard></PageShell>;
  if (!deployment) return <PageShell><NoRows label="No record found" /></PageShell>;

  const openPositions = positions.filter((p) => p.status === "OPEN");
  const example = deployment.example_payload || { secret: deployment.tradingview_secret || "USER_DEPLOYMENT_SECRET", deployment_id: deployment.id, symbol: "{{ticker}}", timeframe: "{{interval}}", signal: "BUY", price: "{{close}}", time: "{{time}}", reason: "TradingView alert" };

  return (
    <PageShell>
      <PageHeader title={deployment.name} subtitle={`${deployment.instrument} • ${deployment.timeframe}`} actions={<><Link href="/live-trading"><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link><Link href={`/live-trading/${deployment.id}/settings`}><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><Settings className="h-4 w-4" />Settings</Button></Link></>} />

      <GlassCard className="mb-6 p-6" hoverEffect={false}><div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center"><div className="flex flex-wrap items-center gap-3"><StatusBadge value={deployment.status} /><Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">{deployment.mode}</Badge><span className="text-sm text-purple-200">Last signal: {date(deployment.last_signal_at)}</span></div><div className="flex flex-wrap gap-2"><Button disabled={busy} onClick={() => action("start")} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-4 w-4" />Start</Button><Button disabled={busy} onClick={() => action("pause")} className="gap-2 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-4 w-4" />Pause</Button><Button disabled={busy} onClick={() => action("stop")} variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-4 w-4" />Stop</Button></div></div></GlassCard>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-6"><MetricCard label="Equity" value={`₹${money(summary?.equity ?? deployment.capital)}`} /><MetricCard label="Realized PnL" value={`₹${money(summary?.realized_pnl)}`} /><MetricCard label="Unrealized PnL" value={`₹${money(summary?.unrealized_pnl)}`} /><MetricCard label="Open Positions" value={String(summary?.open_positions_count ?? openPositions.length)} /><MetricCard label="Orders Today" value={String(summary?.orders_count_today ?? 0)} /><MetricCard label="Signals Today" value={String(summary?.signals_count_today ?? 0)} /></div>

      <GlassCard className="mb-6 p-6" hoverEffect={false}><h2 className="text-xl font-bold text-lime-300">Broker</h2><p className="mt-1 text-sm text-purple-200">MT5 demo account status, account balance/equity and broker open positions.</p>{!deployment.broker_account_id ? <div className="mt-4"><NoRows label="No broker account connected to this deployment" /></div> : <div className="mt-4 space-y-4"><div className="flex flex-col justify-between gap-3 rounded-xl border border-white/10 bg-white/5 p-4 lg:flex-row lg:items-center"><div><p className="font-semibold text-white">{broker?.account_label || "MT5 Demo"}</p><p className="text-sm text-purple-200">{broker?.broker_name || "MT5"} • {broker?.server_name || brokerInfo?.server || "Server not available"} • Status: {broker?.status || "—"}</p>{brokerInfo?.message && <p className="mt-1 text-xs text-purple-300">{brokerInfo.message}</p>}</div><Button disabled={brokerBusy} onClick={refreshBroker} className="gap-2 bg-blue-500 text-white hover:bg-blue-400"><RefreshCw className="h-4 w-4" />Refresh Broker</Button></div><div className="grid grid-cols-1 gap-3 md:grid-cols-4"><MetricCard label="Balance" value={brokerInfo?.balance ? String(money(brokerInfo.balance)) : "—"} /><MetricCard label="Equity" value={brokerInfo?.equity ? String(money(brokerInfo.equity)) : "—"} /><MetricCard label="Currency" value={brokerInfo?.currency || "—"} /><MetricCard label="Connected" value={brokerInfo?.connected ? "Yes" : "No"} /></div><div><h3 className="mb-2 font-semibold text-white">Broker Open Positions</h3>{brokerPositions.length === 0 ? <NoRows label="No MT5 broker positions found" /> : <div className="space-y-2">{brokerPositions.slice(0, 8).map((p, index) => <div key={`${p.ticket || index}`} className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-purple-100"><div className="flex justify-between"><b>{String(p.symbol || "—")}</b><span>Ticket {String(p.ticket || "—")}</span></div><div className="mt-1 grid grid-cols-2 gap-2 text-purple-300 md:grid-cols-4"><span>Vol {String(p.volume || "—")}</span><span>Open {String(p.price_open || "—")}</span><span>Now {String(p.price_current || "—")}</span><span>Profit {String(p.profit || "—")}</span></div>{p.message && <p className="mt-1 text-xs text-yellow-200">{String(p.message)}</p>}</div>)}</div>}</div></div>}</GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}><h2 className="text-xl font-bold text-lime-300">Manual Signal Test</h2><p className="mt-1 text-sm text-purple-200">PAPER opens simulated positions. DEMO sends MT5 demo market orders when broker is connected.</p><div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3"><div><label className="text-sm text-purple-200">Price</label><input value={manualPrice} onChange={(e) => setManualPrice(e.target.value)} placeholder="2350.25" className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-4 py-3 text-white outline-none focus:border-lime-300/60" /></div><div className="lg:col-span-2"><label className="text-sm text-purple-200">Reason</label><input value={manualReason} onChange={(e) => setManualReason(e.target.value)} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-4 py-3 text-white outline-none focus:border-lime-300/60" /></div></div><div className="mt-4 flex flex-wrap gap-2"><Button disabled={busy} onClick={() => sendManualSignal("BUY")} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Send className="h-4 w-4" />BUY</Button><Button disabled={busy} onClick={() => sendManualSignal("SELL")} className="gap-2 bg-fuchsia-500 text-white hover:bg-fuchsia-400"><Send className="h-4 w-4" />SELL</Button><Button disabled={busy} onClick={() => sendManualSignal("EXIT")} variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-4 w-4" />EXIT</Button></div></GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}><div className="flex flex-col gap-4"><div><h2 className="text-xl font-bold text-lime-300">TradingView Webhook Setup</h2><p className="mt-1 text-sm text-purple-200">Signals are stored first. Orders are created only when this deployment is RUNNING and Auto Trade is enabled.</p></div><div className="grid grid-cols-1 gap-4 lg:grid-cols-2"><div className="rounded-xl border border-white/10 bg-white/5 p-4"><div className="mb-2 flex items-center justify-between gap-2"><p className="text-sm font-semibold text-white">Webhook URL</p><Button size="sm" variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10" onClick={() => copyToClipboard(deployment.webhook_url || "/api/v1/webhooks/tradingview", "Webhook URL")}><Copy className="h-3 w-3" />Copy</Button></div><code className="block overflow-x-auto rounded-lg bg-black/30 p-3 text-xs text-lime-100">{deployment.webhook_url || "/api/v1/webhooks/tradingview"}</code></div><div className="rounded-xl border border-white/10 bg-white/5 p-4"><div className="mb-2 flex items-center justify-between gap-2"><p className="text-sm font-semibold text-white">Secret</p><Button size="sm" variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10" onClick={() => copyToClipboard(deployment.tradingview_secret || "", "Secret")}><Copy className="h-3 w-3" />Copy</Button></div><code className="block overflow-x-auto rounded-lg bg-black/30 p-3 text-xs text-cyan-100">{deployment.tradingview_secret || "Secret not generated"}</code></div></div><div className="rounded-xl border border-white/10 bg-black/20 p-4"><div className="mb-2 flex items-center justify-between gap-2"><p className="text-sm font-semibold text-white">TradingView alert message JSON</p><Button size="sm" variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10" onClick={() => copyToClipboard(prettyJson(example), "Example JSON")}><Copy className="h-3 w-3" />Copy JSON</Button></div><pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-black/30 p-4 text-xs text-purple-100">{prettyJson(example)}</pre></div></div></GlassCard>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3"><GlassCard className="p-6 xl:col-span-2" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Live Chart</h2><div className="flex h-80 items-center justify-center rounded-2xl border border-dashed border-white/20 bg-black/20 text-center text-purple-200">Live chart will stream candles and signals here</div></GlassCard><GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Open Position</h2>{openPositions.length === 0 ? <NoRows label="No open positions" /> : <div className="space-y-3">{openPositions.map((p) => <div key={p.id} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100"><div className="flex justify-between"><b className="text-white">{p.symbol}</b><span>{p.side}</span></div><div className="mt-2 flex justify-between"><span>Qty</span><span>{money(p.qty)}</span></div><div className="flex justify-between"><span>Entry</span><span>₹{money(p.avg_entry_price)}</span></div><div className="flex justify-between"><span>SL / Target</span><span>₹{money(p.stop_loss)} / ₹{money(p.target)}</span></div><div className="flex justify-between"><span>Unrealized PnL</span><span>₹{money(p.unrealized_pnl)}</span></div></div>)}</div>}</GlassCard></div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2"><GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Recent Signals</h2>{signals.length === 0 ? <NoRows label="No signals received" /> : <div className="space-y-2">{signals.slice(0, 8).map((s) => <div key={s.id} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100"><div className="flex justify-between"><span>{s.signal_type} {s.side || ""}</span><span>{s.status}</span></div><div className="mt-1 flex justify-between text-purple-300"><span>₹{money(s.price)}</span><span>{date(s.created_at)}</span></div>{s.rejection_reason && <p className="mt-1 text-xs text-red-200">{s.rejection_reason}</p>}</div>)}</div>}</GlassCard><GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Recent Orders</h2>{orders.length === 0 ? <NoRows label="No orders yet" /> : <div className="space-y-2">{orders.slice(0, 8).map((o) => <div key={o.id} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100"><div className="flex justify-between"><span>{o.side} {o.symbol}</span><span>{o.status}</span></div><div className="mt-1 flex justify-between text-purple-300"><span>Qty {money(o.qty)}</span><span>₹{money(o.executed_price || o.entry_price)}</span></div>{o.error_message && <p className="mt-1 text-xs text-red-200">{o.error_message}</p>}</div>)}</div>}</GlassCard><GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Logs</h2>{logs.length === 0 ? <NoRows label="No logs yet" /> : <div className="max-h-80 space-y-2 overflow-y-auto">{logs.slice(0, 20).map((l) => <div key={l.id} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm"><div className="flex justify-between text-purple-100"><b className="text-white">{l.event_type}</b><span>{l.level}</span></div><p className="mt-1 text-purple-200">{l.message}</p><p className="mt-1 text-xs text-purple-300">{date(l.created_at)}</p></div>)}</div>}</GlassCard><GlassCard className="p-6" hoverEffect={false}><h2 className="mb-3 text-xl font-bold text-white">Deployment Config</h2><div className="grid grid-cols-2 gap-3 text-sm text-purple-100">{[["Capital", `₹${money(deployment.capital)}`], ["Risk/trade", String(deployment.risk_per_trade)], ["RR ratio", String(deployment.rr_ratio)], ["Price risk", String(deployment.price_risk_pct)], ["Max daily loss", `₹${money(deployment.max_daily_loss)}`], ["Max trades/day", deployment.max_trades_per_day], ["Max open positions", deployment.max_open_positions], ["Allow short", deployment.allow_short ? "Yes" : "No"], ["Auto trade", deployment.auto_trade_enabled ? "Yes" : "No"]].map(([k, v]) => <div key={String(k)} className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-purple-300">{k}</p><p className="mt-1 font-semibold text-white">{String(v)}</p></div>)}</div></GlassCard></div>
    </PageShell>
  );
}
