"use client";

import { ChangeEvent, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  FileText,
  Headset,
  Loader2,
  MessageCircle,
  Paperclip,
  RefreshCcw,
  Search,
  Send,
  ShieldCheck,
  UserRound,
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

const statusOptions: Array<{ value: "" | SupportStatus; label: string }> = [
  { value: "", label: "All" },
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In Progress" },
  { value: "waiting_user", label: "Waiting User" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
];

const priorityOptions: Array<{ value: "" | SupportPriority; label: string }> = [
  { value: "", label: "All priorities" },
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

const categoryOptions: Array<{ value: "" | SupportCategory; label: string }> = [
  { value: "", label: "All categories" },
  { value: "ask_ai", label: "Ask AI" },
  { value: "technical", label: "Technical" },
  { value: "billing", label: "Billing" },
  { value: "broker", label: "Broker" },
  { value: "live_trading", label: "Live Trading" },
  { value: "backtest", label: "Backtest" },
  { value: "strategy", label: "Strategy" },
  { value: "other", label: "Other" },
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

function FieldSelect({ value, onChange, children, className, disabled }: { value: string; onChange: (value: string) => void; children: ReactNode; className?: string; disabled?: boolean }) {
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className={cx(
        "h-11 rounded-2xl border border-white/10 bg-white/10 px-3 text-sm text-white outline-none transition focus:border-fuchsia-300/50 disabled:cursor-not-allowed disabled:opacity-60 [&_option]:bg-slate-950",
        className,
      )}
    >
      {children}
    </select>
  );
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

export default function AdminSupportTicketsPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<"" | SupportStatus>("");
  const [priorityFilter, setPriorityFilter] = useState<"" | SupportPriority>("");
  const [categoryFilter, setCategoryFilter] = useState<"" | SupportCategory>("");
  const [search, setSearch] = useState("");
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [reply, setReply] = useState("");
  const [replyStatus, setReplyStatus] = useState<SupportStatus>("waiting_user");
  const [replyFiles, setReplyFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const limit = 20;

  const messages: SupportMessage[] = useMemo(() => {
    if (!selectedTicket) return [];
    return selectedTicket.messages?.length
      ? selectedTicket.messages
      : [
          {
            id: `${selectedTicket.id}-root`,
            ticket_id: selectedTicket.id,
            sender_role: "user",
            message: selectedTicket.message,
            created_at: selectedTicket.created_at,
            attachments: selectedTicket.attachments,
          },
        ];
  }, [selectedTicket]);

  const stats = useMemo(() => {
    const open = tickets.filter((ticket) => ticket.status === "open" || ticket.status === "in_progress").length;
    const urgent = tickets.filter((ticket) => ticket.priority === "urgent").length;
    const waitingAdmin = tickets.filter((ticket) => ticket.last_reply_by === "user" && ticket.status !== "closed" && ticket.status !== "resolved").length;
    return { open, urgent, waitingAdmin };
  }, [tickets]);

  const loadTickets = useCallback(async (nextSkip = skip) => {
    setLoading(true);
    setListError(null);
    try {
      const response = await supportApi.adminList({
        skip: nextSkip,
        limit,
        status: statusFilter,
        priority: priorityFilter,
        category: categoryFilter,
        search: search.trim() || undefined,
      });
      setTickets(response.items);
      setTotal(response.total);
      setSkip(nextSkip);
      if (selectedTicket && !response.items.some((ticket) => ticket.id === selectedTicket.id)) {
        setSelectedTicket(null);
      }
    } catch (error: any) {
      const message = error?.message || "Failed to load support tickets";
      setListError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, priorityFilter, search, selectedTicket, skip, statusFilter]);

  const loadTicketDetail = useCallback(async (ticketId: string) => {
    setDetailLoading(true);
    setDetailError(null);
    try {
      const detail = await supportApi.adminGet(ticketId);
      setSelectedTicket(detail);
    } catch (error: any) {
      const message = error?.message || "Failed to load ticket conversation";
      setDetailError(message);
      toast.error(message);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTickets(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, priorityFilter, categoryFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => loadTickets(0), 350);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const selectTicket = (ticket: SupportTicket) => {
    setSelectedTicket(ticket);
    setReply("");
    setReplyFiles([]);
    setReplyStatus("waiting_user");
    loadTicketDetail(ticket.id);
  };

  const refreshAll = async () => {
    await loadTickets(skip);
    if (selectedTicket) await loadTicketDetail(selectedTicket.id);
  };

  const updateTicket = async (payload: { status?: SupportStatus; priority?: SupportPriority; category?: SupportCategory }) => {
    if (!selectedTicket) return;
    setSubmitting(true);
    try {
      const updated = await supportApi.adminUpdate(selectedTicket.id, payload);
      toast.success("Ticket updated");
      setSelectedTicket((prev) => (prev ? { ...prev, ...updated } : updated));
      await loadTickets(skip);
      await loadTicketDetail(selectedTicket.id);
    } catch (error: any) {
      toast.error(error?.message || "Failed to update ticket");
    } finally {
      setSubmitting(false);
    }
  };

  const assignToMe = async () => {
    if (!selectedTicket) return;
    setSubmitting(true);
    try {
      await supportApi.adminAssign(selectedTicket.id);
      toast.success("Ticket assigned to you");
      await loadTickets(skip);
      await loadTicketDetail(selectedTicket.id);
    } catch (error: any) {
      toast.error(error?.message || "Failed to assign ticket");
    } finally {
      setSubmitting(false);
    }
  };

  const onFilesSelected = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files || []);
    const valid: File[] = [];
    selected.forEach((file) => {
      if (file.size > maxFileBytes) {
        toast.error(`${file.name} is larger than 10MB`);
      } else {
        valid.push(file);
      }
    });
    setReplyFiles((prev) => [...prev, ...valid]);
    if (event.target) event.target.value = "";
  };

  const sendReply = async () => {
    if (!selectedTicket || (!reply.trim() && replyFiles.length === 0)) {
      toast.error("Write a reply or attach a file first");
      return;
    }
    setSubmitting(true);
    try {
      await supportApi.adminReply(selectedTicket.id, reply.trim(), replyFiles, replyStatus);
      toast.success("Reply sent to user");
      setReply("");
      setReplyFiles([]);
      await loadTickets(skip);
      await loadTicketDetail(selectedTicket.id);
    } catch (error: any) {
      toast.error(error?.message || "Failed to send reply");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Admin Support Inbox" subtitle="Reply to users, manage ticket status, assign ownership, and resolve support conversations." />

      <div className="grid gap-4 md:grid-cols-3">
        <GlassCard className="rounded-3xl border border-white/10 p-5 hover:scale-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-purple-100/65">Open / active</p>
              <p className="mt-1 text-3xl font-bold text-white">{stats.open}</p>
            </div>
            <Headset className="h-8 w-8 text-fuchsia-200" />
          </div>
        </GlassCard>
        <GlassCard className="rounded-3xl border border-white/10 p-5 hover:scale-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-purple-100/65">Urgent tickets</p>
              <p className="mt-1 text-3xl font-bold text-white">{stats.urgent}</p>
            </div>
            <AlertCircle className="h-8 w-8 text-rose-200" />
          </div>
        </GlassCard>
        <GlassCard className="rounded-3xl border border-white/10 p-5 hover:scale-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-purple-100/65">Waiting admin</p>
              <p className="mt-1 text-3xl font-bold text-white">{stats.waitingAdmin}</p>
            </div>
            <Clock3 className="h-8 w-8 text-amber-200" />
          </div>
        </GlassCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.35fr]">
        <GlassCard className="rounded-3xl border border-white/10 p-5 hover:scale-100">
          <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="flex items-center gap-2 text-xl font-semibold text-white">
                <MessageCircle className="h-5 w-5 text-fuchsia-200" /> Tickets
              </h2>
              <p className="mt-1 text-sm text-purple-100/65">{total} total matching tickets</p>
            </div>
            <Button onClick={() => refreshAll()} disabled={loading || detailLoading} className="rounded-2xl border border-white/10 bg-white/10 text-white hover:bg-white/15">
              <RefreshCcw className={cx("mr-2 h-4 w-4", loading && "animate-spin")} /> Refresh
            </Button>
          </div>

          <div className="mb-4 grid gap-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-purple-100/45" />
              <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search subject, email, message..." className="rounded-2xl border-white/10 bg-white/10 pl-10 text-white placeholder:text-purple-100/45" />
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              <FieldSelect value={statusFilter} onChange={(value) => setStatusFilter(value as "" | SupportStatus)}>
                {statusOptions.map((option) => <option key={option.value || "all"} value={option.value}>{option.label}</option>)}
              </FieldSelect>
              <FieldSelect value={priorityFilter} onChange={(value) => setPriorityFilter(value as "" | SupportPriority)}>
                {priorityOptions.map((option) => <option key={option.value || "all"} value={option.value}>{option.label}</option>)}
              </FieldSelect>
              <FieldSelect value={categoryFilter} onChange={(value) => setCategoryFilter(value as "" | SupportCategory)}>
                {categoryOptions.map((option) => <option key={option.value || "all"} value={option.value}>{option.label}</option>)}
              </FieldSelect>
            </div>
          </div>

          <div className="max-h-[720px] space-y-3 overflow-y-auto pr-1">
            {loading ? (
              Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="h-32 animate-pulse rounded-3xl border border-white/10 bg-white/5" />
              ))
            ) : listError ? (
              <div className="rounded-3xl border border-rose-300/20 bg-rose-500/10 p-6 text-center text-sm text-rose-100">
                <AlertCircle className="mx-auto mb-3 h-8 w-8" />
                <p>{listError}</p>
                <Button onClick={() => loadTickets(skip)} className="mt-4 rounded-2xl bg-white/10 text-white hover:bg-white/15">Retry</Button>
              </div>
            ) : tickets.length === 0 ? (
              <div className="rounded-3xl border border-white/10 bg-white/5 p-8 text-center text-purple-100/70">
                <MessageCircle className="mx-auto mb-3 h-10 w-10 text-purple-100/45" />
                <p className="font-semibold text-white">No tickets found</p>
                <p className="mt-1 text-sm">Try another status, priority, category, or search term.</p>
              </div>
            ) : (
              tickets.map((ticket) => (
                <button
                  key={ticket.id}
                  type="button"
                  onClick={() => selectTicket(ticket)}
                  className={cx(
                    "w-full rounded-3xl border p-4 text-left transition hover:-translate-y-0.5 hover:bg-white/10",
                    selectedTicket?.id === ticket.id ? "border-fuchsia-300/40 bg-fuchsia-500/10" : "border-white/10 bg-white/5",
                  )}
                >
                  <div className="mb-3 flex flex-wrap gap-2">
                    <Pill className={statusClasses[ticket.status] || statusClasses.open}>{labelize(ticket.status)}</Pill>
                    <Pill className={priorityClasses[ticket.priority] || priorityClasses.medium}>{labelize(ticket.priority)}</Pill>
                    <Pill className="border-white/10 bg-white/10 text-purple-100">{labelize(ticket.category)}</Pill>
                  </div>
                  <h3 className="line-clamp-2 text-base font-semibold text-white">{ticket.subject}</h3>
                  <div className="mt-2 flex items-center gap-2 text-xs text-purple-100/65">
                    <UserRound className="h-3.5 w-3.5" />
                    <span className="truncate">{ticket.user_name || ticket.user_email || ticket.user_id}</span>
                  </div>
                  <div className="mt-2 grid gap-1 text-xs text-purple-100/55">
                    <span>Created: {formatDate(ticket.created_at)}</span>
                    <span>Last reply: {formatDate(ticket.last_reply_at || ticket.updated_at)}</span>
                    <span>Assigned: {ticket.assigned_admin_name || ticket.assigned_admin_email || ticket.assigned_admin_id || "Unassigned"}</span>
                  </div>
                </button>
              ))
            )}
          </div>

          {total > limit && (
            <div className="mt-5 flex items-center justify-between border-t border-white/10 pt-4 text-sm text-purple-100/65">
              <span>{skip + 1} - {Math.min(skip + limit, total)} of {total}</span>
              <div className="flex gap-2">
                <Button disabled={skip === 0 || loading} onClick={() => loadTickets(Math.max(0, skip - limit))} className="rounded-2xl border border-white/10 bg-white/10 text-white hover:bg-white/15">Previous</Button>
                <Button disabled={skip + limit >= total || loading} onClick={() => loadTickets(skip + limit)} className="rounded-2xl border border-white/10 bg-white/10 text-white hover:bg-white/15">Next</Button>
              </div>
            </div>
          )}
        </GlassCard>

        <GlassCard className="min-h-[720px] rounded-3xl border border-white/10 p-5 hover:scale-100">
          {!selectedTicket ? (
            <div className="flex h-[640px] flex-col items-center justify-center text-center text-purple-100/70">
              <MessageCircle className="mb-4 h-14 w-14 text-purple-100/45" />
              <h2 className="text-xl font-semibold text-white">Select a ticket</h2>
              <p className="mt-2 max-w-md text-sm">Choose a ticket from the inbox to view user details, conversation, attachments, and workflow actions.</p>
            </div>
          ) : detailLoading ? (
            <div className="flex h-[640px] items-center justify-center text-purple-100/75">
              <Loader2 className="mr-3 h-6 w-6 animate-spin" /> Loading conversation...
            </div>
          ) : detailError ? (
            <div className="flex h-[640px] flex-col items-center justify-center text-center text-rose-100">
              <AlertCircle className="mb-3 h-10 w-10" />
              <p>{detailError}</p>
              <Button onClick={() => loadTicketDetail(selectedTicket.id)} className="mt-4 rounded-2xl bg-white/10 text-white hover:bg-white/15">Retry</Button>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="mb-3 flex flex-wrap gap-2">
                      <Pill className={statusClasses[selectedTicket.status] || statusClasses.open}>{labelize(selectedTicket.status)}</Pill>
                      <Pill className={priorityClasses[selectedTicket.priority] || priorityClasses.medium}>{labelize(selectedTicket.priority)}</Pill>
                      <Pill className="border-white/10 bg-white/10 text-purple-100">{labelize(selectedTicket.category)}</Pill>
                    </div>
                    <h2 className="text-2xl font-bold text-white">{selectedTicket.subject}</h2>
                    <p className="mt-2 max-w-3xl text-sm text-purple-100/70">{selectedTicket.message}</p>
                    <div className="mt-4 grid gap-2 text-sm text-purple-100/65 sm:grid-cols-2">
                      <span>User: {selectedTicket.user_name || selectedTicket.user_email || selectedTicket.user_id}</span>
                      <span>Created: {formatDate(selectedTicket.created_at)}</span>
                      <span>Last reply: {formatDate(selectedTicket.last_reply_at || selectedTicket.updated_at)}</span>
                      <span>Assigned: {selectedTicket.assigned_admin_name || selectedTicket.assigned_admin_email || selectedTicket.assigned_admin_id || "Unassigned"}</span>
                    </div>
                  </div>
                  <Button onClick={assignToMe} disabled={submitting} className="rounded-2xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white hover:opacity-95">
                    <ShieldCheck className="mr-2 h-4 w-4" /> Assign to me
                  </Button>
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-3">
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-purple-100/50">Status</p>
                    <FieldSelect value={selectedTicket.status} disabled={submitting} onChange={(value) => updateTicket({ status: value as SupportStatus })} className="w-full">
                      {statusOptions.filter((option) => option.value).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                    </FieldSelect>
                  </div>
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-purple-100/50">Priority</p>
                    <FieldSelect value={selectedTicket.priority} disabled={submitting} onChange={(value) => updateTicket({ priority: value as SupportPriority })} className="w-full">
                      {priorityOptions.filter((option) => option.value).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                    </FieldSelect>
                  </div>
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-purple-100/50">Category</p>
                    <FieldSelect value={selectedTicket.category} disabled={submitting} onChange={(value) => updateTicket({ category: value as SupportCategory })} className="w-full">
                      {categoryOptions.filter((option) => option.value).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                    </FieldSelect>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                  <MessageCircle className="h-5 w-5 text-fuchsia-200" /> Conversation
                </h3>
                <div className="max-h-[420px] space-y-4 overflow-y-auto pr-1">
                  {messages.length === 0 ? (
                    <p className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center text-sm text-purple-100/65">No messages yet.</p>
                  ) : (
                    messages.map((message) => {
                      const isAdmin = message.sender_role === "admin";
                      const isSystem = message.sender_role === "system";
                      return (
                        <div key={message.id} className={cx("flex", isAdmin ? "justify-end" : "justify-start")}>
                          <div className={cx("max-w-[82%] rounded-3xl border px-4 py-3", isAdmin ? "border-fuchsia-300/25 bg-fuchsia-500/15" : isSystem ? "border-amber-300/20 bg-amber-500/10" : "border-white/10 bg-white/8")}>
                            <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-purple-100/55">
                              <span className="font-semibold uppercase text-purple-100/80">{isAdmin ? "Admin" : isSystem ? "System" : selectedTicket.user_name || selectedTicket.user_email || "User"}</span>
                              <span>{formatDate(message.created_at)}</span>
                            </div>
                            <p className="whitespace-pre-wrap text-sm text-white">{message.message}</p>
                            <AttachmentList attachments={message.attachments} />
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                  <Send className="h-5 w-5 text-blue-200" /> Reply to user
                </h3>
                <Textarea value={reply} onChange={(event) => setReply(event.target.value)} placeholder="Write your admin reply..." className="min-h-[110px] rounded-2xl border-white/10 bg-white/10 text-white placeholder:text-purple-100/45" />
                {replyFiles.length > 0 && (
                  <div className="mt-3 space-y-2 rounded-2xl border border-white/10 bg-white/5 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-purple-100/50">Selected attachments</p>
                    {replyFiles.map((file, index) => (
                      <div key={`${file.name}-${index}`} className="flex items-center justify-between gap-3 rounded-xl bg-white/5 px-3 py-2 text-sm text-purple-100/85">
                        <span className="flex min-w-0 items-center gap-2"><FileText className="h-4 w-4 shrink-0" /><span className="truncate">{file.name}</span></span>
                        <button type="button" onClick={() => setReplyFiles((prev) => prev.filter((_, i) => i !== index))} className="rounded-full p-1 hover:bg-white/10"><X className="h-4 w-4" /></button>
                      </div>
                    ))}
                  </div>
                )}
                <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap gap-3">
                    <input ref={fileInputRef} type="file" multiple accept={allowedAccept} className="hidden" onChange={onFilesSelected} />
                    <Button type="button" onClick={() => fileInputRef.current?.click()} className="rounded-2xl border border-white/10 bg-white/10 text-white hover:bg-white/15">
                      <Paperclip className="mr-2 h-4 w-4" /> Attach
                    </Button>
                    <FieldSelect value={replyStatus} disabled={submitting} onChange={(value) => setReplyStatus(value as SupportStatus)}>
                      <option value="waiting_user">Waiting User</option>
                      <option value="in_progress">In Progress</option>
                      <option value="resolved">Resolved</option>
                      <option value="closed">Closed</option>
                    </FieldSelect>
                  </div>
                  <Button onClick={sendReply} disabled={submitting || (!reply.trim() && replyFiles.length === 0)} className="rounded-2xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white hover:opacity-95 disabled:opacity-60">
                    {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />} Send reply
                  </Button>
                </div>
              </div>
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
