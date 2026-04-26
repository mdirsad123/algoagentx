"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Info } from "lucide-react";
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

export default function NewLiveDeploymentPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [strategies, setStrategies] = useState<StrategyCatalogItem[]>([]);
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(defaults);

  const demoBrokers = useMemo(() => brokers.filter((b) => b.mode === "DEMO" || b.mode === "PAPER"), [brokers]);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [strategyRows, brokerRows] = await Promise.all([liveTradingApi.listStrategies(), liveTradingApi.listBrokerAccounts()]);
        setStrategies(strategyRows);
        setBrokers(brokerRows);
        if (strategyRows[0]) setForm((prev) => ({ ...prev, strategy_id: strategyRows[0].id, name: `${strategyRows[0].name} Live Deployment` }));
      } catch (error: any) {
        showToast(error.message || "Failed to load form data", "error");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
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
        subtitle="Deploy a published strategy in PAPER or DEMO mode. LIVE mode stays blocked until demo validation."
        actions={<Link href="/live-trading"><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link>}
      />

      <GlassCard className="p-6" hoverEffect={false}>
        {loading ? (
          <p className="text-purple-100">Loading strategies and broker accounts...</p>
        ) : (
          <form onSubmit={submit} className="space-y-6">
            <div className="rounded-xl border border-lime-400/20 bg-lime-400/10 p-4 text-sm text-lime-100">
              <div className="flex gap-2"><Info className="mt-0.5 h-4 w-4" /><span>Only published strategies are shown. Live mode will be enabled after demo validation.</span></div>
            </div>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
              <label className="space-y-2 text-sm text-purple-100">Deployment name<input required className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Published strategy<select required className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-white outline-none" value={form.strategy_id} onChange={(e) => setForm({ ...form, strategy_id: e.target.value })}>{strategies.length === 0 && <option value="">No published strategies found</option>}{strategies.map((strategy) => <option key={strategy.id} value={strategy.id}>{strategy.name}</option>)}</select></label>
              <label className="space-y-2 text-sm text-purple-100">Instrument<input required className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.instrument} onChange={(e) => setForm({ ...form, instrument: e.target.value.toUpperCase() })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Timeframe<select className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-white outline-none" value={form.timeframe} onChange={(e) => setForm({ ...form, timeframe: e.target.value })}>{["M5", "M15", "M30", "H1", "H4", "D1"].map((tf) => <option key={tf} value={tf}>{tf}</option>)}</select></label>
              <label className="space-y-2 text-sm text-purple-100">Mode<select className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-white outline-none" value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value as "PAPER" | "DEMO" })}><option value="PAPER">PAPER</option><option value="DEMO">DEMO</option><option value="LIVE" disabled>LIVE - Live mode will be enabled after demo validation.</option></select></label>
              <label className="space-y-2 text-sm text-purple-100">Broker account {form.mode === "DEMO" && <span className="text-lime-300">*</span>}<select className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-white outline-none" value={form.broker_account_id} onChange={(e) => setForm({ ...form, broker_account_id: e.target.value })}><option value="">{form.mode === "DEMO" ? "Select broker account" : "Optional"}</option>{demoBrokers.map((broker) => <option key={broker.id} value={broker.id}>{broker.account_label} • {broker.mode}</option>)}</select></label>
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
