"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ChevronDown, Search, ShieldAlert, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import FieldHelpTooltip from "@/components/common/FieldHelpTooltip";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { ApprovedBrokerAccount, BrokerAccount, LiveMode, MarketInstrument, StrategyCatalogItem } from "@/types/live-trading";

const riskOptions = [
  { label: "0.25%", value: 0.0025 },
  { label: "0.5%", value: 0.005 },
  { label: "1%", value: 0.01 },
  { label: "1.5%", value: 0.015 },
  { label: "2%", value: 0.02 },
  { label: "3%", value: 0.03 },
  { label: "5%", value: 0.05 },
];

const priceRiskOptions = [
  { label: "0.2%", value: 0.002 },
  { label: "0.5%", value: 0.005 },
  { label: "1%", value: 0.01 },
  { label: "1.5%", value: 0.015 },
  { label: "2%", value: 0.02 },
  { label: "3%", value: 0.03 },
];

const defaults = {
  name: "",
  strategy_id: "",
  instrument: "XAUUSD",
  broker_symbol: "",
  instrument_key: "",
  exchange: "",
  segment: "",
  timeframe: "M15",
  mode: "DEMO" as LiveMode,
  broker_account_id: "",
  risk_per_trade: 0.01,
  rr_ratio: 2,
  price_risk_pct: 0.02,
  max_daily_loss: 5000,
  max_trades_per_day: 10,
  max_open_positions: 1,
  allow_short: true,
  auto_trade_enabled: false,
};

const isDemoReady = (s: StrategyCatalogItem) => Boolean(s.isDeployableDemo ?? s.is_deployable_demo);
const isLiveReady = (s: StrategyCatalogItem) => Boolean(s.isLiveApproved ?? s.is_live_approved);

const normalizeMode = (value?: string | null): LiveMode | "" => {
  const upper = String(value || "").toUpperCase();
  if (upper === "REAL") return "LIVE";
  if (upper === "LIVE" || upper === "DEMO" || upper === "PAPER") return upper as LiveMode;
  return "";
};

const approvedMode = (broker: ApprovedBrokerAccount): LiveMode | "" => {
  const direct = normalizeMode((broker as any).approval_mode || broker.mode || broker.broker_mode);
  if (direct) return direct;
  const selected = (broker as any).selected_account || (broker as any).metadata_json?.selected_account || (broker as any).metadata_json?.mt5_selected_account || {};
  return normalizeMode(selected.mode || selected.account_type || selected.trading_mode);
};

const instrumentLabel = (instrument: MarketInstrument) => {
  const symbol = instrument.symbol || "—";
  const name = instrument.name || instrument.instrument_type || "Instrument";
  const market = instrument.asset_class || instrument.market || (instrument as any).segment || instrument.instrument_type || "Market";
  const exchange = instrument.exchange || "—";
  return `${symbol} · ${name} · ${market} · ${exchange}`;
};

const instrumentKeyValue = (instrument?: MarketInstrument | null) => {
  if (!instrument) return "";
  return String((instrument as any).instrument_key || instrument.broker_symbol || instrument.symbol || "");
};

type LiveAccessStatus = { allowed: boolean; requires_subscription: boolean; message?: string; recommended_coupon?: string | null };

const extractGateDetail = (error: any): LiveAccessStatus | null => {
  const detail = error?.response?.data?.detail;
  if (detail && typeof detail === "object" && detail.code === "SUBSCRIPTION_REQUIRED") {
    return { allowed: false, requires_subscription: true, message: detail.message, recommended_coupon: detail.recommended_coupon || null };
  }
  return null;
};

const errorMessage = (error: any, fallback: string) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  return error?.message || fallback;
};

function Field({ label, help, children }: { label: string; help: string; children: ReactNode }) {
  return (
    <label className="space-y-2 text-sm text-purple-100">
      <span className="flex items-center gap-2">{label}<FieldHelpTooltip label={label} content={help} /></span>
      {children}
    </label>
  );
}

const inputClass = "w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none";
const selectClass = "w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-white outline-none";

export default function NewLiveDeploymentPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [strategies, setStrategies] = useState<StrategyCatalogItem[]>([]);
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [approvedBrokers, setApprovedBrokers] = useState<ApprovedBrokerAccount[]>([]);
  const [marketInstruments, setMarketInstruments] = useState<MarketInstrument[]>([]);
  const [instrumentSearch, setInstrumentSearch] = useState("");
  const [instrumentOpen, setInstrumentOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [accessStatus, setAccessStatus] = useState<LiveAccessStatus | null>(null);
  const [form, setForm] = useState(defaults);

  const approvedConnectedBrokers = useMemo(() => approvedBrokers.filter((b) => {
    const brokerStatus = String(b.broker_status || "").toUpperCase();
    return brokerStatus ? brokerStatus === "CONNECTED" : String(b.status || "").toUpperCase() === "APPROVED";
  }), [approvedBrokers]);
  const connectedDemoBrokers = useMemo(() => approvedConnectedBrokers.filter((b) => approvedMode(b) === "DEMO"), [approvedConnectedBrokers]);
  const connectedLiveBrokers = useMemo(() => approvedConnectedBrokers.filter((b) => approvedMode(b) === "LIVE"), [approvedConnectedBrokers]);
  const brokerOptions = form.mode === "LIVE" ? connectedLiveBrokers : connectedDemoBrokers;
  const selectedApproval = useMemo(() => approvedBrokers.find((b) => b.broker_account_id === form.broker_account_id), [approvedBrokers, form.broker_account_id]);
  const selectedBroker = useMemo(() => brokers.find((b) => b.id === form.broker_account_id), [brokers, form.broker_account_id]);
  const selectedProvider = ((selectedApproval?.broker_code || selectedApproval?.broker_name || selectedBroker?.broker_code || selectedBroker?.broker_name || "") as string).toUpperCase();
  const isUpstox = selectedProvider === "UPSTOX";
  const isCtrader = selectedProvider === "CTRADER" || selectedProvider === "CTRADER_API";
  const selectedCtraderAccount = (selectedBroker?.metadata_json as any)?.ctrader_selected_account || (selectedApproval as any)?.selected_account || null;
  const activeInstruments = useMemo(() => {
    const active = marketInstruments.filter((item) => item.is_active !== false);
    return active.length ? active : marketInstruments;
  }, [marketInstruments]);
  const filteredInstruments = useMemo(() => {
    const q = instrumentSearch.trim().toUpperCase();
    const rows = q
      ? activeInstruments.filter((item) => [item.symbol, item.name, item.asset_class, item.market, item.exchange, item.broker_symbol, (item as any).instrument_key].some((value) => String(value || "").toUpperCase().includes(q)))
      : activeInstruments;
    return rows.slice(0, 30);
  }, [activeInstruments, instrumentSearch]);
  const selectedInstrument = useMemo(() => activeInstruments.find((item) => String(item.symbol).toUpperCase() === form.instrument.toUpperCase()), [activeInstruments, form.instrument]);
  const selectedInstrumentDisplay = selectedInstrument ? instrumentLabel(selectedInstrument) : form.instrument;
  const selectedMarket = String(selectedInstrument?.market || selectedInstrument?.asset_class || (selectedInstrument as any)?.segment || "").toUpperCase();
  const selectedExchange = String(selectedInstrument?.exchange || form.exchange || "").toUpperCase();
  const isIndianInstrument = selectedMarket.includes("INDIAN") || ["NSE", "NSE_EQ", "NSE_FO", "BSE"].some((value) => selectedExchange.includes(value));
  const resolvedBrokerSymbol = form.broker_symbol || instrumentKeyValue(selectedInstrument) || form.instrument;
  const showInstrumentKeyField = Boolean(
    isUpstox ||
    isIndianInstrument ||
    String((selectedBroker as any)?.requires_instrument_key || "").toLowerCase() === "true" ||
    (selectedInstrument && instrumentKeyValue(selectedInstrument) && instrumentKeyValue(selectedInstrument).toUpperCase() !== String(selectedInstrument.symbol || "").toUpperCase() && isUpstox)
  );
  const showExchangeField = isUpstox || isIndianInstrument;
  const deployableStrategies = useMemo(
    () => strategies.filter((strategy) => form.mode === "LIVE" ? isLiveReady(strategy) : isDemoReady(strategy)),
    [strategies, form.mode],
  );

  useEffect(() => {
    const loadApprovedBrokers = async () => {
      const apiAny = liveTradingApi as any;
      if (typeof apiAny.listApprovedBrokers === "function") {
        return apiAny.listApprovedBrokers();
      }
      if (typeof apiAny.listApprovedBrokerAccounts === "function") {
        return apiAny.listApprovedBrokerAccounts();
      }
      console.warn("Approved broker API helper missing");
      return [];
    };

    const load = async () => {
      try {
        setLoading(true);
        const [strategyRows, brokerRows, access, approvedBrokerRows, instrumentRows] = await Promise.all([
          liveTradingApi.listStrategies(),
          liveTradingApi.listBrokerAccounts(),
          liveTradingApi.getLiveAccessStatus().catch(() => null),
          loadApprovedBrokers().catch(() => []),
          liveTradingApi.listMarketInstruments().catch(() => []),
        ]);
        if (access) setAccessStatus(access);
        setStrategies(strategyRows);
        setBrokers(brokerRows);
        setApprovedBrokers(approvedBrokerRows);
        setMarketInstruments(instrumentRows);
      } catch (error: any) {
        showToast(errorMessage(error, "Failed to load form data"), "error");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [showToast]);

  useEffect(() => {
    if (form.mode === "DEMO" && connectedDemoBrokers.length === 0 && connectedLiveBrokers.length > 0) {
      setForm((prev) => ({ ...prev, mode: "LIVE", broker_account_id: connectedLiveBrokers[0]?.broker_account_id || "" }));
      return;
    }
    const options = form.mode === "LIVE" ? connectedLiveBrokers : connectedDemoBrokers;
    if (!form.broker_account_id && options.length > 0) {
      setForm((prev) => ({ ...prev, broker_account_id: options[0].broker_account_id }));
    }
    if (form.broker_account_id && !options.some((broker) => broker.broker_account_id === form.broker_account_id)) {
      setForm((prev) => ({ ...prev, broker_account_id: options[0]?.broker_account_id || "" }));
    }
  }, [connectedDemoBrokers, connectedLiveBrokers, form.mode, form.broker_account_id]);

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

  useEffect(() => {
    if (!activeInstruments.length) return;
    const preferred = activeInstruments.find((item) => String(item.symbol).toUpperCase() === "XAUUSD") || activeInstruments[0];
    if (activeInstruments.some((item) => String(item.symbol).toUpperCase() === form.instrument.toUpperCase())) return;
    selectInstrument(preferred.symbol);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeInstruments, form.instrument]);

  const selectInstrument = (symbol: string) => {
    const instrument = activeInstruments.find((item) => String(item.symbol).toUpperCase() === symbol.toUpperCase());
    if (!instrument) {
      setForm((prev) => ({ ...prev, instrument: symbol.toUpperCase() }));
      setInstrumentSearch(symbol.toUpperCase());
      setInstrumentOpen(false);
      return;
    }
    const key = instrumentKeyValue(instrument);
    setForm((prev) => ({
      ...prev,
      instrument: instrument.symbol,
      exchange: instrument.exchange || "",
      segment: instrument.market || instrument.asset_class || "",
      broker_symbol: key || instrument.symbol || "",
      instrument_key: key || instrument.symbol || "",
    }));
    setInstrumentSearch(instrumentLabel(instrument));
    setInstrumentOpen(false);
  };

  useEffect(() => {
    if (selectedInstrument && !instrumentOpen) {
      setInstrumentSearch(instrumentLabel(selectedInstrument));
    }
  }, [selectedInstrument, instrumentOpen]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (accessStatus?.allowed === false) {
      showToast("Active subscription required to deploy live strategies", "error");
      return;
    }
    if (!form.strategy_id) {
      showToast("No deployable strategy found for selected mode", "error");
      return;
    }
    if (!form.broker_account_id) {
      showToast("Select approved broker account.", "error");
      return;
    }
    if (!selectedInstrument && !form.instrument) {
      showToast("Select instrument from Market Master.", "error");
      return;
    }
    if (form.mode === "LIVE" && connectedLiveBrokers.length === 0) {
      showToast("Request LIVE broker approval first.", "error");
      return;
    }
    if (form.mode === "DEMO" && connectedDemoBrokers.length === 0) {
      showToast("Request DEMO broker approval first.", "error");
      return;
    }
    if (showInstrumentKeyField && !(form.instrument_key || form.broker_symbol)) {
      showToast("Instrument key is required for this broker/instrument.", "error");
      return;
    }
    const selectedInstrumentKey = form.instrument_key || instrumentKeyValue(selectedInstrument);
    if (isUpstox && (!selectedInstrumentKey || !selectedInstrumentKey.includes("|"))) {
      showToast("Selected instrument does not have Upstox instrument_key. Update Market Master first.", "error");
      return;
    }
    if (isCtrader) {
      if (!selectedCtraderAccount) {
        showToast("Please sync/select a cTrader trading account before creating deployment", "error");
        return;
      }
      const accountMode = String(selectedCtraderAccount.account_type || selectedBroker?.mode || "").toUpperCase();
      const normalizedAccountMode = accountMode === "REAL" ? "LIVE" : accountMode;
      if (normalizedAccountMode && normalizedAccountMode !== form.mode) {
        showToast(`Selected cTrader account is not ${form.mode}.`, "error");
        return;
      }
    }
    try {
      setSaving(true);
      const resolvedInstrument = selectedInstrument?.symbol || form.instrument;
      const resolvedKey = form.instrument_key || instrumentKeyValue(selectedInstrument) || resolvedInstrument;
      const created = await liveTradingApi.createDeployment({
        ...form,
        broker_account_id: form.broker_account_id,
        instrument: resolvedInstrument,
        broker_symbol: form.broker_symbol || resolvedKey || resolvedInstrument,
        instrument_key: resolvedKey || null,
        exchange: form.exchange || selectedInstrument?.exchange || null,
        segment: form.segment || selectedInstrument?.market || selectedInstrument?.asset_class || null,
      });
      showToast("Deployment created", "success");
      router.push(`/live-trading/${created.id}`);
    } catch (error: any) {
      const gate = extractGateDetail(error);
      if (gate) {
        setAccessStatus(gate);
        showToast(gate.message || "Active subscription required to deploy live strategies", "error");
      } else {
        showToast(errorMessage(error, "Failed to create deployment"), "error");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageShell>
      <PageHeader
        title="Create Live Deployment"
        subtitle="Create DEMO or LIVE broker deployments. Both require a connected broker account approved by admin."
        actions={<Link href="/live-trading"><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link>}
      />

      {accessStatus?.allowed === false && (
        <GlassCard className="mb-6 rounded-3xl border border-amber-300/25 bg-amber-400/10 p-5" hoverEffect={false}>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-3">
              <ShieldAlert className="mt-1 h-5 w-5 text-amber-200" />
              <div>
                <h3 className="font-semibold text-white">Subscription required</h3>
                <p className="mt-1 text-sm text-purple-100/75">
                  Live trading deployment is available for active subscribers.
                  {accessStatus.recommended_coupon ? ` Use coupon ${accessStatus.recommended_coupon} for discount.` : ""}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              {accessStatus.recommended_coupon && <Button onClick={() => router.push(`/billing/checkout?type=subscription&plan=PRO&period=MONTHLY&coupon=${encodeURIComponent(accessStatus.recommended_coupon || "")}`)} className="bg-gradient-to-r from-lime-400 to-emerald-500 text-slate-950">Apply Coupon</Button>}
              <Button onClick={() => router.push("/pricing")} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">View Plans</Button>
            </div>
          </div>
        </GlassCard>
      )}

      <GlassCard className="p-6" hoverEffect={false}>
        {loading ? (
          <p className="text-purple-100">Loading deployable strategies and approved broker accounts...</p>
        ) : (
          <form onSubmit={submit} className="space-y-6">
            <div className="rounded-xl border border-lime-400/20 bg-lime-400/10 p-4 text-sm text-lime-100">
              <div className="flex gap-2"><ShieldCheck className="mt-0.5 h-4 w-4" /><span>DEMO and LIVE deployments require a connected broker account approved by admin.</span></div>
            </div>

            {!deployableStrategies.length && (
              <div className="rounded-xl border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100">
                No deployable strategy found for {form.mode}. Run verification/sandbox and ask admin to enable deployment.
              </div>
            )}

            {connectedDemoBrokers.length === 0 && connectedLiveBrokers.length === 0 && (
              <div className="flex flex-col gap-3 rounded-xl border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="font-semibold text-white">No approved broker account found.</div>
                  <div>Request broker approval before creating DEMO or LIVE deployments.</div>
                </div>
                <Link href="/live-approval" className="rounded-lg bg-lime-500 px-4 py-2 font-semibold text-slate-950 hover:bg-lime-400">Request Broker Approval</Link>
              </div>
            )}

            {form.mode === "LIVE" && connectedLiveBrokers.length === 0 && (
              <div className="flex flex-col gap-3 rounded-xl border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="font-semibold text-white">No approved broker found for this mode.</div>
                  <div>Request LIVE broker approval first.</div>
                </div>
                <Link href="/live-approval" className="rounded-lg bg-lime-500 px-4 py-2 font-semibold text-slate-950 hover:bg-lime-400">Request Broker Approval</Link>
              </div>
            )}

            {form.mode === "DEMO" && connectedDemoBrokers.length === 0 && connectedLiveBrokers.length > 0 && (
              <div className="flex flex-col gap-3 rounded-xl border border-cyan-400/25 bg-cyan-400/10 p-4 text-sm text-cyan-100 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="font-semibold text-white">No approved DEMO broker found.</div>
                  <div>Request DEMO broker approval first, or switch to LIVE if your live broker is approved.</div>
                </div>
                <Link href="/live-approval" className="rounded-lg bg-lime-500 px-4 py-2 font-semibold text-slate-950 hover:bg-lime-400">Request Broker Approval</Link>
              </div>
            )}

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
              <Field label="Deployment name" help="A friendly name to identify this broker deployment in your workspace."><input required className={inputClass} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
              <Field label="Deployable strategy" help="Only strategies approved for the selected mode are shown here."><select required className={selectClass} value={form.strategy_id} onChange={(e) => setForm({ ...form, strategy_id: e.target.value })}>{deployableStrategies.length === 0 && <option value="">No deployable strategy found</option>}{deployableStrategies.map((strategy) => <option key={strategy.id} value={strategy.id}>{strategy.name} • {form.mode === "LIVE" ? "Live Approved" : "Demo Ready"}</option>)}</select></Field>

              <Field label="Instrument" help="Search and select one active instrument from Market Master. The selected symbol is sent to the deployment engine.">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-purple-200/70" />
                  <input
                    className={`${inputClass} pl-9 pr-9`}
                    value={instrumentOpen ? instrumentSearch : selectedInstrumentDisplay}
                    onFocus={() => { setInstrumentOpen(true); setInstrumentSearch(""); }}
                    onChange={(e) => { setInstrumentOpen(true); setInstrumentSearch(e.target.value); }}
                    placeholder="Search symbol, name, market, exchange..."
                  />
                  <ChevronDown className="pointer-events-none absolute right-3 top-2.5 h-4 w-4 text-purple-200/70" />
                  {instrumentOpen && (
                    <div className="absolute z-30 mt-2 max-h-72 w-full overflow-y-auto rounded-xl border border-white/10 bg-slate-950/95 p-1 shadow-2xl backdrop-blur-xl">
                      {!activeInstruments.length && <div className="px-3 py-2 text-xs text-amber-200">No instruments found in Market Master. Ask admin to add instruments.</div>}
                      {activeInstruments.length > 0 && filteredInstruments.length === 0 && <div className="px-3 py-2 text-xs text-amber-200">No matching instruments found.</div>}
                      {filteredInstruments.map((instrument) => (
                        <button
                          key={String(instrument.id || instrument.symbol)}
                          type="button"
                          onMouseDown={(e) => e.preventDefault()}
                          onClick={() => selectInstrument(instrument.symbol)}
                          className="block w-full rounded-lg px-3 py-2 text-left text-sm text-purple-50 hover:bg-white/10"
                        >
                          {instrumentLabel(instrument)}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </Field>

              <Field label="Timeframe" help="The candle timeframe used by the live strategy runner."><select className={selectClass} value={form.timeframe} onChange={(e) => setForm({ ...form, timeframe: e.target.value })}>{["M5", "M15", "M30", "H1", "H4", "D1"].map((tf) => <option key={tf} value={tf}>{tf}</option>)}</select></Field>

              {showInstrumentKeyField ? (
                <Field label={isUpstox ? "Upstox instrument key" : "Broker symbol / instrument key"} help={isUpstox ? "Required for Upstox Indian instruments." : "Broker-specific symbol or instrument key required for this broker/instrument."}>
                  <input className={inputClass} placeholder={isUpstox ? "NSE_EQ|INE002A01018" : "Broker symbol / instrument key"} value={form.instrument_key} onChange={(e) => setForm({ ...form, instrument_key: e.target.value.trim(), broker_symbol: e.target.value.trim() })} />
                  <p className="text-xs text-purple-300">{isUpstox ? "Required for Upstox Indian instruments." : "Used only for broker-specific symbol mapping."}</p>
                </Field>
              ) : selectedInstrument && resolvedBrokerSymbol && resolvedBrokerSymbol.toUpperCase() !== String(selectedInstrument.symbol || "").toUpperCase() ? (
                <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100">
                  <div className="text-xs uppercase tracking-wide text-purple-300">Mapping</div>
                  <div className="mt-1 font-medium text-white">Broker symbol: {resolvedBrokerSymbol}</div>
                </div>
              ) : null}

              {showExchangeField && (
                <Field label="Exchange / Segment" help="Exchange or segment mapping used by Indian brokers, for example NSE_EQ or NSE_FO.">
                  <input className={inputClass} placeholder="NSE_EQ / NSE_FO" value={form.exchange} onChange={(e) => setForm({ ...form, exchange: e.target.value.toUpperCase() })} />
                  {form.segment && <p className="text-xs text-purple-300">Segment: {form.segment}</p>}
                </Field>
              )}

              <Field label="Mode" help="DEMO and LIVE send approved signals to a connected, admin-approved broker account."><select className={selectClass} value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value as LiveMode, broker_account_id: "" })}><option value="DEMO" disabled={connectedDemoBrokers.length === 0}>DEMO / Broker</option><option value="LIVE" disabled={connectedLiveBrokers.length === 0}>LIVE / Broker</option></select></Field>
              <Field label="Broker account" help="Required for DEMO and LIVE broker execution. Risk is calculated from broker account balance/equity where available."><select required className={selectClass} value={form.broker_account_id} onChange={(e) => setForm({ ...form, broker_account_id: e.target.value })}><option value="">Select approved {form.mode} broker</option>{brokerOptions.map((broker) => {
                const code = String(broker.broker_code || broker.broker_name || "BROKER").toUpperCase();
                const mode = approvedMode(broker) || broker.mode || form.mode;
                const login = broker.login_id || (broker as any).selected_account?.login || (broker as any).selected_account?.account_number || "";
                const server = broker.server_name || (broker as any).selected_account?.server || (broker as any).selected_account?.server_name || "";
                const suffix = [login, server].filter(Boolean).join("/");
                const label = `${code} • ${broker.account_label || broker.broker_name || "Broker"} • Approval Mode ${mode} • ${broker.broker_status || "CONNECTED"}${suffix ? ` • ${suffix}` : ""}`;
                return <option key={broker.broker_account_id} value={broker.broker_account_id}>{label}</option>;
              })}</select><p className="text-xs text-purple-300">Risk is calculated from broker account balance/equity where available.</p></Field>

              <Field label="Risk per trade" help="Percent of broker balance/equity risked on one trade. Example: 1% means 0.01 internally."><select className={selectClass} value={form.risk_per_trade} onChange={(e) => setForm({ ...form, risk_per_trade: Number(e.target.value) })}>{riskOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><p className="text-xs text-purple-300">Displayed as percent. Stored internally as decimal fraction.</p></Field>
              <Field label="RR ratio" help="Reward-to-risk target used when the strategy or runtime engine calculates target price."><input type="number" step="0.1" className={inputClass} value={form.rr_ratio} onChange={(e) => setForm({ ...form, rr_ratio: Number(e.target.value) })} /></Field>
              <Field label="Price risk %" help="Fallback fixed stop-loss distance when strategy does not provide SL. Example: 2% means 0.02 internally."><select className={selectClass} value={form.price_risk_pct} onChange={(e) => setForm({ ...form, price_risk_pct: Number(e.target.value) })}>{priceRiskOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><p className="text-xs text-purple-300">Displayed as percent. Stored internally as decimal fraction.</p></Field>
              <Field label="Max daily loss" help="Maximum daily loss guard for this deployment. The runner should stop trading when this limit is reached."><input type="number" className={inputClass} value={form.max_daily_loss} onChange={(e) => setForm({ ...form, max_daily_loss: Number(e.target.value) })} /></Field>
              <Field label="Max trades per day" help="Maximum number of orders the runner is allowed to place in one day."><input type="number" className={inputClass} value={form.max_trades_per_day} onChange={(e) => setForm({ ...form, max_trades_per_day: Number(e.target.value) })} /></Field>
              <Field label="Max open positions" help="Maximum open positions allowed at the same time for this deployment."><input type="number" className={inputClass} value={form.max_open_positions} onChange={(e) => setForm({ ...form, max_open_positions: Number(e.target.value) })} /></Field>
            </div>
            {isUpstox && <div className="rounded-xl border border-cyan-400/25 bg-cyan-400/10 p-4 text-sm text-cyan-100">Upstox deployment requires the Upstox instrument key. Example Reliance: NSE_EQ|INE002A01018.</div>}
            {isCtrader && <div className="rounded-xl border border-fuchsia-400/25 bg-fuchsia-400/10 p-4 text-sm text-fuchsia-100">cTrader broker deployment routing is approval-gated. DEMO requires demo approval; LIVE also requires platform cTrader LIVE configuration.</div>}

            <div className="flex flex-wrap gap-4 rounded-xl border border-white/10 bg-white/5 p-4">
              <label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.allow_short} onChange={(e) => setForm({ ...form, allow_short: e.target.checked })} />Allow short<FieldHelpTooltip label="Allow short" content="Allow the strategy to open short/sell positions when sell signals are approved." /></label>
              <label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.auto_trade_enabled} onChange={(e) => setForm({ ...form, auto_trade_enabled: e.target.checked })} />Auto trade enabled<FieldHelpTooltip label="Auto trade enabled" content="When enabled, approved signals can be sent to the execution engine. Keep disabled until QA is complete." /></label>
            </div>

            <Button disabled={saving || !form.strategy_id || !form.broker_account_id || accessStatus?.allowed === false} className="border-0 bg-gradient-to-r from-lime-400 to-emerald-500 text-slate-950 hover:from-lime-300 hover:to-emerald-400">{accessStatus?.allowed === false ? "Subscription Required" : saving ? "Creating..." : "Create Deployment"}</Button>
          </form>
        )}
      </GlassCard>
    </PageShell>
  );
}
