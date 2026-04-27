"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { ArrowLeft, Pause, Play, Power, RefreshCw, ShieldAlert, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { AdminLiveDeploymentDetail, AdminLiveControlAction } from "@/types/live-trading";

const date = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");
const num = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 4 });
const money = (value: unknown, currency?: string | null) => {
  const amount = Number(value || 0);
  const code = currency?.toUpperCase();
  if (code === "USD" || code === "INR" || code === "EUR" || code === "GBP") {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: code, maximumFractionDigits: 2 }).format(amount);
  }
  return code ? `${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${code}` : amount.toLocaleString(undefined, { maximumFractionDigits: 2 });
};

function Empty({ text }: { text: string }) {
  return <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-200">{text}</div>;
}

function StatusBadge({ value }: { value?: string }) {
  const color = value === "RUNNING" ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : value === "PAUSED" ? "border-yellow-400/30 bg-yellow-400/20 text-yellow-100" : value === "ERROR" ? "border-red-400/30 bg-red-400/20 text-red-100" : "border-purple-300/30 bg-purple-400/20 text-purple-100";
  return <Badge className={color}>{value || "—"}</Badge>;
}

function InfoCard({ title, rows }: { title: string; rows: { label: string; value: ReactNode }[] }) {
  return (
    <GlassCard className="p-6" hoverEffect={false}>
      <h2 className="mb-4 text-xl font-bold text-lime-300">{title}</h2>
      <div className="space-y-2 text-sm text-purple-100">
        {rows.map((row) => <div key={row.label} className="flex justify-between gap-4 border-b border-white/5 pb-2"><span className="text-purple-300">{row.label}</span><span className="text-right font-medium text-white">{row.value || "—"}</span></div>)}
      </div>
    </GlassCard>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-xs text-purple-300">{label}</p><p className="mt-2 text-2xl font-bold text-white">{value}</p></div>;
}

export default function AdminLiveTradingDetailPage() {
  const { deploymentId } = useParams<{ deploymentId: string }>();
  const { showToast } = useToast();
  const [data, setData] = useState<AdminLiveDeploymentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [runnerBusy, setRunnerBusy] = useState(false);
  const [runnerResult, setRunnerResult] = useState("");
  const [reason, setReason] = useState("Admin live control center action");

  const load = async () => {
    try {
      setLoading(true);
      setData(await liveTradingApi.adminGetLiveDeployment(deploymentId));
    } catch (error: any) {
      showToast(error.message || "Failed to load admin deployment detail", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (deploymentId) load(); }, [deploymentId]);

  const runAction = async (action: AdminLiveControlAction) => {
    try {
      setBusy(true);
      const updated = await liveTradingApi.adminControlDeployment(deploymentId, action, reason || "Admin live control center action");
      setData(updated);
      showToast("Admin action completed", "success");
    } catch (error: any) {
      showToast(error.message || "Admin action failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const runStrategy = async (execute: boolean) => {
    try {
      setRunnerBusy(true);
      const result = await liveTradingApi.adminRunStrategyOnce(deploymentId, execute);
      setData(result.detail);
      const msg = result.runner?.message || (execute ? "Strategy run completed" : "Dry run completed");
      setRunnerResult(`${result.runner?.signal || "HOLD"} • ${msg}`);
      showToast(msg, "success");
    } catch (error: any) {
      showToast(error.message || "Admin strategy runner failed", "error");
    } finally {
      setRunnerBusy(false);
    }
  };

  if (loading) return <PageShell><GlassCard className="p-6 text-purple-100">Loading admin detail...</GlassCard></PageShell>;
  if (!data?.deployment) return <PageShell><Empty text="No record found" /></PageShell>;

  const d = data.deployment;
  const m = data.metrics || {};
  const b = data.broker;
  const currency = b?.currency || m.currency || null;

  return (
    <PageShell>
      <PageHeader
        title={`Admin: ${d.name}`}
        subtitle="Deployment, user, strategy, broker status, risk settings, execution metrics and audit trail."
        actions={<><Link href="/admin/live-trading"><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link><Button onClick={load} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="h-4 w-4" />Refresh</Button></>}
      />

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-3"><StatusBadge value={d.status} /><Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">{d.mode}</Badge><span className="text-sm text-purple-200">Auto Trade: {d.auto_trade_enabled ? "ON" : "OFF"}</span></div>
            <p className="text-sm text-purple-200">Last signal: {date(d.last_signal_at)} • Last heartbeat: {date(d.last_heartbeat_at)}</p>
          </div>
          <div className="grid min-w-[320px] grid-cols-1 gap-2 md:grid-cols-2">
            <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Admin action reason" className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white placeholder:text-purple-300 outline-none focus:border-lime-300 md:col-span-2" />
            <Button disabled={busy} onClick={() => runAction("force-pause")} className="gap-2 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-4 w-4" />Force Pause</Button>
            <Button disabled={busy} onClick={() => runAction("force-stop")} variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-4 w-4" />Force Stop</Button>
            <Button disabled={busy} onClick={() => runAction("enable-auto-trade")} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Power className="h-4 w-4" />Enable Auto</Button>
            <Button disabled={busy} onClick={() => runAction("disable-auto-trade")} variant="outline" className="gap-2 border-orange-400/30 bg-orange-500/10 text-orange-100 hover:bg-orange-500/20"><ShieldAlert className="h-4 w-4" />Disable Auto</Button>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div>
            <h2 className="text-xl font-bold text-lime-300">Admin Strategy Runner</h2>
            <p className="mt-1 text-sm text-purple-200">Run the deployment strategy once on latest closed live_market_candles. No tick execution and no live mode.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={runnerBusy || d.status !== "RUNNING"} onClick={() => runStrategy(true)} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Play className="h-4 w-4" />Run Strategy Once</Button>
            <Button disabled={runnerBusy || d.status !== "RUNNING"} onClick={() => runStrategy(false)} variant="outline" className="gap-2 border-cyan-400/30 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20"><RefreshCw className="h-4 w-4" />Dry Run Strategy</Button>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
          <Metric label="Strategy" value={data.strategy?.name || d.strategy_id} />
          <Metric label="Last Signal" value={(data.recent_signals || []).find((s) => s.source === "ENGINE")?.signal_type || "—"} />
          <Metric label="Last Runner Log" value={(data.recent_logs || []).find((l) => l.event_type?.startsWith("RUNNER_"))?.level || "—"} />
          <Metric label="Auto Trade" value={d.auto_trade_enabled ? "ON" : "OFF"} />
        </div>
        <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">Latest runner result: <span className="font-semibold text-white">{runnerResult || (data.recent_logs || []).find((l) => l.event_type?.startsWith("RUNNER_"))?.message || "—"}</span></div>
      </GlassCard>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4 xl:grid-cols-7">
        <Metric label="Equity" value={money(m.equity, currency)} />
        <Metric label="Realized PnL" value={money(m.realized_pnl, currency)} />
        <Metric label="Unrealized PnL" value={money(m.unrealized_pnl, currency)} />
        <Metric label="Today PnL" value={money(m.today_pnl, currency)} />
        <Metric label="Open Positions" value={m.open_positions_count ?? 0} />
        <Metric label="Signals Today" value={m.signals_today ?? 0} />
        <Metric label="Orders Today" value={m.orders_today ?? 0} />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <InfoCard title="Deployment" rows={[{ label: "Instrument", value: d.instrument }, { label: "Timeframe", value: d.timeframe }, { label: "Capital", value: money(d.capital, currency) }, { label: "Created", value: date(d.created_at) }]} />
        <InfoCard title="User" rows={[{ label: "Name", value: data.user?.fullname || "—" }, { label: "Email", value: data.user?.email || "—" }, { label: "Role", value: data.user?.role || "—" }, { label: "User ID", value: data.user?.id || d.user_id }]} />
        <InfoCard title="Strategy" rows={[{ label: "Name", value: data.strategy?.name || d.strategy_id }, { label: "Visibility", value: data.strategy?.visibility || "—" }, { label: "Strategy ID", value: d.strategy_id }, { label: "Updated", value: date(data.strategy?.updated_at) }]} />
        <InfoCard title="Broker Safe Status" rows={[{ label: "Account", value: b?.account_label || "No broker" }, { label: "Status", value: b?.status || "—" }, { label: "Login", value: b?.login_id || "—" }, { label: "Server", value: b?.server_name || "—" }, { label: "Balance", value: money(b?.balance, b?.currency) }, { label: "Equity", value: money(b?.equity, b?.currency) }, { label: "Currency", value: b?.currency || "—" }]} />
        <InfoCard title="Risk Settings" rows={[{ label: "Risk / Trade", value: num(d.risk_per_trade) }, { label: "RR Ratio", value: num(d.rr_ratio) }, { label: "Price Risk %", value: num(d.price_risk_pct) }, { label: "Max Daily Loss", value: money(d.max_daily_loss, currency) }, { label: "Max Trades / Day", value: d.max_trades_per_day }, { label: "Max Open Positions", value: d.max_open_positions }, { label: "Allow Short", value: d.allow_short ? "YES" : "NO" }]} />
        <InfoCard title="Execution Metrics" rows={[{ label: "Total Orders", value: m.total_orders ?? 0 }, { label: "Total Signals", value: m.total_signals ?? 0 }, { label: "Orders Today", value: m.orders_today ?? 0 }, { label: "Signals Today", value: m.signals_today ?? 0 }, { label: "Open Positions", value: m.open_positions_count ?? 0 }]} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-4 text-xl font-bold text-white">Open Positions</h2>{(data.open_positions || []).length === 0 ? <Empty text="No open positions" /> : <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="text-purple-200"><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Avg Entry</th><th>Current</th><th>SL</th><th>Target</th><th>Unrealized PnL</th><th>Status</th><th>Opened At</th></tr></thead><tbody className="divide-y divide-white/10">{data.open_positions?.map((p) => <tr key={p.id} className="text-purple-50"><td className="py-3">{p.symbol}</td><td>{p.side}</td><td>{num(p.qty)}</td><td>{num(p.avg_entry_price)}</td><td>{num(p.current_price)}</td><td>{num(p.stop_loss)}</td><td>{num(p.target)}</td><td>{money(p.unrealized_pnl, currency)}</td><td>{p.status}</td><td>{date(p.opened_at)}</td></tr>)}</tbody></table></div>}</GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-4 text-xl font-bold text-white">Recent Signals</h2>{(data.recent_signals || []).length === 0 ? <Empty text="No signals yet" /> : <div className="overflow-x-auto"><table className="w-full min-w-[820px] text-left text-sm"><thead className="text-purple-200"><tr><th>Time</th><th>Source</th><th>Signal</th><th>Symbol</th><th>Price</th><th>Status</th><th>Reason</th></tr></thead><tbody className="divide-y divide-white/10">{data.recent_signals?.map((s) => <tr key={s.id} className="text-purple-50"><td className="py-3">{date(s.created_at)}</td><td>{s.source}</td><td>{s.signal_type}</td><td>{s.symbol}</td><td>{num(s.price)}</td><td>{s.status}</td><td>{s.rejection_reason || s.reason || "—"}</td></tr>)}</tbody></table></div>}</GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-4 text-xl font-bold text-white">Recent Orders</h2>{(data.recent_orders || []).length === 0 ? <Empty text="No orders yet" /> : <div className="overflow-x-auto"><table className="w-full min-w-[1000px] text-left text-sm"><thead className="text-purple-200"><tr><th>Time</th><th>Side</th><th>Symbol</th><th>Qty</th><th>Entry</th><th>Executed</th><th>SL</th><th>Target</th><th>Status</th><th>Broker Order ID</th><th>Error</th></tr></thead><tbody className="divide-y divide-white/10">{data.recent_orders?.map((o) => <tr key={o.id} className="text-purple-50"><td className="py-3">{date(o.created_at)}</td><td>{o.side}</td><td>{o.symbol}</td><td>{num(o.qty)}</td><td>{num(o.entry_price)}</td><td>{num(o.executed_price)}</td><td>{num(o.stop_loss)}</td><td>{num(o.target)}</td><td>{o.status}</td><td>{o.broker_order_id || "—"}</td><td>{o.error_message || "—"}</td></tr>)}</tbody></table></div>}</GlassCard>
        <GlassCard className="p-6" hoverEffect={false}><h2 className="mb-4 text-xl font-bold text-white">Execution Logs</h2>{(data.recent_logs || []).length === 0 ? <Empty text="No logs yet" /> : <div className="max-h-[520px] overflow-x-auto overflow-y-auto"><table className="w-full min-w-[820px] text-left text-sm"><thead className="text-purple-200"><tr><th>Time</th><th>Level</th><th>Event Type</th><th>Message</th></tr></thead><tbody className="divide-y divide-white/10">{data.recent_logs?.map((l) => <tr key={l.id} className="text-purple-50"><td className="py-3">{date(l.created_at)}</td><td>{l.level}</td><td>{l.event_type}</td><td>{l.message}</td></tr>)}</tbody></table></div>}</GlassCard>
        <GlassCard className="p-6 xl:col-span-2" hoverEffect={false}><h2 className="mb-4 text-xl font-bold text-white">Admin Audit Actions</h2>{(data.admin_audit_actions || []).length === 0 ? <Empty text="No admin audit actions yet" /> : <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="text-purple-200"><tr><th>Time</th><th>Admin</th><th>Action</th><th>Reason</th></tr></thead><tbody className="divide-y divide-white/10">{data.admin_audit_actions?.map((a) => <tr key={a.id} className="text-purple-50"><td className="py-3">{date(a.created_at)}</td><td>{a.admin_user_id}</td><td>{a.action}</td><td>{a.reason || "—"}</td></tr>)}</tbody></table></div>}</GlassCard>
      </div>
    </PageShell>
  );
}
