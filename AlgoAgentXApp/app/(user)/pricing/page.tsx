"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  CreditCard,
  RefreshCw,
  ShieldAlert,
  X,
} from "lucide-react";
import { toast } from "sonner";

import RazorpayScript from "@/components/shared/RazorpayScript";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  subscriptionsApi,
  type ActiveSubscription,
  type SubscriptionCheckoutOrder,
  type SubscriptionPlan,
  type SubscriptionPlansGrouped,
} from "@/lib/api/subscriptions";
import { formatErrorMessage, parseApiError } from "@/lib/api/error";

const EMPTY_PLANS: SubscriptionPlansGrouped = { free: [], monthly: [], yearly: [] };

const CREDIT_PACKS = [
  { label: "$1", credits: 100 },
  { label: "$3", credits: 250 },
  { label: "$5", credits: 500 },
  { label: "$10", credits: 1000 },
];

type BillingView = "MONTHLY" | "YEARLY";
type AnyRecord = Record<string, unknown>;

type PlanTheme = {
  border: string;
  glow: string;
  badge: string;
  button: string;
  soft: string;
};

const normalizeUpper = (value?: string | null): string => String(value || "").trim().toUpperCase();

const toPlanKey = (planCode?: string | null, billingPeriod?: string | null): string =>
  `${normalizeUpper(planCode)}::${normalizeUpper(billingPeriod)}`;

const formatDateTime = (value?: string | null): string => {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
};

const formatCurrency = (value: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value % 1 === 0 ? 0 : 2,
  }).format(value || 0);

const getPlanUsdPrice = (plan: SubscriptionPlan): number => {
  const direct = Number((plan as any).price_usd || 0);
  if (direct > 0 || Number(plan.price_inr || 0) <= 0) return direct;
  return Number((Number(plan.price_inr || 0) / 83).toFixed(2));
};

const formatCount = (value?: number | null): string => (value || 0).toLocaleString();

const getPlanTheme = (plan: SubscriptionPlan): PlanTheme => {
  const code = normalizeUpper(plan.code);

  if (code.includes("FREE")) {
    return {
      border: "border-white/15",
      glow: "from-white/10 via-slate-400/10 to-white/5",
      badge: "bg-slate-200/10 text-slate-200 border-slate-200/20",
      button: "bg-slate-500/25 hover:bg-slate-500/35 text-white border border-slate-300/15",
      soft: "text-slate-200/80",
    };
  }

  if (code.includes("PRO")) {
    return {
      border: "border-sky-400/35",
      glow: "from-sky-500/30 via-indigo-500/18 to-fuchsia-500/12",
      badge: "bg-sky-400 text-slate-950 border-sky-300/60",
      button: "bg-gradient-to-r from-sky-500 via-indigo-500 to-fuchsia-500 hover:opacity-95 text-white",
      soft: "text-sky-100/90",
    };
  }

  if (code.includes("PREMIUM")) {
    return {
      border: "border-emerald-400/35",
      glow: "from-emerald-500/26 via-teal-500/16 to-cyan-500/10",
      badge: "bg-emerald-400 text-slate-950 border-emerald-300/60",
      button: "bg-gradient-to-r from-emerald-500 to-teal-500 hover:opacity-95 text-white",
      soft: "text-emerald-100/90",
    };
  }

  return {
    border: "border-pink-400/35",
    glow: "from-violet-500/25 via-pink-500/20 to-fuchsia-500/14",
    badge: "bg-pink-400 text-slate-950 border-pink-300/60",
    button: "bg-gradient-to-r from-violet-500 via-fuchsia-500 to-pink-500 hover:opacity-95 text-white",
    soft: "text-pink-100/90",
  };
};

const getPlanTag = (plan: SubscriptionPlan): string => {
  const code = normalizeUpper(plan.code);
  if (code.includes("FREE")) return "Basic";
  if (code.includes("PRO")) return "Popular";
  if (code.includes("PREMIUM")) return "Advanced";
  return "Enterprise";
};

const getPlanSubtitle = (plan: SubscriptionPlan): string => {
  const code = normalizeUpper(plan.code);
  if (code.includes("FREE")) return "Get started";
  if (code.includes("PRO")) return "For serious traders";
  if (code.includes("PREMIUM")) return "For professionals";
  return "For institutions";
};

const getPerText = (plan: SubscriptionPlan): string => {
  const period = normalizeUpper(plan.billing_period);
  if (period === "YEARLY" || period === "ANNUAL") return "per year";
  if (getPlanUsdPrice(plan) <= 0) return "starter access";
  return "per month";
};

const toRecord = (value: unknown): AnyRecord =>
  (value && typeof value === "object" ? value : {}) as AnyRecord;

const getNum = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "" && !Number.isNaN(Number(value))) return Number(value);
  return null;
};

const getBool = (value: unknown): boolean | null => {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value > 0;
  if (typeof value === "string") {
    const v = value.trim().toLowerCase();
    if (["true", "yes", "1", "included", "unlimited"].includes(v)) return true;
    if (["false", "no", "0", "not_included"].includes(v)) return false;
  }
  return null;
};

const getString = (value: unknown): string | null => {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return null;
};

const extractPlanMeta = (plan: SubscriptionPlan) => {
  const p = toRecord(plan);
  const features = toRecord((p as AnyRecord).features);
  const meta = toRecord((p as AnyRecord).metadata);
  const limits = toRecord((p as AnyRecord).limits);

  const pick = (...keys: string[]) => {
    for (const key of keys) {
      if (key in p) return (p as AnyRecord)[key];
      if (key in features) return features[key];
      if (key in meta) return meta[key];
      if (key in limits) return limits[key];
    }
    return undefined;
  };

  return {
    includedCredits: getNum(pick("included_credits", "credits", "monthly_credits")) ?? 0,
    dailyBacktests: getNum(pick("daily_backtests", "backtests_per_day", "daily_backtest_limit")),
    aiRuns: getNum(pick("daily_ai_screener_runs", "ai_screener_runs", "daily_screeners")),
    maxDateRangeDays: getNum(pick("max_date_range_days", "date_range_days")),
    exportResults: getBool(pick("export_results", "exports_enabled")),
    advancedStrategies: getBool(pick("advanced_strategies", "advanced_strategy_access")),
    aiScreenerAccess: getBool(pick("ai_screener_access", "screener_access")),
    prioritySupport: getBool(pick("priority_support")),
    dedicatedManager: getBool(pick("dedicated_account_manager", "dedicated_manager")),
    summary: getString(pick("summary", "tagline", "description")),
  };
};

type CompareRow = {
  label: string;
  values: Record<string, string | boolean>;
};

export default function PricingPage() {
  const [plans, setPlans] = useState<SubscriptionPlansGrouped>(EMPTY_PLANS);
  const [subscription, setSubscription] = useState<ActiveSubscription | null>(null);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [loadingSubscription, setLoadingSubscription] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [plansError, setPlansError] = useState<string | null>(null);
  const [subscriptionError, setSubscriptionError] = useState<string | null>(null);
  const [processingPlanKey, setProcessingPlanKey] = useState<string | null>(null);
  const [billingView, setBillingView] = useState<BillingView>("MONTHLY");
  const router = useRouter();

  const activePlanKey = useMemo(() => {
    if (!subscription) return null;
    return subscription.plan_key || toPlanKey(subscription.plan_code, subscription.billing_period);
  }, [subscription]);

  const displayedPlans = useMemo(() => {
    const freePlans = plans.free || [];
    const paidPlans = billingView === "MONTHLY" ? plans.monthly || [] : plans.yearly || [];

    const all = [...freePlans, ...paidPlans];

    const orderValue = (plan: SubscriptionPlan) => {
      const code = normalizeUpper(plan.code);
      if (code.includes("FREE")) return 0;
      if (code.includes("PRO")) return 1;
      if (code.includes("PREMIUM")) return 2;
      if (code.includes("ULTIMATE")) return 3;
      return 10;
    };

    return [...all].sort((a, b) => orderValue(a) - orderValue(b));
  }, [plans, billingView]);

  const hasAnyPlans = displayedPlans.length > 0;

  const loadPlans = useCallback(async () => {
    setLoadingPlans(true);
    try {
      const plansData = await subscriptionsApi.getPlans();
      setPlans(plansData || EMPTY_PLANS);
      setPlansError(null);
    } catch (error) {
      const message = formatErrorMessage(parseApiError(error)) || "Failed to load plans";
      setPlans(EMPTY_PLANS);
      setPlansError(message);
    } finally {
      setLoadingPlans(false);
    }
  }, []);

  const loadSubscription = useCallback(async () => {
    setLoadingSubscription(true);
    try {
      const subData = await subscriptionsApi.getMySubscription();
      setSubscription(subData || null);
      setSubscriptionError(null);
    } catch (error) {
      const message = formatErrorMessage(parseApiError(error)) || "Failed to load current subscription";
      setSubscription(null);
      setSubscriptionError(message);
    } finally {
      setLoadingSubscription(false);
    }
  }, []);

  const loadData = useCallback(
    async (silent = false) => {
      if (silent) setRefreshing(true);
      await Promise.allSettled([loadPlans(), loadSubscription()]);
      if (silent) setRefreshing(false);
    },
    [loadPlans, loadSubscription],
  );

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const verifySubscriptionPayment = async (
    response: { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string },
  ) => {
    const verified = await subscriptionsApi.verifyPayment({
      order_id: response.razorpay_order_id,
      razorpay_payment_id: response.razorpay_payment_id,
      razorpay_signature: response.razorpay_signature,
    });

    if (!verified?.success) {
      throw new Error(verified?.message || "Subscription payment verification failed");
    }

    toast.success(verified.idempotent ? "Subscription already active" : "Subscription activated successfully");
    await loadData(true);
  };

  const openRazorpayCheckout = (order: SubscriptionCheckoutOrder, plan: SubscriptionPlan): Promise<void> =>
    new Promise((resolve, reject) => {
      const Razorpay = (window as any)?.Razorpay;
      if (!Razorpay) {
        reject(new Error("Razorpay SDK not loaded. Please refresh and try again."));
        return;
      }

      const options = {
        key: order.razorpay_key_id || order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "AlgoAgentX",
        description: `${plan.code} (${plan.billing_period}) Subscription`,
        image: "/images/algoagentx_icon.jpeg",
        order_id: order.order_id,
        handler: async (response: any) => {
          try {
            await verifySubscriptionPayment(response);
            resolve();
          } catch (error) {
            reject(error);
          }
        },
        modal: {
          ondismiss: async () => {
            try {
              await subscriptionsApi.markFailure({
                order_id: order.order_id,
                reason: "checkout_closed_by_user",
              });
            } catch {
              //
            }
            reject(new Error("Checkout cancelled"));
          },
        },
        notes: {
          plan_code: plan.code,
          billing_period: plan.billing_period,
          billing_order_id: order.billing_order_id,
        },
        theme: { color: "#7c3aed" },
      };

      const rzp = new Razorpay(options);
      rzp.on("payment.failed", async (failure: any) => {
        try {
          await subscriptionsApi.markFailure({
            order_id: order.order_id,
            reason: failure?.error?.description || "payment_failed",
            code: failure?.error?.code,
          });
        } catch {
          //
        }
        reject(new Error(failure?.error?.description || "Payment failed"));
      });

      rzp.open();
    });

  const buyPlan = async (plan: SubscriptionPlan) => {
    const planKey = plan.plan_key || toPlanKey(plan.code, plan.billing_period);
    setProcessingPlanKey(planKey);

    try {
      if (getPlanUsdPrice(plan) <= 0) {
        await subscriptionsApi.activateFree({
          plan_code: plan.code,
          billing_period: plan.billing_period,
        });
        toast.success("Free plan activated");
        await loadData(true);
        return;
      }

      router.push(`/billing/checkout?type=subscription&plan=${encodeURIComponent(plan.code)}&period=${encodeURIComponent(plan.billing_period)}`);
    } catch (error) {
      const parsed = parseApiError(error);
      const message = formatErrorMessage(parsed);

      if (message && message.toLowerCase() !== "checkout cancelled") {
        toast.error(message);
      }
    } finally {
      setProcessingPlanKey(null);
    }
  };

  const comparisonRows = useMemo<CompareRow[]>(() => {
    const plansToCompare = displayedPlans;

    const rows: CompareRow[] = [
      {
        label: "Included Credits",
        values: Object.fromEntries(
          plansToCompare.map((plan) => [
            toPlanKey(plan.code, plan.billing_period),
            formatCount(extractPlanMeta(plan).includedCredits),
          ]),
        ),
      },
    ];

    const maybeAddNumericRow = (label: string, selector: (plan: SubscriptionPlan) => number | null, unlimitedText = "Unlimited") => {
      const hasAny = plansToCompare.some((plan) => selector(plan) !== null);
      if (!hasAny) return;

      rows.push({
        label,
        values: Object.fromEntries(
          plansToCompare.map((plan) => {
            const value = selector(plan);
            return [
              toPlanKey(plan.code, plan.billing_period),
              value === null ? "—" : value >= 999999 ? unlimitedText : String(value),
            ];
          }),
        ),
      });
    };

    const maybeAddBoolRow = (label: string, selector: (plan: SubscriptionPlan) => boolean | null) => {
      const hasAny = plansToCompare.some((plan) => selector(plan) !== null);
      if (!hasAny) return;

      rows.push({
        label,
        values: Object.fromEntries(
          plansToCompare.map((plan) => [
            toPlanKey(plan.code, plan.billing_period),
            selector(plan) ?? false,
          ]),
        ),
      });
    };

    maybeAddNumericRow("Daily Backtests", (plan) => extractPlanMeta(plan).dailyBacktests);
    maybeAddNumericRow("Daily AI Screener Runs", (plan) => extractPlanMeta(plan).aiRuns);
    maybeAddNumericRow("Max Date Range", (plan) => extractPlanMeta(plan).maxDateRangeDays, "Unlimited");
    maybeAddBoolRow("Export Results", (plan) => extractPlanMeta(plan).exportResults);
    maybeAddBoolRow("Advanced Strategies", (plan) => extractPlanMeta(plan).advancedStrategies);
    maybeAddBoolRow("AI Screener Access", (plan) => extractPlanMeta(plan).aiScreenerAccess);
    maybeAddBoolRow("Priority Support", (plan) => extractPlanMeta(plan).prioritySupport);
    maybeAddBoolRow("Dedicated Account Manager", (plan) => extractPlanMeta(plan).dedicatedManager);

    return rows;
  }, [displayedPlans]);

  const renderComparisonCell = (value: string | boolean) => {
    if (typeof value === "boolean") {
      return value ? (
        <Check className="mx-auto h-4 w-4 text-emerald-400" />
      ) : (
        <X className="mx-auto h-4 w-4 text-rose-400" />
      );
    }

    const isUnlimited = value.toLowerCase() === "unlimited";
    return <span className={isUnlimited ? "font-semibold text-emerald-300" : "text-muted-foreground"}>{value}</span>;
  };

  const renderPlanCard = (plan: SubscriptionPlan) => {
    const key = plan.plan_key || toPlanKey(plan.code, plan.billing_period);
    const theme = getPlanTheme(plan);
    const liveState = normalizeUpper(subscription?.billing_state || subscription?.lifecycle_state || subscription?.status);
    const isLive = liveState === "ACTIVE" || liveState === "TRIAL";
    const isActive = activePlanKey === key && isLive;
    const isProcessing = processingPlanKey === key;
    const meta = extractPlanMeta(plan);

    const ctaLabel =
      getPlanUsdPrice(plan) <= 0
        ? "Start Free Trial"
        : `Buy ${normalizeUpper(plan.billing_period) === "YEARLY" ? "Yearly" : "Monthly"}`;

    return (
      <Card
        key={key}
        className={`overflow-hidden rounded-2xl border ${theme.border} bg-card/40 shadow-2xl backdrop-blur-xl`}
      >
        <div className={`bg-gradient-to-r ${theme.glow} px-5 py-4`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-2xl font-bold text-white">{plan.code}</p>
              <p className={`text-xs ${theme.soft}`}>{meta.summary || getPlanSubtitle(plan)}</p>
            </div>
            <Badge className={`${theme.badge} rounded-full px-2.5 py-0.5 text-[10px] font-semibold`}>
              {isActive ? "Active" : getPlanTag(plan)}
            </Badge>
          </div>
        </div>

        <CardContent className="space-y-4 p-5">
          <div>
            <div className="text-5xl font-bold tracking-tight text-white">{formatCurrency(getPlanUsdPrice(plan))}</div>
            <p className="mt-1 text-sm text-muted-foreground">{getPerText(plan)}</p>
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between gap-4 text-muted-foreground">
              <span>Included Credits</span>
              <span className="font-semibold text-white">{formatCount(meta.includedCredits)} credits</span>
            </div>

            {meta.dailyBacktests !== null && (
              <div className="flex items-center justify-between gap-4 text-muted-foreground">
                <span>Daily Backtests</span>
                <span className="font-semibold text-white">
                  {meta.dailyBacktests >= 999999 ? "Unlimited" : meta.dailyBacktests}
                </span>
              </div>
            )}

            {meta.aiRuns !== null && (
              <div className="flex items-center justify-between gap-4 text-muted-foreground">
                <span>Daily AI Screener Runs</span>
                <span className="font-semibold text-white">
                  {meta.aiRuns >= 999999 ? "Unlimited" : meta.aiRuns}
                </span>
              </div>
            )}

            {meta.prioritySupport !== null && (
              <div className="flex items-center justify-between gap-4 text-muted-foreground">
                <span>Priority Support</span>
                <span className="font-semibold text-white">{meta.prioritySupport ? "Included" : "—"}</span>
              </div>
            )}
          </div>

          <Button
            type="button"
            onClick={() => void buyPlan(plan)}
            disabled={isProcessing || isActive || !!plansError}
            className={`w-full rounded-xl ${theme.button}`}
          >
            {isProcessing ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : isActive ? (
              <>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Current Plan
              </>
            ) : (
              <>
                <CreditCard className="mr-2 h-4 w-4" />
                {ctaLabel}
              </>
            )}
          </Button>

          <Button
            asChild
            variant="outline"
            className="w-full rounded-xl border-white/10 bg-black/15 text-white hover:bg-white/10"
          >
            <Link href="/credits">Continue with Credits</Link>
          </Button>
        </CardContent>
      </Card>
    );
  };

  return (
    <RazorpayScript>
      <div className="space-y-6">
        <header className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">Pricing</h1>
          <p className="text-sm text-muted-foreground">Manage your trading workspace</p>
        </header>

        <section className="rounded-2xl border border-border/50 bg-card/30 p-5 shadow-xl backdrop-blur-xl">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold text-white">USD Pricing &amp; Subscriptions</h2>
              <p className="mt-1 text-sm text-white/85">
                Choose a plan with recurring included credits. If included credits are exhausted, wallet credits are used.
              </p>
              <p className="mt-1 text-xs text-white/75">
                Final usage order: subscription included credits → wallet credits → block with upgrade/top-up CTA.
              </p>
            </div>

            <Button
              variant="outline"
              onClick={() => void loadData(true)}
              disabled={refreshing}
              className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40"
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>

          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              onClick={() => setBillingView("MONTHLY")}
              className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                billingView === "MONTHLY"
                  ? "bg-white text-slate-900"
                  : "bg-white/10 text-white hover:bg-white/20"
              }`}
            >
              Monthly
            </button>
            <button
              type="button"
              onClick={() => setBillingView("YEARLY")}
              className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                billingView === "YEARLY"
                  ? "bg-white text-slate-900"
                  : "bg-white/10 text-white hover:bg-white/20"
              }`}
            >
              Yearly
            </button>
          </div>

          <div className="mt-5 rounded-2xl border border-border/50 bg-card/20 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-xl font-semibold text-white">Current Subscription</h3>
                <p className="text-sm text-muted-foreground">Your active plan and refill status</p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button asChild variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">
                  <Link href="/credits">Top-up Wallet Credits</Link>
                </Button>
                <Button asChild variant="outline" className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">
                  <Link href="/backtest">Run Backtest</Link>
                </Button>
              </div>
            </div>

            {loadingSubscription ? (
              <div className="mt-4 rounded-xl border border-border/40 bg-card/20 p-4 text-sm text-muted-foreground">
                Loading current subscription...
              </div>
            ) : subscriptionError ? (
              <div className="mt-4 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
                {subscriptionError}
              </div>
            ) : !subscription ? (
              <div className="mt-4 rounded-xl border border-border/40 bg-card/20 p-4 text-sm text-muted-foreground">
                No active subscription found. You can start with FREE plan or buy a paid plan.
              </div>
            ) : (
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                  <p className="text-xs text-muted-foreground">Plan</p>
                  <p className="mt-1 text-lg font-semibold text-white">
                    {subscription.plan_code} ({subscription.billing_period})
                  </p>
                </div>
                <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                  <p className="text-xs text-muted-foreground">Status</p>
                  <p className="mt-1 text-lg font-semibold text-white">
                    {subscription.billing_state || subscription.lifecycle_state || subscription.status || "—"}
                  </p>
                </div>
                <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                  <p className="text-xs text-muted-foreground">Included Credits</p>
                  <p className="mt-1 text-lg font-semibold text-white">
                    {formatCount(subscription.included_credits_remaining)} / {formatCount(subscription.included_credits_total)}
                  </p>
                </div>
                <div className="rounded-xl border border-border/50 bg-card/20 p-4">
                  <p className="text-xs text-muted-foreground">Next Refill / Reset</p>
                  <p className="mt-1 text-sm font-medium text-white">
                    {formatDateTime(subscription.next_refill_reset_at || subscription.next_credit_refill_at)}
                  </p>
                </div>
              </div>
            )}
          </div>
        </section>

        {plansError && (
          <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-100">
            <div className="flex items-start gap-3">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-medium">Pricing plans could not be loaded.</p>
                <p className="mt-1 text-rose-100/90">{plansError}</p>
              </div>
            </div>
          </div>
        )}

        {loadingPlans ? (
          <div className="rounded-2xl border border-border/50 bg-card/30 p-8 text-sm text-muted-foreground">
            Loading plans...
          </div>
        ) : hasAnyPlans ? (
          <>
            <section className="grid grid-cols-1 gap-4 xl:grid-cols-4">
              {displayedPlans.map(renderPlanCard)}
            </section>

            {comparisonRows.length > 1 && (
              <Card className="rounded-2xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
                <CardHeader>
                  <CardTitle className="text-white">Feature Comparison</CardTitle>
                  <CardDescription className="text-muted-foreground">
                    Compare all features across your plans
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="responsive-table-wrapper overflow-x-auto">
                    <table className="min-w-full border-separate border-spacing-0 text-sm">
                      <thead>
                        <tr className="text-muted-foreground">
                          <th className="border-b border-white/10 px-4 py-3 text-left font-medium">Features</th>
                          {displayedPlans.map((plan) => (
                            <th key={toPlanKey(plan.code, plan.billing_period)} className="border-b border-white/10 px-4 py-3 text-center font-medium">
                              {plan.code}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {comparisonRows.map((row) => (
                          <tr key={row.label}>
                            <td className="border-b border-white/5 px-4 py-3 font-medium text-white">{row.label}</td>
                            {displayedPlans.map((plan) => (
                              <td
                                key={`${row.label}-${toPlanKey(plan.code, plan.billing_period)}`}
                                className="border-b border-white/5 px-4 py-3 text-center"
                              >
                                {renderComparisonCell(row.values[toPlanKey(plan.code, plan.billing_period)] ?? "—")}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            <Card className="rounded-2xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="text-white">Credit-Only Option</CardTitle>
                <CardDescription className="text-muted-foreground">
                  Prefer to pay per usage? Buy credits and pay only for what you use.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                  {CREDIT_PACKS.map((pack) => (
                    <div key={pack.label} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                      <div className="text-center">
                        <p className="text-4xl font-bold text-white">{pack.label}</p>
                        <p className="mt-2 text-sm text-muted-foreground">{pack.credits} Credits</p>
                      </div>
                      <Button asChild className="mt-5 w-full rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
                        <Link href="/credits">
                          Buy Now
                          <ArrowRight className="ml-2 h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </>
        ) : (
          <div className="rounded-2xl border border-border/50 bg-card/30 p-8 text-sm text-muted-foreground">
            No plans are currently available. Please try refreshing.
          </div>
        )}
      </div>
    </RazorpayScript>
  );
}