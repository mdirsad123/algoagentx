"use client";

import { Bell, CheckCheck, CircleAlert, CircleCheck, Info, Loader2, RefreshCw, Trash2, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { notificationApi } from "@/lib/api/notifications";
import type { NotificationResponse } from "@/types/notifications";

function timeLabel(value: string) {
  try { return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); } catch { return value; }
}

function iconFor(severity?: string) {
  const cls = "h-5 w-5";
  if (severity === "success") return <CircleCheck className={`${cls} text-emerald-300`} />;
  if (severity === "warning") return <TriangleAlert className={`${cls} text-amber-300`} />;
  if (severity === "error") return <CircleAlert className={`${cls} text-rose-300`} />;
  return <Info className={`${cls} text-sky-300`} />;
}

export default function NotificationsClient({ admin = false }: { admin?: boolean }) {
  const [items, setItems] = useState<NotificationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const unreadCount = useMemo(() => items.filter((item) => !item.is_read).length, [items]);

  const load = async () => {
    setLoading(true);
    try {
      const data = await notificationApi.getNotifications(0, 50, unreadOnly);
      setItems(data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [unreadOnly]);

  const markOne = async (item: NotificationResponse) => {
    if (!item.is_read) {
      setItems((prev) => prev.map((x) => x.id === item.id ? { ...x, is_read: true } : x));
      try { await notificationApi.markOneRead(item.id); } catch { await load(); }
    }
  };

  const markAll = async () => {
    setItems((prev) => prev.map((x) => ({ ...x, is_read: true })));
    try { await notificationApi.markAllRead(); } catch { await load(); }
  };

  const remove = async (id: string) => {
    setItems((prev) => prev.filter((x) => x.id !== id));
    try { await notificationApi.deleteNotification(id); } catch { await load(); }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-[#4c168c] via-[#35166f] to-[#15204a] px-6 py-8 text-white">
      <section className="mb-8 rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl shadow-purple-950/30 backdrop-blur-xl">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-fuchsia-500 to-blue-500 shadow-lg"><Bell className="h-6 w-6" /></div>
              <div>
                <h2 className="text-3xl font-bold">{admin ? "Admin Notifications" : "Notifications"}</h2>
                <p className="text-sm text-purple-100/70">Track support, trading, billing, and system activity.</p>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-fuchsia-400/30 bg-fuchsia-500/10 px-3 py-1 text-sm text-fuchsia-100">{unreadCount} unread</span>
            <Button onClick={() => setUnreadOnly((v) => !v)} className="rounded-xl bg-white/10 text-white hover:bg-white/15">
              {unreadOnly ? "Show all" : "Unread only"}
            </Button>
            <Button onClick={markAll} className="gap-2 rounded-xl bg-white/10 text-white hover:bg-white/15"><CheckCheck className="h-4 w-4" /> Mark all read</Button>
            <Button onClick={load} className="gap-2 rounded-xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white"><RefreshCw className="h-4 w-4" /> Refresh</Button>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="flex items-center justify-center gap-2 rounded-3xl border border-white/10 bg-white/5 p-12 text-purple-100"><Loader2 className="h-5 w-5 animate-spin" /> Loading notifications</div>
      ) : items.length === 0 ? (
        <div className="rounded-3xl border border-white/10 bg-white/5 p-12 text-center text-purple-100/75">No notifications found.</div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <article key={item.id} className={`rounded-2xl border p-4 shadow-xl backdrop-blur-xl ${item.is_read ? "border-white/10 bg-white/[0.04]" : "border-fuchsia-400/30 bg-fuchsia-500/10"}`}>
              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10">{iconFor(item.severity)}</div>
                <button onClick={() => markOne(item)} className="min-w-0 flex-1 text-left">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-white">{item.title}</h3>
                    {!item.is_read && <span className="rounded-full bg-fuchsia-500 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide">New</span>}
                    <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-purple-100/60">{item.type}</span>
                  </div>
                  <p className="mt-1 text-sm leading-6 text-purple-100/75">{item.message}</p>
                  <p className="mt-2 text-xs text-purple-100/50">{timeLabel(item.created_at)}</p>
                </button>
                <div className="flex shrink-0 items-center gap-2">
                  {!item.is_read && <Button onClick={() => markOne(item)} className="rounded-xl bg-white/10 text-white hover:bg-white/15">Mark read</Button>}
                  <Button onClick={() => remove(item.id)} className="rounded-xl bg-rose-500/10 text-rose-100 hover:bg-rose-500/20"><Trash2 className="h-4 w-4" /></Button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
