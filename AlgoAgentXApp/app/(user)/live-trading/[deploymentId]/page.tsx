"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Activity, Clipboard, Link2, Pause, Play, RefreshCw, Send, Settings, ShieldCheck, Square, GitBranch } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, LiveCandleSnapshot, FullDryTestResponse, FinalQaResult, QaOrderTestResult, LiveDeploymentSummary, LiveReadiness, LiveReadinessCheck, SignalType, StrategyDeployment } from "@/types/live-trading";

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
    "Order is sent to broker or paper engine",
    "Position is monitored and synced",
  ];
  return (
    <GlassCard className="mb-6 p-6" hoverEffect={false}>
      <div className="mb-4 flex items-center gap-2">
        <Activity className="h-5 w-5 text-lime-300" />
        <div>
          <h2 className="text-xl font-bold text-white">Live Flow Explanation</h2>
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
        <div className="rounded-xl border border-white/10 bg-white/5 p-4"><span className="font-semibold text-white">PAPER mode</span> simulates orders inside AlgoAgentX.</div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-4"><span className="font-semibold text-white">DEMO mode</span> sends orders to your connected demo broker.</div>
      </div>
    </GlassCard>
  );
}

function ReadinessChecklist({ readiness }: { readiness: LiveReadiness | null }) {
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
  const [finalQa, setFinalQa] = useState<FinalQaResult | null>(null);
  const [qaTestResult, setQaTestResult] = useState<QaOrderTestResult | null>(null);
  const [demoConfirmText, setDemoConfirmText] = useState("");
  const [showFinalQaDetails, setShowFinalQaDetails] = useState(false);
  const [showDemoMicroConfirm, setShowDemoMicroConfirm] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [showSignals, setShowSignals] = useState(false);
  const [showOrders, setShowOrders] = useState(false);
  const [showAdvancedDiagnostics, setShowAdvancedDiagnostics] = useState(false);
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
  const brokerSync = summary?.broker_sync;
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
      const [d, sm, accounts, candles, ready] = await Promise.all([
        liveTradingApi.getDeployment(deploymentId),
        liveTradingApi.getDeploymentSummary(deploymentId),
        liveTradingApi.listBrokerAccounts(),
        liveTradingApi.getDeploymentCandles(deploymentId, 5).catch(() => null),
        liveTradingApi.getDeploymentReadiness(deploymentId).catch(() => null),
      ]);
      setDeployment(d);
      setSummary(sm);
      setLiveSyncInterval(String(sm?.deployment?.live_sync_interval_seconds || d?.live_sync_interval_seconds || 10));
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
      await liveTradingApi.updateDeployment(deploymentId, { auto_trade_enabled: enabled });
      showToast(enabled ? "Auto Trade enabled" : "Auto Trade disabled", "success");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Failed to update Auto Trade", "error");
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
    } catch (error: any) {
      showToast(error.message || "Strategy runner failed", "error");
    } finally {
      setRunnerBusy(false);
    }
  };

  const processPaperPositions = async () => {
    if (!deploymentId) return;
    try {
      setRunnerBusy(true);
      const result = await liveTradingApi.processPaperPositions(deploymentId);
      showToast(String(result.message || "Paper positions processed"), "success");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Failed to process paper positions", "error");
    } finally {
      setRunnerBusy(false);
    }
  };

  const runFullDryTest = async () => {
    if (!deploymentId) return;
    if (!isRunning) {
      showToast("Start deployment before running full dry test", "error");
      return;
    }
    if (mode === "DEMO" && isDemoBrokerBlocked) {
      showToast("DEMO full dry test requires connected broker", "error");
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


  const loadFinalQa = async () => {
    if (!deploymentId) return;
    try {
      setRunnerBusy(true);
      const result = await liveTradingApi.getFinalQa(deploymentId);
      setFinalQa(result);
      showToast(result.summary || "Final QA loaded", result.overall_status === "FAIL" ? "error" : "success");
    } catch (error: any) {
      showToast(error.message || "Final QA failed", "error");
    } finally {
      setRunnerBusy(false);
    }
  };

  const runPaperOrderTest = async () => {
    if (!deploymentId) return;
    if (!confirm("This creates a test paper position only. No broker order will be placed.")) return;
    try {
      setRunnerBusy(true);
      const result = await liveTradingApi.runPaperOrderTest(deploymentId, "BUY");
      setQaTestResult(result);
      showToast(result.message || "Paper order test completed", result.status === "OK" ? "success" : "error");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Paper order test failed", "error");
    } finally {
      setRunnerBusy(false);
    }
  };

  const runDemoMicroOrderTest = async () => {
    if (!deploymentId) return;
    if (mode === "LIVE") {
      showToast("Real live trading is locked for safety. Use PAPER or DEMO until final QA passes.", "error");
      return;
    }
    if (demoConfirmText.trim().toUpperCase() !== "DEMO") {
      showToast("Type DEMO before placing a demo micro order", "error");
      return;
    }
    try {
      setRunnerBusy(true);
      const result = await liveTradingApi.runDemoMicroOrderTest(deploymentId, { side: "BUY", confirm_demo_micro_order: true });
      setQaTestResult(result);
      setDemoConfirmText("");
      setShowDemoMicroConfirm(false);
      showToast(result.message || "Demo micro order test completed", result.status === "OK" ? "success" : "error");
      await loadSummary(true);
    } catch (error: any) {
      showToast(error.message || "Demo micro order test failed", "error");
    } finally {
      setRunnerBusy(false);
    }
  };

  const copyQaSummary = async () => {
    const qa = finalQa;
    const text = JSON.stringify({
      deployment_id: deploymentId,
      strategy: summary?.deployment?.strategy_name || deployment?.strategy_id,
      instrument: summary?.deployment?.instrument || deployment?.instrument,
      mode,
      readiness_status: readiness?.overall_status,
      final_qa_status: qa?.overall_status,
      last_error: qa?.last_results?.last_blocking_error || deployment?.runner_last_error,
      risk_preview: qa?.checks?.find((check) => check.key === "risk_preview_ok"),
      broker_status: broker?.status,
    }, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      showToast("QA summary copied", "success");
    } catch {
      showToast("Copy failed. Select and copy the QA summary manually.", "error");
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


  const finalQaChecks = finalQa?.checks || [];
  const finalQaPassed = finalQaChecks.filter((check) => check.status === "PASS").length;
  const finalQaTotal = finalQaChecks.length;
  const finalQaNeedsAttention = finalQaChecks.filter((check) => check.status !== "PASS").length;
  const finalQaStatus = finalQa?.overall_status || "—";
  const finalQaBadgeClass = finalQa?.overall_status === "PASS"
    ? "border-lime-400/30 bg-lime-400/20 text-lime-100"
    : finalQa?.overall_status === "WARNING"
      ? "border-yellow-400/30 bg-yellow-400/20 text-yellow-100"
      : "border-red-400/30 bg-red-400/20 text-red-100";
  const finalQaSummary = finalQaTotal
    ? `${finalQaPassed}/${finalQaTotal} checks passed${finalQaNeedsAttention ? ` • ${finalQaNeedsAttention} needs attention` : ""}`
    : "Run or view QA to load the checklist.";

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

      <ReadinessChecklist readiness={readiness} />


      <GlassCard className="mb-6 overflow-hidden p-0" hoverEffect={false}>
        <div className="border-b border-white/10 bg-gradient-to-r from-lime-400/10 via-purple-500/10 to-fuchsia-500/10 p-6">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-2xl font-bold text-lime-300">Final Demo QA</h2>
                <Badge className={finalQaBadgeClass}>Final QA {finalQaStatus}</Badge>
              </div>
              <p className="mt-2 text-sm text-purple-100">Controlled final checks for PAPER and MT5 DEMO before any real live trading. LIVE mode remains locked for safety.</p>
              <p className="mt-1 text-xs text-purple-300">{finalQaSummary}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button disabled={runnerBusy} onClick={loadFinalQa} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">View Last QA Result</Button>
              <Button onClick={() => setShowFinalQaDetails((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{showFinalQaDetails ? "Hide QA Details" : "Show QA Details"}</Button>
              <Button size="sm" onClick={copyQaSummary} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><Clipboard className="h-4 w-4" />Copy QA Summary</Button>
            </div>
          </div>
          {mode === "LIVE" && (
            <div className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">Real live trading is locked for safety. Use PAPER or DEMO until final QA passes.</div>
          )}
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-5 shadow-xl">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-cyan-200">Step 1</p>
                  <h3 className="text-lg font-bold text-white">Dry Test</h3>
                </div>
                <RefreshCw className="h-5 w-5 text-cyan-200" />
              </div>
              <p className="min-h-[42px] text-sm text-purple-100">Simulates one full runner cycle without placing any order.</p>
              <Button disabled={runnerBusy} onClick={runFullDryTest} className="mt-4 w-full bg-cyan-500 text-slate-950 hover:bg-cyan-400">Run Full Dry Test</Button>
            </div>

            <div className="rounded-2xl border border-lime-400/20 bg-lime-500/10 p-5 shadow-xl">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-lime-200">Step 2</p>
                  <h3 className="text-lg font-bold text-white">Paper Order Test</h3>
                </div>
                <ShieldCheck className="h-5 w-5 text-lime-200" />
              </div>
              <p className="min-h-[42px] text-sm text-purple-100">Creates a test paper position only. No broker order is placed.</p>
              <Button disabled={runnerBusy || mode !== "PAPER"} onClick={runPaperOrderTest} className="mt-4 w-full bg-lime-500 text-slate-950 hover:bg-lime-400">Run Paper Order Test</Button>
              {mode !== "PAPER" && <p className="mt-2 text-xs text-purple-300">Available only for PAPER deployments.</p>}
            </div>

            <div className="rounded-2xl border border-fuchsia-400/20 bg-fuchsia-500/10 p-5 shadow-xl">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-fuchsia-200">Step 3</p>
                  <h3 className="text-lg font-bold text-white">Demo Micro Order</h3>
                </div>
                <Send className="h-5 w-5 text-fuchsia-200" />
              </div>
              <p className="min-h-[42px] text-sm text-purple-100">Places a tiny order on your DEMO broker only after confirmation.</p>
              <Button disabled={mode !== "DEMO" || runnerBusy} onClick={() => setShowDemoMicroConfirm(true)} className="mt-4 w-full bg-fuchsia-500 text-white hover:bg-fuchsia-400">Open Demo Micro Test</Button>
              {mode !== "DEMO" && <p className="mt-2 text-xs text-purple-300">Available only for DEMO deployments.</p>}
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={syncBroker} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">Sync Broker Now</Button>
            <Button disabled={runnerBusy} onClick={loadFinalQa} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">Refresh QA Status</Button>
          </div>

          {showDemoMicroConfirm && (
            <div className="mt-5 rounded-2xl border border-yellow-400/30 bg-yellow-500/10 p-5 shadow-xl">
              <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                <div>
                  <p className="text-sm font-semibold text-yellow-100">Confirm Demo Micro Order</p>
                  <p className="mt-1 text-sm text-purple-100">This will place a real order on your DEMO broker account only. It will not use real money. Type <span className="font-bold text-white">DEMO</span> to confirm.</p>
                </div>
                <Button onClick={() => { setShowDemoMicroConfirm(false); setDemoConfirmText(""); }} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">Cancel</Button>
              </div>
              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <input value={demoConfirmText} onChange={(event) => setDemoConfirmText(event.target.value)} placeholder="Type DEMO" className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300" />
                <Button disabled={runnerBusy || mode !== "DEMO" || demoConfirmText.trim().toUpperCase() !== "DEMO"} onClick={runDemoMicroOrderTest} className="bg-fuchsia-500 text-white hover:bg-fuchsia-400">Confirm Demo Micro Order</Button>
              </div>
            </div>
          )}

          {showFinalQaDetails && finalQa && (
            <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-2">
              {finalQa.checks?.map((check) => (
                <div key={check.key} className="rounded-xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center gap-2">
                    <ReadinessIcon status={check.status === "PASS" ? "PASS" : check.status === "WARNING" ? "WARNING" : "FAIL"} />
                    <p className="font-semibold text-white">{check.label}</p>
                    <Badge className={check.status === "PASS" ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : check.status === "WARNING" ? "border-yellow-400/30 bg-yellow-400/20 text-yellow-100" : "border-red-400/30 bg-red-400/20 text-red-100"}>{check.status}</Badge>
                  </div>
                  <p className="mt-2 text-sm text-purple-200">{check.message}</p>
                </div>
              ))}
            </div>
          )}

          {showFinalQaDetails && (finalQa?.last_results || qaTestResult) && (
            <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-2">
              <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">
                <h3 className="mb-2 font-semibold text-white">QA Result Card</h3>
                <p>Last dry test: {finalQa?.last_results?.last_dry_test ? "Available" : "—"}</p>
                <p>Last paper test: {finalQa?.last_results?.last_paper_test ? "Available" : "—"}</p>
                <p>Last demo micro test: {finalQa?.last_results?.last_demo_micro_test ? "Available" : "—"}</p>
                <p>Last broker sync: {date(String(finalQa?.last_results?.last_broker_sync || ""))}</p>
                <p>Last auto runner cycle: {date(String(finalQa?.last_results?.last_auto_runner_cycle || ""))}</p>
                <p>Last blocking error: {JSON.stringify(finalQa?.last_results?.last_blocking_error || null)}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="font-semibold text-white">Support / Debug Summary</h3>
                  <Button size="sm" onClick={copyQaSummary} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><Clipboard className="h-4 w-4" />Copy QA Summary</Button>
                </div>
                <pre className="max-h-56 overflow-auto whitespace-pre-wrap text-xs text-purple-100">{JSON.stringify(qaTestResult || finalQa?.debug_summary || {}, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge value={summary.deployment?.status || deployment.status} />
            <Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">{mode}</Badge>
            <Badge className={summary.deployment?.auto_trade_enabled ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : "border-yellow-400/30 bg-yellow-400/20 text-yellow-100"}>Auto Trade {summary.deployment?.auto_trade_enabled ? "ON" : "OFF"}</Badge>
            <Badge className={summary.deployment?.auto_runner_enabled ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : "border-yellow-400/30 bg-yellow-400/20 text-yellow-100"}>Auto Runner {summary.deployment?.auto_runner_enabled ? "ON" : "OFF"}</Badge>
            <span className="text-sm text-purple-200">Last signal: {date(summary.deployment?.last_signal_at || deployment.last_signal_at)}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={busy} onClick={() => action("start")} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-4 w-4" />Start</Button>
            <Button disabled={busy} onClick={() => action("pause")} className="gap-2 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-4 w-4" />Pause</Button>
            <Button disabled={busy} onClick={() => action("stop")} variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-4 w-4" />Stop</Button>
            <Button disabled={runnerBusy || !isRunning || (mode === "DEMO" && isDemoBrokerBlocked)} onClick={runFullDryTest} variant="outline" className="gap-2 border-cyan-400/30 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20"><RefreshCw className="h-4 w-4" />Run Full Dry Test</Button>
            <Button disabled={busy} onClick={() => toggleAutoTrade(!summary.deployment?.auto_trade_enabled)} className="gap-2 bg-fuchsia-500 text-white hover:bg-fuchsia-400">{summary.deployment?.auto_trade_enabled ? "Disable Auto Trade" : "Enable Auto Trade"}</Button>
            <Button disabled={runnerBusy || !isRunning || !summary.deployment?.auto_trade_enabled} onClick={() => autoRunnerAction(summary.deployment?.auto_runner_enabled ? "disable" : "enable")} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400">{summary.deployment?.auto_runner_enabled ? "Disable Auto Runner" : "Enable Auto Runner"}</Button>
          </div>
        </div>
        {runnerResult && <p className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100">Last dry/runner result: {runnerResult}</p>}
        {fullDryTest && (
          <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="font-bold text-white">Full Dry Test Timeline</h3>
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
          </div>
        )}
      </GlassCard>

      <LiveFlowPanel />

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
          <div><h2 className="text-xl font-bold text-lime-300">Broker Summary</h2><p className="mt-1 text-sm text-purple-200">PAPER works without a broker. DEMO sends orders to your connected demo broker. Broker Sync only reads positions/orders; it does not place new orders.</p></div>
          <div className="flex flex-wrap gap-2">
            {!broker && connectedMt5Broker && <Button disabled={brokerBusy} onClick={attachConnectedBroker} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><Link2 className="h-4 w-4" />Attach Demo Broker</Button>}
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={() => refreshBroker()} className="gap-2 bg-blue-500 text-white hover:bg-blue-400"><RefreshCw className="h-4 w-4" />Refresh Broker</Button>
            <Button disabled={brokerBusy || !deployment.broker_account_id} onClick={syncBroker} className="gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><RefreshCw className="h-4 w-4" />Sync Broker</Button>
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
          </div>
        )}
      </GlassCard>

      <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <GlassCard className="p-6 xl:col-span-2" hoverEffect={false}>
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-xl font-bold text-white">Open Position</h2>
              <p className="mt-1 text-sm text-purple-200">PAPER positions are closed by AlgoAgentX using candles. DEMO positions are usually closed by broker SL/TP and AlgoAgentX syncs them.</p>
            </div>
            <Badge className="border-lime-400/30 bg-lime-400/20 text-lime-100">{metrics?.broker_synced ? `${brokerProviderLabel} synced` : "DB view"}</Badge>
          </div>
          {openPositions.length === 0 ? <NoRows label="No open positions" /> : <div className="responsive-table-wrapper overflow-x-auto"><table className="w-full min-w-[860px] text-left text-sm"><thead className="text-purple-200"><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Avg Entry</th><th>Current</th><th>SL</th><th>Target</th><th>Unrealized PnL</th><th>Status</th><th>Managed By</th><th>Opened At</th></tr></thead><tbody className="divide-y divide-white/10">{openPositions.map((p) => <tr key={p.id} className="text-purple-50"><td className="py-3">{p.symbol}</td><td>{p.side}</td><td>{num(p.qty)}</td><td>{num(p.avg_entry_price)}</td><td>{num(p.current_price)}</td><td>{num(p.stop_loss)}</td><td>{num(p.target)}</td><td>{formatMoney(p.unrealized_pnl, currency)}</td><td>{p.status}</td><td>{mode === "PAPER" ? "AlgoAgentX Paper Engine" : "Broker SL/TP Sync"}</td><td>{date(p.opened_at)}</td></tr>)}</tbody></table></div>}
        </GlassCard>
        <GlassCard className="p-6" hoverEffect={false}>
          <h2 className="text-xl font-bold text-white">Latest Activity</h2>
          <div className="mt-4 space-y-3 text-sm text-purple-100">
            <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-purple-300">Latest Signal</p><p className="mt-1 font-semibold text-white">{summary.latest_signal ? `${summary.latest_signal.signal_type} • ${date(summary.latest_signal.created_at)}` : "—"}</p></div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-purple-300">Latest Order</p><p className="mt-1 font-semibold text-white">{summary.latest_order ? `${summary.latest_order.status} • ${summary.latest_order.side} ${summary.latest_order.symbol}` : "—"}</p></div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-purple-300">Today PnL</p><p className="mt-1 font-semibold text-white">{formatMoney(metrics?.today_pnl, currency)}</p></div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-purple-300">Last Runner Cycle</p><p className="mt-1 font-semibold text-white">{runner?.last_execution_decision || runner?.latest_runner_log || "—"}</p></div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-purple-300">Last Entry Plan</p><p className="mt-1 font-semibold text-white">{runner?.last_entry_plan ? `SL ${num((runner.last_entry_plan as any).stop_loss)} • TP ${num((runner.last_entry_plan as any).target)}` : "—"}</p></div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-purple-300">Last Risk Preview</p><p className="mt-1 font-semibold text-white">{runner?.last_risk_preview ? `${(runner.last_risk_preview as any).quantity_mode || ""} ${num((runner.last_risk_preview as any).final_lot || (runner.last_risk_preview as any).final_quantity)}` : "—"}</p></div>
          </div>
        </GlassCard>
      </div>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Advanced Diagnostics</h2>
            <p className="mt-1 text-sm text-purple-200">Market data snapshot, runner status, signal/order history, and execution logs are hidden by default.</p>
          </div>
          <Button onClick={() => setShowAdvancedDiagnostics((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">
            {showAdvancedDiagnostics ? "Hide Advanced Diagnostics" : "Show Advanced Diagnostics"}
          </Button>
        </div>
      </GlassCard>

      {showAdvancedDiagnostics && (
        <>
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
            {summary.deployment?.live_sync_last_error && <p className="mt-2 rounded-xl border border-red-400/20 bg-red-500/10 p-3 text-sm text-red-100">Last error: {summary.deployment.live_sync_last_error}</p>}
          </GlassCard>

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
              <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
                <div><h2 className="text-xl font-bold text-lime-300">Strategy Runner</h2><p className="mt-1 text-sm text-purple-200">Runs selected strategy on latest closed live_market_candles. DEMO refreshes broker candles first. No tick execution.</p></div>
                <div className="flex flex-wrap gap-2">
                  <Button disabled={runnerBusy || !isRunning || (mode === "DEMO" && isDemoBrokerBlocked)} onClick={() => runStrategy(true)} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-4 w-4" />Run Strategy Once</Button>
                  <Button disabled={runnerBusy || !isRunning || (mode === "DEMO" && isDemoBrokerBlocked)} onClick={() => runStrategy(false)} variant="outline" className="gap-2 border-cyan-400/30 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20"><RefreshCw className="h-4 w-4" />Dry Run Strategy</Button>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
                <MetricCard label="Strategy" value={summary.deployment?.strategy_name || deployment.strategy_id} />
                <MetricCard label="Last Run" value={date(runner?.last_run_at)} />
                <MetricCard label="Last Processed Candle" value={date(runner?.last_processed_candle_time || runner?.last_candle_time || candleSnapshot?.latest_candle_time)} />
                <MetricCard label="Last Signal" value={runner?.last_signal || summary.latest_signal?.signal_type || "—"} />
                <MetricCard label="Auto Trade" value={summary.deployment?.auto_trade_enabled ? "ON" : "OFF"} />
                <MetricCard label="Latest Order" value={runner?.latest_order_status || summary.latest_order?.status || "—"} />
              </div>
              <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">Latest runner log: <span className="font-semibold text-white">{runnerResult || runner?.latest_runner_log || "—"}</span></div>
            </GlassCard>

            <GlassCard className="p-6" hoverEffect={false}>
              <h2 className="text-xl font-bold text-lime-300">Manual Signal Test</h2>
              <p className="mt-1 text-sm text-purple-200">Use only for controlled demo/paper validation. Dry Run is safer for beginner testing.</p>
              {lastResult && <p className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100">Last result: {lastResult}</p>}
              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
                <label className="text-sm text-purple-100">Price<input value={manualPrice} onChange={(e) => setManualPrice(e.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300" /></label>
                <label className="text-sm text-purple-100 md:col-span-2">Reason<input value={manualReason} onChange={(e) => setManualReason(e.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300" /></label>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">{(["BUY", "SELL", "EXIT", "HOLD"] as SignalType[]).map((signal) => <Button key={signal} disabled={busy || !isRunning || isDemoBrokerBlocked} onClick={() => sendManualSignal(signal)} className="gap-2 bg-fuchsia-500 text-white hover:bg-fuchsia-400"><Send className="h-4 w-4" />{signal}</Button>)}</div>
            </GlassCard>
          </div>

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
            <div className="mb-4 flex items-center justify-between gap-2"><h2 className="text-xl font-bold text-white">Execution Logs</h2><Button size="sm" onClick={() => setShowLogs((value) => !value)} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{showLogs ? "Hide" : "Open Logs"}</Button></div>
            {!showLogs ? <NoRows label="Logs are hidden by default. Click Open Logs when you need execution details." /> : recentLogs.length === 0 ? <NoRows label="No logs yet" /> : <div className="responsive-table-wrapper max-h-[360px] overflow-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="sticky top-0 bg-purple-950 text-purple-200"><tr><th className="p-3">Time</th><th>Level</th><th>Event Type</th><th>Message</th></tr></thead><tbody className="divide-y divide-white/10">{recentLogs.map((l) => <tr key={l.id} className="text-purple-50"><td className="p-3">{date(l.created_at)}</td><td>{l.level}</td><td>{l.event_type}</td><td>{l.message}</td></tr>)}</tbody></table></div>}
          </GlassCard>
        </>
      )}
    </PageShell>
  );
}
