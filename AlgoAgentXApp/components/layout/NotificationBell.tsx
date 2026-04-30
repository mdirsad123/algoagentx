"use client";

import { Bell, CheckCheck, CircleAlert, CircleCheck, Info, Loader2, Trash2, TriangleAlert } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { notificationApi } from "@/lib/api/notifications";
import type { NotificationResponse } from "@/types/notifications";

function timeAgo(value: string) {
  const diff = Date.now() - new Date(value).getTime();
  if (Number.isNaN(diff)) return "Just now";
  const min = Math.max(1, Math.floor(diff / 60000));
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

function iconFor(severity?: string) {
  const cls = "h-4 w-4";
  if (severity === "success") return <CircleCheck className={`${cls} text-emerald-300`} />;
  if (severity === "warning") return <TriangleAlert className={`${cls} text-amber-300`} />;
  if (severity === "error") return <CircleAlert className={`${cls} text-rose-300`} />;
  return <Info className={`${cls} text-sky-300`} />;
}

export default function NotificationBell() {
  const router = useRouter();
  const pathname = usePathname();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [items, setItems] = useState<NotificationResponse[]>([]);

  const isAdmin = pathname.startsWith("/admin");
  const pageHref = isAdmin ? "/admin/notifications" : "/notifications";

  const fetchUnread = async () => {
    try {
      const data = await notificationApi.getUnreadCount();
      setUnreadCount(data.unread_count || 0);
    } catch {}
  };

  const fetchItems = async () => {
    setLoading(true);
    try {
      const data = await notificationApi.getNotifications(0, 10, false);
      setItems(data || []);
      await fetchUnread();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnread();
    const id = window.setInterval(fetchUnread, 45000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => { if (open) fetchItems(); }, [open]);
  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const markOne = async (notification: NotificationResponse) => {
    if (!notification.is_read) {
      setItems((prev) => prev.map((item) => item.id === notification.id ? { ...item, is_read: true } : item));
      setUnreadCount((prev) => Math.max(0, prev - 1));
      try { await notificationApi.markOneRead(notification.id); } catch { await fetchItems(); }
    }
  };

  const markAll = async () => {
    setItems((prev) => prev.map((item) => ({ ...item, is_read: true })));
    setUnreadCount(0);
    try { await notificationApi.markAllRead(); } catch { await fetchItems(); }
  };

  const remove = async (notificationId: string) => {
    const item = items.find((x) => x.id === notificationId);
    setItems((prev) => prev.filter((x) => x.id !== notificationId));
    if (item && !item.is_read) setUnreadCount((prev) => Math.max(0, prev - 1));
    try { await notificationApi.deleteNotification(notificationId); } catch { await fetchItems(); }
  };

  return (
    <div className="relative" ref={rootRef}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        className="relative h-11 w-11 rounded-2xl border border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -right-3 -top-3 z-[2147483647] flex h-8 min-w-8 items-center justify-center rounded-full border-2 border-[#24103d] px-2.5 text-[14px] font-black leading-none text-white shadow-[0_0_18px_rgba(255,45,111,0.85)]"
            style={{ backgroundColor: "#ff2d6f" }}>
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 top-14 z-[2147483647] w-[420px] max-w-[calc(100vw-24px)] overflow-hidden rounded-3xl border border-fuchsia-300/35 shadow-[0_30px_90px_rgba(0,0,0,1)] ring-1 ring-white/15"
          style={{ backgroundColor: "#0b0314", opacity: 1, isolation: "isolate", backdropFilter: "none" }}>
          <div className="flex items-center justify-between border-b border-fuchsia-300/20 p-5"
            style={{ backgroundColor: "#0b0314" }}>
            <div>
              <div className="text-base font-bold text-white">Notifications</div>
              <div className="text-xs text-purple-100/60">Latest account and trading updates</div>
            </div>
            <button onClick={markAll} className="flex items-center gap-1 rounded-xl border border-fuchsia-300/20 bg-[#211034] px-3 py-2 text-xs font-semibold text-purple-100 hover:bg-[#2a0d3f]">
              <CheckCheck className="h-3.5 w-3.5" /> Mark all
            </button>
          </div>

          <div className="max-h-[520px] space-y-3 overflow-y-auto overflow-x-hidden p-3"
            style={{ backgroundColor: "#0b0314" }}>
            {loading ? (
              <div className="flex items-center justify-center gap-2 p-10 text-sm text-purple-100/70"><Loader2 className="h-4 w-4 animate-spin" /> Loading</div>
            ) : items.length === 0 ? (
              <div className="p-10 text-center text-sm text-purple-100/70">No notifications yet.</div>
            ) : items.map((item) => (
              <div key={item.id} className={`group w-full overflow-hidden rounded-2xl border p-4 transition ${item.is_read ? "border-white/10 shadow-md shadow-black/30" : "border-fuchsia-400/45 shadow-lg shadow-black/50"}`}
                style={{ backgroundColor: item.is_read ? "#140a22" : "#2b0b45" }}>
                <button onClick={() => markOne(item)} className="flex w-full gap-3 text-left">
                  <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#3a1858]">{iconFor(item.severity)}</div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-bold leading-5 text-white">{item.title}</p>
                      <span className="shrink-0 rounded-full bg-[#3a1858] px-2 py-1 text-[11px] text-purple-100/70">{timeAgo(item.created_at)}</span>
                    </div>
                    <p className="mt-1.5 line-clamp-3 text-xs leading-5 text-purple-100/75">{item.message}</p>
                    {!item.is_read && <span className="mt-2 inline-flex rounded-full bg-fuchsia-500/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-fuchsia-100">Unread</span>}
                  </div>
                </button>
                <div className="mt-3 flex justify-end gap-1 opacity-100 transition md:opacity-0 md:group-hover:opacity-100">
                  {!item.is_read && <button onClick={() => markOne(item)} className="rounded-lg px-2 py-1 text-[11px] text-purple-100 hover:bg-white/10">Mark read</button>}
                  <button onClick={() => remove(item.id)} className="rounded-lg p-1.5 text-rose-200 hover:bg-rose-500/10" title="Delete"><Trash2 className="h-3.5 w-3.5" /></button>
                </div>
              </div>
            ))}
          </div>

          <button onClick={() => { setOpen(false); router.push(pageHref); }} className="w-full border-t border-fuchsia-300/20 px-4 py-4 text-sm font-bold text-purple-100 hover:brightness-110"
            style={{ backgroundColor: "#0b0314" }}>
            View all notifications
          </button>
        </div>
      )}
    </div>
  );
}
