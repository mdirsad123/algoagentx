"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, FileText, Link2, Pause, Play, RefreshCw, Send, Settings, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, BrokerOrderEvent, LiveCandleSnapshot, LiveDeploymentSummary, SignalType, StrategyDeployment } from "@/types/live-trading";

const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");
const num = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 4 });

const formatMoney = (value: unknown, currency?: string | null) => {
  const amount = Number(value || 0);
  const code = currency?.toUpperCase();
  if (code === "USD" || code === "INR" || code === "EUR" || code === "GBP") {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: code, maximumFractionDigits: 2 }).format(amount);
  }
  const formatted = amount.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return code ? `${formatted} ${code}` : formatted;
};

function NoRows({ label }: { label: string }) {
  return <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-200">{label}</div>;
}

function StatusBadge({ value }: { value?: string }) {
  const color = value === "RUNNING" ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : value === "PAUSED" ? "border-yellow-400/30 bg-yellow-400/20 text-yellow-100" : value === "ERROR" ? "border-red-400/30 bg-red-400/20 text-red-100" : "border-purple-300/30 bg-purple-400/20 text-purple-100";
  return <Badge className={color}>{value || "—"}</Badge>;
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-xs text-purple-300">{label}</p><p className="mt-2 text-2xl font-bold text-white">{value}</p></div>;
}

export default function LiveDeploymentDetailPage() {
  const { deploymentId } = useParams<{ deploymentId: string }>();
  const { showToast } = useToast();
  const [deployment, setDeployment] = useState<StrategyDeployment | null>(null);
  const [summary, setSummary] = useState<LiveDeploymentSummary | null>(null);
  const [candleSnapshot, setCandleSnapshot] = useState<LiveCandleSnapshot | null>(null);
  const [brokerEvents, setBrokerEvents] = useState<BrokerOrderEvent[]>([]);
  const [brokerAccounts, setBrokerAccounts] = useState<BrokerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [brokerBusy, setBrokerBusy] = useState(false);
  const [candleBusy, setCandleBusy] = useState(false);
  const [runnerBusy, setRunnerBusy] = useState(false);
  const [runnerResult, setRunnerResult] = useState<string>("");
  const [showLogs, setShowLogs] = useState(false);
  const [showSignals, setShowSignals] = useState(false);
  const [showOrders, setShowOrders] = useState(false);
  const [manualPrice, setManualPrice] = useState("2350.25");
  const [manualReason, setManualReason] = useState("Manual signal test");
  const [lastResult, setLastResult] = useState<string>("");
  const [liveSyncInterval, setLiveSyncInterval] = useState("10");

  const metrics = summary?.metrics;
  const broker = summary?.broker;
  const recentSignals = summary?.recent_signals || [];
  const recentOrders = summary?.recent_orders || [];
  const openPositions = summary?.open_positions || [];
  const recentLogs = summary?.recent_logs || [];
  const latestCandles = candleSnapshot?.candles?.slice(0, 5) || [];
  const runner = summary?.runner;
  const currency = broker?.currency || metrics?.currency || null;
  const isRunning = (summary?.deployment?.status || deployment?.status) === "RUNNING";
  const mode = summary?.deployment?.mode || deployment?.mode;
  const isDemoBrokerBlocked = mode === "DEMO" && broker?.status !== "CONNECTED";
  const brokerProviderLabel = ((broker?.broker_name || broker?.broker_code || candleSnapshot?.source || "MT5") as string).toUpperCase();
  const candleSource = (candleSnapshot?.source || brokerProviderLabel || "MT5").toUpperCase();
  const isUpstoxBroker = brokerProviderLabel === "UPSTOX";

  const connectedMt5Broker = useMemo(
    () => brokerAccounts.find((item) => item.status === "CONNECTED" && item.mode === "DEMO"),
    [brokerAccounts]
  );

  const loadSummary = async (silent = false) => {
    if (!deploymentId) return;
    try {
      if (!silent) setLoading(true);
      const [d, sm, accounts, candles] = await Promise.all([
        liveTradingApi.getDeployment(deploymentId),
        liveTradingApi.getDeploymentSummary(deploymentId),
        liveTradingApi.listBrokerAccounts(),
        liveTradingApi.getDeploymentCandles(deploymentId, 5).catch(() => null),
      ]);
      setDeployment(d);
      setSummary(sm);
      setLiveSyncInterval(String(sm?.deployment?.live_sync_interval_seconds || d?.live_sync_interval_seconds || 10));
      setBrokerAccounts(accounts);
      if (candles) setCandleSnapshot(candles);
      const events = await liveTradingApi.listDeploymentBrokerEvents(deploymentId, 30).catch(() => []);
      setBrokerEvents(events);
    } catch (error: any) {
      showToast(error.message || "Failed to load deployment summary", "error");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const refreshBroker = async (silent = false) => {
    if (!deploymentId || !deployment?.broker_account_id) return;
    try {
      setBrokerBusy(true);
      const result = await liveTradingApi.getDeploymentBrokerStatus(deploymentId);
      if (!silent) showToast(result.message || "Broker status refreshed", result.connected ? "success" : "error");
      await loadSummary(true);
    } catch (error: any) {
      if (!silent) showToast(error.message || "Failed to refresh broker status", "error");
    } finally {
      setBrokerBusy(false);
    }
  };

  const syncBroker = async () => {
    if (!deploymentId || !deployment?.broker_account_id) return;
    try {
      setBrokerBusy(true);
      await liveTradingApi.syncDeploymentBroker(deploymentId);
      showToast("Broker orders/positions synced", "success");
      await loadSummary(true);
      const events = await liveTradingApi.listDeploymentBrokerEvents(deploymentId, 30).catch(() => []);
      setBrokerEvents(events);
    } catch (error: any) {
      showToast(error.message || "Failed to sync broker", "error");
    } finally {
      setBrokerBusy(false);
    }
  };


  const liveSyncAction = async (type: "enable" | "disable" | "save") => {
    if (!deploymentId) return;
    const interval = Number(liveSyncInterval || 10);
    try {
      setBrokerBusy(true);
      if (type === "enable") await liveTradingApi.enableLiveSync(deploymentId, interval);
      if (type === "disable") await liveTradingApi.disableLiveSync(deploymentId);
      if (type === "save") await liveTradingApi.updateLiveSyncSettings(deploymentId, interval);
      showToast(type === "enable" ? "Live broker auto-sync enabled" : type === "disable" ? "Live broker auto-sync disabled" : "Live sync interval saved", "success");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Live sync action failed", "error");
    } finally {
      setBrokerBusy(false);
    }
  };

  const attachConnectedBroker = async () => {
    if (!deploymentId || !connectedMt5Broker) {
      showToast("No connected demo broker found. Go to Brokers and click Test Connection first.", "error");
      return;
    }
    try {
      setBrokerBusy(true);
      await liveTradingApi.updateDeployment(deploymentId, { mode: "DEMO", broker_account_id: connectedMt5Broker.id });
      showToast("Demo broker linked to this deployment", "success");
      await loadSummary(true);
      await refreshBroker(true);
    } catch (error: any) {
      showToast(error.message || "Failed to link broker", "error");
    } finally {
      setBrokerBusy(false);
    }
  };

  const refreshCandles = async () => {
    if (!deploymentId) return;
    if (mode !== "DEMO") {
      showToast("Broker candle snapshot is available for DEMO deployments only", "error");
      return;
    }
    if (!broker || broker.status !== "CONNECTED") {
      showToast("Connect and link a broker before refreshing candles", "error");
      return;
    }
    try {
      setCandleBusy(true);
      const result = await liveTradingApi.refreshDeploymentCandles(deploymentId, 300);
      setCandleSnapshot(result);
      showToast(`Stored ${result.upserted_count ?? 0} broker candles`, "success");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Failed to refresh broker candles", "error");
    } finally {
      setCandleBusy(false);
    }
  };

  useEffect(() => { loadSummary(); }, [deploymentId]);

  useEffect(() => {
    if (!deploymentId) return;
    const timer = setInterval(() => loadSummary(true), 5000);
    return () => clearInterval(timer);
  }, [deploymentId]);

  useEffect(() => {
    if (deployment?.broker_account_id) refreshBroker(true);
    // broker status refresh runs once after a linked broker is known, not every 5 sec
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deployment?.broker_account_id]);

  const action = async (type: "start" | "pause" | "stop") => {
    if (!deploymentId) return;
    try {
      setBusy(true);
      if (type === "start") await liveTradingApi.startDeployment(deploymentId);
      if (type === "pause") await liveTradingApi.pauseDeployment(deploymentId);
      if (type === "stop") await liveTradingApi.stopDeployment(deploymentId);
      showToast(`Deployment ${type} action completed`, "success");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || `Failed to ${type}`, "error");
    } finally {
      setBusy(false);
    }
  };

  const runStrategy = async (execute: boolean) => {
    if (!deploymentId) return;
    if (!isRunning) {
      showToast("Start deployment before running strategy", "error");
      return;
    }
    if (mode === "DEMO" && isDemoBrokerBlocked) {
      showToast("DEMO strategy runner requires connected broker", "error");
      return;
    }
    try {
      setRunnerBusy(true);
      const result = await liveTradingApi.runStrategyOnce(deploymentId, execute);
      const msg = result.message || (execute ? "Strategy run completed" : "Dry run completed");
      const orderTail = result.broker_order_id ? ` • Broker Order: ${result.broker_order_id}` : result.order_status ? ` • Order: ${result.order_status}` : "";
      setRunnerResult(`${result.signal || "HOLD"} • ${msg}${orderTail}`);
      showToast(msg, result.success && result.order_status !== "ERROR" ? "success" : "error");
      await loadSummary(true);
      const candles = await liveTradingApi.getDeploymentCandles(deploymentId, 5).catch(() => null);
      if (candles) setCandleSnapshot(candles);
      const events = await liveTradingApi.listDeploymentBrokerEvents(deploymentId, 30).catch(() => []);
      setBrokerEvents(events);
    } catch (error: any) {
      showToast(error.message || "Strategy runner failed", "error");
    } finally {
      setRunnerBusy(false);
    }
  };

  const autoRunnerAction = async (action: "enable" | "disable" | "run-now") => {
    if (!deploymentId) return;
    try {
      setRunnerBusy(true);
      if (action === "enable") await liveTradingApi.enableAutoRunner(deploymentId);
      if (action === "disable") await liveTradingApi.disableAutoRunner(deploymentId);
      if (action === "run-now") {
        const result = await liveTradingApi.runAutoRunnerNow(deploymentId);
        setRunnerResult(String(result.message || result.reason || "Auto runner checked"));
      }
      showToast(action === "enable" ? "Auto runner enabled" : action === "disable" ? "Auto runner disabled" : "Auto runner tick completed", "success");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Auto runner action failed", "error");
    } finally {
      setRunnerBusy(false);
    }
  };

  const sendManualSignal = async (signalType: SignalType) => {
    if (!deploymentId) return;
    const price = Number(manualPrice);
    if (!price || price <= 0) {
      showToast("Invalid price", "error");
      return;
    }
    try {
      setBusy(true);
      const result = await liveTradingApi.createDeploymentManualSignal(deploymentId, { signal_type: signalType, price, reason: manualReason || "Manual signal test" });
      const msg = result.message || `${signalType} signal ${result.status || "processed"}`;
      setLastResult(msg);
      showToast(msg, result.status === "REJECTED" || result.status === "ERROR" ? "error" : "success");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Manual signal failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const title = summary?.deployment?.name || deployment?.name || "Live Deployment";
  const subtitle = `${summary?.deployment?.strategy_name || deployment?.strategy_id || "Strategy"} • ${summary?.deployment?.instrument || deployment?.instrument || "—"} • ${summary?.deployment?.timeframe || deployment?.timeframe || "—"}`;

  if (loading) return <PageShell><GlassCard className="p-6 text-purple-100">Loading deployment...</GlassCard></PageShell>;
  if (!deployment || !summary) return <PageShell><NoRows label="No record found" /></PageShell>;

  return (
    <PageShell>
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={<><Link href="/live-trading"><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link><Button onClick={() => loadSummary(true)} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="h-4 w-4" />Refresh</Button><Button onClick={() => setShowLogs((value) => !value)} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><FileText className="h-4 w-4" />{showLogs ? "Hide Logs" : "Logs"}</Button><Link href={`/live-trading/${deployment.id}/settings`}><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><Settings className="h-4 w-4" />Settings</Button></Link></>}
      />

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge value={summary.deployment?.status || deployment.status} />
            <Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">{mode}</Badge>
            <span className="text-sm text-purple-200">Last signal: {date(summary.deployment?.last_signal_at || deployment.last_signal_at)}</span>
            <span className="text-sm text-purple-200">Auto trade: {summary.deployment?.auto_trade_enabled ? "ON" : "OFF"}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={busy} onClick={() => action("start")} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-4 w-4" />Start</Button>
            <Button disabled={busy} onClick={() => action("pause")} className="gap-2 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-4 w-4" />Pause</Button>
            <Button disabled={busy} onClick={() => action("stop")} variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-4 w-4" />Stop</Button>
          </div>
        </div>
      </GlassCard>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-7">
        <MetricCard label="Equity" value={formatMoney(metrics?.equity ?? deployment.capital, currency)} />
        <MetricCard label="Realized PnL" value={formatMoney(metrics?.realized_pnl, currency)} />
        <MetricCard label="Unrealized PnL" value={formatMoney(metrics?.unrealized_pnl, currency)} />
        <MetricCard label="Today PnL" value={formatMoney(metrics?.today_pnl, currency)} />
        <MetricCard label="Open Positions" value={String(metrics?.open_positions ?? 0)} />
        <MetricCard label="Orders Today" value={String(metrics?.orders_today ?? 0)} />
        <MetricCard label="Signals Today" value={String(metrics?.signals_today ?? 0)} />
      </div>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div><h2 className="text-xl font-bold text-lime-300">Broker</h2><p className="mt-1 text-sm text-purple-200">Connected broker account used for DEMO execution. MT5 demo execution works; Upstox execution is gated by admin safety and user confirmation.</p></div>
          <div className="flex flex-wrap gap-2">
            {!broker && connectedMt5Broker && <Button disabled={brokerBusy} onClick={attachConnectedBroker} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><Link2 className="h-4 w-4" />Attach Demo Broker</Button>}
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={() => refreshBroker()} className="gap-2 bg-blue-500 text-white hover:bg-blue-400"><RefreshCw className="h-4 w-4" />Refresh Broker</Button><Button disabled={brokerBusy || !deployment.broker_account_id} onClick={syncBroker} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><RefreshCw className="h-4 w-4" />Sync Broker</Button>
          </div>
        </div>
        {!broker ? (
          <div className="mt-4 space-y-3">
            <NoRows label="No broker account connected to this deployment. PAPER works without broker; DEMO execution requires a connected broker." />
            {connectedMt5Broker ? <p className="text-sm text-lime-200">Connected broker found: {connectedMt5Broker.account_label}. Click Attach Demo Broker to link it and switch this deployment to DEMO mode.</p> : <p className="text-sm text-yellow-100">No connected demo broker found. Go to Brokers and click Test Connection first.</p>}
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
            <MetricCard label="Account" value={broker.account_label || "Demo Broker"} />
            <MetricCard label="Status" value={broker.status || "—"} />
            <MetricCard label="Login" value={broker.login_id || "—"} />
            <MetricCard label="Server" value={broker.server_name || "—"} />
            <MetricCard label="Balance" value={formatMoney(broker.balance, broker.currency)} />
            <MetricCard label="Equity" value={formatMoney(broker.equity, broker.currency)} />
            <MetricCard label="Currency" value={broker.currency || "—"} />
            <MetricCard label="Last Connected" value={date(broker.last_connected_at)} />
            <MetricCard label="Last Broker Sync" value={date(summary.deployment?.last_broker_sync_at || deployment.last_broker_sync_at)} />
          </div>
        )}
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div>
            <h2 className="text-xl font-bold text-lime-300">Live Broker Sync</h2>
            <p className="mt-1 text-sm text-purple-200">Controlled broker order/position auto-sync. Default is OFF. Manual Sync Broker still works.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select value={liveSyncInterval} onChange={(e) => setLiveSyncInterval(e.target.value)} className="rounded-lg border border-white/10 bg-purple-950 px-3 py-2 text-sm text-white">
              {[5,10,15,30,60].map((v) => <option key={v} value={v}>{v} sec</option>)}
            </select>
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={() => liveSyncAction("enable")} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-4 w-4" />Enable Live Sync</Button>
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={() => liveSyncAction("disable")} variant="outline" className="gap-2 border-yellow-400/30 bg-yellow-500/10 text-yellow-100 hover:bg-yellow-500/20"><Pause className="h-4 w-4" />Disable Live Sync</Button>
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={() => liveSyncAction("save")} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">Save Interval</Button>
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={syncBroker} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><RefreshCw className="h-4 w-4" />Manual Sync Broker</Button>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-5">
          <MetricCard label="Live Sync" value={summary.deployment?.live_sync_enabled ? "ON" : "OFF"} />
          <MetricCard label="Interval" value={`${summary.deployment?.live_sync_interval_seconds || liveSyncInterval || 10} sec`} />
          <MetricCard label="Last Sync" value={date(summary.deployment?.last_live_sync_at || summary.deployment?.last_broker_sync_at || deployment.last_broker_sync_at)} />
          <MetricCard label="Sync Errors" value={String(summary.deployment?.live_sync_error_count || 0)} />
          <MetricCard label="Status" value={(summary.deployment?.status || deployment.status)} />
        </div>
        <p className={`mt-3 rounded-xl border p-3 text-sm ${summary.deployment?.live_sync_enabled ? "border-lime-400/20 bg-lime-400/10 text-lime-100" : "border-yellow-400/20 bg-yellow-400/10 text-yellow-100"}`}>
          {summary.deployment?.live_sync_enabled ? `Live broker auto-sync is ON. AlgoAgentX will refresh broker orders/positions every ${summary.deployment?.live_sync_interval_seconds || liveSyncInterval || 10} seconds.` : "Live broker auto-sync is OFF. Orders and positions will update only when you click Sync Broker."}
        </p>
        {summary.deployment?.live_sync_last_error && <p className="mt-2 rounded-xl border border-red-400/20 bg-red-500/10 p-3 text-sm text-red-100">Last error: {summary.deployment.live_sync_last_error}</p>}
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div>
            <h2 className="text-xl font-bold text-lime-300">Market Data Snapshot</h2>
            <p className="mt-1 text-sm text-purple-200">Latest closed candles stored from MT5 or UPSTOX for the live strategy runner. No chart and no fake data.</p>
          </div>
          <Button disabled={candleBusy || mode !== "DEMO" || !broker || broker.status !== "CONNECTED"} onClick={refreshCandles} className="gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-400">
            <RefreshCw className="h-4 w-4" /> Refresh Candles
          </Button>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-6">
          <MetricCard label="Data Source" value={candleSource} />
          <MetricCard label="Deployment Symbol" value={candleSnapshot?.symbol || summary.deployment?.instrument || deployment.instrument} />
          <MetricCard label={isUpstoxBroker ? "Instrument Key" : "Broker Symbol"} value={candleSnapshot?.instrument_key || candleSnapshot?.resolved_symbol || deployment.instrument_key || deployment.broker_symbol || candleSnapshot?.symbol || summary.deployment?.instrument || deployment.instrument} />
          <MetricCard label="Timeframe" value={candleSnapshot?.timeframe || summary.deployment?.timeframe || deployment.timeframe} />
          <MetricCard label="Candles Stored" value={String(candleSnapshot?.stored_count ?? 0)} />
          <MetricCard label="Latest Close" value={num(candleSnapshot?.latest_close)} />
        </div>
        <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">
          Latest candle time: <span className="font-semibold text-white">{date(candleSnapshot?.latest_candle_time)}</span>
        </div>
        {mode !== "DEMO" && <p className="mt-3 rounded-xl border border-yellow-400/20 bg-yellow-400/10 p-3 text-sm text-yellow-100">Switch deployment to DEMO and link a connected broker to refresh candle snapshots.</p>}
        {mode === "DEMO" && (!broker || broker.status !== "CONNECTED") && <p className="mt-3 rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-100">Broker candle refresh requires a linked CONNECTED broker account.</p>}
        {isUpstoxBroker && !(deployment.instrument_key || deployment.broker_symbol || candleSnapshot?.instrument_key) && <p className="mt-3 rounded-xl border border-yellow-400/20 bg-yellow-400/10 p-3 text-sm text-yellow-100">Upstox candle refresh requires an instrument_key/broker_symbol on this deployment. Example: NSE_EQ|INE002A01018.</p>}
        {latestCandles.length === 0 ? (
          <div className="mt-4"><NoRows label="No broker candles stored yet. For Upstox, make sure the deployment instrument_key is set, for example NSE_EQ|INE002A01018. For MT5, open Market Watch → Show All and open the symbol chart once." /></div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-purple-200"><tr><th>Time</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Volume</th></tr></thead>
              <tbody className="divide-y divide-white/10">{latestCandles.map((candle, index) => (
                <tr key={candle.id || `${candle.candle_time}-${index}`} className="text-purple-50"><td className="py-3">{date(candle.candle_time)}</td><td>{num(candle.open)}</td><td>{num(candle.high)}</td><td>{num(candle.low)}</td><td>{num(candle.close)}</td><td>{num(candle.volume)}</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div>
            <h2 className="text-xl font-bold text-lime-300">Auto Runner</h2>
            <p className="mt-1 text-sm text-purple-200">Automatic scheduler runs only on a new closed candle when deployment is RUNNING and Auto Trade is ON. Duplicate candles are skipped.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={runnerBusy || !isRunning || !summary.deployment?.auto_trade_enabled} onClick={() => autoRunnerAction("enable")} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-4 w-4" />Enable Auto Runner</Button>
            <Button disabled={runnerBusy} onClick={() => autoRunnerAction("disable")} variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Pause className="h-4 w-4" />Disable Auto Runner</Button>
            <Button disabled={runnerBusy || !isRunning || !summary.deployment?.auto_trade_enabled} onClick={() => autoRunnerAction("run-now")} variant="outline" className="gap-2 border-cyan-400/30 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20"><RefreshCw className="h-4 w-4" />Run Once Now</Button>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <MetricCard label="Auto Runner" value={summary.deployment?.auto_runner_enabled ? "ON" : "OFF"} />
          <MetricCard label="Last Runner At" value={date(summary.deployment?.last_runner_at || runner?.last_run_at)} />
          <MetricCard label="Last Processed Candle" value={date(summary.deployment?.last_processed_candle_time || runner?.last_processed_candle_time)} />
          <MetricCard label="Error Count" value={String(summary.deployment?.runner_error_count ?? runner?.runner_error_count ?? 0)} />
          <MetricCard label="Auto Trade" value={summary.deployment?.auto_trade_enabled ? "ON" : "OFF"} />
          <MetricCard label="Status" value={summary.deployment?.status || deployment.status} />
        </div>
        <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">Last error: <span className="font-semibold text-white">{summary.deployment?.runner_last_error || runner?.runner_last_error || "—"}</span></div>
        {!summary.deployment?.auto_trade_enabled && <p className="mt-3 rounded-xl border border-yellow-400/20 bg-yellow-400/10 p-3 text-sm text-yellow-100">Auto runner requires Auto Trade ON. It will not execute when auto_trade_enabled is false.</p>}
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div>
            <h2 className="text-xl font-bold text-lime-300">Strategy Runner</h2>
            <p className="mt-1 text-sm text-purple-200">Runs selected strategy on latest closed live_market_candles. DEMO refreshes broker candles first. No tick execution.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={runnerBusy || !isRunning || (mode === "DEMO" && isDemoBrokerBlocked)} onClick={() => runStrategy(true)} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-4 w-4" />Run Strategy Once</Button>
            <Button disabled={runnerBusy || !isRunning || (mode === "DEMO" && isDemoBrokerBlocked)} onClick={() => runStrategy(false)} variant="outline" className="gap-2 border-cyan-400/30 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20"><RefreshCw className="h-4 w-4" />Dry Run Strategy</Button>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <MetricCard label="Strategy" value={summary.deployment?.strategy_name || deployment.strategy_id} />
          <MetricCard label="Last Run" value={date(runner?.last_run_at)} />
          <MetricCard label="Last Candle" value={date(runner?.last_candle_time || candleSnapshot?.latest_candle_time)} />
          <MetricCard label="Last Signal" value={runner?.last_signal || summary.latest_signal?.signal_type || "—"} />
          <MetricCard label="Auto Trade" value={summary.deployment?.auto_trade_enabled ? "ON" : "OFF"} />
          <MetricCard label="Latest Order" value={runner?.latest_order_status || summary.latest_order?.status || "—"} />
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">Latest runner log: <span className="font-semibold text-white">{runnerResult || runner?.latest_runner_log || "—"}</span></div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">Latest order result: <span className="font-semibold text-white">{summary.latest_order ? `${summary.latest_order.status}${summary.latest_order.broker_order_id ? ` • ${summary.latest_order.broker_order_id}` : ""}${summary.latest_order.error_message ? ` • ${summary.latest_order.error_message}` : ""}` : runner?.latest_order_error || "—"}</span></div>
        </div>
        {!isRunning && <p className="mt-3 rounded-xl border border-yellow-400/20 bg-yellow-400/10 p-3 text-sm text-yellow-100">Deployment must be RUNNING before strategy runner can execute.</p>}
        {mode === "DEMO" && isDemoBrokerBlocked && <p className="mt-3 rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-100">DEMO strategy runner requires linked CONNECTED broker.</p>}
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="mb-4 flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div>
            <h2 className="text-xl font-bold text-lime-300">Broker Events</h2>
            <p className="mt-1 text-sm text-purple-200">Recent broker order webhook and sync events. Raw payload is redacted and safe for debugging.</p>
          </div>
          <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={syncBroker} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><RefreshCw className="h-4 w-4" />Sync Broker</Button>
        </div>
        <div className="mb-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">Last sync: <span className="font-semibold text-white">{date(summary.deployment?.last_broker_sync_at || deployment.last_broker_sync_at)}</span></div>
        {brokerEvents.length === 0 ? <NoRows label="No broker events yet. Click Sync Broker after placing a broker order, or configure broker webhook updates." /> : (
          <div className="max-h-[360px] overflow-auto rounded-xl border border-white/10">
            <table className="w-full min-w-[960px] text-left text-sm">
              <thead className="sticky top-0 bg-purple-950 text-purple-200"><tr><th className="p-3">Time</th><th>Provider</th><th>Event</th><th>Broker Order ID</th><th>Processed</th><th>Payload</th></tr></thead>
              <tbody className="divide-y divide-white/10">{brokerEvents.map((event) => <tr key={event.id} className="text-purple-50"><td className="p-3">{date(event.created_at)}</td><td>{event.broker_provider_code}</td><td>{event.event_type}</td><td>{event.broker_order_id || "—"}</td><td>{event.processed ? "YES" : "NO"}</td><td className="max-w-[360px] truncate" title={JSON.stringify(event.raw_payload || {})}>{JSON.stringify(event.raw_payload || {}).slice(0, 180)}</td></tr>)}</tbody>
            </table>
          </div>
        )}
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <h2 className="text-xl font-bold text-lime-300">Manual Signal Test</h2>
        <p className="mt-1 text-sm text-purple-200">PAPER opens simulated positions. MT5 DEMO can send demo orders. Upstox can send real broker orders only when admin safety and user confirmation are enabled.</p>
        {!isRunning && <p className="mt-3 rounded-xl border border-yellow-400/20 bg-yellow-400/10 p-3 text-sm text-yellow-100">Deployment not running. Start deployment to execute manual signals.</p>}
        {isDemoBrokerBlocked && <p className="mt-3 rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-100">Broker not connected. DEMO execution requires a connected broker.</p>}
        {lastResult && <p className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100">Last result: {lastResult}</p>}
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          <label className="text-sm text-purple-100">Price<input value={manualPrice} onChange={(e) => setManualPrice(e.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300" /></label>
          <label className="text-sm text-purple-100 md:col-span-2">Reason<input value={manualReason} onChange={(e) => setManualReason(e.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300" /></label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(["BUY", "SELL", "EXIT", "HOLD"] as SignalType[]).map((signal) => <Button key={signal} disabled={busy || !isRunning || isDemoBrokerBlocked} onClick={() => sendManualSignal(signal)} className="gap-2 bg-fuchsia-500 text-white hover:bg-fuchsia-400"><Send className="h-4 w-4" />{signal}</Button>)}
        </div>
      </GlassCard>

      <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <GlassCard className="p-6" hoverEffect={false}>
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-xl font-bold text-white">Recent Signals</h2>
              <p className="mt-1 text-sm text-purple-200">Hidden by default to keep the live screen clean.</p>
            </div>
            <Button size="sm" onClick={() => setShowSignals((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{showSignals ? "Hide" : "Open Signals"}</Button>
          </div>
          {!showSignals ? <NoRows label={`Signals are hidden. Total today: ${metrics?.signals_today ?? 0}.`} /> : recentSignals.length === 0 ? <NoRows label="No signals yet" /> : <div className="max-h-[360px] overflow-auto rounded-xl border border-white/10"><table className="w-full min-w-[760px] text-left text-sm"><thead className="sticky top-0 bg-purple-950 text-purple-200"><tr><th className="p-3">Time</th><th>Source</th><th>Signal</th><th>Symbol</th><th>Price</th><th>Status</th><th>Reason</th></tr></thead><tbody className="divide-y divide-white/10">{recentSignals.map((s) => <tr key={s.id} className="text-purple-50"><td className="p-3">{date(s.created_at)}</td><td>{s.source}</td><td>{s.signal_type}</td><td>{s.symbol}</td><td>{num(s.price)}</td><td>{s.status}</td><td className="max-w-[260px] truncate" title={s.rejection_reason || s.reason || "-"}>{s.rejection_reason || s.reason || "-"}</td></tr>)}</tbody></table></div>}
        </GlassCard>

        <GlassCard className="p-6" hoverEffect={false}>
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-xl font-bold text-white">Recent Orders</h2>
              <p className="mt-1 text-sm text-purple-200">Hidden by default. Open only when debugging order history.</p>
            </div>
            <Button size="sm" onClick={() => setShowOrders((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{showOrders ? "Hide" : "Open Orders"}</Button>
          </div>
          {!showOrders ? <NoRows label={`Orders are hidden. Total today: ${metrics?.orders_today ?? 0}.`} /> : recentOrders.length === 0 ? <NoRows label="No orders yet" /> : <div className="max-h-[360px] overflow-auto rounded-xl border border-white/10"><table className="w-full min-w-[980px] text-left text-sm"><thead className="sticky top-0 bg-purple-950 text-purple-200"><tr><th className="p-3">Time</th><th>Side</th><th>Symbol</th><th>Qty</th><th>Entry</th><th>Executed</th><th>SL</th><th>Target</th><th>Status</th><th>Broker Order ID</th><th>Error</th></tr></thead><tbody className="divide-y divide-white/10">{recentOrders.map((o) => <tr key={o.id} className="text-purple-50"><td className="p-3">{date(o.created_at)}</td><td>{o.side}</td><td>{o.symbol}</td><td>{num(o.qty)}</td><td>{num(o.entry_price)}</td><td>{num(o.executed_price)}</td><td>{num(o.stop_loss)}</td><td>{num(o.target)}</td><td>{o.status}</td><td>{o.broker_order_id || "-"}</td><td className="max-w-[260px] truncate" title={o.error_message || "-"}>{o.error_message || "-"}</td></tr>)}</tbody></table></div>}
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <GlassCard className="p-6" hoverEffect={false}>
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-xl font-bold text-white">Open Positions</h2>
              <p className="mt-1 text-sm text-purple-200">Synced from demo broker when the broker is connected.</p>
            </div>
            <Badge className="border-lime-400/30 bg-lime-400/20 text-lime-100">{metrics?.broker_synced ? `${brokerProviderLabel} synced` : "DB view"}</Badge>
          </div>
          {openPositions.length === 0 ? <NoRows label="No open positions" /> : <div className="overflow-x-auto"><table className="w-full min-w-[860px] text-left text-sm"><thead className="text-purple-200"><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Avg Entry</th><th>Current</th><th>SL</th><th>Target</th><th>Unrealized PnL</th><th>Status</th><th>Opened At</th></tr></thead><tbody className="divide-y divide-white/10">{openPositions.map((p) => <tr key={p.id} className="text-purple-50"><td className="py-3">{p.symbol}</td><td>{p.side}</td><td>{num(p.qty)}</td><td>{num(p.avg_entry_price)}</td><td>{num(p.current_price)}</td><td>{num(p.stop_loss)}</td><td>{num(p.target)}</td><td>{formatMoney(p.unrealized_pnl, currency)}</td><td>{p.status}</td><td>{date(p.opened_at)}</td></tr>)}</tbody></table></div>}
        </GlassCard>

        <GlassCard className="p-6" hoverEffect={false}><div className="mb-4 flex items-center justify-between gap-2"><h2 className="text-xl font-bold text-white">Execution Logs</h2><Button size="sm" onClick={() => setShowLogs((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{showLogs ? "Hide" : "Open Logs"}</Button></div>{!showLogs ? <NoRows label="Logs are hidden by default. Click Open Logs when you need execution details." /> : recentLogs.length === 0 ? <NoRows label="No logs yet" /> : <div className="max-h-[360px] overflow-auto rounded-xl border border-white/10"><table className="w-full min-w-[760px] text-left text-sm"><thead className="sticky top-0 bg-purple-950 text-purple-200"><tr><th className="p-3">Time</th><th>Level</th><th>Event Type</th><th>Message</th></tr></thead><tbody className="divide-y divide-white/10">{recentLogs.map((l) => <tr key={l.id} className="text-purple-50"><td className="p-3">{date(l.created_at)}</td><td>{l.level}</td><td>{l.event_type}</td><td>{l.message}</td></tr>)}</tbody></table></div>}</GlassCard>
      </div>
    </PageShell>
  );
}
