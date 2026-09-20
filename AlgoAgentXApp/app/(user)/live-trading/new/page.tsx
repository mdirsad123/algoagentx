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
import { fundedBacktestsApi, type FundedAccountProfile } from "@/lib/api/funded-backtests";
import type { AccountPolicyType, BrokerAccount, BrokerSymbol, FundedAttachMode, FundedLiveRiskMode, LiveMode, MarketInstrument, StrategyCatalogItem } from "@/types/live-trading";

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
  account_policy_type: "STANDARD" as AccountPolicyType,
  funded_profile_id: "",
  funded_phase_number: null as number | null,
  funded_risk_mode: "DYNAMIC" as FundedLiveRiskMode,
  funded_fixed_risk_pct: 0.01,
  funded_safety_buffer_pct: 0.05,
  funded_configured_max_risk_pct: 0.02,
  funded_attach_mode: "NEW_OR_RESET_ACCOUNT" as FundedAttachMode,
  funded_initialization_json: {} as Record<string, number | string>,
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

const brokerMode = (broker: BrokerAccount): LiveMode | "" => {
  const direct = normalizeMode(broker.mode || (broker as any).broker_mode);
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

type LiveAccessStatus = {
  allowed: boolean;
  requires_subscription: boolean;
  message?: string;
  recommended_coupon?: string | null;
  subscription?: Record<string, unknown> | null;
  funded_live?: {
    allowed: boolean;
    requires_subscription: boolean;
    code?: string | null;
    message?: string;
    subscription?: Record<string, unknown> | null;
  };
};

const extractGateDetail = (error: any): LiveAccessStatus | null => {
  const detail = error?.response?.data?.detail;
  if (detail && typeof detail === "object" && ["SUBSCRIPTION_REQUIRED", "FUNDED_LIVE_SUBSCRIPTION_REQUIRED"].includes(String(detail.code || ""))) {
    const fundedOnly = String(detail.code || "") === "FUNDED_LIVE_SUBSCRIPTION_REQUIRED";
    return {
      allowed: fundedOnly ? true : false,
      requires_subscription: !fundedOnly,
      message: detail.message,
      recommended_coupon: detail.recommended_coupon || null,
      funded_live: fundedOnly ? { allowed: false, requires_subscription: true, code: detail.code, message: detail.message } : undefined,
    };
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

function BadgePill({ children }: { children: ReactNode }) {
  return <span className="rounded-full border border-white/15 bg-white/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">{children}</span>;
}

export default function NewLiveDeploymentPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [strategies, setStrategies] = useState<StrategyCatalogItem[]>([]);
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [marketInstruments, setMarketInstruments] = useState<MarketInstrument[]>([]);
  const [brokerSymbols, setBrokerSymbols] = useState<BrokerSymbol[]>([]);
  const [brokerSymbolsLoading, setBrokerSymbolsLoading] = useState(false);
  const [brokerSymbolsError, setBrokerSymbolsError] = useState<string | null>(null);
  const [fundedProfiles, setFundedProfiles] = useState<FundedAccountProfile[]>([]);
  const [instrumentSearch, setInstrumentSearch] = useState("");
  const [instrumentOpen, setInstrumentOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [accessStatus, setAccessStatus] = useState<LiveAccessStatus | null>(null);
  const [form, setForm] = useState(defaults);

  const connectedBrokerAccounts = useMemo(() => brokers.filter((b) => String(b.status || "").toUpperCase() === "CONNECTED"), [brokers]);
  const connectedDemoBrokers = useMemo(() => connectedBrokerAccounts.filter((b) => brokerMode(b) === "DEMO"), [connectedBrokerAccounts]);
  const connectedLiveBrokers = useMemo(() => connectedBrokerAccounts.filter((b) => brokerMode(b) === "LIVE"), [connectedBrokerAccounts]);
  const brokerOptions = form.mode === "LIVE" ? connectedLiveBrokers : connectedDemoBrokers;
  const selectedBroker = useMemo(() => brokers.find((b) => b.id === form.broker_account_id), [brokers, form.broker_account_id]);
  const selectedFundedProfile = useMemo(() => fundedProfiles.find((p) => p.id === form.funded_profile_id) || null, [fundedProfiles, form.funded_profile_id]);
  const selectedFundedPhase = useMemo(() => selectedFundedProfile?.phases?.find((p) => p.phase_number === form.funded_phase_number) || null, [selectedFundedProfile, form.funded_phase_number]);
  const selectedFundedMaxDrawdownMode = useMemo(() => {
    if (!selectedFundedProfile) return "";
    if (String(selectedFundedProfile.challenge_type || "").toUpperCase() !== "INSTANT") return String(selectedFundedPhase?.max_drawdown_mode || "").toUpperCase();
    const rules: any = selectedFundedProfile.rules_json || {};
    const payout: any = selectedFundedProfile.payout_config || {};
    return String(payout.max_drawdown_mode || rules.max_drawdown_mode || "").toUpperCase();
  }, [selectedFundedProfile, selectedFundedPhase]);
  const brokerFinancials = useMemo(() => {
    const meta: any = selectedBroker?.metadata_json || {};
    const info: any = meta.last_test || meta.account_info || meta.selected_account || meta.mt5_selected_account || {};
    return { balance: info.balance ?? null, equity: info.equity ?? null, currency: info.currency ?? null, synced_at: info.synced_at ?? selectedBroker?.last_connected_at ?? null };
  }, [selectedBroker]);
  const brokerMetricsFresh = useMemo(() => {
    if (!brokerFinancials.synced_at) return false;
    const syncedAt = new Date(String(brokerFinancials.synced_at)).getTime();
    return Number.isFinite(syncedAt) && Date.now() - syncedAt >= 0 && Date.now() - syncedAt <= 120_000;
  }, [brokerFinancials.synced_at]);
  const fundedCompatibilityReady = useMemo(() => {
    if (form.account_policy_type !== "FUNDED") return true;
    if (!selectedFundedProfile) return false;
    const profileCurrency = String(selectedFundedProfile.account_currency || "").toUpperCase();
    const brokerCurrency = String(brokerFinancials.currency || "").toUpperCase();
    return Boolean(
      selectedBroker &&
      String(selectedBroker.status || "").toUpperCase() === "CONNECTED" &&
      Number(brokerFinancials.balance || 0) > 0 &&
      Number(brokerFinancials.equity || 0) > 0 &&
      brokerCurrency &&
      brokerCurrency === profileCurrency &&
      brokerMetricsFresh
    );
  }, [form.account_policy_type, selectedFundedProfile, selectedBroker, brokerFinancials.balance, brokerFinancials.equity, brokerFinancials.currency, brokerMetricsFresh]);
  const fundedSubscriptionAllowed = accessStatus?.funded_live?.allowed ?? accessStatus?.allowed ?? true;
  const selectedPolicyAccessBlocked = form.account_policy_type === "FUNDED"
    ? fundedSubscriptionAllowed === false
    : accessStatus?.allowed === false;
  const selectedProvider = ((selectedBroker?.broker_code || selectedBroker?.broker_name || "") as string).toUpperCase();
  const isUpstox = selectedProvider === "UPSTOX";
  const isCtrader = selectedProvider === "CTRADER" || selectedProvider === "CTRADER_API";
  const selectedCtraderAccount = (selectedBroker?.metadata_json as any)?.ctrader_selected_account || (selectedBroker?.metadata_json as any)?.selected_account || null;
  const activeInstruments = useMemo(() => {
    const active = marketInstruments.filter((item) => item.is_active !== false);
    return active.length ? active : marketInstruments;
  }, [marketInstruments]);
  const brokerInstrumentChoices = useMemo<MarketInstrument[]>(() => {
    const usable = brokerSymbols.filter((item) => item?.symbol && item.success !== false);
    if (!usable.length) return activeInstruments;
    return usable.map((item) => {
      const exact = String(item.symbol).trim();
      const canonical = activeInstruments.find((candidate) => {
        const a = String(candidate.symbol || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
        const b = exact.toUpperCase().replace(/[^A-Z0-9]/g, "");
        return a === b || b.startsWith(a) || a.startsWith(b);
      });
      return {
        ...(canonical || {}),
        symbol: exact,
        name: item.description || item.name || canonical?.name || exact,
        broker_symbol: exact,
        instrument_key: exact,
        market: selectedProvider || canonical?.market || canonical?.asset_class || "BROKER",
        asset_class: canonical?.asset_class || canonical?.market || undefined,
      } as MarketInstrument;
    });
  }, [brokerSymbols, activeInstruments, selectedProvider]);
  const filteredInstruments = useMemo(() => {
    const q = instrumentSearch.trim().toUpperCase();
    const rows = q
      ? brokerInstrumentChoices.filter((item) => [item.symbol, item.name, item.asset_class, item.market, item.exchange, item.broker_symbol, (item as any).instrument_key].some((value) => String(value || "").toUpperCase().includes(q)))
      : brokerInstrumentChoices;
    return rows.slice(0, 500);
  }, [brokerInstrumentChoices, instrumentSearch]);
  const selectedInstrument = useMemo(() => brokerInstrumentChoices.find((item) => String(item.symbol).toUpperCase() === form.instrument.toUpperCase()), [brokerInstrumentChoices, form.instrument]);
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
    const load = async () => {
      try {
        setLoading(true);
        const [strategyRows, brokerRows, access, instrumentRows, profileRows] = await Promise.all([
          liveTradingApi.listStrategies(),
          liveTradingApi.listBrokerAccounts(),
          liveTradingApi.getLiveAccessStatus().catch(() => null),
          liveTradingApi.listMarketInstruments().catch(() => []),
          fundedBacktestsApi.listProfiles().catch(() => []),
        ]);
        if (access) setAccessStatus(access);
        setStrategies(strategyRows);
        setBrokers(brokerRows);
        setMarketInstruments(instrumentRows);
        setFundedProfiles(profileRows.filter((p) => p.is_active !== false));
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
      setForm((prev) => ({ ...prev, mode: "LIVE", broker_account_id: connectedLiveBrokers[0]?.id || "" }));
      return;
    }
    const options = form.mode === "LIVE" ? connectedLiveBrokers : connectedDemoBrokers;
    if (!form.broker_account_id && options.length > 0) {
      setForm((prev) => ({ ...prev, broker_account_id: options[0].id }));
    }
    if (form.broker_account_id && !options.some((broker) => broker.id === form.broker_account_id)) {
      setForm((prev) => ({ ...prev, broker_account_id: options[0]?.id || "" }));
    }
  }, [connectedDemoBrokers, connectedLiveBrokers, form.mode, form.broker_account_id]);

  useEffect(() => {
    const accountId = form.broker_account_id;
    if (!accountId) {
      setBrokerSymbols([]);
      setBrokerSymbolsError(null);
      return;
    }
    let cancelled = false;
    setBrokerSymbolsLoading(true);
    setBrokerSymbolsError(null);
    void liveTradingApi.listBrokerSymbols(accountId, "", 2000).then((rows) => {
      if (cancelled) return;
      const usable = (rows || []).filter((row) => row?.symbol && row.success !== false);
      setBrokerSymbols(usable);
      const failed = (rows || []).find((row) => row?.success === false);
      if (failed && !usable.length) setBrokerSymbolsError(String(failed.message || "Unable to load symbols from selected broker."));
    }).catch((error: any) => {
      if (!cancelled) {
        setBrokerSymbols([]);
        setBrokerSymbolsError(errorMessage(error, "Unable to load symbols from selected broker."));
      }
    }).finally(() => { if (!cancelled) setBrokerSymbolsLoading(false); });
    return () => { cancelled = true; };
  }, [form.broker_account_id]);

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
    if (!brokerInstrumentChoices.length) return;
    const preferred = brokerInstrumentChoices.find((item) => String(item.symbol).toUpperCase() === "XAUUSD") || brokerInstrumentChoices.find((item) => String(item.symbol).toUpperCase().startsWith("XAUUSD")) || brokerInstrumentChoices[0];
    if (brokerInstrumentChoices.some((item) => String(item.symbol).toUpperCase() === form.instrument.toUpperCase())) return;
    selectInstrument(preferred.symbol);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brokerInstrumentChoices, form.instrument]);

  const selectInstrument = (symbol: string) => {
    const instrument = brokerInstrumentChoices.find((item) => String(item.symbol).toUpperCase() === symbol.toUpperCase());
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

  useEffect(() => {
    if (form.account_policy_type !== "FUNDED") return;
    const profile = selectedFundedProfile || fundedProfiles[0] || null;
    if (!profile) return;
    const phase = String(profile.challenge_type || "").toUpperCase() === "INSTANT" ? null : (profile.phases?.[0]?.phase_number ?? null);
    if (!selectedFundedProfile) {
      setForm((prev) => ({ ...prev, funded_profile_id: profile.id, funded_phase_number: phase }));
    } else if (String(profile.challenge_type || "").toUpperCase() !== "INSTANT" && !profile.phases?.some((p) => p.phase_number === form.funded_phase_number)) {
      setForm((prev) => ({ ...prev, funded_phase_number: phase }));
    }
  }, [form.account_policy_type, form.funded_phase_number, fundedProfiles, selectedFundedProfile]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (form.account_policy_type === "FUNDED" && fundedSubscriptionAllowed === false) {
      showToast(accessStatus?.funded_live?.message || "Active paid subscription required for Funded / Prop Live Trading.", "error");
      return;
    }
    if (form.account_policy_type !== "FUNDED" && accessStatus?.allowed === false) {
      showToast("Active subscription required to deploy live strategies", "error");
      return;
    }
    if (!form.strategy_id) {
      showToast("No deployable strategy found for selected mode", "error");
      return;
    }
    if (!form.broker_account_id) {
      showToast("Select a connected broker account.", "error");
      return;
    }
    if (!selectedBroker || String(selectedBroker.status || "").toUpperCase() !== "CONNECTED") {
      showToast("Selected broker account is not connected.", "error");
      return;
    }
    const selectedMode = brokerMode(selectedBroker);
    if (selectedMode && selectedMode !== form.mode) {
      showToast(`Selected broker account is not ${form.mode}.`, "error");
      return;
    }
    if (!selectedInstrument && !form.instrument) {
      showToast("Select instrument from Market Master.", "error");
      return;
    }
    if (form.mode === "LIVE" && connectedLiveBrokers.length === 0) {
      showToast("No connected broker account found for this mode.", "error");
      return;
    }
    if (form.mode === "DEMO" && connectedDemoBrokers.length === 0) {
      showToast("No connected broker account found for this mode.", "error");
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
    if (form.account_policy_type === "FUNDED") {
      if (!selectedFundedProfile) { showToast("Select a funded account profile.", "error"); return; }
      if (String(selectedFundedProfile.challenge_type || "").toUpperCase() !== "INSTANT" && !form.funded_phase_number) { showToast("Select the current funded phase.", "error"); return; }
      if (form.funded_risk_mode === "FIXED" && form.funded_fixed_risk_pct <= 0) { showToast("Fixed funded risk must be greater than 0%.", "error"); return; }
      const brokerCurrency = String(brokerFinancials.currency || "").toUpperCase();
      if (brokerCurrency && brokerCurrency !== String(selectedFundedProfile.account_currency || "").toUpperCase()) { showToast(`Broker currency ${brokerCurrency} does not match funded profile currency ${selectedFundedProfile.account_currency}.`, "error"); return; }
      if (form.funded_attach_mode === "EXISTING_IN_PROGRESS") {
        const init = form.funded_initialization_json || {};
        const positive = (key: string) => Number(init[key] || 0) > 0;
        if (!positive("today_start_balance")) { showToast("Today start balance is required and must be greater than 0 for an existing in-progress funded account.", "error"); return; }
        if (!positive("today_start_equity")) { showToast("Today start equity is required and must be greater than 0 for an existing in-progress funded account.", "error"); return; }
        if (["TRAILING_BALANCE", "HIGH_WATER_MARK"].includes(selectedFundedMaxDrawdownMode) && !positive("existing_high_water_balance")) { showToast("Existing high-water balance is required for this trailing funded account.", "error"); return; }
        if (["TRAILING_EQUITY", "HIGH_WATER_MARK"].includes(selectedFundedMaxDrawdownMode) && !positive("existing_high_water_equity")) { showToast("Existing high-water equity is required for this trailing funded account.", "error"); return; }
        for (const key of ["completed_trading_days", "completed_qualifying_days"]) {
          const value = init[key];
          if (value !== undefined && value !== "" && Number(value) < 0) { showToast(`${key.replace(/_/g, " " )} cannot be negative.`, "error"); return; }
        }
      }
    }
    try {
      setSaving(true);
      const resolvedInstrument = selectedInstrument?.symbol || form.instrument;
      const resolvedKey = form.instrument_key || instrumentKeyValue(selectedInstrument) || resolvedInstrument;
      const created = await liveTradingApi.createDeployment({
        ...form,
        broker_account_id: form.broker_account_id || null,
        funded_profile_id: form.account_policy_type === "FUNDED" && form.funded_profile_id ? form.funded_profile_id : null,
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
        if (gate.funded_live) {
          setAccessStatus((prev) => ({
            allowed: prev?.allowed ?? true,
            requires_subscription: prev?.requires_subscription ?? false,
            message: prev?.message,
            recommended_coupon: gate.recommended_coupon ?? prev?.recommended_coupon ?? null,
            subscription: prev?.subscription ?? null,
            funded_live: gate.funded_live,
          }));
        } else {
          setAccessStatus(gate);
        }
        showToast(gate.message || gate.funded_live?.message || "Active subscription required to deploy live strategies", "error");
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
        subtitle="Create DEMO or LIVE broker deployments using your connected broker account."
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
          <p className="text-purple-100">Loading deployable strategies and connected broker accounts...</p>
        ) : (
          <form onSubmit={submit} className="space-y-6">
            <section className="rounded-2xl border border-white/10 bg-white/5 p-5" aria-labelledby="account-type-heading">
              <div className="mb-4">
                <h2 id="account-type-heading" className="text-base font-semibold text-white">Account Type</h2>
                <p className="mt-1 text-xs text-purple-200/75">Choose the account policy first. Broker execution remains DEMO or LIVE in both cases.</p>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, account_policy_type: "STANDARD" }))}
                  className={`rounded-2xl border p-4 text-left transition ${form.account_policy_type === "STANDARD" ? "border-cyan-300/50 bg-cyan-400/15 ring-1 ring-cyan-300/30" : "border-white/10 bg-black/10 hover:border-white/20 hover:bg-white/5"}`}
                >
                  <div className="flex items-center justify-between gap-3"><span className="font-semibold text-white">Standard Broker Account</span>{form.account_policy_type === "STANDARD" && <BadgePill>Selected</BadgePill>}</div>
                  <p className="mt-2 text-xs leading-5 text-purple-200/75">Use the existing standard live risk controls and broker execution flow.</p>
                </button>
                <button
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, account_policy_type: "FUNDED" }))}
                  className={`rounded-2xl border p-4 text-left transition ${form.account_policy_type === "FUNDED" ? "border-lime-300/50 bg-lime-400/15 ring-1 ring-lime-300/30" : "border-white/10 bg-black/10 hover:border-white/20 hover:bg-white/5"}`}
                >
                  <div className="flex items-center justify-between gap-3"><span className="font-semibold text-white">Funded / Prop Account</span><span className="flex flex-wrap justify-end gap-1"><BadgePill>Subscriber Only</BadgePill>{form.account_policy_type === "FUNDED" && <BadgePill>Selected</BadgePill>}</span></div>
                  <p className="mt-2 text-xs leading-5 text-purple-200/75">Attach an existing funded profile and enforce prop drawdown, phase and dynamic/fixed risk rules server-side. An active paid subscription is required.</p>
                </button>
              </div>
            </section>

            {form.account_policy_type === "FUNDED" && (
              fundedSubscriptionAllowed ? (
                <div className="rounded-xl border border-lime-400/20 bg-lime-400/10 p-4 text-sm text-lime-100">
                  <div className="flex gap-2"><ShieldCheck className="mt-0.5 h-4 w-4" /><span><strong>Funded Live subscriber access:</strong> active. You may configure a Funded / Prop deployment; broker and funded guard readiness are still validated separately.</span></div>
                </div>
              ) : (
                <div className="flex flex-col gap-3 rounded-xl border border-amber-300/25 bg-amber-400/10 p-4 text-sm text-amber-100 md:flex-row md:items-center md:justify-between">
                  <div className="flex gap-2"><ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" /><div><strong>Funded / Prop Live Trading requires an active paid subscription.</strong><div className="mt-1 text-xs text-amber-100/80">The backend also enforces this rule, so the funded deployment cannot be created by bypassing the browser.</div></div></div>
                  <Button type="button" onClick={() => router.push("/pricing")} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">View Plans</Button>
                </div>
              )
            )}

            <div className="rounded-xl border border-lime-400/20 bg-lime-400/10 p-4 text-sm text-lime-100">
              <div className="flex gap-2"><ShieldCheck className="mt-0.5 h-4 w-4" /><span>DEMO and LIVE deployments require a connected broker account.</span></div>
            </div>

            {!deployableStrategies.length && (
              <div className="rounded-xl border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100">
                No deployable strategy found for {form.mode}. Run verification/sandbox and ask admin to enable deployment.
              </div>
            )}

            {connectedDemoBrokers.length === 0 && connectedLiveBrokers.length === 0 && (
              <div className="flex flex-col gap-3 rounded-xl border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="font-semibold text-white">No connected broker account found.</div>
                  <div>Connect a broker account before creating DEMO or LIVE deployments.</div>
                </div>
                <Link href="/brokers" className="rounded-lg bg-lime-500 px-4 py-2 font-semibold text-slate-950 hover:bg-lime-400">Connect Broker</Link>
              </div>
            )}

            {form.mode === "LIVE" && connectedLiveBrokers.length === 0 && (
              <div className="flex flex-col gap-3 rounded-xl border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="font-semibold text-white">No connected broker found for this mode.</div>
                  <div>No connected broker account found for this mode.</div>
                </div>
                <Link href="/brokers" className="rounded-lg bg-lime-500 px-4 py-2 font-semibold text-slate-950 hover:bg-lime-400">Connect Broker</Link>
              </div>
            )}

            {form.mode === "DEMO" && connectedDemoBrokers.length === 0 && connectedLiveBrokers.length > 0 && (
              <div className="flex flex-col gap-3 rounded-xl border border-cyan-400/25 bg-cyan-400/10 p-4 text-sm text-cyan-100 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="font-semibold text-white">No connected DEMO broker found.</div>
                  <div>Connect a DEMO broker account, or switch to LIVE if your LIVE broker account is connected.</div>
                </div>
                <Link href="/brokers" className="rounded-lg bg-lime-500 px-4 py-2 font-semibold text-slate-950 hover:bg-lime-400">Connect Broker</Link>
              </div>
            )}

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
              <Field label="Deployment name" help="A friendly name to identify this broker deployment in your workspace."><input required className={inputClass} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
              <Field label="Deployable strategy" help="Only strategies approved for the selected mode are shown here."><select required className={selectClass} value={form.strategy_id} onChange={(e) => setForm({ ...form, strategy_id: e.target.value })}>{deployableStrategies.length === 0 && <option value="">No deployable strategy found</option>}{deployableStrategies.map((strategy) => <option key={strategy.id} value={strategy.id}>{strategy.name} • {form.mode === "LIVE" ? "Live Approved" : "Demo Ready"}</option>)}</select></Field>

              <Field label="Instrument" help="Search symbols from the selected connected broker. Broker naming/suffixes are preserved exactly; Market Master is only a fallback.">
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
                      {brokerSymbolsLoading && <div className="px-3 py-2 text-xs text-purple-200">Loading exact symbols from selected broker…</div>}
                      {!brokerSymbolsLoading && !brokerInstrumentChoices.length && <div className="px-3 py-2 text-xs text-amber-200">No instruments returned by the selected broker or Market Master.</div>}
                      {!brokerSymbolsLoading && brokerInstrumentChoices.length > 0 && filteredInstruments.length === 0 && <div className="px-3 py-2 text-xs text-amber-200">No matching instruments found.</div>}
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
                <p className={`mt-1 text-xs ${brokerSymbolsError ? "text-amber-200" : "text-purple-300"}`}>{brokerSymbolsError || (brokerSymbols.length ? `Loaded ${brokerSymbols.length} exact symbols from ${selectedProvider || "broker"}. ${instrumentOpen && instrumentSearch.trim() ? `Showing ${filteredInstruments.length} matching result(s); clear the search box to see all.` : `Showing up to ${Math.min(500, brokerInstrumentChoices.length)} instruments in the dropdown.`}` : form.broker_account_id ? "Using Market Master fallback until broker symbols are available." : "Select a broker account first.")}</p>
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

              <Field label="Mode" help="DEMO and LIVE are broker execution environments. Funded is a separate account policy, not a broker mode."><select className={selectClass} value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value as LiveMode, broker_account_id: "" })}><option value="DEMO" disabled={connectedDemoBrokers.length === 0}>DEMO / Broker</option><option value="LIVE" disabled={connectedLiveBrokers.length === 0}>LIVE / Broker</option></select></Field>
              <Field label="Broker account" help="Required for DEMO and LIVE broker execution. Risk is calculated from broker account balance/equity where available."><select required className={selectClass} value={form.broker_account_id} onChange={(e) => setForm({ ...form, broker_account_id: e.target.value })}><option value="">Select connected {form.mode} broker</option>{brokerOptions.map((broker) => {
                const code = String(broker.broker_code || broker.broker_name || "BROKER").toUpperCase();
                const mode = brokerMode(broker) || form.mode;
                const login = broker.login_id || (broker.metadata_json as any)?.selected_account?.login || (broker.metadata_json as any)?.selected_account?.account_number || "";
                const server = broker.server_name || (broker.metadata_json as any)?.selected_account?.server || (broker.metadata_json as any)?.selected_account?.server_name || "";
                const suffix = [login, server].filter(Boolean).join("/");
                const label = `${code} • ${broker.account_label || broker.broker_name || "Broker"} • ${mode} • ${broker.status || "CONNECTED"}${suffix ? ` • ${suffix}` : ""}`;
                return <option key={broker.id} value={broker.id}>{label}</option>;
              })}</select><p className="text-xs text-purple-300">Risk is calculated from broker account balance/equity where available.</p></Field>

              {form.account_policy_type === "STANDARD" && <Field label="Risk per trade" help="Percent of broker balance/equity risked on one trade. Example: 1% means 0.01 internally."><select className={selectClass} value={form.risk_per_trade} onChange={(e) => setForm({ ...form, risk_per_trade: Number(e.target.value) })}>{riskOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><p className="text-xs text-purple-300">Displayed as percent. Stored internally as decimal fraction.</p></Field>}
              <Field label="RR ratio" help="Reward-to-risk target used when the strategy or runtime engine calculates target price."><input type="number" step="0.1" className={inputClass} value={form.rr_ratio} onChange={(e) => setForm({ ...form, rr_ratio: Number(e.target.value) })} /></Field>
              <Field label="Price risk %" help="Fallback fixed stop-loss distance when strategy does not provide SL. Example: 2% means 0.02 internally."><select className={selectClass} value={form.price_risk_pct} onChange={(e) => setForm({ ...form, price_risk_pct: Number(e.target.value) })}>{priceRiskOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><p className="text-xs text-purple-300">Displayed as percent. Stored internally as decimal fraction.</p></Field>
              {form.account_policy_type === "STANDARD" && <Field label="Max daily loss" help="Maximum additional AlgoAgentX daily-loss guard for a standard broker deployment."><input type="number" className={inputClass} value={form.max_daily_loss} onChange={(e) => setForm({ ...form, max_daily_loss: Number(e.target.value) })} /></Field>}
              <Field label="Max trades per day" help="Maximum number of orders the runner is allowed to place in one day."><input type="number" className={inputClass} value={form.max_trades_per_day} onChange={(e) => setForm({ ...form, max_trades_per_day: Number(e.target.value) })} /></Field>
              <Field label="Max open positions" help="Maximum open positions allowed at the same time for this deployment."><input type="number" className={inputClass} value={form.max_open_positions} onChange={(e) => setForm({ ...form, max_open_positions: Number(e.target.value) })} /></Field>
            </div>

            {form.account_policy_type === "FUNDED" && (
              <div className="space-y-4 rounded-2xl border border-lime-300/20 bg-lime-300/5 p-5">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="mt-0.5 h-5 w-5 text-lime-300" />
                  <div><h3 className="font-semibold text-white">Funded Account Guard</h3><p className="text-xs text-purple-200/75">Prop-firm rules are enforced by the API from fresh broker balance/equity. Legacy fallback deployment capital is never used for funded sizing.</p></div>
                </div>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  <Field label="Funded Account Profile" help="Existing funded profile is snapshotted into this live deployment so later profile edits cannot silently change active rules.">
                    <select className={selectClass} value={form.funded_profile_id} onChange={(e) => { const p = fundedProfiles.find((x) => x.id === e.target.value); setForm({ ...form, funded_profile_id: e.target.value, funded_phase_number: String(p?.challenge_type || "").toUpperCase() === "INSTANT" ? null : (p?.phases?.[0]?.phase_number ?? null) }); }}>
                      <option value="">Select funded profile</option>{fundedProfiles.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.provider_name || "Provider"} · {p.account_currency} {Number(p.account_size).toLocaleString()}</option>)}
                    </select>
                  </Field>
                  {selectedFundedProfile && String(selectedFundedProfile.challenge_type || "").toUpperCase() !== "INSTANT" && <Field label="Current Stage / Phase" help="Live phase does not advance automatically. PASS READY waits for explicit provider transition."><select className={selectClass} value={form.funded_phase_number ?? ""} onChange={(e) => setForm({ ...form, funded_phase_number: Number(e.target.value) })}>{(selectedFundedProfile.phases || []).map((p) => <option key={p.phase_number} value={p.phase_number}>{p.phase_name || `Phase ${p.phase_number}`}</option>)}</select></Field>}
                  <Field label="Attach Mode" help="Use Existing In-Progress only when attaching an already-traded funded account. Trailing rules may require provider high-water/start-of-day values."><select className={selectClass} value={form.funded_attach_mode} onChange={(e) => setForm({ ...form, funded_attach_mode: e.target.value as FundedAttachMode })}><option value="NEW_OR_RESET_ACCOUNT">New / Reset Account</option><option value="EXISTING_IN_PROGRESS">Existing In-Progress Account</option></select></Field>
                  <Field label="Funded Risk Mode" help="Dynamic selects the profile risk ladder by account return. Fixed uses one requested risk percentage, still capped by funded loss capacity."><select className={selectClass} value={form.funded_risk_mode} onChange={(e) => setForm({ ...form, funded_risk_mode: e.target.value as FundedLiveRiskMode })}><option value="DYNAMIC">Dynamic Risk Ladder</option><option value="FIXED">Fixed Risk %</option></select></Field>
                  {form.funded_risk_mode === "FIXED" && <Field label="Fixed funded risk" help="Requested risk per entry. The funded guard may reduce it near a DD boundary."><select className={selectClass} value={form.funded_fixed_risk_pct} onChange={(e) => setForm({ ...form, funded_fixed_risk_pct: Number(e.target.value) })}>{riskOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></Field>}
                  <Field label="Safety Buffer %" help="AlgoAgentX conservative buffer applied to remaining daily/max drawdown capacity. 5 means 5% of remaining capacity is reserved."><input type="number" min="0" max="99" step="0.5" className={inputClass} value={form.funded_safety_buffer_pct * 100} onChange={(e) => setForm({ ...form, funded_safety_buffer_pct: Number(e.target.value) / 100 })} /></Field>
                  <Field label="Configured maximum risk %" help="Optional hard cap above dynamic/fixed requested risk."><input type="number" min="0.01" max="10" step="0.25" className={inputClass} value={form.funded_configured_max_risk_pct * 100} onChange={(e) => setForm({ ...form, funded_configured_max_risk_pct: Number(e.target.value) / 100 })} /></Field>
                  <Field label="Additional AlgoAgentX Daily Safety Cap" help="Optional extra AlgoAgentX loss cap. This is not the prop firm's daily drawdown rule; the funded profile remains authoritative."><input type="number" min="0" step="1" className={inputClass} value={form.max_daily_loss} onChange={(e) => setForm({ ...form, max_daily_loss: Number(e.target.value) })} /></Field>
                </div>

                {selectedFundedProfile && <div className="grid gap-3 rounded-xl border border-white/10 bg-black/10 p-4 text-xs md:grid-cols-2 xl:grid-cols-4">
                  <div><span className="text-purple-300">Provider</span><div className="mt-1 font-medium text-white">{selectedFundedProfile.provider_name || "—"}</div></div>
                  <div><span className="text-purple-300">Challenge</span><div className="mt-1 font-medium text-white">{selectedFundedProfile.challenge_type}</div></div>
                  <div><span className="text-purple-300">Account size</span><div className="mt-1 font-medium text-white">{selectedFundedProfile.account_currency} {Number(selectedFundedProfile.account_size).toLocaleString()}</div></div>
                  <div><span className="text-purple-300">Rule timezone</span><div className="mt-1 font-medium text-white">{String((selectedFundedProfile.rules_json as any)?.rule_timezone || "UTC")}</div></div>
                  {selectedFundedPhase && <><div><span className="text-purple-300">Daily DD</span><div className="mt-1 font-medium text-white">{(Number(selectedFundedPhase.daily_drawdown_pct) * 100).toFixed(2)}% · {selectedFundedPhase.daily_drawdown_mode}</div></div><div><span className="text-purple-300">Max DD</span><div className="mt-1 font-medium text-white">{(Number(selectedFundedPhase.max_drawdown_pct) * 100).toFixed(2)}% · {selectedFundedPhase.max_drawdown_mode}</div></div></>}
                  <div><span className="text-purple-300">Broker balance</span><div className="mt-1 font-medium text-white">{brokerFinancials.balance ?? "Not synced"}</div></div>
                  <div><span className="text-purple-300">Broker equity</span><div className="mt-1 font-medium text-white">{brokerFinancials.equity ?? "Not synced"}</div></div>
                  <div><span className="text-purple-300">Broker currency</span><div className="mt-1 font-medium text-white">{brokerFinancials.currency || "Not synced"}</div></div>
                  <div><span className="text-purple-300">Broker freshness</span><div className={`mt-1 font-medium ${brokerMetricsFresh ? "text-lime-200" : "text-amber-200"}`}>{brokerMetricsFresh ? "Fresh" : "Stale / not synchronized"}</div></div>
                  <div><span className="text-purple-300">Broker Compatibility / Guard Readiness</span><div className={`mt-1 font-medium ${fundedCompatibilityReady ? "text-lime-200" : "text-amber-200"}`}>{fundedCompatibilityReady ? "READY" : "BLOCKED — sync valid balance/equity and verify currency"}</div></div>
                </div>}

                {form.funded_risk_mode === "DYNAMIC" && selectedFundedProfile && <div className="rounded-xl border border-white/10 bg-black/10 p-4"><div className="mb-2 text-xs font-semibold uppercase tracking-wide text-purple-200">Dynamic risk ladder snapshot</div><div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">{(selectedFundedProfile.risk_tiers || []).filter((t) => t.is_active).map((tier) => <div key={`${tier.sort_order}-${tier.name}`} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-purple-100"><div className="font-medium text-white">{tier.name}</div><div>{tier.min_account_return_pct == null ? "−∞" : `${(Number(tier.min_account_return_pct) * 100).toFixed(2)}%`} → {tier.max_account_return_pct == null ? "+∞" : `${(Number(tier.max_account_return_pct) * 100).toFixed(2)}%`} · Risk {(Number(tier.risk_percent) * 100).toFixed(2)}%</div></div>)}</div></div>}

                {form.funded_attach_mode === "EXISTING_IN_PROGRESS" && <details className="rounded-xl border border-amber-300/20 bg-amber-400/5 p-4"><summary className="cursor-pointer text-sm font-medium text-amber-100">Advanced in-progress account state</summary><p className="mt-2 text-xs text-amber-100/80">Today start balance/equity are required. Drawdown mode: <strong>{selectedFundedMaxDrawdownMode || "profile-defined"}</strong>. Historical high-water values become required for trailing rules; AlgoAgentX will not guess them.</p><div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[
                  ["today_start_balance", "Today start balance"], ["today_start_equity", "Today start equity"], ["existing_high_water_balance", "Existing high-water balance"], ["existing_high_water_equity", "Existing high-water equity"], ["completed_trading_days", "Completed trading days"], ["completed_qualifying_days", "Completed qualifying days"],
                ].map(([key, label]) => <Field key={key} label={label} help="Required when needed to reconstruct an existing funded provider state safely. The API validates all required values again."><input type="number" min="0" step={String(key).includes("days") ? "1" : "0.01"} className={inputClass} value={String(form.funded_initialization_json[key] ?? "")} onChange={(e) => setForm({ ...form, funded_initialization_json: { ...form.funded_initialization_json, [key]: e.target.value === "" ? "" : Number(e.target.value) } })} /></Field>)}</div></details>}
              </div>
            )}

            {isUpstox && <div className="rounded-xl border border-cyan-400/25 bg-cyan-400/10 p-4 text-sm text-cyan-100">Upstox deployment requires the Upstox instrument key. Example Reliance: NSE_EQ|INE002A01018.</div>}
            {isCtrader && <div className="rounded-xl border border-fuchsia-400/25 bg-fuchsia-400/10 p-4 text-sm text-fuchsia-100">cTrader deployment uses the selected synced cTrader account. LIVE also requires platform cTrader LIVE configuration.</div>}

            <div className="flex flex-wrap gap-4 rounded-xl border border-white/10 bg-white/5 p-4">
              <label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.allow_short} onChange={(e) => setForm({ ...form, allow_short: e.target.checked })} />Allow short<FieldHelpTooltip label="Allow short" content="Allow the strategy to open short/sell positions when sell signals are approved." /></label>
              <label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.auto_trade_enabled} onChange={(e) => setForm({ ...form, auto_trade_enabled: e.target.checked })} />Auto trade enabled<FieldHelpTooltip label="Auto trade enabled" content="When enabled, approved signals can be sent to the execution engine. Keep disabled until QA is complete." /></label>
            </div>

            <Button disabled={saving || !form.strategy_id || !form.broker_account_id || selectedPolicyAccessBlocked || (form.account_policy_type === "FUNDED" && !fundedCompatibilityReady)} className="border-0 bg-gradient-to-r from-lime-400 to-emerald-500 text-slate-950 hover:from-lime-300 hover:to-emerald-400">{selectedPolicyAccessBlocked ? (form.account_policy_type === "FUNDED" ? "Funded Subscription Required" : "Subscription Required") : saving ? "Creating..." : "Create Deployment"}</Button>
          </form>
        )}
      </GlassCard>
    </PageShell>
  );
}
