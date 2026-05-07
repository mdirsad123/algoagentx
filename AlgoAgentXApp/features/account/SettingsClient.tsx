"use client";

import { useEffect, useMemo, useState } from "react";
import { BellRing, Eye, EyeOff, KeyRound, Mail, Save, ShieldAlert, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { toast } from "sonner";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { profileSettingsApi, AccountSettings, Profile } from "@/lib/api/profile-settings";
import CouponBarSettingsCard from "@/components/admin/CouponBarSettingsCard";
import BillingSettingsCard from "@/components/admin/BillingSettingsCard";

const notificationLabels: Record<string, string> = {
  support_replies: "Support replies",
  trade_order_updates: "Trade / order updates",
  live_approval_requests: "Live approval requests",
  broker_connection_alerts: "Broker connection alerts",
  billing_payment_updates: "Billing / payment updates",
  strategy_request_updates: "Strategy request updates",
};

const emailTypeLabels: Record<string, string> = {
  support_replies: "Support reply emails",
  ticket_status_updates: "Ticket status update emails",
  login_alerts: "Login security alerts",
  trade_order_updates: "Trading / order update emails",
  live_approval_requests: "Live approval request emails",
  broker_alerts: "Broker alert emails",
  billing_payment_updates: "Billing / payment emails",
  subscription_updates: "Subscription update emails",
  credit_updates: "Credit update emails",
  strategy_request_updates: "Strategy request emails",
  backtest_updates: "Backtest result emails",
};

const adminEmailTypeLabels: Record<string, string> = {
  support_new_ticket_admin: "New support ticket emails",
  user_support_replies_admin: "User support reply emails",
  new_strategy_request_admin: "New strategy request emails",
  failed_payment_refund_admin: "Failed payment / refund emails",
  failed_order_admin: "Failed order emails",
  admin_login_alerts: "Admin login alerts",
  system_critical_alerts_admin: "System critical alerts",
  broker_alerts: "Broker failure emails",
};

const safetyLabels: Record<string, string> = {
  require_live_approval_before_execution: "Require live approval before execution",
  live_sync_warning_enabled: "Live sync warning enabled",
  default_order_confirmation_required: "Default order confirmation required",
};

const adminAlertLabels: Record<string, string> = {
  new_support_ticket: "New support ticket",
  new_strategy_request: "New strategy request",
  failed_payment: "Failed payment",
  failed_order: "Failed order",
  broker_connection_issue: "Broker connection issue",
};

const defaultEmailTypes = {
  support_replies: true,
  support_new_ticket_admin: true,
  ticket_status_updates: true,
  login_alerts: false,
  admin_login_alerts: true,
  trade_order_updates: true,
  live_approval_requests: true,
  broker_alerts: true,
  billing_payment_updates: true,
  subscription_updates: true,
  credit_updates: true,
  strategy_request_updates: true,
  backtest_updates: false,
  user_support_replies_admin: true,
  new_strategy_request_admin: true,
  failed_payment_refund_admin: true,
  failed_order_admin: true,
  system_critical_alerts_admin: true,
};

const defaultSettings: AccountSettings = {
  preferences: { default_broker: "", default_strategy: "", default_timeframe: "15m", default_risk_mode: "balanced" },
  notifications: {
    ...Object.fromEntries(Object.keys(notificationLabels).map((key) => [key, true])),
    email_notifications_enabled: true,
    email_notification_types: defaultEmailTypes,
  },
  safety: Object.fromEntries(Object.keys(safetyLabels).map((key) => [key, true])),
  admin_alerts: Object.fromEntries(Object.keys(adminAlertLabels).map((key) => [key, true])),
};

function ToggleRow({ label, checked, onChange, description }: { label: string; checked: boolean; onChange: (value: boolean) => void; description?: string }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/[0.06] p-4 text-sm text-purple-100/85 transition hover:bg-white/10">
      <span><span className="block font-medium text-white/90">{label}</span>{description && <span className="mt-0.5 block text-xs text-purple-100/55">{description}</span>}</span>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="h-5 w-5 shrink-0 accent-fuchsia-500" />
    </label>
  );
}

export default function SettingsClient({ admin = false }: { admin?: boolean }) {
  const [loading, setLoading] = useState(true);
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [settings, setSettings] = useState<AccountSettings>(defaultSettings);
  const [password, setPassword] = useState({ current_password: "", new_password: "", confirm_password: "" });

  const isAdmin = useMemo(() => admin || String(profile?.role || "").toLowerCase() === "admin", [admin, profile]);

  const normalizeSettings = (settingsData: AccountSettings) => ({
    preferences: { ...defaultSettings.preferences, ...(settingsData.preferences || {}) },
    notifications: {
      ...defaultSettings.notifications,
      ...(settingsData.notifications || {}),
      email_notification_types: {
        ...defaultEmailTypes,
        ...((settingsData.notifications || {}).email_notification_types || {}),
      },
    },
    safety: { ...defaultSettings.safety, ...(settingsData.safety || {}) },
    admin_alerts: { ...defaultSettings.admin_alerts, ...(settingsData.admin_alerts || {}) },
  });

  const load = async () => {
    try {
      setLoading(true);
      const [profileData, settingsData] = await Promise.all([profileSettingsApi.getProfile(), profileSettingsApi.getSettings()]);
      setProfile(profileData);
      setSettings(normalizeSettings(settingsData));
    } catch (error: any) {
      toast.error(error?.message || "Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const updatePreference = (key: string, value: any) => setSettings((prev) => ({ ...prev, preferences: { ...prev.preferences, [key]: value } }));
  const updateToggle = (section: "notifications" | "safety" | "admin_alerts", key: string, value: boolean) => setSettings((prev) => ({ ...prev, [section]: { ...prev[section], [key]: value } }));
  const updateEmailToggle = (key: string, value: boolean) => setSettings((prev) => ({
    ...prev,
    notifications: {
      ...prev.notifications,
      email_notification_types: { ...(prev.notifications.email_notification_types || {}), [key]: value },
    },
  }));

  const saveSettings = async () => {
    try {
      setSavingPreferences(true);
      const body = isAdmin ? settings : { preferences: settings.preferences, notifications: settings.notifications, safety: settings.safety };
      const updated = await profileSettingsApi.updateSettings(body);
      setSettings(normalizeSettings(updated));
      toast.success("Settings saved successfully");
    } catch (error: any) {
      toast.error(error?.message || "Failed to save settings");
    } finally {
      setSavingPreferences(false);
    }
  };

  const changePassword = async () => {
    if (!password.current_password) return toast.error("Current password is required");
    if (password.new_password.length < 8) return toast.error("New password must be at least 8 characters");
    if (password.new_password !== password.confirm_password) return toast.error("Confirm password does not match");
    try {
      setSavingPassword(true);
      await profileSettingsApi.changePassword({ current_password: password.current_password, new_password: password.new_password });
      setPassword({ current_password: "", new_password: "", confirm_password: "" });
      toast.success("Password updated successfully");
    } catch (error: any) {
      toast.error(error?.message || "Failed to update password");
    } finally {
      setSavingPassword(false);
    }
  };

  const passwordType = showPassword ? "text" : "password";
  const emailLabels = isAdmin ? adminEmailTypeLabels : emailTypeLabels;

  return (
    <div className="space-y-6">
      <PageHeader title={isAdmin ? "Admin Settings" : "Settings"} subtitle={isAdmin ? "Security, in-app notifications, email alerts, and console alert preferences." : "Manage security, preferences, in-app notifications, email alerts, and trading safety."} />

      {loading ? (
        <GlassCard className="rounded-3xl border border-white/10 p-8"><div className="h-40 animate-pulse rounded-2xl bg-white/10" /></GlassCard>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-6">
            {isAdmin && <CouponBarSettingsCard />}
            {isAdmin && <BillingSettingsCard />}

            <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
              <div className="mb-5 flex items-center justify-between">
                <div><h3 className="flex items-center gap-2 text-lg font-semibold text-white"><KeyRound className="h-5 w-5 text-fuchsia-300" />Security</h3><p className="mt-1 text-sm text-purple-100/65">Change password safely with current password verification.</p></div>
                <Button type="button" variant="outline" onClick={() => setShowPassword((v) => !v)} className="rounded-xl border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</Button>
              </div>
              <div className="space-y-4">
                <div className="space-y-2"><Label className="text-purple-100/80">Current password</Label><Input type={passwordType} value={password.current_password} onChange={(e) => setPassword((p) => ({ ...p, current_password: e.target.value }))} placeholder="Current password" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40" /></div>
                <div className="space-y-2"><Label className="text-purple-100/80">New password</Label><Input type={passwordType} value={password.new_password} onChange={(e) => setPassword((p) => ({ ...p, new_password: e.target.value }))} placeholder="At least 8 characters" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40" /></div>
                <div className="space-y-2"><Label className="text-purple-100/80">Confirm new password</Label><Input type={passwordType} value={password.confirm_password} onChange={(e) => setPassword((p) => ({ ...p, confirm_password: e.target.value }))} placeholder="Confirm new password" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40" /></div>
                <Button onClick={changePassword} disabled={savingPassword} className="w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white shadow-lg shadow-fuchsia-950/30">{savingPassword ? "Updating..." : "Update password"}</Button>
              </div>
            </GlassCard>

            <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
              <h3 className="flex items-center gap-2 text-lg font-semibold text-white"><SlidersHorizontal className="h-5 w-5 text-blue-300" />Preferences</h3>
              <div className="mt-5 grid gap-4">
                <div className="space-y-2"><Label className="text-purple-100/80">Default broker</Label><Input value={settings.preferences.default_broker || ""} onChange={(e) => updatePreference("default_broker", e.target.value)} placeholder="e.g., Upstox / MT5" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40" /></div>
                <div className="space-y-2"><Label className="text-purple-100/80">Default strategy</Label><Input value={settings.preferences.default_strategy || ""} onChange={(e) => updatePreference("default_strategy", e.target.value)} placeholder="e.g., EMA-9-20" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40" /></div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2"><Label className="text-purple-100/80">Default timeframe</Label><Input value={settings.preferences.default_timeframe || ""} onChange={(e) => updatePreference("default_timeframe", e.target.value)} placeholder="15m / 1h / 1d" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40" /></div>
                  <div className="space-y-2"><Label className="text-purple-100/80">Default risk mode</Label><Input value={settings.preferences.default_risk_mode || ""} onChange={(e) => updatePreference("default_risk_mode", e.target.value)} placeholder="safe / balanced / aggressive" className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40" /></div>
                </div>
              </div>
            </GlassCard>
          </div>

          <div className="space-y-6">
            <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
              <h3 className="flex items-center gap-2 text-lg font-semibold text-white"><BellRing className="h-5 w-5 text-fuchsia-300" />In-app notification preferences</h3>
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                {Object.entries(notificationLabels).map(([key, label]) => <ToggleRow key={key} label={label} checked={!!settings.notifications[key]} onChange={(v) => updateToggle("notifications", key, v)} />)}
              </div>
            </GlassCard>

            <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <h3 className="flex items-center gap-2 text-lg font-semibold text-white"><Mail className="h-5 w-5 text-blue-300" />Email Notifications</h3>
                  <p className="mt-1 text-sm text-purple-100/65">SMTP must be configured in backend .env. Emails are optional and in-app notifications still work when disabled.</p>
                </div>
                <div className="min-w-[220px]"><ToggleRow label="Enable email notifications" checked={settings.notifications.email_notifications_enabled !== false} onChange={(v) => updateToggle("notifications", "email_notifications_enabled", v)} /></div>
              </div>
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                {Object.entries(emailLabels).map(([key, label]) => <ToggleRow key={key} label={label} checked={!!(settings.notifications.email_notification_types || {})[key]} onChange={(v) => updateEmailToggle(key, v)} />)}
              </div>
            </GlassCard>

            {!isAdmin && (
              <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
                <h3 className="flex items-center gap-2 text-lg font-semibold text-white"><ShieldCheck className="h-5 w-5 text-emerald-300" />Trading safety preferences</h3>
                <div className="mt-5 grid gap-3">
                  {Object.entries(safetyLabels).map(([key, label]) => <ToggleRow key={key} label={label} checked={!!settings.safety[key]} onChange={(v) => updateToggle("safety", key, v)} />)}
                </div>
                <button onClick={() => window.location.assign("/live-trading")} className="mt-4 text-sm font-medium text-fuchsia-200 hover:text-white">Open advanced live trading controls →</button>
              </GlassCard>
            )}

            {isAdmin && (
              <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
                <h3 className="flex items-center gap-2 text-lg font-semibold text-white"><ShieldAlert className="h-5 w-5 text-amber-300" />Admin alert preferences</h3>
                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  {Object.entries(adminAlertLabels).map(([key, label]) => <ToggleRow key={key} label={label} checked={!!settings.admin_alerts[key]} onChange={(v) => updateToggle("admin_alerts", key, v)} />)}
                </div>
              </GlassCard>
            )}

            <Button onClick={saveSettings} disabled={savingPreferences} className="w-full rounded-2xl bg-gradient-to-r from-fuchsia-500 to-blue-500 py-6 text-white shadow-xl shadow-fuchsia-950/30"><Save className="mr-2 h-5 w-5" />{savingPreferences ? "Saving settings..." : "Save all preferences"}</Button>
          </div>
        </div>
      )}
    </div>
  );
}
