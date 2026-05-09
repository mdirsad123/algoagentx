"use client";

import { useEffect, useMemo, useState } from "react";
import { CalendarClock, Edit, Plus, RefreshCw, Save, Search, TicketPercent, X } from "lucide-react";
import { toast } from "sonner";
import { adminApi, type AdminCoupon, type AdminCouponPayload, type CouponAppliesTo, type CouponBillingPeriod, type CouponDiscountType } from "@/lib/api/admin";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

const emptyForm: AdminCouponPayload = {
  code: "",
  description: "",
  discount_type: "PERCENT",
  discount_value: 20,
  applies_to: "ALL",
  plan_code: "",
  billing_period: "",
  min_order_usd: null,
  max_discount_usd: null,
  max_redemptions: null,
  per_user_limit: 1,
  starts_at: "",
  expires_at: "",
  is_active: true,
};

const money = (value?: number | null) => value == null ? "—" : `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const compactDate = (value?: string | null) => value ? new Date(value).toLocaleString() : "—";

function normalizedForm(form: AdminCouponPayload): AdminCouponPayload {
  const blankToNull = (value: any) => value === "" || value === undefined ? null : value;
  return {
    ...form,
    code: String(form.code || "").trim().toUpperCase(),
    description: String(form.description || "").trim() || null,
    plan_code: String(form.plan_code || "").trim().toUpperCase() || null,
    billing_period: (String(form.billing_period || "").trim().toUpperCase() || null) as CouponBillingPeriod | null,
    min_order_usd: blankToNull(form.min_order_usd) == null ? null : Number(form.min_order_usd),
    max_discount_usd: blankToNull(form.max_discount_usd) == null ? null : Number(form.max_discount_usd),
    max_redemptions: blankToNull(form.max_redemptions) == null ? null : Number(form.max_redemptions),
    per_user_limit: blankToNull(form.per_user_limit) == null ? null : Number(form.per_user_limit),
    starts_at: String(form.starts_at || "").trim() || null,
    expires_at: String(form.expires_at || "").trim() || null,
  };
}

function toDatetimeLocal(value?: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function couponToForm(coupon: AdminCoupon): AdminCouponPayload {
  return {
    code: coupon.code,
    description: coupon.description || "",
    discount_type: coupon.discount_type,
    discount_value: Number(coupon.discount_value || 0),
    applies_to: coupon.applies_to,
    plan_code: coupon.plan_code || "",
    billing_period: coupon.billing_period || "",
    min_order_usd: coupon.min_order_usd ?? null,
    max_discount_usd: coupon.max_discount_usd ?? null,
    max_redemptions: coupon.max_redemptions ?? null,
    per_user_limit: coupon.per_user_limit ?? 1,
    starts_at: toDatetimeLocal(coupon.starts_at),
    expires_at: toDatetimeLocal(coupon.expires_at),
    is_active: coupon.is_active,
  };
}

function validate(form: AdminCouponPayload) {
  const code = String(form.code || "").trim();
  if (!code) return "Coupon code is required";
  if (/\s/.test(code)) return "Coupon code cannot contain spaces";
  if (form.discount_type === "PERCENT" && (Number(form.discount_value) <= 0 || Number(form.discount_value) > 100)) return "Percent discount must be greater than 0 and max 100";
  if (form.discount_type === "FIXED_USD" && Number(form.discount_value) <= 0) return "Fixed USD discount must be greater than 0";
  if (form.per_user_limit != null && Number(form.per_user_limit) <= 0) return "Per user limit must be positive";
  if (form.starts_at && form.expires_at && new Date(form.expires_at) < new Date(form.starts_at)) return "Expiry date cannot be before start date";
  return null;
}

function CouponForm({ form, setForm, onSubmit, onCancel, saving, mode }: {
  form: AdminCouponPayload;
  setForm: (next: AdminCouponPayload) => void;
  onSubmit: () => void;
  onCancel?: () => void;
  saving: boolean;
  mode: "create" | "edit";
}) {
  const update = (patch: Partial<AdminCouponPayload>) => setForm({ ...form, ...patch });
  return (
    <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-semibold text-white"><TicketPercent className="h-5 w-5 text-fuchsia-300" />{mode === "create" ? "Create Coupon" : "Edit Coupon"}</h2>
          <p className="mt-1 text-sm text-purple-100/65">Create real checkout-ready discount rules. Preview only in this phase.</p>
        </div>
        {onCancel && <Button variant="outline" className="gap-2 border-white/15 bg-white/5 text-white hover:bg-white/10" onClick={onCancel}><X className="h-4 w-4" />Cancel</Button>}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2"><Label>Coupon code</Label><Input value={form.code} onChange={(e) => update({ code: e.target.value.toUpperCase().replace(/\s/g, "") })} placeholder="HELLO" className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Discount type</Label><select value={form.discount_type} onChange={(e) => update({ discount_type: e.target.value as CouponDiscountType })} className="h-10 w-full rounded-md border border-white/10 bg-[#3a1a63] px-3 text-sm text-white"><option value="PERCENT">Percent</option><option value="FIXED_USD">Fixed USD</option></select></div>
        <div className="space-y-2"><Label>Discount value</Label><Input type="number" min={0} step="0.01" value={form.discount_value} onChange={(e) => update({ discount_value: Number(e.target.value) })} className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Applies to</Label><select value={form.applies_to} onChange={(e) => update({ applies_to: e.target.value as CouponAppliesTo })} className="h-10 w-full rounded-md border border-white/10 bg-[#3a1a63] px-3 text-sm text-white"><option value="ALL">All</option><option value="SUBSCRIPTION">Subscription</option><option value="CREDITS">Credits</option></select></div>
        <div className="space-y-2"><Label>Plan code optional</Label><Input value={form.plan_code || ""} onChange={(e) => update({ plan_code: e.target.value.toUpperCase() })} placeholder="PREMIUM" className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Billing period optional</Label><select value={form.billing_period || ""} onChange={(e) => update({ billing_period: e.target.value as CouponBillingPeriod })} className="h-10 w-full rounded-md border border-white/10 bg-[#3a1a63] px-3 text-sm text-white"><option value="">Any</option><option value="NONE">None</option><option value="MONTHLY">Monthly</option><option value="YEARLY">Yearly</option></select></div>
        <div className="space-y-2"><Label>Min order USD</Label><Input type="number" min={0} step="0.01" value={form.min_order_usd ?? ""} onChange={(e) => update({ min_order_usd: e.target.value === "" ? null : Number(e.target.value) })} placeholder="Optional" className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Max discount USD</Label><Input type="number" min={0} step="0.01" value={form.max_discount_usd ?? ""} onChange={(e) => update({ max_discount_usd: e.target.value === "" ? null : Number(e.target.value) })} placeholder="Optional" className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Max redemptions</Label><Input type="number" min={1} value={form.max_redemptions ?? ""} onChange={(e) => update({ max_redemptions: e.target.value === "" ? null : Number(e.target.value) })} placeholder="Optional" className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Per user limit</Label><Input type="number" min={1} value={form.per_user_limit ?? ""} onChange={(e) => update({ per_user_limit: e.target.value === "" ? null : Number(e.target.value) })} className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Start date</Label><Input type="datetime-local" value={form.starts_at || ""} onChange={(e) => update({ starts_at: e.target.value })} className="border-white/10 bg-white/10 text-white" /></div>
        <div className="space-y-2"><Label>Expiry date</Label><Input type="datetime-local" value={form.expires_at || ""} onChange={(e) => update({ expires_at: e.target.value })} className="border-white/10 bg-white/10 text-white" /></div>
      </div>
      <div className="mt-4 space-y-2"><Label>Description</Label><Textarea value={form.description || ""} onChange={(e) => update({ description: e.target.value })} placeholder="Internal admin note or public coupon description" className="min-h-[82px] border-white/10 bg-white/10 text-white" /></div>
      <label className="mt-4 flex cursor-pointer items-center justify-between rounded-2xl border border-white/10 bg-white/[0.06] p-4 text-sm text-purple-100/85"><span><span className="block font-medium text-white/90">Active coupon</span><span className="text-xs text-purple-100/55">Inactive coupons fail preview validation.</span></span><input type="checkbox" checked={form.is_active} onChange={(e) => update({ is_active: e.target.checked })} className="h-5 w-5 accent-fuchsia-500" /></label>
      <Button onClick={onSubmit} disabled={saving} className="mt-5 w-full gap-2 rounded-xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white"><Save className="h-4 w-4" />{saving ? "Saving..." : mode === "create" ? "Create coupon" : "Save coupon"}</Button>
    </GlassCard>
  );
}

export default function AdminCouponsPage() {
  const [items, setItems] = useState<AdminCoupon[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [createForm, setCreateForm] = useState<AdminCouponPayload>(emptyForm);
  const [editing, setEditing] = useState<AdminCoupon | null>(null);
  const [editForm, setEditForm] = useState<AdminCouponPayload>(emptyForm);

  const load = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getCoupons(search.trim() || undefined);
      setItems(data.items || []);
    } catch (error: any) {
      toast.error(error?.message || "Failed to load coupons");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const stats = useMemo(() => ({
    total: items.length,
    active: items.filter((item) => item.is_active).length,
    percent: items.filter((item) => item.discount_type === "PERCENT").length,
    fixed: items.filter((item) => item.discount_type === "FIXED_USD").length,
  }), [items]);

  const createCoupon = async () => {
    const error = validate(createForm);
    if (error) return toast.error(error);
    try {
      setSaving(true);
      await adminApi.createCoupon(normalizedForm(createForm));
      toast.success("Coupon created");
      setCreateForm(emptyForm);
      await load();
    } catch (error: any) {
      toast.error(error?.message || "Failed to create coupon");
    } finally {
      setSaving(false);
    }
  };

  const updateCoupon = async () => {
    if (!editing) return;
    const error = validate(editForm);
    if (error) return toast.error(error);
    try {
      setSaving(true);
      await adminApi.updateCoupon(editing.id, normalizedForm(editForm));
      toast.success("Coupon updated");
      setEditing(null);
      await load();
    } catch (error: any) {
      toast.error(error?.message || "Failed to update coupon");
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (coupon: AdminCoupon) => {
    try {
      await adminApi.toggleCoupon(coupon.id, !coupon.is_active);
      toast.success(!coupon.is_active ? "Coupon activated" : "Coupon deactivated");
      await load();
    } catch (error: any) {
      toast.error(error?.message || "Failed to update coupon status");
    }
  };

  const startEdit = (coupon: AdminCoupon) => {
    setEditing(coupon);
    setEditForm(couponToForm(coupon));
    if (typeof window !== "undefined") window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Coupon Master" subtitle="Create checkout-ready coupon codes and manage discount rules." />

      <div className="grid gap-4 md:grid-cols-4">
        {[ ["Total coupons", stats.total], ["Active coupons", stats.active], ["Percent discounts", stats.percent], ["Fixed USD", stats.fixed] ].map(([label, value]) => (
          <GlassCard key={String(label)} className="rounded-2xl border border-white/10 p-5 hover:scale-100"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-purple-100/60">{label}</p><p className="mt-2 text-3xl font-bold text-white">{value}</p></GlassCard>
        ))}
      </div>

      {editing ? <CouponForm form={editForm} setForm={setEditForm} onSubmit={updateCoupon} onCancel={() => setEditing(null)} saving={saving} mode="edit" /> : <CouponForm form={createForm} setForm={setCreateForm} onSubmit={createCoupon} saving={saving} mode="create" />}

      <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div><h2 className="text-xl font-semibold text-white">Coupons Table</h2><p className="mt-1 text-sm text-purple-100/65">Deactivate coupons instead of deleting them so audit history remains safe.</p></div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative"><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-purple-100/55" /><Input value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") load(); }} placeholder="Search coupon" className="pl-9 border-white/10 bg-white/10 text-white" /></div>
            <Button variant="outline" onClick={load} className="gap-2 border-white/15 bg-white/5 text-white hover:bg-white/10"><RefreshCw className="h-4 w-4" />Refresh</Button>
          </div>
        </div>
        <div className="admin-table-scroll overflow-x-auto rounded-2xl border border-white/10">
          <table className="admin-data-table min-w-full divide-y divide-white/10 text-sm">
            <thead className="bg-white/[0.06] text-left text-xs uppercase tracking-wide text-purple-100/70"><tr><th className="px-4 py-3">Code</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Applies</th><th className="px-4 py-3">Scope</th><th className="px-4 py-3">Limits</th><th className="px-4 py-3">Dates</th><th className="px-4 py-3">Audit</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th></tr></thead>
            <tbody className="divide-y divide-white/10 text-purple-100/85">
              {loading ? <tr><td colSpan={9} className="px-4 py-8 text-center text-purple-100/65">Loading coupons...</td></tr> : items.length === 0 ? <tr><td colSpan={9} className="px-4 py-8 text-center text-purple-100/65">No coupons found. Create HELLO or TEST5 to start.</td></tr> : items.map((coupon) => (
                <tr key={coupon.id} className="hover:bg-white/[0.04]">
                  <td className="px-4 py-4"><div className="font-bold text-white">{coupon.code}</div><div className="max-w-[260px] truncate text-xs text-purple-100/55">{coupon.description || "—"}</div></td>
                  <td className="px-4 py-4"><Badge className="border-fuchsia-300/30 bg-fuchsia-500/15 text-fuchsia-100">{coupon.discount_type === "PERCENT" ? `${coupon.discount_value}%` : money(coupon.discount_value)}</Badge></td>
                  <td className="px-4 py-4">{coupon.applies_to}</td>
                  <td className="px-4 py-4"><div>{coupon.plan_code || "Any plan"}</div><div className="text-xs text-purple-100/55">{coupon.billing_period || "Any period"}</div></td>
                  <td className="px-4 py-4"><div>Min: {money(coupon.min_order_usd)}</div><div className="text-xs text-purple-100/55">Max disc: {money(coupon.max_discount_usd)} · Used {coupon.redemption_count || 0}/{coupon.max_redemptions || "∞"}</div><div className="text-xs text-purple-100/55">Per user: {coupon.per_user_limit || "∞"}</div></td>
                  <td className="px-4 py-4"><div className="flex items-center gap-1"><CalendarClock className="h-3.5 w-3.5" />{compactDate(coupon.starts_at)}</div><div className="mt-1 text-xs text-purple-100/55">Expires: {compactDate(coupon.expires_at)}</div></td>
                  <td className="px-4 py-4"><div>{coupon.redemption_count || 0} redemptions</div><div className="text-xs text-emerald-200">Total discount: {money((coupon as any).total_discount_usd)}</div><div className="text-xs text-purple-100/55">Last used: {compactDate((coupon as any).last_used_at)}</div></td>
                  <td className="px-4 py-4"><Badge className={coupon.is_active ? "border-emerald-300/30 bg-emerald-500/15 text-emerald-100" : "border-rose-300/30 bg-rose-500/15 text-rose-100"}>{coupon.is_active ? "Active" : "Inactive"}</Badge></td>
                  <td className="px-4 py-4"><div className="flex justify-end gap-2"><Button size="sm" variant="outline" onClick={() => startEdit(coupon)} className="gap-1 border-white/15 bg-white/5 text-white hover:bg-white/10"><Edit className="h-3.5 w-3.5" />Edit</Button><Button size="sm" variant="outline" onClick={() => toggle(coupon)} className="border-white/15 bg-white/5 text-white hover:bg-white/10">{coupon.is_active ? "Deactivate" : "Activate"}</Button></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}
