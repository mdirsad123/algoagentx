"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Activity, Link2, RefreshCw, Settings, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { OrderCalculationAuditPanel } from "@/components/live/OrderCalculationAuditPanel";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import axiosInstance from "@/lib/axios";
import type { BrokerAccount, LiveCandleSnapshot, FullDryTestResponse, LiveDeploymentSummary, LiveLatencyResponse, LivePipelineHealth, LiveReadiness, LiveReadinessCheck, StrategyDeployment } from "@/types/live-trading";
import { formatDateTimeIST } from "@/lib/timezone";

const date = (value?: string | null) => formatDateTimeIST(value);
const dateWithSeconds = (value?: string | null) => formatDateTimeIST(value, { seconds: true });
const num = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 4 });
const pct = (value: unknown) => value === null || value === undefined || value === "" ? "—" : `${(Number(value) * 100).toFixed(2)}%`;

// Keep pipeline health independent from the large liveTradingApi object. Older
// production bundles can briefly contain a stale copy of that object while the
// deployment page itself is already on the new build, which previously caused
// `getDeploymentPipelineHealth is not a function`. This direct client uses the
// same authenticated axios instance and the same backend route, so health UI can
// recover cleanly even during a mixed/stale browser bundle transition.
const getDeploymentPipelineHealthDirect = async (deploymentId: string): Promise<LivePipelineHealth> => {
  const response = await axiosInstance.get(`/api/v1/live/deployments/${deploymentId}/pipeline-health`);
  const payload = response.data as { success?: boolean; data?: LivePipelineHealth } | LivePipelineHealth;
  if (payload && typeof payload === "object" && "success" in payload) {
    return ((payload as { data?: LivePipelineHealth }).data ?? {}) as LivePipelineHealth;
  }
  return payload as LivePipelineHealth;
};

const openedAtDisplay = (p: { opened_at?: string | null; broker_opened_at?: string | null; broker_opened_at_raw?: string | null }) => {
  const broker = p.broker_opened_at ? date(p.broker_opened_at) : p.broker_opened_at_raw || null;
  const local = date(p.opened_at);
  if (broker) {
    return (
      <div className="space-y-0.5 text-xs leading-5" title="Normalized display timezone: Asia/Kolkata (UTC+05:30).">
        <div>Broker → IST: {broker}</div>
        <div className="text-purple-300">AlgoAgentX IST: {local}</div>
      </div>
    );
  }
  return <span title="Shown in Asia/Kolkata (UTC+05:30).">IST: {local}</span>;
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

const formatOptionalMoney = (value: unknown, currency?: string | null) => {
  if (value === null || value === undefined || value === "") return "Unavailable";
  return formatMoney(value, currency);
};

function NoRows({ label }: { label: string }) {
  return <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-200">{label}</div>;
}

function StatusBadge({ value }: { value?: string }) {
  const color = value === "RUNNING" ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : value === "PAUSED" ? "border-yellow-400/30 bg-yellow-400/20 text-yellow-100" : value === "ERROR" ? "border-red-400/30 bg-red-400/20 text-red-100" : "border-purple-300/30 bg-purple-400/20 text-purple-100";
  return <Badge className={color}>{value || "—"}</Badge>;
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 overflow-hidden rounded-xl border border-white/10 bg-white/5 p-4">
      <p className="text-xs leading-4 text-purple-300 break-words [overflow-wrap:anywhere]">{label}</p>
      <p
        className="mt-2 min-w-0 break-words text-lg font-bold leading-tight text-white sm:text-xl [overflow-wrap:anywhere] 2xl:text-2xl"
        title={value}
      >
        {value}
      </p>
    </div>
  );
}


function ControlToggle({
  label,
  active,
  disabled,
  onClick,
  tone = "lime",
}: {
  label: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  tone?: "lime" | "yellow" | "red" | "cyan" | "fuchsia";
}) {
  // All enabled/active controls use the same green state so the operator can
  // scan the runner toolbar instantly. The inactive state intentionally stays
  // neutral/dim. `tone` is kept in the API for backward compatibility.
  void tone;
  const activeClass = "border-emerald-400/60 bg-emerald-500/25 text-emerald-50 shadow-[0_0_0_1px_rgba(52,211,153,0.10)]";
  return (
    <button
      type="button"
      role="switch"
      aria-checked={active}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex h-9 items-center gap-2 rounded-full border px-3 text-xs font-semibold transition ${active ? activeClass : "border-white/10 bg-white/5 text-purple-200 hover:bg-white/10"} disabled:cursor-not-allowed disabled:opacity-40`}
    >
      <span className={`relative h-4 w-7 rounded-full ${active ? "bg-white/25" : "bg-slate-950/40"}`}>
        <span className={`absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all ${active ? "left-3.5" : "left-0.5"}`} />
      </span>
      {label}
    </button>
  );
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
    "Persistent broker stream receives a closed candle",
    "Candle is stored and published through Redis",
    "Strategy, safety and risk checks run",
    "Order is sent on the persistent broker session",
    "Broker ACK/fill and positions are synchronized",
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
        <div className="rounded-xl border border-white/10 bg-white/5 p-4"><span className="font-semibold text-white">LIVE mode</span> sends orders only after broker connection, readiness, and safety checks pass.</div>
      </div>
    </GlassCard>
  );
}

function LivePipelineCard({ latency, health, healthError }: { latency: LiveLatencyResponse | null; health: LivePipelineHealth | null; healthError?: string }) {
  const latest = latency?.latest;
  const timeline = latest?.timeline || {};
  const t0 = timeline.t0_expected_close_at ? new Date(timeline.t0_expected_close_at).getTime() : null;
  const offset = (field: string) => {
    const value = timeline[field];
    if (!value || t0 === null) return "Pending";
    return `+${Math.max(0, new Date(value).getTime() - t0).toLocaleString()} ms`;
  };
  const metric = (key: string, percentile: "p50" | "p95") => {
    const value = latency?.rollup?.[key]?.[percentile];
    return value === null || value === undefined ? "—" : `${Number(value).toFixed(1)} ms`;
  };
  const market = health?.workers?.live_market_worker;
  const strategy = health?.workers?.live_strategy_worker;
  const reconcile = health?.workers?.live_reconcile_worker;
  const connections = market?.connections || {};
  const connection = health?.connection || Object.values(connections)[0];
  const flagsEnabled = Boolean(
    health?.event_pipeline_enabled
      && health?.market_worker_enabled
      && health?.strategy_stream_enabled
      && health?.reconcile_worker_enabled
      && health?.persistent_ctrader_enabled
  );
  const marketStatus = !health ? "CHECKING" : !health.event_pipeline_enabled || !health.market_worker_enabled ? "DISABLED" : market?.status || "OFFLINE";
  const strategyStatus = !health ? "CHECKING" : !health.event_pipeline_enabled || !health.strategy_stream_enabled ? "DISABLED" : strategy?.status || "OFFLINE";
  const reconcileStatus = !health ? "CHECKING" : !health.event_pipeline_enabled || !health.reconcile_worker_enabled ? "DISABLED" : reconcile?.status || "OFFLINE";
  const connectionStatus = !health ? "CHECKING" : !health.event_pipeline_enabled || !health.persistent_ctrader_enabled ? "DISABLED" : connection?.state || "OFFLINE";
  const eventMode = Boolean(
    flagsEnabled
      && [marketStatus, strategyStatus, reconcileStatus].every((value) => value === "HEALTHY" || value === "DEGRADED")
      && connectionStatus === "CONNECTED"
  );
  const disabledFlags = health ? [
    !health.event_pipeline_enabled && "LIVE_EVENT_PIPELINE_ENABLED",
    !health.market_worker_enabled && "LIVE_MARKET_WORKER_ENABLED",
    !health.strategy_stream_enabled && "LIVE_STRATEGY_STREAM_ENABLED",
    !health.reconcile_worker_enabled && "LIVE_RECONCILE_WORKER_ENABLED",
    !health.persistent_ctrader_enabled && "CTRADER_PERSISTENT_CONNECTION_ENABLED",
  ].filter(Boolean) as string[] : [];
  const statusClass = (value?: string) => value === "HEALTHY" || value === "CONNECTED" ? "text-lime-200" : value === "DISABLED" ? "text-yellow-200" : value === "CHECKING" ? "text-purple-200" : value ? "text-amber-200" : "text-red-200";

  return (
    <GlassCard className="mb-6 p-6" hoverEffect={false}>
      <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-start">
        <div>
          <div className="flex items-center gap-2"><Activity className="h-5 w-5 text-cyan-300" /><h2 className="text-xl font-bold text-white">Connection & End-to-End Latency</h2></div>
          <p className="mt-1 text-sm text-purple-200">Observer-only diagnostics. The browser is not part of the candle → strategy → order path.</p>
        </div>
        <Badge className={eventMode ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : !health ? "border-purple-400/30 bg-purple-400/20 text-purple-100" : "border-yellow-400/30 bg-yellow-400/20 text-yellow-100"}>
          {eventMode ? "EVENT PIPELINE ACTIVE" : !health ? "HEALTH CHECK PENDING" : disabledFlags.length ? "EVENT PIPELINE DISABLED" : "EVENT PIPELINE STARTING / DEGRADED"}
        </Badge>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        <MetricCard label={`cTrader ${connection?.environment || health?.deployment_environment || ""}`.trim()} value={connectionStatus} />
        <MetricCard label="Market Worker" value={marketStatus} />
        <MetricCard label="Strategy Worker" value={strategyStatus} />
        <MetricCard label="Reconcile Worker" value={reconcileStatus} />
        <MetricCard label="Close → Send p50" value={metric("close_to_order_send_ms", "p50")} />
        <MetricCard label="Close → Send p95" value={metric("close_to_order_send_ms", "p95")} />
      </div>
      {healthError && (
        <div className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">
          Pipeline health API error: <span className="font-semibold">{healthError}</span>. The worker containers may still be running; check the API build/route and Redis heartbeat keys.
        </div>
      )}
      {disabledFlags.length > 0 && (
        <div className="mt-4 rounded-xl border border-yellow-400/30 bg-yellow-500/10 p-3 text-sm text-yellow-100">
          Docker containers may be running but these workers are intentionally idle because API environment flags are OFF: <span className="font-semibold">{disabledFlags.join(", ")}</span>. Set them to true in <code>.env.prod</code> and recreate API + live workers.
        </div>
      )}
      {health && disabledFlags.length === 0 && !eventMode && (
        <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-500/10 p-3 text-sm text-amber-100">
          Event flags are enabled, but the runtime is not fully healthy yet. Market feeds: <span className="font-semibold">{String(market?.feeds ?? 0)}</span>.
          {health.redis_error ? <span> Redis health read: <span className="font-semibold">{String(health.redis_error)}</span>.</span> : null}
          {market?.last_error ? <span> Market worker: <span className="font-semibold">{String(market.last_error)}</span>.</span> : null}
          {strategy?.last_error ? <span> Strategy worker: <span className="font-semibold">{String(strategy.last_error)}</span>.</span> : null}
          {reconcile?.last_error ? <span> Reconcile worker: <span className="font-semibold">{String(reconcile.last_error)}</span>.</span> : null}
        </div>
      )}
      <div className="mt-4 grid grid-cols-2 gap-2 text-sm md:grid-cols-4 xl:grid-cols-7">
        {[
          ["Broker event", "t1_broker_event_received_at"],
          ["DB stored", "t3_candle_db_commit_at"],
          ["Strategy start", "t6_strategy_started_at"],
          ["Signal ready", "t8_signal_persisted_at"],
          ["Order sent", "t12_order_request_sent_at"],
          ["Broker accepted", "t13_broker_order_accepted_at"],
          ["Filled", "t14_broker_fill_received_at"],
        ].map(([label, field]) => <div key={field} className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-xs text-purple-300">{label}</p><p className="mt-1 font-semibold text-white">{offset(field)}</p></div>)}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-purple-200">
        <span>Trace: <span className="text-white">{latest?.trace_id || "No completed candle trace yet"}</span></span>
        <span>Status: <span className={statusClass(latest?.status)}>{latest?.status || "WAITING"}</span></span>
        <span>Reconnects: <span className="text-white">{connection?.reconnect_count ?? 0}</span></span>
        <span>Close → fill p50/p95: <span className="text-white">{metric("close_to_fill_ms", "p50")} / {metric("close_to_fill_ms", "p95")}</span></span>
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
  const [latency, setLatency] = useState<LiveLatencyResponse | null>(null);
  const [pipelineHealth, setPipelineHealth] = useState<LivePipelineHealth | null>(null);
  const [pipelineHealthError, setPipelineHealthError] = useState("");
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
  // Runtime resources are polled independently. One slow endpoint (for example
  // latency/health during broker recovery) must never freeze candle/summary UI.
  // The generation changes after a mutation so older responses cannot overwrite
  // Start/Auto Runner/Auto Trade changes.
  const runtimeGeneration = useRef(0);
  const runtimeInFlight = useRef<Record<string, number>>({});

  const metrics = summary?.metrics;
  const broker = summary?.broker;
  const recentSignals = summary?.recent_signals || [];
  const recentOrders = summary?.recent_orders || [];
  const openPositions = summary?.open_positions || [];
  const recentLogs = summary?.recent_logs || [];
  const latestCandles = candleSnapshot?.candles?.slice(0, 5) || [];
  const marketWorkerHealth = pipelineHealth?.workers?.live_market_worker;
  const marketFeedCount = Number(marketWorkerHealth?.feeds ?? 0);
  const healthStoredCandleCount = Number(pipelineHealth?.market_data?.stored_count ?? 0);
  const marketSnapshotEmptyMessage = healthStoredCandleCount > 0
    ? `Database health reports ${healthStoredCandleCount} stored candle${healthStoredCandleCount === 1 ? "" : "s"}, but this snapshot has not refreshed yet. The independent candle poll will retry automatically; Refresh also forces an immediate read.`
    : pipelineHealth && marketFeedCount === 0
      ? "Market worker has no registered feed for this deployment yet. Keep the deployment RUNNING, Auto Runner ON, cTrader CONNECTED, and verify the market worker health/error above."
      : marketWorkerHealth?.last_error
        ? `Market worker has not stored a candle yet. Current worker error: ${String(marketWorkerHealth.last_error)}`
        : "No broker candles stored yet. The cTrader live feed stays subscribed even if historical bootstrap temporarily fails and will retry automatically. You can also use Refresh Candles for a manual bootstrap check.";
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

  const loadRuntime = async (silent = false) => {
    if (!deploymentId) return;
    const generation = runtimeGeneration.current;

    const runResource = async <T,>(
      key: string,
      request: () => Promise<T>,
      apply: (value: T) => void,
      errorLabel: string,
      onError?: (message: string) => void,
    ) => {
      // Do not overlap the same poll within one generation. A mutation creates a
      // new generation and is allowed to issue a fresh request immediately.
      if (runtimeInFlight.current[key] === generation) return;
      runtimeInFlight.current[key] = generation;
      try {
        const value = await request();
        if (generation === runtimeGeneration.current) apply(value);
      } catch (error: any) {
        const message = error?.message || errorLabel;
        if (generation === runtimeGeneration.current) onError?.(message);
        if (!silent && generation === runtimeGeneration.current) {
          showToast(message, "error");
        }
      } finally {
        if (runtimeInFlight.current[key] === generation) {
          delete runtimeInFlight.current[key];
        }
      }
    };

    // Apply each response as soon as it arrives. Previously Promise.all waited
    // for the slowest call, and the 5-second poll could repeatedly invalidate
    // the entire batch. That left Pipeline Health on CHECKING and the Market
    // Data Snapshot stuck at its old zero-candle value even while trades ran.
    await Promise.allSettled([
      runResource(
        "summary",
        () => liveTradingApi.getDeploymentSummary(deploymentId, { refreshBroker: false }),
        setSummary,
        "Failed to load deployment summary",
      ),
      runResource(
        "candles",
        () => liveTradingApi.getDeploymentCandles(deploymentId, 20),
        setCandleSnapshot,
        "Failed to load market candles",
      ),
      runResource(
        "latency",
        () => liveTradingApi.getDeploymentLatency(deploymentId, 50),
        setLatency,
        "Failed to load live latency",
      ),
      runResource(
        "pipelineHealth",
        getDeploymentPipelineHealthDirect.bind(null, deploymentId),
        (value) => { setPipelineHealth(value); setPipelineHealthError(""); },
        "Failed to load pipeline health",
        setPipelineHealthError,
      ),
    ]);
  };

  const loadSummary = async (silent = false) => {
    if (!deploymentId) return;
    try {
      if (!silent) setLoading(true);

      // A newly-created deployment can briefly race navigation/DB visibility.
      // Retry the primary deployment read instead of flashing a false "No record found".
      let d: StrategyDeployment | null = null;
      let lastError: any = null;
      const attempts = silent ? 1 : 6;
      for (let attempt = 0; attempt < attempts; attempt += 1) {
        try {
          d = await liveTradingApi.getDeployment(deploymentId);
          break;
        } catch (error: any) {
          lastError = error;
          if (attempt < attempts - 1) await new Promise((resolve) => setTimeout(resolve, 500 + attempt * 250));
        }
      }
      if (!d) throw lastError || new Error("Deployment is not available yet");

      setDeployment(d);

      // Optional/readiness calls must never make an existing deployment look missing.
      const [accountsResult, readyResult] = await Promise.allSettled([
        liveTradingApi.listBrokerAccounts(),
        liveTradingApi.getDeploymentReadiness(deploymentId),
      ]);
      if (accountsResult.status === "fulfilled") setBrokerAccounts(accountsResult.value);
      if (readyResult.status === "fulfilled") setReadiness(readyResult.value);

      await loadRuntime(true);
    } catch (error: any) {
      if (!silent) showToast(error.message || "Failed to load deployment summary", "error");
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
      const refreshedSummary = await liveTradingApi.getDeploymentSummary(deploymentId, { refreshBroker: true }).catch(() => null);
      if (refreshedSummary) setSummary(refreshedSummary);
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
      const refreshedSummary = await liveTradingApi.getDeploymentSummary(deploymentId, { refreshBroker: true }).catch(() => null);
      if (refreshedSummary) setSummary(refreshedSummary);
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
    const timer = setInterval(() => loadRuntime(true), 5000);
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
      let updated: StrategyDeployment;
      if (type === "start") updated = await liveTradingApi.startDeployment(deploymentId);
      else if (type === "pause") updated = await liveTradingApi.pauseDeployment(deploymentId);
      else updated = await liveTradingApi.stopDeployment(deploymentId);

      runtimeGeneration.current += 1;
      // Update the visible state immediately from the successful action response;
      // the background refresh then fills broker/runtime details without leaving DRAFT stale.
      setDeployment(updated);
      setSummary((previous) => previous ? { ...previous, deployment: { ...previous.deployment, ...updated } } : previous);
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
      runtimeGeneration.current += 1;
      const updated = await liveTradingApi.updateDeployment(deploymentId, { auto_trade_enabled: enabled });
      setDeployment(updated);
      setSummary((previous) => previous ? { ...previous, deployment: { ...previous.deployment, ...updated } } : previous);
      showToast(enabled ? "Auto Trade enabled" : "Auto Trade disabled", "success");
      await loadRuntime(true);
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
      runtimeGeneration.current += 1;
      if (action === "enable" || action === "disable") {
        const updated = action === "enable"
          ? await liveTradingApi.enableAutoRunner(deploymentId)
          : await liveTradingApi.disableAutoRunner(deploymentId);
        // Apply the mutation response immediately. This removes the visible
        // ON-toast/OFF-toggle race caused by an older 5-second poll finishing late.
        setDeployment(updated);
        setSummary((previous) => previous ? { ...previous, deployment: { ...previous.deployment, ...updated } } : previous);
      }
      if (action === "run-now") {
        const result = await liveTradingApi.runAutoRunnerNow(deploymentId);
        setRunnerResult(String(result.message || result.reason || "Auto runner checked"));
      }
      showToast(action === "enable" ? "Auto runner enabled" : action === "disable" ? "Auto runner disabled" : "Auto runner tick completed", "success");
      await loadRuntime(true);
    } catch (error: any) {
      showToast(error.message || "Auto runner action failed", "error");
    } finally {
      setRunnerBusy(false);
    }
  };



  const title = summary?.deployment?.name || deployment?.name || "Live Deployment";
  const subtitle = `${summary?.deployment?.strategy_name || deployment?.strategy_id || "Strategy"} • ${summary?.deployment?.instrument || deployment?.instrument || "—"} • ${summary?.deployment?.timeframe || deployment?.timeframe || "—"}`;

  if (loading) return <PageShell><GlassCard className="p-6 text-purple-100">Loading deployment...</GlassCard></PageShell>;
  if (!deployment) return <PageShell><NoRows label="Deployment not available. Refresh once if it was just created; otherwise it may have been deleted." /></PageShell>;
  if (!summary) return <PageShell><GlassCard className="p-6 text-purple-100">Deployment loaded. Waiting for live runtime status...</GlassCard></PageShell>;

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

      {summary.funded && (
        <GlassCard className="mb-6 p-6" hoverEffect={false}>
          <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-start">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-xl font-bold text-lime-300">Funded Account Guard</h2>
                <Badge className="border-lime-400/30 bg-lime-400/20 text-lime-100">FUNDED</Badge>
                <StatusBadge value={summary.funded.guard?.status || "NOT_INITIALIZED"} />
              </div>
              <p className="mt-1 text-sm text-purple-200">Server-side prop-account protection using fresh broker balance/equity. Standard strategy logic remains unchanged.</p>
              {summary.funded.guard?.reason && <p className="mt-2 rounded-xl border border-yellow-400/20 bg-yellow-500/10 p-3 text-xs text-yellow-100">{summary.funded.guard.reason}</p>}
            </div>
            <div className="text-right text-xs text-purple-200">
              <div>{summary.funded.profile?.provider_name || "Funded profile"} · {summary.funded.profile?.challenge_type || "—"}</div>
              <div>{summary.funded.phase_number ? `Phase ${summary.funded.phase_number}` : "Instant / payout stage"}</div>
            </div>
          </div>
          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <MetricCard label="Broker Balance" value={formatOptionalMoney(summary.funded.guard?.balance ?? summary.funded.broker?.balance, summary.funded.broker?.currency || summary.funded.profile?.account_currency)} />
            <MetricCard label="Broker Equity" value={formatOptionalMoney(summary.funded.guard?.equity ?? summary.funded.broker?.equity, summary.funded.broker?.currency || summary.funded.profile?.account_currency)} />
            <MetricCard label="Daily DD Remaining" value={formatOptionalMoney(summary.funded.guard?.remaining_daily_capacity, summary.funded.broker?.currency || summary.funded.profile?.account_currency)} />
            <MetricCard label="Max DD Remaining" value={formatOptionalMoney(summary.funded.guard?.remaining_max_capacity, summary.funded.broker?.currency || summary.funded.profile?.account_currency)} />
            <MetricCard label="Risk Tier" value={summary.funded.guard?.risk_tier || (summary.funded.risk_mode === "FIXED" ? "Fixed" : "—")} />
            <MetricCard label="Effective Risk" value={pct(summary.funded.guard?.effective_risk_pct)} />
            <MetricCard label="Requested Risk" value={pct(summary.funded.guard?.requested_risk_pct)} />
            <MetricCard label="Target Progress" value={pct(summary.funded.guard?.target_progress_pct)} />
            <MetricCard label="Trading Days" value={String(summary.funded.guard?.trading_days ?? 0)} />
            <MetricCard label="Qualifying Days" value={String(summary.funded.guard?.qualifying_days ?? 0)} />
            <MetricCard label="Daily Floor" value={formatOptionalMoney(summary.funded.guard?.daily_floor, summary.funded.broker?.currency || summary.funded.profile?.account_currency)} />
            <MetricCard label="Max DD Floor" value={formatOptionalMoney(summary.funded.guard?.max_floor, summary.funded.broker?.currency || summary.funded.profile?.account_currency)} />
          </div>
          {summary.funded.guard?.limiting_rule && <p className="mt-4 rounded-xl border border-cyan-400/20 bg-cyan-500/10 p-3 text-sm text-cyan-100">Risk reduced by funded guard: <span className="font-semibold">{summary.funded.guard.limiting_rule}</span>. Requested {pct(summary.funded.guard.requested_risk_pct)}, effective {pct(summary.funded.guard.effective_risk_pct)}.</p>}
        </GlassCard>
      )}

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div>
            <h2 className="text-xl font-bold text-lime-300">Strategy Runner</h2>
            <p className="mt-1 max-w-2xl text-sm text-purple-200">Runs the selected strategy on the latest closed broker candles. Auto Trade only places orders after the live engine status and risk checks pass.</p>
          </div>
          <div className="flex max-w-3xl flex-wrap justify-end gap-2 rounded-2xl border border-white/10 bg-slate-950/20 p-2">
            <ControlToggle label="Start" active={isRunning} disabled={busy || isPaperDeprecated} onClick={() => action("start")} tone="lime" />
            <ControlToggle label="Pause" active={(summary.deployment?.status || deployment.status) === "PAUSED"} disabled={busy} onClick={() => action("pause")} tone="yellow" />
            <ControlToggle label="Stop" active={(summary.deployment?.status || deployment.status) === "STOPPED"} disabled={busy} onClick={() => action("stop")} tone="red" />
            <ControlToggle label="Auto Trade" active={Boolean(summary.deployment?.auto_trade_enabled)} disabled={busy} onClick={() => toggleAutoTrade(!summary.deployment?.auto_trade_enabled)} tone="fuchsia" />
            <ControlToggle label="Auto Runner" active={Boolean(summary.deployment?.auto_runner_enabled)} disabled={runnerBusy || !isRunning || !summary.deployment?.auto_trade_enabled} onClick={() => autoRunnerAction(summary.deployment?.auto_runner_enabled ? "disable" : "enable")} tone="lime" />
            <button
              type="button"
              disabled={runnerBusy || !isRunning || !summary.deployment?.auto_trade_enabled}
              onClick={() => autoRunnerAction("run-now")}
              className="inline-flex h-9 items-center gap-2 rounded-full border border-cyan-400/40 bg-cyan-400/10 px-3 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <RefreshCw className="h-3.5 w-3.5" />Run Once
            </button>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
          <MetricCard label="Strategy" value={summary.deployment?.strategy_name || deployment.strategy_id || "—"} />
          <MetricCard label="Last Run" value={dateWithSeconds(summary.deployment?.last_runner_at || deployment.last_runner_at)} />
          <MetricCard label="Last Processed Candle" value={date(summary.deployment?.last_processed_candle_time || deployment.last_processed_candle_time)} />
          <MetricCard label="Next Scheduled Run" value={dateWithSeconds(summary.deployment?.next_run_at || deployment.next_run_at)} />
          <MetricCard label="Auto Runner" value={summary.deployment?.auto_runner_enabled ? "ON" : "OFF"} />
          <MetricCard label="Last Signal" value={recentSignals[0]?.signal_type || "—"} />
          <MetricCard label="Latest Order" value={recentOrders[0]?.status || "—"} />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <StatusBadge value={summary.deployment?.status || deployment.status} />
          <Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">{mode}</Badge>
          {summary.funded && <Badge className="border-lime-400/30 bg-lime-400/20 text-lime-100">FUNDED</Badge>}
          <Badge className={summary.deployment?.auto_runner_enabled ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : "border-yellow-400/30 bg-yellow-400/20 text-yellow-100"}>Auto Runner {summary.deployment?.auto_runner_enabled ? "ON" : "OFF"}</Badge>
          <span className="text-sm text-purple-200">Last signal: {date(summary.deployment?.last_signal_at || deployment.last_signal_at)}</span>
        </div>
        <p className="mt-3 rounded-xl border border-cyan-400/20 bg-cyan-500/10 p-3 text-xs text-cyan-100">In event mode, the persistent cTrader stream publishes each closed candle immediately; +3s/+8s historical requests are recovery only. The legacy scheduler remains available behind rollout flags.</p>
        {runnerResult && <p className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-purple-100">Latest runner log: {runnerResult}</p>}
      </GlassCard>

      <LivePipelineCard latency={latency} health={pipelineHealth} healthError={pipelineHealthError} />

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
          <div><h2 className="text-xl font-bold text-lime-300">Broker Summary</h2><p className="mt-1 text-sm text-purple-200">DEMO and approved LIVE deployments use a connected broker account. Broker Sync reads positions/orders; it does not place new orders.</p><p className="mt-1 text-xs text-lime-200">Broker Auto-Sync: {(summary?.deployment?.live_sync_enabled || summary?.deployment?.auto_runner_enabled) ? "ON" : "OFF"} · every {summary?.deployment?.live_sync_interval_seconds ?? 10}s · last sync {date(summary?.deployment?.last_broker_sync_at)}</p><p className="mt-1 text-xs text-purple-300">{pnlSourceLabel}</p></div>
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
          <>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
              <MetricCard label="Account" value={broker.account_label || "Demo Broker"} />
              <MetricCard label="Status" value={broker.status || "—"} />
              <MetricCard label="Login" value={broker.login_id || "—"} />
              <MetricCard label="Server" value={broker.server_name || "—"} />
              <MetricCard label="Balance" value={formatOptionalMoney(broker.balance, broker.currency)} />
              <MetricCard label="Equity" value={formatOptionalMoney(broker.equity, broker.currency)} />
              <MetricCard label="Currency" value={broker.currency || (isUpstoxBroker ? "INR" : "—")} />
              <MetricCard label="Last Connected" value={date(broker.last_connected_at)} />
            </div>
            {isUpstoxBroker && (broker.balance === null || broker.balance === undefined || broker.equity === null || broker.equity === undefined || metrics?.broker_sync_warning) && (
              <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-500/10 p-3 text-sm text-amber-100">
                {metrics?.broker_sync_warning || "Funds/margin unavailable from Upstox. Broker is connected, but balance could not be parsed."}
              </div>
            )}
          </>
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
            <div className="flex min-w-0 flex-col justify-between gap-3 lg:flex-row lg:items-center">
              <div className="min-w-0">
                <h2 className="text-xl font-bold text-lime-300">Market Data Snapshot</h2>
                <p className="mt-1 text-sm text-purple-200">Latest closed candles stored from the connected broker for the live strategy runner. No chart and no fake data.</p>
              </div>
              <Button disabled={candleBusy || !["DEMO", "LIVE"].includes(mode) || !broker || broker.status !== "CONNECTED"} onClick={refreshCandles} className="gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-400"><RefreshCw className="h-4 w-4" /> Refresh Candles</Button>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-8">
              <MetricCard label="Data Source" value={candleSource} />
              <MetricCard label="Deployment Symbol" value={candleSnapshot?.symbol || summary.deployment?.instrument || deployment.instrument} />
              <MetricCard label={isUpstoxBroker ? "Instrument Key" : "Broker Symbol"} value={candleSnapshot?.instrument_key || candleSnapshot?.resolved_symbol || deployment.instrument_key || deployment.broker_symbol || candleSnapshot?.symbol || summary.deployment?.instrument || deployment.instrument} />
              <MetricCard label="Timeframe" value={candleSnapshot?.timeframe || summary.deployment?.timeframe || deployment.timeframe} />
              <MetricCard label="Candles Stored" value={String(candleSnapshot?.stored_count ?? 0)} />
              <MetricCard label="Latest Close" value={num(candleSnapshot?.latest_close)} />
              <MetricCard label="Closed At" value={date(candleSnapshot?.latest_candle_close_time)} />
              <MetricCard label="Ingest Latency" value={candleSnapshot?.ingestion_latency_seconds == null ? "-" : `${Number(candleSnapshot.ingestion_latency_seconds).toFixed(1)}s`} />
            </div>
            <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">
              Candle OPEN time: <span className="font-semibold text-white">{date(candleSnapshot?.latest_candle_time)}</span>
              <span className="mx-2 text-purple-400">•</span>
              Closed at: <span className="font-semibold text-white">{date(candleSnapshot?.latest_candle_close_time)}</span>
              <span className="mx-2 text-purple-400">•</span>
              Next close expected: <span className="font-semibold text-white">{date(candleSnapshot?.next_closed_candle_expected_at)}</span>
            </div>
            {latestCandles.length === 0 ? <div className="mt-4"><NoRows label={marketSnapshotEmptyMessage} /></div> : (
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
