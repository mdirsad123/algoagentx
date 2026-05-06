"use client";

import { ReactNode } from "react";
import { FieldHelpTooltip } from "@/components/common/FieldHelpTooltip";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RUNTIME_FIELD_HELP, STRATEGY_PARAM_HELP } from "./runtimeSettingsHelp";
import type { RuntimeConfig, RuntimeFieldSchema, RuntimeTab } from "./runtimeSettingsTypes";

type NumberOption = { label: string; value: number };
const numberOptions = (values: number[]): NumberOption[] => values.map((value) => ({ label: String(value), value }));
const RISK_PERCENT_OPTIONS: NumberOption[] = [
  { label: "0.25%", value: 0.0025 }, { label: "0.50%", value: 0.005 }, { label: "1.00%", value: 0.01 },
  { label: "1.50%", value: 0.015 }, { label: "2.00%", value: 0.02 }, { label: "3.00%", value: 0.03 }, { label: "5.00%", value: 0.05 },
];
const RR_RATIO_OPTIONS = numberOptions([1, 1.5, 2, 3, 4, 5]);
const ATR_PERIOD_OPTIONS = numberOptions([7, 10, 14, 20, 21, 50]);
const ATR_MULTIPLIER_OPTIONS = numberOptions([1, 1.5, 2, 2.5, 3]);
const SWING_LOOKBACK_OPTIONS = numberOptions([3, 5, 10, 20]);
const FIXED_PRICE_RISK_OPTIONS: NumberOption[] = [
  { label: "0.10%", value: 0.001 }, { label: "0.20%", value: 0.002 }, { label: "0.50%", value: 0.005 },
  { label: "1.00%", value: 0.01 }, { label: "2.00%", value: 0.02 },
];
const MAX_OPEN_POSITION_OPTIONS = numberOptions([1, 2, 3, 5]);
const BREAK_EVEN_R_OPTIONS = numberOptions([0.5, 1, 1.5, 2]);
const TRAIL_START_R_OPTIONS = numberOptions([1, 1.5, 2, 3]);
const TRAIL_ATR_MULTIPLIER_OPTIONS = numberOptions([1, 1.5, 2, 2.5, 3]);
const MAX_TRADES_PER_DAY_OPTIONS = ["NONE", "1", "2", "3", "5", "10", "20"].map((value) => ({ label: value === "NONE" ? "No Limit" : value, value }));

const safeNumber = (value: unknown, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};
const toOptionalNumber = (value: string) => value === "" ? null : safeNumber(value, 0);
const humanLabel = (value: string) => value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

function FieldLabel({ label, help }: { label: string; help?: string }) {
  return <span className="inline-flex items-center gap-1.5 text-muted-foreground">{label}<FieldHelpTooltip label={`${label} help`} content={help || RUNTIME_FIELD_HELP[label] || STRATEGY_PARAM_HELP} /></span>;
}

const toggleClass = (enabled: boolean) => `relative inline-flex h-7 w-12 items-center rounded-full border transition ${enabled ? "border-primary/60 bg-primary" : "border-border/60 bg-muted/40"}`;
const toggleKnobClass = (enabled: boolean) => `inline-block h-5 w-5 rounded-full bg-white shadow transition ${enabled ? "translate-x-6" : "translate-x-1"}`;

type RuntimeSettingsFormProps = {
  activeTab: RuntimeTab;
  config: RuntimeConfig;
  updateSection: (section: keyof RuntimeConfig, key: string, value: any) => void;
  strategySchema?: Record<string, RuntimeFieldSchema>;
  updateStrategyParam?: (key: string, value: any) => void;
  initialCapital?: string | number;
  onInitialCapitalChange?: (value: string) => void;
  currency?: string;
  instrumentSymbol?: string;
  supportsIntradaySquareOff?: boolean;
  mode?: "backtest" | "live" | "admin";
  extraRiskContent?: ReactNode;
};

export function RuntimeSettingsForm({
  activeTab,
  config,
  updateSection,
  strategySchema = {},
  updateStrategyParam,
  initialCapital,
  onInitialCapitalChange,
  currency = "USD",
  instrumentSymbol = "this instrument",
  supportsIntradaySquareOff = false,
  mode = "backtest",
  extraRiskContent,
}: RuntimeSettingsFormProps) {
  const positionSizeMode = config.risk?.position_size_mode || (mode === "live" ? "RISK_BASED" : "RISK_BASED");
  const slMode = config.sl_tp?.sl_mode || "ATR";
  const breakEvenEnabled = Boolean(config.trade_management?.break_even_enabled);
  const trailingEnabled = Boolean(config.trade_management?.trailing_enabled);
  const partialExitEnabled = Boolean(config.trade_management?.partial_exit_enabled);
  const strategyParamEntries = Object.entries(strategySchema || {});

  const renderPresetSelect = (label: string, value: unknown, options: NumberOption[], onChange: (value: number) => void, hint?: string) => (
    <div className="space-y-2">
      <Label className="text-muted-foreground"><FieldLabel label={label} /></Label>
      <Select value={String(value ?? options[0]?.value ?? "")} onValueChange={(next) => onChange(safeNumber(next, options[0]?.value ?? 0))}>
        <SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground"><SelectValue /></SelectTrigger>
        <SelectContent className="z-[130] rounded-xl border-border/60 bg-[#34135c] text-foreground">
          {options.map((option) => <SelectItem key={String(option.value)} value={String(option.value)}>{option.label}</SelectItem>)}
        </SelectContent>
      </Select>
      {hint && <p className="text-[11px] leading-relaxed text-muted-foreground">{hint}</p>}
    </div>
  );

  if (activeTab === "risk") {
    return <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {onInitialCapitalChange ? <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Initial Capital" /></Label><Input type="number" value={initialCapital ?? config.risk?.initial_capital ?? ""} onChange={(event) => onInitialCapitalChange(event.target.value)} className="rounded-xl border-border/50 bg-card/20 text-foreground" /></div> : null}
      <div className="rounded-xl border border-border/50 bg-card/20 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Instrument Currency</p>
        <p className="mt-1 text-sm font-semibold text-foreground">{currency}</p>
        <p className="mt-1 text-[11px] text-muted-foreground">Readonly from Instrument Master. Admin controlled instrument specs.</p>
      </div>
      {positionSizeMode === "RISK_BASED" && renderPresetSelect("Capital Risk %", config.risk?.risk_percent, RISK_PERCENT_OPTIONS, (value) => updateSection("risk", "risk_percent", value), "Beginner-safe presets prevent unrealistic risk like 50% or 500%.")}
      <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Position Size Mode" /></Label><Select value={String(positionSizeMode)} onValueChange={(value) => updateSection("risk", "position_size_mode", value)}><SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground"><SelectValue /></SelectTrigger><SelectContent className="z-[130] rounded-xl border-border/60 bg-[#34135c] text-foreground"><SelectItem value="RISK_BASED">Risk Based</SelectItem><SelectItem value="FIXED_LOT">Fixed Lot</SelectItem><SelectItem value="FIXED_QUANTITY">Fixed Quantity</SelectItem></SelectContent></Select></div>
      {positionSizeMode === "FIXED_LOT" && <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Fixed Lot Size" /></Label><Input type="number" step={0.01} value={config.risk?.fixed_lot ?? ""} onChange={(event) => updateSection("risk", "fixed_lot", toOptionalNumber(event.target.value))} className="rounded-xl border-border/50 bg-card/20 text-foreground" /></div>}
      {positionSizeMode === "FIXED_QUANTITY" && <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Fixed Quantity" /></Label><Input type="number" step={1} value={config.risk?.fixed_quantity ?? ""} onChange={(event) => updateSection("risk", "fixed_quantity", toOptionalNumber(event.target.value))} className="rounded-xl border-border/50 bg-card/20 text-foreground" /></div>}
      {positionSizeMode !== "FIXED_QUANTITY" && <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Max Lot Cap" /></Label><Input type="number" step={0.01} value={config.risk?.max_lot_cap ?? ""} onChange={(event) => updateSection("risk", "max_lot_cap", toOptionalNumber(event.target.value))} className="rounded-xl border-border/50 bg-card/20 text-foreground" />{mode === "live" && safeNumber(config.risk?.max_lot_cap, 0) > 0.02 ? <p className="text-[11px] text-amber-200">Live safety warning: keep demo max lot low. Backend caps still apply.</p> : null}</div>}
      {positionSizeMode === "FIXED_QUANTITY" && <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Max Quantity Cap" /></Label><Input type="number" step={1} value={config.risk?.max_quantity_cap ?? ""} onChange={(event) => updateSection("risk", "max_quantity_cap", toOptionalNumber(event.target.value))} className="rounded-xl border-border/50 bg-card/20 text-foreground" /></div>}
      {extraRiskContent}
    </div>;
  }

  if (activeTab === "sl_tp") {
    return <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {renderPresetSelect("RR Ratio", config.sl_tp?.rr_ratio, RR_RATIO_OPTIONS, (value) => updateSection("sl_tp", "rr_ratio", value), "Reward-to-risk presets keep reports comparable.")}
      <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="SL Mode" /></Label><Select value={String(slMode)} onValueChange={(value) => updateSection("sl_tp", "sl_mode", value)}><SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground"><SelectValue /></SelectTrigger><SelectContent className="z-[130] rounded-xl border-border/60 bg-[#34135c] text-foreground"><SelectItem value="ATR">ATR</SelectItem><SelectItem value="SWING">Swing</SelectItem><SelectItem value="FIXED_PERCENT">Fixed Percent</SelectItem><SelectItem value="STRATEGY_SUGGESTED">Strategy Suggested</SelectItem></SelectContent></Select></div>
      {slMode === "ATR" && renderPresetSelect("ATR Period", config.sl_tp?.atr_period, ATR_PERIOD_OPTIONS, (value) => updateSection("sl_tp", "atr_period", value), "Common ATR periods for intraday and swing systems.")}
      {slMode === "ATR" && renderPresetSelect("ATR Multiplier", config.sl_tp?.atr_multiplier, ATR_MULTIPLIER_OPTIONS, (value) => updateSection("sl_tp", "atr_multiplier", value), "Higher multiplier means wider stop loss.")}
      {slMode === "SWING" && renderPresetSelect("Swing Lookback", config.sl_tp?.swing_lookback, SWING_LOOKBACK_OPTIONS, (value) => updateSection("sl_tp", "swing_lookback", value), "Number of candles used to find recent swing high/low.")}
      {slMode === "FIXED_PERCENT" && renderPresetSelect("Fixed Price Risk %", config.sl_tp?.fixed_price_risk_pct, FIXED_PRICE_RISK_OPTIONS, (value) => updateSection("sl_tp", "fixed_price_risk_pct", value), "Used only when SL Mode is Fixed Percent.")}
      {slMode === "STRATEGY_SUGGESTED" && <div className="rounded-xl border border-border/50 bg-card/30 p-3 text-sm text-muted-foreground md:col-span-2">Strategy Suggested mode uses the strategy engine's own stop-loss suggestion. ATR, swing and fixed-percent controls stay saved but hidden here.</div>}
    </div>;
  }

  if (activeTab === "execution") {
    return <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Entry Mode" /></Label><Input value="Next Candle Open" readOnly className="rounded-xl border-border/50 bg-card/20 text-foreground" /></div>
      {[["exit_on_opposite_signal", "Exit on Opposite Signal"], ["allow_long", "Allow Long"], ["allow_short", "Allow Short"]].map(([key, label]) => {
        const enabled = Boolean(config.execution?.[key]);
        return <div key={key} className="flex items-center justify-between rounded-xl border border-border/50 bg-card/20 p-3"><span className="text-sm font-medium text-foreground"><FieldLabel label={label} /></span><button type="button" className={toggleClass(enabled)} onClick={() => updateSection("execution", key, !enabled)}><span className={toggleKnobClass(enabled)} /></button></div>;
      })}
      {supportsIntradaySquareOff ? <><div className="flex items-center justify-between rounded-xl border border-border/50 bg-card/20 p-3"><span className="text-sm font-medium text-foreground"><FieldLabel label="Intraday Square Off" /></span><button type="button" className={toggleClass(Boolean(config.execution?.intraday_square_off))} onClick={() => updateSection("execution", "intraday_square_off", !config.execution?.intraday_square_off)}><span className={toggleKnobClass(Boolean(config.execution?.intraday_square_off))} /></button></div><div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Square Off Time" /></Label><Input type="time" value={config.execution?.square_off_time || "15:15"} onChange={(event) => updateSection("execution", "square_off_time", event.target.value)} className="rounded-xl border-border/50 bg-card/20 text-foreground" /></div></> : <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100 md:col-span-2">Intraday square-off is available only for intraday Indian market instruments. It is disabled for {instrumentSymbol || "this instrument"}.</div>}
      <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Max Trades Per Day" /></Label><Select value={config.execution?.max_trades_per_day == null ? "NONE" : String(config.execution?.max_trades_per_day)} onValueChange={(value) => updateSection("execution", "max_trades_per_day", value === "NONE" ? null : safeNumber(value, 1))}><SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground"><SelectValue /></SelectTrigger><SelectContent className="z-[130] rounded-xl border-border/60 bg-[#34135c] text-foreground">{MAX_TRADES_PER_DAY_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select><p className="text-[11px] leading-relaxed text-muted-foreground">Optional daily trade limiter.</p></div>
      {renderPresetSelect("Max Open Positions", config.execution?.max_open_positions, MAX_OPEN_POSITION_OPTIONS, (value) => updateSection("execution", "max_open_positions", value), "Keep this low for realism and risk control.")}
    </div>;
  }

  if (activeTab === "trade_management") {
    return <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {[["break_even_enabled", "Break Even Enabled"], ["trailing_enabled", "Trailing Stop Enabled"], ["partial_exit_enabled", "Partial Exit Enabled"]].map(([key, label]) => {
        const enabled = Boolean(config.trade_management?.[key]);
        return <div key={key} className="flex items-center justify-between rounded-xl border border-border/50 bg-card/20 p-3"><span className="text-sm font-medium text-foreground"><FieldLabel label={label} /></span><button type="button" className={toggleClass(enabled)} onClick={() => updateSection("trade_management", key, !enabled)}><span className={toggleKnobClass(enabled)} /></button></div>;
      })}
      {breakEvenEnabled && renderPresetSelect("Break Even Trigger R", config.trade_management?.break_even_trigger_r, BREAK_EVEN_R_OPTIONS, (value) => updateSection("trade_management", "break_even_trigger_r", value), "Move stop loss to entry after this R multiple.")}
      {trailingEnabled && <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Trailing Mode" /></Label><Select value={config.trade_management?.trailing_mode || "ATR_TRAIL"} onValueChange={(value) => updateSection("trade_management", "trailing_mode", value)}><SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground"><SelectValue /></SelectTrigger><SelectContent className="z-[130] rounded-xl border-border/60 bg-[#34135c] text-foreground"><SelectItem value="ATR_TRAIL">ATR Trail</SelectItem><SelectItem value="EMA20_TRAIL">EMA20 Trail</SelectItem><SelectItem value="SWING_TRAIL">Swing Trail</SelectItem></SelectContent></Select></div>}
      {trailingEnabled && renderPresetSelect("Trail Start R", config.trade_management?.trail_start_r, TRAIL_START_R_OPTIONS, (value) => updateSection("trade_management", "trail_start_r", value), "Trailing starts only after this R multiple.")}
      {trailingEnabled && renderPresetSelect("Trail ATR Multiplier", config.trade_management?.trail_atr_multiplier, TRAIL_ATR_MULTIPLIER_OPTIONS, (value) => updateSection("trade_management", "trail_atr_multiplier", value), "Used when trailing mode is ATR Trail.")}
      {partialExitEnabled && renderPresetSelect("Partial Exit At R", config.trade_management?.partial_exit_at_r, BREAK_EVEN_R_OPTIONS, (value) => updateSection("trade_management", "partial_exit_at_r", value), "Close part of the position after this R multiple.")}
      {partialExitEnabled && <div className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label="Partial Exit Percent" /></Label><Select value={String(config.trade_management?.partial_exit_percent ?? 0.5)} onValueChange={(value) => updateSection("trade_management", "partial_exit_percent", safeNumber(value, 0.5))}><SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground"><SelectValue /></SelectTrigger><SelectContent className="z-[130] rounded-xl border-border/60 bg-[#34135c] text-foreground"><SelectItem value="0.25">25%</SelectItem><SelectItem value="0.5">50%</SelectItem><SelectItem value="0.75">75%</SelectItem></SelectContent></Select><p className="text-[11px] leading-relaxed text-muted-foreground">Remaining position continues to TP/trailing stop.</p></div>}
    </div>;
  }

  return <div className="space-y-4">
    {!strategyParamEntries.length ? <div className="rounded-xl border border-border/50 bg-card/20 p-4 text-sm text-muted-foreground">No runtime strategy parameters published for this strategy yet.</div> : <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {strategyParamEntries.map(([key, field]) => {
        const value = config.strategy_params?.[key] ?? field.default ?? "";
        const fieldType = field.type || "text";
        const label = field.label || humanLabel(key);
        if (fieldType === "boolean") {
          const enabled = Boolean(value);
          return <div key={key} className="flex items-center justify-between rounded-xl border border-border/50 bg-card/20 p-3"><span className="text-sm font-medium text-foreground"><FieldLabel label={label} help={STRATEGY_PARAM_HELP} /></span><button type="button" className={toggleClass(enabled)} onClick={() => updateStrategyParam?.(key, !enabled)}><span className={toggleKnobClass(enabled)} /></button></div>;
        }
        if (fieldType === "select" && Array.isArray(field.options)) {
          return <div key={key} className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label={label} help={STRATEGY_PARAM_HELP} /></Label><Select value={String(value)} onValueChange={(next) => updateStrategyParam?.(key, next)}><SelectTrigger className="h-11 rounded-xl border-border/50 bg-card/20 text-foreground"><SelectValue /></SelectTrigger><SelectContent className="z-[130] rounded-xl border-border/60 bg-[#34135c] text-foreground">{field.options.map((option) => { const optionValue = typeof option === "object" ? String(option.value ?? option.label ?? "") : String(option); const optionLabel = typeof option === "object" ? String(option.label ?? option.value ?? "") : String(option); return <SelectItem key={optionValue} value={optionValue}>{optionLabel}</SelectItem>; })}</SelectContent></Select></div>;
        }
        return <div key={key} className="space-y-2"><Label className="text-muted-foreground"><FieldLabel label={label} help={STRATEGY_PARAM_HELP} /></Label><Input type={fieldType === "number" ? "number" : "text"} min={field.min} max={field.max} step={field.step ?? (fieldType === "number" ? 1 : undefined)} value={String(value)} onChange={(event) => updateStrategyParam?.(key, fieldType === "number" ? safeNumber(event.target.value, 0) : event.target.value)} className="rounded-xl border-border/50 bg-card/20 text-foreground" /></div>;
      })}
    </div>}
  </div>;
}
