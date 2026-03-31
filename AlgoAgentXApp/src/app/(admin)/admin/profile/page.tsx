"use client";

import { ShieldCheck, Mail, User2, BadgeCheck } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";

function getCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

export default function AdminProfilePage() {
  const name = getCookie("loggedinuserfullname") || getCookie("loggedinusername")?.split("@")[0] || "Admin User";
  const email = getCookie("loggedinuseremail") || getCookie("loggedinusername") || "admin@algoagentx.com";
  return (<div className="space-y-6"><PageHeader title="Admin Profile" subtitle="Console identity, admin access details, and support ownership overview." /><div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]"><GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100"><div className="mb-6 flex items-center gap-4"><div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-fuchsia-500 to-blue-500 text-white shadow-2xl shadow-fuchsia-900/40"><User2 className="h-9 w-9" /></div><div><h2 className="text-2xl font-semibold text-white">{name}</h2><p className="text-sm text-purple-100/75">Administrator account</p></div></div><div className="grid gap-4"><div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-purple-100/85"><Mail className="h-4 w-4 text-fuchsia-300" /> {email}</div><div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-purple-100/85"><ShieldCheck className="h-4 w-4 text-emerald-300" /> Full admin control enabled for users, payments, credits, orders, and support.</div><div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-purple-100/85"><BadgeCheck className="h-4 w-4 text-blue-300" /> Use Support Tickets to manage both user conversations and escalation flows.</div></div></GlassCard><GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100"><h3 className="mb-4 text-lg font-semibold text-white">Console guidance</h3><ul className="space-y-2 text-sm text-purple-100/75"><li>• Use Users to manage plan, activation, and access details.</li><li>• Use Support Tickets to answer Ask AI, billing, and technical requests.</li><li>• Use Credits and Payments together when resolving subscription disputes.</li></ul></GlassCard></div></div>);
}
