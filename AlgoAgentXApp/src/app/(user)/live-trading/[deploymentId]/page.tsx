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
import type { BrokerAccount, LiveCandleSnapshot, LiveDeploymentSummary, SignalType, StrategyDeployment } from "@/types/live-trading";

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
  const [brokerAccounts, setBrokerAccounts] = useState<BrokerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [brokerBusy, setBrokerBusy] = useState(false);
  const [candleBusy, setCandleBusy] = useState(false);
  const [runnerBusy, setRunnerBusy] = useState(false);
  const [runnerResult, setRunnerResult] = useState<string>("");
  const [showLogs, setShowLogs] = useState(false);
  const [manualPrice, setManualPrice] = useState("2350.25");
  const [manualReason, setManualReason] = useState("Manual signal test");
  const [lastResult, setLastResult] = useState<string>("");

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

  const connectedMt5Broker = useMemo(
    () => brokerAccounts.find((item) => item.status === "CONNECTED" && item.mode === "DEMO" && (item.broker_name || "").toUpperCase() === "MT5"),
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
      setBrokerAccounts(accounts);
      if (candles) setCandleSnapshot(candles);
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

  const attachConnectedBroker = async () => {
    if (!deploymentId || !connectedMt5Broker) {
      showToast("No connected MT5 demo broker found. Go to Brokers and click Test Connection first.", "error");
      return;
    }
    try {
      setBrokerBusy(true);
      await liveTradingApi.updateDeployment(deploymentId, { mode: "DEMO", broker_account_id: connectedMt5Broker.id });
      showToast("MT5 demo broker linked to this deployment", "success");
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
      showToast("MT5 candle snapshot is available for DEMO deployments only", "error");
      return;
    }
    if (!broker || broker.status !== "CONNECTED") {
      showToast("Connect and link an MT5 demo broker before refreshing candles", "error");
      return;
    }
    try {
      setCandleBusy(true);
      const result = await liveTradingApi.refreshDeploymentCandles(deploymentId, 300);
      setCandleSnapshot(result);
      showToast(`Stored ${result.upserted_count ?? 0} MT5 candles`, "success");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Failed to refresh MT5 candles", "error");
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
      showToast("DEMO strategy runner requires connected MT5 broker", "error");
      return;
    }
    try {
      setRunnerBusy(true);
      const result = await liveTradingApi.runStrategyOnce(deploymentId, execute);
      const msg = result.message || (execute ? "Strategy run completed" : "Dry run completed");
      setRunnerResult(`${result.signal || "HOLD"} • ${msg}`);
      showToast(msg, result.success ? "success" : "error");
      await loadSummary(true);
      const candles = await liveTradingApi.getDeploymentCandles(deploymentId, 5).catch(() => null);
      if (candles) setCandleSnapshot(candles);
    } catch (error: any) {
      showToast(error.message || "Strategy runner failed", "error");
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
          <div><h2 className="text-xl font-bold text-lime-300">Broker</h2><p className="mt-1 text-sm text-purple-200">MT5 demo broker account used for DEMO execution.</p></div>
          <div className="flex flex-wrap gap-2">
            {!broker && connectedMt5Broker && <Button disabled={brokerBusy} onClick={attachConnectedBroker} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><Link2 className="h-4 w-4" />Attach MT5 Demo</Button>}
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={() => refreshBroker()} className="gap-2 bg-blue-500 text-white hover:bg-blue-400"><RefreshCw className="h-4 w-4" />Refresh Broker</Button>
          </div>
        </div>
        {!broker ? (
          <div className="mt-4 space-y-3">
            <NoRows label="No broker account connected to this deployment. PAPER works without broker; DEMO execution requires an MT5 demo broker." />
            {connectedMt5Broker ? <p className="text-sm text-lime-200">Connected broker found: {connectedMt5Broker.account_label}. Click Attach MT5 Demo to link it and switch this deployment to DEMO mode.</p> : <p className="text-sm text-yellow-100">No connected MT5 demo broker found. Go to Brokers and click Test Connection first.</p>}
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
            <MetricCard label="Account" value={broker.account_label || "MT5 Demo"} />
            <MetricCard label="Status" value={broker.status || "—"} />
            <MetricCard label="Login" value={broker.login_id || "—"} />
            <MetricCard label="Server" value={broker.server_name || "—"} />
            <MetricCard label="Balance" value={formatMoney(broker.balance, broker.currency)} />
            <MetricCard label="Equity" value={formatMoney(broker.equity, broker.currency)} />
            <MetricCard label="Currency" value={broker.currency || "—"} />
            <MetricCard label="Last Connected" value={date(broker.last_connected_at)} />
          </div>
        )}
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div>
            <h2 className="text-xl font-bold text-lime-300">Market Data Snapshot</h2>
            <p className="mt-1 text-sm text-purple-200">Latest closed candles stored from MT5 for the live strategy runner. No chart and no fake data.</p>
          </div>
          <Button disabled={candleBusy || mode !== "DEMO" || !broker || broker.status !== "CONNECTED"} onClick={refreshCandles} className="gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-400">
            <RefreshCw className="h-4 w-4" /> Refresh Candles
          </Button>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-6">
          <MetricCard label="Data Source" value={candleSnapshot?.source || "MT5"} />
          <MetricCard label="Deployment Symbol" value={candleSnapshot?.symbol || summary.deployment?.instrument || deployment.instrument} />
          <MetricCard label="MT5 Symbol" value={candleSnapshot?.resolved_symbol || candleSnapshot?.symbol || summary.deployment?.instrument || deployment.instrument} />
          <MetricCard label="Timeframe" value={candleSnapshot?.timeframe || summary.deployment?.timeframe || deployment.timeframe} />
          <MetricCard label="Candles Stored" value={String(candleSnapshot?.stored_count ?? 0)} />
          <MetricCard label="Latest Close" value={num(candleSnapshot?.latest_close)} />
        </div>
        <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">
          Latest candle time: <span className="font-semibold text-white">{date(candleSnapshot?.latest_candle_time)}</span>
        </div>
        {mode !== "DEMO" && <p className="mt-3 rounded-xl border border-yellow-400/20 bg-yellow-400/10 p-3 text-sm text-yellow-100">Switch deployment to DEMO and link a connected MT5 broker to refresh candle snapshots.</p>}
        {mode === "DEMO" && (!broker || broker.status !== "CONNECTED") && <p className="mt-3 rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-100">MT5 candle refresh requires a linked CONNECTED broker account.</p>}
        {latestCandles.length === 0 ? (
          <div className="mt-4"><NoRows label="No MT5 candles stored yet. Click Refresh Candles after MT5 is connected. If MT5 returns no candles, open Market Watch → Show All and open the symbol chart once in the MT5 terminal." /></div>
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
            <h2 className="text-xl font-bold text-lime-300">Strategy Runner</h2>
            <p className="mt-1 text-sm text-purple-200">Runs selected strategy on latest closed live_market_candles. DEMO refreshes MT5 candles first. No tick execution.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={runnerBusy || !isRunning || (mode === "DEMO" && isDemoBrokerBlocked)} onClick={() => runStrategy(true)} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-4 w-4" />Run Strategy Once</Button>
            <Button disabled={runnerBusy || !isRunning || (mode === "DEMO" && isDemoBrokerBlocked)} onClick={() => runStrategy(false)} variant="outline" className="gap-2 border-cyan-400/30 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20"><RefreshCw className="h-4 w-4" />Dry Run Strategy</Button>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-5">
          <MetricCard label="Strategy" value={summary.deployment?.strategy_name || deployment.strategy_id} />
          <MetricCard label="Last Run" value={date(runner?.last_run_at)} />
          <MetricCard label="Last Candle" value={date(runner?.last_candle_time || candleSnapshot?.latest_candle_time)} />
          <MetricCard label="Last Signal" value={runner?.last_signal || summary.latest_signal?.signal_type || "—"} />
          <MetricCard label="Auto Trade" value={summary.deployment?.auto_trade_enabled ? "ON" : "OFF"} />
        </div>
        <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">Latest runner log: <span className="font-semibold text-white">{runnerResult || runner?.latest_runner_log || "—"}</span></div>
        {!isRunning && <p className="mt-3 rounded-xl border border-yellow-400/20 bg-yellow-400/10 p-3 text-sm text-yellow-100">Deployment must be RUNNING before strategy runner can execute.</p>}
        {mode === "DEMO" && isDemoBrokerBlocked && <p className="mt-3 rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-100">DEMO strategy runner requires linked CONNECTED MT5 broker.</p>}
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <h2 className="text-xl font-bold text-lime-300">Manual Signal Test</h2>
        <p className="mt-1 text-sm text-purple-200">PAPER opens simulated positions. DEMO sends MT5 demo orders when broker is connected.</p>
        {!isRunning && <p className="mt-3 rounded-xl border border-yellow-400/20 bg-yellow-400/10 p-3 text-sm text-yellow-100">Deployment not running. Start deployment to execute manual signals.</p>}
        {isDemoBrokerBlocked && <p className="mt-3 rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-100">Broker not connected. DEMO execution requires a connected MT5 demo broker.</p>}
        {lastResult && <p className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100">Last result: {lastResult}</p>}
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          <label className="text-sm text-purple-100">Price<input value={manualPrice} onChange={(e) => setManualPrice(e.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300" /></label>
          <label className="text-sm text-purple-100 md:col-span-2">Reason<input value={manualReason} onChange={(e) => setManualReason(e.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300" /></label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(["BUY", "SELL", "EXIT", "HOLD"] as SignalType[]).map((signal) => <Button key={signal} disabled={busy || !isRunning || isDemoBrokerBlocked} onClick={() => sendManualSignal(signal)} className="gap-2 bg-fuchsia-500 text-white hover:bg-fuchsia-400"><Send className="h-4 w-4" />{signal}</Button>)}
        </div>
      </GlassCard>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-4 text-xl font-bold text-white">Recent Signals</h2>{recentSignals.length === 0 ? <NoRows label="No signals yet" /> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="text-purple-200"><tr><th>Time</th><th>Source</th><th>Signal</th><th>Symbol</th><th>Price</th><th>Status</th><th>Reason</th></tr></thead><tbody className="divide-y divide-white/10">{recentSignals.map((s) => <tr key={s.id} className="text-purple-50"><td className="py-3">{date(s.created_at)}</td><td>{s.source}</td><td>{s.signal_type}</td><td>{s.symbol}</td><td>{num(s.price)}</td><td>{s.status}</td><td>{s.rejection_reason || s.reason || "—"}</td></tr>)}</tbody></table></div>}</GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-4 text-xl font-bold text-white">Recent Orders</h2>{recentOrders.length === 0 ? <NoRows label="No orders yet" /> : <div className="overflow-x-auto"><table className="w-full min-w-[980px] text-left text-sm"><thead className="text-purple-200"><tr><th>Time</th><th>Side</th><th>Symbol</th><th>Qty</th><th>Entry</th><th>Executed</th><th>SL</th><th>Target</th><th>Status</th><th>Broker Order ID</th><th>Error</th></tr></thead><tbody className="divide-y divide-white/10">{recentOrders.map((o) => <tr key={o.id} className="text-purple-50"><td className="py-3">{date(o.created_at)}</td><td>{o.side}</td><td>{o.symbol}</td><td>{num(o.qty)}</td><td>{num(o.entry_price)}</td><td>{num(o.executed_price)}</td><td>{num(o.stop_loss)}</td><td>{num(o.target)}</td><td>{o.status}</td><td>{o.broker_order_id || "—"}</td><td>{o.error_message || "—"}</td></tr>)}</tbody></table></div>}</GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-4 text-xl font-bold text-white">Open Positions</h2>{openPositions.length === 0 ? <NoRows label="No open positions" /> : <div className="overflow-x-auto"><table className="w-full min-w-[860px] text-left text-sm"><thead className="text-purple-200"><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Avg Entry</th><th>Current</th><th>SL</th><th>Target</th><th>Unrealized PnL</th><th>Status</th><th>Opened At</th></tr></thead><tbody className="divide-y divide-white/10">{openPositions.map((p) => <tr key={p.id} className="text-purple-50"><td className="py-3">{p.symbol}</td><td>{p.side}</td><td>{num(p.qty)}</td><td>{num(p.avg_entry_price)}</td><td>{num(p.current_price)}</td><td>{num(p.stop_loss)}</td><td>{num(p.target)}</td><td>{formatMoney(p.unrealized_pnl, currency)}</td><td>{p.status}</td><td>{date(p.opened_at)}</td></tr>)}</tbody></table></div>}</GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><div className="mb-4 flex items-center justify-between gap-2"><h2 className="text-xl font-bold text-white">Execution Logs</h2><Button size="sm" onClick={() => setShowLogs((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{showLogs ? "Hide" : "Open Logs"}</Button></div>{!showLogs ? <NoRows label="Logs are hidden by default. Click Open Logs when you need execution details." /> : recentLogs.length === 0 ? <NoRows label="No logs yet" /> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="text-purple-200"><tr><th>Time</th><th>Level</th><th>Event Type</th><th>Message</th></tr></thead><tbody className="divide-y divide-white/10">{recentLogs.map((l) => <tr key={l.id} className="text-purple-50"><td className="py-3">{date(l.created_at)}</td><td>{l.level}</td><td>{l.event_type}</td><td>{l.message}</td></tr>)}</tbody></table></div>}</GlassCard>
      </div>
    </PageShell>
  );
}
