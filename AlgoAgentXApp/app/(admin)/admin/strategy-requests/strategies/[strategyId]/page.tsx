"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, Code2, GitCompareArrows, History, Play, RotateCcw, Save, ShieldCheck, UploadCloud } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";

import {
  adminApi,
  type ImplementedStrategy,
  type AdminStrategySandboxResult,
  type StrategyPreset,
  type StrategyRuntimePreset,
  type StrategyVersion,
  type StrategyWorkflowStatus,
} from "@/lib/api/admin";
import { backtestsApi } from "@/lib/api/backtests";
import { FieldHelpTooltip } from "@/components/common/FieldHelpTooltip";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";


const RUNTIME_FIELD_HELP: Record<string, string> = {"Initial Capital": "Starting capital used in this runtime preset. It affects backtest sizing, equity curve and drawdown calculations.", "Risk Percent": "Percentage of capital risked per trade for risk-based sizing. Example: 1% means 0.01 in config. High risk can create large drawdowns.", "Position Size Mode": "Risk Based calculates size from stop loss and risk percent. Fixed Lot/Quantity uses a manual size.", "Max Lot Cap": "Maximum allowed lot size to prevent oversized trades.", "Fixed Lot": "Manual lot size used for every trade in this preset. High fixed lots can create unrealistic risk.", "Fixed Quantity": "Manual quantity used for non-lot instruments.", "Max Quantity Cap": "Maximum quantity cap for non-lot instruments.", "SL Mode": "Defines how stop loss is calculated: Fixed Percent, ATR volatility, recent swing, or strategy suggested.", "RR Ratio": "Reward-to-risk ratio. Example: 2 means target is twice the stop loss distance.", "ATR Period": "Number of candles used to calculate Average True Range. Higher values smooth the volatility estimate.", "ATR Multiplier": "Multiplier applied to ATR for stop distance. Higher multiplier means wider stop.", "Swing Lookback": "Number of candles used to find recent swing high/low for stop placement.", "Fixed Price Risk %": "Stop loss distance as a fixed percent of entry price.", "Entry Mode": "Controls when trade enters after signal. Next Candle Open is safer for realistic backtests.", "Max Open Positions": "Limits simultaneous open positions.", "Max Trades Per Day": "Limits daily trade count to reduce overtrading.", "Square Off Time": "Time used to close intraday Indian-market positions.", "Break Even Trigger R": "Profit multiple required before stop loss moves to entry.", "Trailing Mode": "Method used to trail stop. ATR trail uses volatility.", "Trail Start R": "Profit multiple after which trailing starts.", "Trail ATR Multiplier": "ATR multiplier used for trailing stop distance.", "Partial Exit At R": "R multiple where partial exit happens.", "Partial Exit Percent": "Percent of position closed during partial exit."};

function HelpLabel({ label, help }: { label: string; help?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {label}
      <FieldHelpTooltip label={`${label} help`} content={help || RUNTIME_FIELD_HELP[label] || "Runtime setting. Changing this may affect sizing, entries, exits, risk, and strategy behavior."} />
    </span>
  );
}

const fieldClass =
  "w-full rounded-xl border border-border/60 bg-card/25 px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";

const safeNumber = (value: unknown, fallback = 0): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const formatCurrency = (value: number | null | undefined): string =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(safeNumber(value, 0));

const formatPercent = (value: number | null | undefined): string => `${safeNumber(value, 0).toFixed(2)}%`;

const formatDateTime = (value?: string | null) => {
  if (!value) return "—";
  const dt = new Date(value);
  return Number.isNaN(dt.getTime()) ? value : dt.toLocaleString();
};

const strategyToForm = (strategy: ImplementedStrategy) => {
  const params = strategy.parameters || {};
  return {
    name: strategy.name || "",
    description: strategy.description || "",
    visibility: (strategy.visibility || "PRIVATE").toUpperCase(),
    strategy_type: strategy.strategyType || strategy.strategy_type || "",
    market: strategy.market || "",
    timeframe: strategy.timeframe || "",
    entry_rules: strategy.entry_rules || "",
    exit_rules: strategy.exit_rules || "",
    confirmation_rules: strategy.confirmation_rules || "",
    risk_rules: strategy.risk_rules || "",
    invalidation_rules: strategy.invalidation_rules || "",
    trade_management_rules: strategy.trade_management_rules || "",
    notes: strategy.notes || "",
    source_code: strategy.sourceCode || strategy.source_code || "",
    rr_ratio: String(params.rr_ratio ?? 2),
    capital_risk_pct: String(params.capital_risk_pct ?? 0.01),
    price_risk_pct: String(params.price_risk_pct ?? 0.002),
    max_bars_in_trade: String(params.max_bars_in_trade ?? 6),
  };
};

const calcChangedLines = (currentText: string, oldText: string) => {
  const current = currentText.split("\n");
  const old = oldText.split("\n");
  let changed = 0;
  const max = Math.max(current.length, old.length);
  for (let i = 0; i < max; i += 1) {
    if ((current[i] || "") !== (old[i] || "")) changed += 1;
  }
  return changed;
};

const recommendPresetKey = (timeframe: string, strategyType: string) => {
  const tf = String(timeframe || '').toLowerCase();
  const st = String(strategyType || '').toLowerCase();
  if (tf.includes('5m') || tf.includes('1m') || st.includes('scalp')) return 'scalp_tight_risk';
  if (tf.includes('15m') || tf.includes('30m') || st.includes('intraday') || st.includes('momentum')) return 'intraday_momentum';
  if (tf.includes('1h') || tf.includes('4h') || tf.includes('1d') || st.includes('swing')) return 'swing_rr4';
  return '';
};


const DEFAULT_RUNTIME_PRESET_CONFIG: Record<string, any> = {
  risk: {
    initial_capital: 100000,
    risk_percent: 0.01,
    position_size_mode: "RISK_BASED",
    fixed_lot: null,
    fixed_quantity: null,
    max_lot_cap: null,
    max_quantity_cap: null,
  },
  sl_tp: {
    sl_mode: "ATR",
    rr_ratio: 2,
    atr_period: 14,
    atr_multiplier: 1.5,
    swing_lookback: 5,
    fixed_price_risk_pct: 0.002,
  },
  execution: {
    entry_mode: "NEXT_CANDLE_OPEN",
    exit_on_opposite_signal: true,
    allow_long: true,
    allow_short: true,
    max_trades_per_day: null,
    max_open_positions: 1,
    intraday_square_off: false,
    square_off_time: "15:15",
  },
  trade_management: {
    break_even_enabled: false,
    break_even_trigger_r: 1,
    break_even_offset_points: 0,
    trailing_enabled: false,
    trailing_mode: "ATR_TRAIL",
    trail_start_r: 1.5,
    trail_atr_multiplier: 1,
    partial_exit_enabled: false,
    partial_exit_at_r: 1,
    partial_exit_percent: 0.5,
  },
  strategy_params: {},
};

const RUNTIME_PRESET_TEMPLATES: Record<string, { description: string; config: Record<string, any> }> = {
  Conservative: {
    description: "Lower risk preset with wider ATR stop and breakeven protection.",
    config: {
      risk: { risk_percent: 0.005, position_size_mode: "RISK_BASED" },
      sl_tp: { sl_mode: "ATR", rr_ratio: 2, atr_multiplier: 2, atr_period: 14 },
      trade_management: { break_even_enabled: true, break_even_trigger_r: 1, trailing_enabled: false },
    },
  },
  Balanced: {
    description: "Balanced default preset for normal backtesting.",
    config: {
      risk: { risk_percent: 0.01, position_size_mode: "RISK_BASED" },
      sl_tp: { sl_mode: "ATR", rr_ratio: 2, atr_multiplier: 1.5, atr_period: 14 },
      trade_management: { break_even_enabled: false, trailing_enabled: false },
    },
  },
  Aggressive: {
    description: "Higher risk and reward preset for advanced testing.",
    config: {
      risk: { risk_percent: 0.02, position_size_mode: "RISK_BASED" },
      sl_tp: { sl_mode: "SWING", rr_ratio: 3, swing_lookback: 5 },
      trade_management: { break_even_enabled: false, trailing_enabled: true, trail_start_r: 1.5, trailing_mode: "ATR_TRAIL" },
    },
  },
};

const runtimeDeepMerge = (base: any, override: any): Record<string, any> => {
  const output = { ...(base || {}) };
  Object.entries(override || {}).forEach(([key, value]) => {
    if (value && typeof value === "object" && !Array.isArray(value) && output[key] && typeof output[key] === "object" && !Array.isArray(output[key])) {
      output[key] = runtimeDeepMerge(output[key], value);
    } else {
      output[key] = value;
    }
  });
  return output;
};

const normalizePresetConfigForForm = (config: any): Record<string, any> => runtimeDeepMerge(DEFAULT_RUNTIME_PRESET_CONFIG, config || {});

const getConfigValue = (config: any, path: string, fallback: any = "") => {
  const value = path.split(".").reduce((acc: any, key) => (acc == null ? undefined : acc[key]), config);
  return value ?? fallback;
};

const setConfigValue = (config: any, path: string, value: any): Record<string, any> => {
  const next = JSON.parse(JSON.stringify(config || {}));
  const keys = path.split(".");
  let cursor = next;
  keys.slice(0, -1).forEach((key) => {
    if (!cursor[key] || typeof cursor[key] !== "object") cursor[key] = {};
    cursor = cursor[key];
  });
  cursor[keys[keys.length - 1]] = value;
  return next;
};

const parsePresetJson = (value: string): { ok: boolean; config: Record<string, any>; error?: string } => {
  try {
    return { ok: true, config: normalizePresetConfigForForm(JSON.parse(value || "{}")) };
  } catch (error: any) {
    return { ok: false, config: normalizePresetConfigForForm({}), error: error?.message || "Invalid JSON" };
  }
};

const presetSummary = (preset: StrategyRuntimePreset) => {
  const cfg = normalizePresetConfigForForm(preset.config_json || preset.configJson || {});
  return {
    risk: `${(safeNumber(cfg.risk?.risk_percent, 0) * 100).toFixed(2)}%`,
    sl: cfg.sl_tp?.sl_mode === "ATR" ? `ATR × ${cfg.sl_tp?.atr_multiplier ?? "—"}` : String(cfg.sl_tp?.sl_mode || "—"),
    rr: `1:${cfg.sl_tp?.rr_ratio ?? "—"}`,
    position: String(cfg.risk?.position_size_mode || "RISK_BASED").replaceAll("_", " "),
    be: cfg.trade_management?.break_even_enabled ? `On @ ${cfg.trade_management?.break_even_trigger_r ?? 1}R` : "Off",
    trail: cfg.trade_management?.trailing_enabled ? String(cfg.trade_management?.trailing_mode || "ATR_TRAIL").replaceAll("_", " ") : "Off",
  };
};

const validatePresetFormConfig = (config: any, meta: { name: string; advancedJsonError?: string | null }) => {
  const errors: string[] = [];
  const warnings: string[] = [];
  const risk = config.risk || {};
  const sltp = config.sl_tp || {};
  const execution = config.execution || {};
  const tm = config.trade_management || {};
  if (!meta.name.trim()) errors.push("Preset name is required.");
  if (meta.advancedJsonError) errors.push(`Advanced JSON is invalid: ${meta.advancedJsonError}`);
  const riskPercent = safeNumber(risk.risk_percent, 0);
  if (riskPercent <= 0 || riskPercent > 0.10) errors.push("Risk percent must be between 0 and 10%.");
  if (riskPercent > 0.03) warnings.push("Risk percent above 3% is high. Use only for advanced testing.");
  if (risk.position_size_mode === "FIXED_LOT" && safeNumber(risk.fixed_lot, 0) <= 0) errors.push("Fixed lot is required when position size mode is FIXED_LOT.");
  if (risk.position_size_mode === "FIXED_QUANTITY" && safeNumber(risk.fixed_quantity, 0) <= 0) errors.push("Fixed quantity is required when position size mode is FIXED_QUANTITY.");
  if (safeNumber(sltp.rr_ratio, 0) <= 0) errors.push("RR ratio must be greater than zero.");
  if ((sltp.sl_mode || "ATR") === "ATR" && safeNumber(sltp.atr_period, 0) <= 0) errors.push("ATR period must be greater than zero.");
  if ((sltp.sl_mode || "ATR") === "ATR" && safeNumber(sltp.atr_multiplier, 0) <= 0) errors.push("ATR multiplier must be greater than zero.");
  if ((sltp.sl_mode || "ATR") === "SWING" && safeNumber(sltp.swing_lookback, 0) <= 0) errors.push("Swing lookback must be greater than zero.");
  if ((sltp.sl_mode || "ATR") === "FIXED_PERCENT" && safeNumber(sltp.fixed_price_risk_pct, 0) <= 0) errors.push("Fixed price risk % must be greater than zero.");
  if (safeNumber(execution.max_open_positions, 0) < 1) errors.push("Max open positions must be at least 1.");
  if (execution.max_trades_per_day !== null && execution.max_trades_per_day !== "" && safeNumber(execution.max_trades_per_day, 0) < 1) errors.push("Max trades per day must be empty or at least 1.");
  if (!/^\d{2}:\d{2}$/.test(String(execution.square_off_time || "15:15"))) errors.push("Square off time must use HH:mm format.");
  if (tm.break_even_enabled && safeNumber(tm.break_even_trigger_r, 0) <= 0) errors.push("Breakeven trigger R must be greater than zero.");
  if (tm.trailing_enabled && safeNumber(tm.trail_start_r, 0) <= 0) errors.push("Trail start R must be greater than zero.");
  const partialPercent = safeNumber(tm.partial_exit_percent, 0);
  if (tm.partial_exit_enabled && (partialPercent <= 0 || partialPercent > 100)) errors.push("Partial exit percent must be between 1 and 100 when enabled.");
  return { errors, warnings };
};

export default function AdminStrategyWorkspacePage() {
  const params = useParams<{ strategyId: string }>();
  const strategyId = params?.strategyId as string;

  const [strategy, setStrategy] = useState<ImplementedStrategy | null>(null);
  const [form, setForm] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [sandboxing, setSandboxing] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [sandboxResult, setSandboxResult] = useState<AdminStrategySandboxResult | null>(null);
  const [catalog, setCatalog] = useState<Array<{ id: number; symbol: string }>>([]);
  const [versions, setVersions] = useState<StrategyVersion[]>([]);
  const [workflow, setWorkflow] = useState<StrategyWorkflowStatus | null>(null);
  const [presets, setPresets] = useState<StrategyPreset[]>([]);
  const [runtimePresets, setRuntimePresets] = useState<StrategyRuntimePreset[]>([]);
  const [runtimePresetForm, setRuntimePresetForm] = useState({
    name: "Balanced",
    description: "Balanced default runtime preset",
    risk_label: "Balanced",
    config_json: JSON.stringify(normalizePresetConfigForForm(RUNTIME_PRESET_TEMPLATES.Balanced.config), null, 2),
    is_active: true,
    is_default: false,
  });
  const [editingRuntimePresetId, setEditingRuntimePresetId] = useState<string | null>(null);
  const [showAdvancedRuntimeJson, setShowAdvancedRuntimeJson] = useState(false);
  const [allowAdvancedRuntimeJsonEdit, setAllowAdvancedRuntimeJsonEdit] = useState(false);
  const [runtimePresetSaving, setRuntimePresetSaving] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<string>("");
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");
  const [sandboxInput, setSandboxInput] = useState({ instrument_id: 1, timeframe: "5m", start_date: "2025-12-24", end_date: "2025-12-26", capital: 100000 });

  const load = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [strategyData, instrumentsResponse, versionsResponse, presetResponse, runtimePresetResponse] = await Promise.all([
        adminApi.getAdminStrategyById(strategyId),
        backtestsApi.getInstruments(),
        adminApi.listAdminStrategyVersions(strategyId),
        adminApi.listAdminStrategyPresets(),
        adminApi.listStrategyRuntimePresets(strategyId),
      ]);
      const instruments = Array.isArray(instrumentsResponse) ? instrumentsResponse : [];
      setCatalog(instruments.map((item: any) => ({ id: Number(item.id), symbol: item.symbol || item.name || `#${item.id}` })));
      setStrategy(strategyData);
      setForm(strategyToForm(strategyData));
      setVersions(versionsResponse.items || []);
      setWorkflow(versionsResponse.workflow || strategyData.workflow || null);
      setPresets(presetResponse.items || []);
      setRuntimePresets(runtimePresetResponse.items || []);
      if (versionsResponse.items?.[0]?.version_id) setSelectedVersionId((prev) => prev || versionsResponse.items[0].version_id);
      if (instruments[0]?.id) {
        setSandboxInput((prev) => ({ ...prev, instrument_id: Number(instruments[0].id) }));
      }
    } catch (error: any) {
      const message = error?.message || "Failed to load strategy workspace";
      setLoadError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [strategyId]);

  const equityRows = useMemo(
    () => (sandboxResult?.equity_curve || []).map((point, index) => ({ label: point.timestamp ? new Date(point.timestamp).toLocaleDateString() : String(index + 1), equity: safeNumber(point.equity, 0) })),
    [sandboxResult?.equity_curve],
  );

  const selectedVersion = useMemo(() => versions.find((item) => item.version_id === selectedVersionId) || null, [versions, selectedVersionId]);
  const selectedVersionSource = String(selectedVersion?.payload?.source_code || "");
  const currentSource = String(form?.source_code || "");
  const changedLines = useMemo(() => calcChangedLines(currentSource, selectedVersionSource), [currentSource, selectedVersionSource]);
  const recommendedPresetKey = useMemo(() => recommendPresetKey(String(sandboxInput.timeframe || form?.timeframe || ''), String(form?.strategy_type || '')), [sandboxInput.timeframe, form?.timeframe, form?.strategy_type]);
  const recommendedPreset = useMemo(() => presets.find((item) => item.key === recommendedPresetKey) || null, [presets, recommendedPresetKey]);
  const runtimePresetJsonState = useMemo(() => parsePresetJson(runtimePresetForm.config_json), [runtimePresetForm.config_json]);
  const runtimePresetConfig = runtimePresetJsonState.config;
  const runtimePresetValidation = useMemo(() => validatePresetFormConfig(runtimePresetConfig, { name: runtimePresetForm.name, advancedJsonError: runtimePresetJsonState.ok ? null : runtimePresetJsonState.error }), [runtimePresetConfig, runtimePresetForm.name, runtimePresetJsonState.ok, runtimePresetJsonState.error]);
  const runtimeConfigSchema = useMemo(() => ((strategy as any)?.runtime_config_schema || (strategy as any)?.runtimeConfigSchema || {}) as Record<string, any>, [strategy]);
  const strategyParamSchema = useMemo(() => (runtimeConfigSchema?.strategy_params || {}) as Record<string, any>, [runtimeConfigSchema]);

  useEffect(() => {
    if (recommendedPresetKey && !selectedPreset) setSelectedPreset(recommendedPresetKey);
  }, [recommendedPresetKey, selectedPreset]);

  const refreshWorkflowAndVersions = async () => {
    try {
      const [strategyData, versionsResponse] = await Promise.all([
        adminApi.getAdminStrategyById(strategyId),
        adminApi.listAdminStrategyVersions(strategyId),
      ]);
      setStrategy(strategyData);
      setForm(strategyToForm(strategyData));
      setVersions(versionsResponse.items || []);
      setWorkflow(versionsResponse.workflow || strategyData.workflow || null);
      if (versionsResponse.items?.[0]?.version_id) setSelectedVersionId((prev) => prev || versionsResponse.items[0].version_id);
    } catch {
      // noop
    }
  };

  const saveStrategy = async () => {
    if (!form) return;
    if (!window.confirm("Save updated strategy code and configuration?")) return;
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        description: form.description,
        visibility: form.visibility,
        strategy_type: form.strategy_type,
        market: form.market,
        timeframe: form.timeframe,
        entry_rules: form.entry_rules,
        exit_rules: form.exit_rules,
        confirmation_rules: form.confirmation_rules,
        risk_rules: form.risk_rules,
        invalidation_rules: form.invalidation_rules,
        trade_management_rules: form.trade_management_rules,
        notes: form.notes,
        source_code: form.source_code,
        parameters: {
          rr_ratio: safeNumber(form.rr_ratio, 2),
          capital_risk_pct: safeNumber(form.capital_risk_pct, 0.01),
          price_risk_pct: safeNumber(form.price_risk_pct, 0.002),
          max_bars_in_trade: safeNumber(form.max_bars_in_trade, 6),
        },
      };
      const updated = await adminApi.updateAdminStrategyById(strategyId, payload);
      setStrategy(updated);
      setForm(strategyToForm(updated));
      toast.success("Strategy saved successfully");
      await refreshWorkflowAndVersions();
    } catch (error: any) {
      toast.error(error?.message || "Failed to save strategy");
    } finally {
      setSaving(false);
    }
  };

  const verifyCode = async () => {
    setVerifying(true);
    try {
      const res = await adminApi.validateAdminStrategyById(strategyId, sandboxInput);
      if (res.validation_ok) toast.success(res.message || "Validation passed");
      else toast.error(res.message || "Validation failed");
      await refreshWorkflowAndVersions();
    } catch (error: any) {
      toast.error(error?.message || "Validation failed");
    } finally {
      setVerifying(false);
    }
  };

  const runSandbox = async () => {
    setSandboxing(true);
    try {
      const res = await adminApi.runAdminStrategySandboxBacktest(strategyId, sandboxInput);
      setSandboxResult(res);
      toast.success("Sandbox backtest completed");
      await refreshWorkflowAndVersions();
    } catch (error: any) {
      toast.error(error?.message || "Sandbox backtest failed");
    } finally {
      setSandboxing(false);
    }
  };

  const applyPreset = () => {
    const preset = presets.find((item) => item.key === selectedPreset);
    if (!preset) return;
    setForm((prev: any) => ({
      ...prev,
      rr_ratio: String(preset.config.rr_ratio ?? prev.rr_ratio),
      capital_risk_pct: String(preset.config.capital_risk_pct ?? prev.capital_risk_pct),
      price_risk_pct: String(preset.config.price_risk_pct ?? prev.price_risk_pct),
      max_bars_in_trade: String(preset.config.max_bars_in_trade ?? prev.max_bars_in_trade),
    }));
    toast.success(`${preset.name} preset applied`);
  };

  const rollbackVersion = async () => {
    if (!selectedVersion) return;
    if (!window.confirm(`Rollback to version captured on ${formatDateTime(selectedVersion.captured_at)}?`)) return;
    try {
      const updated = await adminApi.rollbackAdminStrategyVersion(strategyId, selectedVersion.version_id);
      setStrategy(updated);
      setForm(strategyToForm(updated));
      toast.success("Rolled back successfully");
      await refreshWorkflowAndVersions();
    } catch (error: any) {
      toast.error(error?.message || "Rollback failed");
    }
  };

  const publishStrategy = async () => {
    setPublishing(true);
    try {
      const updated = await adminApi.publishAdminStrategyById(strategyId);
      setStrategy(updated);
      setForm(strategyToForm(updated));
      toast.success("Strategy published successfully");
      await refreshWorkflowAndVersions();
    } catch (error: any) {
      toast.error(error?.message || "Publish blocked");
    } finally {
      setPublishing(false);
    }
  };

  const unpublishStrategy = async () => {
    setPublishing(true);
    try {
      const updated = await adminApi.unpublishAdminStrategyById(strategyId);
      setStrategy(updated);
      setForm(strategyToForm(updated));
      toast.success("Strategy moved to private");
      await refreshWorkflowAndVersions();
    } catch (error: any) {
      toast.error(error?.message || "Unpublish failed");
    } finally {
      setPublishing(false);
    }
  };

  const refreshRuntimePresets = async () => {
    try {
      const response = await adminApi.listStrategyRuntimePresets(strategyId);
      setRuntimePresets(response.items || []);
    } catch (error: any) {
      toast.error(error?.message || "Failed to refresh runtime presets");
    }
  };

  const updateRuntimePresetConfig = (path: string, value: any) => {
    const next = setConfigValue(runtimePresetConfig, path, value);
    setRuntimePresetForm((prev) => ({ ...prev, config_json: JSON.stringify(next, null, 2) }));
  };

  const resetRuntimePresetForm = (kind: "Conservative" | "Balanced" | "Aggressive" = "Balanced") => {
    const template = RUNTIME_PRESET_TEMPLATES[kind];
    setEditingRuntimePresetId(null);
    setAllowAdvancedRuntimeJsonEdit(false);
    setShowAdvancedRuntimeJson(false);
    setRuntimePresetForm({
      name: kind,
      description: template.description,
      risk_label: kind,
      config_json: JSON.stringify(normalizePresetConfigForForm(template.config), null, 2),
      is_active: true,
      is_default: kind === "Balanced",
    });
  };

  const saveRuntimePreset = async () => {
    const validation = validatePresetFormConfig(runtimePresetConfig, { name: runtimePresetForm.name, advancedJsonError: runtimePresetJsonState.ok ? null : runtimePresetJsonState.error });
    if (validation.errors.length) {
      toast.error(validation.errors[0]);
      return;
    }
    setRuntimePresetSaving(true);
    try {
      const payload = {
        name: runtimePresetForm.name.trim(),
        description: runtimePresetForm.description,
        risk_label: runtimePresetForm.risk_label,
        config_json: runtimePresetConfig,
        is_default: runtimePresetForm.is_default,
        is_active: runtimePresetForm.is_active,
      };
      if (editingRuntimePresetId) {
        await adminApi.updateStrategyRuntimePreset(editingRuntimePresetId, payload);
        toast.success("Runtime preset updated");
      } else {
        await adminApi.createStrategyRuntimePreset(strategyId, payload);
        toast.success("Runtime preset created");
      }
      resetRuntimePresetForm("Balanced");
      await refreshRuntimePresets();
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      const message = detail?.message || detail?.errors?.[0] || error?.message || "Failed to save runtime preset";
      toast.error(message);
    } finally {
      setRuntimePresetSaving(false);
    }
  };

  const loadRuntimePresetForEdit = (preset: StrategyRuntimePreset) => {
    setEditingRuntimePresetId(preset.id);
    setShowAdvancedRuntimeJson(false);
    setAllowAdvancedRuntimeJsonEdit(false);
    setRuntimePresetForm({
      name: preset.name || "Preset",
      description: preset.description || "",
      risk_label: preset.risk_label || preset.riskLabel || "",
      config_json: JSON.stringify(normalizePresetConfigForForm(preset.config_json || preset.configJson || {}), null, 2),
      is_active: Boolean(preset.is_active ?? preset.isActive ?? true),
      is_default: Boolean(preset.is_default ?? preset.isDefault ?? false),
    });
  };

  const createExampleRuntimePreset = (kind: "Conservative" | "Balanced" | "Aggressive") => {
    resetRuntimePresetForm(kind);
    toast.success(`${kind} template loaded. Review fields and click Save Preset.`);
  };

  const makeRuntimePresetDefault = async (presetId: string) => {
    try {
      await adminApi.makeStrategyRuntimePresetDefault(presetId);
      toast.success("Default preset updated");
      await refreshRuntimePresets();
    } catch (error: any) {
      toast.error(error?.message || "Failed to mark default");
    }
  };

  const toggleRuntimePresetActive = async (preset: StrategyRuntimePreset) => {
    try {
      await adminApi.updateStrategyRuntimePreset(preset.id, { is_active: !(preset.is_active ?? preset.isActive) });
      toast.success("Runtime preset updated");
      await refreshRuntimePresets();
    } catch (error: any) {
      toast.error(error?.message || "Failed to update preset");
    }
  };

  const updateDeploymentGate = async (payload: { is_deployable_paper?: boolean; is_deployable_demo?: boolean; is_live_approved?: boolean; reason?: string }) => {
    try {
      const updated = await adminApi.updateAdminStrategyDeploymentGate(strategyId, payload);
      setStrategy(updated);
      setForm(strategyToForm(updated));
      toast.success("Deployment gate updated");
      await refreshWorkflowAndVersions();
    } catch (error: any) {
      toast.error(error?.message || "Failed to update deployment gate");
    }
  };

  if (loading) {
    return <div className="h-72 animate-pulse rounded-xl bg-card/30" />;
  }

  if (!form) {
    return (
      <div className="space-y-4">
        <PageHeader title="Strategy Workspace" subtitle={loadError || "Unable to load this strategy workspace."} />
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardContent className="flex flex-col gap-3 p-6">
            <p className="text-sm text-muted-foreground">The workspace could not be opened. Go back to the strategy library and retry.</p>
            <div>
              <Button variant="outline" className="rounded-xl" asChild><Link href="/admin/strategy-requests"><ArrowLeft className="mr-2 h-4 w-4" />Back to Library</Link></Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Strategy Workspace · ${strategy?.name || "Strategy"}`}
        subtitle="IDE-style admin flow: save versions, compare changes, rollback safely, and publish only after validation + sandbox pass."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" className="rounded-xl" asChild>
              <Link href="/admin/strategy-requests"><ArrowLeft className="mr-2 h-4 w-4" />Back to Library</Link>
            </Button>
            <Button variant="outline" className="rounded-xl" asChild><Link href="/admin/backtest-engine"><Code2 className="mr-2 h-4 w-4" />Engine Workspace</Link></Button>
            <Button variant="outline" onClick={() => void verifyCode()} disabled={verifying} className="rounded-xl"><ShieldCheck className="mr-2 h-4 w-4" />{verifying ? "Verifying..." : "Verify Code"}</Button>
            {String(form.visibility).toUpperCase() === "PUBLIC" ? (
              <Button variant="outline" onClick={() => void unpublishStrategy()} disabled={publishing} className="rounded-xl">{publishing ? "Updating..." : "Unpublish"}</Button>
            ) : (
              <Button variant="outline" onClick={() => void publishStrategy()} disabled={publishing} className="rounded-xl"><UploadCloud className="mr-2 h-4 w-4" />{publishing ? "Publishing..." : "Publish"}</Button>
            )}
            <Button onClick={() => void saveStrategy()} disabled={saving} className="rounded-xl bg-primary text-primary-foreground"><Save className="mr-2 h-4 w-4" />{saving ? "Saving..." : "Save Strategy"}</Button>
          </div>
        }
      />

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle className="text-base">Workflow Gate</CardTitle><CardDescription>Publish is allowed only after the latest source/config passes verify and sandbox.</CardDescription></CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 text-sm">
            {[
              ["Validation", workflow?.validation?.ok, workflow?.validation?.checked_at, workflow?.validation?.message],
              ["Sandbox", workflow?.sandbox?.ok, workflow?.sandbox?.checked_at, workflow?.sandbox?.message],
            ].map(([label, ok, checkedAt, message]) => (
              <div key={String(label)} className="rounded-xl border border-border/50 bg-card/20 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium text-foreground">{String(label)}</p>
                  <span className={`rounded-full px-2 py-1 text-xs ${ok ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"}`}>{ok ? "PASS" : "PENDING"}</span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">{message || "No run yet"}</p>
                <p className="mt-1 text-xs text-muted-foreground">{formatDateTime(String(checkedAt || ""))}</p>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="rounded-xl border border-lime-400/30 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle className="flex items-center gap-2 text-base"><ShieldCheck className="h-4 w-4 text-lime-300" />Deployment Gate</CardTitle><CardDescription>Control which published strategies are allowed for PAPER and MT5 DEMO deployment.</CardDescription></CardHeader>
          <CardContent className="space-y-3 text-sm">
            {[
              ["Verify Status", strategy?.verifiedAt || strategy?.verified_at ? "PASS" : "PENDING", strategy?.verifiedAt || strategy?.verified_at],
              ["Sandbox Status", strategy?.sandboxPassedAt || strategy?.sandbox_passed_at ? "PASS" : "PENDING", strategy?.sandboxPassedAt || strategy?.sandbox_passed_at],
              ["Paper Deployment", strategy?.isDeployablePaper || strategy?.is_deployable_paper ? "ENABLED" : "DISABLED", strategy?.paperEnabledAt || strategy?.paper_enabled_at],
              ["Demo Deployment", strategy?.isDeployableDemo || strategy?.is_deployable_demo ? "ENABLED" : "DISABLED", strategy?.demoEnabledAt || strategy?.demo_enabled_at],
              ["Live", strategy?.isLiveApproved || strategy?.is_live_approved ? "APPROVED (still locked globally)" : "LOCKED", strategy?.liveApprovedAt || strategy?.live_approved_at],
            ].map(([label, state, at]) => (
              <div key={String(label)} className="flex items-center justify-between gap-3 rounded-xl border border-border/50 bg-card/20 p-3">
                <div><p className="font-medium text-foreground">{String(label)}</p><p className="text-xs text-muted-foreground">{formatDateTime(String(at || ""))}</p></div>
                <span className={`rounded-full px-2 py-1 text-xs ${String(state).includes("ENABLED") || String(state) === "PASS" ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"}`}>{String(state)}</span>
              </div>
            ))}
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <Button variant="outline" className="rounded-xl" onClick={() => void updateDeploymentGate({ is_deployable_paper: true, reason: "Admin enabled PAPER deployment" })}>Enable Paper</Button>
              <Button variant="outline" className="rounded-xl" onClick={() => void updateDeploymentGate({ is_deployable_paper: false, reason: "Admin disabled PAPER deployment" })}>Disable Paper</Button>
              <Button variant="outline" className="rounded-xl" onClick={() => void updateDeploymentGate({ is_deployable_demo: true, reason: "Admin enabled MT5 DEMO deployment" })}>Enable Demo</Button>
              <Button variant="outline" className="rounded-xl" onClick={() => void updateDeploymentGate({ is_deployable_demo: false, reason: "Admin disabled MT5 DEMO deployment" })}>Disable Demo</Button>
              <Button variant="outline" className="rounded-xl" onClick={() => void updateDeploymentGate({ is_live_approved: true, reason: "Admin marked live approved but global live execution remains blocked" })}>Mark Live Approved</Button>
              <Button variant="outline" className="rounded-xl" onClick={() => void updateDeploymentGate({ is_live_approved: false, reason: "Admin locked live deployment" })}>Lock Live</Button>
            </div>
            <p className="text-xs text-muted-foreground">LIVE trading remains globally blocked even if this strategy is marked live approved.</p>
          </CardContent>
        </Card>


        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle className="text-base">Strategy Config Presets</CardTitle><CardDescription>Quick-start engine settings for common trading styles.</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            <select className={fieldClass} value={selectedPreset} onChange={(e)=>setSelectedPreset(e.target.value)}>
              <option value="">Select preset</option>
              {presets.map((preset) => <option key={preset.key} value={preset.key}>{preset.name}</option>)}
            </select>
            <Button variant="outline" className="rounded-xl" onClick={applyPreset} disabled={!selectedPreset}><CheckCircle2 className="mr-2 h-4 w-4" />Apply Preset</Button>
            <div className="rounded-xl border border-border/50 bg-card/20 p-3 text-xs text-muted-foreground">
              {selectedPreset ? JSON.stringify(presets.find((preset) => preset.key === selectedPreset)?.config || {}, null, 2) : "Pick a preset to preview RR, capital risk, price risk, and holding rules."}
            </div>
            <p className="text-xs text-muted-foreground">Recommended profile: <span className="text-foreground">{recommendedPreset?.name || 'Manual custom config'}</span>. Timeframe helps pick a starting risk style, but you can still override RR, risk %, and holding bars per strategy.</p>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle className="flex items-center gap-2 text-base"><History className="h-4 w-4" />Version History</CardTitle><CardDescription>Each save creates a rollback point for source code and strategy config.</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            <select className={fieldClass} value={selectedVersionId} onChange={(e)=>setSelectedVersionId(e.target.value)}>
              <option value="">Select version</option>
              {versions.map((version) => <option key={version.version_id} value={version.version_id}>{formatDateTime(version.captured_at)} · {version.reason || "save"}</option>)}
            </select>
            <div className="flex gap-2">
              <Button variant="outline" className="rounded-xl" onClick={rollbackVersion} disabled={!selectedVersion}><RotateCcw className="mr-2 h-4 w-4" />Rollback</Button>
              <div className="rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-xs text-muted-foreground">Changed lines vs selected: <span className="text-foreground">{selectedVersion ? changedLines : 0}</span></div>
            </div>
          </CardContent>
        </Card>
      </section>


      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="rounded-xl border border-primary/30 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader>
            <CardTitle>Runtime Presets</CardTitle>
            <CardDescription>Admin-managed defaults and presets shown in the user Backtest Runtime Settings drawer.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {(["Conservative", "Balanced", "Aggressive"] as const).map((kind) => (
                <Button key={kind} variant="outline" disabled={runtimePresetSaving} className="rounded-xl" onClick={() => createExampleRuntimePreset(kind)}>Load {kind} Form</Button>
              ))}
            </div>
            <div className="space-y-3">
              {runtimePresets.length ? runtimePresets.map((preset) => {
                const summary = presetSummary(preset);
                return (
                  <div key={preset.id} className="rounded-xl border border-border/50 bg-card/20 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-semibold text-foreground">{preset.name}</p>
                          {(preset.is_default || preset.isDefault) && <span className="rounded-full bg-primary/20 px-2 py-1 text-xs text-primary-foreground">Default</span>}
                          <span className={`rounded-full px-2 py-1 text-xs ${(preset.is_active ?? preset.isActive) ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"}`}>{(preset.is_active ?? preset.isActive) ? "Active" : "Inactive"}</span>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">{preset.description || "No description"}</p>
                        <p className="mt-1 text-xs text-muted-foreground">Risk label: {preset.risk_label || preset.riskLabel || "—"}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button variant="outline" className="rounded-xl" onClick={() => loadRuntimePresetForEdit(preset)}>Edit Form</Button>
                        <Button variant="outline" className="rounded-xl" onClick={() => { loadRuntimePresetForEdit(preset); setShowAdvancedRuntimeJson(true); }}>Preview JSON</Button>
                        <Button variant="outline" className="rounded-xl" disabled={Boolean(preset.is_default || preset.isDefault)} onClick={() => void makeRuntimePresetDefault(preset.id)}>Make Default</Button>
                        <Button variant="outline" className="rounded-xl" onClick={() => void toggleRuntimePresetActive(preset)}>{(preset.is_active ?? preset.isActive) ? "Deactivate" : "Activate"}</Button>
                      </div>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs md:grid-cols-3">
                      {[
                        ["Risk", summary.risk],
                        ["SL", summary.sl],
                        ["RR", summary.rr],
                        ["Position", summary.position],
                        ["BE", summary.be],
                        ["Trail", summary.trail],
                      ].map(([label, value]) => (
                        <div key={label} className="rounded-lg border border-border/40 bg-black/10 p-2">
                          <p className="text-muted-foreground">{label}</p>
                          <p className="mt-1 font-medium text-foreground">{value}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              }) : (
                <div className="rounded-xl border border-dashed border-border/50 p-5 text-sm text-muted-foreground">No runtime presets yet. Load Conservative, Balanced, or Aggressive, review the form, then save to expose preset choices to users.</div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader>
            <CardTitle>{editingRuntimePresetId ? "Edit Runtime Preset" : "Create Runtime Preset"}</CardTitle>
            <CardDescription>Use clean form controls. AlgoAgentX generates valid runtime config JSON in the background.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="mb-3 text-sm font-semibold text-foreground">Preset Info</p>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <input className={fieldClass} value={runtimePresetForm.name} onChange={(e)=>setRuntimePresetForm((p)=>({...p,name:e.target.value}))} placeholder="Preset name" />
                <input className={fieldClass} value={runtimePresetForm.risk_label} onChange={(e)=>setRuntimePresetForm((p)=>({...p,risk_label:e.target.value}))} placeholder="Risk label" />
              </div>
              <input className={`${fieldClass} mt-4`} value={runtimePresetForm.description} onChange={(e)=>setRuntimePresetForm((p)=>({...p,description:e.target.value}))} placeholder="Description" />
              <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                <label className="flex items-center gap-2"><input type="checkbox" checked={runtimePresetForm.is_active} onChange={(e)=>setRuntimePresetForm((p)=>({...p,is_active:e.target.checked}))} /> Active</label>
                <label className="flex items-center gap-2"><input type="checkbox" checked={runtimePresetForm.is_default} onChange={(e)=>setRuntimePresetForm((p)=>({...p,is_default:e.target.checked}))} /> Mark as default</label>
              </div>
            </div>

            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="mb-3 text-sm font-semibold text-foreground">Risk Settings</p>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Initial Capital" /></p><input className={fieldClass} type="number" value={getConfigValue(runtimePresetConfig,"risk.initial_capital",100000)} onChange={(e)=>updateRuntimePresetConfig("risk.initial_capital", Number(e.target.value))} /></div>
                {getConfigValue(runtimePresetConfig,"risk.position_size_mode","RISK_BASED") === "RISK_BASED" && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Risk Percent" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"risk.risk_percent",0.01)} onChange={(e)=>updateRuntimePresetConfig("risk.risk_percent", Number(e.target.value))}>{[0.0025,0.005,0.01,0.015,0.02,0.03,0.05].map((v)=><option key={v} value={v}>{(v*100).toFixed(2)}%</option>)}</select></div>}
                <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Position Size Mode" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"risk.position_size_mode","RISK_BASED")} onChange={(e)=>updateRuntimePresetConfig("risk.position_size_mode", e.target.value)}><option value="RISK_BASED">Risk Based</option><option value="FIXED_LOT">Fixed Lot</option><option value="FIXED_QUANTITY">Fixed Quantity</option></select></div>
                {getConfigValue(runtimePresetConfig,"risk.position_size_mode","RISK_BASED") !== "FIXED_QUANTITY" && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Max Lot Cap" /></p><input className={fieldClass} type="number" value={getConfigValue(runtimePresetConfig,"risk.max_lot_cap","") ?? ""} onChange={(e)=>updateRuntimePresetConfig("risk.max_lot_cap", e.target.value === "" ? null : Number(e.target.value))} /></div>}
                {getConfigValue(runtimePresetConfig,"risk.position_size_mode") === "FIXED_LOT" && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Fixed Lot" /></p><input className={fieldClass} type="number" step="0.01" value={getConfigValue(runtimePresetConfig,"risk.fixed_lot","") ?? ""} onChange={(e)=>updateRuntimePresetConfig("risk.fixed_lot", e.target.value === "" ? null : Number(e.target.value))} /></div>}
                {getConfigValue(runtimePresetConfig,"risk.position_size_mode") === "FIXED_QUANTITY" && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Fixed Quantity" /></p><input className={fieldClass} type="number" value={getConfigValue(runtimePresetConfig,"risk.fixed_quantity","") ?? ""} onChange={(e)=>updateRuntimePresetConfig("risk.fixed_quantity", e.target.value === "" ? null : Number(e.target.value))} /></div>}
                {getConfigValue(runtimePresetConfig,"risk.position_size_mode") === "FIXED_QUANTITY" && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Max Quantity Cap" /></p><input className={fieldClass} type="number" value={getConfigValue(runtimePresetConfig,"risk.max_quantity_cap","") ?? ""} onChange={(e)=>updateRuntimePresetConfig("risk.max_quantity_cap", e.target.value === "" ? null : Number(e.target.value))} /></div>}
              </div>
            </div>

            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="mb-3 text-sm font-semibold text-foreground">SL / TP Settings</p>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="SL Mode" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"sl_tp.sl_mode","ATR")} onChange={(e)=>updateRuntimePresetConfig("sl_tp.sl_mode", e.target.value)}><option value="ATR">ATR</option><option value="SWING">Swing</option><option value="FIXED_PERCENT">Fixed Percent</option><option value="STRATEGY_SUGGESTED">Strategy Suggested</option></select></div>
                <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="RR Ratio" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"sl_tp.rr_ratio",2)} onChange={(e)=>updateRuntimePresetConfig("sl_tp.rr_ratio", Number(e.target.value))}>{[1,1.5,2,3,4,5].map((v)=><option key={v} value={v}>{v}</option>)}</select></div>
                {getConfigValue(runtimePresetConfig,"sl_tp.sl_mode","ATR") === "ATR" && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="ATR Period" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"sl_tp.atr_period",14)} onChange={(e)=>updateRuntimePresetConfig("sl_tp.atr_period", Number(e.target.value))}>{[7,10,14,20,21,50].map((v)=><option key={v} value={v}>{v}</option>)}</select></div>}
                {getConfigValue(runtimePresetConfig,"sl_tp.sl_mode","ATR") === "ATR" && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="ATR Multiplier" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"sl_tp.atr_multiplier",1.5)} onChange={(e)=>updateRuntimePresetConfig("sl_tp.atr_multiplier", Number(e.target.value))}>{[1,1.5,2,2.5,3].map((v)=><option key={v} value={v}>{v}</option>)}</select></div>}
                {getConfigValue(runtimePresetConfig,"sl_tp.sl_mode","ATR") === "SWING" && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Swing Lookback" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"sl_tp.swing_lookback",5)} onChange={(e)=>updateRuntimePresetConfig("sl_tp.swing_lookback", Number(e.target.value))}>{[3,5,10,20].map((v)=><option key={v} value={v}>{v}</option>)}</select></div>}
                {getConfigValue(runtimePresetConfig,"sl_tp.sl_mode","ATR") === "FIXED_PERCENT" && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Fixed Price Risk %" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"sl_tp.fixed_price_risk_pct",0.002)} onChange={(e)=>updateRuntimePresetConfig("sl_tp.fixed_price_risk_pct", Number(e.target.value))}>{[0.001,0.002,0.005,0.01,0.02].map((v)=><option key={v} value={v}>{(v*100).toFixed(2)}%</option>)}</select></div>}
                {getConfigValue(runtimePresetConfig,"sl_tp.sl_mode","ATR") === "STRATEGY_SUGGESTED" && <div className="rounded-xl border border-border/50 bg-card/30 p-3 text-sm text-muted-foreground md:col-span-2">Strategy Suggested mode keeps old ATR, swing and fixed values saved but hides them from this preset form.</div>}
              </div>
            </div>

            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="mb-3 text-sm font-semibold text-foreground">Execution Settings</p>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Entry Mode" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"execution.entry_mode","NEXT_CANDLE_OPEN")} onChange={(e)=>updateRuntimePresetConfig("execution.entry_mode", e.target.value)}><option value="NEXT_CANDLE_OPEN">Next Candle Open</option></select></div>
                <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Max Open Positions" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"execution.max_open_positions",1)} onChange={(e)=>updateRuntimePresetConfig("execution.max_open_positions", Number(e.target.value))}>{[1,2,3,5].map((v)=><option key={v} value={v}>{v}</option>)}</select></div>
                <label className="flex items-center gap-2 text-sm text-muted-foreground"><input type="checkbox" checked={Boolean(getConfigValue(runtimePresetConfig,"execution.exit_on_opposite_signal",true))} onChange={(e)=>updateRuntimePresetConfig("execution.exit_on_opposite_signal", e.target.checked)} /> <HelpLabel label="Exit on opposite signal" /></label>
                <label className="flex items-center gap-2 text-sm text-muted-foreground"><input type="checkbox" checked={Boolean(getConfigValue(runtimePresetConfig,"execution.allow_long",true))} onChange={(e)=>updateRuntimePresetConfig("execution.allow_long", e.target.checked)} /> <HelpLabel label="Allow Long" /></label>
                <label className="flex items-center gap-2 text-sm text-muted-foreground"><input type="checkbox" checked={Boolean(getConfigValue(runtimePresetConfig,"execution.allow_short",true))} onChange={(e)=>updateRuntimePresetConfig("execution.allow_short", e.target.checked)} /> <HelpLabel label="Allow Short" /></label>
                <label className="flex items-center gap-2 text-sm text-muted-foreground"><input type="checkbox" checked={Boolean(getConfigValue(runtimePresetConfig,"execution.intraday_square_off",false))} onChange={(e)=>updateRuntimePresetConfig("execution.intraday_square_off", e.target.checked)} /> <HelpLabel label="Intraday Square Off" /></label>
                <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Max Trades Per Day" /></p><input className={fieldClass} type="number" value={getConfigValue(runtimePresetConfig,"execution.max_trades_per_day","") ?? ""} onChange={(e)=>updateRuntimePresetConfig("execution.max_trades_per_day", e.target.value === "" ? null : Number(e.target.value))} /></div>
                <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Square Off Time" /></p><input className={fieldClass} type="time" value={getConfigValue(runtimePresetConfig,"execution.square_off_time","15:15")} onChange={(e)=>updateRuntimePresetConfig("execution.square_off_time", e.target.value)} /></div>
              </div>
            </div>

            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="mb-3 text-sm font-semibold text-foreground">Trade Management</p>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="flex items-center gap-2 text-sm text-muted-foreground"><input type="checkbox" checked={Boolean(getConfigValue(runtimePresetConfig,"trade_management.break_even_enabled",false))} onChange={(e)=>updateRuntimePresetConfig("trade_management.break_even_enabled", e.target.checked)} /> <HelpLabel label="Break Even Enabled" /></label>
                {Boolean(getConfigValue(runtimePresetConfig,"trade_management.break_even_enabled",false)) && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Break Even Trigger R" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"trade_management.break_even_trigger_r",1)} onChange={(e)=>updateRuntimePresetConfig("trade_management.break_even_trigger_r", Number(e.target.value))}>{[0.5,1,1.5,2].map((v)=><option key={v} value={v}>{v}</option>)}</select></div>}
                <label className="flex items-center gap-2 text-sm text-muted-foreground"><input type="checkbox" checked={Boolean(getConfigValue(runtimePresetConfig,"trade_management.trailing_enabled",false))} onChange={(e)=>updateRuntimePresetConfig("trade_management.trailing_enabled", e.target.checked)} /> <HelpLabel label="Trailing Enabled" /></label>
                {Boolean(getConfigValue(runtimePresetConfig,"trade_management.trailing_enabled",false)) && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Trailing Mode" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"trade_management.trailing_mode","ATR_TRAIL")} onChange={(e)=>updateRuntimePresetConfig("trade_management.trailing_mode", e.target.value)}><option value="ATR_TRAIL">ATR Trail</option><option value="EMA20_TRAIL">EMA20 Trail</option><option value="SWING_TRAIL">Swing Trail</option></select></div>}
                {Boolean(getConfigValue(runtimePresetConfig,"trade_management.trailing_enabled",false)) && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Trail Start R" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"trade_management.trail_start_r",1.5)} onChange={(e)=>updateRuntimePresetConfig("trade_management.trail_start_r", Number(e.target.value))}>{[1,1.5,2,3].map((v)=><option key={v} value={v}>{v}</option>)}</select></div>}
                {Boolean(getConfigValue(runtimePresetConfig,"trade_management.trailing_enabled",false)) && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Trail ATR Multiplier" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"trade_management.trail_atr_multiplier",1)} onChange={(e)=>updateRuntimePresetConfig("trade_management.trail_atr_multiplier", Number(e.target.value))}>{[1,1.5,2,2.5,3].map((v)=><option key={v} value={v}>{v}</option>)}</select></div>}
                <label className="flex items-center gap-2 text-sm text-muted-foreground"><input type="checkbox" checked={Boolean(getConfigValue(runtimePresetConfig,"trade_management.partial_exit_enabled",false))} onChange={(e)=>updateRuntimePresetConfig("trade_management.partial_exit_enabled", e.target.checked)} /> <HelpLabel label="Partial Exit Enabled" /></label>
                {Boolean(getConfigValue(runtimePresetConfig,"trade_management.partial_exit_enabled",false)) && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Partial Exit At R" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"trade_management.partial_exit_at_r",1)} onChange={(e)=>updateRuntimePresetConfig("trade_management.partial_exit_at_r", Number(e.target.value))}>{[0.5,1,1.5,2].map((v)=><option key={v} value={v}>{v}</option>)}</select></div>}
                {Boolean(getConfigValue(runtimePresetConfig,"trade_management.partial_exit_enabled",false)) && <div><p className="mb-2 text-xs text-muted-foreground"><HelpLabel label="Partial Exit Percent" /></p><select className={fieldClass} value={getConfigValue(runtimePresetConfig,"trade_management.partial_exit_percent",0.5)} onChange={(e)=>updateRuntimePresetConfig("trade_management.partial_exit_percent", Number(e.target.value))}>{[[0.25,"25%"],[0.5,"50%"],[0.75,"75%"]].map(([v,label])=><option key={String(v)} value={Number(v)}>{label}</option>)}</select></div>}
              </div>
            </div>

            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="mb-3 text-sm font-semibold text-foreground">Strategy Params</p>
              {Object.keys(strategyParamSchema).length ? (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {Object.entries(strategyParamSchema).map(([key, schema]: any) => {
                    const fieldType = schema?.type || "text";
                    const label = schema?.label || key;
                    const value = getConfigValue(runtimePresetConfig, `strategy_params.${key}`, schema?.default ?? "");
                    if (fieldType === "boolean") {
                      return <label key={key} className="flex items-center gap-2 text-sm text-muted-foreground"><input type="checkbox" checked={Boolean(value)} onChange={(e)=>updateRuntimePresetConfig(`strategy_params.${key}`, e.target.checked)} /> {label}</label>;
                    }
                    if (fieldType === "select" && Array.isArray(schema?.options)) {
                      return <div key={key}><p className="mb-2 text-xs text-muted-foreground">{label}</p><select className={fieldClass} value={value} onChange={(e)=>updateRuntimePresetConfig(`strategy_params.${key}`, e.target.value)}>{schema.options.map((option: any)=><option key={String(option.value ?? option)} value={option.value ?? option}>{option.label ?? option.value ?? option}</option>)}</select></div>;
                    }
                    return <div key={key}><p className="mb-2 text-xs text-muted-foreground">{label}</p><input className={fieldClass} type={fieldType === "number" ? "number" : "text"} value={value} min={schema?.min} max={schema?.max} onChange={(e)=>updateRuntimePresetConfig(`strategy_params.${key}`, fieldType === "number" ? Number(e.target.value) : e.target.value)} /></div>;
                  })}
                </div>
              ) : <p className="text-sm text-muted-foreground">No dynamic strategy params are defined for this strategy schema.</p>}
            </div>

            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-foreground">Generated Runtime Config JSON</p>
                  <p className="text-xs text-muted-foreground">Readonly preview by default. Advanced raw editing is hidden for safety.</p>
                </div>
                <Button variant="outline" className="rounded-xl" onClick={()=>setShowAdvancedRuntimeJson((v)=>!v)}>{showAdvancedRuntimeJson ? "Hide JSON" : "Preview JSON"}</Button>
              </div>
              {showAdvancedRuntimeJson && (
                <div className="mt-4 space-y-3">
                  <textarea readOnly={!allowAdvancedRuntimeJsonEdit} className={`${fieldClass} min-h-[220px] font-mono text-xs ${allowAdvancedRuntimeJsonEdit ? "" : "opacity-80"}`} value={runtimePresetForm.config_json} onChange={(e)=>setRuntimePresetForm((p)=>({...p,config_json:e.target.value}))} />
                  {!allowAdvancedRuntimeJsonEdit ? <Button variant="outline" className="rounded-xl" onClick={()=>setAllowAdvancedRuntimeJsonEdit(true)}>I understand advanced JSON editing</Button> : <p className="text-xs text-amber-300">Advanced JSON edit is enabled. Save is blocked while JSON is invalid.</p>}
                  {!runtimePresetJsonState.ok && <p className="text-xs text-rose-300">Invalid JSON: {runtimePresetJsonState.error}</p>}
                </div>
              )}
            </div>

            {(runtimePresetValidation.errors.length > 0 || runtimePresetValidation.warnings.length > 0) && (
              <div className="rounded-xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm">
                {runtimePresetValidation.errors.map((item) => <p key={item} className="text-rose-300">• {item}</p>)}
                {runtimePresetValidation.warnings.map((item) => <p key={item} className="text-amber-300">• {item}</p>)}
              </div>
            )}

            <div className="flex flex-wrap gap-3">
              <Button onClick={() => void saveRuntimePreset()} disabled={runtimePresetSaving || runtimePresetValidation.errors.length > 0} className="rounded-xl bg-primary text-primary-foreground">{runtimePresetSaving ? "Saving..." : editingRuntimePresetId ? "Update Preset" : "Save Preset"}</Button>
              <Button variant="outline" className="rounded-xl" onClick={() => resetRuntimePresetForm("Balanced")}>Reset Form</Button>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.3fr_0.9fr]">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Strategy Definition</CardTitle><CardDescription>Primary metadata, rules, and publication settings.</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <input className={fieldClass} value={form.name} onChange={(e)=>setForm((p:any)=>({...p,name:e.target.value}))} placeholder="Strategy name" />
              <select className={fieldClass} value={form.visibility} onChange={(e)=>setForm((p:any)=>({...p,visibility:e.target.value}))}><option value="PRIVATE">Private</option><option value="PUBLIC">Published</option></select>
              <input className={fieldClass} value={form.strategy_type} onChange={(e)=>setForm((p:any)=>({...p,strategy_type:e.target.value}))} placeholder="Strategy type" />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <input className={fieldClass} value={form.market} onChange={(e)=>setForm((p:any)=>({...p,market:e.target.value}))} placeholder="Market" />
              <input className={fieldClass} value={form.timeframe} onChange={(e)=>setForm((p:any)=>({...p,timeframe:e.target.value}))} placeholder="Preferred timeframe" />
            </div>
            <textarea className={fieldClass} rows={3} value={form.description} onChange={(e)=>setForm((p:any)=>({...p,description:e.target.value}))} placeholder="Description" />

            <div className="rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="mb-3 text-sm font-medium text-foreground">Execution Config</p>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div>
                  <p className="mb-2 text-xs text-muted-foreground">Risk Reward Ratio</p>
                  <input className={fieldClass} type="number" step="0.1" value={form.rr_ratio} onChange={(e)=>setForm((p:any)=>({...p,rr_ratio:e.target.value}))} />
                </div>
                <div>
                  <p className="mb-2 text-xs text-muted-foreground">Capital Risk %</p>
                  <input className={fieldClass} type="number" step="0.001" value={form.capital_risk_pct} onChange={(e)=>setForm((p:any)=>({...p,capital_risk_pct:e.target.value}))} />
                </div>
                <div>
                  <p className="mb-2 text-xs text-muted-foreground">Price Risk %</p>
                  <input className={fieldClass} type="number" step="0.0001" value={form.price_risk_pct} onChange={(e)=>setForm((p:any)=>({...p,price_risk_pct:e.target.value}))} />
                </div>
                <div>
                  <p className="mb-2 text-xs text-muted-foreground">Max Bars In Trade</p>
                  <input className={fieldClass} type="number" step="1" value={form.max_bars_in_trade} onChange={(e)=>setForm((p:any)=>({...p,max_bars_in_trade:e.target.value}))} />
                </div>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">Engine uses these values for quantity sizing, stop-loss distance, target calculation, and holding rules.</p>
            </div>

            {[
              ["Entry Rules","entry_rules"], ["Exit Rules","exit_rules"], ["Confirmation Rules","confirmation_rules"], ["Risk Rules","risk_rules"], ["Invalidation Rules","invalidation_rules"], ["Trade Management Rules","trade_management_rules"], ["Additional Notes","notes"]
            ].map(([label,key]) => (
              <div key={key as string}>
                <p className="mb-2 text-sm text-muted-foreground">{label}</p>
                <textarea className={fieldClass} rows={3} value={form[key]} onChange={(e)=>setForm((p:any)=>({...p,[key]:e.target.value}))} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle className="flex items-center gap-2"><Code2 className="h-5 w-5" />Source Code</CardTitle><CardDescription>Keep the published implementation here so admin can review and update it safely.</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            <textarea className={`${fieldClass} min-h-[520px] font-mono text-xs`} value={form.source_code} onChange={(e)=>setForm((p:any)=>({...p,source_code:e.target.value}))} placeholder="Paste strategy source code here..." />
            {selectedVersion && (
              <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground"><GitCompareArrows className="h-4 w-4" />Compare with selected version</div>
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <textarea readOnly className={`${fieldClass} min-h-[220px] font-mono text-xs opacity-90`} value={selectedVersionSource} />
                  <textarea readOnly className={`${fieldClass} min-h-[220px] font-mono text-xs`} value={currentSource} />
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Sandbox Backtest</CardTitle><CardDescription>Run admin-only validation without cluttering user backtest history.</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <select className={fieldClass} value={sandboxInput.instrument_id} onChange={(e)=>setSandboxInput((p)=>({...p,instrument_id:Number(e.target.value)}))}>
                {catalog.map((item) => <option key={item.id} value={item.id}>{item.symbol}</option>)}
              </select>
              <select className={fieldClass} value={sandboxInput.timeframe} onChange={(e)=>setSandboxInput((p)=>({...p,timeframe:e.target.value}))}>
                {['5m','15m','1h','1d'].map((tf)=><option key={tf} value={tf}>{tf}</option>)}
              </select>
              <input className={fieldClass} type="date" value={sandboxInput.start_date} onChange={(e)=>setSandboxInput((p)=>({...p,start_date:e.target.value}))} />
              <input className={fieldClass} type="date" value={sandboxInput.end_date} onChange={(e)=>setSandboxInput((p)=>({...p,end_date:e.target.value}))} />
              <input className={fieldClass} type="number" value={sandboxInput.capital} onChange={(e)=>setSandboxInput((p)=>({...p,capital:Number(e.target.value)}))} />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void verifyCode()} disabled={verifying} className="rounded-xl"><ShieldCheck className="mr-2 h-4 w-4" />Quick Verify</Button>
              <Button onClick={() => void runSandbox()} disabled={sandboxing} className="rounded-xl bg-primary text-primary-foreground"><Play className="mr-2 h-4 w-4" />{sandboxing ? "Running..." : "Run Sandbox Backtest"}</Button>
            </div>
            {(verifying || sandboxing) && (
              <p className="mt-3 text-sm text-muted-foreground">Loading may take a few minutes on large datasets. Please keep this page open while the backend finishes.</p>
            )}
            {sandboxResult && (
              <div className="grid grid-cols-2 gap-3 text-sm">
                {[
                  ["PnL", formatCurrency(sandboxResult.summary.net_profit)],
                  ["Return", formatPercent(sandboxResult.summary.return_pct)],
                  ["Win Rate", formatPercent(sandboxResult.summary.win_rate)],
                  ["Sharpe", sandboxResult.summary.sharpe_ratio.toFixed(2)],
                  ["Profit Factor", sandboxResult.summary.profit_factor.toFixed(2)],
                  ["Trades", String(sandboxResult.summary.total_trades)],
                ].map(([label,val]) => <div key={label} className="rounded-xl border border-border/50 bg-card/20 p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-foreground">{val}</p></div>)}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader><CardTitle>Sandbox Equity Preview</CardTitle><CardDescription>Quick visual confirmation before publishing the strategy.</CardDescription></CardHeader>
          <CardContent>
            {equityRows.length ? (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equityRows}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                    <XAxis dataKey="label" tick={{ fontSize: 12 }} stroke="rgba(255,255,255,0.45)" hide />
                    <YAxis tick={{ fontSize: 12 }} stroke="rgba(255,255,255,0.45)" />
                    <Tooltip />
                    <Area type="monotone" dataKey="equity" stroke="#b7ff3c" fill="rgba(183,255,60,0.18)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-72 items-center justify-center rounded-xl border border-dashed border-border/50 text-sm text-muted-foreground">Run sandbox backtest to preview equity and trades.</div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
