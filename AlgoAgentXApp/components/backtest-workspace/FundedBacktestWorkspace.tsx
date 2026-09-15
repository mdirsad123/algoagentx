"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Copy, Edit3, Gauge, Loader2,
  Play, Plus, RefreshCcw, Save, ShieldCheck, SlidersHorizontal, Trash2, WalletCards, XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { RuntimeSettingsDrawer } from "@/components/runtime/RuntimeSettingsDrawer";
import { SYSTEM_RUNTIME_DEFAULTS } from "@/components/runtime/runtimeSettingsDefaults";
import type { RuntimeConfig, RuntimeTab } from "@/components/runtime/runtimeSettingsTypes";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { currencySymbolForCode, formatCurrency } from "@/lib/formatters";
import { parseApiError } from "@/lib/api/error";
import {
  backtestsApi, type AdvancedBacktestFilters, type InstrumentOption, type StrategyOption,
} from "@/lib/api/backtests";
import {
  fundedBacktestsApi,
  type FundedAccountPhase,
  type FundedAccountProfile,
  type FundedProfilePayload,
  type FundedPayoutRules,
  type FundedRiskMode,
  type FundedRiskTier,
  type FundedRunDetail,
  type FundedRunRequest,
  type FundedRunStatus,
} from "@/lib/api/funded-backtests";
import {
  decimalToPercent, formatPercent, fundedStatusLabel, isFundedRunFailure, isFundedRunSuccess,
  isFundedRunTerminal, percentToDecimal, stableFingerprint, validateRiskTiers,
} from "@/components/funded-backtest/funded-utils";
import { formatDateTimeIST } from "@/lib/timezone";

const cloneRuntime = (value: RuntimeConfig): RuntimeConfig => JSON.parse(JSON.stringify(value));
const mergeRuntime = (incoming?: Record<string, unknown> | null): RuntimeConfig => {
  const base = cloneRuntime(SYSTEM_RUNTIME_DEFAULTS);
  if (!incoming) return base;
  for (const key of ["risk", "sl_tp", "execution", "trade_management", "strategy_params"] as const) {
    const section = incoming[key];
    if (section && typeof section === "object" && !Array.isArray(section)) {
      (base[key] as Record<string, unknown>) = { ...base[key], ...(section as Record<string, unknown>) };
    }
  }
  return base;
};

const challengeLabel = (value: string) => ({ ONE_STEP: "1-Step", TWO_STEP: "2-Step", INSTANT: "Instant", CUSTOM: "Custom" }[value] || value);
const dailyDdLabel = (value: string) => ({ STATIC_INITIAL_BALANCE: "Static Initial Balance", START_OF_DAY_BALANCE: "Start-of-Day Balance", START_OF_DAY_EQUITY: "Start-of-Day Equity" }[value] || value);
const maxDdLabel = (value: string) => ({ STATIC_INITIAL_BALANCE: "Static Initial Balance", TRAILING_BALANCE: "Trailing Balance", TRAILING_EQUITY: "Trailing Equity", HIGH_WATER_MARK: "High-Water Mark" }[value] || value);
const formatElapsed = (seconds: number): string => {
  const total = Math.max(0, Math.floor(seconds || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  return [hours, minutes, secs].map((value) => String(value).padStart(2, "0")).join(":");
};

const defaultPhase = (phaseNumber: number): FundedAccountPhase => ({
  phase_number: phaseNumber,
  phase_name: `Phase ${phaseNumber}`,
  profit_target_pct: phaseNumber === 1 ? 0.08 : 0.05,
  daily_drawdown_pct: 0.05,
  daily_drawdown_mode: "STATIC_INITIAL_BALANCE",
  max_drawdown_pct: 0.1,
  max_drawdown_mode: "STATIC_INITIAL_BALANCE",
  minimum_trading_days: 3,
  minimum_qualifying_day_profit_pct: 0.005,
  qualifying_day_mode: "MIN_PROFIT_DAY",
  profit_target_required: true,
  reset_balance_after_pass: phaseNumber > 1,
  sequence: phaseNumber,
});

const defaultRiskTiers = (): FundedRiskTier[] => [
  { name: "Deep Defensive", sort_order: 1, min_account_return_pct: null, max_account_return_pct: -0.04, risk_percent: 0.0025, is_active: true },
  { name: "Defensive", sort_order: 2, min_account_return_pct: -0.04, max_account_return_pct: -0.02, risk_percent: 0.005, is_active: true },
  { name: "Normal", sort_order: 3, min_account_return_pct: -0.02, max_account_return_pct: 0.02, risk_percent: 0.01, is_active: true },
  { name: "Growth", sort_order: 4, min_account_return_pct: 0.02, max_account_return_pct: 0.04, risk_percent: 0.015, is_active: true },
  { name: "Aggressive", sort_order: 5, min_account_return_pct: 0.04, max_account_return_pct: null, risk_percent: 0.02, is_active: true },
];

const defaultInstantPayoutConfig = (): FundedPayoutRules => ({
  profit_target_pct: 0,
  minimum_payout_amount: 0,
  minimum_trading_days: 0,
  minimum_qualifying_profitable_days: 0,
  qualifying_day_minimum_profit_pct: 0,
  consistency_rule_enabled: false,
  consistency_maximum_pct: 0.15,
  consistency_calculation_mode: "BEST_DAY_OVER_TOTAL_POSITIVE_PROFIT",
  payout_waiting_calendar_days: 0,
  payout_profit_split_pct: 0.8,
  stop_simulation_when_payout_ready: false,
});

const blankProfile = (): FundedProfilePayload => ({
  name: "",
  provider_name: "",
  challenge_type: "TWO_STEP",
  account_size: 5000,
  account_currency: "USD",
  is_template: false,
  is_active: true,
  description: "",
  payout_config: null,
  rules_json: { rule_timezone: "UTC" },
  phases: [defaultPhase(1), defaultPhase(2)],
  risk_tiers: defaultRiskTiers(),
});

const hydrateProfile = (profile: FundedAccountProfile): FundedProfilePayload => {
  const riskTiers = profile.risk_tiers.map((t) => ({ ...t }));
  // Dynamic ladders must cover every possible account return. Older profiles
  // could persist arbitrary finite outer bounds (for example -6% → -4%),
  // which leaves returns below -6% uncovered. Normalize only the outer edges;
  // internal boundaries remain untouched and are validated separately.
  if (riskTiers.length) {
    riskTiers[0] = { ...riskTiers[0], min_account_return_pct: null };
    riskTiers[riskTiers.length - 1] = { ...riskTiers[riskTiers.length - 1], max_account_return_pct: null };
  }
  return {
    name: profile.name,
    provider_name: profile.provider_name || "",
    challenge_type: profile.challenge_type,
    account_size: Number(profile.account_size),
    account_currency: profile.account_currency,
    is_template: profile.is_template,
    is_active: profile.is_active,
    description: profile.description || "",
    payout_config: profile.payout_config ? { ...profile.payout_config } : null,
    rules_json: { ...(profile.rules_json || {}) },
    phases: profile.phases.map((p) => ({ ...p })),
    risk_tiers: riskTiers,
  };
};

function PercentInput({ value, onChange, disabled = false, step = "0.1" }: { value?: number | null; onChange: (value: number) => void; disabled?: boolean; step?: string }) {
  return <Input type="number" min="0" step={step} disabled={disabled} value={Number.isFinite(decimalToPercent(value)) ? decimalToPercent(value) : 0} onChange={(e) => onChange(percentToDecimal(e.target.value))} />;
}

function PhaseEditor({ phase, onChange }: { phase: FundedAccountPhase; onChange: (phase: FundedAccountPhase) => void }) {
  return <Card className="border-white/10 bg-white/[0.035]">
    <CardHeader className="pb-3"><CardTitle className="text-base">{phase.phase_name}</CardTitle></CardHeader>
    <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <div><Label>Profit Target %</Label><PercentInput value={phase.profit_target_pct} onChange={(v) => onChange({ ...phase, profit_target_pct: v })} /></div>
      <div><Label>Daily Drawdown %</Label><PercentInput value={phase.daily_drawdown_pct} onChange={(v) => onChange({ ...phase, daily_drawdown_pct: v })} /></div>
      <div><Label>Daily Drawdown Mode</Label><Select value={phase.daily_drawdown_mode} onValueChange={(v) => onChange({ ...phase, daily_drawdown_mode: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl"><SelectItem value="STATIC_INITIAL_BALANCE">Static Initial Balance</SelectItem><SelectItem value="START_OF_DAY_BALANCE">Start-of-Day Balance</SelectItem><SelectItem value="START_OF_DAY_EQUITY">Start-of-Day Equity</SelectItem></SelectContent></Select></div>
      <div><Label>Maximum Drawdown %</Label><PercentInput value={phase.max_drawdown_pct} onChange={(v) => onChange({ ...phase, max_drawdown_pct: v })} /></div>
      <div><Label>Maximum Drawdown Mode</Label><Select value={phase.max_drawdown_mode} onValueChange={(v) => onChange({ ...phase, max_drawdown_mode: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl"><SelectItem value="STATIC_INITIAL_BALANCE">Static Initial Balance</SelectItem><SelectItem value="TRAILING_BALANCE">Trailing Balance</SelectItem><SelectItem value="TRAILING_EQUITY">Trailing Equity</SelectItem><SelectItem value="HIGH_WATER_MARK">High-Water Mark</SelectItem></SelectContent></Select></div>
      <div><Label>Minimum Trading Days</Label><Input type="number" min="0" value={phase.minimum_trading_days} onChange={(e) => onChange({ ...phase, minimum_trading_days: Number(e.target.value) })} /></div>
      <div><Label>Qualifying Day Mode</Label><Select value={phase.qualifying_day_mode} onValueChange={(v) => onChange({ ...phase, qualifying_day_mode: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl"><SelectItem value="ANY_TRADE_DAY">Any Trading Day</SelectItem><SelectItem value="MIN_PROFIT_DAY">Minimum Profit Day</SelectItem></SelectContent></Select></div>
      {phase.qualifying_day_mode === "MIN_PROFIT_DAY" && <div><Label>Minimum Qualifying Profit %</Label><PercentInput value={phase.minimum_qualifying_day_profit_pct} onChange={(v) => onChange({ ...phase, minimum_qualifying_day_profit_pct: v })} /></div>}
      <label className="flex items-center gap-2 pt-6 text-sm"><Checkbox checked={phase.reset_balance_after_pass} onCheckedChange={(v) => onChange({ ...phase, reset_balance_after_pass: Boolean(v) })} /> Reset balance after pass</label>
    </CardContent>
  </Card>;
}

function RiskTierEditor({ tiers, onChange }: { tiers: FundedRiskTier[]; onChange: (tiers: FundedRiskTier[]) => void }) {
  const update = (idx: number, patch: Partial<FundedRiskTier>) => onChange(tiers.map((tier, i) => i === idx ? { ...tier, ...patch } : tier));
  return <div className="space-y-3">
    {tiers.map((tier, idx) => <div key={`${tier.sort_order}-${idx}`} className="grid gap-2 rounded-xl border border-white/10 bg-black/10 p-3 md:grid-cols-[1.2fr_1fr_1fr_1fr_auto]">
      <Input aria-label={`Tier ${idx + 1} name`} value={tier.name} onChange={(e) => update(idx, { name: e.target.value })} placeholder="Tier name" />
      {idx === 0
        ? <Input value="Below" disabled aria-label="Open lower bound" className="opacity-90" />
        : <Input type="number" step="0.1" placeholder="From %" value={tier.min_account_return_pct == null ? "" : decimalToPercent(tier.min_account_return_pct)} onChange={(e) => update(idx, { min_account_return_pct: e.target.value === "" ? null : percentToDecimal(e.target.value) })} />}
      {idx === tiers.length - 1
        ? <Input value="Above" disabled aria-label="Open upper bound" className="opacity-90" />
        : <Input type="number" step="0.1" placeholder="To %" value={tier.max_account_return_pct == null ? "" : decimalToPercent(tier.max_account_return_pct)} onChange={(e) => update(idx, { max_account_return_pct: e.target.value === "" ? null : percentToDecimal(e.target.value) })} />}
      <PercentInput value={tier.risk_percent} onChange={(v) => update(idx, { risk_percent: v })} />
      <Button type="button" variant="ghost" size="sm" aria-label="Remove tier" onClick={() => onChange(tiers.filter((_, i) => i !== idx).map((t, i) => ({ ...t, sort_order: i + 1 })))}><Trash2 className="h-4 w-4" /></Button>
    </div>)}
    <Button type="button" variant="outline" onClick={() => onChange([...tiers, { name: `Tier ${tiers.length + 1}`, sort_order: tiers.length + 1, min_account_return_pct: null, max_account_return_pct: null, risk_percent: 0.005, is_active: true }])}><Plus className="mr-2 h-4 w-4" />Add Tier</Button>
  </div>;
}

function ProfileDialog({ open, onOpenChange, initial, mode, onSaved }: { open: boolean; onOpenChange: (open: boolean) => void; initial?: FundedAccountProfile | null; mode: "create" | "edit" | "duplicate"; onSaved: (profile: FundedAccountProfile) => void }) {
  const [form, setForm] = useState<FundedProfilePayload>(() => initial ? hydrateProfile(initial) : blankProfile());
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    const next = initial ? hydrateProfile(initial) : blankProfile();
    if (mode === "duplicate") { next.name = `${next.name} Copy`; next.is_template = false; }
    setForm(next);
  }, [initial, mode, open]);

  const setChallengeType = (value: string) => {
    let phases = form.phases;
    if (value === "ONE_STEP") phases = [form.phases[0] || defaultPhase(1)];
    else if (value === "TWO_STEP") phases = [form.phases[0] || defaultPhase(1), form.phases[1] || defaultPhase(2)];
    else if (value === "INSTANT") phases = [];
    else if (!phases.length) phases = [defaultPhase(1)];
    const payout_config = value === "INSTANT"
      ? { ...defaultInstantPayoutConfig(), ...(form.payout_config || {}) }
      : form.payout_config;
    setForm({ ...form, challenge_type: value, phases, payout_config });
  };

  const save = async () => {
    if (!form.name.trim()) return toast.error("Profile name is required.");
    if (!(Number(form.account_size) > 0)) return toast.error("Account size must be greater than zero.");
    const riskTierError = validateRiskTiers(form.risk_tiers);
    if (riskTierError) return toast.error(riskTierError);
    for (const phase of form.phases) {
      if (!(Number(phase.daily_drawdown_pct) > 0)) return toast.error(`${phase.phase_name}: Daily drawdown must be greater than 0%.`);
      if (!(Number(phase.max_drawdown_pct) > 0)) return toast.error(`${phase.phase_name}: Maximum drawdown must be greater than 0%.`);
    }
    const payoutConfig = form.challenge_type === "INSTANT"
      ? { ...defaultInstantPayoutConfig(), ...(form.payout_config || {}) }
      : form.payout_config;
    if (payoutConfig?.consistency_rule_enabled) {
      if (!(Number(payoutConfig.consistency_maximum_pct) > 0)) {
        return toast.error("Consistency Maximum % is required when the consistency rule is enabled.");
      }
      if (Number(payoutConfig.consistency_maximum_pct) > 1) {
        return toast.error("Consistency Maximum % cannot exceed 100%.");
      }
    }
    setSaving(true);
    try {
      const payload = {
        ...form,
        payout_config: payoutConfig,
        account_size: Number(form.account_size),
        risk_tiers: form.risk_tiers.map((t, i) => ({ ...t, sort_order: i + 1 })),
      };
      const saved = mode === "edit" && initial ? await fundedBacktestsApi.updateProfile(initial.id, payload) : await fundedBacktestsApi.createProfile(payload);
      toast.success(mode === "edit" ? "Funded account updated." : "Funded account created.");
      onSaved(saved); onOpenChange(false);
    } catch (err) { toast.error(parseApiError(err).message); }
    finally { setSaving(false); }
  };

  const payout = form.challenge_type === "INSTANT"
    ? { ...defaultInstantPayoutConfig(), ...(form.payout_config || {}) }
    : (form.payout_config || {});
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="max-h-[92vh] w-[calc(100vw-2rem)] max-w-5xl overflow-y-auto overflow-x-hidden border-white/10 bg-[#211042] text-foreground">
    <DialogHeader><DialogTitle>Funded Account Settings</DialogTitle></DialogHeader>
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div><Label>Profile Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
        <div><Label>Provider Name</Label><Input value={form.provider_name || ""} onChange={(e) => setForm({ ...form, provider_name: e.target.value })} /></div>
        <div><Label>Account Size</Label><Input type="number" min="1" value={form.account_size} onChange={(e) => setForm({ ...form, account_size: Number(e.target.value) })} /></div>
        <div><Label>Currency</Label><Input value={form.account_currency} onChange={(e) => setForm({ ...form, account_currency: e.target.value.toUpperCase() })} /></div>
        <div><Label>Challenge Type</Label><Select value={form.challenge_type} onValueChange={setChallengeType}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl"><SelectItem value="ONE_STEP">1-Step</SelectItem><SelectItem value="TWO_STEP">2-Step</SelectItem><SelectItem value="INSTANT">Instant</SelectItem><SelectItem value="CUSTOM">Custom</SelectItem></SelectContent></Select></div>
        <div className="md:col-span-2 xl:col-span-3"><Label>Description</Label><Textarea value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
      </div>

      {form.challenge_type !== "INSTANT" && <div className="space-y-4"><div className="flex items-center justify-between"><h3 className="text-base font-semibold">Challenge Phases</h3>{form.challenge_type === "CUSTOM" && <Button type="button" size="sm" variant="outline" onClick={() => { const n = form.phases.length + 1; setForm({ ...form, phases: [...form.phases, defaultPhase(n)] }); }}><Plus className="mr-1 h-4 w-4" />Add Phase</Button>}</div>{form.phases.map((phase, idx) => <div key={phase.sequence} className="space-y-2"><PhaseEditor phase={phase} onChange={(next) => setForm({ ...form, phases: form.phases.map((p, i) => i === idx ? next : p) })} />{form.challenge_type === "CUSTOM" && form.phases.length > 1 && <Button type="button" size="sm" variant="ghost" onClick={() => setForm({ ...form, phases: form.phases.filter((_, i) => i !== idx).map((p, i) => ({ ...p, phase_number: i + 1, sequence: i + 1, phase_name: `Phase ${i + 1}` })) })}><Trash2 className="mr-1 h-4 w-4" />Remove Phase</Button>}</div>)}</div>}

      {form.challenge_type === "INSTANT" && <Card className="border-white/10 bg-white/[0.035]"><CardHeader><CardTitle className="text-base">Instant Account & Payout Rules</CardTitle></CardHeader><CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div><Label>Daily DD %</Label><PercentInput value={Number(form.rules_json?.daily_drawdown_pct ?? 0.05)} onChange={(v) => setForm({ ...form, rules_json: { ...(form.rules_json || {}), daily_drawdown_pct: v } })} /></div>
        <div><Label>Daily DD Mode</Label><Select value={String(form.rules_json?.daily_drawdown_mode || "STATIC_INITIAL_BALANCE")} onValueChange={(v) => setForm({ ...form, rules_json: { ...(form.rules_json || {}), daily_drawdown_mode: v } })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl"><SelectItem value="STATIC_INITIAL_BALANCE">Static Initial Balance</SelectItem><SelectItem value="START_OF_DAY_BALANCE">Start-of-Day Balance</SelectItem><SelectItem value="START_OF_DAY_EQUITY">Start-of-Day Equity</SelectItem></SelectContent></Select></div>
        <div><Label>Maximum DD %</Label><PercentInput value={Number(form.rules_json?.max_drawdown_pct ?? 0.1)} onChange={(v) => setForm({ ...form, rules_json: { ...(form.rules_json || {}), max_drawdown_pct: v } })} /></div>
        <div><Label>Maximum DD Mode</Label><Select value={String(form.rules_json?.max_drawdown_mode || "STATIC_INITIAL_BALANCE")} onValueChange={(v) => setForm({ ...form, rules_json: { ...(form.rules_json || {}), max_drawdown_mode: v } })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl"><SelectItem value="STATIC_INITIAL_BALANCE">Static Initial Balance</SelectItem><SelectItem value="TRAILING_BALANCE">Trailing Balance</SelectItem><SelectItem value="TRAILING_EQUITY">Trailing Equity</SelectItem><SelectItem value="HIGH_WATER_MARK">High-Water Mark</SelectItem></SelectContent></Select></div>
        <div><Label>Payout Target %</Label><PercentInput value={payout.profit_target_pct ?? 0} onChange={(v) => setForm({ ...form, payout_config: { ...payout, profit_target_pct: v } })} /></div>
        <div><Label>Minimum Payout</Label><Input type="number" min="0" value={payout.minimum_payout_amount ?? 0} onChange={(e) => setForm({ ...form, payout_config: { ...payout, minimum_payout_amount: Number(e.target.value) } })} /></div>
        <div><Label>Minimum Trading Days</Label><Input type="number" min="0" value={payout.minimum_trading_days ?? 0} onChange={(e) => setForm({ ...form, payout_config: { ...payout, minimum_trading_days: Number(e.target.value) } })} /></div>
        <div><Label>Minimum Qualifying Days</Label><Input type="number" min="0" value={payout.minimum_qualifying_profitable_days ?? 0} onChange={(e) => setForm({ ...form, payout_config: { ...payout, minimum_qualifying_profitable_days: Number(e.target.value) } })} /></div>
        <div><Label>Qualifying Day Minimum Profit %</Label><PercentInput value={payout.qualifying_day_minimum_profit_pct ?? 0} onChange={(v) => setForm({ ...form, payout_config: { ...payout, qualifying_day_minimum_profit_pct: v } })} /></div>
        <div><Label>Consistency Maximum %</Label><PercentInput value={payout.consistency_maximum_pct ?? 0.15} onChange={(v) => setForm({ ...form, payout_config: { ...payout, consistency_maximum_pct: v } })} /></div>
        <div><Label>Payout Waiting Days</Label><Input type="number" min="0" value={payout.payout_waiting_calendar_days ?? 0} onChange={(e) => setForm({ ...form, payout_config: { ...payout, payout_waiting_calendar_days: Number(e.target.value) } })} /></div>
        <div><Label>Profit Split %</Label><PercentInput value={payout.payout_profit_split_pct ?? 0.8} onChange={(v) => setForm({ ...form, payout_config: { ...payout, payout_profit_split_pct: v } })} /></div>
        <label className="flex items-center gap-2 pt-6 text-sm"><Checkbox checked={Boolean(payout.consistency_rule_enabled)} onCheckedChange={(v) => setForm({ ...form, payout_config: { ...payout, consistency_rule_enabled: Boolean(v), consistency_maximum_pct: payout.consistency_maximum_pct ?? 0.15, consistency_calculation_mode: "BEST_DAY_OVER_TOTAL_POSITIVE_PROFIT" } })} /> Enable Consistency Rule</label>
        <label className="flex items-center gap-2 pt-6 text-sm"><Checkbox checked={Boolean(payout.stop_simulation_when_payout_ready)} onCheckedChange={(v) => setForm({ ...form, payout_config: { ...payout, stop_simulation_when_payout_ready: Boolean(v) } })} /> Stop When Payout Ready</label>
      </CardContent></Card>}

      <div><div className="mb-3 flex items-center justify-between"><div><h3 className="font-semibold">Saved Dynamic Risk Ladder</h3><p className="text-xs text-muted-foreground">0.01 = 1% is sent to the backend.</p></div></div><RiskTierEditor tiers={form.risk_tiers} onChange={(risk_tiers) => setForm({ ...form, risk_tiers })} /></div>

      <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button onClick={save} disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}Save Account</Button></div>
    </div>
  </DialogContent></Dialog>;
}

export default function FundedBacktestWorkspace() {
  const searchParams = useSearchParams();
  const rerunId = searchParams.get("rerun") || "";
  const [profiles, setProfiles] = useState<FundedAccountProfile[]>([]);
  const [profilesLoading, setProfilesLoading] = useState(true);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [strategies, setStrategies] = useState<StrategyOption[]>([]);
  const [instruments, setInstruments] = useState<InstrumentOption[]>([]);
  const [timeframes, setTimeframes] = useState<string[]>([]);
  const [strategyId, setStrategyId] = useState("");
  const [instrumentId, setInstrumentId] = useState("");
  const [timeframe, setTimeframe] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [riskMode, setRiskMode] = useState<FundedRiskMode>("DYNAMIC");
  const [fixedRiskPct, setFixedRiskPct] = useState(0.01);
  const [safetyBufferPct, setSafetyBufferPct] = useState(0);
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfig>(() => cloneRuntime(SYSTEM_RUNTIME_DEFAULTS));
  const [runtimeDefaults, setRuntimeDefaults] = useState<RuntimeConfig>(() => cloneRuntime(SYSTEM_RUNTIME_DEFAULTS));
  const [runtimeOpen, setRuntimeOpen] = useState(false);
  const [runtimeTab, setRuntimeTab] = useState<RuntimeTab>("risk");
  const [runtimeSchema, setRuntimeSchema] = useState<Record<string, any>>({});
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advancedEnabled, setAdvancedEnabled] = useState(false);
  const [days, setDays] = useState<string[]>([]);
  const [session, setSession] = useState("ALL");
  const [customStart, setCustomStart] = useState("09:00");
  const [customEnd, setCustomEnd] = useState("17:00");
  const [advancedTimezone, setAdvancedTimezone] = useState("UTC");
  const [preview, setPreview] = useState<any>(null);
  const [previewFingerprint, setPreviewFingerprint] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const [creditSnapshot, setCreditSnapshot] = useState({
    totalAvailable: 0,
    includedBalance: 0,
    walletBalance: 0,
    deductionOrder: ["subscription", "wallet"] as string[],
    subscriptionState: null as string | null,
  });
  const [running, setRunning] = useState(false);
  const [runId, setRunId] = useState("");
  const [runStatus, setRunStatus] = useState<FundedRunStatus | null>(null);
  const [runDetail, setRunDetail] = useState<FundedRunDetail | null>(null);
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null);
  const [runElapsedSeconds, setRunElapsedSeconds] = useState(0);
  const [rerunSeed, setRerunSeed] = useState<FundedRunDetail | null>(null);
  const [profileDialogOpen, setProfileDialogOpen] = useState(false);
  const [profileDialogMode, setProfileDialogMode] = useState<"create" | "edit" | "duplicate">("create");
  const [profileDialogInitial, setProfileDialogInitial] = useState<FundedAccountProfile | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!running || !runStartedAt) return;
    const updateElapsed = () => setRunElapsedSeconds(Math.max(0, Math.floor((Date.now() - runStartedAt) / 1000)));
    updateElapsed();
    const timer = window.setInterval(updateElapsed, 1000);
    return () => window.clearInterval(timer);
  }, [running, runStartedAt]);

  const selectedProfile = useMemo(() => profiles.find((p) => p.id === selectedProfileId) || null, [profiles, selectedProfileId]);
  const selectedInstrument = useMemo(() => instruments.find((i) => String(i.id) === instrumentId) || null, [instruments, instrumentId]);
  const selectedStrategy = useMemo(() => strategies.find((s) => String(s.id) === strategyId) || null, [strategies, strategyId]);

  const advancedFilters = useMemo<AdvancedBacktestFilters>(() => advancedEnabled ? {
    enabled: true, days_of_week: days, session, custom_start_time: session === "CUSTOM" ? customStart : null,
    custom_end_time: session === "CUSTOM" ? customEnd : null, timezone: advancedTimezone,
  } : { enabled: false }, [advancedEnabled, days, session, customStart, customEnd, advancedTimezone]);

  const requestPayload = useMemo<FundedRunRequest | null>(() => {
    if (!selectedProfileId || !strategyId || !instrumentId || !timeframe || !startDate || !endDate) return null;
    return {
      profile_id: selectedProfileId, strategy_id: strategyId, instrument_id: Number(instrumentId), timeframe,
      start_date: startDate, end_date: endDate, runtime_config: runtimeConfig as unknown as Record<string, unknown>,
      advanced_filters: advancedFilters, risk_mode: riskMode, fixed_risk_pct: riskMode === "FIXED" ? fixedRiskPct : null,
      safety_buffer_pct: safetyBufferPct,
    };
  }, [selectedProfileId, strategyId, instrumentId, timeframe, startDate, endDate, runtimeConfig, advancedFilters, riskMode, fixedRiskPct, safetyBufferPct]);

  const currentFingerprint = useMemo(() => requestPayload ? stableFingerprint(requestPayload) : "", [requestPayload]);
  const previewStale = Boolean(preview && previewFingerprint !== currentFingerprint);
  const invalidRequiredPhaseTargets = Boolean(selectedProfile && selectedProfile.challenge_type !== "INSTANT" && selectedProfile.phases.some((phase) => phase.profit_target_required && Number(phase.profit_target_pct || 0) <= 0));
  const canPreview = Boolean(requestPayload && startDate < endDate && !invalidRequiredPhaseTargets);
  const canRun = Boolean(
    preview && !previewStale && canPreview && !running
    && preview.billing?.has_enough_credits !== false
    && preview.billing?.can_run !== false
  );

  const loadProfiles = useCallback(async (selectId?: string) => {
    setProfilesLoading(true);
    try {
      const rows = await fundedBacktestsApi.listProfiles(); setProfiles(rows);
      setSelectedProfileId((current) => selectId || current || rows[0]?.id || "");
    } catch (err) { toast.error(parseApiError(err).message); }
    finally { setProfilesLoading(false); }
  }, []);

  useEffect(() => {
    const role = typeof document !== "undefined" ? (document.cookie.match(/(?:^|; )loggedinuserroleid=([^;]*)/)?.[1] || document.cookie.match(/(?:^|; )loggedinuserrole=([^;]*)/)?.[1] || "") : "";
    setIsAdmin(role === "1" || decodeURIComponent(role).toLowerCase() === "admin");
  }, []);
  useEffect(() => { loadProfiles(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    (async () => {
      try {
        const [s, i, config] = await Promise.all([
          backtestsApi.getStrategiesCatalog(),
          backtestsApi.getInstruments(),
          backtestsApi.getConfig().catch(() => null),
        ]);
        setStrategies(s); setInstruments(i);
        if (config?.credits) {
          setCreditSnapshot({
            totalAvailable: Number(config.credits.total_available ?? config.credits.current_balance ?? config.credits.balance ?? 0),
            includedBalance: Number(config.credits.included_balance ?? config.credits.included ?? 0),
            walletBalance: Number(config.credits.wallet_balance ?? 0),
            deductionOrder: Array.isArray(config.credits.deduction_order) ? config.credits.deduction_order : ["subscription", "wallet"],
            subscriptionState: config.credits.subscription_state ?? null,
          });
        }
      } catch (err) { toast.error(parseApiError(err).message); }
    })();
  }, []);
  useEffect(() => {
    if (!rerunId) return;
    let active = true;
    (async () => {
      try {
        const detail = await fundedBacktestsApi.getRun(rerunId);
        if (!active) return;
        setRerunSeed(detail);
        if (detail.profile_id) setSelectedProfileId(String(detail.profile_id));
        if (detail.strategy_id) setStrategyId(String(detail.strategy_id));
        if (detail.instrument_id !== undefined && detail.instrument_id !== null) setInstrumentId(String(detail.instrument_id));
        if (detail.timeframe) setTimeframe(String(detail.timeframe));
        if (detail.start_date) setStartDate(String(detail.start_date).slice(0, 10));
        if (detail.end_date) setEndDate(String(detail.end_date).slice(0, 10));
        const plan = detail.risk_plan_snapshot || {};
        if (String(plan.mode || "").toUpperCase() === "FIXED") setRiskMode("FIXED");
        else if (plan.mode) setRiskMode("DYNAMIC");
        if (plan.fixed_risk_pct !== undefined && plan.fixed_risk_pct !== null) setFixedRiskPct(Number(plan.fixed_risk_pct));
        if (plan.safety_buffer_pct !== undefined && plan.safety_buffer_pct !== null) setSafetyBufferPct(Number(plan.safety_buffer_pct));
        setPreview(null);
        setPreviewFingerprint("");
        setRunId("");
        setRunStatus(null);
        setRunDetail(null);
        toast.success("Funded backtest settings loaded for rerun. Preview before running again.");
      } catch (err) {
        if (active) toast.error(`Unable to load funded rerun: ${parseApiError(err).message}`);
      }
    })();
    return () => { active = false; };
  }, [rerunId]);
  useEffect(() => {
    if (!instrumentId) { setTimeframes([]); return; }
    backtestsApi.getTimeframes(Number(instrumentId)).then((rows) => { setTimeframes(rows); if (timeframe && !rows.includes(timeframe)) setTimeframe(""); }).catch((err) => toast.error(parseApiError(err).message));
  }, [instrumentId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!strategyId) { setRuntimeConfig(cloneRuntime(SYSTEM_RUNTIME_DEFAULTS)); setRuntimeSchema({}); return; }
    backtestsApi.getStrategyRuntimeConfig(strategyId).then((response) => {
      const merged = mergeRuntime((response.resolved_defaults || response.default_runtime_config) as Record<string, unknown> | null);
      setRuntimeDefaults(cloneRuntime(merged));
      const rerunRuntime = rerunSeed?.strategy_id === strategyId && rerunSeed.runtime_snapshot
        ? mergeRuntime(rerunSeed.runtime_snapshot)
        : merged;
      setRuntimeConfig(cloneRuntime(rerunRuntime));
      setRuntimeSchema((response.runtime_config_schema || {}) as Record<string, any>);
    }).catch(() => {
      const fallback = rerunSeed?.strategy_id === strategyId && rerunSeed.runtime_snapshot
        ? mergeRuntime(rerunSeed.runtime_snapshot)
        : SYSTEM_RUNTIME_DEFAULTS;
      setRuntimeDefaults(cloneRuntime(SYSTEM_RUNTIME_DEFAULTS));
      setRuntimeConfig(cloneRuntime(fallback));
    });
  }, [strategyId, rerunSeed]);

  const stopPolling = useCallback(() => { if (pollRef.current) clearInterval(pollRef.current); pollRef.current = null; }, []);
  const refreshRun = useCallback(async (id: string) => {
    try {
      const status = await fundedBacktestsApi.getStatus(id); setRunStatus(status);
      if (!runStartedAt && status.started_at) {
        const parsedStart = Date.parse(status.started_at);
        if (Number.isFinite(parsedStart)) setRunStartedAt(parsedStart);
      }
      if (isFundedRunTerminal(status.status)) {
        stopPolling(); setRunning(false); const detail = await fundedBacktestsApi.getRun(id); setRunDetail(detail);
      }
    } catch (err) { stopPolling(); setRunning(false); toast.error(parseApiError(err).message); }
  }, [stopPolling, runStartedAt]);
  useEffect(() => () => stopPolling(), [stopPolling]);

  const doPreview = async () => {
    if (!requestPayload) return;
    if (startDate > endDate) return toast.error("Start date must be before end date.");
    setPreviewing(true);
    try {
      const result = await fundedBacktestsApi.preview(requestPayload);
      setPreview(result);
      setPreviewFingerprint(currentFingerprint);
      const balances = result.billing?.balances;
      if (balances) {
        setCreditSnapshot((prev) => ({
          totalAvailable: Number(balances.total_available ?? prev.totalAvailable),
          includedBalance: Number(balances.included_balance ?? prev.includedBalance),
          walletBalance: Number(balances.wallet_balance ?? prev.walletBalance),
          deductionOrder: result.billing?.deduction_order || prev.deductionOrder,
          subscriptionState: result.billing?.subscription_state ?? prev.subscriptionState,
        }));
      }
      if (result.billing?.has_enough_credits === false) {
        toast.error("Preview complete, but available credits are insufficient for this funded backtest.");
      } else if (result.billing?.can_run === false) {
        toast.error("Preview complete, but the selected candle scope is not runnable.");
      } else {
        toast.success("Funded backtest preview is valid and credit cost is ready.");
      }
    }
    catch (err) { setPreview(null); setPreviewFingerprint(""); toast.error(parseApiError(err).message); }
    finally { setPreviewing(false); }
  };

  const doRun = async () => {
    if (!requestPayload || !canRun) return;
    const localStartedAt = Date.now();
    setRunStartedAt(localStartedAt); setRunElapsedSeconds(0);
    setRunning(true); setRunDetail(null); setRunStatus({ id: "", status: "PENDING", progress: 0, message: "Queueing funded backtest..." });
    try {
      const result = await fundedBacktestsApi.run(requestPayload); const id = result.funded_backtest_id; setRunId(id);
      if (result.credits) {
        setCreditSnapshot((prev) => ({
          totalAvailable: Number(result.credits?.total_balance_after ?? prev.totalAvailable),
          includedBalance: Number(result.credits?.included_balance_after ?? prev.includedBalance),
          walletBalance: Number(result.credits?.balance_after ?? prev.walletBalance),
          deductionOrder: result.credits?.deduction_order || prev.deductionOrder,
          subscriptionState: result.credits?.subscription_state ?? prev.subscriptionState,
        }));
      }
      const initialStatus: FundedRunStatus = { id, status: result.status, progress: result.progress ?? 5, message: result.message || "Funded backtest started.", started_at: result.started_at, current_phase: result.current_phase, trades_processed: result.trades_processed, current_balance: result.final_balance, current_equity: result.final_equity };
      if (result.started_at) { const parsedStart = Date.parse(result.started_at); if (Number.isFinite(parsedStart)) setRunStartedAt(parsedStart); }
      setRunStatus(initialStatus);
      if (isFundedRunTerminal(result.status)) { setRunning(false); setRunDetail(await fundedBacktestsApi.getRun(id)); }
      else { stopPolling(); pollRef.current = setInterval(() => refreshRun(id), 2500); await refreshRun(id); }
      toast.success("Funded simulation started.");
    } catch (err: any) {
      setRunning(false); const parsed = parseApiError(err); const failedId = parsed.raw?.detail?.funded_backtest_id;
      if (failedId) { setRunId(failedId); try { setRunDetail(await fundedBacktestsApi.getRun(failedId)); } catch {} }
      toast.error(parsed.message);
    }
  };

  const updateRuntimeSection = (section: keyof RuntimeConfig, key: string, value: any) => setRuntimeConfig((prev) => ({ ...prev, [section]: { ...prev[section], [key]: value } }));
  const profilePrimaryPhase = selectedProfile?.phases?.[0];
  const payout = selectedProfile?.payout_config;
  const summary = runDetail?.summary || {};
  const resultStatus = runDetail?.status || runStatus?.status;
  const sourceOpportunityCount = Number(summary.source_opportunity_count ?? summary.source_trade_count ?? 0);
  const executedFundedCount = Number(summary.executed_funded_trade_count ?? summary.total_trades ?? runStatus?.trades_processed ?? 0);
  const skippedFundedCount = Number(summary.skipped_funded_opportunities ?? summary.skipped_unsafe_opportunities ?? 0);
  const resultTone = resultStatus && isFundedRunFailure(resultStatus) ? "failure" : resultStatus && isFundedRunSuccess(resultStatus) ? "success" : resultStatus === "INCOMPLETE" ? "incomplete" : resultStatus && ["SIMULATION_ERROR", "ERROR"].includes(resultStatus) ? "error" : "running";
  const incompleteReason = String(summary.incomplete_reason || "");
  const incompleteMessage = incompleteReason === "RISK_CAPACITY_EXHAUSTED"
    ? "The account did not breach a hard rule, but remaining funded loss capacity became too small to safely size many later opportunities. Those opportunities were skipped instead of forcing a drawdown breach."
    : incompleteReason === "NO_TRADES"
      ? "The selected historical range completed without an executable funded trade."
      : "The account did not breach a hard rule, but the selected historical range ended before all pass requirements were completed.";
  const resultHeadline = running ? "Funded Simulation Running" : resultTone === "success" ? fundedStatusLabel(resultStatus) : resultTone === "failure" ? "Challenge Failed" : resultTone === "incomplete" ? "Simulation Incomplete — No Hard Failure" : resultTone === "error" ? "Simulation Error" : fundedStatusLabel(resultStatus);
  const billingPreview = preview?.billing;
  const availableCredits = Number(billingPreview?.balances?.total_available ?? creditSnapshot.totalAvailable ?? 0);
  const includedCredits = Number(billingPreview?.balances?.included_balance ?? creditSnapshot.includedBalance ?? 0);
  const walletCredits = Number(billingPreview?.balances?.wallet_balance ?? creditSnapshot.walletBalance ?? 0);
  const estimatedRunCost = billingPreview ? Number(billingPreview.credit_cost ?? billingPreview.estimated_run_cost ?? 0) : null;
  const projectedBalance = billingPreview ? Number(billingPreview.balances?.balance_after_run ?? Math.max(availableCredits - Number(estimatedRunCost || 0), 0)) : null;
  const insufficientCredits = Boolean(billingPreview && billingPreview.has_enough_credits === false);
  const deductionOrderLabel = (billingPreview?.deduction_order || creditSnapshot.deductionOrder || ["subscription", "wallet"])
    .map((item: string) => item === "subscription" ? "Subscription" : item === "wallet" ? "Wallet" : item)
    .join(" → ");

  return <div className="mx-auto w-full min-w-0 max-w-[1600px] space-y-6">
    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
      <div><div className="flex items-center gap-2"><Badge className="bg-fuchsia-500/15 text-fuchsia-200">Funded Simulation</Badge>{preview?.warnings?.some((w: string) => w.includes("TRADE_LEVEL")) && <Badge variant="outline">Drawdown: Trade Level</Badge>}</div><h1 className="mt-3 text-2xl font-bold sm:text-3xl">Funded Backtest Studio</h1><p className="mt-2 max-w-4xl text-sm text-muted-foreground sm:text-base">Test published strategies against funded-account rules, dynamic risk plans, drawdown limits, challenge phases, and payout requirements.</p></div>
      <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => { setRunId(""); setRunStatus(null); setRunDetail(null); }}>New Simulation</Button><Button onClick={() => { setProfileDialogMode("create"); setProfileDialogInitial(null); setProfileDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Add Funded Account</Button></div>
    </div>

    <div className="grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      <Card className="border-white/10 bg-white/[0.035]"><CardContent className="p-4"><p className="text-xs text-muted-foreground">Available Credits</p><p className="mt-1 text-2xl font-semibold">{availableCredits.toLocaleString()}</p><p className="mt-1 text-[11px] text-muted-foreground">Deduction order: {deductionOrderLabel}</p></CardContent></Card>
      <Card className="border-white/10 bg-white/[0.035]"><CardContent className="p-4"><p className="text-xs text-muted-foreground">Subscription Credits</p><p className="mt-1 text-2xl font-semibold">{includedCredits.toLocaleString()}</p><p className="mt-1 text-[11px] text-muted-foreground">Included plan credits are used first.</p></CardContent></Card>
      <Card className="border-white/10 bg-white/[0.035]"><CardContent className="p-4"><p className="text-xs text-muted-foreground">Wallet Credits</p><p className="mt-1 text-2xl font-semibold">{walletCredits.toLocaleString()}</p><p className="mt-1 text-[11px] text-muted-foreground">Top-up wallet credits are used after plan credits.</p></CardContent></Card>
      <Card className="border-white/10 bg-white/[0.035]"><CardContent className="p-4"><p className="text-xs text-muted-foreground">Estimated Run Cost</p><p className="mt-1 text-2xl font-semibold">{estimatedRunCost == null ? "—" : estimatedRunCost.toLocaleString()}</p><p className="mt-1 text-[11px] text-muted-foreground">Based on selected/billable candles using the Standard Backtest pricing rule.</p></CardContent></Card>
      <Card className={`border-white/10 bg-white/[0.035] ${insufficientCredits ? "border-red-400/30" : ""}`}><CardContent className="p-4"><p className="text-xs text-muted-foreground">Balance After Run</p><p className={`mt-1 text-2xl font-semibold ${insufficientCredits ? "text-red-300" : ""}`}>{projectedBalance == null ? "—" : projectedBalance.toLocaleString()}</p><p className="mt-1 text-[11px] text-muted-foreground">{insufficientCredits ? "Insufficient credits for current funded scope." : "Projected total after deduction."}</p></CardContent></Card>
    </div>

    {insufficientCredits && <div className="flex flex-col gap-3 rounded-xl border border-red-400/25 bg-red-400/10 p-4 text-sm text-red-100 sm:flex-row sm:items-center sm:justify-between"><div><strong>Insufficient credits.</strong> This funded simulation uses the same candle-based cost rule as Standard Backtest. Reduce the selected candle scope, upgrade your subscription, or top up wallet credits.</div><div className="flex gap-2"><Button size="sm" variant="outline" asChild><Link href="/pricing">View Plans</Link></Button><Button size="sm" asChild><Link href="/credits">Top-up Credits</Link></Button></div></div>}

    {selectedProfile && <div className="grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
      {[
        ["Account Size", formatCurrency(Number(selectedProfile.account_size), currencySymbolForCode(selectedProfile.account_currency))],
        ["Type", challengeLabel(selectedProfile.challenge_type)],
        [selectedProfile.challenge_type === "INSTANT" ? "Payout Target" : "Phase 1 Target", selectedProfile.challenge_type === "INSTANT" ? formatPercent(payout?.profit_target_pct) : formatPercent(profilePrimaryPhase?.profit_target_pct)],
        ["Daily DD", selectedProfile.challenge_type === "INSTANT" ? formatPercent(Number(selectedProfile.rules_json?.daily_drawdown_pct || 0)) : formatPercent(profilePrimaryPhase?.daily_drawdown_pct)],
        ["Max DD", selectedProfile.challenge_type === "INSTANT" ? formatPercent(Number(selectedProfile.rules_json?.max_drawdown_pct || 0)) : formatPercent(profilePrimaryPhase?.max_drawdown_pct)],
        ["Risk Mode", riskMode === "DYNAMIC" ? "Dynamic" : `Fixed ${formatPercent(fixedRiskPct)}`],
      ].map(([label, value]) => <Card key={label} className="border-white/10 bg-white/[0.035]"><CardContent className="p-4"><p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p><p className="mt-1 font-semibold">{value}</p></CardContent></Card>)}
    </div>}

    <div className="grid min-w-0 gap-6 2xl:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
      <div className="contents">
        <Card className="order-1 min-w-0"><CardHeader><div className="flex items-start justify-between gap-3"><div><CardTitle>1. Funded Account</CardTitle><CardDescription>Select saved rules or create a custom account profile.</CardDescription></div><WalletCards className="h-5 w-5 text-fuchsia-300" /></div></CardHeader><CardContent className="space-y-4">
          {profilesLoading ? <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading funded accounts…</div> : profiles.length === 0 ? <div className="rounded-xl border border-dashed border-white/15 p-5 text-sm text-muted-foreground">No funded accounts yet. Create an account profile to start testing strategies against funded rules.</div> : <Select value={selectedProfileId} onValueChange={setSelectedProfileId}><SelectTrigger><SelectValue placeholder="Select funded account" /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl">{profiles.map((p) => <SelectItem key={p.id} value={p.id}>{p.name} · {challengeLabel(p.challenge_type)} · {formatCurrency(Number(p.account_size), currencySymbolForCode(p.account_currency))}</SelectItem>)}</SelectContent></Select>}
          {selectedProfile && <div className="rounded-xl border border-white/10 bg-black/10 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-medium">{selectedProfile.name}</p><p className="text-sm text-muted-foreground">{selectedProfile.provider_name || "Custom provider"} · {selectedProfile.is_template ? "System template" : "My account"}</p></div><div className="flex gap-1">{(!selectedProfile.is_template || isAdmin) && <Button size="sm" variant="ghost" onClick={() => { setProfileDialogMode("edit"); setProfileDialogInitial(selectedProfile); setProfileDialogOpen(true); }}><Edit3 className="mr-1 h-4 w-4" />Edit</Button>}<Button size="sm" variant="ghost" onClick={() => { setProfileDialogMode("duplicate"); setProfileDialogInitial(selectedProfile); setProfileDialogOpen(true); }}><Copy className="mr-1 h-4 w-4" />Duplicate</Button>{(!selectedProfile.is_template || isAdmin) && <Button size="sm" variant="ghost" className="text-red-300" onClick={async () => { try { await fundedBacktestsApi.deactivateProfile(selectedProfile.id); toast.success("Funded account deactivated."); setSelectedProfileId(""); await loadProfiles(); } catch (err) { toast.error(parseApiError(err).message); } }}><Trash2 className="mr-1 h-4 w-4" />Deactivate</Button>}</div></div>
            {selectedProfile.phases.length > 0 && <div className="mt-4 overflow-x-auto rounded-lg border border-white/10"><table className="w-full min-w-[620px] text-left text-xs"><thead className="bg-black/25 text-muted-foreground"><tr><th className="px-3 py-2">Phase</th><th className="px-3 py-2">Target</th><th className="px-3 py-2">Daily DD</th><th className="px-3 py-2">Max DD</th><th className="px-3 py-2">Min Days</th><th className="px-3 py-2">Qualifying</th></tr></thead><tbody>{selectedProfile.phases.map((phase) => <tr key={phase.sequence} className="border-t border-white/10"><td className="px-3 py-2 font-medium text-foreground">{phase.phase_name}</td><td className={`px-3 py-2 ${phase.profit_target_required && Number(phase.profit_target_pct || 0) <= 0 ? "font-semibold text-red-300" : ""}`}>{formatPercent(phase.profit_target_pct)}</td><td className="px-3 py-2">{formatPercent(phase.daily_drawdown_pct)}<span className="block text-[10px] text-muted-foreground">{dailyDdLabel(phase.daily_drawdown_mode)}</span></td><td className="px-3 py-2">{formatPercent(phase.max_drawdown_pct)}<span className="block text-[10px] text-muted-foreground">{maxDdLabel(phase.max_drawdown_mode)}</span></td><td className="px-3 py-2">{phase.minimum_trading_days}</td><td className="px-3 py-2">{phase.qualifying_day_mode === "MIN_PROFIT_DAY" ? `Min ${formatPercent(phase.minimum_qualifying_day_profit_pct)}` : "Any trade day"}</td></tr>)}</tbody></table></div>}
            {invalidRequiredPhaseTargets && <div className="mt-3 rounded-lg border border-red-400/30 bg-red-400/10 p-3 text-xs text-red-100"><strong>Profile needs correction:</strong> a required challenge phase has a 0% profit target. Edit the funded account and set the intended target (for example Phase 2 = 5%) before Preview/Run.</div>}
          </div>}
        </CardContent></Card>

        <Card className="order-3 min-w-0"><CardHeader><CardTitle>3. Funded Risk Plan</CardTitle><CardDescription>Requested risk is still capped by the backend funded safety guard.</CardDescription></CardHeader><CardContent className="space-y-4">
          <div><Label>Risk Mode</Label><Select value={riskMode} onValueChange={(v) => setRiskMode(v as FundedRiskMode)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl"><SelectItem value="DYNAMIC">Dynamic Risk</SelectItem><SelectItem value="FIXED">Fixed Risk</SelectItem></SelectContent></Select></div>
          {riskMode === "FIXED" ? <div><Label>Risk Per Trade %</Label><PercentInput value={fixedRiskPct} onChange={setFixedRiskPct} /><p className="mt-1 text-xs text-muted-foreground">Requested risk stays fixed, but effective risk may be reduced near drawdown limits.</p></div> : <div className="space-y-2"><p className="text-sm font-medium">Account Risk Ladder</p>{selectedProfile?.risk_tiers?.length ? selectedProfile.risk_tiers.map((tier, idx) => <div key={tier.sort_order} className="flex items-center justify-between rounded-lg border border-white/10 px-3 py-2 text-sm"><span>{idx === 0 ? "Below" : tier.min_account_return_pct == null ? "Below" : `${decimalToPercent(tier.min_account_return_pct).toFixed(1)}%`} → {idx === selectedProfile.risk_tiers.length - 1 ? "Above" : tier.max_account_return_pct == null ? "Above" : `${decimalToPercent(tier.max_account_return_pct).toFixed(1)}%`}</span><Badge variant="outline">{formatPercent(tier.risk_percent)}</Badge></div>) : <p className="text-sm text-amber-300">This profile has no saved dynamic risk tiers.</p>}</div>}
          <div><Label>Loss-Boundary Safety Buffer % <span className="text-white/45 font-normal">(optional)</span></Label><PercentInput value={safetyBufferPct} onChange={setSafetyBufferPct} /><p className="mt-1.5 text-[11px] leading-relaxed text-white/55">Default 0%. This is an extra conservative margin on remaining drawdown capacity, not a prop-firm rule. Example: with $100 loss capacity and a 5% buffer, at most $95 is made available to the sizing guard.</p></div>
          <div className="rounded-xl border border-blue-400/20 bg-blue-400/10 p-3 text-xs text-blue-100">Effective trade risk may be automatically reduced when remaining daily or maximum drawdown capacity is smaller than requested risk. Unsafe minimum-lot trades can be skipped by the backend.</div>
        </CardContent></Card>
      </div>

      <div className="contents">
        <Card className="order-2 min-w-0"><CardHeader><CardTitle>2. Strategy & Market</CardTitle><CardDescription>Uses the same strategy catalog, instrument master, timeframe API, dates and runtime configuration as normal Backtest Studio.</CardDescription></CardHeader><CardContent className="grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2"><Label>Strategy</Label><Select value={strategyId} onValueChange={setStrategyId}><SelectTrigger><SelectValue placeholder="Select published strategy" /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl">{strategies.map((s) => <SelectItem key={String(s.id)} value={String(s.id)}>{s.name}</SelectItem>)}</SelectContent></Select></div>
          <div><Label>Instrument</Label><Select value={instrumentId} onValueChange={setInstrumentId}><SelectTrigger><SelectValue placeholder="Select instrument" /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl">{instruments.filter((i) => i.is_active !== false).map((i) => <SelectItem key={i.id} value={String(i.id)}>{i.symbol}{i.name ? ` · ${i.name}` : ""}</SelectItem>)}</SelectContent></Select></div>
          <div><Label>Timeframe</Label><Select value={timeframe} onValueChange={setTimeframe}><SelectTrigger><SelectValue placeholder="Select timeframe" /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl">{timeframes.map((tf) => <SelectItem key={tf} value={tf}>{tf}</SelectItem>)}</SelectContent></Select></div>
          <div><Label>Start Date</Label><Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></div>
          <div><Label>End Date</Label><Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></div>
          <div className="md:col-span-2 flex flex-wrap gap-2"><Button variant="outline" onClick={() => setRuntimeOpen(true)} disabled={!strategyId}><SlidersHorizontal className="mr-2 h-4 w-4" />Strategy Runtime Settings</Button><Badge variant="outline">RR {runtimeConfig.sl_tp?.rr_ratio ?? "—"}</Badge><Badge variant="outline">SL {runtimeConfig.sl_tp?.sl_mode ?? "—"}</Badge></div>

          <button type="button" className="md:col-span-2 flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.025] p-3 text-left" onClick={() => setAdvancedOpen((v) => !v)}><div><p className="text-sm font-medium">Advanced Filters</p><p className="text-xs text-muted-foreground">Weekday and session filtering using the existing backend request structure.</p></div>{advancedOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}</button>
          {advancedOpen && <div className="md:col-span-2 space-y-4 rounded-xl border border-white/10 p-4"><label className="flex items-center gap-2 text-sm"><Checkbox checked={advancedEnabled} onCheckedChange={(v) => setAdvancedEnabled(Boolean(v))} /> Enable Advanced Filters</label><div className={advancedEnabled ? "space-y-4" : "pointer-events-none space-y-4 opacity-50"}><div><Label>Weekdays</Label><div className="mt-2 flex flex-wrap gap-2">{["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY"].map((d) => <Button key={d} type="button" size="sm" variant={days.includes(d) ? "default" : "outline"} onClick={() => setDays((prev) => prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d])}>{d.slice(0,3)}</Button>)}</div></div><div className="grid gap-4 md:grid-cols-2"><div><Label>Session</Label><Select value={session} onValueChange={setSession}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white shadow-2xl"><SelectItem value="ALL">All Sessions</SelectItem><SelectItem value="ASIAN">Asian</SelectItem><SelectItem value="LONDON">London</SelectItem><SelectItem value="NEW_YORK">New York</SelectItem><SelectItem value="CUSTOM">Custom</SelectItem></SelectContent></Select></div><div><Label>Timezone</Label><Input value={advancedTimezone} onChange={(e) => setAdvancedTimezone(e.target.value)} /></div></div>{session === "CUSTOM" && <div className="grid gap-4 md:grid-cols-2"><div><Label>Start Time</Label><Input type="time" value={customStart} onChange={(e) => setCustomStart(e.target.value)} /></div><div><Label>End Time</Label><Input type="time" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} /></div></div>}</div></div>}
        </CardContent></Card>

        <Card className="order-4 min-w-0"><CardHeader><CardTitle>4–6. Rules Preview & Run</CardTitle><CardDescription>Preview validates profile ownership, market data, strategy/instrument references, risk mode and immutable snapshots before execution.</CardDescription></CardHeader><CardContent className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-black/10 p-4 text-sm"><div className="grid gap-3 sm:grid-cols-2"><div><p className="text-xs text-muted-foreground">ACCOUNT</p><p className="font-medium">{selectedProfile?.name || "—"}</p></div><div><p className="text-xs text-muted-foreground">STRATEGY</p><p className="font-medium">{selectedStrategy?.name || "—"}</p></div><div><p className="text-xs text-muted-foreground">MARKET</p><p className="font-medium">{selectedInstrument?.symbol || "—"}{timeframe ? ` · ${timeframe}` : ""}</p></div><div><p className="text-xs text-muted-foreground">RANGE</p><p className="font-medium">{startDate || "—"} → {endDate || "—"}</p></div><div><p className="text-xs text-muted-foreground">RISK</p><p className="font-medium">{riskMode === "DYNAMIC" ? "Dynamic account ladder" : `Fixed ${formatPercent(fixedRiskPct)}`}</p></div><div><p className="text-xs text-muted-foreground">SNAPSHOT</p><p className="font-medium">Rules + runtime saved with run</p></div></div></div>
          {invalidRequiredPhaseTargets && <div className="rounded-xl border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-100"><AlertTriangle className="mr-2 inline h-4 w-4" />A required phase has a 0% target. Edit the funded profile before previewing.</div>}
          {previewStale && <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-3 text-sm text-amber-200"><AlertTriangle className="mr-2 inline h-4 w-4" />Configuration changed after preview. Preview again before running.</div>}
          {preview && !previewStale && <div className={`rounded-xl border p-4 ${insufficientCredits ? "border-red-400/25 bg-red-400/10" : "border-emerald-400/20 bg-emerald-400/10"}`}><div className={`flex items-center gap-2 text-sm font-medium ${insufficientCredits ? "text-red-100" : "text-emerald-100"}`}>{insufficientCredits ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}{insufficientCredits ? "Simulation Preview — Credits Required" : "Simulation Preview Valid"}</div><div className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-5"><div><span className="text-muted-foreground">Raw Candles:</span> {preview.market_data?.candles ?? "—"}</div><div><span className="text-muted-foreground">Billable Candles:</span> {billingPreview?.billable_candles ?? preview.market_data?.selected_candles ?? "—"}</div><div><span className="text-muted-foreground">Estimated Cost:</span> {estimatedRunCost == null ? "—" : `${estimatedRunCost.toLocaleString()} credits`}</div><div><span className="text-muted-foreground">Balance After:</span> {projectedBalance == null ? "—" : `${projectedBalance.toLocaleString()} credits`}</div><div><span className="text-muted-foreground">Engine:</span> {preview.rule_engine_version ?? "—"}</div></div><div className="mt-2 text-xs text-muted-foreground">Coverage: {preview.market_data?.from ?? "—"} → {preview.market_data?.to ?? "—"} · Pricing: same Standard Backtest selected-candle rule · {deductionOrderLabel}</div>{preview.warnings?.map((w: string) => <div key={w} className="mt-2 text-xs text-amber-200">⚠ {w}</div>)}</div>}
          <div className="flex flex-col gap-2 sm:flex-row"><Button variant="outline" className="flex-1" disabled={!canPreview || previewing || running} onClick={doPreview}>{previewing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShieldCheck className="mr-2 h-4 w-4" />}Preview Funded Backtest</Button><Button className="flex-1" disabled={!canRun} onClick={doRun}>{running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}Run Funded Backtest</Button></div>
          <p className="text-xs text-muted-foreground">Account rules, risk settings, runtime settings and instrument specification are snapshotted by the backend. Future profile edits do not change this result.</p>
        </CardContent></Card>
      </div>
    </div>

    {(runStatus || runDetail) && <Card className={`${resultTone === "failure" ? "border-red-400/50" : resultTone === "success" ? "border-emerald-400/50" : resultTone === "incomplete" ? "border-amber-400/50" : resultTone === "error" ? "border-orange-400/50" : "border-blue-400/30"} overflow-hidden`}><div className={`${resultTone === "failure" ? "bg-red-500/15" : resultTone === "success" ? "bg-emerald-500/15" : resultTone === "incomplete" ? "bg-amber-500/15" : resultTone === "error" ? "bg-orange-500/15" : "bg-blue-500/10"} border-b border-white/10 px-5 py-4 sm:px-6`}><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-start gap-3">{running ? <Loader2 className="mt-0.5 h-6 w-6 animate-spin text-blue-300" /> : resultTone === "failure" ? <XCircle className="mt-0.5 h-6 w-6 text-red-300" /> : resultTone === "success" ? <CheckCircle2 className="mt-0.5 h-6 w-6 text-emerald-300" /> : resultTone === "incomplete" ? <AlertTriangle className="mt-0.5 h-6 w-6 text-amber-300" /> : <AlertTriangle className="mt-0.5 h-6 w-6 text-orange-300" />}<div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Funded Result</p><h2 className="text-xl font-bold sm:text-2xl">{resultHeadline}</h2><p className="mt-1 text-sm text-muted-foreground">{resultTone === "incomplete" ? incompleteMessage : resultTone === "failure" ? (runDetail?.failure_reason || runStatus?.failure_reason || "A funded-account rule was breached.") : resultTone === "success" ? "Backend funded rules confirm the terminal success state shown below." : "The backend is processing or reporting this simulation state."}</p></div></div><div className="flex gap-2">{runId && <Button variant="outline" onClick={() => refreshRun(runId)}><RefreshCcw className="mr-2 h-4 w-4" />Refresh</Button>}{runId && isFundedRunTerminal(resultStatus) && <Button asChild><Link href={`/funded-backtest-report/${runId}`}>View Funded Report</Link></Button>}</div></div>{runId && <p className="mt-3 break-all text-[11px] text-muted-foreground">Run ID: {runId}</p>}</div><CardContent className="space-y-5 p-5 sm:p-6">
      {running && <div className="rounded-xl border border-blue-400/25 bg-blue-400/10 p-4">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
          <div><span className="font-semibold">Background Funded Backtest · {Math.round(Number(runStatus?.progress || 0))}%</span><p className="mt-1 text-xs text-muted-foreground">{runStatus?.message || "Funded simulation is running in the background."}</p></div>
          <span className="rounded-md border border-blue-200/20 bg-black/10 px-2 py-1 font-mono text-xs">Elapsed {formatElapsed(runElapsedSeconds)}</span>
        </div>
        <Progress value={Math.max(2, Math.min(100, Number(runStatus?.progress || 0)))} />
      </div>}
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">{[
        ["Current Phase", runStatus?.current_phase ?? runDetail?.current_phase ?? "—"],
        ["Funded Trades", executedFundedCount],
        ["Balance", formatCurrency(Number(runDetail?.final_balance ?? runStatus?.current_balance ?? 0), currencySymbolForCode(selectedProfile?.account_currency || "USD"))],
        ["Trading Days", runDetail?.trading_days ?? runStatus?.trading_days ?? 0],
        ["Qualifying Days", runDetail?.qualifying_days ?? runStatus?.qualifying_days ?? 0],
        ["Calendar Days", runDetail?.calendar_days ?? summary.calendar_days ?? 0],
      ].map(([k,v]) => <div key={String(k)} className="rounded-xl border border-white/10 bg-white/[0.03] p-3"><p className="text-xs text-muted-foreground">{k}</p><p className="mt-1 font-semibold">{String(v)}</p></div>)}</div>
      {(sourceOpportunityCount > 0 || skippedFundedCount > 0) && <div className="overflow-x-auto rounded-xl border border-white/10"><table className="w-full min-w-[620px] text-left text-sm"><thead className="bg-black/20 text-xs uppercase tracking-wide text-muted-foreground"><tr><th className="px-4 py-3">Strategy Opportunities</th><th className="px-4 py-3">Executed Funded Trades</th><th className="px-4 py-3">Skipped by Safety</th><th className="px-4 py-3">Source Mode</th></tr></thead><tbody><tr className="border-t border-white/10"><td className="px-4 py-3 font-semibold">{sourceOpportunityCount || "—"}</td><td className="px-4 py-3 font-semibold">{executedFundedCount}</td><td className="px-4 py-3 font-semibold">{skippedFundedCount}</td><td className="px-4 py-3 text-xs text-muted-foreground">{String(summary.source_generation_mode || "Strategy source trades")}</td></tr></tbody></table><p className="border-t border-white/10 px-4 py-3 text-xs text-muted-foreground">The ordinary strategy opportunity count and the executed funded-trade count are intentionally shown separately. Funded sizing can reduce/skip unsafe trades, but the engine should no longer lose strategy opportunities merely because the funded account size is smaller.</p></div>}
      {runDetail?.phase_summaries?.length ? <div className="overflow-x-auto rounded-xl border border-white/10"><div className="border-b border-white/10 px-4 py-3"><h3 className="font-semibold">Phase Result</h3><p className="text-xs text-muted-foreground">Backend phase records determine pass/fail; the browser does not recalculate challenge state.</p></div><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-black/20 text-xs uppercase tracking-wide text-muted-foreground"><tr><th className="px-4 py-3">Phase</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Start</th><th className="px-4 py-3">End</th><th className="px-4 py-3">Target</th><th className="px-4 py-3">Trading Days</th><th className="px-4 py-3">Qualifying Days</th></tr></thead><tbody>{runDetail.phase_summaries.map((phase: any) => <tr key={String(phase.id || phase.phase_number)} className="border-t border-white/10"><td className="px-4 py-3 font-semibold">{phase.phase_name || `Phase ${phase.phase_number}`}</td><td className="px-4 py-3"><Badge variant="outline" className={String(phase.phase_status || "").includes("FAIL") ? "border-red-400/30 text-red-200" : phase.phase_status === "PASSED" ? "border-emerald-400/30 text-emerald-200" : "border-amber-400/30 text-amber-200"}>{String(phase.phase_status || "INCOMPLETE").replaceAll("_", " ")}</Badge></td><td className="px-4 py-3">{formatCurrency(Number(phase.starting_balance || 0), currencySymbolForCode(selectedProfile?.account_currency || "USD"))}</td><td className="px-4 py-3">{formatCurrency(Number(phase.ending_balance || 0), currencySymbolForCode(selectedProfile?.account_currency || "USD"))}</td><td className="px-4 py-3">{formatPercent(phase.target_pct)}</td><td className="px-4 py-3">{phase.trading_days ?? 0}</td><td className="px-4 py-3">{phase.qualifying_days ?? 0}</td></tr>)}</tbody></table></div> : null}
      {typeof (runStatus?.target_progress as any)?.current_pct === "number" && <div><div className="mb-1 flex justify-between text-xs text-muted-foreground"><span>Target Progress</span><span>{decimalToPercent((runStatus?.target_progress as any).current_pct).toFixed(2)}%</span></div><Progress value={Math.min(100, decimalToPercent((runStatus?.target_progress as any).current_pct))} /></div>}
      {(runDetail?.failure_reason || runStatus?.failure_reason) && <div className="rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-100">{runDetail?.failure_reason || runStatus?.failure_reason}</div>}
      {(runStatus?.technical_error || summary.technical_error) && <div className="rounded-xl border border-amber-400/20 bg-amber-400/10 p-3 text-sm text-amber-100"><strong>Simulation Error:</strong> {runStatus?.technical_error || summary.technical_error}</div>}
      {resultStatus === "INCOMPLETE" && summary.unmet_requirements && <div className="rounded-xl border border-amber-400/25 bg-amber-400/10 p-4"><div className="flex items-center gap-2 text-amber-100"><AlertTriangle className="h-4 w-4" /><p className="font-semibold">Why it is incomplete{incompleteReason === "RISK_CAPACITY_EXHAUSTED" ? " — Risk Capacity Exhausted" : ""}</p></div><div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{Object.entries(summary.unmet_requirements).map(([key, value]) => <div key={key} className="rounded-lg border border-amber-200/10 bg-black/10 px-3 py-2"><p className="text-[11px] uppercase tracking-wide text-amber-100/60">{key.replaceAll("_", " ")}</p><p className="mt-1 text-sm font-medium text-amber-50">{typeof value === "boolean" ? (value ? "Yes" : "No") : String(value ?? "—")}</p></div>)}</div>{summary.completion_explanation && <p className="mt-3 text-xs text-amber-100/80">{String(summary.completion_explanation)}</p>}</div>}
      {summary.payout && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[
        ["Consistency", summary.payout.consistency_pct == null ? "—" : formatPercent(Number(summary.payout.consistency_pct))],
        ["Payout Ready At", summary.payout.payout_ready_at ? formatDateTimeIST(String(summary.payout.payout_ready_at)) : "Not recorded"],
        ["Gross Eligible Profit", formatCurrency(Number(summary.payout.gross_eligible_profit), currencySymbolForCode(selectedProfile?.account_currency || "USD"))],
        ["Estimated Payout", formatCurrency(Number(summary.payout.estimated_payout_amount), currencySymbolForCode(selectedProfile?.account_currency || "USD"))],
      ].map(([k,v]) => <div key={String(k)} className="rounded-xl border border-white/10 p-3"><p className="text-xs text-muted-foreground">{k}</p><p className="mt-1 font-medium">{String(v)}</p></div>)}</div>}
    </CardContent></Card>}

    <RuntimeSettingsDrawer open={runtimeOpen} onClose={() => setRuntimeOpen(false)} title="Strategy Runtime Settings" subtitle="Funded sizing remains authoritative; these settings control strategy execution, SL/TP and trade management." badgeLabel="Funded Run" activeTab={runtimeTab} onTabChange={setRuntimeTab} config={runtimeConfig} updateSection={updateRuntimeSection} strategySchema={runtimeSchema} updateStrategyParam={(key, value) => updateRuntimeSection("strategy_params", key, value)} initialCapital={selectedProfile?.account_size || runtimeConfig.risk?.initial_capital} currency={selectedProfile?.account_currency || selectedInstrument?.account_currency || "USD"} quantityMode={selectedInstrument?.quantity_mode || "—"} instrumentSymbol={selectedInstrument?.symbol || "—"} footerNote="Runtime settings apply to this funded simulation request only." valid={Boolean(strategyId)} onReset={() => setRuntimeConfig(cloneRuntime(runtimeDefaults))} onApply={() => setRuntimeOpen(false)} />

    <ProfileDialog open={profileDialogOpen} onOpenChange={setProfileDialogOpen} initial={profileDialogInitial} mode={profileDialogMode} onSaved={(profile) => loadProfiles(profile.id)} />
  </div>;
}
