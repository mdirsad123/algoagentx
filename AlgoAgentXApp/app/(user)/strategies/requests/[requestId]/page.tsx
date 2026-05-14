"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, BarChart3, Clock3, ImageIcon, Loader2, MessageSquare, PenLine, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { StrategyAttachmentGallery } from "@/components/strategies/StrategyAttachmentGallery";
import apiClient from "../../../../../lib/axios";

type ApiEnvelope<T> = { success?: boolean; data?: T };
type StrategyRequest = {
  id: string; title: string; status: string; strategy_type?: string | null; strategyType?: string | null; market?: string | null; timeframe?: string | null;
  entry_rules?: string | null; exit_rules?: string | null; confirmation_rules?: string | null; risk_rules?: string | null; invalidation_rules?: string | null; trade_management_rules?: string | null; notes?: string | null;
  admin_notes?: string | null; user_update_notes?: string | null; userUpdateNotes?: string | null; clarification_submitted_at?: string | null; clarificationSubmittedAt?: string | null;
  deployed_strategy_id?: string | null; deployedStrategyId?: string | null; created_at?: string | null; createdAt?: string | null; updated_at?: string | null; updatedAt?: string | null; attachments?: any[];
};
const unwrap = <T,>(payload: ApiEnvelope<T> | T): T => payload && typeof payload === "object" && "success" in (payload as any) ? ((payload as ApiEnvelope<T>).data as T) : (payload as T);
const labels: Record<string,string> = { DRAFT:"Draft", PENDING:"Pending Review", SUBMITTED:"Pending Review", UNDER_REVIEW:"Under Review", NEEDS_CLARIFICATION:"Needs Clarification", UNDER_DEVELOPMENT:"Under Development", DEPLOYED:"Deployed", PUBLISHED:"Published", REJECTED:"Rejected" };
const normalize = (s?: string | null) => String(s || "SUBMITTED").trim().replace(/[\s-]+/g,"_").toUpperCase();
const editable = (s: string) => ["DRAFT","PENDING","SUBMITTED","UNDER_REVIEW","NEEDS_CLARIFICATION"].includes(s);
const fmt = (v?: string | null) => v ? new Date(v).toLocaleString() : "—";
function TextBlock({ title, value }: { title: string; value?: string | null }) { return <div className="rounded-xl border border-border/50 bg-card/20 p-4"><p className="text-xs uppercase tracking-wide text-muted-foreground">{title}</p><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground">{value || "—"}</p></div>; }

export default function UserStrategyRequestDetailPage() {
  const params = useParams<{ requestId: string }>();
  const router = useRouter();
  const [item, setItem] = useState<StrategyRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    apiClient.get(`/api/v1/strategies/requests/${params.requestId}`)
      .then((res) => mounted && setItem(unwrap<StrategyRequest>(res.data)))
      .catch((err) => mounted && setError(err?.message || "Unable to load request"))
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, [params.requestId]);

  if (loading) return <div className="flex min-h-[360px] items-center justify-center text-muted-foreground"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading request...</div>;
  if (error || !item) return <GlassCard className="border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200"><p>{error || "Request not found"}</p><Button className="mt-4" variant="outline" onClick={() => router.push("/strategies?tab=my")}>Back</Button></GlassCard>;
  const status = normalize(item.status);
  const linkedStrategyId = item.deployedStrategyId || item.deployed_strategy_id;
  return <div className="space-y-6">
    <PageHeader title={item.title} subtitle="Strategy request details, admin notes, clarification replies, and screenshots." actions={<Button variant="outline" onClick={() => router.push("/strategies?tab=my")} className="rounded-xl border-border/60 bg-card/30 text-foreground"><ArrowLeft className="mr-2 h-4 w-4" /> Back to Strategies</Button>} />
    <GlassCard className="border border-border/60 bg-card/30 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex flex-wrap items-center gap-2"><Badge className="border-primary/30 bg-primary/10 text-primary">{labels[status] || status}</Badge>{[item.strategyType || item.strategy_type, item.market, item.timeframe].filter(Boolean).map((v) => <Badge key={String(v)} variant="secondary" className="border-border/60 bg-card/40 text-foreground">{v}</Badge>)}</div>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2"><div className="flex items-center gap-2 text-sm text-muted-foreground"><Clock3 className="h-4 w-4" /> Submitted: {fmt(item.createdAt || item.created_at)}</div><div className="flex items-center gap-2 text-sm text-muted-foreground"><Clock3 className="h-4 w-4" /> Updated: {fmt(item.updatedAt || item.updated_at)}</div></div>
      {item.admin_notes ? <div className="mt-4 rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-4"><div className="flex items-center gap-2 font-semibold text-yellow-50"><MessageSquare className="h-4 w-4" /> Admin Notes</div><p className="mt-2 whitespace-pre-wrap text-sm text-yellow-100">{item.admin_notes}</p></div> : null}
      {(item.userUpdateNotes || item.user_update_notes) ? <div className="mt-4 rounded-xl border border-sky-500/30 bg-sky-500/10 p-4"><div className="flex items-center gap-2 font-semibold text-sky-50"><MessageSquare className="h-4 w-4" /> Your Clarification Reply</div><p className="mt-2 whitespace-pre-wrap text-sm text-sky-100">{item.userUpdateNotes || item.user_update_notes}</p></div> : null}
    </GlassCard>
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2"><TextBlock title="Entry Rules" value={item.entry_rules} /><TextBlock title="Exit Rules" value={item.exit_rules} /><TextBlock title="Confirmation Rules" value={item.confirmation_rules} /><TextBlock title="Risk Rules" value={item.risk_rules} /><TextBlock title="Invalidation Rules" value={item.invalidation_rules} /><TextBlock title="Trade Management Rules" value={item.trade_management_rules} /></div>
    <TextBlock title="Additional Notes" value={item.notes} />
    <GlassCard className="border border-border/60 bg-card/30 p-6 shadow-xl backdrop-blur-xl"><div className="mb-4 flex items-center gap-2"><ImageIcon className="h-5 w-5 text-primary" /><h2 className="text-lg font-semibold">Screenshots</h2><Badge className="border-border/60 bg-card/40 text-muted-foreground">{item.attachments?.length || 0}</Badge></div><StrategyAttachmentGallery attachments={item.attachments} emptyText="No screenshots attached." /></GlassCard>
    <div className="flex flex-wrap gap-3">{editable(status) ? <Button onClick={() => router.push(`/strategies/requests/${item.id}/edit`)} className="rounded-xl bg-primary text-primary-foreground"><PenLine className="mr-2 h-4 w-4" /> Update Request</Button> : null}{linkedStrategyId ? <Button onClick={() => router.push(`/strategies/${linkedStrategyId}`)} className="rounded-xl bg-primary text-primary-foreground"><BarChart3 className="mr-2 h-4 w-4" /> Open Strategy</Button> : null}{linkedStrategyId && ["DEPLOYED","PUBLISHED"].includes(status) ? <Button variant="outline" onClick={() => router.push(`/strategies/${linkedStrategyId}/refine`)} className="rounded-xl border-border/60 bg-card/30 text-foreground"><Sparkles className="mr-2 h-4 w-4" /> Request Refinement</Button> : null}</div>
  </div>;
}
