"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ImageIcon, Loader2, Send } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { StrategyAttachmentGallery } from "@/components/strategies/StrategyAttachmentGallery";
import apiClient from "../../../../../../lib/axios";

type ApiEnvelope<T> = { success?: boolean; data?: T };
type Req = any;
const unwrap = <T,>(payload: ApiEnvelope<T> | T): T => payload && typeof payload === "object" && "success" in (payload as any) ? ((payload as ApiEnvelope<T>).data as T) : (payload as T);
const inputClassName = "w-full rounded-xl border border-border/60 bg-card/25 px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";
const sectionCardClass = "rounded-xl border border-border/50 bg-card/20 p-5 backdrop-blur-xl";
const normalize = (s?: string | null) => String(s || "SUBMITTED").trim().replace(/[\s-]+/g,"_").toUpperCase();
const editable = (s: string) => ["DRAFT","PENDING","SUBMITTED","UNDER_REVIEW","NEEDS_CLARIFICATION"].includes(s);

export default function EditStrategyRequestPage() {
  const params = useParams<{ requestId: string }>();
  const router = useRouter();
  const [form, setForm] = useState<Record<string,string>>({ title:"", strategy_type:"", market:"", timeframe:"", entry_rules:"", exit_rules:"", confirmation_rules:"", risk_rules:"", invalidation_rules:"", trade_management_rules:"", notes:"", clarification_reply:"" });
  const [existing, setExisting] = useState<Req | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    apiClient.get(`/api/v1/strategies/requests/${params.requestId}`).then((res) => {
      if (!mounted) return;
      const item = unwrap<Req>(res.data);
      const status = normalize(item.status);
      if (!editable(status)) setError("This request can no longer be edited. Please create a refinement request.");
      setExisting(item);
      setForm({ title:item.title || "", strategy_type:item.strategy_type || item.strategyType || "", market:item.market || "", timeframe:item.timeframe || "", entry_rules:item.entry_rules || "", exit_rules:item.exit_rules || "", confirmation_rules:item.confirmation_rules || "", risk_rules:item.risk_rules || "", invalidation_rules:item.invalidation_rules || "", trade_management_rules:item.trade_management_rules || "", notes:item.notes || "", clarification_reply:"" });
    }).catch((err) => setError(err?.message || "Unable to load request")).finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, [params.requestId]);

  const set = (key: string, value: string) => setForm((p) => ({ ...p, [key]: value }));
  const addFiles = (list: FileList | null) => { const allowed = ["image/png","image/jpeg","image/webp"]; const valid = Array.from(list || []).filter((f) => allowed.includes(f.type) && f.size <= 5 * 1024 * 1024); const existingCount = existing?.attachments?.length || 0; setFiles((prev) => [...prev, ...valid].slice(0, Math.max(0, 6 - existingCount))); };
  const submit = async (e: React.FormEvent) => { e.preventDefault(); setSaving(true); setError(null); setMessage(null); try { const body = new FormData(); Object.entries(form).forEach(([k,v]) => body.append(k, v || "")); body.append("indicators", "{}"); files.forEach((f) => body.append("attachments", f)); await apiClient.patch(`/api/v1/strategies/requests/${params.requestId}`, body); setMessage("Clarification submitted. Admin can review your updated request."); setTimeout(() => router.push(`/strategies/requests/${params.requestId}`), 600); } catch (err:any) { setError(err?.message || "Unable to update request"); } finally { setSaving(false); } };

  if (loading) return <div className="flex min-h-[360px] items-center justify-center text-muted-foreground"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading request...</div>;
  const status = normalize(existing?.status);
  const isAllowed = editable(status);
  return <div className="space-y-6"><PageHeader title="Update Strategy Request" subtitle="Edit your rules, reply to admin clarification, and add more screenshots." actions={<Button variant="outline" onClick={() => router.push("/strategies?tab=my")} className="rounded-xl border-border/60 bg-card/30 text-foreground"><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>} />
    {error ? <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div> : null}{message ? <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">{message}</div> : null}
    {existing?.admin_notes ? <GlassCard className="border border-yellow-500/30 bg-yellow-500/10 p-5"><Badge className="border-yellow-500/30 bg-yellow-500/10 text-yellow-100">Admin Clarification</Badge><p className="mt-3 whitespace-pre-wrap text-sm text-yellow-50">{existing.admin_notes}</p></GlassCard> : null}
    <form onSubmit={submit} className="space-y-5 opacity-100"><div className={sectionCardClass}><h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Strategy Identity</h3><div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">{[["title","Strategy Title *"],["strategy_type","Strategy Type"],["market","Market"],["timeframe","Timeframe"]].map(([k,l]) => <div key={k} className="space-y-2"><label className="text-sm text-muted-foreground">{l}</label><input value={form[k]} onChange={(e)=>set(k,e.target.value)} className={inputClassName} disabled={!isAllowed} /></div>)}</div></div>
      <div className={sectionCardClass}><h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Rule Details</h3><div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">{[["entry_rules","Entry Rules *"],["exit_rules","Exit Rules *"],["risk_rules","Risk Rules *"],["confirmation_rules","Confirmation Rules"],["invalidation_rules","Invalidation Rules"],["trade_management_rules","Trade Management Rules"],["notes","Additional Notes"]].map(([k,l]) => <div key={k} className="space-y-2"><label className="text-sm text-muted-foreground">{l}</label><textarea rows={4} value={form[k]} onChange={(e)=>set(k,e.target.value)} className={inputClassName} disabled={!isAllowed} /></div>)}</div></div>
      <div className={sectionCardClass}><h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Additional Clarification Reply</h3><p className="mt-2 text-sm text-muted-foreground">Explain what you changed or clarify what admin asked.</p><textarea rows={4} value={form.clarification_reply} onChange={(e)=>set("clarification_reply",e.target.value)} className={`${inputClassName} mt-4`} disabled={!isAllowed} /></div>
      <div className={sectionCardClass}><div className="mb-4 flex items-center gap-2"><ImageIcon className="h-5 w-5 text-primary" /><h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Screenshots</h3><Badge className="border-border/60 bg-card/40 text-muted-foreground">{existing?.attachments?.length || 0} existing</Badge></div><StrategyAttachmentGallery attachments={existing?.attachments} emptyText="No existing screenshots." />{isAllowed ? <><div className="mt-4 rounded-xl border border-dashed border-border/60 bg-card/20 p-4"><input type="file" multiple accept="image/png,image/jpeg,image/webp" onChange={(e)=>addFiles(e.target.files)} className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded-lg file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-semibold file:text-primary-foreground" /></div>{files.length ? <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">{files.map((file, i) => <div key={`${file.name}-${i}`} className="overflow-hidden rounded-xl border border-border/50 bg-card/25"><img src={URL.createObjectURL(file)} alt={file.name} className="h-28 w-full object-cover" /><div className="flex items-center justify-between gap-2 p-2 text-xs text-muted-foreground"><span className="truncate">{file.name}</span><button type="button" onClick={()=>setFiles((prev)=>prev.filter((_,idx)=>idx!==i))} className="text-rose-300">Remove</button></div></div>)}</div> : null}</> : null}</div>
      <div className="flex flex-wrap justify-end gap-3"><Button type="button" variant="outline" onClick={()=>router.push(`/strategies/requests/${params.requestId}`)} className="rounded-xl border-border/60 bg-card/30 text-foreground">Cancel</Button><Button disabled={saving || !isAllowed} className="rounded-xl bg-primary text-primary-foreground">{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />} Save Update / Resubmit Clarification</Button></div></form></div>;
}
