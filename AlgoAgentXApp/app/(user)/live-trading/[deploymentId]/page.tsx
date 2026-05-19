"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Activity, Link2, Pause, Play, RefreshCw, Settings, ShieldCheck, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { OrderCalculationAuditPanel } from "@/components/live/OrderCalculationAuditPanel";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, LiveCandleSnapshot, FullDryTestResponse, LiveDeploymentSummary, LiveReadiness, LiveReadinessCheck, StrategyDeployment } from "@/types/live-trading";

const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");
const num = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 4 });

const openedAtDisplay = (p: { opened_at?: string | null; broker_opened_at?: string | null; broker_opened_at_raw?: string | null }) => {
  const broker = p.broker_opened_at ? date(p.broker_opened_at) : p.broker_opened_at_raw || null;
  const local = date(p.opened_at);
  if (broker) {
    return (
      <div className="space-y-0.5 text-xs leading-5" title="MT5/broker time may differ from your browser local time.">
        <div>MT5: {broker}</div>
        <div className="text-purple-300">Local: {local}</div>
      </div>
    );
  }
  return <span title="Shown in your browser local time.">Local: {local}</span>;
};


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


function ReadinessIcon({ status }: { status?: string }) {
  if (status === "PASS") return <span className="text-lg">✅</span>;
  if (status === "WARNING") return <span className="text-lg">⚠️</span>;
  return <span className="text-lg">❌</span>;
}

function readinessTheme(status?: string) {
  if (status === "READY") return { title: "Ready for auto trading", badge: "border-lime-400/30 bg-lime-400/20 text-lime-100", panel: "border-lime-400/20 bg-lime-400/10" };
  if (status === "WARNING") return { title: "Almost ready", badge: "border-yellow-400/30 bg-yellow-400/20 text-yellow-100", panel: "border-yellow-400/20 bg-yellow-400/10" };
  return { title: "Not ready yet", badge: "border-red-400/30 bg-red-400/20 text-red-100", panel: "border-red-400/20 bg-red-400/10" };
}

function LiveFlowPanel() {
  const steps = [
    "Refresh candles",
    "Strategy checks latest closed candle",
    "If signal is BUY/SELL, risk engine calculates lot/qty",
    "Order is sent to the approved broker account",
    "Position is monitored and synced",
  ];
  return (
    <GlassCard className="mb-6 p-6" hoverEffect={false}>
      <div className="mb-4 flex items-center gap-2">
        <Activity className="h-5 w-5 text-lime-300" />
        <div>
          <h2 className="text-xl font-bold text-white">How Live Trading Works</h2>
          <p className="text-sm text-purple-200">Simple beginner view of what AlgoAgentX does when live automation is enabled.</p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
        {steps.map((step, index) => (
          <div key={step} className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">
            <div className="mb-2 flex h-7 w-7 items-center justify-center rounded-full bg-lime-400/20 text-sm font-bold text-lime-100">{index + 1}</div>
            {step}
          </div>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-1 gap-3 text-sm text-purple-100 md:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-white/5 p-4"><span className="font-semibold text-white">Auto Runner</span> checks every new closed candle.</div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-4"><span className="font-semibold text-white">Auto Trade</span> places an order only when strategy gives BUY/SELL and risk preview passes.</div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-4"><span className="font-semibold text-white">Broker Sync</span> reads positions/orders from broker. It does not place new orders.</div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-4"><span className="font-semibold text-white">Dry Run</span> tests strategy signal without placing order.</div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-4"><span className="font-semibold text-white">DEMO mode</span> sends orders to your connected demo broker.</div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-4"><span className="font-semibold text-white">LIVE mode</span> sends orders only after broker approval, readiness, and safety checks pass.</div>
      </div>
    </GlassCard>
  );
}

function ReadinessChecklist({ readiness, onRunFullDryTest, dryTestDisabled }: { readiness: LiveReadiness | null; onRunFullDryTest: () => void; dryTestDisabled?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const theme = readinessTheme(readiness?.overall_status);
  const checks = readiness?.checks || [];
  const failingCount = checks.filter((check) => check.status !== "PASS").length;
  return (
    <GlassCard className={`mb-6 p-6 ${theme.panel}`} hoverEffect={false}>
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-lime-300" />
            <h2 className="text-2xl font-bold text-white">Live Engine Status</h2>
          </div>
          <p className="text-sm text-purple-100">{readiness?.summary || theme.title}</p>
          <p className="mt-1 text-xs text-purple-200">Checklist is collapsed to keep this page clean. Open it only when you need readiness details.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={`${theme.badge} text-sm`}>{theme.title}</Badge>
          <Badge className="border-white/10 bg-white/10 text-purple-100">{failingCount} needs attention</Badge>
          <Button disabled={dryTestDisabled} onClick={onRunFullDryTest} className="gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-400"><RefreshCw className="h-4 w-4" />Run Full Dry Test</Button>
          <Button onClick={() => setExpanded((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{expanded ? "Hide Checklist" : "Show Checklist"}</Button>
        </div>
      </div>
      {expanded && (
        <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-2">
          {checks.map((check: LiveReadinessCheck) => (
            <div key={check.key} className="rounded-xl border border-white/10 bg-purple-950/30 p-4">
              <div className="flex items-start gap-3">
                <ReadinessIcon status={check.status} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-white">{check.label}</p>
                    <Badge className={check.status === "PASS" ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : check.status === "WARNING" ? "border-yellow-400/30 bg-yellow-400/20 text-yellow-100" : "border-red-400/30 bg-red-400/20 text-red-100"}>{check.status}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-purple-200">{check.message}</p>
                  {check.action_label && check.action_href && (
                    <Link href={check.action_href}><Button size="sm" variant="outline" className="mt-3 border-white/10 bg-white/5 text-white hover:bg-white/10">{check.action_label}</Button></Link>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </GlassCard>
  );
}

export default function LiveDeploymentDetailPage() {
  const { deploymentId } = useParams<{ deploymentId: string }>();
  const { showToast } = useToast();
  const [deployment, setDeployment] = useState<StrategyDeployment | null>(null);
  const [summary, setSummary] = useState<LiveDeploymentSummary | null>(null);
  const [readiness, setReadiness] = useState<LiveReadiness | null>(null);
  const [candleSnapshot, setCandleSnapshot] = useState<LiveCandleSnapshot | null>(null);
  const [brokerAccounts, setBrokerAccounts] = useState<BrokerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [brokerBusy, setBrokerBusy] = useState(false);
  const [candleBusy, setCandleBusy] = useState(false);
  const [runnerBusy, setRunnerBusy] = useState(false);
  const [runnerResult, setRunnerResult] = useState<string>("");
  const [fullDryTest, setFullDryTest] = useState<FullDryTestResponse | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const [showSignals, setShowSignals] = useState(false);
  const [showOrders, setShowOrders] = useState(false);
  const [showAdvancedDiagnostics, setShowAdvancedDiagnostics] = useState(false);

  const metrics = summary?.metrics;
  const broker = summary?.broker;
  const recentSignals = summary?.recent_signals || [];
  const recentOrders = summary?.recent_orders || [];
  const openPositions = summary?.open_positions || [];
  const recentLogs = summary?.recent_logs || [];
  const latestCandles = candleSnapshot?.candles?.slice(0, 5) || [];
  const currency = broker?.currency || metrics?.account_currency || metrics?.currency || null;
  const isRunning = (summary?.deployment?.status || deployment?.status) === "RUNNING";
  const mode = summary?.deployment?.mode || deployment?.mode;
  const isBrokerBlocked = (mode === "DEMO" || mode === "LIVE") && broker?.status !== "CONNECTED";
  const isPaperDeprecated = mode === "PAPER";
  const brokerProviderLabel = ((broker?.broker_name || broker?.broker_code || candleSnapshot?.source || "MT5") as string).toUpperCase();
  const candleSource = (candleSnapshot?.source || brokerProviderLabel || "MT5").toUpperCase();
  const pnlSourceLabel = metrics?.broker_pnl_source === "MT5_AGENT_POSITIONS_AND_DEALS"
    ? "PnL source: MT5 broker positions + today deal history"
    : "PnL source: local deployment records";
  const isUpstoxBroker = brokerProviderLabel === "UPSTOX";
  const connectedMt5Broker = useMemo(
    () => brokerAccounts.find((item) => item.status === "CONNECTED" && (item.mode === "DEMO" || item.mode === "LIVE")),
    [brokerAccounts]
  );

  const loadSummary = async (silent = false) => {
    if (!deploymentId) return;
    try {
      if (!silent) setLoading(true);
      const [d, sm, accounts, candles, ready] = await Promise.all([
        liveTradingApi.getDeployment(deploymentId),
        liveTradingApi.getDeploymentSummary(deploymentId),
        liveTradingApi.listBrokerAccounts(),
        liveTradingApi.getDeploymentCandles(deploymentId, 5).catch(() => null),
        liveTradingApi.getDeploymentReadiness(deploymentId).catch(() => null),
      ]);
      setDeployment(d);
      setSummary(sm);
      setBrokerAccounts(accounts);
      if (ready) setReadiness(ready);
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

  const syncBroker = async () => {
    if (!deploymentId || !deployment?.broker_account_id) return;
    try {
      setBrokerBusy(true);
      await liveTradingApi.syncDeploymentBroker(deploymentId);
      showToast("Broker orders/positions synced", "success");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Failed to sync broker", "error");
    } finally {
      setBrokerBusy(false);
    }
  };


  const attachConnectedBroker = async () => {
    if (!deploymentId || !connectedMt5Broker) {
      showToast("No connected broker found. Go to Brokers and click Test Connection first.", "error");
      return;
    }
    try {
      setBrokerBusy(true);
      await liveTradingApi.updateDeployment(deploymentId, { mode: "DEMO", broker_account_id: connectedMt5Broker.id });
      showToast("Broker linked to this deployment", "success");
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
    if (mode !== "DEMO" && mode !== "LIVE") {
      showToast("Broker candle snapshot is available for DEMO/LIVE broker deployments only", "error");
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
    const timer = setInterval(() => loadSummary(true), 15000);
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

  const toggleAutoTrade = async (enabled: boolean) => {
    if (!deploymentId) return;
    try {
      setBusy(true);
      if (enabled) {
        const compat = await liveTradingApi.runCompatibilityCheck(deploymentId);
        if (compat.status === "FAIL") {
          showToast(compat.summary || "Live compatibility failed. Fix failed checks before enabling Auto Trade.", "error");
          return;
        }
      }
      await liveTradingApi.updateDeployment(deploymentId, { auto_trade_enabled: enabled });
      showToast(enabled ? "Auto Trade enabled" : "Auto Trade disabled", "success");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Failed to update Auto Trade", "error");
    } finally {
      setBusy(false);
    }
  };

  const runFullDryTest = async () => {
    if (!deploymentId) return;
    if (!isRunning) {
      showToast("Start deployment before running full dry test", "error");
      return;
    }
    if ((mode === "DEMO" || mode === "LIVE") && isBrokerBlocked) {
      showToast("Broker full dry test requires a connected broker", "error");
      return;
    }
    try {
      setRunnerBusy(true);
      const result = await liveTradingApi.runFullDryTest(deploymentId);
      setFullDryTest(result);
      setRunnerResult(`${result.signal || "HOLD"} • ${result.message || result.final_action}`);
      showToast(result.message || "Full dry test completed", result.success ? "success" : "error");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Full dry test failed", "error");
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



  const title = summary?.deployment?.name || deployment?.name || "Live Deployment";
  const subtitle = `${summary?.deployment?.strategy_name || deployment?.strategy_id || "Strategy"} • ${summary?.deployment?.instrument || deployment?.instrument || "—"} • ${summary?.deployment?.timeframe || deployment?.timeframe || "—"}`;

  if (loading) return <PageShell><GlassCard className="p-6 text-purple-100">Loading deployment...</GlassCard></PageShell>;
  if (!deployment || !summary) return <PageShell><NoRows label="No record found" /></PageShell>;

  return (
    <PageShell>
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={
          <>
            <Link href="/live-trading"><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link>
            <Button onClick={() => loadSummary(true)} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="h-4 w-4" />Refresh</Button>
            <Link href={`/live-trading/${deployment.id}/settings`}><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><Settings className="h-4 w-4" />Settings</Button></Link>
          </>
        }
      />

      <ReadinessChecklist readiness={readiness} onRunFullDryTest={runFullDryTest} dryTestDisabled={runnerBusy || !isRunning || isPaperDeprecated || isBrokerBlocked} />

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div>
            <h2 className="text-xl font-bold text-lime-300">Strategy Runner</h2>
            <p className="mt-1 max-w-2xl text-sm text-purple-200">Runs the selected strategy on the latest closed broker candles. Auto Trade only places orders after the live engine status and risk checks pass.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={busy || isPaperDeprecated} onClick={() => action("start")} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-4 w-4" />Start</Button>
            <Button disabled={busy} onClick={() => action("pause")} className="gap-2 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-4 w-4" />Pause</Button>
            <Button disabled={busy} onClick={() => action("stop")} variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-4 w-4" />Stop</Button>
            <Button disabled={runnerBusy || !isRunning || !summary.deployment?.auto_trade_enabled} onClick={() => autoRunnerAction("run-now")} variant="outline" className="gap-2 border-cyan-400/30 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20"><RefreshCw className="h-4 w-4" />Run Strategy Once</Button>
            <Button disabled={busy} onClick={() => toggleAutoTrade(!summary.deployment?.auto_trade_enabled)} className="gap-2 bg-fuchsia-500 text-white hover:bg-fuchsia-400">{summary.deployment?.auto_trade_enabled ? "Disable Auto Trade" : "Enable Auto Trade"}</Button>
            <Button disabled={runnerBusy || !isRunning || !summary.deployment?.auto_trade_enabled} onClick={() => autoRunnerAction(summary.deployment?.auto_runner_enabled ? "disable" : "enable")} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400">{summary.deployment?.auto_runner_enabled ? "Disable Auto Runner" : "Enable Auto Runner"}</Button>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
          <MetricCard label="Strategy" value={summary.deployment?.strategy_name || deployment.strategy_id || "—"} />
          <MetricCard label="Last Run" value={date(summary.deployment?.last_runner_at || deployment.last_runner_at)} />
          <MetricCard label="Last Processed Candle" value={date(summary.deployment?.last_processed_candle_time || deployment.last_processed_candle_time)} />
          <MetricCard label="Last Signal" value={recentSignals[0]?.signal_type || "—"} />
          <MetricCard label="Auto Trade" value={summary.deployment?.auto_trade_enabled ? "ON" : "OFF"} />
          <MetricCard label="Latest Order" value={recentOrders[0]?.status || "—"} />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <StatusBadge value={summary.deployment?.status || deployment.status} />
          <Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">{mode}</Badge>
          <Badge className={summary.deployment?.auto_runner_enabled ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : "border-yellow-400/30 bg-yellow-400/20 text-yellow-100"}>Auto Runner {summary.deployment?.auto_runner_enabled ? "ON" : "OFF"}</Badge>
          <span className="text-sm text-purple-200">Last signal: {date(summary.deployment?.last_signal_at || deployment.last_signal_at)}</span>
        </div>
        {runnerResult && <p className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100">Latest runner log: {runnerResult}</p>}
      </GlassCard>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-7">
        <MetricCard label="Equity" value={formatMoney(metrics?.equity ?? metrics?.effective_capital ?? deployment.capital, currency)} />
        <MetricCard label="Realized PnL" value={formatMoney(metrics?.realized_pnl, currency)} />
        <MetricCard label="Unrealized PnL" value={formatMoney(metrics?.unrealized_pnl, currency)} />
        <MetricCard label="Today PnL" value={formatMoney(metrics?.today_pnl, currency)} />
        <MetricCard label="Open Positions" value={String(metrics?.open_positions ?? 0)} />
        <MetricCard label="Orders Today" value={String(metrics?.orders_today ?? 0)} />
        <MetricCard label="Signals Today" value={String(metrics?.signals_today ?? 0)} />
      </div>
      <div className="mb-6 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-purple-100">
        {pnlSourceLabel}{metrics?.broker_deal_count !== undefined && metrics?.broker_deal_count !== null ? ` • Deals today: ${metrics.broker_deal_count}` : ""}
      </div>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div><h2 className="text-xl font-bold text-lime-300">Broker Summary</h2><p className="mt-1 text-sm text-purple-200">DEMO and approved LIVE deployments use a connected broker account. Broker Sync reads positions/orders; it does not place new orders.</p><p className="mt-1 text-xs text-purple-300">{pnlSourceLabel}</p></div>
          <div className="flex flex-wrap gap-2">
            {!broker && connectedMt5Broker && <Button disabled={brokerBusy} onClick={attachConnectedBroker} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><Link2 className="h-4 w-4" />Attach Broker</Button>}
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={() => refreshBroker()} className="gap-2 bg-blue-500 text-white hover:bg-blue-400"><RefreshCw className="h-4 w-4" />Refresh Broker</Button>
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={syncBroker} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><RefreshCw className="h-4 w-4" />Sync Broker</Button>
          </div>
        </div>
        {!broker ? (
          <div className="mt-4 space-y-3">
            <NoRows label="No broker account connected to this deployment. DEMO/LIVE execution requires an approved connected broker." />
            {connectedMt5Broker ? <p className="text-sm text-lime-200">Connected broker found: {connectedMt5Broker.account_label}. Click Attach Broker to link it to this deployment.</p> : <p className="text-sm text-yellow-100">No connected broker found. Go to Brokers and click Test Connection first.</p>}
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
          </div>
        )}
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="mb-4 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-xl font-bold text-white">Open Positions</h2>
            <p className="mt-1 text-sm text-purple-200">Broker positions are monitored through broker SL/TP and AlgoAgentX syncs updates for visibility.</p>
          </div>
          <Badge className="border-lime-400/30 bg-lime-400/20 text-lime-100">{metrics?.broker_synced ? `${brokerProviderLabel} synced` : "DB view"}</Badge>
        </div>
        {openPositions.length === 0 ? <NoRows label="No open positions" /> : <div className="responsive-table-wrapper overflow-x-auto"><table className="w-full min-w-[860px] text-left text-sm"><thead className="text-purple-200"><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Avg Entry</th><th>Current</th><th>SL</th><th>Target</th><th>Unrealized PnL</th><th>Status</th><th>Managed By</th><th>Opened At</th></tr></thead><tbody className="divide-y divide-white/10">{openPositions.map((p) => <tr key={p.id} className="text-purple-50"><td className="py-3">{p.symbol}</td><td>{p.side}</td><td>{num(p.qty)}</td><td>{num(p.avg_entry_price)}</td><td>{num(p.current_price)}</td><td>{num(p.stop_loss)}</td><td>{num(p.target)}</td><td>{formatMoney(p.unrealized_pnl, currency)}</td><td>{p.status}</td><td>Broker SL/TP Sync</td><td>{openedAtDisplay(p)}</td></tr>)}</tbody></table></div>}
      </GlassCard>

      <LiveFlowPanel />

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Advanced Diagnostics</h2>
            <p className="mt-1 text-sm text-purple-200">Market data snapshot, signal/order history, dry test details, and technical logs are hidden by default.</p>
          </div>
          <Button onClick={() => setShowAdvancedDiagnostics((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">
            {showAdvancedDiagnostics ? "Hide Advanced Diagnostics" : "Show Advanced Diagnostics"}
          </Button>
        </div>
      </GlassCard>

      {showAdvancedDiagnostics && (
        <>
          <OrderCalculationAuditPanel
            preview={((recentOrders || [])[0]?.raw_response as any)?.audit_preview || ((recentOrders || [])[0]?.raw_response as any)?.sizing}
            latestOrder={(recentOrders || [])[0]}
            latestSignal={(recentSignals || [])[0]}
            currency={currency}
            showPayload={false}
            defaultExpanded={false}
            subtitle="Advanced view of the latest signal, SL/TP, risk, lot/qty, and validation result."
          />
          {fullDryTest && (
            <GlassCard className="mb-6 p-6" hoverEffect={false}>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-xl font-bold text-white">Dry Test Details</h2>
                  <p className="text-sm text-purple-200">Final simulated action: <span className="font-semibold text-cyan-100">{fullDryTest.final_action}</span></p>
                </div>
                <Badge className={fullDryTest.success ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : "border-red-400/30 bg-red-400/20 text-red-100"}>{fullDryTest.success ? "PASSED" : "REJECTED"}</Badge>
              </div>
              <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
                {(fullDryTest.steps || []).map((step, index) => (
                  <div key={`${step.name}-${index}`} className="rounded-xl border border-white/10 bg-purple-950/30 p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <ReadinessIcon status={step.status === "PASS" ? "PASS" : step.status === "WARNING" ? "WARNING" : "FAIL"} />
                      <span className="font-semibold text-white">{index + 1}. {step.name}</span>
                      <Badge className={step.status === "PASS" ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : step.status === "WARNING" ? "border-yellow-400/30 bg-yellow-400/20 text-yellow-100" : "border-red-400/30 bg-red-400/20 text-red-100"}>{step.status}</Badge>
                    </div>
                    <p className="mt-1 text-purple-200">{step.message}</p>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          <GlassCard className="mb-6 p-6" hoverEffect={false}>
            <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
              <div>
                <h2 className="text-xl font-bold text-lime-300">Market Data Snapshot</h2>
                <p className="mt-1 text-sm text-purple-200">Latest closed candles stored from MT5 or UPSTOX for the live strategy runner. No chart and no fake data.</p>
              </div>
              <Button disabled={candleBusy || mode !== "DEMO" || !broker || broker.status !== "CONNECTED"} onClick={refreshCandles} className="gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-400"><RefreshCw className="h-4 w-4" /> Refresh Candles</Button>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-6">
              <MetricCard label="Data Source" value={candleSource} />
              <MetricCard label="Deployment Symbol" value={candleSnapshot?.symbol || summary.deployment?.instrument || deployment.instrument} />
              <MetricCard label={isUpstoxBroker ? "Instrument Key" : "Broker Symbol"} value={candleSnapshot?.instrument_key || candleSnapshot?.resolved_symbol || deployment.instrument_key || deployment.broker_symbol || candleSnapshot?.symbol || summary.deployment?.instrument || deployment.instrument} />
              <MetricCard label="Timeframe" value={candleSnapshot?.timeframe || summary.deployment?.timeframe || deployment.timeframe} />
              <MetricCard label="Candles Stored" value={String(candleSnapshot?.stored_count ?? 0)} />
              <MetricCard label="Latest Close" value={num(candleSnapshot?.latest_close)} />
            </div>
            <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">Latest candle time: <span className="font-semibold text-white">{date(candleSnapshot?.latest_candle_time)}</span></div>
            {latestCandles.length === 0 ? <div className="mt-4"><NoRows label="No broker candles stored yet. For Upstox, make sure instrument_key is set. For MT5, open Market Watch → Show All and open the symbol chart once." /></div> : (
              <div className="responsive-table-wrapper mt-4 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="text-purple-200"><tr><th>Time</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Volume</th></tr></thead><tbody className="divide-y divide-white/10">{latestCandles.map((candle, index) => <tr key={candle.id || `${candle.candle_time}-${index}`} className="text-purple-50"><td className="py-3">{date(candle.candle_time)}</td><td>{num(candle.open)}</td><td>{num(candle.high)}</td><td>{num(candle.low)}</td><td>{num(candle.close)}</td><td>{num(candle.volume)}</td></tr>)}</tbody></table></div>
            )}
          </GlassCard>

          <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
            <GlassCard className="p-6" hoverEffect={false}>
              <div className="mb-4 flex items-center justify-between gap-2"><div><h2 className="text-xl font-bold text-white">Recent Signals</h2><p className="mt-1 text-sm text-purple-200">Detailed signal history.</p></div><Button size="sm" onClick={() => setShowSignals((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{showSignals ? "Hide" : "Open Signals"}</Button></div>
              {!showSignals ? <NoRows label={`Signals are hidden. Total today: ${metrics?.signals_today ?? 0}.`} /> : recentSignals.length === 0 ? <NoRows label="No signals yet" /> : <div className="responsive-table-wrapper max-h-[360px] overflow-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="sticky top-0 bg-purple-950 text-purple-200"><tr><th className="p-3">Time</th><th>Source</th><th>Signal</th><th>Symbol</th><th>Price</th><th>Status</th><th>Reason</th></tr></thead><tbody className="divide-y divide-white/10">{recentSignals.map((sig) => <tr key={sig.id} className="text-purple-50"><td className="p-3">{date(sig.created_at)}</td><td>{sig.source}</td><td>{sig.signal_type}</td><td>{sig.symbol}</td><td>{num(sig.price)}</td><td>{sig.status}</td><td className="max-w-[260px] truncate" title={sig.rejection_reason || sig.reason || "-"}>{sig.rejection_reason || sig.reason || "-"}</td></tr>)}</tbody></table></div>}
            </GlassCard>
            <GlassCard className="p-6" hoverEffect={false}>
              <div className="mb-4 flex items-center justify-between gap-2"><div><h2 className="text-xl font-bold text-white">Recent Orders</h2><p className="mt-1 text-sm text-purple-200">Detailed order history.</p></div><Button size="sm" onClick={() => setShowOrders((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{showOrders ? "Hide" : "Open Orders"}</Button></div>
              {!showOrders ? <NoRows label={`Orders are hidden. Total today: ${metrics?.orders_today ?? 0}.`} /> : recentOrders.length === 0 ? <NoRows label="No orders yet" /> : <div className="responsive-table-wrapper max-h-[360px] overflow-auto"><table className="w-full min-w-[980px] text-left text-sm"><thead className="sticky top-0 bg-purple-950 text-purple-200"><tr><th className="p-3">Time</th><th>Side</th><th>Symbol</th><th>Qty</th><th>Entry</th><th>Executed</th><th>SL</th><th>Target</th><th>Status</th><th>Broker Order ID</th><th>Error</th></tr></thead><tbody className="divide-y divide-white/10">{recentOrders.map((o) => <tr key={o.id} className="text-purple-50"><td className="p-3">{date(o.created_at)}</td><td>{o.side}</td><td>{o.symbol}</td><td>{num(o.qty)}</td><td>{num(o.entry_price)}</td><td>{num(o.executed_price)}</td><td>{num(o.stop_loss)}</td><td>{num(o.target)}</td><td>{o.status}</td><td>{o.broker_order_id || "-"}</td><td className="max-w-[260px] truncate" title={o.error_message || "-"}>{o.error_message || "-"}</td></tr>)}</tbody></table></div>}
            </GlassCard>
          </div>

          <GlassCard className="p-6" hoverEffect={false}>
            <div className="mb-4 flex items-center justify-between gap-2"><h2 className="text-xl font-bold text-white">Technical Logs</h2><Button size="sm" onClick={() => setShowLogs((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{showLogs ? "Hide Technical Logs" : "Open Technical Logs"}</Button></div>
            {!showLogs ? <NoRows label="Technical logs are hidden by default. Open them only when troubleshooting." /> : recentLogs.length === 0 ? <NoRows label="No logs yet" /> : <div className="responsive-table-wrapper max-h-[360px] overflow-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="sticky top-0 bg-purple-950 text-purple-200"><tr><th className="p-3">Time</th><th>Level</th><th>Event Type</th><th>Message</th></tr></thead><tbody className="divide-y divide-white/10">{recentLogs.map((l) => <tr key={l.id} className="text-purple-50"><td className="p-3">{date(l.created_at)}</td><td>{l.level}</td><td>{l.event_type}</td><td>{l.message}</td></tr>)}</tbody></table></div>}
          </GlassCard>
        </>
      )}
    </PageShell>
  );
}
