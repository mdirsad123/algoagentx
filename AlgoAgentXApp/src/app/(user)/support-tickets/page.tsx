"use client";

import { useEffect, useMemo, useState } from "react";
import { Headset, MessageSquarePlus, Send, Sparkles } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { supportApi, SupportTicket } from "@/lib/api/support";
import { toast } from "sonner";

const aiSuggestions = [
  "Use Ask AI style requests for strategy guidance, broker setup, or backtest help.",
  "Use Technical Issue for bugs, broken pages, or login/session issues.",
  "Use Billing for credits, payments, subscriptions, and invoice requests.",
];

export default function SupportTicketsPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [replyingId, setReplyingId] = useState<string | null>(null);
  const [form, setForm] = useState({ type: "ask_ai", subject: "", message: "", priority: "medium" as "low" | "medium" | "high" });
  const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({});

  const fetchTickets = async () => {
    try {
      setLoading(true);
      const data = await supportApi.list();
      setTickets(data);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to load support tickets");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTickets(); }, []);

  const submitTicket = async () => {
    if (!form.subject.trim() || !form.message.trim()) {
      toast.error("Please add a subject and message.");
      return;
    }
    try {
      setSubmitting(true);
      await supportApi.create({
        subject: `[${form.type.replace('_', ' ').toUpperCase()}] ${form.subject}`,
        message: form.message,
        priority: form.priority,
      });
      toast.success("Support ticket submitted");
      setForm({ type: "ask_ai", subject: "", message: "", priority: "medium" });
      fetchTickets();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to submit ticket");
    } finally {
      setSubmitting(false);
    }
  };

  const sendReply = async (ticketId: string) => {
    const message = replyDrafts[ticketId]?.trim();
    if (!message) return;
    try {
      setReplyingId(ticketId);
      await supportApi.reply(ticketId, message);
      setReplyDrafts((prev) => ({ ...prev, [ticketId]: "" }));
      toast.success("Reply sent");
      fetchTickets();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to send reply");
    } finally {
      setReplyingId(null);
    }
  };

  const orderedTickets = useMemo(() => [...tickets].sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at)), [tickets]);

  return (
    <div className="space-y-6">
      <PageHeader title="Support Tickets" subtitle="Ask for help, route issues to the team, and track replies in one place." />
      <div className="grid gap-6 xl:grid-cols-[1.1fr_1.6fr]">
        <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-2xl bg-gradient-to-br from-fuchsia-500 to-blue-500 p-3 text-white shadow-lg"><MessageSquarePlus className="h-5 w-5" /></div>
            <div>
              <h2 className="text-xl font-semibold text-white">Create a support request</h2>
              <p className="text-sm text-purple-100/75">Use Ask AI, billing, or technical support flows.</p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              {[ ["ask_ai", "Ask AI"], ["technical", "Technical"], ["billing", "Billing"] ].map(([value, label]) => (
                <button key={value} onClick={() => setForm((prev) => ({ ...prev, type: value }))} className={["rounded-2xl border px-4 py-3 text-left text-sm font-medium transition-all", form.type === value ? "border-fuchsia-400/50 bg-fuchsia-500/20 text-white" : "border-white/10 bg-white/5 text-purple-100/80 hover:bg-white/10"].join(" ")}>{label}</button>
              ))}
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="mb-2 flex items-center gap-2 text-white"><Sparkles className="h-4 w-4 text-fuchsia-300" /><span className="text-sm font-semibold">Smart support tips</span></div>
              <ul className="space-y-2 text-sm text-purple-100/80">{aiSuggestions.map((tip) => <li key={tip}>• {tip}</li>)}</ul>
            </div>
            <Input value={form.subject} onChange={(e) => setForm((prev) => ({ ...prev, subject: e.target.value }))} placeholder="Short subject" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/45" />
            <Textarea value={form.message} onChange={(e) => setForm((prev) => ({ ...prev, message: e.target.value }))} placeholder="Describe the issue, ask your AI guidance question, or request support assignment..." className="min-h-36 border-white/10 bg-white/10 text-white placeholder:text-purple-100/45" />
            <select value={form.priority} onChange={(e) => setForm((prev) => ({ ...prev, priority: e.target.value as any }))} className="h-11 rounded-xl border border-white/10 bg-white/10 px-3 text-white focus:outline-none">
              <option value="low">Low priority</option><option value="medium">Medium priority</option><option value="high">High priority</option>
            </select>
            <Button onClick={submitTicket} disabled={submitting} className="w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white hover:opacity-95">{submitting ? "Submitting..." : "Submit ticket"}</Button>
          </div>
        </GlassCard>
        <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
          <div className="mb-5 flex items-center justify-between"><div><h2 className="text-xl font-semibold text-white">My tickets</h2><p className="text-sm text-purple-100/75">Track replies from the support team and continue the conversation.</p></div><Button variant="outline" onClick={fetchTickets} className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">Refresh</Button></div>
          {loading ? <div className="grid gap-4">{[1,2,3].map((i) => <div key={i} className="h-28 rounded-2xl bg-white/5 animate-pulse" />)}</div> : orderedTickets.length === 0 ? <div className="rounded-2xl border border-dashed border-white/15 bg-white/5 p-10 text-center text-purple-100/75"><Headset className="mx-auto mb-3 h-9 w-9 text-fuchsia-300" />No tickets yet. Create your first support request.</div> : <div className="space-y-4">{orderedTickets.map((ticket) => <div key={ticket.id} className="rounded-2xl border border-white/10 bg-white/5 p-5"><div className="mb-3 flex flex-wrap items-center gap-2"><span className="rounded-full bg-fuchsia-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-fuchsia-100">{ticket.status.replace('_', ' ')}</span><span className="rounded-full bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-100">{ticket.priority}</span><span className="text-xs text-purple-100/60">{new Date(ticket.created_at).toLocaleString()}</span></div><h3 className="text-lg font-semibold text-white">{ticket.subject}</h3><p className="mt-2 text-sm text-purple-100/80">{ticket.message}</p><div className="mt-4 space-y-3">{(ticket.replies || []).map((reply) => <div key={reply.id} className="rounded-xl border border-white/10 bg-black/10 p-3 text-sm text-purple-100/85"><div className="mb-1 text-xs uppercase tracking-wide text-purple-100/55">{reply.user_id ? "You" : "Support team"}</div><div>{reply.message}</div></div>)}</div>{ticket.status !== "closed" && <div className="mt-4 flex gap-3"><Input value={replyDrafts[ticket.id] || ""} onChange={(e) => setReplyDrafts((prev) => ({ ...prev, [ticket.id]: e.target.value }))} placeholder="Reply to this ticket" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/45" /><Button onClick={() => sendReply(ticket.id)} disabled={replyingId === ticket.id} className="rounded-xl bg-white/10 text-white hover:bg-white/20">{replyingId === ticket.id ? "Sending..." : <Send className="h-4 w-4" />}</Button></div>}</div>)}</div>}
        </GlassCard>
      </div>
    </div>
  );
}
