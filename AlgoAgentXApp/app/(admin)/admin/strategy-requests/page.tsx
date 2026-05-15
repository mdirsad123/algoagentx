"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Code2,
  Clock3,
  Edit3,
  Eye,
  Filter,
  Loader2,
  Plus,
  RefreshCcw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  ImageIcon,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import {
  adminApi,
  AdminStrategyCreatePayload,
  AdminStrategyUpdatePayload,
  ImplementedStrategy,
  StrategyRequest,
  StrategyVisibility,
} from "@/lib/api/admin";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { StrategyAttachmentGallery } from "@/components/strategies/StrategyAttachmentGallery";
import { AuthenticatedStrategyImage } from "@/components/strategies/AuthenticatedStrategyImage";


const strategyAssets = (strategy: any) => (strategy?.assets || strategy?.strategyAssets || strategy?.strategy_assets || []) as any[];
const coverAsset = (strategy: any) => {
  const assets = strategyAssets(strategy);
  return assets.find((asset) => Boolean(asset.isCover ?? asset.is_cover)) || assets[0] || null;
};
const assetUrl = (asset: any) => asset?.publicUrl || asset?.public_url || "";
const assetName = (asset: any) => asset?.originalName || asset?.original_name || asset?.fileName || asset?.file_name || "Strategy cover";

type TabKey = "requests" | "strategies";
type EditorMode = "create" | "edit";

type StrategyEditorForm = {
  name: string;
  description: string;
  strategy_type: string;
  market: string;
  timeframe: string;
  entry_rules: string;
  exit_rules: string;
  confirmation_rules: string;
  risk_rules: string;
  invalidation_rules: string;
  trade_management_rules: string;
  notes: string;
  source_code: string;
  visibility: StrategyVisibility;
  winRate: string;
  sharpeRatio: string;
  maxDrawdown: string;
  totalTrades: string;
  profitFactor: string;
};

const REQUEST_STATUSES = ["SUBMITTED", "UNDER_REVIEW", "UNDER_DEVELOPMENT", "NEEDS_CLARIFICATION", "REJECTED", "DEPLOYED", "PUBLISHED"];

const STATUS_LABEL: Record<string, string> = {
  SUBMITTED: "Pending Review",
  UNDER_REVIEW: "Under Review",
  UNDER_DEVELOPMENT: "Under Development",
  NEEDS_CLARIFICATION: "Needs Clarification",
  REJECTED: "Rejected",
  DEPLOYED: "Deployed",
  PUBLISHED: "Published",
};

const STATUS_BADGE_CLASS: Record<string, string> = {
  SUBMITTED: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  UNDER_REVIEW: "border-sky-500/30 bg-sky-500/10 text-sky-200",
  UNDER_DEVELOPMENT: "border-violet-500/30 bg-violet-500/10 text-violet-200",
  NEEDS_CLARIFICATION: "border-yellow-500/30 bg-yellow-500/10 text-yellow-200",
  REJECTED: "border-rose-500/30 bg-rose-500/10 text-rose-200",
  DEPLOYED: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
  PUBLISHED: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
};
const normalizeRequestStatus = (status?: string | null) => String(status || "SUBMITTED").trim().replace(/[\s-]+/g, "_").toUpperCase();

const fieldClass =
  "w-full rounded-xl border border-border/60 bg-card/25 px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";

const initialEditorForm: StrategyEditorForm = {
  name: "",
  description: "",
  strategy_type: "",
  market: "",
  timeframe: "",
  entry_rules: "",
  exit_rules: "",
  confirmation_rules: "",
  risk_rules: "",
  invalidation_rules: "",
  trade_management_rules: "",
  notes: "",
  source_code: "",
  visibility: "PRIVATE",
  winRate: "",
  sharpeRatio: "",
  maxDrawdown: "",
  totalTrades: "",
  profitFactor: "",
};

function formatDateTime(value?: string | null) {
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

function asNumberInput(value: number | null | undefined) {
  return value === null || value === undefined || Number.isNaN(Number(value)) ? "" : String(value);
}

function toOptionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isNaN(parsed) ? null : parsed;
}

function strategyToForm(strategy: ImplementedStrategy): StrategyEditorForm {
  return {
    name: strategy.name || "",
    description: strategy.description || "",
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
    source_code: strategy.source_code || strategy.sourceCode || String(strategy.parameters?.source_code || ""),
    visibility: (strategy.visibility?.toUpperCase() === "PUBLIC" ? "PUBLIC" : "PRIVATE") as StrategyVisibility,
    winRate: asNumberInput(strategy.winRate),
    sharpeRatio: asNumberInput(strategy.sharpeRatio),
    maxDrawdown: asNumberInput(strategy.maxDrawdown),
    totalTrades: asNumberInput(strategy.totalTrades),
    profitFactor: asNumberInput(strategy.profitFactor),
  };
}

function formToPayload(form: StrategyEditorForm): AdminStrategyCreatePayload | AdminStrategyUpdatePayload {
  return {
    name: form.name.trim(),
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
    visibility: form.visibility,
    performance_metrics: {
      winRate: toOptionalNumber(form.winRate),
      sharpeRatio: toOptionalNumber(form.sharpeRatio),
      maxDrawdown: toOptionalNumber(form.maxDrawdown),
      totalTrades: toOptionalNumber(form.totalTrades),
      profitFactor: toOptionalNumber(form.profitFactor),
    },
  };
}

export default function AdminStrategyRequestsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("requests");

  const [requests, setRequests] = useState<StrategyRequest[]>([]);
  const [strategies, setStrategies] = useState<ImplementedStrategy[]>([]);

  const [requestSearch, setRequestSearch] = useState("");
  const [requestStatus, setRequestStatus] = useState("");
  const [strategySearch, setStrategySearch] = useState("");
  const [strategyVisibility, setStrategyVisibility] = useState<"" | StrategyVisibility>("");
  const [strategySource, setStrategySource] = useState<"" | "MANUAL" | "REQUESTED">("");

  const [requestSkip, setRequestSkip] = useState(0);
  const [strategySkip, setStrategySkip] = useState(0);
  const requestLimit = 20;
  const strategyLimit = 20;

  const [requestTotal, setRequestTotal] = useState(0);
  const [strategyTotal, setStrategyTotal] = useState(0);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedRequest, setSelectedRequest] = useState<StrategyRequest | null>(null);
  const [requestStatusDraft, setRequestStatusDraft] = useState<string>("UNDER_DEVELOPMENT");
  const [requestNotesDraft, setRequestNotesDraft] = useState<string>("");
  const [requestDeployTargetId, setRequestDeployTargetId] = useState<string>("");

  const [editorOpen, setEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<EditorMode>("create");
  const [editorTarget, setEditorTarget] = useState<ImplementedStrategy | null>(null);
  const [editorForm, setEditorForm] = useState<StrategyEditorForm>(initialEditorForm);

  const deployedRequestCount = useMemo(
    () => requests.filter((item) => item.status === "DEPLOYED").length,
    [requests],
  );
  const publishedStrategyCount = useMemo(
    () => strategies.filter((item) => (item.visibility || "PRIVATE") === "PUBLIC").length,
    [strategies],
  );

  const loadData = useCallback(
    async (nextRequestSkip = requestSkip, nextStrategySkip = strategySkip) => {
      setLoading(true);
      setError(null);

      try {
        const response = await adminApi.getStrategyManagementData({
          requestSkip: nextRequestSkip,
          requestLimit,
          requestSearch: requestSearch || undefined,
          requestStatus: requestStatus || undefined,
          strategySkip: nextStrategySkip,
          strategyLimit,
          strategySearch: strategySearch || undefined,
          strategyVisibility: strategyVisibility || undefined,
          strategySource: strategySource || undefined,
        });

        setRequests(Array.isArray(response.items) ? response.items : []);
        setStrategies(Array.isArray(response.implemented) ? response.implemented : []);
        setRequestTotal(response.total || 0);
        setStrategyTotal(response.strategy_total || response.implemented?.length || 0);
        setRequestSkip(nextRequestSkip);
        setStrategySkip(nextStrategySkip);
      } catch (err: any) {
        setError(err?.message || "Failed to load strategy management data");
      } finally {
        setLoading(false);
      }
    },
    [requestSkip, strategySkip, requestSearch, requestStatus, strategySearch, strategyVisibility, strategySource],
  );

  useEffect(() => {
    void loadData(0, 0);
  }, []);

  const resetEditor = () => {
    setEditorForm(initialEditorForm);
    setEditorTarget(null);
    setEditorMode("create");
  };

  const openCreateEditor = () => {
    resetEditor();
    setEditorMode("create");
    setEditorOpen(true);
  };

  const openEditEditor = (strategy: ImplementedStrategy) => {
    setEditorTarget(strategy);
    setEditorMode("edit");
    setEditorForm(strategyToForm(strategy));
    setEditorOpen(true);
  };

  const handleRequestUpdate = async () => {
    if (!selectedRequest) return;

    setSaving(true);
    try {
      await adminApi.updateStrategy(selectedRequest.id, {
        status: requestStatusDraft,
        admin_notes: requestNotesDraft || undefined,
      });
      toast.success("Request status updated");
      setSelectedRequest(null);
      await loadData(requestSkip, strategySkip);
    } catch (err: any) {
      toast.error(err?.message || "Unable to update request");
    } finally {
      setSaving(false);
    }
  };

  const handleDeploy = async (publish = false) => {
    if (!selectedRequest) return;

    setSaving(true);
    try {
      await adminApi.deployStrategyWithPayload(selectedRequest.id, {
        strategy_id: requestDeployTargetId || undefined,
        admin_notes: requestNotesDraft || undefined,
        publish,
        visibility: publish ? "PUBLIC" : "PRIVATE",
      });

      toast.success(publish ? "Request deployed and published" : "Request deployed to strategy");
      setSelectedRequest(null);
      await loadData(requestSkip, strategySkip);
    } catch (err: any) {
      toast.error(err?.message || "Unable to deploy request");
    } finally {
      setSaving(false);
    }
  };


  const handleStartWorkspace = async (request: StrategyRequest) => {
    setSaving(true);
    try {
      const response = await adminApi.createStrategyWorkspace(request.id);
      const strategyId = response?.strategy?.id || request.deployedStrategyId || request.deployed_strategy_id;
      toast.success(strategyId ? "Opening strategy workspace" : "Workspace created");
      if (strategyId) window.location.href = `/admin/strategy-requests/strategies/${strategyId}`;
      else await loadData(requestSkip, strategySkip);
    } catch (err: any) {
      toast.error(err?.message || "Unable to create workspace");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateOrUpdateStrategy = async () => {
    const name = editorForm.name.trim();
    if (!name) {
      toast.error("Strategy name is required");
      return;
    }

    if (editorMode === "edit" && !window.confirm("Save updated strategy code and configuration?")) {
      return;
    }

    setSaving(true);

    try {
      const payload = formToPayload(editorForm);

      if (editorMode === "create") {
        await adminApi.createAdminStrategy(payload as AdminStrategyCreatePayload);
        toast.success("Strategy created");
      } else if (editorTarget) {
        await adminApi.updateAdminStrategyById(editorTarget.id, payload as AdminStrategyUpdatePayload);
        toast.success("Strategy updated");
      }

      setEditorOpen(false);
      resetEditor();
      await loadData(requestSkip, strategySkip);
    } catch (err: any) {
      toast.error(err?.message || "Failed to save strategy");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteStrategy = async (strategy: ImplementedStrategy) => {
    const approved = window.confirm(`Delete strategy '${strategy.name}'? This will un-link deployed requests.`);
    if (!approved) return;

    setSaving(true);
    try {
      await adminApi.deleteAdminStrategyById(strategy.id);
      toast.success("Strategy deleted");
      await loadData(requestSkip, strategySkip);
    } catch (err: any) {
      toast.error(err?.message || "Unable to delete strategy");
    } finally {
      setSaving(false);
    }
  };


  const handleValidateStrategy = async (strategy: ImplementedStrategy) => {
    try {
      setSaving(true);
      const result = await adminApi.validateAdminStrategyById(strategy.id, {});
      if (result?.validation_ok) {
        toast.success(result?.message || "Strategy validation passed");
      } else {
        toast.error(result?.message || "Strategy validation failed");
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Unable to validate strategy");
    } finally {
      setSaving(false);
    }
  };

  const handleTogglePublish = async (strategy: ImplementedStrategy) => {
    setSaving(true);
    try {
      if ((strategy.visibility || "PRIVATE") === "PUBLIC") {
        await adminApi.unpublishAdminStrategyById(strategy.id);
        toast.success("Strategy moved to private");
      } else {
        await adminApi.publishAdminStrategyById(strategy.id);
        toast.success("Strategy published");
      }

      await loadData(requestSkip, strategySkip);
    } catch (err: any) {
      toast.error(err?.message || "Unable to update publish status");
    } finally {
      setSaving(false);
    }
  };


  const handleDeployPrivateStrategy = async (strategy: ImplementedStrategy) => {
    setSaving(true);
    try {
      await adminApi.deployPrivateAdminStrategyById(strategy.id);
      toast.success("Strategy deployed privately to requesting user");
      await loadData(requestSkip, strategySkip);
    } catch (err: any) {
      toast.error(err?.message || "Unable to deploy private strategy");
    } finally {
      setSaving(false);
    }
  };

  const strategyOptions = useMemo(
    () => strategies.map((item) => ({ id: item.id, label: item.name })),
    [strategies],
  );

  const renderLoadingGrid = () => (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {Array.from({ length: 4 }).map((_, index) => (
        <GlassCard key={index} className="border border-border/50 bg-card/25">
          <div className="space-y-3 p-5">
            <div className="h-5 w-1/2 animate-pulse rounded bg-card/60" />
            <div className="h-4 w-full animate-pulse rounded bg-card/60" />
            <div className="h-4 w-4/5 animate-pulse rounded bg-card/60" />
            <div className="h-10 w-full animate-pulse rounded bg-card/60" />
          </div>
        </GlassCard>
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Strategy Management"
        subtitle="Manage user requests, deploy strategies, and control publishing from a single panel."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              onClick={() => void loadData(requestSkip, strategySkip)}
              className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
            >
              <RefreshCcw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Link href="/admin/strategy-requests/strategies/new">
              <Button className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
                <Plus className="mr-2 h-4 w-4" />
                Create Strategy
              </Button>
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <GlassCard className="border border-border/50 bg-card/25 p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Requests</p>
          <p className="mt-2 text-xl font-semibold text-foreground">{requestTotal}</p>
        </GlassCard>
        <GlassCard className="border border-border/50 bg-card/25 p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Deployed Requests</p>
          <p className="mt-2 text-xl font-semibold text-foreground">{deployedRequestCount}</p>
        </GlassCard>
        <GlassCard className="border border-border/50 bg-card/25 p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Strategies</p>
          <p className="mt-2 text-xl font-semibold text-foreground">{strategyTotal}</p>
        </GlassCard>
        <GlassCard className="border border-border/50 bg-card/25 p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Published</p>
          <p className="mt-2 text-xl font-semibold text-foreground">{publishedStrategyCount}</p>
        </GlassCard>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/30 p-2 shadow-xl backdrop-blur-xl">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setActiveTab("requests")}
            className={`rounded-xl border px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "requests"
                ? "border-primary/40 bg-primary/15 text-primary"
                : "border-transparent text-muted-foreground hover:border-border/50 hover:bg-card/40 hover:text-foreground"
            }`}
          >
            Request Queue
          </button>
          <button
            onClick={() => setActiveTab("strategies")}
            className={`rounded-xl border px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "strategies"
                ? "border-primary/40 bg-primary/15 text-primary"
                : "border-transparent text-muted-foreground hover:border-border/50 hover:bg-card/40 hover:text-foreground"
            }`}
          >
            Strategy Library
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      )}

      {activeTab === "requests" && (
        <div className="space-y-4">
          <GlassCard className="border border-border/60 bg-card/25 p-4">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <div className="md:col-span-2">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
                  <input
                    value={requestSearch}
                    onChange={(event) => setRequestSearch(event.target.value)}
                    className={`${fieldClass} pl-9`}
                    placeholder="Search by title, user, strategy type"
                  />
                </div>
              </div>

              <select
                value={requestStatus}
                onChange={(event) => setRequestStatus(event.target.value)}
                className={fieldClass}
              >
                <option value="">All statuses</option>
                {REQUEST_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {STATUS_LABEL[status] || status}
                  </option>
                ))}
              </select>

              <Button
                onClick={() => void loadData(0, strategySkip)}
                className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Filter className="mr-2 h-4 w-4" />
                Apply
              </Button>
            </div>
          </GlassCard>

          {loading ? (
            renderLoadingGrid()
          ) : requests.length === 0 ? (
            <GlassCard className="border border-border/60 bg-card/25 p-8 text-center text-muted-foreground">
              No strategy requests found for the selected filters.
            </GlassCard>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {requests.map((request) => {
                const normalizedStatus = normalizeRequestStatus(request.status);
                const statusClass = STATUS_BADGE_CLASS[normalizedStatus] || "border-border/60 bg-card/40 text-muted-foreground";

                return (
                  <GlassCard key={request.id} className="border border-border/60 bg-card/30 shadow-xl">
                    <div className="space-y-4 p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="text-lg font-semibold tracking-tight text-foreground">{request.title}</h3>
                          <p className="mt-1 text-sm text-muted-foreground">{request.user_name || request.user_email || "Unknown user"}</p>
                          <p className="mt-1 text-xs text-primary">Requested User Strategy</p>
                          {(request.requestKind || request.request_kind || "").toUpperCase() === "REFINEMENT" ? (
                            <div className="mt-2 flex flex-wrap gap-2">
                              <Badge className="border-primary/30 bg-primary/10 text-primary">Refinement Request</Badge>
                              {(request.originalStrategyName || request.original_strategy_name) ? (
                                <Badge variant="secondary" className="border-border/60 bg-card/40 text-foreground">Original: {request.originalStrategyName || request.original_strategy_name}</Badge>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                        <Badge className={statusClass}>{STATUS_LABEL[normalizedStatus] || request.status}</Badge>
                      </div>

                      <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
                        {(request.requestKind || request.request_kind || "").toUpperCase() === "REFINEMENT"
                          ? (request.refinementNotes || request.refinement_notes || request.userUpdateNotes || request.user_update_notes || request.notes)
                          : (request.description || request.entry_rules) || "No description available"}
                      </p>
                      {(request.userUpdateNotes || request.user_update_notes) ? (
                        <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 p-3 text-xs leading-5 text-sky-100">
                          <p className="font-semibold text-sky-50">Updated by User</p>
                          <p className="mt-1 line-clamp-3 whitespace-pre-wrap">{request.userUpdateNotes || request.user_update_notes}</p>
                        </div>
                      ) : null}

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

                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                        <span className="inline-flex items-center gap-1">
                          <ImageIcon className="h-3.5 w-3.5" />
                          {(request.attachmentCount ?? request.attachment_count ?? request.attachments?.length ?? 0)} images
                        </span>
                        <Badge className="border-sky-500/30 bg-sky-500/10 text-sky-200">
                          {request.workspaceStatus || request.workspace_status || ((request.deployedStrategyId || request.deployed_strategy_id) ? "Workspace Created" : "Not Started")}
                        </Badge>
                      </div>

                      {(request.attachments?.length || 0) > 0 && (
                        <StrategyAttachmentGallery attachments={request.attachments?.slice(0, 3)} compact />
                      )}

                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span className="inline-flex items-center gap-1">
                          <Clock3 className="h-3.5 w-3.5" />
                          {formatDateTime(request.createdAt || request.created_at)}
                        </span>
                        {(request.deployedStrategyId || request.deployed_strategy_id) && (
                          <span className="inline-flex items-center gap-1 text-emerald-300">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Linked Strategy
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <Button
                          variant="outline"
                          className="rounded-xl border-primary/40 bg-primary/15 text-primary hover:bg-primary/25"
                          onClick={() => void handleStartWorkspace(request)}
                          disabled={saving}
                        >
                          <Code2 className="mr-2 h-4 w-4" />
                          {(request.deployedStrategyId || request.deployed_strategy_id) ? "Open Workspace" : "Start Development"}
                        </Button>
                        <Link href={`/admin/strategy-requests/${request.id}`}>
                          <Button variant="outline" className="w-full rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
                            <Edit3 className="mr-2 h-4 w-4" />
                            Detail
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </GlassCard>
                );
              })}
            </div>
          )}

          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Showing {requests.length} of {requestTotal}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                disabled={requestSkip === 0}
                onClick={() => void loadData(Math.max(0, requestSkip - requestLimit), strategySkip)}
                className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                disabled={requestSkip + requestLimit >= requestTotal}
                onClick={() => void loadData(requestSkip + requestLimit, strategySkip)}
                className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}

      {activeTab === "strategies" && (
        <div className="space-y-4">
          <GlassCard className="border border-border/60 bg-card/25 p-4">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
              <div className="md:col-span-2">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
                  <input
                    value={strategySearch}
                    onChange={(event) => setStrategySearch(event.target.value)}
                    className={`${fieldClass} pl-9`}
                    placeholder="Search by strategy name or id"
                  />
                </div>
              </div>

              <select
                value={strategyVisibility}
                onChange={(event) => setStrategyVisibility(event.target.value as "" | StrategyVisibility)}
                className={fieldClass}
              >
                <option value="">All visibility</option>
                <option value="PUBLIC">Published</option>
                <option value="PRIVATE">Private</option>
              </select>

              <select
                value={strategySource}
                onChange={(event) => setStrategySource(event.target.value as "" | "MANUAL" | "REQUESTED")}
                className={fieldClass}
              >
                <option value="">All sources</option>
                <option value="MANUAL">Manual</option>
                <option value="REQUESTED">From Request</option>
              </select>

              <Button
                onClick={() => void loadData(requestSkip, 0)}
                className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Filter className="mr-2 h-4 w-4" />
                Apply
              </Button>
            </div>
          </GlassCard>

          {loading ? (
            renderLoadingGrid()
          ) : strategies.length === 0 ? (
            <GlassCard className="border border-border/60 bg-card/25 p-8 text-center text-muted-foreground">
              No strategies found for selected filters.
            </GlassCard>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {strategies.map((strategy) => {
                const isPublic = (strategy.visibility || "PRIVATE") === "PUBLIC";

                return (
                  <GlassCard key={strategy.id} className="border border-border/60 bg-card/30 shadow-xl">
                    <div className="space-y-4 p-5">
                      {coverAsset(strategy) ? (
                        <div className="overflow-hidden rounded-xl border border-border/50 bg-card/20">
                          <AuthenticatedStrategyImage
                            src={assetUrl(coverAsset(strategy))}
                            alt={assetName(coverAsset(strategy))}
                            fileName={assetName(coverAsset(strategy))}
                            compact
                            showOpen={false}
                            showDownload={false}
                          />
                        </div>
                      ) : null}
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="text-lg font-semibold tracking-tight text-foreground">{strategy.name}</h3>
                          <p className="mt-1 text-xs text-muted-foreground">ID: {strategy.id}</p>
                        </div>
                        <Badge
                          className={
                            isPublic
                              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                              : "border-border/60 bg-card/40 text-muted-foreground"
                          }
                        >
                          {isPublic ? "Published" : "Private"}
                        </Badge>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {strategy.sourceRequestId || strategy.source_request_id ? (
                          <Badge className="border-sky-500/30 bg-sky-500/10 text-sky-200">Requested User Strategy</Badge>
                        ) : (
                          <Badge className="border-border/60 bg-card/40 text-muted-foreground">Manual Admin Strategy</Badge>
                        )}
                        <Badge className="border-amber-500/30 bg-amber-500/10 text-amber-200">
                          {strategy.workspaceStatus || strategy.workspace_status || "Workspace Created"}
                        </Badge>
                      </div>

                      <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
                        {strategy.description || "No description provided."}
                      </p>

                      <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                        <div>Win Rate: {strategy.winRate ?? "—"}</div>
                        <div>Sharpe: {strategy.sharpeRatio ?? "—"}</div>
                        <div>Drawdown: {strategy.maxDrawdown ?? "—"}</div>
                        <div>Trades: {strategy.totalTrades ?? "—"}</div>
                      </div>

                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{formatDateTime(strategy.updatedAt || strategy.updated_at || strategy.createdAt || strategy.created_at)}</span>
                        {strategy.sourceRequestId || strategy.source_request_id ? (
                          <span className="inline-flex items-center gap-1">
                            <Sparkles className="h-3.5 w-3.5" />
                            Request: {strategy.sourceRequestId || strategy.source_request_id}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1">
                            <ShieldCheck className="h-3.5 w-3.5" />
                            Manual
                          </span>
                        )}
                      </div>

                      <div className="rounded-xl border border-border/40 bg-card/20 px-3 py-2 text-xs text-muted-foreground">
                        Source Code: {strategy.sourceCode || strategy.source_code ? "Attached" : "Not attached yet"}
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <Button
                          asChild
                          variant="outline"
                          className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
                        >
                          <Link href={`/admin/strategy-requests/strategies/${strategy.id}`}>
                            <Edit3 className="mr-2 h-4 w-4" />
                            Open Workspace
                          </Link>
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
                          onClick={() => void handleValidateStrategy(strategy)}
                        >
                          Verify Code
                        </Button>

                        {strategy.sourceRequestId || strategy.source_request_id ? (
                          <Button
                            variant="outline"
                            className="rounded-xl border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20"
                            onClick={() => void handleDeployPrivateStrategy(strategy)}
                            disabled={saving || isPublic}
                          >
                            <Send className="mr-2 h-4 w-4" />
                            Deploy Private
                          </Button>
                        ) : null}

                        <Button
                          variant="outline"
                          className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
                          onClick={() => void handleTogglePublish(strategy)}
                        >
                          <Upload className="mr-2 h-4 w-4" />
                          {isPublic ? "Unpublish" : "Publish Public"}
                        </Button>

                        <Button
                          variant="outline"
                          className="col-span-2 rounded-xl border-rose-500/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20"
                          onClick={() => void handleDeleteStrategy(strategy)}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </Button>
                      </div>
                    </div>
                  </GlassCard>
                );
              })}
            </div>
          )}

          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Showing {strategies.length} of {strategyTotal}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                disabled={strategySkip === 0}
                onClick={() => void loadData(requestSkip, Math.max(0, strategySkip - strategyLimit))}
                className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                disabled={strategySkip + strategyLimit >= strategyTotal}
                onClick={() => void loadData(requestSkip, strategySkip + strategyLimit)}
                className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}

      <Dialog open={!!selectedRequest} onOpenChange={(open) => !open && setSelectedRequest(null)}>
        <DialogContent className="max-h-[calc(100vh-80px)] max-w-2xl overflow-y-auto rounded-xl border border-border/60 bg-card/95 text-foreground">
          <DialogHeader>
            <DialogTitle>Manage Strategy Request</DialogTitle>
          </DialogHeader>

          {selectedRequest && (
            <div className="space-y-4">
              <div className="rounded-xl border border-border/50 bg-card/30 p-4">
                <h3 className="text-base font-semibold text-foreground">{selectedRequest.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{selectedRequest.user_name || selectedRequest.user_email}</p>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  {selectedRequest.description || selectedRequest.entry_rules || "No details available."}
                </p>
              </div>

              {(selectedRequest.attachments?.length || 0) > 0 && (
                <StrategyAttachmentGallery attachments={selectedRequest.attachments} />
              )}

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm text-muted-foreground">Request Status</label>
                  <select
                    value={requestStatusDraft}
                    onChange={(event) => setRequestStatusDraft(event.target.value)}
                    className={fieldClass}
                  >
                    {REQUEST_STATUSES.map((status) => (
                      <option key={status} value={status}>
                        {STATUS_LABEL[status] || status}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm text-muted-foreground">Deploy Into Existing Strategy (optional)</label>
                  <select
                    value={requestDeployTargetId}
                    onChange={(event) => setRequestDeployTargetId(event.target.value)}
                    className={fieldClass}
                  >
                    <option value="">Create new strategy</option>
                    {strategyOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm text-muted-foreground">Admin Notes</label>
                <textarea
                  value={requestNotesDraft}
                  onChange={(event) => setRequestNotesDraft(event.target.value)}
                  className={fieldClass}
                  rows={4}
                  placeholder="Status explanation and development notes"
                />
              </div>
            </div>
          )}

          <DialogFooter className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Button
              variant="outline"
              className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
              disabled={saving}
              onClick={() => void handleRequestUpdate()}
            >
              <Send className="mr-2 h-4 w-4" />
              Save Status
            </Button>

            <Button
              variant="outline"
              className="rounded-xl border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20"
              disabled={saving}
              onClick={() => void handleDeploy(false)}
            >
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Deploy Private to User
            </Button>

            <Button
              variant="outline"
              className="rounded-xl border-primary/40 bg-primary/15 text-primary hover:bg-primary/25"
              disabled={saving}
              onClick={() => void handleDeploy(true)}
            >
              <Upload className="mr-2 h-4 w-4" />
              Publish Public for All
            </Button>

            <Button
              variant="outline"
              className="rounded-xl border-rose-500/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20"
              disabled={saving}
              onClick={() => {
                setRequestStatusDraft("REJECTED");
                void handleRequestUpdate();
              }}
            >
              <XCircle className="mr-2 h-4 w-4" />
              Reject Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={editorOpen} onOpenChange={(open) => !open && setEditorOpen(false)}>
        <DialogContent className="max-h-[calc(100vh-80px)] max-w-4xl overflow-y-auto rounded-xl border border-border/60 bg-card/95 text-foreground">
          <DialogHeader>
            <DialogTitle>{editorMode === "create" ? "Create Strategy" : "Edit Strategy"}</DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm text-muted-foreground">Strategy Name *</label>
              <input
                value={editorForm.name}
                onChange={(event) => setEditorForm((prev) => ({ ...prev, name: event.target.value }))}
                className={fieldClass}
                placeholder="Institutional Trend Pullback"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm text-muted-foreground">Visibility</label>
              <select
                value={editorForm.visibility}
                onChange={(event) =>
                  setEditorForm((prev) => ({
                    ...prev,
                    visibility: event.target.value as StrategyVisibility,
                  }))
                }
                className={fieldClass}
              >
                <option value="PRIVATE">Private Admin Draft</option>
                <option value="PUBLIC">Public Template</option>
              </select>
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm text-muted-foreground">Description</label>
            <textarea
              rows={3}
              value={editorForm.description}
              onChange={(event) => setEditorForm((prev) => ({ ...prev, description: event.target.value }))}
              className={fieldClass}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <label className="mb-2 block text-sm text-muted-foreground">Strategy Type</label>
              <input
                value={editorForm.strategy_type}
                onChange={(event) => setEditorForm((prev) => ({ ...prev, strategy_type: event.target.value }))}
                className={fieldClass}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm text-muted-foreground">Market</label>
              <input
                value={editorForm.market}
                onChange={(event) => setEditorForm((prev) => ({ ...prev, market: event.target.value }))}
                className={fieldClass}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm text-muted-foreground">Timeframe</label>
              <input
                value={editorForm.timeframe}
                onChange={(event) => setEditorForm((prev) => ({ ...prev, timeframe: event.target.value }))}
                className={fieldClass}
              />
            </div>
          </div>

          {[
            ["entry_rules", "Entry Rules"],
            ["exit_rules", "Exit Rules"],
            ["confirmation_rules", "Confirmation Rules"],
            ["risk_rules", "Risk Rules"],
            ["invalidation_rules", "Invalidation Rules"],
            ["trade_management_rules", "Trade Management Rules"],
            ["notes", "Additional Notes"],
            ["source_code", "Source Code"],
          ].map(([key, label]) => (
            <div key={key}>
              <label className="mb-2 block text-sm text-muted-foreground">{label}</label>
              <textarea
                rows={key === "source_code" ? 12 : 3}
                value={editorForm[key as keyof StrategyEditorForm] as string}
                onChange={(event) =>
                  setEditorForm((prev) => ({
                    ...prev,
                    [key]: event.target.value,
                  }))
                }
                className={key === "source_code" ? `${fieldClass} font-mono text-xs` : fieldClass}
              />
            </div>
          ))}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
            {[
              ["winRate", "Win Rate %"],
              ["sharpeRatio", "Sharpe Ratio"],
              ["maxDrawdown", "Drawdown %"],
              ["totalTrades", "Total Trades"],
              ["profitFactor", "Profit Factor"],
            ].map(([key, label]) => (
              <div key={key}>
                <label className="mb-2 block text-sm text-muted-foreground">{label}</label>
                <input
                  value={editorForm[key as keyof StrategyEditorForm] as string}
                  onChange={(event) =>
                    setEditorForm((prev) => ({
                      ...prev,
                      [key]: event.target.value,
                    }))
                  }
                  className={fieldClass}
                  placeholder="Optional"
                />
              </div>
            ))}
          </div>

          <DialogFooter className="mt-2">
            <Button
              variant="outline"
              className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
              onClick={() => setEditorOpen(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button
              className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={() => void handleCreateOrUpdateStrategy()}
              disabled={saving}
            >
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
              {editorMode === "create" ? "Create Strategy" : "Save Strategy"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
