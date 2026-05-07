"use client";

import { useEffect, useState } from "react";
import { Gift, Save } from "lucide-react";
import { toast } from "sonner";
import { couponBarApi, CouponBarConfig } from "@/lib/api/coupon-bar";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const emptyConfig: CouponBarConfig = { enabled: false, message: "", code: "" };

export default function CouponBarSettingsCard() {
  const [config, setConfig] = useState<CouponBarConfig>(emptyConfig);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    couponBarApi
      .getAdmin()
      .then((data) => {
        if (alive) setConfig(data || emptyConfig);
      })
      .catch((err) => {
        if (alive) setError(err?.message || "Failed to load coupon bar settings");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const save = async () => {
    const payload = {
      enabled: Boolean(config.enabled),
      message: (config.message || "").trim().slice(0, 300),
      code: (config.code || "").trim().slice(0, 50),
    };
    try {
      setSaving(true);
      setError("");
      const saved = await couponBarApi.updateAdmin(payload);
      setConfig(saved);
      toast.success("Coupon announcement bar saved");
    } catch (err: any) {
      const msg = err?.message || "Failed to save coupon bar settings";
      setError(msg);
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="flex items-center gap-2 text-lg font-semibold text-white">
            <Gift className="h-5 w-5 text-fuchsia-300" />
            Coupon Announcement Bar
          </h3>
          <p className="mt-1 text-sm text-purple-100/65">Manage top promotional message shown to logged-in users.</p>
        </div>
        <label className="inline-flex cursor-pointer items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3 text-sm font-medium text-white transition hover:bg-white/10">
          <input
            type="checkbox"
            checked={config.enabled}
            disabled={loading}
            onChange={(e) => setConfig((prev) => ({ ...prev, enabled: e.target.checked }))}
            className="h-5 w-5 accent-fuchsia-500"
          />
          Enable coupon bar
        </label>
      </div>

      <div className="mt-5 grid gap-4">
        <div className="space-y-2">
          <Label className="text-purple-100/80">Announcement message</Label>
          <Textarea
            value={config.message}
            maxLength={300}
            disabled={loading}
            onChange={(e) => setConfig((prev) => ({ ...prev, message: e.target.value }))}
            placeholder="Haven't purchased yet? Use code HELLO & Get 20% OFF now on your first purchase!"
            className="min-h-[96px] resize-none border-white/10 bg-white/10 text-white placeholder:text-purple-100/40"
          />
          <div className="text-right text-xs text-purple-100/50">{(config.message || "").length}/300</div>
        </div>
        <div className="space-y-2">
          <Label className="text-purple-100/80">Coupon code</Label>
          <Input
            value={config.code}
            maxLength={50}
            disabled={loading}
            onChange={(e) => setConfig((prev) => ({ ...prev, code: e.target.value.toUpperCase() }))}
            placeholder="HELLO"
            className="border-white/10 bg-white/10 font-semibold uppercase tracking-[0.18em] text-white placeholder:text-purple-100/40"
          />
        </div>
        {error ? <div className="rounded-2xl border border-red-400/25 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}
        <Button onClick={save} disabled={loading || saving} className="w-full rounded-2xl bg-gradient-to-r from-fuchsia-500 to-blue-500 py-6 text-white shadow-xl shadow-fuchsia-950/30 md:w-auto md:px-8">
          <Save className="mr-2 h-5 w-5" />
          {saving ? "Saving..." : "Save coupon bar"}
        </Button>
      </div>
    </GlassCard>
  );
}
