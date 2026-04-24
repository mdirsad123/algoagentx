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
  type StrategyVersion,
  type StrategyWorkflowStatus,
} from "@/lib/api/admin";
import { backtestsApi } from "@/lib/api/backtests";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";

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
  const [selectedPreset, setSelectedPreset] = useState<string>("");
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");
  const [sandboxInput, setSandboxInput] = useState({ instrument_id: 1, timeframe: "5m", start_date: "2025-12-24", end_date: "2025-12-26", capital: 100000 });

  const load = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [strategyData, instrumentsResponse, versionsResponse, presetResponse] = await Promise.all([
        adminApi.getAdminStrategyById(strategyId),
        backtestsApi.getInstruments(),
        adminApi.listAdminStrategyVersions(strategyId),
        adminApi.listAdminStrategyPresets(),
      ]);
      const instruments = Array.isArray(instrumentsResponse) ? instrumentsResponse : [];
      setCatalog(instruments.map((item: any) => ({ id: Number(item.id), symbol: item.symbol || item.name || `#${item.id}` })));
      setStrategy(strategyData);
      setForm(strategyToForm(strategyData));
      setVersions(versionsResponse.items || []);
      setWorkflow(versionsResponse.workflow || strategyData.workflow || null);
      setPresets(presetResponse.items || []);
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
