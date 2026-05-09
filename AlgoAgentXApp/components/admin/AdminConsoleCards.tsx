import React from "react";
import { cn } from "@/lib/utils";

export function AdminSectionCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-2xl border border-white/10 bg-white/[0.045] p-4 shadow-xl shadow-purple-950/20 backdrop-blur-xl sm:p-5", className)}>
      {children}
    </section>
  );
}

export function AdminMetricCard({ label, value, helper, className = "" }: { label: string; value: React.ReactNode; helper?: React.ReactNode; className?: string }) {
  return (
    <AdminSectionCard className={cn("min-h-[118px]", className)}>
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-purple-100/65">{label}</p>
      <div className="mt-2 text-2xl font-black text-white sm:text-3xl">{value}</div>
      {helper ? <div className="mt-2 text-xs font-medium text-purple-100/60">{helper}</div> : null}
    </AdminSectionCard>
  );
}

export function AdminStatusBadge({ value, className = "" }: { value?: string | boolean | null; className?: string }) {
  const raw = String(value ?? "UNKNOWN");
  const key = raw.toLowerCase();
  const tone = key.includes("active") || key.includes("paid") || key.includes("approved") || key.includes("success") || key === "true"
    ? "border-emerald-300/25 bg-emerald-500/15 text-emerald-200"
    : key.includes("pending") || key.includes("trial") || key.includes("draft")
      ? "border-amber-300/25 bg-amber-500/15 text-amber-100"
      : key.includes("fail") || key.includes("reject") || key.includes("inactive") || key.includes("cancel") || key === "false"
        ? "border-rose-300/25 bg-rose-500/15 text-rose-100"
        : "border-white/10 bg-white/10 text-purple-100";
  return <span className={cn("inline-flex rounded-full border px-2.5 py-1 text-xs font-bold uppercase tracking-wide", tone, className)}>{raw}</span>;
}
