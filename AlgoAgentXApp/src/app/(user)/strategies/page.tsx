"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  Clock3,
  Loader2,
  Plus,
  RefreshCcw,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/shared/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import apiClient from "../../../lib/axios";

type StrategyItem = {
  id: string;
  name: string;
  description?: string | null;
  visibility?: string | null;
  status?: string | null;
  strategyType?: string | null;
  market?: string | null;
  timeframe?: string | null;
  parameters?: Record<string, any> | null;
  winRate?: number | null;
  sharpeRatio?: number | null;
  totalTrades?: number | null;
  maxDrawdown?: number | null;
  profitFactor?: number | null;
  lastUpdated?: string | null;
  createdAt?: string | null;
  lifecycle_status?: string | null;
  lifecycleStatus?: string | null;
  is_deployable_paper?: boolean;
  isDeployablePaper?: boolean;
  is_deployable_demo?: boolean;
  isDeployableDemo?: boolean;
  is_live_approved?: boolean;
  isLiveApproved?: boolean;
};

type StrategyRequestItem = {
  id: string;
  title: string;
  name?: string;
  description?: string | null;
  strategy_type?: string | null;
  strategyType?: string | null;
  market?: string | null;
  timeframe?: string | null;
  status: string;
  admin_notes?: string | null;
  deployed_strategy_id?: string | null;
  deployedStrategyId?: string | null;
  created_at?: string | null;
  createdAt?: string | null;
  updated_at?: string | null;
  updatedAt?: string | null;
  lastUpdated?: string | null;
};

type MyStrategiesResponse =
  | StrategyItem[]
  | {
      strategies?: StrategyItem[];
      requests?: StrategyRequestItem[];
    };

type StrategyRequestPayload = {
  title: string;
  strategy_type: string;
  entry_rules: string;
  exit_rules: string;
  confirmation_rules: string;
  risk_rules: string;
  invalidation_rules: string;
  trade_management_rules: string;
  notes: string;
};

const initialForm: StrategyRequestPayload = {
  title: "",
  strategy_type: "",
  entry_rules: "",
  exit_rules: "",
  confirmation_rules: "",
  risk_rules: "",
  invalidation_rules: "",
  trade_management_rules: "",
  notes: "",
};

const STATUS_LABEL: Record<string, string> = {
  UNDER_DEVELOPMENT: "Under Development",
  NEEDS_CLARIFICATION: "Needs Clarification",
  REJECTED: "Rejected",
  DEPLOYED: "Deployed",
};

const statusBadgeClass: Record<string, string> = {
  UNDER_DEVELOPMENT: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  NEEDS_CLARIFICATION: "border-sky-500/30 bg-sky-500/10 text-sky-200",
  REJECTED: "border-rose-500/30 bg-rose-500/10 text-rose-200",
  DEPLOYED: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
};

const inputClassName =
  "w-full rounded-xl border border-border/60 bg-card/25 px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";

const sectionCardClass = "rounded-xl border border-border/50 bg-card/20 p-5 backdrop-blur-xl";

type ApiEnvelope<T> = {
  success?: boolean;
  data?: T;
};

const getToken = () => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
};

const unwrap = <T,>(payload: ApiEnvelope<T> | T): T => {
  if (payload && typeof payload === "object" && "success" in (payload as Record<string, unknown>)) {
    return ((payload as ApiEnvelope<T>).data ?? null) as T;
  }
  return payload as T;
};

const apiGet = async <T,>(url: string, options?: { auth?: boolean }): Promise<T> => {
  const response = await apiClient.get<ApiEnvelope<T> | T>(url, options?.auth === false ? ({ auth: false } as any) : undefined);
  return unwrap<T>(response.data);
};

const apiPost = async <T,>(url: string, body?: unknown, options?: { auth?: boolean }): Promise<T> => {
  const response = await apiClient.post<ApiEnvelope<T> | T>(url, body, options?.auth === false ? ({ auth: false } as any) : undefined);
  return unwrap<T>(response.data);
};

function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function metricValue(value: number | null | undefined, options?: { suffix?: string; decimals?: number }): string {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const decimals = options?.decimals ?? 2;
  const suffix = options?.suffix ?? "";
  return `${Number(value).toFixed(decimals)}${suffix}`;
}

function integerMetricValue(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return String(Math.round(Number(value)));
}

export default function StrategiesPage() {
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<"templates" | "request" | "my">("templates");
  const [templates, setTemplates] = useState<StrategyItem[]>([]);
  const [myStrategies, setMyStrategies] = useState<StrategyItem[]>([]);
  const [myRequests, setMyRequests] = useState<StrategyRequestItem[]>([]);

  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [myLoading, setMyLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);

  const [templatesError, setTemplatesError] = useState<string | null>(null);
  const [myError, setMyError] = useState<string | null>(null);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [form, setForm] = useState<StrategyRequestPayload>(initialForm);

  const isAuthenticated = useMemo(() => Boolean(getToken()), []);

  const loadTemplates = useCallback(async () => {
    setTemplatesLoading(true);
    setTemplatesError(null);
    try {
      const response = await apiGet<StrategyItem[]>("/api/v1/strategies/templates", { auth: false });
      setTemplates(Array.isArray(response) ? response : []);
    } catch (error: any) {
      setTemplates([]);
      setTemplatesError(error?.message || "Failed to load template strategies");
    } finally {
      setTemplatesLoading(false);
    }
  }, []);

  const loadMyStrategies = useCallback(async () => {
    if (!getToken()) {
      setMyStrategies([]);
      setMyRequests([]);
      setMyError("Please sign in to view your strategy requests and private strategies.");
      return;
    }

    setMyLoading(true);
    setMyError(null);

    try {
      const response = await apiGet<MyStrategiesResponse>("/api/v1/strategies/my");

      if (Array.isArray(response)) {
        setMyStrategies(response);
        const requests = await apiGet<StrategyRequestItem[]>("/api/v1/strategies/my/requests");
        setMyRequests(Array.isArray(requests) ? requests : []);
      } else {
        setMyStrategies(Array.isArray(response?.strategies) ? response.strategies : []);
        setMyRequests(Array.isArray(response?.requests) ? response.requests : []);
      }
    } catch (error: any) {
      setMyStrategies([]);
      setMyRequests([]);
      setMyError(error?.message || "Failed to load your strategy data");
    } finally {
      setMyLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  useEffect(() => {
    if (activeTab === "my") {
      void loadMyStrategies();
    }
  }, [activeTab, loadMyStrategies]);

  const pendingRequests = useMemo(
    () => myRequests.filter((item) => item.status !== "DEPLOYED"),
    [myRequests],
  );
  const deployedRequests = useMemo(
    () => myRequests.filter((item) => item.status === "DEPLOYED"),
    [myRequests],
  );

  const privateStrategies = useMemo(
    () => myStrategies.filter((item) => (item.visibility || "PRIVATE") !== "PUBLIC"),
    [myStrategies],
  );
  const publishedStrategies = useMemo(
    () => myStrategies.filter((item) => (item.visibility || "PRIVATE") === "PUBLIC"),
    [myStrategies],
  );

  const handleChange = (field: keyof StrategyRequestPayload, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const openBacktest = (strategyId: string) => {
    if (!getToken()) {
      setActiveTab("request");
      setSubmitError("Please sign in to run a backtest.");
      return;
    }

    router.push(`/backtest?strategyId=${strategyId}`);
  };

  const submitRequest = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitError(null);
    setSubmitMessage(null);

    if (!getToken()) {
      setSubmitError("Please sign in before submitting a request.");
      return;
    }

    const requiredFields: Array<keyof StrategyRequestPayload> = [
      "title",
      "entry_rules",
      "exit_rules",
      "risk_rules",
    ];

    const emptyRequired = requiredFields.find((field) => !form[field].trim());
    if (emptyRequired) {
      setSubmitError("Title, Entry Rules, Exit Rules and Risk Rules are mandatory.");
      return;
    }

    const tooShort = requiredFields.find((field) => form[field].trim().length < 3);
    if (tooShort) {
      setSubmitError("Mandatory fields must be at least 3 characters long.");
      return;
    }

    setSubmitLoading(true);

    try {
      await apiPost("/api/v1/strategies/request", {
        title: form.title.trim(),
        strategy_type: form.strategy_type.trim() || null,
        market: null,
        timeframe: null,
        indicators: null,
        entry_rules: form.entry_rules.trim(),
        exit_rules: form.exit_rules.trim(),
        confirmation_rules: form.confirmation_rules.trim() || null,
        risk_rules: form.risk_rules.trim(),
        invalidation_rules: form.invalidation_rules.trim() || null,
        trade_management_rules: form.trade_management_rules.trim() || null,
        notes: form.notes.trim() || null,
      });

      setForm(initialForm);
      setSubmitMessage("Strategy request submitted successfully. Track progress in My Strategies.");
      setActiveTab("my");
      void loadMyStrategies();
    } catch (error: any) {
      setSubmitError(error?.message || "Unable to submit strategy request.");
    } finally {
      setSubmitLoading(false);
    }
  };

  const renderMetric = (label: string, value: string, hint?: string) => (
    <div className="rounded-xl border border-border/50 bg-card/20 p-3">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold text-foreground">{value}</p>
      {hint ? <p className="mt-1 text-[11px] text-muted-foreground">{hint}</p> : null}
    </div>
  );

  const renderMetaBadges = (strategy: StrategyItem) => (
    <div className="mt-4 flex flex-wrap gap-2">
      {(strategy.strategyType || strategy.parameters?.strategy_type) && (
        <Badge variant="secondary" className="border-border/60 bg-card/40 text-foreground">
          {strategy.strategyType || strategy.parameters?.strategy_type}
        </Badge>
      )}
      {(strategy.market || strategy.parameters?.market) && (
        <Badge variant="secondary" className="border-border/60 bg-card/40 text-foreground">
          {strategy.market || strategy.parameters?.market}
        </Badge>
      )}
      {(strategy.timeframe || strategy.parameters?.timeframe) && (
        <Badge variant="secondary" className="border-border/60 bg-card/40 text-foreground">
          {strategy.timeframe || strategy.parameters?.timeframe}
        </Badge>
      )}
    </div>
  );
  const renderDeploymentBadges = (strategy: StrategyItem) => {
    const paperReady = Boolean(strategy.isDeployablePaper ?? strategy.is_deployable_paper);
    const demoReady = Boolean(strategy.isDeployableDemo ?? strategy.is_deployable_demo);
    const liveApproved = Boolean(strategy.isLiveApproved ?? strategy.is_live_approved);
    return (
      <div className="mt-3 flex flex-wrap gap-2">
        <Badge className="border-sky-500/30 bg-sky-500/10 text-sky-200">Backtest Ready</Badge>
        {paperReady ? <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-200">Paper Ready</Badge> : null}
        {demoReady ? <Badge className="border-lime-500/30 bg-lime-500/10 text-lime-200">Demo Ready</Badge> : null}
        <Badge className={liveApproved ? "border-amber-500/30 bg-amber-500/10 text-amber-200" : "border-border/60 bg-card/40 text-muted-foreground"}>
          {liveApproved ? "Live Approved" : "Live Locked"}
        </Badge>
      </div>
    );
  };

  const renderStrategyCard = (strategy: StrategyItem, mode: "template" | "my") => {
    const visibility = (strategy.visibility || "PRIVATE").toUpperCase();

    return (
      <GlassCard
        key={strategy.id}
        className="h-full border border-border/60 bg-card/30 shadow-xl backdrop-blur-xl transition-colors hover:border-primary/40"
      >
        <div className="flex h-full flex-col gap-4 p-6">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 space-y-2">
              <h3 className="line-clamp-2 text-lg font-semibold tracking-tight text-foreground">{strategy.name}</h3>
              <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
                {strategy.description || "No strategy description provided."}
              </p>
            </div>
            <Badge
              className={
                visibility === "PUBLIC"
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                  : "border-border/60 bg-card/40 text-muted-foreground"
              }
            >
              {visibility === "PUBLIC" ? "Published" : "Private"}
            </Badge>
          </div>

          {renderMetaBadges(strategy)}
          {renderDeploymentBadges(strategy)}

          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
            {renderMetric("Win Rate", metricValue(strategy.winRate, { suffix: "%", decimals: 2 }))}
            {renderMetric("Sharpe Ratio", metricValue(strategy.sharpeRatio, { decimals: 2 }))}
            {renderMetric("Drawdown", metricValue(strategy.maxDrawdown, { suffix: "%", decimals: 2 }))}
            {renderMetric("Total Trades", integerMetricValue(strategy.totalTrades))}
            {renderMetric("Profit Factor", metricValue(strategy.profitFactor, { decimals: 2 }))}
          </div>

          <div className="mt-auto flex flex-col gap-4 pt-2">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>Updated: {formatDateTime(strategy.lastUpdated || strategy.createdAt)}</span>
              {mode === "template" ? <span>Template Strategy</span> : <span>Your Strategy</span>}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Button
                onClick={() => openBacktest(strategy.id)}
                className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <BarChart3 className="mr-2 h-4 w-4" />
                Backtest Strategy
              </Button>
              <Button
                variant="outline"
                onClick={() => setActiveTab("request")}
                className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
              >
                <Sparkles className="mr-2 h-4 w-4" />
                {mode === "my" ? "Request Refinement" : "Request Similar"}
              </Button>
            </div>
          </div>
        </div>
      </GlassCard>
    );
  };

  const renderRequestCard = (request: StrategyRequestItem) => {
    const statusClass = statusBadgeClass[request.status] || "border-border/60 bg-card/40 text-muted-foreground";

    return (
      <GlassCard
        key={request.id}
        className="h-full border border-border/60 bg-card/30 shadow-xl backdrop-blur-xl transition-colors hover:border-primary/35"
      >
        <div className="flex h-full flex-col gap-4 p-6">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-2">
              <h3 className="line-clamp-2 text-lg font-semibold tracking-tight text-foreground">
                {request.title || request.name || "Untitled request"}
              </h3>
              <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
                {request.description || "Your request has been submitted for strategy engineering review."}
              </p>
            </div>
            <Badge className={statusClass}>{STATUS_LABEL[request.status] || request.status}</Badge>
          </div>

          <div className="flex flex-wrap gap-2">
            {(request.strategyType || request.strategy_type) && (
              <Badge variant="secondary" className="border-border/60 bg-card/40 text-foreground">
                {request.strategyType || request.strategy_type}
              </Badge>
            )}
            {request.market && (
              <Badge variant="secondary" className="border-border/60 bg-card/40 text-foreground">
                {request.market}
              </Badge>
            )}
            {request.timeframe && (
              <Badge variant="secondary" className="border-border/60 bg-card/40 text-foreground">
                {request.timeframe}
              </Badge>
            )}
          </div>

          <div className="rounded-xl border border-border/50 bg-card/20 p-4 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock3 className="h-4 w-4" />
              Submitted: {formatDateTime(request.createdAt || request.created_at)}
            </div>

            {request.deployed_strategy_id || request.deployedStrategyId ? (
              <div className="mt-2 flex items-center gap-2 text-emerald-300">
                <CheckCircle2 className="h-4 w-4" />
                Strategy has been deployed.
              </div>
            ) : null}

            {request.admin_notes ? (
              <div className="mt-3 rounded-lg border border-border/50 bg-card/30 p-3 text-xs leading-5 text-muted-foreground">
                <p className="font-medium text-foreground">Admin Notes</p>
                <p className="mt-1 whitespace-pre-wrap">{request.admin_notes}</p>
              </div>
            ) : null}
          </div>
        </div>
      </GlassCard>
    );
  };

  const loadingCards = (count = 4) => (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {Array.from({ length: count }).map((_, index) => (
        <GlassCard key={index} className="border border-border/50 bg-card/25">
          <div className="space-y-4 p-6">
            <div className="h-5 w-2/3 animate-pulse rounded bg-card/60" />
            <div className="h-4 w-full animate-pulse rounded bg-card/60" />
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
              {Array.from({ length: 5 }).map((__, idx) => (
                <div key={idx} className="h-16 animate-pulse rounded-xl bg-card/60" />
              ))}
            </div>
            <div className="h-10 w-full animate-pulse rounded-xl bg-card/60" />
          </div>
        </GlassCard>
      ))}
    </div>
  );

  const renderTemplates = () => {
    if (templatesLoading) return loadingCards();

    if (templatesError) {
      return (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 text-sm text-rose-200">
          <div className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 h-4 w-4" />
            <div className="space-y-3">
              <p>{templatesError}</p>
              <Button
                variant="outline"
                onClick={() => void loadTemplates()}
                className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
              >
                <RefreshCcw className="mr-2 h-4 w-4" />
                Retry
              </Button>
            </div>
          </div>
        </div>
      );
    }

    if (!templates.length) {
      return (
        <EmptyState
          title="No Template Strategies Yet"
          description="Template strategies will appear here once they are published by the admin team."
          action={
            <Button onClick={() => setActiveTab("request")} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
              <Plus className="mr-2 h-4 w-4" />
              Request Custom Strategy
            </Button>
          }
        />
      );
    }

    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-foreground">Template Strategies</h2>
            <p className="text-sm text-muted-foreground">Public templates curated for fast exploration and backtesting.</p>
          </div>
          <Badge className="border-border/60 bg-card/40 text-muted-foreground">{templates.length} available</Badge>
        </div>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">{templates.map((item) => renderStrategyCard(item, "template"))}</div>
      </section>
    );
  };

  const renderMyStrategies = () => {
    if (myLoading) return loadingCards(3);

    if (myError) {
      return (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 text-sm text-rose-200">
          <div className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 h-4 w-4" />
            <div className="space-y-3">
              <p>{myError}</p>
              {getToken() ? (
                <Button
                  variant="outline"
                  onClick={() => void loadMyStrategies()}
                  className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
                >
                  <RefreshCcw className="mr-2 h-4 w-4" />
                  Retry
                </Button>
              ) : (
                <Button
                  variant="outline"
                  onClick={() => setActiveTab("request")}
                  className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
                >
                  Open Request Strategy
                </Button>
              )}
            </div>
          </div>
        </div>
      );
    }

    if (!myRequests.length && !myStrategies.length) {
      return (
        <EmptyState
          title="No Requests or Strategies"
          description="Submit your first custom strategy request. It will appear here with status updates."
          action={
            <Button onClick={() => setActiveTab("request")} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
              <Plus className="mr-2 h-4 w-4" />
              Request Strategy
            </Button>
          }
        />
      );
    }

    return (
      <div className="space-y-8">
        {pendingRequests.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-foreground">Pending Requests</h2>
                <p className="text-sm text-muted-foreground">Requests currently under development or clarification.</p>
              </div>
              <Badge className="border-amber-500/30 bg-amber-500/10 text-amber-200">{pendingRequests.length}</Badge>
            </div>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">{pendingRequests.map(renderRequestCard)}</div>
          </section>
        )}

        {deployedRequests.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-foreground">Processed Requests</h2>
                <p className="text-sm text-muted-foreground">Requests already deployed or published into strategy records.</p>
              </div>
              <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-200">{deployedRequests.length}</Badge>
            </div>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">{deployedRequests.map(renderRequestCard)}</div>
          </section>
        )}

        {privateStrategies.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-foreground">My Private Strategies</h2>
                <p className="text-sm text-muted-foreground">Deployed strategies available only in your workspace.</p>
              </div>
              <Badge className="border-border/60 bg-card/40 text-muted-foreground">{privateStrategies.length}</Badge>
            </div>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">{privateStrategies.map((item) => renderStrategyCard(item, "my"))}</div>
          </section>
        )}

        {publishedStrategies.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-foreground">Published from My Requests</h2>
                <p className="text-sm text-muted-foreground">Strategies from your requests that are now publicly visible.</p>
              </div>
              <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-200">{publishedStrategies.length}</Badge>
            </div>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">{publishedStrategies.map((item) => renderStrategyCard(item, "my"))}</div>
          </section>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Trading Strategies"
        subtitle="Explore templates, request professional strategy builds, and track deployment status."
        actions={
          <Button
            onClick={() => setActiveTab("request")}
            className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="mr-2 h-4 w-4" />
            Request Strategy
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <GlassCard className="border border-border/50 bg-card/25 p-4 shadow-xl backdrop-blur-xl">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Templates</p>
          <p className="mt-2 text-xl font-semibold text-foreground">{templates.length}</p>
          <p className="mt-1 text-xs text-muted-foreground">Public baseline strategies</p>
        </GlassCard>
        <GlassCard className="border border-border/50 bg-card/25 p-4 shadow-xl backdrop-blur-xl">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">My Active Requests</p>
          <p className="mt-2 text-xl font-semibold text-foreground">{pendingRequests.length}</p>
          <p className="mt-1 text-xs text-muted-foreground">Under review or clarification</p>
        </GlassCard>
        <GlassCard className="border border-border/50 bg-card/25 p-4 shadow-xl backdrop-blur-xl">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">My Strategies</p>
          <p className="mt-2 text-xl font-semibold text-foreground">{myStrategies.length}</p>
          <p className="mt-1 text-xs text-muted-foreground">Private + published strategies</p>
        </GlassCard>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/30 p-2 shadow-xl backdrop-blur-xl">
        <div className="flex flex-wrap gap-2">
          {[
            { key: "templates", label: "Templates", icon: Sparkles },
            { key: "request", label: "Request Strategy", icon: Target },
            { key: "my", label: "My Strategies", icon: TrendingUp },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;

            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as "templates" | "request" | "my")}
                className={`inline-flex items-center rounded-xl border px-4 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "border-primary/40 bg-primary/15 text-primary"
                    : "border-transparent text-muted-foreground hover:border-border/50 hover:bg-card/40 hover:text-foreground"
                }`}
              >
                <Icon className="mr-2 h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {activeTab === "templates" && renderTemplates()}
      {activeTab === "my" && renderMyStrategies()}

      {activeTab === "request" && (
        <GlassCard className="border border-border/60 bg-card/30 shadow-xl backdrop-blur-xl">
          <div className="space-y-6 p-6">
            <div className={sectionCardClass}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold tracking-tight text-foreground">Request a Professional Strategy Build</h2>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    Define rules with precision. The admin team reviews, engineers, deploys, and can optionally
                    publish after validation.
                  </p>
                </div>
                <Badge className="border-border/60 bg-card/40 text-muted-foreground">Structured Form</Badge>
              </div>

              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
                <div className="rounded-xl border border-border/50 bg-card/25 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Mandatory</p>
                  <p className="mt-1 text-sm text-foreground">Title, Entry, Exit, Risk</p>
                </div>
                <div className="rounded-xl border border-border/50 bg-card/25 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Optional Depth</p>
                  <p className="mt-1 text-sm text-foreground">Confirmation, invalidation, management</p>
                </div>
                <div className="rounded-xl border border-border/50 bg-card/25 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Outcome</p>
                  <p className="mt-1 text-sm text-foreground">Private deployment with publish option</p>
                </div>
              </div>
            </div>

            {submitMessage && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{submitMessage}</span>
                </div>
              </div>
            )}

            {submitError && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  <span>{submitError}</span>
                </div>
              </div>
            )}

            <form onSubmit={submitRequest} className="space-y-5">
              <div className={sectionCardClass}>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Strategy Identity</h3>
                <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Strategy Title *</label>
                    <input
                      value={form.title}
                      onChange={(event) => handleChange("title", event.target.value)}
                      className={inputClassName}
                      placeholder="Example: Multi-Timeframe Momentum Breakout"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Strategy Type</label>
                    <input
                      value={form.strategy_type}
                      onChange={(event) => handleChange("strategy_type", event.target.value)}
                      className={inputClassName}
                      placeholder="Example: Swing / Momentum / Reversal"
                    />
                  </div>
                </div>
              </div>

              <div className={sectionCardClass}>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Core Trading Rules</h3>
                <div className="mt-4 space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Entry Rules *</label>
                    <textarea
                      rows={4}
                      value={form.entry_rules}
                      onChange={(event) => handleChange("entry_rules", event.target.value)}
                      className={inputClassName}
                      placeholder="Define exact signal conditions, filters, and trigger confirmation."
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Exit Rules *</label>
                    <textarea
                      rows={4}
                      value={form.exit_rules}
                      onChange={(event) => handleChange("exit_rules", event.target.value)}
                      className={inputClassName}
                      placeholder="Define fixed target, trailing logic, and emergency exits."
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Risk Rules *</label>
                    <textarea
                      rows={4}
                      value={form.risk_rules}
                      onChange={(event) => handleChange("risk_rules", event.target.value)}
                      className={inputClassName}
                      placeholder="Position sizing, max risk per trade/day, and invalid risk scenarios."
                    />
                  </div>
                </div>
              </div>

              <div className={sectionCardClass}>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Advanced Logic & Notes</h3>

                <div className="mt-4 space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Confirmation Rules</label>
                    <textarea
                      rows={3}
                      value={form.confirmation_rules}
                      onChange={(event) => handleChange("confirmation_rules", event.target.value)}
                      className={inputClassName}
                      placeholder="Optional confirmation layer before entry activation."
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Invalidation Rules</label>
                    <textarea
                      rows={3}
                      value={form.invalidation_rules}
                      onChange={(event) => handleChange("invalidation_rules", event.target.value)}
                      className={inputClassName}
                      placeholder="Conditions that invalidate setup before execution."
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Trade Management Rules</label>
                    <textarea
                      rows={3}
                      value={form.trade_management_rules}
                      onChange={(event) => handleChange("trade_management_rules", event.target.value)}
                      className={inputClassName}
                      placeholder="Partial exits, SL shifts, break-even logic, and re-entry policy."
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Additional Notes</label>
                    <textarea
                      rows={3}
                      value={form.notes}
                      onChange={(event) => handleChange("notes", event.target.value)}
                      className={inputClassName}
                      placeholder="Any implementation context or strategic intent."
                    />
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-muted-foreground">
                  Mandatory fields ensure admin-ready implementation quality.
                </p>

                <div className="flex flex-wrap items-center gap-3">
                  {!isAuthenticated && (
                    <span className="inline-flex items-center text-xs text-amber-300">
                      <AlertCircle className="mr-1 h-3.5 w-3.5" />
                      Sign in required
                    </span>
                  )}

                  <Button
                    disabled={submitLoading || !isAuthenticated}
                    className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    {submitLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      <>
                        Submit Strategy Request
                        <ArrowUpRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
