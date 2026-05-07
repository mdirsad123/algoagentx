"use client";

import { useEffect, useMemo, useState } from "react";
import { Edit, RefreshCw, ReceiptText, Save, Search, X } from "lucide-react";
import { toast } from "sonner";
import { adminApi, type AdminCreditRule, type AdminCreditRulePayload, type CreditRuleMarket, type CreditRuleOperationType } from "@/lib/api/admin";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

const emptyForm: AdminCreditRulePayload = {
  name: "",
  operation_type: "BACKTEST",
  market: "ALL",
  instrument_symbol: "",
  timeframe: "",
  base_credits: 1,
  per_1000_candles_credits: 1,
  min_credits: 1,
  max_credits: null,
  advanced_filter_multiplier: 1,
  is_active: true,
  priority: 100,
};

function normalize(form: AdminCreditRulePayload): AdminCreditRulePayload {
  const blank = (value: any) => value === "" || value === undefined ? null : value;
  return {
    ...form,
    name: String(form.name || "").trim(),
    operation_type: (String(form.operation_type || "BACKTEST").trim().toUpperCase() || "BACKTEST") as CreditRuleOperationType,
    market: (String(form.market || "").trim().toUpperCase() || null) as CreditRuleMarket | null,
    instrument_symbol: String(form.instrument_symbol || "").trim().toUpperCase() || null,
    timeframe: String(form.timeframe || "").trim().toUpperCase() || null,
    base_credits: Number(form.base_credits || 0),
    per_1000_candles_credits: Number(form.per_1000_candles_credits || 0),
    min_credits: Number(form.min_credits || 0),
    max_credits: blank(form.max_credits) == null ? null : Number(form.max_credits),
    advanced_filter_multiplier: Number(form.advanced_filter_multiplier || 1),
    priority: Number(form.priority || 100),
  };
}

function ruleToForm(rule: AdminCreditRule): AdminCreditRulePayload {
  return {
    name: rule.name,
    operation_type: rule.operation_type,
    market: rule.market || "",
    instrument_symbol: rule.instrument_symbol || "",
    timeframe: rule.timeframe || "",
    base_credits: Number(rule.base_credits || 0),
    per_1000_candles_credits: Number(rule.per_1000_candles_credits || 0),
    min_credits: Number(rule.min_credits || 0),
    max_credits: rule.max_credits ?? null,
    advanced_filter_multiplier: Number(rule.advanced_filter_multiplier || 1),
    is_active: Boolean(rule.is_active),
    priority: Number(rule.priority || 100),
  };
}

function validate(form: AdminCreditRulePayload) {
  if (!String(form.name || "").trim()) return "Rule name is required";
  if (Number(form.base_credits) < 0) return "Base credits must be 0 or greater";
  if (Number(form.per_1000_candles_credits) < 0) return "Per 1000 candles cost must be 0 or greater";
  if (Number(form.min_credits) < 0) return "Min credits must be 0 or greater";
  if (form.max_credits != null && Number(form.max_credits) < Number(form.min_credits)) return "Max credits must be greater than or equal to min credits";
  if (Number(form.advanced_filter_multiplier) <= 0) return "Advanced filter multiplier must be greater than 0";
  if (Number(form.priority) <= 0) return "Priority must be positive";
  return null;
}

function RuleForm({ form, setForm, saving, mode, onSubmit, onCancel }: {
  form: AdminCreditRulePayload;
  setForm: (next: AdminCreditRulePayload) => void;
  saving: boolean;
  mode: "create" | "edit";
  onSubmit: () => void;
  onCancel?: () => void;
}) {
  const update = (patch: Partial<AdminCreditRulePayload>) => setForm({ ...form, ...patch });
  return (
    <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-semibold text-white"><ReceiptText className="h-5 w-5 text-cyan-300" />{mode === "create" ? "Create Credit Rule" : "Edit Credit Rule"}</h2>
          <p className="mt-1 text-sm text-purple-100/65">Control backtest credit usage by market, instrument, timeframe, candle count, and filters.</p>
        </div>
        {onCancel && <Button variant="outline" className="gap-2 border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={onCancel}><X className="h-4 w-4" />Cancel</Button>}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2"><Label>Rule name</Label><Input value={form.name} onChange={(e) => update({ name: e.target.value })} placeholder="Default Backtest Candle Rule" className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Operation</Label><select value={form.operation_type} onChange={(e) => update({ operation_type: e.target.value as CreditRuleOperationType })} className="h-10 w-full rounded-md border border-white/10 bg-[#3a1a63] px-3 text-sm text-white"><option value="BACKTEST">Backtest</option><option value="AI_SCREENER">AI Screener</option><option value="LIVE_DEPLOYMENT">Live Deployment</option><option value="OTHER">Other</option></select></div>
        <div className="space-y-2"><Label>Market</Label><select value={form.market || ""} onChange={(e) => update({ market: e.target.value as CreditRuleMarket })} className="h-10 w-full rounded-md border border-white/10 bg-[#3a1a63] px-3 text-sm text-white"><option value="">Any</option><option value="ALL">All</option><option value="FOREX">Forex</option><option value="INDIAN">Indian</option><option value="CRYPTO">Crypto</option></select></div>
        <div className="space-y-2"><Label>Instrument optional</Label><Input value={form.instrument_symbol || ""} onChange={(e) => update({ instrument_symbol: e.target.value.toUpperCase() })} placeholder="XAUUSD" className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Timeframe optional</Label><Input value={form.timeframe || ""} onChange={(e) => update({ timeframe: e.target.value.toUpperCase() })} placeholder="5M / M5 / 15M" className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Priority</Label><Input type="number" min={1} value={form.priority} onChange={(e) => update({ priority: Number(e.target.value) })} className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Base credits</Label><Input type="number" min={0} value={form.base_credits} onChange={(e) => update({ base_credits: Number(e.target.value) })} className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Per 1000 candles</Label><Input type="number" min={0} step="0.01" value={form.per_1000_candles_credits} onChange={(e) => update({ per_1000_candles_credits: Number(e.target.value) })} className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Advanced filter multiplier</Label><Input type="number" min={0.01} step="0.01" value={form.advanced_filter_multiplier} onChange={(e) => update({ advanced_filter_multiplier: Number(e.target.value) })} className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Min credits</Label><Input type="number" min={0} value={form.min_credits} onChange={(e) => update({ min_credits: Number(e.target.value) })} className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Max credits optional</Label><Input type="number" min={0} value={form.max_credits ?? ""} onChange={(e) => update({ max_credits: e.target.value === "" ? null : Number(e.target.value) })} placeholder="No cap" className="border-white/10 bg-white/10 text-white" /></div>
        <label className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white md:col-span-1">
          <span><span className="font-semibold">Active rule</span><span className="mt-1 block text-xs text-purple-100/60">Inactive rules are ignored.</span></span>
          <input type="checkbox" checked={form.is_active} onChange={(e) => update({ is_active: e.target.checked })} className="h-4 w-4 accent-fuchsia-500" />
        </label>
      </div>
      <Button onClick={onSubmit} disabled={saving} className="mt-5 w-full gap-2 bg-gradient-to-r from-fuchsia-500 via-violet-500 to-blue-500 text-white disabled:opacity-60"><Save className="h-4 w-4" />{saving ? "Saving..." : mode === "create" ? "Create rule" : "Save rule"}</Button>
    </GlassCard>
  );
}

export default function AdminCreditRulesPage() {
  const [items, setItems] = useState<AdminCreditRule[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<AdminCreditRulePayload>(emptyForm);
  const [editing, setEditing] = useState<AdminCreditRule | null>(null);

  const stats = useMemo(() => ({
    total: items.length,
    active: items.filter((item) => item.is_active).length,
    backtest: items.filter((item) => item.operation_type === "BACKTEST").length,
    custom: items.filter((item) => item.instrument_symbol || item.timeframe || (item.market && item.market !== "ALL")).length,
  }), [items]);

  const load = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getCreditRules(search.trim() || undefined);
      setItems(data.items || []);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to load credit rules");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const submit = async () => {
    const payload = normalize(form);
    const error = validate(payload);
    if (error) { toast.error(error); return; }
    try {
      setSaving(true);
      if (editing) {
        await adminApi.updateCreditRule(editing.id, payload);
        toast.success("Credit rule updated");
      } else {
        await adminApi.createCreditRule(payload);
        toast.success("Credit rule created");
      }
      setForm(emptyForm);
      setEditing(null);
      await load();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Unable to save credit rule");
    } finally {
      setSaving(false);
    }
  };

  const edit = (rule: AdminCreditRule) => { setEditing(rule); setForm(ruleToForm(rule)); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const toggle = async (rule: AdminCreditRule) => {
    try {
      await adminApi.toggleCreditRule(rule.id, !rule.is_active);
      toast.success(!rule.is_active ? "Rule activated" : "Rule deactivated");
      await load();
    } catch (error: any) { toast.error(error?.response?.data?.detail || "Unable to update rule status"); }
  };

  return (
    <div className="space-y-8 p-6">
      <PageHeader title="Credit Rules" description="Admin-managed usage pricing for backtests and future billable operations." />
      <div>
        <h1 className="text-3xl font-bold text-lime-300">Credit Expense Rules</h1>
        <p className="mt-2 text-purple-100">Make one-year, high-candle backtests cost the correct credits without code changes.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[['Total Rules', stats.total], ['Active Rules', stats.active], ['Backtest Rules', stats.backtest], ['Custom Scope', stats.custom]].map(([label, value]) => (
          <GlassCard key={label} className="rounded-3xl border border-white/10 p-5 hover:scale-100"><p className="text-xs font-semibold uppercase tracking-wider text-purple-100/60">{label}</p><p className="mt-2 text-3xl font-bold text-white">{value}</p></GlassCard>
        ))}
      </div>

      <RuleForm form={form} setForm={setForm} saving={saving} mode={editing ? "edit" : "create"} onSubmit={submit} onCancel={editing ? () => { setEditing(null); setForm(emptyForm); } : undefined} />

      <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div><h2 className="text-xl font-semibold text-white">Rules Table</h2><p className="mt-1 text-sm text-purple-100/65">Lower priority number wins when multiple rules match.</p></div>
          <div className="flex gap-2"><div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-purple-200/70" /><Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search rule" className="w-64 border-white/10 bg-white/10 pl-9 text-white" /></div><Button variant="outline" onClick={load} className="gap-2 border-white/15 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="h-4 w-4" />Refresh</Button></div>
        </div>
        <div className="overflow-auto rounded-2xl border border-white/10 bg-slate-950/30">
          <table className="w-full min-w-[1200px] text-sm text-white">
            <thead><tr className="border-b border-white/10 text-left text-purple-100/80"><th className="px-4 py-3">Rule</th><th className="px-4 py-3">Scope</th><th className="px-4 py-3">Base</th><th className="px-4 py-3">Per 1000</th><th className="px-4 py-3">Min/Max</th><th className="px-4 py-3">Filter Mult.</th><th className="px-4 py-3">Priority</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th></tr></thead>
            <tbody>
              {loading ? <tr><td colSpan={9} className="px-4 py-8 text-purple-100/70">Loading rules...</td></tr> : items.length === 0 ? <tr><td colSpan={9} className="px-4 py-8 text-center text-purple-100/70">No rules found</td></tr> : items.map((rule) => (
                <tr key={rule.id} className="border-b border-white/5 hover:bg-white/5">
                  <td className="px-4 py-4"><div className="font-semibold text-white">{rule.name}</div><div className="text-xs text-purple-100/60">{rule.operation_type}</div></td>
                  <td className="px-4 py-4"><div>{rule.market || 'Any'} · {rule.instrument_symbol || 'Any instrument'}</div><div className="text-xs text-purple-100/60">Timeframe: {rule.timeframe || 'Any'}</div></td>
                  <td className="px-4 py-4">{rule.base_credits}</td>
                  <td className="px-4 py-4">{rule.per_1000_candles_credits}</td>
                  <td className="px-4 py-4">{rule.min_credits} / {rule.max_credits ?? 'No cap'}</td>
                  <td className="px-4 py-4">{rule.advanced_filter_multiplier}x</td>
                  <td className="px-4 py-4">{rule.priority}</td>
                  <td className="px-4 py-4"><Badge className={rule.is_active ? "bg-emerald-500/15 text-emerald-200" : "bg-rose-500/15 text-rose-200"}>{rule.is_active ? "Active" : "Inactive"}</Badge></td>
                  <td className="px-4 py-4"><div className="flex justify-end gap-2"><Button size="sm" variant="outline" onClick={() => edit(rule)} className="gap-2 border-white/15 bg-white/5 text-white hover:bg-white/10"><Edit className="h-4 w-4" />Edit</Button><Button size="sm" variant="outline" onClick={() => toggle(rule)} className="border-white/15 bg-white/5 text-white hover:bg-white/10">{rule.is_active ? "Deactivate" : "Activate"}</Button></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}
