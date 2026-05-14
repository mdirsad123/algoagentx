"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, Code2, ImageIcon, Loader2, Rocket, Save, ShieldCheck, UploadCloud, X } from "lucide-react";
import { toast } from "sonner";

import { adminApi, type AdminStrategyCreatePayload, type StrategyVisibility } from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";

const fieldClass = "w-full rounded-xl border border-border/60 bg-card/25 px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";
const areaClass = `${fieldClass} min-h-[112px] resize-y`;

const ALLOWED_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
const MAX_SIZE = 5 * 1024 * 1024;
const MAX_FILES = 6;

const initialForm = {
  name: "",
  visibility: "PRIVATE" as StrategyVisibility,
  strategy_type: "",
  market: "",
  timeframe: "",
  description: "",
  entry_rules: "",
  exit_rules: "",
  confirmation_rules: "",
  risk_rules: "",
  invalidation_rules: "",
  trade_management_rules: "",
  notes: "",
  source_code: "",
  risk_percent: "0.01",
  rr_ratio: "2",
  sl_mode: "STRATEGY_SUGGESTED",
  position_size_mode: "RISK_BASED",
  max_bars_in_trade: "6",
  trailing_enabled: false,
  break_even_enabled: false,
  partial_exit_enabled: false,
  winRate: "",
  sharpeRatio: "",
  maxDrawdown: "",
  totalTrades: "",
  profitFactor: "",
};

function optionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function Section({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <Card className="rounded-2xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
      <CardHeader>
        <CardTitle className="text-base text-foreground">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function Label({ children }: { children: ReactNode }) {
  return <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">{children}</label>;
}

export default function AdminNewStrategyBuilderPage() {
  const router = useRouter();
  const [form, setForm] = useState(initialForm);
  const [images, setImages] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);

  const previews = useMemo(() => images.map((file) => ({ file, url: URL.createObjectURL(file) })), [images]);
  const hasCode = form.source_code.trim().length > 0;

  const update = (key: keyof typeof initialForm, value: any) => setForm((prev) => ({ ...prev, [key]: value }));

  const onSelectImages = (files: FileList | null) => {
    if (!files?.length) return;
    const next = [...images];
    for (const file of Array.from(files)) {
      if (next.length >= MAX_FILES) {
        toast.error("Maximum 6 images are allowed");
        break;
      }
      if (!ALLOWED_TYPES.has(file.type)) {
        toast.error(`${file.name} is not PNG, JPG, or WEBP`);
        continue;
      }
      if (file.size > MAX_SIZE) {
        toast.error(`${file.name} is larger than 5 MB`);
        continue;
      }
      next.push(file);
    }
    setImages(next);
  };

  const saveDraft = async () => {
    const name = form.name.trim();
    if (!name) {
      toast.error("Strategy name is required");
      return;
    }
    setSaving(true);
    try {
      const payload: AdminStrategyCreatePayload = {
        name,
        visibility: form.visibility,
        description: form.description.trim() || null,
        strategy_type: form.strategy_type.trim() || null,
        market: form.market.trim() || null,
        timeframe: form.timeframe.trim() || null,
        entry_rules: form.entry_rules.trim() || null,
        exit_rules: form.exit_rules.trim() || null,
        confirmation_rules: form.confirmation_rules.trim() || null,
        risk_rules: form.risk_rules.trim() || null,
        invalidation_rules: form.invalidation_rules.trim() || null,
        trade_management_rules: form.trade_management_rules.trim() || null,
        notes: form.notes.trim() || null,
        source_code: form.source_code || null,
        performance_metrics: {
          winRate: optionalNumber(form.winRate),
          sharpeRatio: optionalNumber(form.sharpeRatio),
          maxDrawdown: optionalNumber(form.maxDrawdown),
          totalTrades: optionalNumber(form.totalTrades),
          profitFactor: optionalNumber(form.profitFactor),
        },
        parameters: {
          risk_percent: optionalNumber(form.risk_percent) ?? 0.01,
          rr_ratio: optionalNumber(form.rr_ratio) ?? 2,
          sl_mode: form.sl_mode,
          position_size_mode: form.position_size_mode,
          max_bars_in_trade: optionalNumber(form.max_bars_in_trade) ?? 6,
          trailing_enabled: form.trailing_enabled,
          break_even_enabled: form.break_even_enabled,
          partial_exit_enabled: form.partial_exit_enabled,
        },
      };
      const created = await adminApi.createAdminStrategy(payload);
      if (images.length) await adminApi.uploadAdminStrategyAssets(created.id, images);
      toast.success("Strategy draft created");
      router.push(`/admin/strategy-requests/strategies/${created.id}`);
    } catch (error: any) {
      toast.error(error?.message || "Failed to create strategy");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 pb-28">
      <PageHeader
        title="Create Strategy Builder"
        subtitle="Build a manual admin strategy with rules, source code, runtime defaults, metrics, images, and publishing gates."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/admin/strategy-requests?tab=strategies">
              <Button variant="outline" className="rounded-xl border-border/60 bg-card/30"><ArrowLeft className="mr-2 h-4 w-4" />Back</Button>
            </Link>
            <Button onClick={saveDraft} disabled={saving} className="rounded-xl bg-primary text-primary-foreground">
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              Save Draft
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <Section title="Strategy Identity" description="Define where this strategy belongs before attaching code or publishing.">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div><Label>Strategy Name *</Label><input className={fieldClass} value={form.name} onChange={(e) => update("name", e.target.value)} placeholder="Institutional Trend Pullback" /></div>
              <div><Label>Visibility</Label><select className={fieldClass} value={form.visibility} onChange={(e) => update("visibility", e.target.value as StrategyVisibility)}><option value="PRIVATE">Private Admin Draft</option><option value="PUBLIC">Public Template</option></select></div>
              <div><Label>Strategy Type</Label><input className={fieldClass} value={form.strategy_type} onChange={(e) => update("strategy_type", e.target.value)} placeholder="SMC / Momentum / Supply Demand" /></div>
              <div><Label>Market</Label><input className={fieldClass} value={form.market} onChange={(e) => update("market", e.target.value)} placeholder="Forex / Indian / Crypto" /></div>
              <div><Label>Timeframe</Label><input className={fieldClass} value={form.timeframe} onChange={(e) => update("timeframe", e.target.value)} placeholder="5m / 15m / 1h" /></div>
              <div className="md:col-span-2"><Label>Description</Label><textarea className={areaClass} value={form.description} onChange={(e) => update("description", e.target.value)} placeholder="Explain the strategy idea in simple language." /></div>
            </div>
          </Section>

          <Section title="Rule Definition" description="Keep rules structured so users and the backtest workspace understand the strategy clearly.">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div><Label>Entry Rules</Label><textarea className={areaClass} value={form.entry_rules} onChange={(e) => update("entry_rules", e.target.value)} /></div>
              <div><Label>Exit Rules</Label><textarea className={areaClass} value={form.exit_rules} onChange={(e) => update("exit_rules", e.target.value)} /></div>
              <div><Label>Confirmation Rules</Label><textarea className={areaClass} value={form.confirmation_rules} onChange={(e) => update("confirmation_rules", e.target.value)} /></div>
              <div><Label>Risk Rules</Label><textarea className={areaClass} value={form.risk_rules} onChange={(e) => update("risk_rules", e.target.value)} /></div>
              <div><Label>Invalidation Rules</Label><textarea className={areaClass} value={form.invalidation_rules} onChange={(e) => update("invalidation_rules", e.target.value)} /></div>
              <div><Label>Trade Management Rules</Label><textarea className={areaClass} value={form.trade_management_rules} onChange={(e) => update("trade_management_rules", e.target.value)} /></div>
              <div className="md:col-span-2"><Label>Additional Notes</Label><textarea className={areaClass} value={form.notes} onChange={(e) => update("notes", e.target.value)} /></div>
            </div>
          </Section>

          <Section title="Source Code" description="Attach dynamic strategy code now or save the rule draft and add code later in the workspace.">
            <div className="mb-3 flex items-center gap-2"><Badge className={hasCode ? "bg-emerald-500/15 text-emerald-200" : "bg-card/40 text-muted-foreground"}><Code2 className="mr-1 h-3 w-3" />{hasCode ? "Source Code Attached" : "No Source Code Yet"}</Badge></div>
            <textarea className={`${fieldClass} min-h-[360px] font-mono text-xs`} value={form.source_code} onChange={(e) => update("source_code", e.target.value)} placeholder="# Paste Python strategy class here" />
          </Section>
        </div>

        <aside className="space-y-6">
          <Section title="Screenshots / Concept Images" description="Optional for manual admin strategies. Add up to 6 documentation images.">
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-primary/40 bg-primary/10 p-6 text-center transition hover:bg-primary/15">
              <UploadCloud className="mb-2 h-7 w-7 text-primary" />
              <span className="text-sm font-semibold">Upload images</span>
              <span className="mt-1 text-xs text-muted-foreground">PNG, JPG, WEBP · max 5 MB each</span>
              <input type="file" accept="image/png,image/jpeg,image/webp" multiple className="hidden" onChange={(e) => onSelectImages(e.target.files)} />
            </label>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
              {previews.map((item, index) => (
                <div key={item.file.name + index} className="overflow-hidden rounded-xl border border-border/50 bg-card/25">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={item.url} alt={item.file.name} className="h-36 w-full object-cover" />
                  <div className="flex items-center justify-between gap-2 p-2 text-xs text-muted-foreground"><span className="truncate">{item.file.name}</span><button onClick={() => setImages((prev) => prev.filter((_, i) => i !== index))} className="rounded p-1 hover:bg-card/60"><X className="h-3 w-3" /></button></div>
                </div>
              ))}
              {!images.length && <div className="rounded-xl border border-border/50 bg-card/20 p-4 text-sm text-muted-foreground"><ImageIcon className="mb-2 h-5 w-5" />No concept images selected.</div>}
            </div>
          </Section>

          <Section title="Runtime Defaults">
            <div className="space-y-3">
              <div><Label>Risk Percent</Label><input className={fieldClass} value={form.risk_percent} onChange={(e) => update("risk_percent", e.target.value)} /></div>
              <div><Label>Reward Ratio</Label><input className={fieldClass} value={form.rr_ratio} onChange={(e) => update("rr_ratio", e.target.value)} /></div>
              <div><Label>Stop Loss Mode</Label><select className={fieldClass} value={form.sl_mode} onChange={(e) => update("sl_mode", e.target.value)}><option>STRATEGY_SUGGESTED</option><option>ATR</option><option>SWING</option><option>FIXED_PERCENT</option></select></div>
              <div><Label>Position Size Mode</Label><select className={fieldClass} value={form.position_size_mode} onChange={(e) => update("position_size_mode", e.target.value)}><option>RISK_BASED</option><option>FIXED_LOT</option><option>FIXED_QUANTITY</option></select></div>
              <div><Label>Max Bars in Trade</Label><input className={fieldClass} value={form.max_bars_in_trade} onChange={(e) => update("max_bars_in_trade", e.target.value)} /></div>
              {["trailing_enabled", "break_even_enabled", "partial_exit_enabled"].map((key) => <label key={key} className="flex items-center justify-between rounded-xl border border-border/50 bg-card/20 px-3 py-2 text-sm"><span>{key.replaceAll("_", " ")}</span><input type="checkbox" checked={(form as any)[key]} onChange={(e) => update(key as any, e.target.checked)} /></label>)}
            </div>
          </Section>

          <Section title="Performance Metrics">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Win Rate</Label><input className={fieldClass} value={form.winRate} onChange={(e) => update("winRate", e.target.value)} /></div>
              <div><Label>Sharpe</Label><input className={fieldClass} value={form.sharpeRatio} onChange={(e) => update("sharpeRatio", e.target.value)} /></div>
              <div><Label>Drawdown</Label><input className={fieldClass} value={form.maxDrawdown} onChange={(e) => update("maxDrawdown", e.target.value)} /></div>
              <div><Label>Total Trades</Label><input className={fieldClass} value={form.totalTrades} onChange={(e) => update("totalTrades", e.target.value)} /></div>
              <div className="col-span-2"><Label>Profit Factor</Label><input className={fieldClass} value={form.profitFactor} onChange={(e) => update("profitFactor", e.target.value)} /></div>
            </div>
          </Section>

          <Section title="Publishing Gate" description="Save first, then open workspace to verify code, run sandbox backtest, and publish.">
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-muted-foreground"><ShieldCheck className="h-4 w-4" /> Code verification: pending</div>
              <div className="flex items-center gap-2 text-muted-foreground"><CheckCircle2 className="h-4 w-4" /> Sandbox backtest: pending</div>
              <Button disabled className="mt-3 w-full rounded-xl"><Rocket className="mr-2 h-4 w-4" />Publish Public after gates pass</Button>
            </div>
          </Section>
        </aside>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border/50 bg-background/80 px-4 py-3 backdrop-blur-xl md:left-[240px]">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
          <div className="text-xs text-muted-foreground">Create full strategy draft first. Verification, sandbox, deploy and publish continue in the workspace.</div>
          <Button onClick={saveDraft} disabled={saving} className="rounded-xl bg-primary text-primary-foreground">{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}Save Draft</Button>
        </div>
      </div>
    </div>
  );
}
