"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle, Clock, Copy, Download, Edit3, ExternalLink, KeyRound, Plus, RefreshCw, Trash2, WifiOff, X, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, BrokerConnectionResult, BrokerProvider, LiveMode, MT5AgentStatus, CTraderTradingAccount } from "@/types/live-trading";
import { getBackendCallbackUrl } from "@/lib/api-base";

const CRYPTO_CODES = new Set(["BINANCE", "BYBIT", "OKX"]);
const CTRADER_CODES = new Set(["CTRADER", "CTRADER_API"]);

type ActiveForm = null | "MT5" | "UPSTOX" | "CRYPTO" | "CTRADER";

const emptyMt5Form = {
  account_label: "MT5 Demo",
  broker_name: "MT5",
  broker_code: "MT5",
  mode: "DEMO" as LiveMode,
  server_name: "",
  login_id: "",
};

const makeEmptyUpstoxForm = () => ({
  account_label: "Upstox India",
  client_id: "",
  client_secret: "",
  redirect_uri: process.env.NEXT_PUBLIC_UPSTOX_REDIRECT_URI || getBackendCallbackUrl("/api/v1/broker-accounts/upstox/callback"),
});

const makeEmptyCryptoForm = (code = "BINANCE") => ({
  code,
  account_label: `${displayBrokerName(code)} API`,
  api_key: "",
  api_secret: "",
  passphrase: "",
});

const makeEmptyCtraderForm = () => ({
  account_label: "cTrader Open API",
  client_id: "",
  client_secret: "",
  redirect_uri: getBackendCallbackUrl("/api/v1/broker-accounts/ctrader/callback"),
});

function displayBrokerName(code?: string | null) {
  const value = String(code || "").toUpperCase();
  if (value === "UPSTOX") return "Upstox India";
  if (value === "MT5") return "MT5 Agent / MetaTrader 5";
  if (value === "CTRADER" || value === "CTRADER_API") return "cTrader Open API";
  if (value === "ANGEL_ONE") return "Angel One";
  if (value === "BINANCE") return "Binance";
  if (value === "BYBIT") return "Bybit";
  if (value === "OKX") return "OKX";
  if (value === "ZERODHA") return "Zerodha Kite";
  if (value === "DHAN") return "Dhan";
  if (value === "GROWW") return "Groww";
  return value || "Broker";
}

const formatDate = (value?: string | null) => (value ? new Date(value).toLocaleString() : "Not connected yet");
const money = (value: unknown) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
const brokerCodeOf = (broker: BrokerAccount) => (broker.broker_code || broker.broker_name || "").toUpperCase();
const statusOf = (broker: BrokerAccount, agent?: MT5AgentStatus | null) => {
  const code = brokerCodeOf(broker);
  if (code === "MT5" && agent?.status !== "CONNECTED" && broker.status === "CONNECTED") return "AGENT_OFFLINE";
  return String(broker.status || "DISCONNECTED").toUpperCase();
};

function statusBadge(status: string) {
  const normalized = String(status || "DISCONNECTED").toUpperCase();
  if (normalized === "CONNECTED") return <Badge className="border-green-500/30 bg-green-500/20 text-green-100">Connected</Badge>;
  if (normalized === "PENDING_AUTH") return <Badge className="border-blue-500/30 bg-blue-500/20 text-blue-100">Pending Auth</Badge>;
  if (normalized === "PENDING_ACCOUNT_SYNC") return <Badge className="border-blue-500/30 bg-blue-500/20 text-blue-100">Sync Required</Badge>;
  if (normalized === "AGENT_OFFLINE") return <Badge className="border-orange-500/30 bg-orange-500/20 text-orange-100">Agent Offline</Badge>;
  if (normalized === "COMING_SOON") return <Badge className="border-white/20 bg-white/10 text-purple-100">Coming Soon</Badge>;
  if (normalized === "ERROR") return <Badge className="border-yellow-500/30 bg-yellow-500/20 text-yellow-100">Error</Badge>;
  return <Badge className="border-red-500/30 bg-red-500/20 text-red-100">Disconnected</Badge>;
}

function agentStatusBadge(agent?: MT5AgentStatus | null) {
  return agent?.status === "CONNECTED" ? (
    <Badge className="border-green-500/30 bg-green-500/20 text-green-100">Agent Connected</Badge>
  ) : (
    <Badge className="border-orange-500/30 bg-orange-500/20 text-orange-100">Agent Disconnected</Badge>
  );
}

function categoryTitle(provider: BrokerProvider) {
  const code = provider.code?.toUpperCase();
  if (CRYPTO_CODES.has(code)) return "Crypto API Broker";
  if (code === "MT5") return "MT5 Agent Broker";
  if (CTRADER_CODES.has(code)) return "Cloud Forex Broker";
  return provider.broker_category || "Cloud Broker";
}

function defaultCtraderOrderSymbol(broker: BrokerAccount) {
  const meta = (broker.metadata_json || {}) as any;
  const preview = Array.isArray(meta.ctrader_symbols_preview) ? meta.ctrader_symbols_preview : [];
  const first = preview.find((item: any) => item?.symbol_name || item?.trading_symbol || item?.symbol);
  return String(first?.symbol_name || first?.trading_symbol || first?.symbol || "EURUSD").toUpperCase();
}

function isCtraderDemoSelected(selected: any, broker: BrokerAccount) {
  const mode = String(selected?.account_type || broker.mode || "DEMO").toUpperCase();
  return !mode.includes("LIVE") && mode !== "REAL";
}

export default function BrokersPage() {
  const { showToast } = useToast();
  const [providers, setProviders] = useState<BrokerProvider[]>([]);
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [connectOpen, setConnectOpen] = useState(false);
  const [activeForm, setActiveForm] = useState<ActiveForm>(null);
  const [editing, setEditing] = useState<BrokerAccount | null>(null);
  const [form, setForm] = useState(emptyMt5Form);
  const [upstoxForm, setUpstoxForm] = useState(makeEmptyUpstoxForm);
  const [cryptoForm, setCryptoForm] = useState(makeEmptyCryptoForm("BINANCE"));
  const [ctraderForm, setCtraderForm] = useState(makeEmptyCtraderForm);
  const [connectionResults, setConnectionResults] = useState<Record<string, BrokerConnectionResult>>({});
  const [connectingUpstox, setConnectingUpstox] = useState(false);
  const [agentStatuses, setAgentStatuses] = useState<Record<string, MT5AgentStatus | null>>({});
  const [generatedAgentToken, setGeneratedAgentToken] = useState("");
  const [generatingAgentToken, setGeneratingAgentToken] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<BrokerAccount | null>(null);
  const [deleteWarning, setDeleteWarning] = useState<string | null>(null);
  const [deleteForce, setDeleteForce] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [ctraderSelectTarget, setCtraderSelectTarget] = useState<{ broker: BrokerAccount; accounts: CTraderTradingAccount[] } | null>(null);
  const [ctraderOrderTarget, setCtraderOrderTarget] = useState<BrokerAccount | null>(null);
  const [ctraderOrderForm, setCtraderOrderForm] = useState({ symbol: "EURUSD", side: "BUY" as "BUY" | "SELL", volume: "1000", stop_loss: "", take_profit: "" });
  const [placingCtraderOrder, setPlacingCtraderOrder] = useState(false);
  const [ctraderOrderResult, setCtraderOrderResult] = useState<Record<string, unknown> | null>(null);

  const mt5Provider = providers.find((p) => p.code === "MT5");
  const connectedCount = useMemo(() => brokers.filter((b) => statusOf(b, agentStatuses[b.id]) === "CONNECTED").length, [brokers, agentStatuses]);
  const groupedProviders = useMemo(() => {
    const groups: Record<string, BrokerProvider[]> = { "Cloud Brokers": [], "Crypto API Brokers": [], "Forex / MT5 Brokers": [] };
    providers.forEach((provider) => {
      const code = provider.code.toUpperCase();
      if (CRYPTO_CODES.has(code)) groups["Crypto API Brokers"].push(provider);
      else if (code === "MT5" || CTRADER_CODES.has(code)) groups["Forex / MT5 Brokers"].push(provider);
      else groups["Cloud Brokers"].push(provider);
    });
    return groups;
  }, [providers]);

  const load = async () => {
    try {
      setLoading(true);
      const [providerRows, accountRows] = await Promise.all([liveTradingApi.listAvailableBrokerProviders(), liveTradingApi.listBrokerAccounts()]);
      setProviders(providerRows);
      setBrokers(accountRows);
      const mt5Rows = accountRows.filter((b) => brokerCodeOf(b) === "MT5");
      const statusEntries = await Promise.all(mt5Rows.map(async (b) => {
        try { return [b.id, await liveTradingApi.getMt5AgentStatus(b.id)] as const; } catch { return [b.id, null] as const; }
      }));
      setAgentStatuses(Object.fromEntries(statusEntries));
    } catch (error: any) {
      showToast(error.message || "Failed to load broker accounts", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const params = new URLSearchParams(window.location.search);
    const brokerParam = params.get("broker");
    if (brokerParam === "upstox" || brokerParam === "ctrader") {
      const label = brokerParam === "ctrader" ? "cTrader" : "Upstox";
      if (params.get("connected") === "true") showToast(brokerParam === "ctrader" ? "cTrader account connected successfully." : `${label} connected successfully`, "success");
      else if (params.get("connected") === "false") showToast(params.get("error") || `${label} connection failed`, "error");
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  const closeConnect = () => {
    setConnectOpen(false);
    setActiveForm(null);
    setEditing(null);
    setGeneratedAgentToken("");
  };

  const openSelector = () => {
    setEditing(null);
    setActiveForm(null);
    setGeneratedAgentToken("");
    setConnectOpen(true);
  };

  const openMt5Form = (broker?: BrokerAccount | null) => {
    setEditing(broker || null);
    setGeneratedAgentToken("");
    setForm(broker ? { ...emptyMt5Form, account_label: broker.account_label || "MT5 Demo", server_name: broker.server_name || "", login_id: broker.login_id || "" } : emptyMt5Form);
    setActiveForm("MT5");
    setConnectOpen(true);
  };

  const openUpstoxForm = async (broker?: BrokerAccount | null) => {
    setEditing(broker || null);
    let redirectUri = broker?.oauth_redirect_uri || makeEmptyUpstoxForm().redirect_uri;
    try {
      const redirect = await liveTradingApi.getBrokerRedirectUri("upstox");
      redirectUri = redirect.redirect_uri || redirectUri;
    } catch {
      // Keep local fallback when API is still restarting.
    }
    setUpstoxForm(broker ? {
      account_label: broker.account_label || "Upstox India",
      client_id: broker.oauth_client_id || "",
      client_secret: "",
      redirect_uri: redirectUri,
    } : { ...makeEmptyUpstoxForm(), redirect_uri: redirectUri });
    setActiveForm("UPSTOX");
    setConnectOpen(true);
  };

  const openCtraderForm = async (broker?: BrokerAccount | null) => {
    setEditing(broker || null);
    let redirectUri = broker?.oauth_redirect_uri || makeEmptyCtraderForm().redirect_uri;
    try {
      const redirect = await liveTradingApi.getBrokerRedirectUri("ctrader");
      redirectUri = redirect.redirect_uri || redirectUri;
    } catch {
      // Keep local fallback when API is still restarting.
    }
    setCtraderForm(broker ? {
      account_label: broker.account_label || "cTrader Open API",
      client_id: broker.oauth_client_id || "",
      client_secret: "",
      redirect_uri: redirectUri,
    } : { ...makeEmptyCtraderForm(), redirect_uri: redirectUri });
    setActiveForm("CTRADER");
    setConnectOpen(true);
  };

  const openCryptoForm = (code: string, broker?: BrokerAccount | null) => {
    const normalized = code.toUpperCase();
    setEditing(broker || null);
    setCryptoForm({ ...makeEmptyCryptoForm(normalized), account_label: broker?.account_label || `${displayBrokerName(normalized)} API` });
    setActiveForm("CRYPTO");
    setConnectOpen(true);
  };

  const reconnect = (broker: BrokerAccount) => {
    const code = brokerCodeOf(broker);
    if (code === "MT5") return openMt5Form(broker);
    if (code === "UPSTOX") { void openUpstoxForm(broker); return; }
    if (CTRADER_CODES.has(code)) { void openCtraderForm(broker); return; }
    if (CRYPTO_CODES.has(code)) return openCryptoForm(code, broker);
    showToast("This broker is coming soon. Connection flow is not implemented yet.", "error");
  };

  const submitMt5 = async (event: FormEvent) => {
    event.preventDefault();
    try {
      setSaving(true);
      const payload = {
        broker_provider_id: mt5Provider?.id || null,
        broker_name: "MT5",
        broker_code: "MT5",
        auth_type: "MT5_AGENT",
        account_label: form.account_label,
        mode: "DEMO" as const,
        status: editing?.status || "DISCONNECTED" as const,
        server_name: form.server_name || null,
        login_id: form.login_id || null,
        metadata_json: { provider: "MT5", setup_mode: "MT5_AGENT", mt5_agent: { status: "AGENT_REQUIRED", message: "Install AlgoAgentX MT5 Agent on your Windows PC or VPS where MetaTrader 5 is running." } },
      };
      const savedAccount = editing ? await liveTradingApi.updateBrokerAccount(editing.id, payload) : await liveTradingApi.createBrokerAccount(payload);
      const tokenResult = await liveTradingApi.generateMt5AgentToken(savedAccount.id, "DEMO");
      setGeneratedAgentToken(tokenResult.agent_token);
      setEditing(savedAccount);
      showToast("MT5 Agent token generated. Copy it now; it is shown only once.", "success");
      await load();
    } catch (error: any) {
      showToast(error.message || "Failed to save MT5 Agent account", "error");
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
      const account = editing ? await liveTradingApi.updateBrokerAccount(editing.id, {
        account_label: upstoxForm.account_label,
        broker_name: "UPSTOX",
        broker_code: "UPSTOX",
        auth_type: "OAUTH2",
        mode: "DEMO",
        status: "PENDING_AUTH",
        server_name: "Upstox API v2",
        oauth_client_id: upstoxForm.client_id,
        encrypted_client_secret: upstoxForm.client_secret,
        oauth_redirect_uri: upstoxForm.redirect_uri,
        metadata_json: { provider: "UPSTOX", market: "INDIAN_EQUITY", credential_mode: "BYO" },
      }) : await liveTradingApi.createUpstoxBrokerAccount({ ...upstoxForm, redirect_after: "/brokers" });
      const result = await liveTradingApi.getUpstoxAccountConnectUrl(account.id, "/brokers");
      window.location.href = result.auth_url;
    } catch (error: any) {
      showToast(error.message || "Failed to start Upstox OAuth", "error");
      setConnectingUpstox(false);
    } finally {
      setSaving(false);
    }
  };

  const submitCtrader = async (event: FormEvent) => {
    event.preventDefault();
    if (editing && !ctraderForm.client_secret) {
      showToast("For security, enter the cTrader Client Secret again before reconnecting.", "error");
      return;
    }
    try {
      setSaving(true);
      const result = await liveTradingApi.connectCtraderOAuth({
        broker_account_id: editing?.id || null,
        account_label: ctraderForm.account_label,
        client_id: ctraderForm.client_id,
        client_secret: ctraderForm.client_secret,
        redirect_uri: ctraderForm.redirect_uri,
        redirect_after: "/brokers",
      });
      window.location.href = result.auth_url;
    } catch (error: any) {
      showToast(error.message || "Failed to start cTrader OAuth", "error");
    } finally {
      setSaving(false);
    }
  };

  const submitCrypto = async (event: FormEvent) => {
    event.preventDefault();
    const code = cryptoForm.code.toUpperCase();
    try {
      setSaving(true);
      const payload = {
        broker_name: code,
        broker_code: code,
        auth_type: "API_KEY_SECRET",
        account_label: cryptoForm.account_label,
        mode: "DEMO" as const,
        status: "DISCONNECTED" as const,
        server_name: `${displayBrokerName(code)} API`,
        login_id: "API key saved",
        encrypted_api_key: cryptoForm.api_key,
        encrypted_api_secret: cryptoForm.api_secret,
        encrypted_api_passphrase: code === "OKX" ? cryptoForm.passphrase : null,
        metadata_json: { provider: code, market: "CRYPTO", setup_mode: "API_KEY_SECRET", live_orders_enabled: false },
      };
      const account = editing ? await liveTradingApi.updateBrokerAccount(editing.id, payload) : await liveTradingApi.createBrokerAccount(payload);
      const result = await liveTradingApi.testBrokerConnection(account.id);
      setConnectionResults((prev) => ({ ...prev, [account.id]: result.connection }));
      showToast(result.connection.message || "Crypto API connection checked", result.connection.connected ? "success" : "error");
      closeConnect();
      await load();
    } catch (error: any) {
      showToast(error.message || "Failed to save crypto API broker", "error");
    } finally {
      setSaving(false);
    }
  };

  const copyText = async (text: string, label = "Copied") => {
    try { await navigator.clipboard.writeText(text); showToast(label, "success"); } catch { showToast("Copy failed. Please copy manually.", "error"); }
  };

  const downloadMt5Agent = () => window.open(liveTradingApi.getMt5AgentDownloadUrl(), "_blank", "noopener,noreferrer");

  const generateAgentToken = async (broker: BrokerAccount) => {
    try {
      setGeneratingAgentToken(true);
      const result = await liveTradingApi.generateMt5AgentToken(broker.id, "DEMO");
      setGeneratedAgentToken(result.agent_token);
      setEditing(broker);
      setForm({ ...emptyMt5Form, account_label: broker.account_label || "MT5 Demo", server_name: broker.server_name || "", login_id: broker.login_id || "" });
      setActiveForm("MT5");
      setConnectOpen(true);
      showToast("MT5 Agent token generated. Copy it now; it is shown only once.", "success");
      await load();
    } catch (error: any) {
      showToast(error.message || "Failed to generate MT5 Agent token", "error");
    } finally {
      setGeneratingAgentToken(false);
    }
  };

  const testConnection = async (broker: BrokerAccount) => {
    try {
      setTestingId(broker.id);
      const result = await liveTradingApi.testBrokerConnection(broker.id);
      setConnectionResults((prev) => ({ ...prev, [broker.id]: result.connection }));
      showToast(result.connection.message || (result.connection.connected ? "Broker connected" : "Broker connection failed"), result.connection.connected ? "success" : "error");
      await load();
    } catch (error: any) {
      showToast(error.message || "Connection test failed", "error");
    } finally {
      setTestingId(null);
    }
  };

  const syncBroker = async (broker: BrokerAccount) => {
    try {
      setSyncingId(broker.id);
      const result = await liveTradingApi.syncBrokerAccount(broker.id);
      if (result.requires_account_selection && result.accounts?.length) {
        setCtraderSelectTarget({ broker: result.broker_account || broker, accounts: result.accounts });
        showToast("Select your cTrader trading account to finish sync.", "success");
      } else {
        const synced = result.symbols_synced !== undefined ? ` Symbols synced: ${result.symbols_synced}.` : "";
        showToast(`Broker sync completed.${synced}`, "success");
      }
      await load();
    } catch (error: any) {
      showToast(error.message || "Broker sync failed", "error");
    } finally {
      setSyncingId(null);
    }
  };

  const openCtraderAccountSelector = async (broker: BrokerAccount) => {
    try {
      setSyncingId(broker.id);
      const result = await liveTradingApi.getCtraderAccounts(broker.id);
      setCtraderSelectTarget({ broker: result.broker_account || broker, accounts: result.accounts || [] });
    } catch (error: any) {
      showToast(error.message || "Failed to load cTrader accounts", "error");
    } finally {
      setSyncingId(null);
    }
  };

  const selectCtraderAccount = async (account: CTraderTradingAccount) => {
    if (!ctraderSelectTarget) return;
    const accountId = String(account.ctrader_account_id || account.account_number || "");
    if (!accountId) {
      showToast("Account selection required", "error");
      return;
    }
    try {
      setSyncingId(ctraderSelectTarget.broker.id);
      await liveTradingApi.selectCtraderAccount(ctraderSelectTarget.broker.id, accountId);
      setCtraderSelectTarget(null);
      showToast("cTrader trading account selected", "success");
      await syncBroker(ctraderSelectTarget.broker);
    } catch (error: any) {
      showToast(error.message || "Failed to select cTrader account", "error");
    } finally {
      setSyncingId(null);
    }
  };


  const openCtraderDemoOrder = (broker: BrokerAccount) => {
    const selected = (broker.metadata_json as any)?.ctrader_selected_account || null;
    if (!selected) {
      showToast("Select and sync a cTrader demo account before placing a test order.", "error");
      return;
    }
    if (!isCtraderDemoSelected(selected, broker)) {
      showToast("cTrader live order execution is disabled in this phase.", "error");
      return;
    }
    setCtraderOrderTarget(broker);
    setCtraderOrderResult(null);
    setCtraderOrderForm({ symbol: defaultCtraderOrderSymbol(broker), side: "BUY", volume: "1000", stop_loss: "", take_profit: "" });
  };

  const submitCtraderDemoOrder = async () => {
    if (!ctraderOrderTarget) return;
    try {
      setPlacingCtraderOrder(true);
      const result = await liveTradingApi.placeCtraderTestOrder(ctraderOrderTarget.id, {
        symbol: ctraderOrderForm.symbol,
        side: ctraderOrderForm.side,
        volume: ctraderOrderForm.volume,
        stop_loss: ctraderOrderForm.stop_loss || null,
        take_profit: ctraderOrderForm.take_profit || null,
        comment: "AlgoAgentX cTrader DEMO test order",
      });
      setCtraderOrderResult(result as unknown as Record<string, unknown>);
      showToast(result.message || "cTrader demo order placed", "success");
      await load();
    } catch (error: any) {
      showToast(error.message || "cTrader demo order failed", "error");
    } finally {
      setPlacingCtraderOrder(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await liveTradingApi.deleteBrokerAccount(deleteTarget.id, deleteForce);
      showToast("Broker account deleted", "success");
      setDeleteTarget(null);
      setDeleteWarning(null);
      setDeleteForce(false);
      await load();
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      if (error?.response?.status === 409) {
        setDeleteWarning(typeof detail === "string" ? detail : detail?.message || error.message || "This broker is used by active deployments.");
        setDeleteForce(true);
      } else {
        showToast(error.message || "Failed to delete broker account", "error");
      }
    }
  };

  return (
    <PageShell>
      <PageHeader title="Brokers" subtitle="Manage broker connections with safe status, test, reconnect, edit, and delete flows." />
      <GlassCard className="p-6" hoverEffect={false}>
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">Broker Accounts</h1>
            <p className="mt-2 text-purple-100">Connect Cloud, Crypto API, and MT5 Agent brokers. Secrets stay encrypted and are never returned to the frontend.</p>
          </div>
          <Button onClick={openSelector} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><Plus className="h-4 w-4" /> Connect Broker</Button>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-200">Total Accounts</p><p className="mt-2 text-2xl font-bold text-white">{brokers.length}</p></div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-200">Connected</p><p className="mt-2 text-2xl font-bold text-lime-300">{connectedCount}</p></div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-purple-200">Available Providers</p><p className="mt-2 text-2xl font-bold text-white">{providers.length}</p></div>
        </div>

        {connectOpen && (
          <div className="mt-8 rounded-2xl border border-white/10 bg-black/20 p-5 shadow-2xl">
            <div className="mb-5 flex items-center justify-between gap-4">
              <div><h2 className="text-xl font-bold text-white">{activeForm ? (editing ? "Reconnect / Edit Broker" : "Connect Broker") : "Connect Broker"}</h2><p className="text-sm text-purple-200">Choose a provider and complete the correct setup flow.</p></div>
              <Button type="button" variant="ghost" className="text-purple-100 hover:bg-white/10" onClick={closeConnect}><X className="mr-2 h-4 w-4" /> Close</Button>
            </div>

            {!activeForm && (
              <div className="space-y-6">
                {Object.entries(groupedProviders).map(([title, rows]) => rows.length ? (
                  <div key={title}>
                    <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-purple-200">{title}</h3>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                      {rows.map((provider) => {
                        const code = provider.code.toUpperCase();
                        const isReady = provider.is_enabled && (code === "MT5" || code === "UPSTOX" || CRYPTO_CODES.has(code) || CTRADER_CODES.has(code));
                        return (
                          <button key={provider.id} type="button" disabled={!isReady} onClick={() => code === "MT5" ? openMt5Form() : code === "UPSTOX" ? void openUpstoxForm() : CTRADER_CODES.has(code) ? void openCtraderForm() : CRYPTO_CODES.has(code) ? openCryptoForm(code) : undefined} className={`rounded-2xl border p-4 text-left transition ${isReady ? "border-white/10 bg-white/5 hover:bg-white/10" : "border-white/5 bg-white/[0.03] opacity-60"}`}>
                            <div className="flex items-start justify-between gap-3"><div><div className="font-bold text-white">{provider.display_name || provider.name || displayBrokerName(code)}</div><div className="mt-1 text-xs text-purple-200">{categoryTitle(provider)} • {provider.setup_mode || provider.auth_type}</div></div>{isReady ? <Badge className="bg-lime-500/20 text-lime-100">Ready</Badge> : <Badge className="bg-white/10 text-purple-100">Coming Soon</Badge>}</div>
                            <p className="mt-3 text-sm text-purple-200">{provider.description || (code === "MT5" ? "Use the Windows MT5 Agent where your terminal is running." : CRYPTO_CODES.has(code) ? "Connect with exchange API key and secret. Live orders stay disabled in this phase." : "Cloud broker OAuth/API setup.")}</p>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : null)}
              </div>
            )}

            {activeForm === "MT5" && (
              <form onSubmit={submitMt5} className="space-y-4">
                <div className="rounded-xl border border-blue-400/20 bg-blue-500/10 p-4 text-sm text-blue-100">
                  <div className="font-semibold text-white">Install AlgoAgentX MT5 Agent on your Windows PC or VPS where MetaTrader 5 is running.</div>
                  <ol className="mt-3 list-decimal space-y-1 pl-5"><li>Install MetaTrader 5 on Windows/VPS.</li><li>Login to your broker account.</li><li>Enable Algo Trading.</li><li>Download AlgoAgentX MT5 Agent.</li><li>Paste the Agent Token into config.json.</li><li>Run the Agent.</li></ol>
                </div>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <label className="text-sm text-purple-100">Account Label<input value={form.account_label} onChange={(e) => setForm({ ...form, account_label: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
                  <label className="text-sm text-purple-100">Provider<input value="MT5 Agent / MetaTrader 5" readOnly className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
                  <label className="text-sm text-purple-100">Trading Mode<input value="DEMO" readOnly className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
                </div>
                {editing && agentStatuses[editing.id] && <AgentStatusPanel agent={agentStatuses[editing.id]} />}
                {generatedAgentToken && <TokenPanel token={generatedAgentToken} onCopy={() => copyText(generatedAgentToken, "Agent token copied")} />}
                <div className="flex flex-wrap gap-2"><Button type="submit" disabled={saving || generatingAgentToken} className="bg-lime-500 text-slate-950 hover:bg-lime-400">{saving ? "Saving..." : editing ? "Generate New Agent Token" : "Save & Generate Agent Token"}</Button><Button type="button" onClick={downloadMt5Agent} className="gap-2 bg-white/10 text-white hover:bg-white/15"><Download className="h-4 w-4" /> Download Agent</Button>{editing && <Button type="button" onClick={() => testConnection(editing)} className="gap-2 bg-white/10 text-white hover:bg-white/15"><RefreshCw className="h-4 w-4" /> Test Agent Connection</Button>}</div>
              </form>
            )}

            {activeForm === "UPSTOX" && (
              <form onSubmit={submitUpstox} className="space-y-4">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <label className="text-sm text-purple-100">Account Label<input value={upstoxForm.account_label} onChange={(e) => setUpstoxForm({ ...upstoxForm, account_label: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
                  <label className="text-sm text-purple-100">Client ID / API Key<input value={upstoxForm.client_id} onChange={(e) => setUpstoxForm({ ...upstoxForm, client_id: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
                  <label className="text-sm text-purple-100">Client Secret<input value={upstoxForm.client_secret} onChange={(e) => setUpstoxForm({ ...upstoxForm, client_secret: e.target.value })} type="password" className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
                  <label className="text-sm text-purple-100">Redirect URI<div className="mt-1 flex gap-2"><input value={upstoxForm.redirect_uri} readOnly className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /><Button type="button" onClick={() => copyText(upstoxForm.redirect_uri, "Redirect URI copied")} className="gap-2 bg-white/10 text-white hover:bg-white/15"><Copy className="h-4 w-4" /> Copy</Button></div></label>
                </div>
                <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/10 p-3 text-sm text-yellow-100">Use this exact Redirect URI in your broker developer app.</div>
                <Button type="submit" disabled={saving || connectingUpstox} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><ExternalLink className="h-4 w-4" />{saving || connectingUpstox ? "Opening OAuth..." : "Save & Open OAuth"}</Button>
              </form>
            )}

            {activeForm === "CTRADER" && (
              <form onSubmit={submitCtrader} className="space-y-4">
                <div className="rounded-xl border border-blue-400/20 bg-blue-500/10 p-3 text-sm text-blue-100">Use this exact Redirect URI in your cTrader Open API application. Market data setup is enabled; order execution stays disabled in this phase.</div>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <label className="text-sm text-purple-100">Account Label<input value={ctraderForm.account_label} onChange={(e) => setCtraderForm({ ...ctraderForm, account_label: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
                  <label className="text-sm text-purple-100">Client ID / API Key<input value={ctraderForm.client_id} onChange={(e) => setCtraderForm({ ...ctraderForm, client_id: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
                  <label className="text-sm text-purple-100">Client Secret<input value={ctraderForm.client_secret} onChange={(e) => setCtraderForm({ ...ctraderForm, client_secret: e.target.value })} type="password" className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
                  <label className="text-sm text-purple-100">Redirect URI<div className="mt-1 flex gap-2"><input value={ctraderForm.redirect_uri} readOnly className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /><Button type="button" onClick={() => copyText(ctraderForm.redirect_uri, "cTrader Redirect URI copied")} className="gap-2 bg-white/10 text-white hover:bg-white/15"><Copy className="h-4 w-4" /> Copy</Button></div></label>
                </div>
                <Button type="submit" disabled={saving} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><ExternalLink className="h-4 w-4" />{saving ? "Opening OAuth..." : "Save & Open cTrader OAuth"}</Button>
              </form>
            )}

            {activeForm === "CRYPTO" && (
              <form onSubmit={submitCrypto} className="space-y-4">
                <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/10 p-3 text-sm text-yellow-100">Create API key with read/trade permission only. Do not enable withdrawal permission.</div>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <label className="text-sm text-purple-100">Broker<input value={displayBrokerName(cryptoForm.code)} readOnly className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
                  <label className="text-sm text-purple-100">Account Label<input value={cryptoForm.account_label} onChange={(e) => setCryptoForm({ ...cryptoForm, account_label: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
                  <label className="text-sm text-purple-100">API Key<input value={cryptoForm.api_key} onChange={(e) => setCryptoForm({ ...cryptoForm, api_key: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
                  <label className="text-sm text-purple-100">API Secret<input value={cryptoForm.api_secret} onChange={(e) => setCryptoForm({ ...cryptoForm, api_secret: e.target.value })} type="password" className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>
                  {cryptoForm.code.toUpperCase() === "OKX" && <label className="text-sm text-purple-100">API Passphrase<input value={cryptoForm.passphrase} onChange={(e) => setCryptoForm({ ...cryptoForm, passphrase: e.target.value })} type="password" className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" required /></label>}
                </div>
                <Button type="submit" disabled={saving} className="gap-2 bg-lime-500 text-slate-950 hover:bg-lime-400"><KeyRound className="h-4 w-4" />{saving ? "Testing..." : "Save & Test Connection"}</Button>
              </form>
            )}
          </div>
        )}

        <div className="mt-8 space-y-4">
          {loading && <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-purple-100">Loading broker accounts...</div>}
          {!loading && brokers.length === 0 && <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-purple-100">No broker accounts yet. Click Connect Broker to start.</div>}
          {brokers.map((broker) => {
            const result = connectionResults[broker.id];
            const last = result || (broker.last_connection_result as any) || (broker.metadata_json as any)?.last_test;
            const code = brokerCodeOf(broker);
            const isUpstox = code === "UPSTOX";
            const isMt5 = code === "MT5";
            const isCrypto = CRYPTO_CODES.has(code);
            const isCtrader = CTRADER_CODES.has(code);
            const agent = isMt5 ? agentStatuses[broker.id] : null;
            const ctraderSelected = isCtrader ? ((broker.metadata_json as any)?.ctrader_selected_account || null) : null;
            const ctraderSyncStatus = isCtrader ? ((broker.metadata_json as any)?.sync_status || null) : null;
            const normalizedStatus = statusOf(broker, agent);
            return (
              <div key={broker.id} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
                  <div className="flex items-start gap-3">
                    {normalizedStatus === "CONNECTED" ? <CheckCircle className="h-5 w-5 text-green-300" /> : normalizedStatus === "ERROR" ? <AlertCircle className="h-5 w-5 text-yellow-300" /> : normalizedStatus === "AGENT_OFFLINE" ? <WifiOff className="h-5 w-5 text-orange-300" /> : <XCircle className="h-5 w-5 text-red-300" />}
                    <div>
                      <div className="flex flex-wrap items-center gap-2"><h3 className="text-lg font-bold text-white">{broker.account_label}</h3>{statusBadge(normalizedStatus)}<Badge className="bg-white/10 text-purple-100">{code}</Badge>{isCrypto && <Badge className="bg-white/10 text-purple-100">Crypto API</Badge>}{isCtrader && <Badge className="bg-white/10 text-purple-100">Cloud Forex</Badge>}{isUpstox && <Badge className="bg-white/10 text-purple-100">Indian Equity</Badge>}{isMt5 && agentStatusBadge(agent)}</div>
                      <p className="mt-1 text-sm text-purple-200">{isMt5 ? `${agent?.mt5_account_login || "Agent waiting"} • ${agent?.server_name || broker.server_name || "MT5 Agent"}` : isCrypto ? `${displayBrokerName(code)} API • Live orders disabled` : isCtrader ? `${displayBrokerName(code)} • ${ctraderSelected?.account_number || ctraderSelected?.ctrader_account_id || "Account sync pending"} • Orders disabled` : isUpstox ? (broker.login_id || "OAuth pending") : broker.login_id} {isMt5 || isCrypto ? "" : ` • ${broker.server_name || ""}`}</p>
                      <p className="mt-1 flex items-center gap-1 text-xs text-purple-300"><Clock className="h-3 w-3" /> Last connected: {formatDate(broker.last_connected_at)}</p>
                      {isMt5 && <p className="mt-1 text-xs text-purple-300">Terminal: {agent?.terminal_status || "Waiting for Agent"} • Server: {agent?.server_name || "—"} • Last heartbeat: {formatDate(agent?.last_heartbeat_at)} • Balance/Equity: {money(agent?.balance)} / {money(agent?.equity)} {agent?.currency || ""}</p>}
                      {isCtrader && <p className="mt-1 text-xs text-purple-300">Selected: {ctraderSelected?.account_number || ctraderSelected?.ctrader_account_id || "Not selected"} • Broker: {ctraderSelected?.broker_name || "—"} • Last sync: {formatDate((broker.metadata_json as any)?.last_sync_at || broker.last_connected_at)} • Sync: {ctraderSyncStatus || "PENDING"}</p>}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2"><Button onClick={() => testConnection(broker)} disabled={testingId === broker.id} className="gap-2 bg-white/10 text-white hover:bg-white/15"><RefreshCw className="h-4 w-4" /> Test</Button>{isCtrader && <Button onClick={() => syncBroker(broker)} disabled={syncingId === broker.id} className="gap-2 bg-white/10 text-white hover:bg-white/15"><RefreshCw className="h-4 w-4" /> Sync</Button>}{isCtrader && <Button onClick={() => openCtraderAccountSelector(broker)} disabled={syncingId === broker.id} className="gap-2 bg-white/10 text-white hover:bg-white/15">Select Account</Button>}{isCtrader && isCtraderDemoSelected(ctraderSelected, broker) && <Button onClick={() => openCtraderDemoOrder(broker)} className="gap-2 bg-lime-500/20 text-lime-100 hover:bg-lime-500/30">Test Demo Order</Button>}{isCtrader && !isCtraderDemoSelected(ctraderSelected, broker) && <Button disabled className="gap-2 bg-white/5 text-purple-200">Live Orders Disabled</Button>}<Button onClick={() => reconnect(broker)} className="gap-2 bg-white/10 text-white hover:bg-white/15"><RefreshCw className="h-4 w-4" /> Reconnect</Button><Button onClick={() => reconnect(broker)} className="gap-2 bg-white/10 text-white hover:bg-white/15"><Edit3 className="h-4 w-4" /> Edit</Button>{isMt5 && <Button onClick={() => generateAgentToken(broker)} disabled={generatingAgentToken} className="gap-2 bg-white/10 text-white hover:bg-white/15"><Copy className="h-4 w-4" /> Generate Token</Button>}<Button onClick={() => { setDeleteTarget(broker); setDeleteWarning(null); setDeleteForce(false); }} className="gap-2 bg-red-500/15 text-red-100 hover:bg-red-500/25"><Trash2 className="h-4 w-4" /> Delete</Button></div>
                </div>
                {last && <div className="mt-4 rounded-xl border border-white/10 bg-black/10 p-4 text-sm text-purple-100"><div className="font-semibold text-white">Last connection result</div><p className="mt-1">{last?.message || "No details"}</p><div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-3"><span>Balance: {isUpstox ? "—" : money(isCtrader && ctraderSelected ? ctraderSelected.balance : last?.balance)}</span><span>Equity: {isUpstox ? "—" : money(isCtrader && ctraderSelected ? ctraderSelected.equity : last?.equity)}</span><span>Currency: {(isCtrader && ctraderSelected?.currency) || last?.currency || (isUpstox ? "INR" : "—")}</span></div></div>}
              </div>
            );
          })}
        </div>
      </GlassCard>

      {ctraderSelectTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-3xl rounded-2xl border border-white/10 bg-[#241047] p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4"><div><h2 className="text-xl font-bold text-white">Select cTrader Trading Account</h2><p className="mt-2 text-sm text-purple-200">Choose which linked cTrader account AlgoAgentX should use for balance, symbols, and future trading setup.</p></div><Button variant="ghost" onClick={() => setCtraderSelectTarget(null)} className="text-purple-100 hover:bg-white/10"><X className="h-4 w-4" /></Button></div>
            <div className="mt-5 space-y-3">
              {ctraderSelectTarget.accounts.length === 0 && <div className="rounded-xl border border-yellow-400/30 bg-yellow-500/10 p-4 text-sm text-yellow-100">No cTrader account found. Reconnect cTrader and make sure account permission is approved.</div>}
              {ctraderSelectTarget.accounts.map((account, index) => (
                <button key={`${account.ctrader_account_id || account.account_number || index}`} type="button" onClick={() => selectCtraderAccount(account)} className="w-full rounded-xl border border-white/10 bg-white/5 p-4 text-left hover:bg-white/10">
                  <div className="flex flex-col justify-between gap-2 md:flex-row md:items-center"><div><div className="font-semibold text-white">{account.account_number || account.ctrader_account_id || `Account ${index + 1}`}</div><div className="text-sm text-purple-200">{account.broker_name || "cTrader"} • {account.account_type || "DEMO/LIVE"}</div></div><Badge className="bg-lime-500/20 text-lime-100">Select</Badge></div>
                  <div className="mt-3 grid grid-cols-1 gap-2 text-sm text-purple-100 md:grid-cols-4"><span>Balance: {money(account.balance)}</span><span>Equity: {money(account.equity)}</span><span>Free margin: {money(account.free_margin)}</span><span>Currency: {account.currency || "—"}</span></div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}


      {ctraderOrderTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-white/10 bg-[#241047] p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4"><div><h2 className="text-xl font-bold text-white">cTrader Test Demo Order</h2><p className="mt-2 text-sm text-purple-200">This will place a demo market order on the selected cTrader demo account. Live cTrader orders remain blocked.</p></div><Button variant="ghost" onClick={() => setCtraderOrderTarget(null)} className="text-purple-100 hover:bg-white/10"><X className="h-4 w-4" /></Button></div>
            <div className="mt-4 rounded-xl border border-yellow-400/30 bg-yellow-500/10 p-3 text-sm text-yellow-100">Confirm the symbol and volume. Use the smallest safe demo volume supported by your cTrader symbol metadata.</div>
            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="text-sm text-purple-100">Symbol<input value={ctraderOrderForm.symbol} onChange={(e) => setCtraderOrderForm({ ...ctraderOrderForm, symbol: e.target.value.toUpperCase() })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
              <label className="text-sm text-purple-100">Side<select value={ctraderOrderForm.side} onChange={(e) => setCtraderOrderForm({ ...ctraderOrderForm, side: e.target.value as "BUY" | "SELL" })} className="mt-1 w-full rounded-xl border border-white/10 bg-[#2b1553] px-3 py-2 text-white outline-none"><option value="BUY">BUY</option><option value="SELL">SELL</option></select></label>
              <label className="text-sm text-purple-100">Volume<input value={ctraderOrderForm.volume} onChange={(e) => setCtraderOrderForm({ ...ctraderOrderForm, volume: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
              <label className="text-sm text-purple-100">Stop Loss Optional<input value={ctraderOrderForm.stop_loss} onChange={(e) => setCtraderOrderForm({ ...ctraderOrderForm, stop_loss: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
              <label className="text-sm text-purple-100">Take Profit Optional<input value={ctraderOrderForm.take_profit} onChange={(e) => setCtraderOrderForm({ ...ctraderOrderForm, take_profit: e.target.value })} className="mt-1 w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" /></label>
            </div>
            {ctraderOrderResult && <div className="mt-4 rounded-xl border border-green-400/30 bg-green-500/10 p-4 text-sm text-green-100"><div className="font-semibold text-white">Order Result</div><div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2"><span>Order ID: {String(ctraderOrderResult.order_id || "—")}</span><span>Status: {String(ctraderOrderResult.status || "—")}</span><span>Symbol: {String(ctraderOrderResult.symbol || "—")}</span><span>Side / Volume: {String(ctraderOrderResult.side || "—")} {String(ctraderOrderResult.volume || "")}</span></div></div>}
            <div className="mt-6 flex flex-wrap justify-end gap-2"><Button onClick={() => setCtraderOrderTarget(null)} className="bg-white/10 text-white hover:bg-white/15">Cancel</Button><Button onClick={submitCtraderDemoOrder} disabled={placingCtraderOrder} className="bg-lime-500 text-slate-950 hover:bg-lime-400">{placingCtraderOrder ? "Placing..." : "Confirm Demo Market Order"}</Button></div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-[#241047] p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4"><div><h2 className="text-xl font-bold text-white">Delete broker account?</h2><p className="mt-2 text-sm text-purple-200">{deleteTarget.account_label} will be removed. Stored credentials will be cleared and never exposed.</p></div><Button variant="ghost" onClick={() => setDeleteTarget(null)} className="text-purple-100 hover:bg-white/10"><X className="h-4 w-4" /></Button></div>
            {deleteWarning && <div className="mt-4 rounded-xl border border-yellow-400/30 bg-yellow-500/10 p-3 text-sm text-yellow-100">{deleteWarning}<div className="mt-2 font-semibold">Click Confirm Force Delete only after stopping or moving related deployments.</div></div>}
            <div className="mt-6 flex flex-wrap justify-end gap-2"><Button onClick={() => setDeleteTarget(null)} className="bg-white/10 text-white hover:bg-white/15">Cancel</Button><Button onClick={confirmDelete} className="bg-red-500/20 text-red-100 hover:bg-red-500/30"><Trash2 className="mr-2 h-4 w-4" />{deleteForce ? "Confirm Force Delete" : "Delete"}</Button></div>
          </div>
        </div>
      )}
    </PageShell>
  );
}

function AgentStatusPanel({ agent }: { agent?: MT5AgentStatus | null }) {
  return <div className="rounded-xl border border-white/10 bg-black/10 p-4 text-sm text-purple-100"><div className="mb-2 flex flex-wrap items-center gap-2"><span className="font-semibold text-white">Agent Status</span>{agentStatusBadge(agent)}</div><div className="grid grid-cols-1 gap-2 md:grid-cols-3"><span>Last heartbeat: {formatDate(agent?.last_heartbeat_at)}</span><span>Terminal: {agent?.terminal_status || "Waiting"}</span><span>Login: {agent?.mt5_account_login || "—"}</span><span>Balance: {money(agent?.balance)}</span><span>Equity: {money(agent?.equity)}</span><span>Currency: {agent?.currency || "—"}</span></div></div>;
}

function TokenPanel({ token, onCopy }: { token: string; onCopy: () => void }) {
  return <div className="rounded-xl border border-yellow-400/30 bg-yellow-500/10 p-4 text-sm text-yellow-100"><div className="font-semibold text-white">Copy this Agent Token now. It is shown only once.</div><div className="mt-2 flex flex-col gap-2 md:flex-row md:items-center"><code className="min-w-0 flex-1 overflow-auto rounded-lg bg-black/30 px-3 py-2 text-xs text-yellow-50">{token}</code><Button type="button" onClick={onCopy} className="gap-2 bg-white/10 text-white hover:bg-white/15"><Copy className="h-4 w-4" /> Copy Agent Token</Button></div></div>;
}
