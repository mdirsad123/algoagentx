"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle, Edit3, Plus, RefreshCw, Trash2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, BrokerConnectionResult, LiveMode } from "@/types/live-trading";

const emptyForm = {
  account_label: "MT5 Demo",
  broker_name: "MT5",
  mode: "DEMO" as LiveMode,
  server_name: "",
  login_id: "",
  encrypted_password: "",
};

const formatDate = (value?: string | null) => (value ? new Date(value).toLocaleString() : "Not connected yet");
const money = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

function statusBadge(status: string) {
  const normalized = status?.toUpperCase();
  if (normalized === "CONNECTED") return <Badge className="border-green-500/30 bg-green-500/20 text-green-100">Connected</Badge>;
  if (normalized === "ERROR") return <Badge className="border-yellow-500/30 bg-yellow-500/20 text-yellow-100">Error</Badge>;
  if (normalized === "EXPIRED") return <Badge className="border-orange-500/30 bg-orange-500/20 text-orange-100">Expired</Badge>;
  return <Badge className="border-red-500/30 bg-red-500/20 text-red-100">Disconnected</Badge>;
}

function statusIcon(status: string) {
  const normalized = status?.toUpperCase();
  if (normalized === "CONNECTED") return <CheckCircle className="h-5 w-5 text-green-300" />;
  if (normalized === "ERROR") return <AlertCircle className="h-5 w-5 text-yellow-300" />;
  return <XCircle className="h-5 w-5 text-red-300" />;
}

export default function BrokersPage() {
  const { showToast } = useToast();
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<BrokerAccount | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [connectionResults, setConnectionResults] = useState<Record<string, BrokerConnectionResult>>({});

  const connectedCount = useMemo(() => brokers.filter((b) => b.status === "CONNECTED").length, [brokers]);

  const load = async () => {
    try {
      setLoading(true);
      setBrokers(await liveTradingApi.listBrokerAccounts());
    } catch (error: any) {
      showToast(error.message || "Failed to load broker accounts", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setShowForm(true);
  };

  const openEdit = (broker: BrokerAccount) => {
    setEditing(broker);
    setForm({
      account_label: broker.account_label || "MT5 Demo",
      broker_name: broker.broker_name || "MT5",
      mode: "DEMO",
      server_name: broker.server_name || "",
      login_id: broker.login_id || "",
      encrypted_password: "",
    });
    setShowForm(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      setSaving(true);
      const payload = {
        broker_name: "MT5",
        account_label: form.account_label,
        mode: "DEMO" as const,
        status: editing?.status || "DISCONNECTED" as const,
        server_name: form.server_name || null,
        login_id: form.login_id || null,
        encrypted_password: form.encrypted_password || null,
        metadata_json: { provider: "MT5", phase: "mt5-demo-adapter" },
      };
      if (editing) {
        await liveTradingApi.updateBrokerAccount(editing.id, payload);
        showToast("MT5 demo account updated", "success");
      } else {
        await liveTradingApi.createBrokerAccount(payload);
        showToast("MT5 demo account added", "success");
      }
      setShowForm(false);
      await load();
    } catch (error: any) {
      showToast(error.message || "Failed to save broker account", "error");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this broker account?")) return;
    try {
      await liveTradingApi.deleteBrokerAccount(id);
      showToast("Broker account deleted", "success");
      await load();
    } catch (error: any) {
      showToast(error.message || "Failed to delete broker account", "error");
    }
  };

  const testConnection = async (broker: BrokerAccount) => {
    try {
      setTestingId(broker.id);
      const result = await liveTradingApi.testBrokerConnection(broker.id);
      setConnectionResults((prev) => ({ ...prev, [broker.id]: result.connection }));
      showToast(result.connection.message || (result.connection.connected ? "MT5 connected" : "MT5 connection failed"), result.connection.connected ? "success" : "error");
      await load();
    } catch (error: any) {
      showToast(error.message || "MT5 connection test failed", "error");
    } finally {
      setTestingId(null);
    }
  };

  return (
    <PageShell>
      <PageHeader title="Brokers" subtitle="Manage your trading workspace" />

      <GlassCard className="p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div>
            <h1 className="text-2xl font-bold text-lime-300">Broker Accounts</h1>
            <p className="mt-2 text-purple-100">Connect one MT5 demo account first. Real LIVE execution is still blocked.</p>
          </div>
          <Button onClick={openCreate} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400">
            <Plus className="h-4 w-4" /> Add MT5 Demo Account
          </Button>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-200">Total Accounts</p><p className="mt-2 text-2xl font-bold text-white">{brokers.length}</p></div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-200">Connected</p><p className="mt-2 text-2xl font-bold text-lime-300">{connectedCount}</p></div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-200">Primary Broker</p><p className="mt-2 text-2xl font-bold text-white">MT5 Demo</p></div>
        </div>

        {showForm && (
          <form onSubmit={submit} className="mt-8 rounded-2xl border border-white/10 bg-black/10 p-5">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-white">{editing ? "Edit MT5 Demo Account" : "Add MT5 Demo Account"}</h2>
                <p className="text-sm text-purple-200">Credentials are stored encrypted on backend. Password is never shown again.</p>
              </div>
              <Button type="button" variant="ghost" className="text-purple-100 hover:bg-white/10" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              <label className="text-sm text-purple-100">Account Label<input value={form.account_label} onChange={(e) => setForm({ ...form, account_label: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300/60" required /></label>
              <label className="text-sm text-purple-100">Broker Name<input value="MT5" readOnly className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
              <label className="text-sm text-purple-100">Mode<input value="DEMO" readOnly className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
              <label className="text-sm text-purple-100">Server Name<input value={form.server_name} onChange={(e) => setForm({ ...form, server_name: e.target.value })} placeholder="Exness-MT5Trial17" className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300/60" required /></label>
              <label className="text-sm text-purple-100">Login ID<input value={form.login_id} onChange={(e) => setForm({ ...form, login_id: e.target.value })} placeholder="463345714" className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300/60" required /></label>
              <label className="text-sm text-purple-100">Password<input type="password" value={form.encrypted_password} onChange={(e) => setForm({ ...form, encrypted_password: e.target.value })} placeholder={editing ? "Leave blank to keep old password" : "MT5 demo password"} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none focus:border-lime-300/60" /></label>
            </div>
            <div className="mt-5 flex flex-wrap gap-2"><Button disabled={saving} type="submit" className="bg-lime-500 text-slate-950 hover:bg-lime-400">{saving ? "Saving..." : "Save MT5 Demo"}</Button></div>
          </form>
        )}

        <div className="mt-8">
          {loading ? (
            <div className="text-purple-100">Loading brokers...</div>
          ) : brokers.length === 0 ? (
            <EmptyState title="No broker connected" description="Add an MT5 demo account to enable DEMO mode deployments." />
          ) : (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              {brokers.map((broker) => {
                const lastTest = (broker.metadata_json?.last_test || connectionResults[broker.id]) as BrokerConnectionResult | undefined;
                return (
                  <div key={broker.id} className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-xl">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">{statusIcon(broker.status)}<h3 className="text-lg font-bold text-white">{broker.account_label}</h3></div>
                        <p className="mt-1 text-sm text-purple-200">{broker.broker_name} • {broker.mode}</p>
                      </div>
                      {statusBadge(broker.status)}
                    </div>

                    <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-xs text-purple-300">Login</p><p className="mt-1 font-semibold text-white">{broker.login_id || "—"}</p></div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-xs text-purple-300">Server</p><p className="mt-1 font-semibold text-white">{broker.server_name || "—"}</p></div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-xs text-purple-300">Balance</p><p className="mt-1 font-semibold text-white">{lastTest?.balance ? money(lastTest.balance) : "—"}</p></div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-xs text-purple-300">Equity</p><p className="mt-1 font-semibold text-white">{lastTest?.equity ? money(lastTest.equity) : "—"}</p></div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-xs text-purple-300">Currency</p><p className="mt-1 font-semibold text-white">{lastTest?.currency || "—"}</p></div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-xs text-purple-300">Last connected</p><p className="mt-1 font-semibold text-white">{formatDate(broker.last_connected_at)}</p></div>
                    </div>

                    {lastTest?.message && <div className="mt-3 rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-purple-100">{lastTest.message}</div>}

                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button disabled={testingId === broker.id} onClick={() => testConnection(broker)} className="gap-2 bg-blue-500 text-white hover:bg-blue-400"><RefreshCw className="h-4 w-4" />{testingId === broker.id ? "Testing..." : "Test Connection"}</Button>
                      <Button onClick={() => openEdit(broker)} variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><Edit3 className="h-4 w-4" />Edit</Button>
                      <Button onClick={() => remove(broker.id)} variant="outline" className="gap-2 border-red-400/30 bg-red-500/10 text-red-100 hover:bg-red-500/20"><Trash2 className="h-4 w-4" />Delete</Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </GlassCard>
    </PageShell>
  );
}
