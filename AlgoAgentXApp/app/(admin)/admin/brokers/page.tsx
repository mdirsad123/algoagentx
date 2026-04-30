"use client";

import { useEffect, useState } from "react";
import { RefreshCw, ShieldCheck, ShieldOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerProvider } from "@/types/live-trading";

function yn(value: boolean) {
  return value ? <Badge className="border-lime-400/30 bg-lime-500/15 text-lime-100">Yes</Badge> : <Badge className="border-white/10 bg-white/10 text-purple-100">No</Badge>;
}

export default function AdminBrokersPage() {
  const { showToast } = useToast();
  const [providers, setProviders] = useState<BrokerProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      setProviders(await liveTradingApi.adminListBrokerProviders());
    } catch (error: any) {
      showToast(error.message || "Failed to load broker providers", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const toggle = async (provider: BrokerProvider) => {
    try {
      setSavingId(provider.id);
      if (provider.is_enabled) {
        await liveTradingApi.adminDisableBrokerProvider(provider.id);
        showToast(`${provider.code} disabled`, "success");
      } else {
        await liveTradingApi.adminEnableBrokerProvider(provider.id);
        showToast(`${provider.code} enabled`, "success");
      }
      await load();
    } catch (error: any) {
      showToast(error.message || "Failed to update provider", "error");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <PageShell>
      <PageHeader title="Admin Brokers" subtitle="Manage broker providers for AlgoAgentX SaaS" />
      <GlassCard className="p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div>
            <h1 className="text-2xl font-bold text-lime-300">Broker Provider Catalog</h1>
            <p className="mt-2 text-purple-100">MT5 remains working. Upstox is visible as coming next phase. LIVE trading remains disabled.</p>
          </div>
          <Button onClick={load} disabled={loading} className="gap-2 bg-white/10 text-white hover:bg-white/15"><RefreshCw className="h-4 w-4" /> Refresh</Button>
        </div>

        <div className="mt-8 overflow-x-auto rounded-2xl border border-white/10">
          <table className="min-w-full text-left text-sm text-purple-100">
            <thead className="bg-white/8 text-xs uppercase tracking-wide text-purple-200">
              <tr>
                <th className="px-4 py-3">Code</th><th className="px-4 py-3">Name</th><th className="px-4 py-3">Market</th><th className="px-4 py-3">Auth</th><th className="px-4 py-3">Data</th><th className="px-4 py-3">Orders</th><th className="px-4 py-3">Websocket</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.id} className="border-t border-white/10 align-top">
                  <td className="px-4 py-4 font-bold text-white">{p.code}</td>
                  <td className="px-4 py-4"><div className="font-semibold text-white">{p.name}</div><div className="mt-1 max-w-sm text-xs text-purple-200">{p.admin_notes || "—"}</div></td>
                  <td className="px-4 py-4">{p.market_type}</td>
                  <td className="px-4 py-4">{p.auth_type}</td>
                  <td className="px-4 py-4">{yn(p.supports_market_data)}</td>
                  <td className="px-4 py-4">{yn(p.supports_orders)}</td>
                  <td className="px-4 py-4">{yn(p.supports_websocket)}</td>
                  <td className="px-4 py-4">{p.is_enabled ? <Badge className="bg-lime-500/20 text-lime-100">Enabled</Badge> : <Badge className="bg-red-500/20 text-red-100">Disabled</Badge>}</td>
                  <td className="px-4 py-4"><Button disabled={savingId === p.id} onClick={() => toggle(p)} className="gap-2 bg-white/10 text-white hover:bg-white/15">{p.is_enabled ? <ShieldOff className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}{p.is_enabled ? "Disable" : "Enable"}</Button></td>
                </tr>
              ))}
              {!loading && providers.length === 0 && <tr><td colSpan={9} className="px-4 py-8 text-center text-purple-200">No broker providers found. Run the Phase 13 SQL migration.</td></tr>}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </PageShell>
  );
}
