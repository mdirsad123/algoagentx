"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle, Clock, Edit3, ExternalLink, Plus, RefreshCw, Trash2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, BrokerConnectionResult, BrokerProvider, LiveMode } from "@/types/live-trading";

const emptyMt5Form = {
  account_label: "MT5 Demo",
  broker_name: "MT5",
  broker_code: "MT5",
  mode: "DEMO" as LiveMode,
  server_name: "",
  login_id: "",
  encrypted_password: "",
};

const emptyUpstoxForm = {
  account_label: "Upstox India",
  client_id: "",
  client_secret: "",
  redirect_uri: "http://localhost:8000/api/v1/broker-accounts/upstox/callback",
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

function providerCard(provider: BrokerProvider, onMt5: () => void, onUpstox: () => void, connectingUpstox: boolean) {
  const code = provider.code?.toUpperCase();
  const isMt5 = code === "MT5";
  const isUpstox = code === "UPSTOX";
  const canConnect = provider.is_enabled && (isMt5 || isUpstox);
  return (
    <div key={provider.id} className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-lg font-bold text-white">{provider.name}</div>
          <div className="mt-1 text-sm text-purple-200">{provider.market_type} • {provider.auth_type}</div>
        </div>
        {provider.is_enabled ? <Badge className="bg-lime-500/20 text-lime-100">Enabled</Badge> : <Badge className="bg-red-500/20 text-red-100">Disabled</Badge>}
      </div>
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        {provider.supports_market_data && <Badge className="bg-white/10 text-purple-100">Market data</Badge>}
        {provider.supports_orders && <Badge className="bg-white/10 text-purple-100">Orders</Badge>}
        {provider.supports_websocket && <Badge className="bg-white/10 text-purple-100">Websocket</Badge>}
        {provider.supports_demo && <Badge className="bg-white/10 text-purple-100">Demo</Badge>}
      </div>
      <p className="mt-4 min-h-[42px] text-sm text-purple-200">
        {isMt5
          ? "Connect your local MT5 demo terminal for DEMO execution."
          : isUpstox
            ? "Connect your own Upstox developer app credentials. OAuth tokens stay encrypted."
            : "Future broker placeholder."}
      </p>
      <Button
        disabled={!canConnect || connectingUpstox}
        onClick={isMt5 ? onMt5 : onUpstox}
        className={canConnect ? "mt-4 gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400" : "mt-4 bg-white/10 text-purple-200"}
      >
        {isMt5 ? "Add MT5 Demo" : isUpstox ? <><ExternalLink className="h-4 w-4" /> {connectingUpstox ? "Opening..." : "Connect Upstox"}</> : "Coming later"}
      </Button>
    </div>
  );
}

export default function BrokersPage() {
  const { showToast } = useToast();
  const [providers, setProviders] = useState<BrokerProvider[]>([]);
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [showMt5Form, setShowMt5Form] = useState(false);
  const [showUpstoxForm, setShowUpstoxForm] = useState(false);
  const [editing, setEditing] = useState<BrokerAccount | null>(null);
  const [form, setForm] = useState(emptyMt5Form);
  const [upstoxForm, setUpstoxForm] = useState(emptyUpstoxForm);
  const [connectionResults, setConnectionResults] = useState<Record<string, BrokerConnectionResult>>({});
  const [connectingUpstox, setConnectingUpstox] = useState(false);

  const mt5Provider = providers.find((p) => p.code === "MT5");
  const connectedCount = useMemo(() => brokers.filter((b) => b.status === "CONNECTED").length, [brokers]);

  const load = async () => {
    try {
      setLoading(true);
      const [providerRows, accountRows] = await Promise.all([liveTradingApi.listAvailableBrokerProviders(), liveTradingApi.listBrokerAccounts()]);
      setProviders(providerRows);
      setBrokers(accountRows);
    } catch (error: any) {
      showToast(error.message || "Failed to load broker accounts", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const params = new URLSearchParams(window.location.search);
    if (params.get("broker") === "upstox") {
      if (params.get("connected") === "true") showToast("Upstox connected successfully", "success");
      else if (params.get("connected") === "false") showToast(params.get("error") || "Upstox connection failed", "error");
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyMt5Form);
    setShowMt5Form(true);
  };

  const openUpstox = () => {
    setUpstoxForm(emptyUpstoxForm);
    setShowUpstoxForm(true);
  };

  const openEdit = (broker: BrokerAccount) => {
    if ((broker.broker_code || broker.broker_name || "").toUpperCase() === "UPSTOX") {
      setUpstoxForm({
        account_label: broker.account_label || "Upstox India",
        client_id: broker.oauth_client_id || "",
        client_secret: "",
        redirect_uri: broker.oauth_redirect_uri || emptyUpstoxForm.redirect_uri,
      });
      setEditing(broker);
      setShowUpstoxForm(true);
      return;
    }
    setEditing(broker);
    setForm({ account_label: broker.account_label || "MT5 Demo", broker_name: broker.broker_name || "MT5", broker_code: broker.broker_code || broker.broker_name || "MT5", mode: "DEMO", server_name: broker.server_name || "", login_id: broker.login_id || "", encrypted_password: "" });
    setShowMt5Form(true);
  };

  const submitMt5 = async (event: FormEvent) => {
    event.preventDefault();
    try {
      setSaving(true);
      const payload = {
        broker_provider_id: mt5Provider?.id || null,
        broker_name: "MT5",
        broker_code: "MT5",
        auth_type: "PASSWORD",
        account_label: form.account_label,
        mode: "DEMO" as const,
        status: editing?.status || "DISCONNECTED" as const,
        server_name: form.server_name || null,
        login_id: form.login_id || null,
        encrypted_password: form.encrypted_password || null,
        metadata_json: { provider: "MT5", phase: "phase14-1-safe" },
      };
      if (editing) {
        await liveTradingApi.updateBrokerAccount(editing.id, payload);
        showToast("MT5 demo account updated", "success");
      } else {
        await liveTradingApi.createBrokerAccount(payload);
        showToast("MT5 demo account added", "success");
      }
      setShowMt5Form(false);
      await load();
    } catch (error: any) {
      showToast(error.message || "Failed to save broker account", "error");
    } finally {
      setSaving(false);
    }
  };

  const submitUpstox = async (event: FormEvent) => {
    event.preventDefault();
    if (editing && !upstoxForm.client_secret) {
      showToast("For security, enter the Upstox Client Secret again before reconnecting.", "error");
      return;
    }
    try {
      setSaving(true);
      setConnectingUpstox(true);
      let account: BrokerAccount;
      if (editing) {
        account = await liveTradingApi.updateBrokerAccount(editing.id, {
          account_label: upstoxForm.account_label,
          broker_name: "UPSTOX",
          broker_code: "UPSTOX",
          auth_type: "OAUTH2",
          mode: "DEMO",
          status: "DISCONNECTED",
          server_name: "Upstox API v2",
          oauth_client_id: upstoxForm.client_id,
          encrypted_client_secret: upstoxForm.client_secret,
          oauth_redirect_uri: upstoxForm.redirect_uri,
          metadata_json: { provider: "UPSTOX", market: "INDIAN_EQUITY", credential_mode: "BYO" },
        });
      } else {
        account = await liveTradingApi.createUpstoxBrokerAccount({ ...upstoxForm, redirect_after: "/brokers" });
      }
      const result = await liveTradingApi.getUpstoxAccountConnectUrl(account.id, "/brokers");
      window.location.href = result.auth_url;
    } catch (error: any) {
      showToast(error.message || "Failed to start Upstox OAuth", "error");
      setConnectingUpstox(false);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this broker account?")) return;
    try { await liveTradingApi.deleteBrokerAccount(id); showToast("Broker account deleted", "success"); await load(); } catch (error: any) { showToast(error.message || "Failed to delete broker account", "error"); }
  };

  const testConnection = async (broker: BrokerAccount) => {
    try {
      setTestingId(broker.id);
      const result = await liveTradingApi.testBrokerConnection(broker.id);
      setConnectionResults((prev) => ({ ...prev, [broker.id]: result.connection }));
      showToast(result.connection.message || (result.connection.connected ? "Broker connected" : "Broker connection failed"), result.connection.connected ? "success" : "error");
      await load();
    } catch (error: any) { showToast(error.message || "Connection test failed", "error"); } finally { setTestingId(null); }
  };

  return (
    <PageShell>
      <PageHeader title="Brokers" subtitle="Manage your trading workspace" />
      <GlassCard className="p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div><h1 className="text-2xl font-bold text-lime-300">Broker Accounts</h1><p className="mt-2 text-purple-100">Multi-broker framework is ready. MT5 works now; Upstox uses SaaS-safe BYO OAuth credentials per user.</p></div>
          <Button onClick={openCreate} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Plus className="h-4 w-4" /> Add MT5 Demo Account</Button>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-200">Total Accounts</p><p className="mt-2 text-2xl font-bold text-white">{brokers.length}</p></div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-200">Connected</p><p className="mt-2 text-2xl font-bold text-lime-300">{connectedCount}</p></div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-200">Available Providers</p><p className="mt-2 text-2xl font-bold text-white">{providers.length}</p></div>
        </div>

        <h2 className="mt-8 text-xl font-bold text-white">Choose Broker Provider</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">{providers.map((p) => providerCard(p, openCreate, openUpstox, connectingUpstox))}</div>

        {showMt5Form && (
          <form onSubmit={submitMt5} className="mt-8 rounded-2xl border border-white/10 bg-black/10 p-5">
            <div className="mb-4 flex items-center justify-between gap-4"><div><h2 className="text-lg font-bold text-white">{editing ? "Edit MT5 Demo Account" : "Add MT5 Demo Account"}</h2><p className="text-sm text-purple-200">Credentials are encrypted on backend and never returned to frontend.</p></div><Button type="button" variant="ghost" className="text-purple-100 hover:bg-white/10" onClick={() => setShowMt5Form(false)}>Cancel</Button></div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              <label className="text-sm text-purple-100">Account Label<input value={form.account_label} onChange={(e) => setForm({ ...form, account_label: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
              <label className="text-sm text-purple-100">Provider<input value="MT5 / MetaTrader 5" readOnly className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
              <label className="text-sm text-purple-100">Mode<input value="DEMO" readOnly className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
              <label className="text-sm text-purple-100">Server Name<input value={form.server_name} onChange={(e) => setForm({ ...form, server_name: e.target.value })} placeholder="Exness-MT5Trial17" className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
              <label className="text-sm text-purple-100">Login ID<input value={form.login_id} onChange={(e) => setForm({ ...form, login_id: e.target.value })} placeholder="463345714" className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
              <label className="text-sm text-purple-100">Password<input value={form.encrypted_password} onChange={(e) => setForm({ ...form, encrypted_password: e.target.value })} type="password" placeholder={editing ? "Leave blank to keep existing" : "Investor/trading password"} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required={!editing} /></label>
            </div>
            <Button type="submit" disabled={saving} className="mt-5 bg-lime-500 text-slate-950 hover:bg-lime-400">{saving ? "Saving..." : "Save Broker Account"}</Button>
          </form>
        )}

        {showUpstoxForm && (
          <form onSubmit={submitUpstox} className="mt-8 rounded-2xl border border-white/10 bg-black/10 p-5">
            <div className="mb-4 flex items-center justify-between gap-4"><div><h2 className="text-lg font-bold text-white">{editing ? "Reconnect Upstox" : "Connect Upstox"}</h2><p className="text-sm text-purple-200">Use the exact Client ID and Redirect URI registered in your Upstox Developer app.</p></div><Button type="button" variant="ghost" className="text-purple-100 hover:bg-white/10" onClick={() => { setShowUpstoxForm(false); setEditing(null); }}>Cancel</Button></div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="text-sm text-purple-100">Account Label<input value={upstoxForm.account_label} onChange={(e) => setUpstoxForm({ ...upstoxForm, account_label: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
              <label className="text-sm text-purple-100">Upstox Client ID / API Key<input value={upstoxForm.client_id} onChange={(e) => setUpstoxForm({ ...upstoxForm, client_id: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
              <label className="text-sm text-purple-100">Upstox Client Secret<input value={upstoxForm.client_secret} onChange={(e) => setUpstoxForm({ ...upstoxForm, client_secret: e.target.value })} type="password" className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
              <label className="text-sm text-purple-100">Redirect URI<input value={upstoxForm.redirect_uri} onChange={(e) => setUpstoxForm({ ...upstoxForm, redirect_uri: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
            </div>
            <div className="mt-4 rounded-xl border border-yellow-500/20 bg-yellow-500/10 p-3 text-sm text-yellow-100">This Redirect URI must match exactly inside Upstox Developer &gt; Apps. Default: http://localhost:8000/api/v1/broker-accounts/upstox/callback</div>
            <Button type="submit" disabled={saving || connectingUpstox} className="mt-5 gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><ExternalLink className="h-4 w-4" />{saving || connectingUpstox ? "Opening Upstox..." : "Save & Open Upstox OAuth"}</Button>
          </form>
        )}

        <div className="mt-8 space-y-4">
          {loading && <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-purple-100">Loading broker accounts...</div>}
          {!loading && brokers.length === 0 && <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-purple-100">No broker accounts yet. Add MT5 demo or connect Upstox to start.</div>}
          {brokers.map((broker) => {
            const result = connectionResults[broker.id];
            const last = (broker.metadata_json as any)?.last_test;
            const isUpstox = (broker.broker_code || broker.broker_name || "").toUpperCase() === "UPSTOX";
            return (
              <div key={broker.id} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
                  <div className="flex items-start gap-3">{broker.status === "CONNECTED" ? <CheckCircle className="h-5 w-5 text-green-300" /> : broker.status === "ERROR" ? <AlertCircle className="h-5 w-5 text-yellow-300" /> : <XCircle className="h-5 w-5 text-red-300" />}<div><div className="flex flex-wrap items-center gap-2"><h3 className="text-lg font-bold text-white">{broker.account_label}</h3>{statusBadge(broker.status)}<Badge className="bg-white/10 text-purple-100">{broker.broker_code || broker.broker_name}</Badge>{isUpstox && <Badge className="bg-white/10 text-purple-100">Indian Equity</Badge>}</div><p className="mt-1 text-sm text-purple-200">{isUpstox ? (broker.login_id || "OAuth pending") : broker.login_id} • {broker.server_name}</p>{isUpstox && (broker.metadata_json as any)?.profile?.user_name && <p className="mt-1 text-xs text-purple-300">{String((broker.metadata_json as any).profile.user_name)} • {String((broker.metadata_json as any).profile.broker || "Upstox")}</p>}<p className="mt-1 flex items-center gap-1 text-xs text-purple-300"><Clock className="h-3 w-3" /> Last connected: {formatDate(broker.last_connected_at)}</p></div></div>
                  <div className="flex flex-wrap gap-2"><Button onClick={() => testConnection(broker)} disabled={testingId === broker.id} className="gap-2 bg-white/10 text-white hover:bg-white/15"><RefreshCw className="h-4 w-4" /> Test</Button><Button onClick={() => openEdit(broker)} className="gap-2 bg-white/10 text-white hover:bg-white/15"><Edit3 className="h-4 w-4" /> {isUpstox ? "Reconnect" : "Edit"}</Button><Button onClick={() => remove(broker.id)} className="gap-2 bg-red-500/15 text-red-100 hover:bg-red-500/25"><Trash2 className="h-4 w-4" /> Delete</Button></div>
                </div>
                {(result || last) && <div className="mt-4 rounded-xl border border-white/10 bg-black/10 p-4 text-sm text-purple-100"><div className="font-semibold text-white">Last connection result</div><p className="mt-1">{result?.message || last?.message || "No details"}</p><div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-3"><span>Balance: {isUpstox ? "—" : `$${money(result?.balance || last?.balance)}`}</span><span>Equity: {isUpstox ? "—" : `$${money(result?.equity || last?.equity)}`}</span><span>Currency: {result?.currency || last?.currency || (isUpstox ? "INR" : "—")}</span></div></div>}
              </div>
            );
          })}
        </div>
      </GlassCard>
    </PageShell>
  );
}
