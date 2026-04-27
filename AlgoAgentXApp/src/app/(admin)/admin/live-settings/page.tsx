"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, Pause, RefreshCw, Save, ShieldAlert, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { PlatformTradingSettings } from "@/types/live-trading";

const ToggleRow = ({ label, description, checked, disabled, onChange }: { label: string; description: string; checked: boolean; disabled?: boolean; onChange: (checked: boolean) => void }) => (
  <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/5 p-4 md:flex-row md:items-center md:justify-between">
    <div>
      <div className="font-semibold text-white">{label}</div>
      <div className="mt-1 text-sm text-purple-200">{description}</div>
    </div>
    <label className={`relative inline-flex cursor-pointer items-center ${disabled ? "opacity-50" : ""}`}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} className="peer sr-only" />
      <div className="h-7 w-12 rounded-full bg-white/10 after:absolute after:left-1 after:top-1 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all peer-checked:bg-lime-500 peer-checked:after:translate-x-5" />
    </label>
  </div>
);

export default function AdminLiveSettingsPage() {
  const { showToast } = useToast();
  const [settings, setSettings] = useState<PlatformTradingSettings | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      setBusy(true);
      setSettings(await liveTradingApi.getLiveSettings());
    } catch (error: any) {
      showToast(error.message || "Failed to load live trading settings", "error");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { load(); }, []);

  const patch = (key: keyof PlatformTradingSettings, value: any) => {
    if (!settings) return;
    setSettings({ ...settings, [key]: value });
  };

  const save = async () => {
    if (!settings) return;
    try {
      setBusy(true);
      const saved = await liveTradingApi.updateLiveSettings({
        paper_trading_enabled: settings.paper_trading_enabled,
        demo_trading_enabled: settings.demo_trading_enabled,
        live_trading_enabled: false,
        global_kill_switch: settings.global_kill_switch,
        max_global_demo_orders_per_day: settings.max_global_demo_orders_per_day ?? null,
        max_user_demo_orders_per_day: settings.max_user_demo_orders_per_day ?? null,
      });
      setSettings(saved);
      showToast("Live trading safety settings saved", "success");
    } catch (error: any) {
      showToast(error.message || "Failed to save settings", "error");
    } finally {
      setBusy(false);
    }
  };

  const killSwitch = async (enabled: boolean) => {
    try {
      setBusy(true);
      const saved = await liveTradingApi.setKillSwitch(enabled);
      setSettings(saved);
      showToast(enabled ? "Global kill switch enabled" : "Global kill switch disabled", enabled ? "error" : "success");
    } catch (error: any) {
      showToast(error.message || "Kill switch action failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const emergency = async (type: "stop" | "pause-demo") => {
    const ok = window.confirm(type === "stop" ? "Force stop all running/paused deployments?" : "Pause all running MT5 DEMO deployments?");
    if (!ok) return;
    try {
      setBusy(true);
      const res = type === "stop" ? await liveTradingApi.forceStopAllLive() : await liveTradingApi.pauseAllDemoLive();
      showToast(`Emergency action completed. Affected: ${res.affected}`, "success");
    } catch (error: any) {
      showToast(error.message || "Emergency action failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <PageShell>
      <PageHeader
        title="Live Trading Safety Settings"
        subtitle="Global controls for PAPER and MT5 DEMO execution. LIVE trading remains locked."
        actions={<div className="flex gap-2"><Link href="/admin/live-trading"><Button variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">Back to Control Center</Button></Link><Button onClick={load} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="h-4 w-4" />Refresh</Button></div>}
      />

      {!settings ? (
        <GlassCard className="p-6 text-purple-100">Loading live safety settings...</GlassCard>
      ) : (
        <div className="space-y-6">
          {settings.global_kill_switch && (
            <div className="rounded-2xl border border-red-400/40 bg-red-500/20 p-5 text-red-50 shadow-xl">
              <div className="flex items-center gap-3 text-lg font-bold"><AlertTriangle className="h-5 w-5" />Global Kill Switch is ON</div>
              <p className="mt-1 text-sm">All PAPER and DEMO order execution is blocked until this is turned off.</p>
            </div>
          )}

          <GlassCard className="p-6" hoverEffect={false}>
            <h2 className="text-xl font-bold text-lime-300">Global Execution Switches</h2>
            <div className="mt-5 grid grid-cols-1 gap-4">
              <ToggleRow label="Paper Trading" description="Allow PAPER simulated execution for user deployments." checked={settings.paper_trading_enabled} onChange={(v) => patch("paper_trading_enabled", v)} />
              <ToggleRow label="MT5 Demo Trading" description="Allow DEMO market orders through connected MT5 demo accounts." checked={settings.demo_trading_enabled} onChange={(v) => patch("demo_trading_enabled", v)} />
              <ToggleRow label="Live Trading" description="Disabled until final production, legal and risk review." checked={false} disabled onChange={() => {}} />
              <ToggleRow label="Global Kill Switch" description="Immediately block every new PAPER and DEMO order before execution." checked={settings.global_kill_switch} onChange={(v) => patch("global_kill_switch", v)} />
            </div>
          </GlassCard>

          <GlassCard className="p-6" hoverEffect={false}>
            <h2 className="text-xl font-bold text-lime-300">Demo Order Limits</h2>
            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="text-sm text-purple-100">Max global demo orders/day
                <input type="number" min={0} value={settings.max_global_demo_orders_per_day ?? ""} onChange={(e) => patch("max_global_demo_orders_per_day", e.target.value === "" ? null : Number(e.target.value))} className="mt-2 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-3 text-white outline-none focus:border-lime-300" placeholder="Unlimited" />
              </label>
              <label className="text-sm text-purple-100">Max demo orders/user/day
                <input type="number" min={0} value={settings.max_user_demo_orders_per_day ?? ""} onChange={(e) => patch("max_user_demo_orders_per_day", e.target.value === "" ? null : Number(e.target.value))} className="mt-2 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-3 text-white outline-none focus:border-lime-300" placeholder="Unlimited" />
              </label>
            </div>
            <Button disabled={busy} onClick={save} className="mt-5 gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Save className="h-4 w-4" />Save Settings</Button>
          </GlassCard>

          <GlassCard className="p-6" hoverEffect={false}>
            <h2 className="text-xl font-bold text-red-200">Emergency Admin Actions</h2>
            <p className="mt-1 text-sm text-purple-200">These actions create admin audit logs and live execution logs.</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button disabled={busy || settings.global_kill_switch} onClick={() => killSwitch(true)} className="gap-2 bg-red-500 text-white hover:bg-red-400"><ShieldAlert className="h-4 w-4" />Kill Switch ON</Button>
              <Button disabled={busy || !settings.global_kill_switch} onClick={() => killSwitch(false)} variant="outline" className="gap-2 border-lime-400/40 bg-lime-500/10 text-lime-100 hover:bg-lime-500/20"><ShieldAlert className="h-4 w-4" />Kill Switch OFF</Button>
              <Button disabled={busy} onClick={() => emergency("pause-demo")} className="gap-2 bg-yellow-500 text-slate-950 hover:bg-yellow-400"><Pause className="h-4 w-4" />Pause All Demo</Button>
              <Button disabled={busy} onClick={() => emergency("stop")} variant="outline" className="gap-2 border-red-400/40 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Square className="h-4 w-4" />Force Stop All</Button>
            </div>
          </GlassCard>
        </div>
      )}
    </PageShell>
  );
}
