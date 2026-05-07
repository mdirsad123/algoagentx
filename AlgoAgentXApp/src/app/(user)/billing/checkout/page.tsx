"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, BadgePercent, CreditCard, Coins, Loader2, ShieldCheck, Wallet } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { billingApi, type BillingPublicSettings, type CheckoutPreviewResponse, type PaymentMethod, type PurchaseType } from "@/lib/api/billing";

const METHOD_LABEL: Record<PaymentMethod, string> = {
  RAZORPAY_UPI: "Razorpay UPI",
  CARD: "Card",
  CRYPTO: "Crypto",
};

const METHOD_HELP: Record<PaymentMethod, string> = {
  RAZORPAY_UPI: "Pay in INR using UPI. Razorpay checkout opens after order creation.",
  CARD: "Pay in USD by card. Provider placeholder creates a pending order.",
  CRYPTO: "Pay in USD-equivalent crypto. Invoice placeholder creates a pending order.",
};

const formatUsd = (value?: number | null) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(Number(value || 0));

const formatInr = (value?: number | null) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value || 0));

declare global {
  interface Window {
    Razorpay?: any;
  }
}

const loadRazorpayScript = () =>
  new Promise<boolean>((resolve) => {
    if (typeof window === "undefined") return resolve(false);
    if (window.Razorpay) return resolve(true);
    const existing = document.querySelector<HTMLScriptElement>("script[src='https://checkout.razorpay.com/v1/checkout.js']");
    if (existing) {
      existing.addEventListener("load", () => resolve(true), { once: true });
      existing.addEventListener("error", () => resolve(false), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });

const normalizeUpper = (value?: string | null) => String(value || "").trim().toUpperCase();

function getEnabledMethods(settings: BillingPublicSettings | null): PaymentMethod[] {
  const enabled = settings?.payment_methods || { razorpay_upi: true, card: true, crypto: true };
  const methods: PaymentMethod[] = [];
  if (enabled.razorpay_upi) methods.push("RAZORPAY_UPI");
  if (enabled.card) methods.push("CARD");
  if (enabled.crypto) methods.push("CRYPTO");
  return methods.length ? methods : ["RAZORPAY_UPI"];
}

function BillingCheckoutContent() {
  const router = useRouter();
  const params = useSearchParams();

  const purchaseType: PurchaseType = normalizeUpper(params.get("type")) === "CREDITS" ? "CREDITS" : "SUBSCRIPTION";
  const planCode = normalizeUpper(params.get("plan"));
  const billingPeriod = normalizeUpper(params.get("period")) || "MONTHLY";
  const creditAmount = Number(params.get("credits") || 0);

  const [settings, setSettings] = useState<BillingPublicSettings | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("RAZORPAY_UPI");
  const [couponInput, setCouponInput] = useState("");
  const [appliedCoupon, setAppliedCoupon] = useState<string | null>(null);
  const [preview, setPreview] = useState<CheckoutPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [previewing, setPreviewing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [orderResult, setOrderResult] = useState<any>(null);
  const [couponMessage, setCouponMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const enabledMethods = useMemo(() => getEnabledMethods(settings), [settings]);

  const buildPayload = useCallback(
    (coupon?: string | null, method: PaymentMethod = paymentMethod) => ({
      purchase_type: purchaseType,
      plan_code: purchaseType === "SUBSCRIPTION" ? planCode : undefined,
      billing_period: purchaseType === "SUBSCRIPTION" ? billingPeriod : undefined,
      credit_amount: purchaseType === "CREDITS" ? creditAmount : undefined,
      coupon_code: coupon || undefined,
      payment_method: method,
    }),
    [billingPeriod, creditAmount, paymentMethod, planCode, purchaseType],
  );

  const loadPreview = useCallback(
    async (coupon?: string | null, method: PaymentMethod = paymentMethod, silent = false) => {
      if (purchaseType === "SUBSCRIPTION" && (!planCode || !billingPeriod)) {
        setError("Missing plan details. Please go back to pricing and choose a plan.");
        setLoading(false);
        return;
      }
      if (purchaseType === "CREDITS" && (!creditAmount || creditAmount <= 0)) {
        setError("Missing credit amount. Please go back to credits and choose a pack.");
        setLoading(false);
        return;
      }

      if (!silent) setPreviewing(true);
      try {
        const result = await billingApi.previewCheckout(buildPayload(coupon, method));
        setPreview(result);
        setError(null);
        if (coupon) {
          setCouponMessage(result.message || (result.valid ? "Coupon applied" : "Coupon is not valid"));
          if (result.valid) setAppliedCoupon(coupon);
        }
      } catch (err: any) {
        setError(err?.message || "Failed to preview checkout");
        if (coupon) setCouponMessage(err?.message || "Coupon is not valid");
      } finally {
        setLoading(false);
        setPreviewing(false);
      }
    },
    [billingPeriod, buildPayload, creditAmount, paymentMethod, planCode, purchaseType],
  );

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const config = await billingApi.getPublicSettings();
        if (!mounted) return;
        setSettings(config);
        const methods = getEnabledMethods(config);
        const defaultMethod = methods.includes("RAZORPAY_UPI") ? "RAZORPAY_UPI" : methods[0];
        setPaymentMethod(defaultMethod);
        await loadPreview(null, defaultMethod, true);
      } catch (err: any) {
        if (!mounted) return;
        setError(err?.message || "Failed to load billing settings");
        setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [loadPreview]);

  const onMethodChange = async (method: PaymentMethod) => {
    setPaymentMethod(method);
    await loadPreview(appliedCoupon, method, true);
  };

  const applyCoupon = async () => {
    const code = couponInput.trim().toUpperCase();
    if (!code) {
      setCouponMessage("Enter a coupon code first.");
      return;
    }
    await loadPreview(code, paymentMethod);
  };

  const removeCoupon = async () => {
    setAppliedCoupon(null);
    setCouponInput("");
    setCouponMessage(null);
    await loadPreview(null, paymentMethod, true);
  };

  const continueToPayment = async () => {
    setCreating(true);
    setOrderResult(null);
    setError(null);
    try {
      const order = await billingApi.createCheckoutOrder(buildPayload(appliedCoupon, paymentMethod));
      setOrderResult(order);

      if (order.payment_method !== "RAZORPAY_UPI") {
        toast.info(order.message || "Pending order created");
        return;
      }

      const loaded = await loadRazorpayScript();
      if (!loaded || !window.Razorpay) {
        throw new Error("Unable to load Razorpay checkout script");
      }

      const razorpayOrderId = order.razorpay_order_id;
      if (!razorpayOrderId) throw new Error("Razorpay order id missing");

      const rz = new window.Razorpay({
        key: order.razorpay_key_id || order.key_id || order.checkout?.key_id,
        amount: order.amount_paise,
        currency: order.currency || "INR",
        name: order.checkout?.name || "AlgoAgentX",
        description: order.checkout?.description || title,
        order_id: razorpayOrderId,
        handler: async (response: { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) => {
          try {
            await billingApi.verifyRazorpayCheckout(purchaseType, {
              order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            toast.success(purchaseType === "SUBSCRIPTION" ? "Subscription activated successfully" : "Credits added successfully");
            router.push(purchaseType === "SUBSCRIPTION" ? "/pricing" : "/credits");
          } catch (err: any) {
            toast.error(err?.response?.data?.detail || err?.message || "Payment verification failed");
          }
        },
        modal: {
          ondismiss: async () => {
            try {
              await billingApi.markRazorpayFailure(purchaseType, { order_id: razorpayOrderId, reason: "checkout_dismissed" });
            } catch { }
          },
        },
        theme: { color: "#7c3aed" },
      });
      rz.open();
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Unable to continue to payment";
      setError(message);
      toast.error(message);
    } finally {
      setCreating(false);
    }
  };

  const title = purchaseType === "SUBSCRIPTION" ? `${preview?.plan_code || planCode} Plan` : `${preview?.credit_amount || creditAmount} Credits`;
  const subtitle = purchaseType === "SUBSCRIPTION" ? `${preview?.billing_period || billingPeriod} billing` : "One-time credit top-up";

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-purple-100">
        <Loader2 className="mr-3 h-6 w-6 animate-spin" /> Loading checkout preview...
      </div>
    );
  }

  return (
    <div className="space-y-6 p-1 md:p-2">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <button onClick={() => router.back()} className="mb-3 inline-flex items-center gap-2 text-sm text-purple-100/70 hover:text-white">
            <ArrowLeft className="h-4 w-4" /> Back
          </button>
          <h1 className="text-3xl font-bold text-lime-400">Billing Checkout</h1>
          <p className="mt-1 text-purple-100/75">Review your order, apply coupon, and choose payment method before payment.</p>
        </div>
        <div className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-200">
          Base currency: USD
        </div>
      </div>

      {error && <div className="rounded-2xl border border-rose-400/40 bg-rose-500/10 p-4 text-rose-100">{error}</div>}

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-6">
          <Card className="rounded-2xl border-white/15 bg-gradient-to-br from-white/10 to-purple-500/10 shadow-2xl backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white"><Wallet className="h-5 w-5 text-purple-300" /> Purchase Summary</CardTitle>
              <CardDescription className="text-purple-100/65">Backend-calculated summary. Frontend URL prices are never trusted.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-white/10 bg-black/15 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-purple-100/50">Item</p>
                <p className="mt-2 text-2xl font-bold text-white">{title}</p>
                <p className="text-sm text-purple-100/60">{subtitle}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/15 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-purple-100/50">Included</p>
                <p className="mt-2 text-2xl font-bold text-white">
                  {purchaseType === "SUBSCRIPTION" ? `${(preview?.plan?.included_credits || 0).toLocaleString()} credits` : `${(preview?.credit_amount || creditAmount).toLocaleString()} credits`}
                </p>
                <p className="text-sm text-purple-100/60">{purchaseType === "SUBSCRIPTION" ? "Plan credits" : "Wallet top-up"}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-white/15 bg-gradient-to-br from-white/10 to-fuchsia-500/10 shadow-2xl backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white"><BadgePercent className="h-5 w-5 text-pink-300" /> Coupon</CardTitle>
              <CardDescription className="text-purple-100/65">Apply a checkout coupon created in Coupon Master.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-col gap-3 md:flex-row">
                <Input
                  value={couponInput}
                  onChange={(e) => setCouponInput(e.target.value.toUpperCase())}
                  placeholder="Enter coupon code"
                  className="border-white/15 bg-white/10 text-white placeholder:text-purple-100/45"
                  disabled={previewing}
                />
                <Button onClick={applyCoupon} disabled={previewing} className="bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">
                  {previewing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Apply
                </Button>
                {appliedCoupon && (
                  <Button variant="outline" onClick={removeCoupon} className="border-white/20 text-purple-100 hover:bg-white/10">
                    Remove
                  </Button>
                )}
              </div>
              {couponMessage && (
                <p className={`text-sm ${preview?.valid === false ? "text-rose-200" : "text-emerald-200"}`}>{couponMessage}</p>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-white/15 bg-gradient-to-br from-white/10 to-blue-500/10 shadow-2xl backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white"><CreditCard className="h-5 w-5 text-sky-300" /> Payment Method</CardTitle>
              <CardDescription className="text-purple-100/65">Only enabled methods from admin billing settings are shown.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-3">
              {enabledMethods.map((method) => (
                <button
                  key={method}
                  onClick={() => onMethodChange(method)}
                  className={`rounded-2xl border p-4 text-left transition ${paymentMethod === method ? "border-sky-300 bg-sky-500/20 shadow-lg shadow-sky-500/15" : "border-white/15 bg-white/5 hover:bg-white/10"}`}
                >
                  <p className="font-semibold text-white">{METHOD_LABEL[method]}</p>
                  <p className="mt-1 text-xs text-purple-100/60">{METHOD_HELP[method]}</p>
                </button>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="sticky top-6 rounded-2xl border-white/15 bg-gradient-to-br from-purple-950/70 via-indigo-950/70 to-slate-950/80 shadow-2xl backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white"><ShieldCheck className="h-5 w-5 text-emerald-300" /> Order Summary</CardTitle>
              <CardDescription className="text-purple-100/65">Preview only. No subscription activation or credits addition happens here.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3 rounded-xl border border-white/10 bg-black/15 p-4">
                <div className="flex justify-between text-sm"><span className="text-purple-100/65">Subtotal</span><span className="font-semibold text-white">{formatUsd(preview?.subtotal_usd)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-purple-100/65">Coupon discount</span><span className="font-semibold text-emerald-300">-{formatUsd(preview?.discount_usd)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-purple-100/65">Final USD</span><span className="font-semibold text-white">{formatUsd(preview?.final_usd)}</span></div>
                {paymentMethod === "RAZORPAY_UPI" && (
                  <>
                    <div className="border-t border-white/10 pt-3" />
                    <div className="flex justify-between text-sm"><span className="text-purple-100/65">Conversion rate</span><span className="font-semibold text-white">1 USD = ₹{preview?.inr_conversion_rate || settings?.inr_conversion_rate || 83}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-purple-100/65">GST ({preview?.gst_percent || settings?.gst_percent || 18}%)</span><span className="font-semibold text-white">{formatInr(preview?.gst_inr)}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-purple-100/65">Final INR</span><span className="font-semibold text-white">{formatInr(preview?.final_inr)}</span></div>
                  </>
                )}
              </div>

              <div className="rounded-2xl border border-emerald-400/25 bg-emerald-500/10 p-4">
                <p className="text-sm text-emerald-100/75">Final payable amount</p>
                <p className="mt-1 text-4xl font-bold text-white">
                  {preview?.payment_currency === "INR" ? formatInr(preview?.payment_amount) : formatUsd(preview?.payment_amount)}
                </p>
                <p className="mt-1 text-xs text-emerald-100/60">Payment currency: {preview?.payment_currency || "USD"}</p>
              </div>

              {orderResult && orderResult.payment_method !== "RAZORPAY_UPI" && (
                <div className="rounded-2xl border border-amber-300/30 bg-amber-500/10 p-4 text-amber-100">
                  <p className="font-semibold">{orderResult.payment_method === "CARD" ? "Card payment is coming soon" : "Crypto invoice pending"}</p>
                  <p className="mt-1 text-sm text-amber-100/75">{orderResult.message}</p>
                  <p className="mt-2 font-mono text-xs text-amber-100/60">Order ID: {orderResult.order_id}</p>
                  <p className="mt-1 text-sm">Amount: {formatUsd(orderResult.amount)}</p>
                  <p className="text-xs text-amber-100/60">Status: {orderResult.status || "PENDING"}</p>
                </div>
              )}

              <Button disabled={creating || previewing} onClick={continueToPayment} className="w-full bg-gradient-to-r from-emerald-500 via-cyan-500 to-blue-500 py-6 text-base font-bold text-white">
                {creating ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Coins className="mr-2 h-5 w-5" />} Continue to Payment
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}


export default function BillingCheckoutPage() {
  return (
    <Suspense fallback={<div className="flex min-h-[50vh] items-center justify-center text-purple-100">Loading checkout...</div>}>
      <BillingCheckoutContent />
    </Suspense>
  );
}
