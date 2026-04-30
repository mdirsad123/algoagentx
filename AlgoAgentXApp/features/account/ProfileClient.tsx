"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, BadgeCheck, CalendarDays, CreditCard, KeyRound, Mail, Phone, RefreshCw, ShieldCheck, User2, WalletCards } from "lucide-react";
import { toast } from "sonner";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Profile, profileSettingsApi } from "@/lib/api/profile-settings";

function formatDate(value?: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function initials(name?: string | null, email?: string | null) {
  const source = (name || email || "U").trim();
  const parts = source.includes("@") ? [source[0]] : source.split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase()).join("") || "U";
}

function syncLocalProfile(profile: Profile) {
  if (typeof window === "undefined") return;
  const name = profile.full_name || profile.fullname || "";
  localStorage.setItem("currentUser", JSON.stringify({ ...profile, full_name: name, fullname: name }));
  document.cookie = `loggedinuserfullname=${encodeURIComponent(name)}; path=/; max-age=86400; samesite=strict`;
  document.cookie = `loggedinuseremail=${encodeURIComponent(profile.email || "")}; path=/; max-age=86400; samesite=strict`;
  document.cookie = `loggedinuserrole=${encodeURIComponent(profile.role || "user")}; path=/; max-age=86400; samesite=strict`;
  window.dispatchEvent(new Event("storage"));
}

function StatCard({ icon: Icon, label, value }: { icon: any; label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-4 shadow-lg shadow-purple-950/20">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-fuchsia-200">
        <Icon className="h-5 w-5" />
      </div>
      <div className="text-2xl font-semibold text-white">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-purple-100/60">{label}</div>
    </div>
  );
}

export default function ProfileClient({ admin = false }: { admin?: boolean }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState({ full_name: "", mobile: "", company: "" });

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await profileSettingsApi.getProfile();
      const name = data.full_name || data.fullname || "";
      setProfile({ ...data, full_name: name, fullname: name });
      setForm({ full_name: name, mobile: data.mobile || "", company: data.company || "" });
      syncLocalProfile({ ...data, full_name: name, fullname: name });
    } catch (error: any) {
      toast.error(error?.message || "Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadProfile(); }, []);

  const saveProfile = async () => {
    if (!form.full_name.trim()) {
      toast.error("Full name is required");
      return;
    }
    try {
      setSaving(true);
      const updated = await profileSettingsApi.updateProfile({ full_name: form.full_name.trim(), mobile: form.mobile.trim() || undefined, company: form.company.trim() || undefined });
      const name = updated.full_name || updated.fullname || "";
      setProfile({ ...updated, full_name: name, fullname: name });
      syncLocalProfile({ ...updated, full_name: name, fullname: name });
      toast.success("Profile updated successfully");
    } catch (error: any) {
      toast.error(error?.message || "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const displayName = profile?.full_name || profile?.fullname || profile?.email?.split("@")[0] || (admin ? "Admin" : "User");
  const stats = profile?.stats;
  const role = String(profile?.role || (admin ? "admin" : "user")).toLowerCase();
  const isAdminProfile = admin || role === "admin";

  const activityCards = useMemo(() => isAdminProfile ? [
    { icon: ShieldCheck, label: "Console access", value: "Enabled" },
    { icon: BadgeCheck, label: "Role", value: "Admin" },
    { icon: Activity, label: "Admin actions", value: "Audit safe" },
    { icon: KeyRound, label: "Security", value: "Protected" },
  ] : [
    { icon: Activity, label: "Total backtests", value: stats?.total_backtests ?? 0 },
    { icon: ShieldCheck, label: "Connected brokers", value: stats?.connected_brokers ?? 0 },
    { icon: CreditCard, label: "Subscription", value: stats?.active_subscription || "None" },
    { icon: WalletCards, label: "Credits", value: stats?.credit_balance ?? 0 },
  ], [isAdminProfile, stats]);

  return (
    <div className="space-y-6">
      <PageHeader title={isAdminProfile ? "Admin Profile" : "My Profile"} subtitle={isAdminProfile ? "Manage your admin console identity and security summary." : "Manage your personal details and trading workspace identity."} />

      {loading ? (
        <GlassCard className="rounded-3xl border border-white/10 p-8"><div className="h-28 animate-pulse rounded-2xl bg-white/10" /></GlassCard>
      ) : (
        <>
          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
              <div className="mb-6 flex flex-wrap items-center gap-4">
                <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-fuchsia-500 via-violet-500 to-blue-500 text-2xl font-bold text-white shadow-2xl shadow-fuchsia-900/40">
                  {initials(displayName, profile?.email)}
                </div>
                <div className="min-w-0 flex-1">
                  <h2 className="truncate text-2xl font-semibold text-white">{displayName}</h2>
                  <p className="text-sm text-purple-100/75">{isAdminProfile ? "Administrator workspace profile" : "Trading workspace profile"}</p>
                </div>
                <span className="rounded-full border border-emerald-300/20 bg-emerald-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-200">
                  {profile?.account_status || "active"}
                </span>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2"><Label className="text-purple-100/80">Full name</Label><Input value={form.full_name} onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))} placeholder="Enter full name" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40" /></div>
                <div className="space-y-2"><Label className="text-purple-100/80">Email</Label><Input value={profile?.email || ""} disabled className="border-white/10 bg-white/5 text-purple-100/70" /></div>
                <div className="space-y-2"><Label className="text-purple-100/80">Mobile</Label><Input value={form.mobile} onChange={(e) => setForm((p) => ({ ...p, mobile: e.target.value }))} placeholder="Optional mobile" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40" /></div>
                <div className="space-y-2"><Label className="text-purple-100/80">Company</Label><Input value={form.company} onChange={(e) => setForm((p) => ({ ...p, company: e.target.value }))} placeholder="Optional company" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40" /></div>
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                <Button onClick={saveProfile} disabled={saving} className="rounded-xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white shadow-lg shadow-fuchsia-950/30 hover:opacity-95">{saving ? "Saving..." : "Save changes"}</Button>
                <Button variant="outline" onClick={loadProfile} className="rounded-xl border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
              </div>
            </GlassCard>

            <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
              <h3 className="mb-4 text-lg font-semibold text-white">Security summary</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-purple-100/85"><Mail className="h-4 w-4 text-fuchsia-300" />{profile?.email || "Not available"}</div>
                <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-purple-100/85"><ShieldCheck className="h-4 w-4 text-blue-300" />Role: {role}</div>
                <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-purple-100/85"><CalendarDays className="h-4 w-4 text-emerald-300" />Joined: {formatDate(profile?.created_at)}</div>
                <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-purple-100/85"><Phone className="h-4 w-4 text-cyan-300" />Last login: {formatDate(profile?.last_login_at)}</div>
              </div>
              <Button onClick={() => window.location.assign(isAdminProfile ? "/admin/settings" : "/settings")} className="mt-5 w-full rounded-xl bg-white/10 text-white hover:bg-white/15"><KeyRound className="mr-2 h-4 w-4" />Change password in Settings</Button>
            </GlassCard>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {activityCards.map((item) => <StatCard key={item.label} icon={item.icon} label={item.label} value={item.value} />)}
          </div>
        </>
      )}
    </div>
  );
}
