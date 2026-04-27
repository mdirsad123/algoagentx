"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount } from "@/types/live-trading";

export default function LiveDeploymentSettingsPage() {
  const { deploymentId } = useParams<{ deploymentId: string }>();
  const router = useRouter();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [form, setForm] = useState({
    name: "",
    instrument: "",
    timeframe: "",
    mode: "PAPER" as "PAPER" | "DEMO",
    broker_account_id: "" as string,
    capital: 100000,
    risk_per_trade: 0.01,
    rr_ratio: 2,
    price_risk_pct: 0.002,
    max_daily_loss: 5000,
    max_trades_per_day: 10,
    max_open_positions: 1,
    allow_short: true,
    auto_trade_enabled: false,
  });

  const connectedDemoBrokers = useMemo(() => brokers.filter((broker) => broker.mode === "DEMO" && broker.status === "CONNECTED"), [brokers]);

  useEffect(() => {
    const load = async () => {
      try {
        const [row, brokerRows] = await Promise.all([
          liveTradingApi.getDeployment(deploymentId),
          liveTradingApi.listBrokerAccounts(),
        ]);
        setBrokers(brokerRows);
        setForm({
          name: row.name,
          instrument: row.instrument,
          timeframe: row.timeframe,
          mode: (row.mode === "DEMO" ? "DEMO" : "PAPER") as "PAPER" | "DEMO",
          broker_account_id: row.broker_account_id || "",
          capital: Number(row.capital),
          risk_per_trade: Number(row.risk_per_trade),
          rr_ratio: Number(row.rr_ratio),
          price_risk_pct: Number(row.price_risk_pct),
          max_daily_loss: Number(row.max_daily_loss),
          max_trades_per_day: Number(row.max_trades_per_day),
          max_open_positions: Number(row.max_open_positions),
          allow_short: Boolean(row.allow_short),
          auto_trade_enabled: Boolean(row.auto_trade_enabled),
        });
      } catch (error: any) { showToast(error.message || "Failed to load settings", "error"); }
      finally { setLoading(false); }
    };
    if (deploymentId) load();
  }, [deploymentId]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (form.mode === "DEMO" && !form.broker_account_id) {
      showToast("DEMO mode requires a connected MT5 demo broker", "error");
      return;
    }
    try {
      setSaving(true);
      await liveTradingApi.updateDeployment(deploymentId, { ...form, broker_account_id: form.broker_account_id || null });
      showToast("Deployment settings updated", "success");
      router.push(`/live-trading/${deploymentId}`);
    } catch (error: any) { showToast(error.message || "Failed to update settings", "error"); }
    finally { setSaving(false); }
  };

  return (
    <PageShell>
      <PageHeader title="Deployment Settings" subtitle="Edit broker, mode, risk, and deployment configuration." actions={<Link href={`/live-trading/${deploymentId}`}><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link>} />
      <GlassCard className="p-6" hoverEffect={false}>
        {loading ? <p className="text-purple-100">Loading settings...</p> : (
          <form onSubmit={submit} className="space-y-6">
            <div className="rounded-xl border border-lime-300/20 bg-lime-300/10 p-4 text-sm text-lime-100">
              PAPER can run without broker. DEMO requires your connected MT5 demo account.
            </div>
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
              <label className="space-y-2 text-sm text-purple-100">Name<input className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Mode<select className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-white outline-none" value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value as "PAPER" | "DEMO", broker_account_id: e.target.value === "PAPER" ? "" : form.broker_account_id })}><option value="PAPER">PAPER</option><option value="DEMO">DEMO / MT5</option></select></label>
              <label className="space-y-2 text-sm text-purple-100">MT5 Demo Broker<select disabled={form.mode !== "DEMO"} className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-white outline-none disabled:opacity-50" value={form.broker_account_id} onChange={(e) => setForm({ ...form, broker_account_id: e.target.value })}><option value="">Select connected broker</option>{connectedDemoBrokers.map((broker) => <option key={broker.id} value={broker.id}>{broker.account_label} • {broker.login_id} • {broker.server_name}</option>)}</select></label>
              <label className="space-y-2 text-sm text-purple-100">Instrument<input className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.instrument} onChange={(e) => setForm({ ...form, instrument: e.target.value.toUpperCase() })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Timeframe<input className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.timeframe} onChange={(e) => setForm({ ...form, timeframe: e.target.value.toUpperCase() })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Capital<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.capital} onChange={(e) => setForm({ ...form, capital: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Risk per trade<input type="number" step="0.001" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.risk_per_trade} onChange={(e) => setForm({ ...form, risk_per_trade: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">RR ratio<input type="number" step="0.1" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.rr_ratio} onChange={(e) => setForm({ ...form, rr_ratio: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Price risk %<input type="number" step="0.0001" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.price_risk_pct} onChange={(e) => setForm({ ...form, price_risk_pct: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max daily loss<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_daily_loss} onChange={(e) => setForm({ ...form, max_daily_loss: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max trades per day<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_trades_per_day} onChange={(e) => setForm({ ...form, max_trades_per_day: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max open positions<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_open_positions} onChange={(e) => setForm({ ...form, max_open_positions: Number(e.target.value) })} /></label>
            </div>
            <div className="flex flex-wrap gap-4 rounded-xl border border-white/10 bg-white/5 p-4"><label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.allow_short} onChange={(e) => setForm({ ...form, allow_short: e.target.checked })} />Allow short</label><label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.auto_trade_enabled} onChange={(e) => setForm({ ...form, auto_trade_enabled: e.target.checked })} />Auto trade enabled</label></div>
            <Button disabled={saving} className="border-0 bg-gradient-to-r from-lime-400 to-emerald-500 text-slate-950 hover:from-lime-300 hover:to-emerald-400">{saving ? "Saving..." : "Save Settings"}</Button>
          </form>
        )}
      </GlassCard>
    </PageShell>
  );
}
