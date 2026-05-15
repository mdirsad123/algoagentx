"use client";

import { useEffect, useMemo, useState, type ComponentType } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, BarChart3, CheckCircle2, ImageIcon, Loader2, Settings2, ShieldCheck, Sparkles, Target, Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { StrategyAttachmentGallery } from "@/components/strategies/StrategyAttachmentGallery";
import apiClient from "../../../../lib/axios";

type Attachment = {
  id: string;
  publicUrl?: string | null;
  public_url?: string | null;
  originalName?: string | null;
  original_name?: string | null;
  caption?: string | null;
  isCover?: boolean | null;
  is_cover?: boolean | null;
};

type StrategyDetail = {
  id: string;
  name: string;
  description?: string | null;
  visibility?: string | null;
  sourceRequestId?: string | null;
  source_request_id?: string | null;
  strategyType?: string | null;
  strategy_type?: string | null;
  market?: string | null;
  timeframe?: string | null;
  parameters?: Record<string, any> | null;
  entry_rules?: string | null;
  exit_rules?: string | null;
  confirmation_rules?: string | null;
  risk_rules?: string | null;
  invalidation_rules?: string | null;
  trade_management_rules?: string | null;
  notes?: string | null;
  winRate?: number | null;
  sharpeRatio?: number | null;
  maxDrawdown?: number | null;
  totalTrades?: number | null;
  profitFactor?: number | null;
  isDeployablePaper?: boolean;
  isDeployableDemo?: boolean;
  isLiveApproved?: boolean;
  defaultRuntimeConfig?: Record<string, any> | null;
  default_runtime_config?: Record<string, any> | null;
  attachments?: Attachment[];
  assets?: Attachment[];
  strategy_assets?: Attachment[];
  strategyAssets?: Attachment[];
};

type ApiEnvelope<T> = { success?: boolean; data?: T };
const unwrap = <T,>(payload: ApiEnvelope<T> | T): T =>
  payload && typeof payload === "object" && "success" in (payload as any) ? ((payload as ApiEnvelope<T>).data as T) : (payload as T);

function metric(value: number | null | undefined, suffix = "") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return `${Number(value).toFixed(2)}${suffix}`;
}


const FRIENDLY_LABELS: Record<string, string> = {
  risk_percent: "Risk Per Trade",
  initial_capital: "Initial Capital",
  position_size_mode: "Position Size Mode",
  rr_ratio: "Reward Ratio",
  sl_mode: "Stop Loss Mode",
  atr_period: "ATR Period",
  atr_multiplier: "ATR Multiplier",
  trailing_enabled: "Trailing Stop",
  break_even_enabled: "Break Even",
  partial_exit_enabled: "Partial Exit",
  max_bars_in_trade: "Max Bars in Trade",
  fixed_lot: "Fixed Lot",
  fixed_quantity: "Fixed Quantity",
  max_lot_cap: "Max Lot Cap",
  max_quantity_cap: "Max Quantity Cap",
  fixed_price_risk_pct: "Fixed Price Risk",
  swing_lookback: "Swing Lookback",
  entry_mode: "Entry Mode",
  exit_on_opposite_signal: "Exit On Opposite Signal",
  allow_long: "Allow Long Trades",
  allow_short: "Allow Short Trades",
  max_trades_per_day: "Max Trades Per Day",
  max_open_positions: "Max Open Positions",
  intraday_square_off: "Intraday Square Off",
  square_off_time: "Square Off Time",
  trailing_mode: "Trailing Mode",
  trail_start_r: "Trail Starts At",
  trail_atr_multiplier: "Trail ATR Multiplier",
  break_even_trigger_r: "Break Even Trigger",
  break_even_offset_points: "Break Even Offset",
  partial_exit_at_r: "Partial Exit At",
  partial_exit_percent: "Partial Exit Size",
};

type RuntimeGroup = {
  title: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  keys: string[];
  fallbackPath?: string;
};

const RUNTIME_GROUPS: RuntimeGroup[] = [
  {
    title: "Risk & Capital",
    description: "How capital and position size are controlled.",
    icon: ShieldCheck,
    fallbackPath: "risk",
    keys: ["initial_capital", "account_currency", "risk_percent", "position_size_mode", "fixed_lot", "fixed_quantity", "max_lot_cap", "max_quantity_cap"],
  },
  {
    title: "Stop Loss & Target",
    description: "Stop-loss method, target ratio, and ATR settings.",
    icon: Target,
    fallbackPath: "sl_tp",
    keys: ["sl_mode", "rr_ratio", "atr_period", "atr_multiplier", "swing_lookback", "fixed_price_risk_pct"],
  },
  {
    title: "Trade Management",
    description: "Break-even, trailing stop, and partial profit settings.",
    icon: Settings2,
    fallbackPath: "trade_management",
    keys: ["trailing_enabled", "trailing_mode", "trail_start_r", "trail_atr_multiplier", "break_even_enabled", "break_even_trigger_r", "break_even_offset_points", "partial_exit_enabled", "partial_exit_at_r", "partial_exit_percent", "max_bars_in_trade"],
  },
  {
    title: "Execution Rules",
    description: "Order timing, trade direction, and session limits.",
    icon: Zap,
    fallbackPath: "execution",
    keys: ["entry_mode", "exit_on_opposite_signal", "allow_long", "allow_short", "max_trades_per_day", "max_open_positions", "intraday_square_off", "square_off_time"],
  },
];

function titleCase(value: string) {
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getRuntimeValue(runtime: Record<string, any> | null | undefined, group: RuntimeGroup, key: string) {
  if (!runtime) return undefined;
  const nested = group.fallbackPath && runtime[group.fallbackPath] && typeof runtime[group.fallbackPath] === "object" ? runtime[group.fallbackPath][key] : undefined;
  return nested !== undefined ? nested : runtime[key];
}

function formatRuntimeValue(key: string, value: any, currency?: string | null) {
  if (value === null || value === undefined || value === "") {
    if (["fixed_lot", "fixed_quantity", "max_lot_cap", "max_quantity_cap", "account_currency"].includes(key)) return "Auto";
    return "Not Set";
  }
  if (typeof value === "boolean") return value ? "Enabled" : "Disabled";
  if (key === "risk_percent" || key === "fixed_price_risk_pct") {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(numeric * 100 < 1 ? 2 : 1).replace(/\.0$/, "")}%` : String(value);
  }
  if (["rr_ratio", "trail_start_r", "break_even_trigger_r", "partial_exit_at_r"].includes(key)) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${numeric}R` : String(value);
  }
  if (key === "partial_exit_percent") {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${Math.round(numeric * 100)}%` : String(value);
  }
  if (key === "initial_capital") {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${currency || ""}${currency ? " " : ""}${numeric.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : String(value);
  }
  if (typeof value === "string") return titleCase(value);
  if (typeof value === "number") return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return "Configured";
}

function RuntimeSettingsSummary({ runtime }: { runtime?: Record<string, any> | null }) {
  const currency = (runtime?.risk?.account_currency || runtime?.account_currency || runtime?.currency || "") as string;

  if (!runtime || Object.keys(runtime).length === 0) {
    return (
      <GlassCard className="border border-border/60 bg-card/30 p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center gap-2">
          <Settings2 className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold text-foreground">Runtime Settings</h2>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">Runtime settings are not configured for this strategy yet.</p>
      </GlassCard>
    );
  }

  return (
    <GlassCard className="border border-border/60 bg-card/30 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Runtime Settings</h2>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">Human-friendly summary of the default backtest and execution configuration.</p>
        </div>
        <Badge className="w-fit border-primary/30 bg-primary/10 text-primary">Default Preset</Badge>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {RUNTIME_GROUPS.map((group) => {
          const Icon = group.icon;
          const rows = group.keys.map((key) => ({ key, value: getRuntimeValue(runtime, group, key) }));
          return (
            <div key={group.title} className="rounded-2xl border border-border/50 bg-card/25 p-4 shadow-lg backdrop-blur-xl">
              <div className="mb-4 flex items-start gap-3">
                <div className="rounded-xl border border-primary/25 bg-primary/10 p-2 text-primary">
                  <Icon className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">{group.title}</h3>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">{group.description}</p>
                </div>
              </div>
              <div className="space-y-2">
                {rows.map(({ key, value }) => {
                  const isEnabled = typeof value === "boolean" && value;
                  return (
                    <div key={key} className="flex items-center justify-between gap-3 rounded-xl border border-border/40 bg-background/20 px-3 py-2">
                      <span className="text-xs text-muted-foreground">{FRIENDLY_LABELS[key] || titleCase(key)}</span>
                      <span className="flex items-center gap-1 text-right text-xs font-semibold text-foreground">
                        {isEnabled ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" /> : null}
                        {formatRuntimeValue(key, value, currency)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}

function TextBlock({ title, value }: { title: string; value?: string | null }) {
  return (
    <div className="rounded-xl border border-border/50 bg-card/20 p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{title}</p>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground">{value || "—"}</p>
    </div>
  );
}

export default function StrategyDetailPage() {
  const params = useParams<{ strategyId: string }>();
  const router = useRouter();
  const [item, setItem] = useState<StrategyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    apiClient
      .get<ApiEnvelope<StrategyDetail> | StrategyDetail>(`/api/v1/strategies/${params.strategyId}`)
      .then((res) => mounted && setItem(unwrap<StrategyDetail>(res.data)))
      .catch((err) => mounted && setError(err?.response?.data?.detail || err?.message || "Unable to load strategy details"))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, [params.strategyId]);

  const visibility = (item?.visibility || "PRIVATE").toUpperCase();
  const runtime = useMemo(() => item?.defaultRuntimeConfig || item?.default_runtime_config || null, [item]);

  if (loading) {
    return (
      <div className="flex min-h-[360px] items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading strategy details...
      </div>
    );
  }

  if (error || !item) {
    return (
      <GlassCard className="border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
        <p>{error || "Strategy not found"}</p>
        <Button variant="outline" onClick={() => router.push("/strategies")} className="mt-4 rounded-xl border-border/60 bg-card/30 text-foreground">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Strategies
        </Button>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={item.name}
        subtitle={item.description || "Complete strategy rules, deployment readiness, and request screenshots."}
        actions={
          <Button variant="outline" onClick={() => router.push("/strategies")} className="rounded-xl border-border/60 bg-card/30 text-foreground">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Strategies
          </Button>
        }
      />

      <GlassCard className="border border-border/60 bg-card/30 p-6 shadow-xl backdrop-blur-xl">
        <div className="flex flex-wrap gap-2">
          <Badge className={visibility === "PUBLIC" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-primary/30 bg-primary/10 text-primary"}>
            {visibility === "PUBLIC" ? (item.sourceRequestId || item.source_request_id ? "Published From My Request" : "Public Template") : "My Private Strategy"}
          </Badge>
          {[item.strategyType || item.strategy_type, item.market, item.timeframe].filter(Boolean).map((v) => (
            <Badge key={String(v)} variant="secondary" className="border-border/60 bg-card/40 text-foreground">{v}</Badge>
          ))}
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-5">
          <TextBlock title="Win Rate" value={metric(item.winRate, "%")} />
          <TextBlock title="Sharpe Ratio" value={metric(item.sharpeRatio)} />
          <TextBlock title="Drawdown" value={metric(item.maxDrawdown, "%")} />
          <TextBlock title="Total Trades" value={item.totalTrades == null ? "—" : String(Math.round(Number(item.totalTrades)))} />
          <TextBlock title="Profit Factor" value={metric(item.profitFactor)} />
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <Badge className="border-sky-500/30 bg-sky-500/10 text-sky-200">Backtest Ready</Badge>
          {item.isDeployablePaper ? <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-200">Paper Ready</Badge> : null}
          {item.isDeployableDemo ? <Badge className="border-lime-500/30 bg-lime-500/10 text-lime-200">Demo Ready</Badge> : null}
          <Badge className={item.isLiveApproved ? "border-amber-500/30 bg-amber-500/10 text-amber-200" : "border-border/60 bg-card/40 text-muted-foreground"}>
            {item.isLiveApproved ? "Live Approved" : "Live Locked"}
          </Badge>
        </div>
      </GlassCard>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TextBlock title="Entry Rules" value={item.entry_rules || item.parameters?.entry_rules} />
        <TextBlock title="Exit Rules" value={item.exit_rules || item.parameters?.exit_rules} />
        <TextBlock title="Confirmation Rules" value={item.confirmation_rules || item.parameters?.confirmation_rules} />
        <TextBlock title="Risk Rules" value={item.risk_rules || item.parameters?.risk_rules} />
        <TextBlock title="Invalidation Rules" value={item.invalidation_rules || item.parameters?.invalidation_rules} />
        <TextBlock title="Trade Management Rules" value={item.trade_management_rules || item.parameters?.trade_management_rules} />
      </div>

      <TextBlock title="Notes" value={item.notes || item.parameters?.notes} />
      <RuntimeSettingsSummary runtime={runtime} />

      {(() => {
        const docs = (item.assets || item.strategyAssets || item.strategy_assets || []).slice().sort((a: any, b: any) => Number(Boolean(b.isCover ?? b.is_cover)) - Number(Boolean(a.isCover ?? a.is_cover)));
        return docs.length ? (
          <GlassCard className="border border-border/60 bg-card/30 p-6 shadow-xl backdrop-blur-xl">
            <div className="mb-4 flex items-center gap-2">
              <ImageIcon className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold text-foreground">Strategy Documentation Images</h2>
              <Badge className="border-border/60 bg-card/40 text-muted-foreground">{docs.length}</Badge>
            </div>
            <StrategyAttachmentGallery attachments={docs} emptyText="No documentation images available." />
          </GlassCard>
        ) : null;
      })()}

      <div className="flex flex-wrap gap-3">
        <Button onClick={() => router.push(`/backtest?strategyId=${item.id}`)} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
          <BarChart3 className="mr-2 h-4 w-4" /> Backtest Strategy
        </Button>
        <Button variant="outline" onClick={() => router.push(`/strategies/${item.id}/refine`)} className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
          <Sparkles className="mr-2 h-4 w-4" /> Request Refinement
        </Button>
        <Button variant="outline" onClick={() => router.push("/strategies?tab=request")} className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
          <Sparkles className="mr-2 h-4 w-4" /> Request Similar
        </Button>
      </div>
    </div>
  );
}
