"use client";

import { useEffect, useState } from "react";
import { CreditCard, Save } from "lucide-react";
import { toast } from "sonner";

import axiosInstance from "@/lib/axios";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface BillingSettings {
  base_currency: string;
  inr_conversion_rate: number;
  gst_percent: number;
  payment_methods: {
    razorpay_upi: boolean;
    card: boolean;
    crypto: boolean;
  };
  live_trading_requires_subscription: boolean;
}

const DEFAULT_SETTINGS: BillingSettings = {
  base_currency: "USD",
  inr_conversion_rate: 83,
  gst_percent: 18,
  payment_methods: {
    razorpay_upi: true,
    card: true,
    crypto: true,
  },
  live_trading_requires_subscription: true,
};

const unwrap = <T,>(payload: any): T => (payload?.success ? payload.data : payload) as T;

function ToggleRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/[0.06] p-4 text-sm text-purple-100/85 transition hover:bg-white/10">
      <span className="font-medium text-white/90">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-5 w-5 shrink-0 accent-fuchsia-500"
      />
    </label>
  );
}

export default function BillingSettingsCard() {
  const [settings, setSettings] = useState<BillingSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const response = await axiosInstance.get("/api/v1/admin/billing/settings");
      const data = unwrap<BillingSettings>(response.data);
      setSettings({ ...DEFAULT_SETTINGS, ...(data || {}), payment_methods: { ...DEFAULT_SETTINGS.payment_methods, ...(data?.payment_methods || {}) } });
    } catch (error: any) {
      toast.error(error?.message || "Failed to load billing settings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const save = async () => {
    const inrRate = Number(settings.inr_conversion_rate || 0);
    const gst = Number(settings.gst_percent || 0);
    const methods = settings.payment_methods;

    if (inrRate <= 0) return toast.error("INR conversion rate must be greater than 0");
    if (gst < 0 || gst > 50) return toast.error("GST percent must be between 0 and 50");
    if (!methods.razorpay_upi && !methods.card && !methods.crypto) {
      return toast.error("At least one payment method must remain enabled");
    }

    try {
      setSaving(true);
      const response = await axiosInstance.put("/api/v1/admin/billing/settings", {
        base_currency: "USD",
        inr_conversion_rate: inrRate,
        gst_percent: gst,
        payment_methods: methods,
        live_trading_requires_subscription: settings.live_trading_requires_subscription,
      });
      const data = unwrap<BillingSettings>(response.data);
      setSettings({ ...DEFAULT_SETTINGS, ...(data || {}), payment_methods: { ...DEFAULT_SETTINGS.payment_methods, ...(data?.payment_methods || {}) } });
      toast.success("Billing settings saved");
    } catch (error: any) {
      toast.error(error?.message || "Failed to save billing settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h3 className="flex items-center gap-2 text-lg font-semibold text-white">
            <CreditCard className="h-5 w-5 text-emerald-300" />
            Billing Settings
          </h3>
          <p className="mt-1 text-sm text-purple-100/65">
            Manage USD billing foundation, INR conversion, GST, payment methods, and live trading access gate.
          </p>
        </div>
        <span className="rounded-full border border-emerald-300/20 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-200">
          Base: USD
        </span>
      </div>

      {loading ? (
        <div className="h-32 animate-pulse rounded-2xl bg-white/10" />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label className="text-purple-100/80">INR conversion rate</Label>
              <Input
                type="number"
                min={0.01}
                step="0.01"
                value={settings.inr_conversion_rate}
                onChange={(event) => setSettings((prev) => ({ ...prev, inr_conversion_rate: Number(event.target.value || 0) }))}
                className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40"
              />
              <p className="text-xs text-purple-100/55">Example: 1 USD = 83 INR</p>
            </div>
            <div className="space-y-2">
              <Label className="text-purple-100/80">GST percent</Label>
              <Input
                type="number"
                min={0}
                max={50}
                step="0.01"
                value={settings.gst_percent}
                onChange={(event) => setSettings((prev) => ({ ...prev, gst_percent: Number(event.target.value || 0) }))}
                className="border-white/10 bg-white/10 text-white placeholder:text-purple-100/40"
              />
              <p className="text-xs text-purple-100/55">Used for future invoices and checkout summaries.</p>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <ToggleRow
              label="Razorpay UPI enabled"
              checked={settings.payment_methods.razorpay_upi}
              onChange={(value) => setSettings((prev) => ({ ...prev, payment_methods: { ...prev.payment_methods, razorpay_upi: value } }))}
            />
            <ToggleRow
              label="Card payment enabled"
              checked={settings.payment_methods.card}
              onChange={(value) => setSettings((prev) => ({ ...prev, payment_methods: { ...prev.payment_methods, card: value } }))}
            />
            <ToggleRow
              label="Crypto payment enabled"
              checked={settings.payment_methods.crypto}
              onChange={(value) => setSettings((prev) => ({ ...prev, payment_methods: { ...prev.payment_methods, crypto: value } }))}
            />
          </div>


          <ToggleRow
            label="Require active subscription for live trading"
            checked={settings.live_trading_requires_subscription !== false}
            onChange={(value) => setSettings((prev) => ({ ...prev, live_trading_requires_subscription: value }))}
          />

          <Button
            type="button"
            onClick={() => void save()}
            disabled={saving}
            className="w-full rounded-2xl bg-gradient-to-r from-emerald-500 via-teal-500 to-blue-500 py-5 text-white shadow-xl shadow-emerald-950/30"
          >
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving billing settings..." : "Save billing settings"}
          </Button>
        </div>
      )}
    </GlassCard>
  );
}
