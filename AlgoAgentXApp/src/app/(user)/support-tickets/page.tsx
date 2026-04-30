"use client";

import { ChangeEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Clock3,
  FileArchive,
  FileText,
  Headset,
  Loader2,
  MessageCircle,
  MessageSquarePlus,
  Paperclip,
  ReceiptText,
  RefreshCcw,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  buildAttachmentUrl,
  supportApi,
  SupportAttachment,
  SupportCategory,
  SupportMessage,
  SupportPriority,
  SupportStatus,
  SupportTicket,
} from "@/lib/api/support";

const categories: Array<{ value: SupportCategory; label: string; icon: any; tips: string[]; placeholder: string }> = [
  {
    value: "ask_ai",
    label: "Ask AI",
    icon: Bot,
    tips: ["Strategy guidance", "Broker setup help", "Backtest result review"],
    placeholder: "Ask for strategy guidance, broker setup support, or backtest help...",
  },
  {
    value: "technical",
    label: "Technical",
    icon: AlertCircle,
    tips: ["Bugs or broken pages", "Login/session issues", "Upload or report problems"],
    placeholder: "Describe the bug, error message, page name, and steps to reproduce...",
  },
  {
    value: "billing",
    label: "Billing",
    icon: ReceiptText,
    tips: ["Credits", "Payments and invoices", "Subscriptions"],
    placeholder: "Share payment, credits, invoice, or subscription details...",
  },
];

const allowedAccept = ".jpg,.jpeg,.png,.webp,.pdf,.txt,.csv,.xlsx,.docx,.zip";
const maxFileBytes = 10 * 1024 * 1024;

const statusClasses: Record<string, string> = {
  open: "bg-emerald-500/15 text-emerald-100 border-emerald-400/25",
  in_progress: "bg-blue-500/15 text-blue-100 border-blue-400/25",
  waiting_user: "bg-amber-500/15 text-amber-100 border-amber-400/25",
  resolved: "bg-purple-500/15 text-purple-100 border-purple-400/25",
  closed: "bg-slate-500/15 text-slate-200 border-slate-400/25",
};

const priorityClasses: Record<string, string> = {
  low: "bg-white/10 text-purple-100 border-white/10",
  medium: "bg-cyan-500/15 text-cyan-100 border-cyan-400/25",
  high: "bg-orange-500/15 text-orange-100 border-orange-400/25",
  urgent: "bg-rose-500/15 text-rose-100 border-rose-400/25",
};

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(" ");

const labelize = (value?: string | null) => String(value || "-").replace(/_/g, " ");

const formatDate = (value?: string | null) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString();
};

const formatBytes = (bytes?: number | null) => {
  const size = Number(bytes || 0);
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

function Pill({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cx("inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide", className)}>{children}</span>;
}

function AttachmentList({ attachments }: { attachments?: SupportAttachment[] }) {
  if (!attachments?.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {attachments.map((attachment) => (
        <a
          key={attachment.id}
          href={buildAttachmentUrl(attachment.download_url)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex max-w-full items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-purple-100/85 transition hover:bg-white/10"
        >
          <Paperclip className="h-3.5 w-3.5 shrink-0 text-fuchsia-200" />
          <span className="truncate">{attachment.original_filename}</span>
          <span className="shrink-0 text-purple-100/45">{formatBytes(attachment.size_bytes)}</span>
        </a>
      ))}
    </div>
  );
}

function MessageBubble({ message }: { message: SupportMessage }) {
  const isUser = message.sender_role === "user";
  const isSystem = message.sender_role === "system";
  return (
    <div className={cx("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cx(
          "max-w-[92%] rounded-2xl border p-4 shadow-lg md:max-w-[78%]",
          isUser && "border-fuchsia-400/25 bg-fuchsia-500/15",
          message.sender_role === "admin" && "border-blue-400/25 bg-blue-500/15",
          isSystem && "border-white/10 bg-white/5"
        )}
      >
        <div className="mb-2 flex items-center justify-between gap-4 text-xs text-purple-100/55">
          <span className="font-semibold uppercase tracking-wide text-purple-100/75">{isUser ? "You" : isSystem ? "System" : "Support Team"}</span>
          <span>{formatDate(message.created_at)}</span>
        </div>
        <p className="whitespace-pre-wrap text-sm leading-6 text-purple-50/90">{message.message}</p>
        <AttachmentList attachments={message.attachments} />
      </div>
    </div>
  );
}

export default function SupportTicketsPage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const replyFileInputRef = useRef<HTMLInputElement | null>(null);

  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [replying, setReplying] = useState(false);
  const [closing, setClosing] = useState(false);
  const [form, setForm] = useState({
    category: "ask_ai" as SupportCategory,
    subject: "",
    message: "",
    priority: "medium" as SupportPriority,
  });
  const [attachments, setAttachments] = useState<File[]>([]);
  const [replyMessage, setReplyMessage] = useState("");
  const [replyAttachments, setReplyAttachments] = useState<File[]>([]);

  const activeCategory = categories.find((category) => category.value === form.category) || categories[0];

  const fetchTickets = async (showToast = false) => {
    try {
      setError(null);
      setLoading(true);
      const data = await supportApi.list();
      setTickets(data);
      if (selectedTicket) {
        const stillSelected = data.find((ticket) => ticket.id === selectedTicket.id);
        if (!stillSelected) setSelectedTicket(null);
      }
      if (showToast) toast.success("Tickets refreshed");
    } catch (err: any) {
      const message = err?.message || err?.response?.data?.detail || "Failed to load support tickets";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const orderedTickets = useMemo(
    () => [...tickets].sort((a, b) => +new Date(b.updated_at || b.created_at) - +new Date(a.updated_at || a.created_at)),
    [tickets]
  );

  const selectedMessages = useMemo(() => {
    if (!selectedTicket) return [];
    const messages = selectedTicket.messages?.length
      ? selectedTicket.messages
      : selectedTicket.replies?.length
        ? selectedTicket.replies
        : [
            {
              id: `${selectedTicket.id}-initial`,
              ticket_id: selectedTicket.id,
              sender_role: "user" as const,
              message: selectedTicket.message,
              created_at: selectedTicket.created_at,
              attachments: selectedTicket.attachments || [],
            },
          ];
    return [...messages].sort((a, b) => +new Date(a.created_at) - +new Date(b.created_at));
  }, [selectedTicket]);

  const validateFiles = (incoming: FileList | File[]) => {
    const files = Array.from(incoming);
    const valid: File[] = [];
    files.forEach((file) => {
      if (file.size > maxFileBytes) {
        toast.error(`${file.name} is larger than 10MB`);
        return;
      }
      valid.push(file);
    });
    return valid;
  };

  const handleTicketFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = validateFiles(event.target.files || []);
    setAttachments((prev) => [...prev, ...files]);
    event.target.value = "";
  };

  const handleReplyFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = validateFiles(event.target.files || []);
    setReplyAttachments((prev) => [...prev, ...files]);
    event.target.value = "";
  };

  const submitTicket = async () => {
    if (!form.subject.trim() || !form.message.trim()) {
      toast.error("Please add a subject and message.");
      return;
    }

    try {
      setSubmitting(true);
      const ticket = await supportApi.create({
        subject: form.subject.trim(),
        category: form.category,
        priority: form.priority,
        message: form.message.trim(),
        attachments,
      });
      toast.success("Support ticket submitted");
      setForm({ category: "ask_ai", subject: "", message: "", priority: "medium" });
      setAttachments([]);
      await fetchTickets();
      await openTicket(ticket.id);
    } catch (err: any) {
      toast.error(err?.message || err?.response?.data?.detail || "Failed to submit ticket");
    } finally {
      setSubmitting(false);
    }
  };

  const openTicket = async (ticketId: string) => {
    try {
      setDetailLoading(true);
      const detail = await supportApi.get(ticketId);
      setSelectedTicket(detail);
    } catch (err: any) {
      toast.error(err?.message || err?.response?.data?.detail || "Failed to open ticket");
    } finally {
      setDetailLoading(false);
    }
  };

  const sendReply = async () => {
    if (!selectedTicket) return;
    if (!replyMessage.trim() && replyAttachments.length === 0) {
      toast.error("Add a reply message or attachment.");
      return;
    }

    try {
      setReplying(true);
      await supportApi.reply(selectedTicket.id, replyMessage.trim(), replyAttachments);
      setReplyMessage("");
      setReplyAttachments([]);
      toast.success("Reply sent");
      await openTicket(selectedTicket.id);
      await fetchTickets();
    } catch (err: any) {
      toast.error(err?.message || err?.response?.data?.detail || "Failed to send reply");
    } finally {
      setReplying(false);
    }
  };

  const closeTicket = async () => {
    if (!selectedTicket) return;
    try {
      setClosing(true);
      await supportApi.close(selectedTicket.id);
      toast.success("Ticket closed");
      await openTicket(selectedTicket.id);
      await fetchTickets();
    } catch (err: any) {
      toast.error(err?.message || err?.response?.data?.detail || "Failed to close ticket");
    } finally {
      setClosing(false);
    }
  };

  const canClose = selectedTicket && ["open", "in_progress", "waiting_user"].includes(selectedTicket.status);

  return (
    <div className="space-y-6">
      <PageHeader title="Support Tickets" subtitle="Create requests, upload proof, track admin replies, and close resolved conversations." />

      <div className="grid gap-6 xl:grid-cols-[1.05fr_1.55fr]">
        <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-2xl bg-gradient-to-br from-fuchsia-500 to-blue-500 p-3 text-white shadow-lg">
              <MessageSquarePlus className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Create a support request</h2>
              <p className="text-sm text-purple-100/75">Ask AI, report bugs, or get billing help with attachments.</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              {categories.map((category) => {
                const Icon = category.icon;
                const active = form.category === category.value;
                return (
                  <button
                    key={category.value}
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, category: category.value }))}
                    className={cx(
                      "rounded-2xl border px-4 py-3 text-left text-sm font-medium transition-all",
                      active ? "border-fuchsia-400/50 bg-fuchsia-500/20 text-white shadow-lg" : "border-white/10 bg-white/5 text-purple-100/80 hover:bg-white/10"
                    )}
                  >
                    <Icon className="mb-2 h-4 w-4" />
                    {category.label}
                  </button>
                );
              })}
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="mb-3 flex items-center gap-2 text-white">
                <Sparkles className="h-4 w-4 text-fuchsia-300" />
                <span className="text-sm font-semibold">Smart support tips for {activeCategory.label}</span>
              </div>
              <div className="grid gap-2 sm:grid-cols-3">
                {activeCategory.tips.map((tip) => (
                  <div key={tip} className="rounded-xl border border-white/10 bg-black/10 px-3 py-2 text-xs text-purple-100/80">
                    {tip}
                  </div>
                ))}
              </div>
            </div>

            <Input
              value={form.subject}
              onChange={(event) => setForm((prev) => ({ ...prev, subject: event.target.value }))}
              placeholder="Short subject"
              className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/45"
            />

            <Textarea
              value={form.message}
              onChange={(event) => setForm((prev) => ({ ...prev, message: event.target.value }))}
              placeholder={activeCategory.placeholder}
              className="min-h-36 border-white/10 bg-white/10 text-white placeholder:text-purple-100/45"
            />

            <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
              <select
                value={form.priority}
                onChange={(event) => setForm((prev) => ({ ...prev, priority: event.target.value as SupportPriority }))}
                className="h-11 rounded-xl border border-white/10 bg-white/10 px-3 text-white outline-none"
              >
                <option className="bg-slate-950" value="low">Low priority</option>
                <option className="bg-slate-950" value="medium">Medium priority</option>
                <option className="bg-slate-950" value="high">High priority</option>
                <option className="bg-slate-950" value="urgent">Urgent priority</option>
              </select>
              <Button
                type="button"
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white"
              >
                <Paperclip className="mr-2 h-4 w-4" /> Attach files
              </Button>
              <input ref={fileInputRef} type="file" multiple accept={allowedAccept} onChange={handleTicketFiles} className="hidden" />
            </div>

            {attachments.length > 0 && (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-purple-100/60">Selected attachments</div>
                <div className="space-y-2">
                  {attachments.map((file, index) => (
                    <div key={`${file.name}-${index}`} className="flex items-center justify-between gap-3 rounded-xl bg-black/10 px-3 py-2 text-sm text-purple-100/85">
                      <span className="truncate"><FileText className="mr-2 inline h-4 w-4 text-fuchsia-200" />{file.name}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-purple-100/45">{formatBytes(file.size)}</span>
                        <button type="button" onClick={() => setAttachments((prev) => prev.filter((_, i) => i !== index))} className="text-purple-100/55 hover:text-white">
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Button onClick={submitTicket} disabled={submitting} className="w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white hover:opacity-95">
              {submitting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Submitting...</> : "Submit ticket"}
            </Button>
          </div>
        </GlassCard>

        <div className="grid gap-6 2xl:grid-cols-[0.9fr_1.1fr]">
          <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-white">My tickets</h2>
                <p className="text-sm text-purple-100/75">Only live backend tickets are shown here.</p>
              </div>
              <Button variant="outline" onClick={() => fetchTickets(true)} className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">
                <RefreshCcw className="h-4 w-4" />
              </Button>
            </div>

            {loading ? (
              <div className="grid gap-4">
                {[1, 2, 3].map((item) => <div key={item} className="h-28 animate-pulse rounded-2xl bg-white/5" />)}
              </div>
            ) : error ? (
              <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 p-6 text-center">
                <AlertCircle className="mx-auto mb-3 h-8 w-8 text-rose-200" />
                <p className="text-sm text-rose-100">{error}</p>
                <Button onClick={() => fetchTickets()} className="mt-4 rounded-xl bg-white/10 text-white hover:bg-white/20">Retry</Button>
              </div>
            ) : orderedTickets.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/15 bg-white/5 p-10 text-center text-purple-100/75">
                <Headset className="mx-auto mb-3 h-9 w-9 text-fuchsia-300" />
                No tickets yet. Create your first support request.
              </div>
            ) : (
              <div className="max-h-[720px] overflow-auto rounded-2xl border border-white/10 bg-white/[0.03]">
                <table className="min-w-full divide-y divide-white/10 text-left text-sm">
                  <thead className="sticky top-0 z-10 bg-[#33106b]/95 backdrop-blur-xl">
                    <tr className="text-xs uppercase tracking-[0.16em] text-purple-100/55">
                      <th className="px-4 py-3 font-semibold">Ticket</th>
                      <th className="px-4 py-3 font-semibold">Category</th>
                      <th className="px-4 py-3 font-semibold">Priority</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="px-4 py-3 font-semibold">Last Reply</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10">
                    {orderedTickets.map((ticket) => (
                      <tr
                        key={ticket.id}
                        onClick={() => openTicket(ticket.id)}
                        className={cx(
                          "cursor-pointer transition hover:bg-white/10",
                          selectedTicket?.id === ticket.id ? "bg-fuchsia-500/15" : "bg-transparent"
                        )}
                      >
                        <td className="px-4 py-4 align-top">
                          <div className="flex items-start gap-2">
                            {ticket.unread || Number(ticket.unread_count || 0) > 0 ? (
                              <span className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full bg-fuchsia-300 shadow-[0_0_12px_rgba(240,171,252,0.9)]" />
                            ) : null}
                            <div>
                              <div className="line-clamp-2 font-semibold text-white">{ticket.subject}</div>
                              <div className="mt-1 text-xs text-purple-100/50">Created {formatDate(ticket.created_at)}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 align-top text-purple-100/80">{labelize(ticket.category)}</td>
                        <td className="px-4 py-4 align-top">
                          <Pill className={priorityClasses[ticket.priority] || priorityClasses.medium}>{ticket.priority}</Pill>
                        </td>
                        <td className="px-4 py-4 align-top">
                          <Pill className={statusClasses[ticket.status] || statusClasses.open}>{labelize(ticket.status)}</Pill>
                        </td>
                        <td className="px-4 py-4 align-top text-xs text-purple-100/60">{formatDate(ticket.last_reply_at || ticket.updated_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </GlassCard>

          <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
            {!selectedTicket ? (
              <div className="flex min-h-[520px] flex-col items-center justify-center rounded-2xl border border-dashed border-white/15 bg-white/5 p-8 text-center">
                <MessageCircle className="mb-4 h-10 w-10 text-fuchsia-300" />
                <h2 className="text-xl font-semibold text-white">Open a ticket conversation</h2>
                <p className="mt-2 max-w-md text-sm text-purple-100/65">Select a ticket from My tickets to view admin replies, uploaded files, and send follow-up messages.</p>
              </div>
            ) : detailLoading ? (
              <div className="flex min-h-[520px] items-center justify-center text-purple-100/75">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading conversation...
              </div>
            ) : (
              <div className="space-y-5">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <Pill className={statusClasses[selectedTicket.status] || statusClasses.open}>{labelize(selectedTicket.status)}</Pill>
                        <Pill className={priorityClasses[selectedTicket.priority] || priorityClasses.medium}>{selectedTicket.priority}</Pill>
                        <Pill className="border-white/10 bg-white/10 text-purple-100">{labelize(selectedTicket.category)}</Pill>
                      </div>
                      <h2 className="text-xl font-semibold text-white">{selectedTicket.subject}</h2>
                      <p className="mt-1 text-xs text-purple-100/55">Created {formatDate(selectedTicket.created_at)} • Last reply {formatDate(selectedTicket.last_reply_at || selectedTicket.updated_at)}</p>
                    </div>
                    {canClose && (
                      <Button onClick={closeTicket} disabled={closing} variant="outline" className="border-emerald-400/25 bg-emerald-500/10 text-emerald-100 hover:bg-emerald-500/20 hover:text-white">
                        {closing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
                        Close Ticket
                      </Button>
                    )}
                  </div>
                </div>

                <div className="max-h-[520px] space-y-4 overflow-y-auto rounded-2xl border border-white/10 bg-black/10 p-4">
                  {selectedMessages.length === 0 ? (
                    <div className="p-8 text-center text-purple-100/65"><Clock3 className="mx-auto mb-3 h-8 w-8" />No messages yet.</div>
                  ) : (
                    selectedMessages.map((message) => <MessageBubble key={message.id} message={message} />)
                  )}
                </div>

                {selectedTicket.status === "closed" ? (
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-purple-100/70">This ticket is closed. Sending a new reply will reopen it from backend if allowed.</div>
                ) : null}

                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <Textarea
                    value={replyMessage}
                    onChange={(event) => setReplyMessage(event.target.value)}
                    placeholder="Write a reply to support team..."
                    className="min-h-24 border-white/10 bg-white/10 text-white placeholder:text-purple-100/45"
                  />
                  {replyAttachments.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {replyAttachments.map((file, index) => (
                        <div key={`${file.name}-${index}`} className="flex items-center justify-between gap-3 rounded-xl bg-black/10 px-3 py-2 text-sm text-purple-100/85">
                          <span className="truncate"><FileArchive className="mr-2 inline h-4 w-4 text-fuchsia-200" />{file.name}</span>
                          <button type="button" onClick={() => setReplyAttachments((prev) => prev.filter((_, i) => i !== index))} className="text-purple-100/55 hover:text-white">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:justify-between">
                    <Button type="button" variant="outline" onClick={() => replyFileInputRef.current?.click()} className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">
                      <Paperclip className="mr-2 h-4 w-4" /> Attach
                    </Button>
                    <input ref={replyFileInputRef} type="file" multiple accept={allowedAccept} onChange={handleReplyFiles} className="hidden" />
                    <Button onClick={sendReply} disabled={replying} className="rounded-xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white hover:opacity-95">
                      {replying ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending...</> : <><Send className="mr-2 h-4 w-4" /> Send reply</>}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
