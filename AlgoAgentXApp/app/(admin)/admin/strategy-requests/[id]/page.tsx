"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Loader2,
  Save,
  Send,
  Upload,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { adminApi, StrategyRequest } from "@/lib/api/admin";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";

const STATUS_LABEL: Record<string, string> = {
  UNDER_DEVELOPMENT: "Under Development",
  NEEDS_CLARIFICATION: "Needs Clarification",
  REJECTED: "Rejected",
  DEPLOYED: "Deployed",
};

const STATUS_BADGE_CLASS: Record<string, string> = {
  UNDER_DEVELOPMENT: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  NEEDS_CLARIFICATION: "border-sky-500/30 bg-sky-500/10 text-sky-200",
  REJECTED: "border-rose-500/30 bg-rose-500/10 text-rose-200",
  DEPLOYED: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
};

const fieldClass =
  "w-full rounded-xl border border-border/60 bg-card/25 px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";

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

export default function AdminStrategyRequestDetailPage() {
  const router = useRouter();
  const params = useParams();
  const requestId = params.id as string;

  const [request, setRequest] = useState<StrategyRequest | null>(null);
  const [statusDraft, setStatusDraft] = useState("UNDER_DEVELOPMENT");
  const [adminNotes, setAdminNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadRequest = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getStrategy(requestId);
      setRequest(data);
      setStatusDraft(data.status || "UNDER_DEVELOPMENT");
      setAdminNotes(data.admin_notes || "");
    } catch (error: any) {
      toast.error(error?.message || "Failed to load strategy request");
      router.push("/admin/strategy-requests");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRequest();
  }, [requestId]);

  const statusBadgeClass = useMemo(() => {
    if (!request) return "border-border/60 bg-card/40 text-muted-foreground";
    return STATUS_BADGE_CLASS[request.status] || "border-border/60 bg-card/40 text-muted-foreground";
  }, [request]);

  const saveStatus = async () => {
    if (!request) return;

    setSaving(true);
    try {
      const updated = await adminApi.updateStrategy(request.id, {
        status: statusDraft,
        admin_notes: adminNotes || undefined,
      });
      setRequest(updated);
      toast.success("Request updated");
    } catch (error: any) {
      toast.error(error?.message || "Unable to update request");
    } finally {
      setSaving(false);
    }
  };

  const deployRequest = async (publish = false) => {
    if (!request) return;

    setSaving(true);
    try {
      await adminApi.deployStrategyWithPayload(request.id, {
        publish,
        visibility: publish ? "PUBLIC" : "PRIVATE",
        admin_notes: adminNotes || undefined,
      });
      toast.success(publish ? "Request deployed and published" : "Request deployed");
      await loadRequest();
    } catch (error: any) {
      toast.error(error?.message || "Unable to deploy request");
    } finally {
      setSaving(false);
    }
  };

  const rejectRequest = async () => {
    setStatusDraft("REJECTED");
    await saveStatus();
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!request) {
    return (
      <GlassCard className="border border-border/60 bg-card/30 p-6 text-center text-muted-foreground">
        Strategy request not found.
      </GlassCard>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Button
            variant="outline"
            onClick={() => router.push("/admin/strategy-requests")}
            className="mb-2 rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to strategy management
          </Button>

          <h1 className="text-2xl font-semibold tracking-tight text-foreground">{request.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">Request ID: {request.id}</p>
        </div>

        <Badge className={statusBadgeClass}>{STATUS_LABEL[request.status] || request.status}</Badge>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2 border border-border/60 bg-card/30 p-5">
          <h2 className="text-lg font-semibold text-foreground">Request Details</h2>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3 text-sm">
            <div className="rounded-xl border border-border/50 bg-card/20 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">User</p>
              <p className="mt-1 text-foreground">{request.user_name || request.user_email || "—"}</p>
            </div>
            <div className="rounded-xl border border-border/50 bg-card/20 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Submitted</p>
              <p className="mt-1 text-foreground">{formatDateTime(request.createdAt || request.created_at)}</p>
            </div>
            <div className="rounded-xl border border-border/50 bg-card/20 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Last Updated</p>
              <p className="mt-1 text-foreground">{formatDateTime(request.updatedAt || request.updated_at)}</p>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
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
            {(request.deployedStrategyId || request.deployed_strategy_id) && (
              <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-200">
                <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                Linked Strategy
              </Badge>
            )}
          </div>

          {[
            ["Entry Rules", request.entry_rules],
            ["Exit Rules", request.exit_rules],
            ["Risk Rules", request.risk_rules],
            ["Additional Notes", request.notes],
          ].map(([label, value]) => (
            <div key={label} className="mt-4 rounded-xl border border-border/50 bg-card/20 p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground">{value || "—"}</p>
            </div>
          ))}
        </GlassCard>

        <GlassCard className="border border-border/60 bg-card/30 p-5">
          <h2 className="text-lg font-semibold text-foreground">Admin Actions</h2>

          <div className="mt-4 space-y-4">
            <div>
              <label className="mb-2 block text-sm text-muted-foreground">Status</label>
              <select value={statusDraft} onChange={(e) => setStatusDraft(e.target.value)} className={fieldClass}>
                <option value="UNDER_DEVELOPMENT">Under Development</option>
                <option value="NEEDS_CLARIFICATION">Needs Clarification</option>
                <option value="REJECTED">Rejected</option>
                <option value="DEPLOYED">Deployed</option>
              </select>
            </div>

            <div>
              <label className="mb-2 block text-sm text-muted-foreground">Admin Notes</label>
              <textarea
                rows={7}
                className={fieldClass}
                value={adminNotes}
                onChange={(e) => setAdminNotes(e.target.value)}
                placeholder="Development notes or clarification guidance"
              />
            </div>

            <div className="grid grid-cols-1 gap-2">
              <Button
                onClick={() => void saveStatus()}
                disabled={saving}
                className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                Save Status
              </Button>

              <Button
                variant="outline"
                onClick={() => void deployRequest(false)}
                disabled={saving}
                className="rounded-xl border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20"
              >
                <Send className="mr-2 h-4 w-4" />
                Deploy Private
              </Button>

              <Button
                variant="outline"
                onClick={() => void deployRequest(true)}
                disabled={saving}
                className="rounded-xl border-primary/40 bg-primary/15 text-primary hover:bg-primary/25"
              >
                <Upload className="mr-2 h-4 w-4" />
                Deploy & Publish
              </Button>

              <Button
                variant="outline"
                onClick={() => void rejectRequest()}
                disabled={saving}
                className="rounded-xl border-rose-500/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20"
              >
                <XCircle className="mr-2 h-4 w-4" />
                Reject
              </Button>
            </div>
          </div>

          <div className="mt-4 rounded-xl border border-border/50 bg-card/20 p-3 text-xs text-muted-foreground">
            <p className="inline-flex items-center gap-1">
              <Clock3 className="h-3.5 w-3.5" />
              Last updated: {formatDateTime(request.updatedAt || request.updated_at)}
            </p>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
