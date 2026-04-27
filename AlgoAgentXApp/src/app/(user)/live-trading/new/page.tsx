"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Info, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, StrategyCatalogItem } from "@/types/live-trading";

const defaults = {
  name: "",
  strategy_id: "",
  instrument: "XAUUSD",
  timeframe: "M15",
  mode: "PAPER" as "PAPER" | "DEMO",
  broker_account_id: "",
  capital: 100000,
  risk_per_trade: 0.01,
  rr_ratio: 2,
  price_risk_pct: 0.002,
  max_daily_loss: 5000,
  max_trades_per_day: 10,
  max_open_positions: 1,
  allow_short: true,
  auto_trade_enabled: false,
};

const isPaperReady = (s: StrategyCatalogItem) => Boolean(s.isDeployablePaper ?? s.is_deployable_paper);
const isDemoReady = (s: StrategyCatalogItem) => Boolean(s.isDeployableDemo ?? s.is_deployable_demo);

export default function NewLiveDeploymentPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [strategies, setStrategies] = useState<StrategyCatalogItem[]>([]);
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(defaults);

  const connectedDemoBrokers = useMemo(() => brokers.filter((b) => b.mode === "DEMO" && b.status === "CONNECTED"), [brokers]);
  const deployableStrategies = useMemo(
    () => strategies.filter((strategy) => (form.mode === "DEMO" ? isDemoReady(strategy) : isPaperReady(strategy))),
    [strategies, form.mode],
  );

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [strategyRows, brokerRows] = await Promise.all([liveTradingApi.listStrategies(), liveTradingApi.listBrokerAccounts()]);
        setStrategies(strategyRows);
        setBrokers(brokerRows);
      } catch (error: any) {
        showToast(error.message || "Failed to load form data", "error");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    const first = deployableStrategies[0];
    if (!deployableStrategies.some((strategy) => strategy.id === form.strategy_id)) {
      setForm((prev) => ({
        ...prev,
        strategy_id: first?.id || "",
        name: first ? `${first.name} Live Deployment` : prev.name,
      }));
    }
  }, [deployableStrategies, form.strategy_id]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.strategy_id) {
      showToast("No deployable strategy found for selected mode", "error");
      return;
    }
    if (form.mode === "DEMO" && !form.broker_account_id) {
      showToast("Broker account is required for DEMO mode", "error");
      return;
    }
    try {
      setSaving(true);
      const created = await liveTradingApi.createDeployment({
        ...form,
        broker_account_id: form.mode === "DEMO" ? form.broker_account_id : form.broker_account_id || null,
      });
      showToast("Deployment created", "success");
      router.push(`/live-trading/${created.id}`);
    } catch (error: any) {
      showToast(error.message || "Failed to create deployment", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageShell>
      <PageHeader
        title="Create Live Deployment"
        subtitle="Only admin-approved strategies can be deployed to PAPER or MT5 DEMO. LIVE mode remains locked."
        actions={<Link href="/live-trading"><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link>}
      />

      <GlassCard className="p-6" hoverEffect={false}>
        {loading ? (
          <p className="text-purple-100">Loading deployable strategies and broker accounts...</p>
        ) : (
          <form onSubmit={submit} className="space-y-6">
            <div className="rounded-xl border border-lime-400/20 bg-lime-400/10 p-4 text-sm text-lime-100">
              <div className="flex gap-2"><ShieldCheck className="mt-0.5 h-4 w-4" /><span>PAPER mode shows only Paper Ready strategies. DEMO mode shows only Demo Ready strategies.</span></div>
            </div>

            {!deployableStrategies.length && (
              <div className="rounded-xl border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100">
                No deployable strategy found. Run verification/sandbox and ask admin to enable deployment.
              </div>
            )}

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
              <label className="space-y-2 text-sm text-purple-100">Deployment name<input required className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Deployable strategy<select required className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-white outline-none" value={form.strategy_id} onChange={(e) => setForm({ ...form, strategy_id: e.target.value })}>{deployableStrategies.length === 0 && <option value="">No deployable strategy found</option>}{deployableStrategies.map((strategy) => <option key={strategy.id} value={strategy.id}>{strategy.name} • {form.mode === "DEMO" ? "Demo Ready" : "Paper Ready"}</option>)}</select></label>
              <label className="space-y-2 text-sm text-purple-100">Instrument<input required className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.instrument} onChange={(e) => setForm({ ...form, instrument: e.target.value.toUpperCase() })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Timeframe<select className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-white outline-none" value={form.timeframe} onChange={(e) => setForm({ ...form, timeframe: e.target.value })}>{["M5", "M15", "M30", "H1", "H4", "D1"].map((tf) => <option key={tf} value={tf}>{tf}</option>)}</select></label>
              <label className="space-y-2 text-sm text-purple-100">Mode<select className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-white outline-none" value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value as "PAPER" | "DEMO", broker_account_id: e.target.value === "PAPER" ? "" : form.broker_account_id })}><option value="PAPER">PAPER</option><option value="DEMO">DEMO / MT5</option><option value="LIVE" disabled>LIVE - disabled until final production review</option></select></label>
              <label className="space-y-2 text-sm text-purple-100">Broker account {form.mode === "DEMO" && <span className="text-lime-300">*</span>}<select disabled={form.mode !== "DEMO"} className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-white outline-none disabled:opacity-50" value={form.broker_account_id} onChange={(e) => setForm({ ...form, broker_account_id: e.target.value })}><option value="">{form.mode === "DEMO" ? "Select connected MT5 demo broker" : "Optional"}</option>{connectedDemoBrokers.map((broker) => <option key={broker.id} value={broker.id}>{broker.account_label} • {broker.login_id} • {broker.server_name}</option>)}</select></label>
              <label className="space-y-2 text-sm text-purple-100">Capital<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.capital} onChange={(e) => setForm({ ...form, capital: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Risk per trade<input type="number" step="0.001" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.risk_per_trade} onChange={(e) => setForm({ ...form, risk_per_trade: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">RR ratio<input type="number" step="0.1" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.rr_ratio} onChange={(e) => setForm({ ...form, rr_ratio: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Price risk %<input type="number" step="0.0001" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.price_risk_pct} onChange={(e) => setForm({ ...form, price_risk_pct: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max daily loss<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_daily_loss} onChange={(e) => setForm({ ...form, max_daily_loss: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max trades per day<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_trades_per_day} onChange={(e) => setForm({ ...form, max_trades_per_day: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max open positions<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_open_positions} onChange={(e) => setForm({ ...form, max_open_positions: Number(e.target.value) })} /></label>
            </div>

            <div className="flex flex-wrap gap-4 rounded-xl border border-white/10 bg-white/5 p-4">
              <label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.allow_short} onChange={(e) => setForm({ ...form, allow_short: e.target.checked })} />Allow short</label>
              <label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.auto_trade_enabled} onChange={(e) => setForm({ ...form, auto_trade_enabled: e.target.checked })} />Auto trade enabled</label>
            </div>

            <Button disabled={saving || !form.strategy_id} className="border-0 bg-gradient-to-r from-lime-400 to-emerald-500 text-slate-950 hover:from-lime-300 hover:to-emerald-400">{saving ? "Creating..." : "Create Deployment"}</Button>
          </form>
        )}
      </GlassCard>
    </PageShell>
  );
}
