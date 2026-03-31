"use client";

import { useEffect, useMemo, useState } from "react";
import { CalendarDays, Mail, Shield, Sparkles, User2 } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { userApi } from "@/lib/api/users";
import axiosInstance from "@/lib/axios";
import { toast } from "sonner";

export default function ProfilePage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState({ id: "", email: "", role: "user", full_name: "", created_at: "" });
  const [fullName, setFullName] = useState("");

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await userApi.getCurrentUser();
      const nextProfile = { id: data.id as any, email: data.email, role: data.role, full_name: (data as any).full_name || (data as any).fullname || "", created_at: (data as any).created_at || "" };
      setProfile(nextProfile);
      setFullName(nextProfile.full_name || "");
      localStorage.setItem("currentUser", JSON.stringify(nextProfile));
      document.cookie = `loggedinuserfullname=${encodeURIComponent(nextProfile.full_name || "")}; path=/; max-age=86400; samesite=strict`;
      document.cookie = `loggedinuseremail=${encodeURIComponent(nextProfile.email || "")}; path=/; max-age=86400; samesite=strict`;
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to load profile");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { loadProfile(); }, []);

  const saveProfile = async () => {
    try {
      setSaving(true);
      await axiosInstance.patch("/api/v1/users/me", { full_name: fullName });
      toast.success("Profile updated");
      await loadProfile();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const joined = useMemo(() => profile.created_at ? new Date(profile.created_at).toLocaleDateString() : "-", [profile.created_at]);
  return (<div className="space-y-6"><PageHeader title="My Profile" subtitle="Manage your personal details and keep your workspace identity up to date." /><div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]"><GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100"><div className="mb-6 flex items-center gap-4"><div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-fuchsia-500 to-blue-500 text-white shadow-2xl shadow-fuchsia-900/40"><User2 className="h-9 w-9" /></div><div><h2 className="text-2xl font-semibold text-white">{profile.full_name || profile.email || "User"}</h2><p className="text-sm text-purple-100/75">Your trading workspace profile</p></div></div><div className="grid gap-4 md:grid-cols-2"><div className="space-y-2"><label className="text-sm text-purple-100/80">Full name</label><Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Enter your full name" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/45" disabled={loading} /></div><div className="space-y-2"><label className="text-sm text-purple-100/80">Email</label><Input value={profile.email} disabled className="border-white/10 bg-white/5 text-purple-100/75" /></div></div><div className="mt-5 flex flex-wrap gap-3"><Button onClick={saveProfile} disabled={saving || loading} className="rounded-xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white hover:opacity-95">{saving ? "Saving..." : "Save changes"}</Button><Button variant="outline" onClick={loadProfile} className="rounded-xl border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">Refresh</Button></div></GlassCard><div className="space-y-6"><GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100"><h3 className="mb-4 text-lg font-semibold text-white">Account summary</h3><div className="space-y-3"><div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-purple-100/85"><Mail className="h-4 w-4 text-fuchsia-300" /> {profile.email || "-"}</div><div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-purple-100/85"><Shield className="h-4 w-4 text-blue-300" /> Role: {profile.role}</div><div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-purple-100/85"><CalendarDays className="h-4 w-4 text-emerald-300" /> Joined: {joined}</div></div></GlassCard><GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100"><div className="mb-3 flex items-center gap-2 text-white"><Sparkles className="h-4 w-4 text-fuchsia-300" /> Profile tips</div><ul className="space-y-2 text-sm text-purple-100/75"><li>• Keep your name updated so support and billing teams can identify you quickly.</li><li>• Use Support Tickets for AI help, billing questions, and technical issues.</li><li>• Review Settings for security and password actions.</li></ul></GlassCard></div></div></div>);
}
