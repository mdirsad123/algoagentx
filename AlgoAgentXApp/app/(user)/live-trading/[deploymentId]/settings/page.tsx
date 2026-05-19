"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Copy, Lock, ShieldCheck } from "lucide-react";
import { FieldHelpTooltip } from "@/components/common/FieldHelpTooltip";
import { LiveCompatibilityCard } from "@/components/live/LiveCompatibilityCard";
import { RuntimeSettingsForm } from "@/components/runtime/RuntimeSettingsForm";
import { RUNTIME_TABS } from "@/components/runtime/runtimeSettingsDefaults";
import type { RuntimeTab } from "@/components/runtime/runtimeSettingsTypes";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, BrokerSymbol, LiveCompatibilityResult, LiveDeploymentSummary, LiveOrderPreview, MarketInstrument } from "@/types/live-trading";


const FIELD_HELP: Record<string, string> = {
  "Name": "Friendly name for this live deployment. It helps you identify this strategy in dashboards and logs.",
  "Mode": "DEMO and LIVE use approved connected broker accounts. Risk is calculated from broker balance/equity.",
  "Broker Account": "Approved connected broker account used for DEMO or LIVE execution. Risk is calculated from broker balance/equity where available.",
  "Instrument": "Trading symbol for this deployment. It should match Instrument Master and broker symbol settings for correct sizing and execution.",
  "Timeframe": "Candle interval used by the strategy runner. Example: M5 means 5-minute candles. It affects signal frequency and execution timing.",
  "Broker Account Capital": "Read-only broker balance/equity used by the live risk engine. It appears after broker sync.",
  "Risk per Trade": "Percentage of capital risked per trade when using risk-based sizing. Example: 1% of $10,000 means $100 risk per trade. Higher values can create large losses.",
  "RR Ratio": "Reward-to-risk ratio. Example: 1:2 means target is twice the stop loss distance. This affects live TP preview and order planning.",
  "SL Mode": "Defines how stop loss is calculated: Fixed Percent, ATR volatility, recent swing high/low, or strategy suggested stop. This directly affects lot/quantity sizing.",
  "ATR Period": "Number of candles used to calculate Average True Range. Example: 14. Higher values make the volatility estimate smoother.",
  "ATR Multiplier": "Multiplier applied to ATR to calculate stop loss distance. Example: 1.5. Higher multiplier means wider stop and usually smaller position size.",
  "Swing Lookback": "Number of candles used to find recent swing high/low for stop loss placement. Example: 5 or 10 candles.",
  "Fixed Price Risk %": "Stop loss distance as a fixed percent of entry price. Example: 0.20% means SL is 0.20% away from entry. Too tight can cause noisy exits.",
  "Max Daily Loss": "Daily loss guardrail for this deployment. If losses reach this amount, trading should stop according to backend safety rules.",
  "Max Trades / Day": "Limits number of trades per day to avoid overtrading. Example: 3 trades/day.",
  "Max Open Positions": "Limits simultaneous open positions. Example: 1 keeps live risk controlled.",
  "MT5 DEMO Max Lot": "Maximum lot allowed for MT5 demo orders from this deployment. Example: 0.02. Keep this low while testing.",
  "Quantity Mode": "Risk Based calculates size from stop loss and risk percent. Fixed Quantity uses the same quantity for each trade.",
  "Fixed Qty": "Manual quantity used when Quantity Mode is Fixed Quantity. High values can place oversized orders.",
  "Max Qty": "Maximum quantity cap for non-lot instruments. This protects from oversized live orders.",
  "Max Order Value": "Maximum order notional value allowed. This prevents very large orders when price or quantity is high.",
  "Product Type": "Broker product type. MIS is intraday; CNC is delivery. Use only the product type supported by your broker and instrument.",
  "Square-off Time": "Time used for intraday square-off on supported Indian market instruments. It is disabled for forex/metals like XAUUSD.",
  "Upstox Instrument Key": "Broker-specific instrument key required for Upstox orders. Example: NSE_EQ|INE040A01034.",
  "Exchange": "Broker exchange code such as NSE or BSE. Wrong values can reject orders.",
  "Segment": "Broker segment such as NSE_EQ or NSE_FO. Wrong values can reject orders.",
  "Side": "Manual preview side. BUY previews long orders; SELL previews short orders.",
  "Manual Entry": "Entry price used only for manual preview. It does not place an order by itself.",
  "Manual Stop Loss": "Stop loss price used only for manual preview. Keep it realistic because sizing depends on stop distance.",
};

const TIMEFRAME_OPTIONS = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"];
const UPSTOX_TIMEFRAME_OPTIONS = ["1m", "5m", "15m", "30m", "1h", "1d"];
const FALLBACK_SYMBOL_OPTIONS = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY", "US30", "NAS100"];

const USD_CAPITAL = [100, 500, 1000, 5000, 10000, 100000];
const INR_CAPITAL = [10000, 25000, 50000, 100000, 500000, 1000000];
const RISK_OPTIONS = [0.0025, 0.005, 0.01, 0.015, 0.02, 0.03];
const RR_OPTIONS = [1, 1.5, 2, 3, 4, 5];
const SL_MODES = ["ATR", "SWING", "FIXED_PERCENT", "STRATEGY_SUGGESTED"];
const ATR_PERIODS = [7, 10, 14, 20, 21];
const ATR_MULTIPLIERS = [1, 1.5, 2, 2.5, 3];
const FIXED_RISK_OPTIONS = [0.001, 0.002, 0.003, 0.005, 0.01];
const USD_DAILY_LOSS = [25, 50, 100, 250, 500, 1000];
const INR_DAILY_LOSS = [500, 1000, 2500, 5000, 10000, 25000];
const MAX_TRADES = [1, 2, 3, 5, 10, 20];
const MAX_OPEN_POSITIONS = [1, 2, 3, 5];
const MT5_LOT_CAPS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1];

type FormState = {
  name: string; instrument: string; timeframe: string; mode: "PAPER" | "DEMO" | "LIVE"; broker_account_id: string;
  capital: number; risk_per_trade: number; rr_ratio: number; sl_mode: string; atr_period: number; atr_multiplier: number; swing_lookback: number; price_risk_pct: number;
  max_daily_loss: number; max_trades_per_day: number; max_open_positions: number; allow_short: boolean; auto_trade_enabled: boolean; auto_runner_enabled: boolean;
  mt5_demo_max_lot: number; broker_symbol: string; instrument_key: string; exchange: string; segment: string; product_type: string; order_variety: string;
  quantity_mode: string; fixed_quantity: number; max_quantity: number; max_order_value: number; square_off_time: string; upstox_order_confirmed: boolean;
  break_even_enabled: boolean; break_even_trigger_r: number; trailing_enabled: boolean; trailing_mode: string; trail_start_r: number; trail_atr_multiplier: number; partial_exit_enabled: boolean; partial_exit_at_r: number; partial_exit_percent: number;
};

const money = (value: number | string | null | undefined, currency = "USD") => new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(value || 0));
const percent = (value: number) => `${(Number(value || 0) * 100).toFixed(value < 0.01 ? 2 : 1)}%`;
const selectValue = (value: number, options: number[]) => options.some((item) => Number(item) === Number(value)) ? String(value) : "CUSTOM";

const normalizeSymbol = (value: unknown) => String(value || "").trim().toUpperCase();
const hasSpecValue = (value: unknown) => value !== null && value !== undefined && value !== "";
const yesNo = (value: unknown) => value === true ? "Yes" : value === false ? "No" : "—";
const displayValue = (value: unknown) => hasSpecValue(value) ? String(value) : "Missing";

type InstrumentOption = { key: string; value: string; label: string; source: "Instrument Master" | "Broker Symbol" | "Fallback"; instrument?: MarketInstrument; broker?: BrokerSymbol };

type InstrumentReadiness = {
  status: "Ready" | "Invalid" | "Missing";
  source: "Instrument Master" | "Broker Symbol Only" | "Fallback";
  spec: Record<string, any>;
  missingFields: string[];
  actionMessage: string;
  fallbackNotice?: string;
};

const buildInstrumentOptions = (currentSymbol: string, instruments: MarketInstrument[], brokerSymbols: BrokerSymbol[]): InstrumentOption[] => {
  const bySymbol = new Map<string, InstrumentOption>();
  const add = (option: InstrumentOption) => {
    const normalized = normalizeSymbol(option.value);
    if (!normalized) return;
    const existing = bySymbol.get(normalized);
    if (!existing || option.source === "Instrument Master") bySymbol.set(normalized, { ...option, value: normalized });
  };

  instruments.forEach((instrument) => {
    const symbol = normalizeSymbol(instrument.symbol);
    if (!symbol) return;
    add({
      key: `master-${instrument.id || symbol}`,
      value: symbol,
      label: `${symbol} · Instrument Master`,
      source: "Instrument Master",
      instrument,
    });
  });

  brokerSymbols.forEach((broker) => {
    const symbol = normalizeSymbol(broker.symbol);
    if (!symbol) return;
    add({ key: `broker-${symbol}`, value: symbol, label: `${symbol} · Broker Symbol`, source: "Broker Symbol", broker });
  });

  FALLBACK_SYMBOL_OPTIONS.forEach((symbol) => add({ key: `fallback-${normalizeSymbol(symbol)}`, value: symbol, label: `${normalizeSymbol(symbol)} · Fallback`, source: "Fallback" }));
  if (currentSymbol) add({ key: `current-${normalizeSymbol(currentSymbol)}`, value: currentSymbol, label: `${normalizeSymbol(currentSymbol)} · Current`, source: "Fallback" });

  return Array.from(bySymbol.values()).sort((a, b) => {
    const rank = { "Instrument Master": 0, "Broker Symbol": 1, "Fallback": 2 } as const;
    const sourceDiff = rank[a.source] - rank[b.source];
    return sourceDiff || a.value.localeCompare(b.value);
  });
};

const findSelectedMasterInstrument = (symbol: string, instruments: MarketInstrument[]) => {
  const normalized = normalizeSymbol(symbol);
  return instruments.find((instrument) => normalizeSymbol(instrument.symbol) === normalized || normalizeSymbol(instrument.broker_symbol) === normalized) || null;
};

const buildInstrumentReadiness = (symbol: string, master: MarketInstrument | null, broker: BrokerSymbol | null, preview: LiveOrderPreview | null): InstrumentReadiness => {
  const normalized = normalizeSymbol(symbol);
  const previewSpec = preview?.instrument_spec_snapshot && normalizeSymbol((preview.instrument_spec_snapshot as any).symbol || symbol) === normalized ? preview.instrument_spec_snapshot : null;
  const source = master ? "Instrument Master" : broker ? "Broker Symbol Only" : "Fallback";
  const rawSpec = master ? { ...master } : previewSpec ? { ...previewSpec } : { symbol: normalized };
  const quantityMode = normalizeSymbol(rawSpec.quantity_mode);
  const missing = new Set<string>();

  if (!master) {
    missing.add("instrument_master_record");
    missing.add("account_currency");
    missing.add("quantity_mode");
    missing.add("broker_symbol");
    missing.add("is_tradeable_live");
    missing.add("min_step_size");
  } else {
    if (!hasSpecValue(rawSpec.account_currency)) missing.add("account_currency");
    if (!hasSpecValue(rawSpec.quantity_mode)) missing.add("quantity_mode");
    if (!hasSpecValue(rawSpec.broker_symbol)) missing.add("broker_symbol");
    if (!hasSpecValue(rawSpec.tick_size) || Number(rawSpec.tick_size) <= 0) missing.add("tick_size");
    if (rawSpec.is_tradeable_live !== true) missing.add("is_tradeable_live");
    if (quantityMode === "LOTS") {
      if (!hasSpecValue(rawSpec.tick_value_per_lot) || Number(rawSpec.tick_value_per_lot) <= 0) missing.add("tick_value_per_lot");
      if (!hasSpecValue(rawSpec.lot_step) || Number(rawSpec.lot_step) <= 0) missing.add("lot_step");
      if (!hasSpecValue(rawSpec.min_lot) || Number(rawSpec.min_lot) <= 0) missing.add("min_lot");
    } else if (["SHARES", "UNITS", "CONTRACTS"].includes(quantityMode)) {
      if (!hasSpecValue(rawSpec.quantity_step) || Number(rawSpec.quantity_step) <= 0) missing.add("quantity_step");
      if (!hasSpecValue(rawSpec.min_quantity) || Number(rawSpec.min_quantity) <= 0) missing.add("min_quantity");
    } else {
      missing.add("quantity_mode");
      missing.add("min_step_size");
    }
  }

  (preview?.missing_fields || []).forEach((field) => missing.add(String(field)));
  const missingFields = Array.from(missing);
  const status = master ? (missingFields.length ? "Invalid" : "Ready") : "Missing";
  return {
    status,
    source,
    spec: rawSpec,
    missingFields,
    fallbackNotice: source !== "Instrument Master" ? "Fallback — not saved in Market Master" : undefined,
    actionMessage: status === "Ready" ? "This instrument is configured for live/demo preview." : `${normalized || "Selected symbol"} is not ready for live trading. Configure account currency, quantity mode, broker symbol, min/step size, and live enabled in Market Master.`,
  };
};

function FieldShell({ label, children, hint, help }: { label: string; children: ReactNode; hint?: string; help?: string }) {
  const helpText = help || FIELD_HELP[label] || "Runtime setting. Changing this can affect live risk, order preview, and execution behavior. Review carefully before saving.";
  return (
    <label className="space-y-2 text-sm text-purple-100">
      <span className="inline-flex items-center gap-1.5 font-semibold text-purple-50">
        {label}
        <FieldHelpTooltip label={`${label} help`} content={helpText} />
      </span>
      {children}
      {hint && <p className="text-xs text-purple-200/80">{hint}</p>}
    </label>
  );
}

function SelectBox(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-white outline-none disabled:cursor-not-allowed disabled:opacity-50 ${props.className || ""}`} />;
}

function InputBox(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none disabled:cursor-not-allowed disabled:opacity-50 ${props.className || ""}`} />;
}

export default function LiveDeploymentSettingsPage() {
  const { deploymentId } = useParams<{ deploymentId: string }>();
  const router = useRouter();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deploymentStatus, setDeploymentStatus] = useState<string>("DRAFT");
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [symbolOptions, setSymbolOptions] = useState<BrokerSymbol[]>([]);
  const [marketInstruments, setMarketInstruments] = useState<MarketInstrument[]>([]);
  const [loadingSymbols, setLoadingSymbols] = useState(false);
  const [advancedMode, setAdvancedMode] = useState(false);
  const [advancedPreview, setAdvancedPreview] = useState(false);
  const [liveRuntimeTab, setLiveRuntimeTab] = useState<RuntimeTab>("risk");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [manualSide, setManualSide] = useState<"BUY" | "SELL">("BUY");
  const [manualEntry, setManualEntry] = useState(4630);
  const [manualSL, setManualSL] = useState(4625);
  const [riskPreview, setRiskPreview] = useState<LiveOrderPreview | null>(null);
  const [summary, setSummary] = useState<LiveDeploymentSummary | null>(null);
  const [compatibility, setCompatibility] = useState<LiveCompatibilityResult | null>(null);
  const [compatBusy, setCompatBusy] = useState(false);
  const [form, setForm] = useState<FormState>({
    name: "", instrument: "", timeframe: "", mode: "PAPER", broker_account_id: "", capital: 100000, risk_per_trade: 0.01, rr_ratio: 2,
    sl_mode: "FIXED_PERCENT", atr_period: 14, atr_multiplier: 2, swing_lookback: 10, price_risk_pct: 0.002, max_daily_loss: 5000,
    max_trades_per_day: 10, max_open_positions: 1, allow_short: true, auto_trade_enabled: false, auto_runner_enabled: false, mt5_demo_max_lot: 0.02,
    broker_symbol: "", instrument_key: "", exchange: "NSE_EQ", segment: "EQ", product_type: "MIS", order_variety: "REGULAR", quantity_mode: "FIXED_QTY",
    fixed_quantity: 1, max_quantity: 1, max_order_value: 5000, square_off_time: "15:15", upstox_order_confirmed: false,
    break_even_enabled: false, break_even_trigger_r: 1, trailing_enabled: false, trailing_mode: "ATR_TRAIL", trail_start_r: 1.5, trail_atr_multiplier: 1, partial_exit_enabled: false, partial_exit_at_r: 1, partial_exit_percent: 0.5,
  });

  const selectedBroker = useMemo(() => brokers.find((broker) => broker.id === form.broker_account_id), [brokers, form.broker_account_id]);
  const connectedBrokers = useMemo(() => brokers.filter((broker) => (broker.mode === "DEMO" || broker.mode === "LIVE") && broker.status === "CONNECTED"), [brokers]);
  const isUpstox = (selectedBroker?.broker_name || selectedBroker?.broker_code || "").toUpperCase() === "UPSTOX";
  const isRunning = deploymentStatus === "RUNNING";
  const isPaperDeprecated = form.mode === "PAPER";
  const selectedMasterInstrument = useMemo(() => findSelectedMasterInstrument(form.instrument, marketInstruments), [form.instrument, marketInstruments]);
  const accountMetrics = summary?.metrics || null;
  const accountCurrency = accountMetrics?.account_currency || accountMetrics?.currency || riskPreview?.account_currency || selectedMasterInstrument?.account_currency || (isUpstox || form.instrument_key ? "INR" : "USD");
  const currency = String(accountCurrency || "USD");
  const effectiveCapital = accountMetrics?.effective_capital ?? accountMetrics?.equity ?? accountMetrics?.balance ?? form.capital;
  const effectiveCapitalSource = accountMetrics?.effective_capital_source || (accountMetrics ? "BROKER_SYNC" : "FALLBACK_DEPLOYMENT_CAPITAL");
  const dailyLossOptions = currency === "INR" ? INR_DAILY_LOSS : USD_DAILY_LOSS;
  const selectedBrokerSymbol = useMemo(() => symbolOptions.find((item) => normalizeSymbol(item.symbol) === normalizeSymbol(form.instrument)) || null, [symbolOptions, form.instrument]);
  const instrumentOptions = useMemo(() => buildInstrumentOptions(form.instrument, marketInstruments, symbolOptions), [form.instrument, marketInstruments, symbolOptions]);
  const instrumentReadiness = useMemo(() => buildInstrumentReadiness(form.instrument, selectedMasterInstrument, selectedBrokerSymbol, riskPreview), [form.instrument, selectedMasterInstrument, selectedBrokerSymbol, riskPreview]);
  const instrumentSpec = instrumentReadiness.spec;
  const instrumentStatus = instrumentReadiness.status;
  const normalizedInstrument = normalizeSymbol(form.instrument);
  const liveSlMode = form.sl_mode || "ATR";
  const liveQuantityMode = form.quantity_mode || "FIXED_QTY";
  const selectedMarketCode = normalizeSymbol(selectedMasterInstrument?.market || selectedMasterInstrument?.asset_class || selectedMasterInstrument?.exchange || (isUpstox ? "NSE" : ""));
  const supportsLiveSquareOff = isUpstox || ["NSE", "NSE_EQ", "NSE_FO", "BSE", "INDIAN_EQUITY", "INDIAN_INDEX", "INDIAN_FO", "INDIAN_FUTURES", "INDIAN_OPTIONS"].some((code) => selectedMarketCode.includes(code));
  const brokerLabel = selectedBroker ? `${selectedBroker.broker_code || selectedBroker.broker_name || "Broker"} • ${selectedBroker.account_label || "Account"} • ${selectedBroker.mode || form.mode} • ${selectedBroker.status || "—"} • ${selectedBroker.login_id || selectedBroker.server_name || "—"}` : "Selected broker account";
  const brokerMappingLabel = form.instrument_key && (isUpstox || selectedMarketCode.includes("INDIAN")) ? `Instrument key: ${form.instrument_key}` : `Broker symbol: ${form.broker_symbol || form.instrument}`;

  useEffect(() => {
    const loadSymbols = async () => {
      if ((form.mode !== "DEMO" && form.mode !== "LIVE") || !form.broker_account_id) { setSymbolOptions([]); return; }
      try {
        setLoadingSymbols(true);
        const query = form.instrument ? form.instrument.replace(/m$/i, "").slice(0, 6) : "";
        const rows = await liveTradingApi.listBrokerSymbols(form.broker_account_id, query, 200);
        setSymbolOptions(rows.filter((row) => row?.symbol && row.success !== false));
      } catch { setSymbolOptions([]); } finally { setLoadingSymbols(false); }
    };
    loadSymbols();
  }, [form.mode, form.broker_account_id]);

  useEffect(() => {
    const load = async () => {
      try {
        const [row, brokerRows, instrumentRows, summaryRow, compatRow] = await Promise.all([liveTradingApi.getDeployment(deploymentId), liveTradingApi.listBrokerAccounts(), liveTradingApi.listMarketInstruments(), liveTradingApi.getDeploymentSummary(deploymentId).catch(() => null), liveTradingApi.runCompatibilityCheck(deploymentId).catch(() => null)]);
        setBrokers(brokerRows);
        setMarketInstruments(instrumentRows);
        setDeploymentStatus(row.status);
        setSummary(summaryRow);
        if (compatRow) setCompatibility(compatRow);
        setForm((prev) => ({ ...prev,
          name: row.name, instrument: row.instrument, timeframe: row.timeframe, mode: (row.mode === "LIVE" ? "LIVE" : row.mode === "DEMO" ? "DEMO" : "PAPER"), broker_account_id: row.broker_account_id || "",
          capital: Number(row.capital), risk_per_trade: Number(row.risk_per_trade), rr_ratio: Number(row.rr_ratio), price_risk_pct: Number(row.price_risk_pct),
          max_daily_loss: Number(row.max_daily_loss), max_trades_per_day: Number(row.max_trades_per_day), max_open_positions: Number(row.max_open_positions),
          allow_short: Boolean(row.allow_short), auto_trade_enabled: Boolean(row.auto_trade_enabled), auto_runner_enabled: Boolean(row.auto_runner_enabled), mt5_demo_max_lot: Number(row.mt5_demo_max_lot ?? 0.02),
          broker_symbol: row.broker_symbol || "", instrument_key: row.instrument_key || "", exchange: row.exchange || "NSE_EQ", segment: row.segment || "EQ", product_type: row.product_type || "MIS",
          order_variety: row.order_variety || "REGULAR", quantity_mode: row.quantity_mode || "FIXED_QTY", fixed_quantity: Number(row.fixed_quantity ?? 1), max_quantity: Number(row.max_quantity ?? 1),
          max_order_value: Number(row.max_order_value ?? 5000), square_off_time: row.square_off_time || "15:15", upstox_order_confirmed: Boolean(row.upstox_order_confirmed),
        }));
      } catch (error: any) { showToast(error.message || "Failed to load settings", "error"); } finally { setLoading(false); }
    };
    if (deploymentId) load();
  }, [deploymentId]);

  const runCompatibility = async () => {
    if (!deploymentId) return;
    try {
      setCompatBusy(true);
      const result = await liveTradingApi.runCompatibilityCheck(deploymentId);
      setCompatibility(result);
      showToast(result.summary || "Live compatibility checked", result.status === "FAIL" ? "error" : result.status === "WARNING" ? "warning" : "success");
    } catch (error: any) {
      showToast(error.message || "Compatibility check failed", "error");
    } finally {
      setCompatBusy(false);
    }
  };

  const runtimeConfig = () => ({
    risk: {
      initial_capital: Number(effectiveCapital || form.capital),
      risk_percent: Number(form.risk_per_trade),
      position_size_mode: form.quantity_mode === "RISK_BASED" ? "RISK_BASED" : "FIXED_QUANTITY",
      fixed_quantity: Number(form.fixed_quantity),
      max_lot_cap: form.mt5_demo_max_lot ? Number(form.mt5_demo_max_lot) : null,
      max_quantity_cap: form.max_quantity ? Number(form.max_quantity) : null,
    },
    sl_tp: { rr_ratio: Number(form.rr_ratio), sl_mode: form.sl_mode, atr_period: Number(form.atr_period), atr_multiplier: Number(form.atr_multiplier), swing_lookback: Number(form.swing_lookback), fixed_price_risk_pct: Number(form.price_risk_pct) },
    execution: { entry_mode: "NEXT_CANDLE_OPEN", exit_on_opposite_signal: true, allow_long: true, allow_short: Boolean(form.allow_short), max_trades_per_day: Number(form.max_trades_per_day), max_open_positions: Number(form.max_open_positions), intraday_square_off: supportsLiveSquareOff, square_off_time: form.square_off_time },
    trade_management: { break_even_enabled: form.break_even_enabled, break_even_trigger_r: form.break_even_trigger_r, trailing_enabled: form.trailing_enabled, trailing_mode: form.trailing_mode, trail_start_r: form.trail_start_r, trail_atr_multiplier: form.trail_atr_multiplier, partial_exit_enabled: form.partial_exit_enabled, partial_exit_at_r: form.partial_exit_at_r, partial_exit_percent: form.partial_exit_percent },
    strategy_params: {},
  });

  const updateLiveRuntimeSection = (section: string, key: string, value: any) => {
    if (section === "risk") {
      if (key === "initial_capital") setForm((prev) => ({ ...prev, capital: Number(value) }));
      else if (key === "risk_percent") setForm((prev) => ({ ...prev, risk_per_trade: Number(value) }));
      else if (key === "position_size_mode") setForm((prev) => ({ ...prev, quantity_mode: value === "RISK_BASED" ? "RISK_BASED" : "FIXED_QTY" }));
      else if (key === "fixed_quantity") setForm((prev) => ({ ...prev, fixed_quantity: Number(value || 0) }));
      else if (key === "max_lot_cap") setForm((prev) => ({ ...prev, mt5_demo_max_lot: Number(value || 0) }));
      else if (key === "max_quantity_cap") setForm((prev) => ({ ...prev, max_quantity: Number(value || 0) }));
    } else if (section === "sl_tp") {
      const map: Record<string, keyof FormState> = { rr_ratio: "rr_ratio", sl_mode: "sl_mode", atr_period: "atr_period", atr_multiplier: "atr_multiplier", swing_lookback: "swing_lookback", fixed_price_risk_pct: "price_risk_pct" };
      const target = map[key];
      if (target) setForm((prev) => ({ ...prev, [target]: key === "sl_mode" ? value : Number(value) }));
    } else if (section === "execution") {
      const map: Record<string, keyof FormState> = { allow_short: "allow_short", max_trades_per_day: "max_trades_per_day", max_open_positions: "max_open_positions", square_off_time: "square_off_time" };
      const target = map[key];
      if (target) setForm((prev) => ({ ...prev, [target]: typeof prev[target] === "boolean" ? Boolean(value) : key === "square_off_time" ? value : Number(value || 0) }));
    } else if (section === "trade_management") {
      const map: Record<string, keyof FormState> = { break_even_enabled: "break_even_enabled", break_even_trigger_r: "break_even_trigger_r", trailing_enabled: "trailing_enabled", trailing_mode: "trailing_mode", trail_start_r: "trail_start_r", trail_atr_multiplier: "trail_atr_multiplier", partial_exit_enabled: "partial_exit_enabled", partial_exit_at_r: "partial_exit_at_r", partial_exit_percent: "partial_exit_percent" };
      const target = map[key];
      if (target) setForm((prev) => ({ ...prev, [target]: typeof prev[target] === "boolean" ? Boolean(value) : key === "trailing_mode" ? value : Number(value) }));
    }
  };

  const runPreview = async (mode: "AUTO_LATEST_PRICE" | "MANUAL") => {
    try {
      setPreviewLoading(true);
      const result = await liveTradingApi.previewLiveOrder({
        deployment_id: deploymentId, symbol: form.instrument, side: mode === "MANUAL" ? manualSide : "BUY", mode,
        entry_price: mode === "MANUAL" ? Number(manualEntry) : undefined, stop_loss: mode === "MANUAL" ? Number(manualSL) : undefined, runtime_config: runtimeConfig(),
      });
      setRiskPreview(result as LiveOrderPreview);
      if ((result as LiveOrderPreview).validation_status === "OK") showToast("Order preview passed", "success");
      else showToast((result as LiveOrderPreview).reason || ((result as LiveOrderPreview).missing_fields?.length ? "Instrument not ready" : ((result as LiveOrderPreview).rejected_reason || "Order preview rejected")), "error");
    } catch (error: any) { showToast(error?.message || "Order preview failed", "error"); } finally { setPreviewLoading(false); }
  };

  const validateBeforeSave = () => {
    if (isPaperDeprecated) return "PAPER deployment is deprecated. Please create a DEMO or LIVE broker deployment.";
    if (form.risk_per_trade <= 0 || form.risk_per_trade > 0.10) return "Risk per trade must be greater than 0% and not more than 10%.";
    if (form.risk_per_trade > 0.03) return "Normal UI blocks risk above 3%. Use a lower safe risk value.";
    if (form.rr_ratio <= 0) return "RR ratio must be greater than 0.";
    if (form.price_risk_pct <= 0) return "Fixed price risk percent must be greater than 0.";
    if (form.max_daily_loss < 0) return "Max daily loss cannot be negative.";
    if (form.max_trades_per_day < 1) return "Max trades per day must be at least 1.";
    if (form.max_open_positions < 1) return "Max open positions must be at least 1.";
    if (form.mt5_demo_max_lot <= 0) return "MT5 demo max lot must be greater than 0.";
    if ((form.mode === "DEMO" || form.mode === "LIVE") && !form.broker_account_id) return "Broker account is required for DEMO and LIVE.";
    return null;
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const error = validateBeforeSave();
    if (error) { showToast(error, "error"); return; }
    try {
      setSaving(true);
      if (form.auto_trade_enabled) {
        const compat = await liveTradingApi.runCompatibilityCheck(deploymentId);
        setCompatibility(compat);
        if (compat.status === "FAIL") {
          showToast(compat.summary || "Live compatibility failed. Fix failed checks before enabling Auto Trade.", "error");
          return;
        }
      }
      await liveTradingApi.updateDeployment(deploymentId, {
        name: form.name,
        risk_per_trade: form.risk_per_trade, rr_ratio: form.rr_ratio, price_risk_pct: form.price_risk_pct, max_daily_loss: form.max_daily_loss,
        max_trades_per_day: form.max_trades_per_day, max_open_positions: form.max_open_positions, allow_short: form.allow_short, auto_trade_enabled: form.auto_trade_enabled,
        auto_runner_enabled: form.auto_runner_enabled, mt5_demo_max_lot: form.mt5_demo_max_lot,
        product_type: form.product_type, order_variety: form.order_variety, quantity_mode: form.quantity_mode, fixed_quantity: form.fixed_quantity,
        max_quantity: form.max_quantity, max_order_value: form.max_order_value, square_off_time: form.square_off_time, upstox_order_confirmed: form.upstox_order_confirmed,
      });
      showToast("Deployment settings updated", "success");
      router.push(`/live-trading/${deploymentId}`);
    } catch (error: any) { showToast(error.message || "Failed to update settings", "error"); } finally { setSaving(false); }
  };

  const LockedNote = () => <div className="rounded-xl border border-cyan-300/25 bg-cyan-400/10 p-4 text-sm text-cyan-100"><Lock className="mr-2 inline h-4 w-4" />Mode, broker account, instrument, and timeframe are locked after deployment creation to keep approval, sync, candle storage, and execution routing safe. Create a new deployment to change them. {isRunning && <span className="ml-1 text-amber-100">This deployment is RUNNING, so additional runtime changes may also be guarded by backend safety.</span>} <Link className="ml-2 underline" href={`/live-trading/new?clone=${deploymentId}`}><Copy className="mr-1 inline h-4 w-4" />Clone Deployment</Link></div>;

  return (
    <PageShell>
      <PageHeader title="Safe Deployment Settings" subtitle="Beginner-safe presets, guarded risk settings, and automatic order preview before auto trading." actions={<Link href={`/live-trading/${deploymentId}`}><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link>} />
      <GlassCard className="p-6" hoverEffect={false}>
        {loading ? <p className="text-purple-100">Loading settings...</p> : (
          <form onSubmit={submit} className="space-y-6">
            <LiveCompatibilityCard result={compatibility} loading={compatBusy} onRun={runCompatibility} compact />
            <LockedNote />
            {isPaperDeprecated && <div className="rounded-xl border border-amber-300/25 bg-amber-400/10 p-4 text-sm text-amber-100"><ShieldCheck className="mr-2 inline h-4 w-4" />PAPER deployment is deprecated. Settings are read-only for broker-only workflow. <Link className="ml-2 underline" href="/live-trading/new">Create Broker Deployment</Link></div>}
            <div className="rounded-xl border border-lime-300/20 bg-lime-300/10 p-4 text-sm text-lime-100"><ShieldCheck className="mr-2 inline h-4 w-4" />Beginner Safe Mode is ON by default. DEMO and LIVE use approved connected broker accounts. Risk is calculated from broker balance/equity.</div>

            <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-5 text-sm text-cyan-50">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"><div><h3 className="text-base font-black text-white">Auto Order Preview</h3><p className="mt-1 text-xs text-cyan-100">Uses latest closed candle, selected SL mode, RR, Instrument Master, and risk engine. No real order is placed.</p></div><Button type="button" disabled={previewLoading} onClick={() => runPreview("AUTO_LATEST_PRICE")} className="border-0 bg-cyan-400 text-slate-950 hover:bg-cyan-300">{previewLoading ? "Previewing..." : "Auto Preview from Latest Price"}</Button></div>
              {riskPreview && <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
                <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Status</p><p className={riskPreview.validation_status === "OK" ? "font-bold text-lime-200" : "font-bold text-rose-200"}>{riskPreview.validation_status || "—"}</p></div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Latest Price</p><p className="font-bold text-white">{riskPreview.latest_price ?? riskPreview.entry_price ?? "—"}</p></div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">SL / TP</p><p className="font-bold text-white">{riskPreview.stop_loss ?? "—"} / {riskPreview.target ?? "—"}</p></div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Risk</p><p className="font-bold text-white">{money(riskPreview.actual_risk_amount ?? riskPreview.risk_amount, riskPreview.account_currency || currency)}</p></div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Reward</p><p className="font-bold text-white">{riskPreview.expected_reward_amount != null ? money(riskPreview.expected_reward_amount, riskPreview.account_currency || currency) : "—"}</p></div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Lot / Qty</p><p className="font-bold text-white">{riskPreview.quantity_mode === "LOTS" ? `${riskPreview.final_lot_size ?? "—"} lots` : `${riskPreview.final_quantity ?? "—"} qty`}</p></div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Broker Symbol</p><p className="truncate font-bold text-white">{riskPreview.broker_symbol || (riskPreview.broker_order_payload_preview as any)?.symbol || "—"}</p></div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Payload</p><p className="truncate font-bold text-white">{riskPreview.quantity_mode === "LOTS" ? `volume=${(riskPreview.broker_order_payload_preview as any)?.volume ?? "—"}` : `qty=${(riskPreview.broker_order_payload_preview as any)?.quantity ?? "—"}`}</p></div>
              </div>}
              {riskPreview?.validation_status === "REJECTED" && <div className="mt-3 rounded-xl border border-rose-300/20 bg-rose-500/10 p-3 text-rose-100"><p className="font-bold">{riskPreview.reason || "Instrument not ready"}</p><p className="mt-1 text-xs">{riskPreview.instrument_not_ready_message || riskPreview.rejected_reason || "Review the Instrument Readiness card below before previewing again."}</p></div>}
              <button type="button" onClick={() => setAdvancedPreview((v) => !v)} className="mt-4 text-xs font-bold text-cyan-100 underline">{advancedPreview ? "Hide" : "Show"} Advanced Manual Preview</button>
              {advancedPreview && <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4"><FieldShell label="Side"><SelectBox value={manualSide} onChange={(e) => setManualSide(e.target.value as "BUY" | "SELL")}><option value="BUY">BUY</option><option value="SELL">SELL</option></SelectBox></FieldShell><FieldShell label="Manual Entry"><InputBox type="number" step="0.01" value={manualEntry} onChange={(e) => setManualEntry(Number(e.target.value))} /></FieldShell><FieldShell label="Manual Stop Loss"><InputBox type="number" step="0.01" value={manualSL} onChange={(e) => setManualSL(Number(e.target.value))} /></FieldShell><Button type="button" disabled={previewLoading} onClick={() => runPreview("MANUAL")} className="mt-7 bg-white/10 text-white hover:bg-white/20">Preview Manual</Button></div>}
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div><h3 className="font-black text-white">Instrument Readiness</h3><p className="mt-1 text-xs text-purple-200">Use this card to confirm the symbol is saved and complete in Market Master before DEMO/LIVE trading.</p></div>
                <Link href="/admin/market-data" className="text-xs font-bold text-cyan-100 underline">Open Market Master</Link>
              </div>
              {instrumentReadiness.fallbackNotice && <p className="mt-3 rounded-xl border border-amber-300/20 bg-amber-400/10 p-3 text-xs text-amber-100">{instrumentReadiness.fallbackNotice}</p>}
              <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8 text-sm">
                <Info label="Instrument" value={form.instrument} />
                <Info label="Source" value={instrumentReadiness.source} />
                <Info label="Instrument ID" value={displayValue(instrumentSpec.id)} />
                <Info label="Asset Class" value={displayValue(instrumentSpec.asset_class)} />
                <Info label="Account Currency" value={displayValue(instrumentSpec.account_currency)} />
                <Info label="Currency Symbol" value={displayValue(instrumentSpec.currency_symbol)} />
                <Info label="Qty Mode" value={displayValue(instrumentSpec.quantity_mode)} />
                <Info label="Broker Symbol" value={displayValue(instrumentSpec.broker_symbol)} />
                <Info label="Tick Size" value={displayValue(instrumentSpec.tick_size)} />
                <Info label="Tick Value / Lot" value={displayValue(instrumentSpec.tick_value_per_lot)} />
                <Info label="Lot Step / Min Lot" value={`${displayValue(instrumentSpec.lot_step)} / ${displayValue(instrumentSpec.min_lot)}`} />
                <Info label="Qty Step / Min Qty" value={normalizeSymbol(instrumentSpec.quantity_mode) === "LOTS" ? "N/A for LOTS" : `${displayValue(instrumentSpec.quantity_step)} / ${displayValue(instrumentSpec.min_quantity)}`} />
                <Info label="Live Enabled" value={yesNo(instrumentSpec.is_tradeable_live)} />
                <Info label="Status" value={instrumentStatus} />
              </div>
              {instrumentReadiness.missingFields.length > 0 && <div className="mt-4 rounded-xl border border-rose-300/20 bg-rose-500/10 p-4 text-sm text-rose-100"><p className="font-bold">Missing / invalid Market Master fields</p><div className="mt-2 flex flex-wrap gap-2">{instrumentReadiness.missingFields.map((field) => <span key={field} className="rounded-full bg-rose-400/15 px-2 py-1 text-xs">{field}</span>)}</div><p className="mt-3 text-xs">{instrumentReadiness.actionMessage}</p></div>}
            </div>

            <div className="rounded-2xl border border-emerald-300/20 bg-emerald-400/10 p-5">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="font-black text-white">Broker Account Capital</h3>
                  <p className="mt-1 text-xs text-emerald-100/80">Read-only balance/equity from broker sync. Risk is calculated from broker balance/equity where available.</p>
                </div>
                <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-xs font-semibold text-emerald-100">{effectiveCapitalSource || "Waiting for sync"}</span>
              </div>
              {accountMetrics ? <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
                <Info label="Currency" value={String(accountMetrics.account_currency || accountMetrics.currency || currency || "USD")} />
                <Info label="Balance" value={money(accountMetrics.balance, currency)} />
                <Info label="Equity" value={money(accountMetrics.equity, currency)} />
                <Info label="Free Margin" value={money(accountMetrics.free_margin, currency)} />
                <Info label="Effective Capital" value={money(effectiveCapital, currency)} />
                <Info label="Capital Source" value={String(effectiveCapitalSource || "—").replace(/_/g, " ")} />
              </div> : <p className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-emerald-50">Broker balance/equity will appear after broker sync.</p>}
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-5"><div className="flex items-center justify-between gap-3"><div><h3 className="font-black text-white">Beginner Safe Mode</h3><p className="text-xs text-purple-200">Safe dropdowns prevent invalid values. Advanced custom inputs stay collapsed.</p></div><Button type="button" variant="outline" onClick={() => setAdvancedMode((v) => !v)} className="border-white/10 bg-white/5 text-white hover:bg-white/10">{advancedMode ? "Hide Advanced" : "Advanced Mode"}</Button></div>
              <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
                <FieldShell label="Name"><InputBox value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></FieldShell>
                <FieldShell label="Mode" hint={isPaperDeprecated ? "PAPER deployment is deprecated. Create a broker deployment instead." : "Mode is locked after deployment creation. Create a new deployment to use another mode."}><SelectBox disabled value={form.mode}>{isPaperDeprecated && <option value="PAPER">PAPER Deprecated</option>}<option value="DEMO">DEMO / Broker</option><option value="LIVE">LIVE / Broker</option></SelectBox></FieldShell>
                <FieldShell label="Broker Account" hint="Broker account is locked after deployment creation to keep approval, sync, and risk routing safe."><SelectBox disabled value={form.broker_account_id}><option value={form.broker_account_id}>{brokerLabel}</option>{connectedBrokers.filter((broker) => broker.id !== form.broker_account_id).map((broker) => <option key={broker.id} value={broker.id}>{broker.broker_code || broker.broker_name} • {broker.account_label} • {broker.mode} • {broker.status} • {broker.login_id || broker.server_name || "—"}</option>)}</SelectBox></FieldShell>
                <FieldShell label="Instrument" hint="Instrument is locked after deployment creation. Create a new deployment to trade another instrument."><SelectBox disabled value={normalizeSymbol(form.instrument)}>{instrumentOptions.length ? instrumentOptions.map((option) => <option key={option.key} value={option.value}>{option.label}</option>) : <option value={normalizeSymbol(form.instrument)}>{loadingSymbols ? "Loading symbols..." : (form.instrument || "Selected symbol")}</option>}</SelectBox><p className="mt-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-purple-100">{brokerMappingLabel}</p></FieldShell>
                <FieldShell label="Timeframe" hint="Timeframe is locked after creation because live candles are stored per deployment timeframe."><SelectBox disabled value={form.timeframe}>{[...new Set([form.timeframe, ...(isUpstox ? UPSTOX_TIMEFRAME_OPTIONS : TIMEFRAME_OPTIONS)])].filter(Boolean).map((tf) => <option key={tf} value={tf}>{tf}</option>)}</SelectBox></FieldShell>
                <FieldShell label="Risk per Trade" hint={form.risk_per_trade > 0.02 ? "Warning: above 2% is aggressive." : "Default recommended: 1%."}><SelectBox value={selectValue(form.risk_per_trade, RISK_OPTIONS)} onChange={(e) => e.target.value !== "CUSTOM" ? setForm({ ...form, risk_per_trade: Number(e.target.value) }) : setAdvancedMode(true)}>{RISK_OPTIONS.map((value) => <option key={value} value={value}>{percent(value)}</option>)}<option value="CUSTOM">Custom Advanced</option></SelectBox>{advancedMode && selectValue(form.risk_per_trade, RISK_OPTIONS) === "CUSTOM" && <InputBox type="number" step="0.001" max="0.10" value={form.risk_per_trade} onChange={(e) => setForm({ ...form, risk_per_trade: Number(e.target.value) })} />}</FieldShell>
                <FieldShell label="RR Ratio"><SelectBox value={form.rr_ratio} onChange={(e) => setForm({ ...form, rr_ratio: Number(e.target.value) })}>{RR_OPTIONS.map((value) => <option key={value} value={value}>1:{value}</option>)}</SelectBox></FieldShell>
                <FieldShell label="SL Mode"><SelectBox value={liveSlMode} onChange={(e) => setForm({ ...form, sl_mode: e.target.value })}>{SL_MODES.map((value) => <option key={value} value={value}>{value.replace(/_/g, " ")}</option>)}</SelectBox></FieldShell>
                <FieldShell label="Max Daily Loss"><SelectBox value={selectValue(form.max_daily_loss, dailyLossOptions)} onChange={(e) => e.target.value !== "CUSTOM" ? setForm({ ...form, max_daily_loss: Number(e.target.value) }) : setAdvancedMode(true)}>{dailyLossOptions.map((value) => <option key={value} value={value}>{money(value, currency)}</option>)}<option value="CUSTOM">Custom</option></SelectBox>{advancedMode && selectValue(form.max_daily_loss, dailyLossOptions) === "CUSTOM" && <InputBox type="number" min="0" value={form.max_daily_loss} onChange={(e) => setForm({ ...form, max_daily_loss: Number(e.target.value) })} />}</FieldShell>
                <FieldShell label="Max Trades / Day"><SelectBox value={form.max_trades_per_day} onChange={(e) => setForm({ ...form, max_trades_per_day: Number(e.target.value) })}>{MAX_TRADES.map((value) => <option key={value} value={value}>{value}</option>)}</SelectBox></FieldShell>
                <FieldShell label="MT5 DEMO Max Lot"><SelectBox value={selectValue(form.mt5_demo_max_lot, MT5_LOT_CAPS)} onChange={(e) => e.target.value !== "CUSTOM" ? setForm({ ...form, mt5_demo_max_lot: Number(e.target.value) }) : setAdvancedMode(true)}>{MT5_LOT_CAPS.map((value) => <option key={value} value={value}>{value.toFixed(2)}</option>)}<option value="CUSTOM">Custom Advanced</option></SelectBox>{advancedMode && selectValue(form.mt5_demo_max_lot, MT5_LOT_CAPS) === "CUSTOM" && <InputBox type="number" step="0.01" min="0.01" value={form.mt5_demo_max_lot} onChange={(e) => setForm({ ...form, mt5_demo_max_lot: Number(e.target.value) })} />}</FieldShell>
              </div>
            </div>

            {advancedMode && <div className="rounded-2xl border border-purple-300/20 bg-purple-500/10 p-5">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="font-black text-white">Unified Runtime Settings</h3>
                  <p className="mt-1 text-xs text-purple-100/80">Same runtime tabs, conditional fields and help tooltips as Backtest. Live-only broker and safety caps remain protected.</p>
                </div>
                <div className="flex flex-wrap gap-2">{RUNTIME_TABS.map((tab) => <button key={tab.value} type="button" onClick={() => setLiveRuntimeTab(tab.value)} className={`rounded-xl border px-3 py-2 text-xs font-medium transition ${liveRuntimeTab === tab.value ? "border-primary/60 bg-primary/20 text-primary-foreground" : "border-white/10 bg-white/5 text-purple-100 hover:bg-white/10"}`}>{tab.label}</button>)}</div>
              </div>
              <div className="mt-5">
                <RuntimeSettingsForm
                  activeTab={liveRuntimeTab}
                  config={runtimeConfig() as any}
                  updateSection={updateLiveRuntimeSection as any}
                  currency={currency}
                  instrumentSymbol={normalizedInstrument || "this instrument"}
                  supportsIntradaySquareOff={supportsLiveSquareOff}
                  mode="live"
                />
              </div>
              {supportsLiveSquareOff && <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
                {isUpstox && <><FieldShell label="Upstox Instrument Key"><InputBox disabled value={form.instrument_key} placeholder="NSE_EQ|INE040A01034" /></FieldShell><FieldShell label="Exchange"><InputBox disabled value={form.exchange} /></FieldShell><FieldShell label="Segment"><InputBox disabled value={form.segment} /></FieldShell></>}
                <FieldShell label="Product Type"><SelectBox value={form.product_type} onChange={(e) => setForm({ ...form, product_type: e.target.value })}><option value="MIS">MIS / Intraday</option><option value="CNC">CNC / Delivery</option></SelectBox></FieldShell>
              </div>}
              <div className="mt-4 rounded-xl border border-amber-300/20 bg-amber-500/10 p-3 text-xs text-amber-100">Live safety remains enforced by broker readiness, MT5_DEMO_MAX_LOT, max lot/quantity caps and daily loss guardrails. Runtime UI cannot bypass backend caps.</div>
            </div>}

            <div className="flex flex-wrap gap-4 rounded-xl border border-white/10 bg-white/5 p-4"><label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.allow_short} onChange={(e) => setForm({ ...form, allow_short: e.target.checked })} />Allow short</label><label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.auto_trade_enabled} onChange={(e) => setForm({ ...form, auto_trade_enabled: e.target.checked })} />Auto trade enabled</label><label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.auto_runner_enabled} onChange={(e) => setForm({ ...form, auto_runner_enabled: e.target.checked })} />Auto runner enabled</label>{isUpstox && <label className="flex items-center gap-2 text-sm text-yellow-100"><input type="checkbox" checked={form.upstox_order_confirmed} onChange={(e) => setForm({ ...form, upstox_order_confirmed: e.target.checked })} />I understand Upstox orders may place real trades</label>}</div>
            <Button disabled={saving || isPaperDeprecated} className="border-0 bg-gradient-to-r from-lime-400 to-emerald-500 text-slate-950 hover:from-lime-300 hover:to-emerald-400">{isPaperDeprecated ? "Create Broker Deployment Instead" : saving ? "Saving..." : "Save Settings"}</Button>
          </form>
        )}
      </GlassCard>
    </PageShell>
  );
}

function Info({ label, value }: { label: string; value: ReactNode }) {
  return <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-purple-200">{label}</p><p className="truncate font-bold text-white">{value || "—"}</p></div>;
}
