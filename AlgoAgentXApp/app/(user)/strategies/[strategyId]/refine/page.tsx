"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ImageIcon, Loader2, Send, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import apiClient from "../../../../../lib/axios";

type ApiEnvelope<T> = { success?: boolean; data?: T };

type StrategyDetail = {
  id: string;
  name: string;
  visibility?: string;
  market?: string;
  timeframe?: string;
  strategy_type?: string;
  strategyType?: string;
  parameters?: Record<string, any>;
  entry_rules?: string;
  exit_rules?: string;
  confirmation_rules?: string;
  risk_rules?: string;
  invalidation_rules?: string;
  trade_management_rules?: string;
  notes?: string;
};

const unwrap = <T,>(payload: ApiEnvelope<T> | T): T =>
  payload && typeof payload === "object" && "success" in (payload as any)
    ? ((payload as ApiEnvelope<T>).data as T)
    : (payload as T);

const inputClassName =
  "w-full rounded-xl border border-border/60 bg-card/25 px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";
const sectionCardClass = "rounded-2xl border border-border/50 bg-card/20 p-5 shadow-xl backdrop-blur-xl";
const allowedTypes = ["image/png", "image/jpeg", "image/webp"];
const maxSize = 5 * 1024 * 1024;

export default function StrategyRefinementPage() {
  const params = useParams<{ strategyId: string }>();
  const router = useRouter();
  const [strategy, setStrategy] = useState<StrategyDetail | null>(null);
  const [form, setForm] = useState<Record<string, string>>({
    requested_changes: "",
    entry_rules: "",
    exit_rules: "",
    confirmation_rules: "",
    risk_rules: "",
    invalidation_rules: "",
    trade_management_rules: "",
    notes: "",
  });
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    apiClient
      .get<ApiEnvelope<StrategyDetail> | StrategyDetail>(`/api/v1/strategies/${params.strategyId}`)
      .then((res) => {
        if (!mounted) return;
        const item = unwrap<StrategyDetail>(res.data);
        const source = item.parameters || {};
        setStrategy(item);
        setForm((previous) => ({
          ...previous,
          entry_rules: item.entry_rules || source.entry_rules || "",
          exit_rules: item.exit_rules || source.exit_rules || "",
          confirmation_rules: item.confirmation_rules || source.confirmation_rules || "",
          risk_rules: item.risk_rules || source.risk_rules || "",
          invalidation_rules: item.invalidation_rules || source.invalidation_rules || "",
          trade_management_rules: item.trade_management_rules || source.trade_management_rules || "",
        }));
      })
      .catch((err) => setError(err?.response?.data?.detail || err?.message || "Unable to load strategy"))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, [params.strategyId]);

  const previews = useMemo(() => files.map((file) => ({ file, url: URL.createObjectURL(file) })), [files]);

  useEffect(() => () => previews.forEach((item) => URL.revokeObjectURL(item.url)), [previews]);

  const set = (key: string, value: string) => setForm((previous) => ({ ...previous, [key]: value }));

  const addFiles = (list: FileList | null) => {
    const incoming = Array.from(list || []);
    const valid: File[] = [];
    for (const file of incoming) {
      if (!allowedTypes.includes(file.type)) {
        toast.error(`${file.name} is not PNG, JPG, or WEBP`);
        continue;
      }
      if (file.size > maxSize) {
        toast.error(`${file.name} is larger than 5 MB`);
        continue;
      }
      valid.push(file);
    }
    setFiles((previous) => [...previous, ...valid].slice(0, 6));
  };

  const removeFile = (index: number) => setFiles((previous) => previous.filter((_, itemIndex) => itemIndex !== index));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.requested_changes.trim()) {
      toast.error("Please describe what should be improved.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const body = new FormData();
      body.append("requested_changes", form.requested_changes.trim());
      body.append("refinement_notes", form.requested_changes.trim());
      body.append("notes", form.notes.trim() || form.requested_changes.trim());
      body.append("entry_rules", form.entry_rules);
      body.append("exit_rules", form.exit_rules);
      body.append("confirmation_rules", form.confirmation_rules);
      body.append("risk_rules", form.risk_rules);
      body.append("invalidation_rules", form.invalidation_rules);
      body.append("trade_management_rules", form.trade_management_rules);
      body.append("title", `Refinement: ${strategy?.name || "Strategy"}`);
      files.forEach((file) => body.append("attachments", file));
      await apiClient.post(`/api/v1/strategies/${params.strategyId}/refinement-request`, body);
      toast.success("Refinement request submitted. Admin will review your V2 request.");
      router.push("/strategies?tab=my");
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Unable to submit refinement request";
      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[360px] items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading strategy...
      </div>
    );
  }

  const parameters = strategy?.parameters || {};
  const visibility = (strategy?.visibility || "PRIVATE").toUpperCase();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Request Strategy Refinement"
        subtitle="Create a V2 improvement request without changing the original deployed strategy."
        actions={
          <Button variant="outline" onClick={() => router.push(`/strategies/${params.strategyId}`)} className="rounded-xl border-border/60 bg-card/30 text-foreground">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back
          </Button>
        }
      />

      {error ? <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div> : null}

      <GlassCard className="border border-border/60 bg-card/30 p-6 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Original Strategy</p>
            <h2 className="mt-1 text-xl font-semibold text-foreground">{strategy?.name || "Strategy"}</h2>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">Original strategy stays unchanged. Admin will review this as a new V2 refinement request.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge className="border-primary/30 bg-primary/10 text-primary">{visibility}</Badge>
            {[strategy?.market || parameters.market, strategy?.timeframe || parameters.timeframe, strategy?.strategyType || strategy?.strategy_type || parameters.strategy_type]
              .filter(Boolean)
              .map((item) => (
                <Badge key={String(item)} variant="secondary" className="border-border/60 bg-card/40 text-foreground">
                  {String(item)}
                </Badge>
              ))}
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-3">
          <Summary label="Current Entry" value={strategy?.entry_rules || parameters.entry_rules} />
          <Summary label="Current Exit" value={strategy?.exit_rules || parameters.exit_rules} />
          <Summary label="Current Risk" value={strategy?.risk_rules || parameters.risk_rules} />
        </div>
      </GlassCard>

      <form onSubmit={submit} className="space-y-5">
        <div className={sectionCardClass}>
          <label className="text-sm font-medium text-foreground">What should be improved? *</label>
          <textarea
            rows={5}
            value={form.requested_changes}
            onChange={(event) => set("requested_changes", event.target.value)}
            className={`${inputClassName} mt-2`}
            required
            placeholder="Explain the exact V2 changes, what failed in current version, or what improvement admin should build."
          />
        </div>

        <div className={sectionCardClass}>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Rule changes for V2</h3>
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {[
              ["entry_rules", "Entry rule changes"],
              ["exit_rules", "Exit rule changes"],
              ["confirmation_rules", "Confirmation rule changes"],
              ["risk_rules", "Risk changes"],
              ["invalidation_rules", "Invalidation changes"],
              ["trade_management_rules", "Trade management changes"],
              ["notes", "Additional notes"],
            ].map(([key, label]) => (
              <div key={key} className="space-y-2">
                <label className="text-sm text-muted-foreground">{label}</label>
                <textarea rows={4} value={form[key]} onChange={(event) => set(key, event.target.value)} className={inputClassName} />
              </div>
            ))}
          </div>
        </div>

        <div className={sectionCardClass}>
          <div className="flex items-center gap-2">
            <ImageIcon className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Screenshots</h3>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">Optional but recommended. Maximum 6 images, PNG/JPG/WEBP, 5 MB each.</p>
          <input
            type="file"
            multiple
            accept="image/png,image/jpeg,image/webp"
            onChange={(event) => addFiles(event.target.files)}
            className="mt-4 block w-full text-sm text-muted-foreground file:mr-4 file:rounded-lg file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-semibold file:text-primary-foreground"
          />
          {previews.length ? (
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {previews.map(({ file, url }, index) => (
                <div key={`${file.name}-${index}`} className="overflow-hidden rounded-xl border border-border/50 bg-card/25">
                  <img src={url} alt={file.name} className="h-32 w-full object-cover" />
                  <div className="flex items-center justify-between gap-2 p-3">
                    <p className="truncate text-xs text-muted-foreground">{file.name}</p>
                    <Button type="button" variant="ghost" size="icon" onClick={() => removeFile(index)} className="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground">
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div className="flex justify-end">
          <Button disabled={saving} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
            {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
            Submit Refinement Request
          </Button>
        </div>
      </form>
    </div>
  );
}

function Summary({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="rounded-xl border border-border/50 bg-card/20 p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-2 line-clamp-4 whitespace-pre-wrap text-sm leading-6 text-foreground">{value || "—"}</p>
    </div>
  );
}
