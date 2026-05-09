"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, Pencil, Plus, RefreshCw, Save, X } from "lucide-react";
import { toast } from "sonner";

import { adminApi, type AdminPricingPlan, type AdminPricingPlanPayload } from "@/lib/api/admin";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type BillingPeriod = AdminPricingPlan["billing_period"];

type PlanFormState = {
  code: string;
  billing_period: BillingPeriod;
  price_usd: number;
  price_inr: number;
  included_credits: number;
  summary: string;
  daily_backtests: number;
  daily_ai_screener_runs: number;
  max_date_range_days: number;
  export_results: boolean;
  advanced_strategies: boolean;
  ai_screener_access: boolean;
  priority_support: boolean;
  dedicated_account_manager: boolean;
  is_active: boolean;
};

const PLAN_PRESETS: Array<{ label: string; code: string; billing_period: BillingPeriod }> = [
  { label: "FREE / NONE", code: "FREE", billing_period: "NONE" },
  { label: "PRO / MONTHLY", code: "PRO", billing_period: "MONTHLY" },
  { label: "PRO / YEARLY", code: "PRO", billing_period: "YEARLY" },
  { label: "PREMIUM / MONTHLY", code: "PREMIUM", billing_period: "MONTHLY" },
  { label: "PREMIUM / YEARLY", code: "PREMIUM", billing_period: "YEARLY" },
  { label: "ULTIMATE / MONTHLY", code: "ULTIMATE", billing_period: "MONTHLY" },
  { label: "ULTIMATE / YEARLY", code: "ULTIMATE", billing_period: "YEARLY" },
];

const emptyForm = (): PlanFormState => ({
  code: "",
  billing_period: "MONTHLY",
  price_usd: 0,
  price_inr: 0,
  included_credits: 0,
  summary: "",
  daily_backtests: 0,
  daily_ai_screener_runs: 0,
  max_date_range_days: 0,
  export_results: false,
  advanced_strategies: false,
  ai_screener_access: false,
  priority_support: false,
  dedicated_account_manager: false,
  is_active: true,
});

const planSortOrder = (code: string): number => {
  const normalized = String(code || "").toUpperCase();
  if (normalized === "FREE") return 1;
  if (normalized === "PRO") return 2;
  if (normalized === "PREMIUM") return 3;
  if (normalized === "ULTIMATE") return 4;
  return 99;
};

const periodSortOrder = (period: string): number => {
  const normalized = String(period || "").toUpperCase();
  if (normalized === "NONE") return 1;
  if (normalized === "MONTHLY") return 2;
  if (normalized === "YEARLY") return 3;
  return 99;
};

const toFormState = (plan: AdminPricingPlan): PlanFormState => ({
  code: String(plan.code || "").toUpperCase(),
  billing_period: plan.billing_period,
  price_usd: Number(plan.price_usd || 0),
  price_inr: Number(plan.price_inr || 0),
  included_credits: Number(plan.included_credits || 0),
  summary: String(plan.summary || ""),
  daily_backtests: Number(plan.daily_backtests || 0),
  daily_ai_screener_runs: Number(plan.daily_ai_screener_runs || 0),
  max_date_range_days: Number(plan.max_date_range_days || 0),
  export_results: !!plan.export_results,
  advanced_strategies: !!plan.advanced_strategies,
  ai_screener_access: !!plan.ai_screener_access,
  priority_support: !!plan.priority_support,
  dedicated_account_manager: !!plan.dedicated_account_manager,
  is_active: !!plan.is_active,
});

const toPayload = (form: PlanFormState): AdminPricingPlanPayload => ({
  code: String(form.code || "").trim().toUpperCase(),
  billing_period: form.billing_period,
  price_usd: Math.max(0, Number(form.price_usd || 0)),
  price_inr: Math.max(0, Number(form.price_inr || 0)) || Math.round(Math.max(0, Number(form.price_usd || 0)) * 83),
  included_credits: Math.max(0, Number(form.included_credits || 0)),
  summary: String(form.summary || "").trim(),
  daily_backtests: Math.max(0, Number(form.daily_backtests || 0)),
  daily_ai_screener_runs: Math.max(0, Number(form.daily_ai_screener_runs || 0)),
  max_date_range_days: Math.max(0, Number(form.max_date_range_days || 0)),
  export_results: !!form.export_results,
  advanced_strategies: !!form.advanced_strategies,
  ai_screener_access: !!form.ai_screener_access,
  priority_support: !!form.priority_support,
  dedicated_account_manager: !!form.dedicated_account_manager,
  is_active: !!form.is_active,
});

export default function AdminPricingPage() {
  const [plans, setPlans] = useState<AdminPricingPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingDraft, setEditingDraft] = useState<PlanFormState | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<PlanFormState>(emptyForm());

  const loadPlans = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getPricingPlans();
      setPlans(
        (data || []).sort((a, b) => {
          const codeOrder = planSortOrder(a.code) - planSortOrder(b.code);
          if (codeOrder !== 0) return codeOrder;
          return periodSortOrder(a.billing_period) - periodSortOrder(b.billing_period);
        }),
      );
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to load pricing plans");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPlans();
  }, []);

  const stats = useMemo(
    () => ({
      total: plans.length,
      active: plans.filter((plan) => plan.is_active).length,
      paid: plans.filter((plan) => plan.code !== "FREE").length,
      free: plans.filter((plan) => plan.code === "FREE").length,
    }),
    [plans],
  );

  const startEdit = (plan: AdminPricingPlan) => {
    setEditingId(plan.id);
    setEditingDraft(toFormState(plan));
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditingDraft(null);
  };

  const updateDraft = <K extends keyof PlanFormState>(key: K, value: PlanFormState[K]) => {
    setEditingDraft((prev) => {
      if (!prev) return prev;
      return { ...prev, [key]: value };
    });
  };

  const saveEdit = async (planId: string) => {
    if (!editingDraft) return;
    try {
      setSavingId(planId);
      await adminApi.updatePricingPlan(planId, toPayload(editingDraft));
      toast.success("Plan updated successfully");
      setEditingId(null);
      setEditingDraft(null);
      await loadPlans();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to update plan");
    } finally {
      setSavingId(null);
    }
  };

  const toggleActive = async (plan: AdminPricingPlan) => {
    try {
      setSavingId(plan.id);
      await adminApi.togglePricingPlan(plan.id, !plan.is_active);
      toast.success(plan.is_active ? "Plan deactivated" : "Plan activated");
      await loadPlans();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to update plan status");
    } finally {
      setSavingId(null);
    }
  };

  const createPlan = async () => {
    try {
      setSavingId("new");
      await adminApi.createPricingPlan(toPayload(createForm));
      toast.success("Plan created successfully");
      setCreateOpen(false);
      setCreateForm(emptyForm());
      await loadPlans();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to create plan");
    } finally {
      setSavingId(null);
    }
  };

  const applyPreset = (preset: { code: string; billing_period: BillingPeriod }) => {
    setCreateForm((prev) => ({
      ...prev,
      code: preset.code,
      billing_period: preset.billing_period,
    }));
  };

  const yesNoCell = (value: boolean) =>
    value ? <Check className="mx-auto h-4 w-4 text-emerald-400" /> : <X className="mx-auto h-4 w-4 text-rose-400" />;

  const renderFormFields = (
    form: PlanFormState,
    setField: <K extends keyof PlanFormState>(key: K, value: PlanFormState[K]) => void,
  ) => (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
      <div className="space-y-1.5">
        <Label>Plan Code</Label>
        <Input
          value={form.code}
          onChange={(e) => setField("code", e.target.value.toUpperCase())}
          placeholder="PRO"
          className="rounded-xl border-border/50 bg-card/20 text-foreground"
        />
      </div>

      <div className="space-y-1.5">
        <Label>Billing Period</Label>
        <Select value={form.billing_period} onValueChange={(value) => setField("billing_period", value as BillingPeriod)}>
          <SelectTrigger className="rounded-xl border-border/50 bg-card/20 text-foreground">
            <SelectValue placeholder="Select period" />
          </SelectTrigger>
          <SelectContent className="border-border/50 bg-card text-foreground">
            <SelectItem value="NONE">NONE</SelectItem>
            <SelectItem value="MONTHLY">MONTHLY</SelectItem>
            <SelectItem value="YEARLY">YEARLY</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>Price USD</Label>
        <Input
          type="number"
          min={0}
          step="0.01"
          value={form.price_usd}
          onChange={(e) => setField("price_usd", Number(e.target.value || 0))}
          className="rounded-xl border-border/50 bg-card/20 text-foreground"
        />
      </div>

      <div className="space-y-1.5">
        <Label>Included Credits</Label>
        <Input
          type="number"
          min={0}
          value={form.included_credits}
          onChange={(e) => setField("included_credits", Number(e.target.value || 0))}
          className="rounded-xl border-border/50 bg-card/20 text-foreground"
        />
      </div>

      <div className="space-y-1.5 md:col-span-2 xl:col-span-4">
        <Label>Summary</Label>
        <Input
          value={form.summary}
          onChange={(e) => setField("summary", e.target.value)}
          placeholder="Plan summary for pricing page"
          className="rounded-xl border-border/50 bg-card/20 text-foreground"
        />
      </div>

      <div className="space-y-1.5">
        <Label>Daily Backtests</Label>
        <Input
          type="number"
          min={0}
          value={form.daily_backtests}
          onChange={(e) => setField("daily_backtests", Number(e.target.value || 0))}
          className="rounded-xl border-border/50 bg-card/20 text-foreground"
        />
      </div>

      <div className="space-y-1.5">
        <Label>Daily AI Screener Runs</Label>
        <Input
          type="number"
          min={0}
          value={form.daily_ai_screener_runs}
          onChange={(e) => setField("daily_ai_screener_runs", Number(e.target.value || 0))}
          className="rounded-xl border-border/50 bg-card/20 text-foreground"
        />
      </div>

      <div className="space-y-1.5">
        <Label>Max Date Range Days</Label>
        <Input
          type="number"
          min={0}
          value={form.max_date_range_days}
          onChange={(e) => setField("max_date_range_days", Number(e.target.value || 0))}
          className="rounded-xl border-border/50 bg-card/20 text-foreground"
        />
      </div>

      <div className="space-y-1.5">
        <Label>Active Status</Label>
        <div className="flex h-10 items-center gap-2 rounded-xl border border-border/50 bg-card/20 px-3">
          <Checkbox checked={form.is_active} onCheckedChange={(checked) => setField("is_active", !!checked)} />
          <span className="text-sm text-foreground">Plan is active</span>
        </div>
      </div>

      <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-card/20 px-3 py-2">
        <Checkbox checked={form.export_results} onCheckedChange={(checked) => setField("export_results", !!checked)} />
        <span className="text-sm text-foreground">Export Results</span>
      </div>
      <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-card/20 px-3 py-2">
        <Checkbox
          checked={form.advanced_strategies}
          onCheckedChange={(checked) => setField("advanced_strategies", !!checked)}
        />
        <span className="text-sm text-foreground">Advanced Strategies</span>
      </div>
      <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-card/20 px-3 py-2">
        <Checkbox
          checked={form.ai_screener_access}
          onCheckedChange={(checked) => setField("ai_screener_access", !!checked)}
        />
        <span className="text-sm text-foreground">AI Screener Access</span>
      </div>
      <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-card/20 px-3 py-2">
        <Checkbox checked={form.priority_support} onCheckedChange={(checked) => setField("priority_support", !!checked)} />
        <span className="text-sm text-foreground">Priority Support</span>
      </div>
      <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-card/20 px-3 py-2 xl:col-span-2">
        <Checkbox
          checked={form.dedicated_account_manager}
          onCheckedChange={(checked) => setField("dedicated_account_manager", !!checked)}
        />
        <span className="text-sm text-foreground">Dedicated Account Manager</span>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Pricing Master</h1>
          <p className="text-sm text-muted-foreground">
            Manage USD plan pricing, limits, features, and activation in a structured admin table.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => void loadPlans()}
            className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>

          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="rounded-xl">
                <Plus className="mr-2 h-4 w-4" />
                Create Plan
              </Button>
            </DialogTrigger>
            <DialogContent className="max-h-[90vh] max-w-5xl overflow-y-auto rounded-2xl border border-border/60 bg-card/95 text-foreground backdrop-blur-xl">
              <DialogHeader>
                <DialogTitle>Create Pricing Plan</DialogTitle>
                <DialogDescription>Use structured fields only. JSON stays internal to backend storage.</DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {PLAN_PRESETS.map((preset) => (
                    <Button
                      key={preset.label}
                      type="button"
                      variant="outline"
                      className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                      onClick={() => applyPreset(preset)}
                    >
                      {preset.label}
                    </Button>
                  ))}
                </div>

                {renderFormFields(createForm, (key, value) => {
                  setCreateForm((prev) => ({ ...prev, [key]: value }));
                })}
              </div>

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setCreateOpen(false)}
                  className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                >
                  Cancel
                </Button>
                <Button type="button" className="rounded-xl" onClick={() => void createPlan()} disabled={savingId === "new"}>
                  {savingId === "new" ? "Creating..." : "Create Plan"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Total Plans</CardDescription>
            <CardTitle className="text-3xl text-foreground">{stats.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Active Plans</CardDescription>
            <CardTitle className="text-3xl text-foreground">{stats.active}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Paid Plans</CardDescription>
            <CardTitle className="text-3xl text-foreground">{stats.paid}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader className="pb-2">
            <CardDescription>Free Plans</CardDescription>
            <CardTitle className="text-3xl text-foreground">{stats.free}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardHeader>
          <CardTitle className="text-foreground">Pricing Plans Table</CardTitle>
          <CardDescription>
            Edit row values with structured inputs. Save or cancel changes safely for each pricing plan.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="rounded-xl border border-border/50 bg-card/20 p-6 text-sm text-muted-foreground">
              Loading pricing plans...
            </div>
          ) : plans.length === 0 ? (
            <div className="rounded-xl border border-border/50 bg-card/20 p-6 text-sm text-muted-foreground">
              No pricing plans found. Create your first plan using <span className="font-medium text-foreground">Create Plan</span>.
            </div>
          ) : (
            <div className="admin-table-scroll overflow-x-auto rounded-xl border border-border/50 bg-card/20">
              <Table className="min-w-[1900px]">
                <TableHeader>
                  <TableRow className="border-border/60 hover:bg-transparent">
                    <TableHead>Plan Code</TableHead>
                    <TableHead>Billing Period</TableHead>
                    <TableHead>Price USD</TableHead>
                    <TableHead>Included Credits</TableHead>
                    <TableHead>Daily Backtests</TableHead>
                    <TableHead>Daily AI Screener Runs</TableHead>
                    <TableHead>Max Date Range Days</TableHead>
                    <TableHead className="text-center">Export Results</TableHead>
                    <TableHead className="text-center">Advanced Strategies</TableHead>
                    <TableHead className="text-center">AI Screener Access</TableHead>
                    <TableHead className="text-center">Priority Support</TableHead>
                    <TableHead className="text-center">Dedicated Account Manager</TableHead>
                    <TableHead>Summary</TableHead>
                    <TableHead>Active Status</TableHead>
                    <TableHead className="w-[220px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {plans.map((plan) => {
                    const isEditing = editingId === plan.id;
                    const row = isEditing && editingDraft ? editingDraft : toFormState(plan);
                    const isSaving = savingId === plan.id;

                    return (
                      <TableRow key={plan.id} className="border-border/40 hover:bg-card/40">
                        <TableCell>
                          {isEditing ? (
                            <Input
                              value={row.code}
                              onChange={(e) => updateDraft("code", e.target.value.toUpperCase())}
                              className="h-9 rounded-xl border-border/50 bg-card/20 text-foreground"
                            />
                          ) : (
                            <span className="font-medium text-foreground">{plan.code}</span>
                          )}
                        </TableCell>

                        <TableCell>
                          {isEditing ? (
                            <Select
                              value={row.billing_period}
                              onValueChange={(value) => updateDraft("billing_period", value as BillingPeriod)}
                            >
                              <SelectTrigger className="h-9 rounded-xl border-border/50 bg-card/20 text-foreground">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent className="border-border/50 bg-card text-foreground">
                                <SelectItem value="NONE">NONE</SelectItem>
                                <SelectItem value="MONTHLY">MONTHLY</SelectItem>
                                <SelectItem value="YEARLY">YEARLY</SelectItem>
                              </SelectContent>
                            </Select>
                          ) : (
                            <span className="text-foreground">{plan.billing_period}</span>
                          )}
                        </TableCell>

                        <TableCell>
                          {isEditing ? (
                            <Input
                              type="number"
                              min={0}
                              value={row.price_usd}
                              onChange={(e) => updateDraft("price_usd", Number(e.target.value || 0))}
                              className="h-9 rounded-xl border-border/50 bg-card/20 text-foreground"
                            />
                          ) : (
                            <span className="text-foreground">${Number(plan.price_usd || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                          )}
                        </TableCell>

                        <TableCell>
                          {isEditing ? (
                            <Input
                              type="number"
                              min={0}
                              value={row.included_credits}
                              onChange={(e) => updateDraft("included_credits", Number(e.target.value || 0))}
                              className="h-9 rounded-xl border-border/50 bg-card/20 text-foreground"
                            />
                          ) : (
                            <span className="text-foreground">{plan.included_credits}</span>
                          )}
                        </TableCell>

                        <TableCell>
                          {isEditing ? (
                            <Input
                              type="number"
                              min={0}
                              value={row.daily_backtests}
                              onChange={(e) => updateDraft("daily_backtests", Number(e.target.value || 0))}
                              className="h-9 rounded-xl border-border/50 bg-card/20 text-foreground"
                            />
                          ) : (
                            <span className="text-foreground">{plan.daily_backtests}</span>
                          )}
                        </TableCell>

                        <TableCell>
                          {isEditing ? (
                            <Input
                              type="number"
                              min={0}
                              value={row.daily_ai_screener_runs}
                              onChange={(e) => updateDraft("daily_ai_screener_runs", Number(e.target.value || 0))}
                              className="h-9 rounded-xl border-border/50 bg-card/20 text-foreground"
                            />
                          ) : (
                            <span className="text-foreground">{plan.daily_ai_screener_runs}</span>
                          )}
                        </TableCell>

                        <TableCell>
                          {isEditing ? (
                            <Input
                              type="number"
                              min={0}
                              value={row.max_date_range_days}
                              onChange={(e) => updateDraft("max_date_range_days", Number(e.target.value || 0))}
                              className="h-9 rounded-xl border-border/50 bg-card/20 text-foreground"
                            />
                          ) : (
                            <span className="text-foreground">{plan.max_date_range_days}</span>
                          )}
                        </TableCell>

                        <TableCell className="text-center">
                          {isEditing ? (
                            <Checkbox
                              checked={row.export_results}
                              onCheckedChange={(checked) => updateDraft("export_results", !!checked)}
                            />
                          ) : (
                            yesNoCell(plan.export_results)
                          )}
                        </TableCell>

                        <TableCell className="text-center">
                          {isEditing ? (
                            <Checkbox
                              checked={row.advanced_strategies}
                              onCheckedChange={(checked) => updateDraft("advanced_strategies", !!checked)}
                            />
                          ) : (
                            yesNoCell(plan.advanced_strategies)
                          )}
                        </TableCell>

                        <TableCell className="text-center">
                          {isEditing ? (
                            <Checkbox
                              checked={row.ai_screener_access}
                              onCheckedChange={(checked) => updateDraft("ai_screener_access", !!checked)}
                            />
                          ) : (
                            yesNoCell(plan.ai_screener_access)
                          )}
                        </TableCell>

                        <TableCell className="text-center">
                          {isEditing ? (
                            <Checkbox
                              checked={row.priority_support}
                              onCheckedChange={(checked) => updateDraft("priority_support", !!checked)}
                            />
                          ) : (
                            yesNoCell(plan.priority_support)
                          )}
                        </TableCell>

                        <TableCell className="text-center">
                          {isEditing ? (
                            <Checkbox
                              checked={row.dedicated_account_manager}
                              onCheckedChange={(checked) => updateDraft("dedicated_account_manager", !!checked)}
                            />
                          ) : (
                            yesNoCell(plan.dedicated_account_manager)
                          )}
                        </TableCell>

                        <TableCell>
                          {isEditing ? (
                            <Input
                              value={row.summary}
                              onChange={(e) => updateDraft("summary", e.target.value)}
                              className="h-9 rounded-xl border-border/50 bg-card/20 text-foreground"
                            />
                          ) : (
                            <span className="line-clamp-1 text-muted-foreground">{plan.summary || "—"}</span>
                          )}
                        </TableCell>

                        <TableCell>
                          {isEditing ? (
                            <div className="flex h-9 items-center gap-2 rounded-xl border border-border/50 bg-card/20 px-2">
                              <Checkbox checked={row.is_active} onCheckedChange={(checked) => updateDraft("is_active", !!checked)} />
                              <span className="text-xs text-foreground">Active</span>
                            </div>
                          ) : (
                            <Badge
                              variant="outline"
                              className="rounded-full border-border/60 bg-card/20 text-foreground"
                            >
                              {plan.is_active ? "Active" : "Inactive"}
                            </Badge>
                          )}
                        </TableCell>

                        <TableCell>
                          <div className="flex flex-wrap gap-2">
                            {isEditing ? (
                              <>
                                <Button
                                  size="sm"
                                  className="rounded-xl"
                                  onClick={() => void saveEdit(plan.id)}
                                  disabled={isSaving}
                                >
                                  <Save className="mr-1.5 h-3.5 w-3.5" />
                                  {isSaving ? "Saving..." : "Save"}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                                  onClick={cancelEdit}
                                  disabled={isSaving}
                                >
                                  <X className="mr-1.5 h-3.5 w-3.5" />
                                  Cancel
                                </Button>
                              </>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                                onClick={() => startEdit(plan)}
                              >
                                <Pencil className="mr-1.5 h-3.5 w-3.5" />
                                Edit
                              </Button>
                            )}

                            <Button
                              size="sm"
                              variant="outline"
                              className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
                              onClick={() => void toggleActive(plan)}
                              disabled={isSaving}
                            >
                              {plan.is_active ? "Deactivate" : "Activate"}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}