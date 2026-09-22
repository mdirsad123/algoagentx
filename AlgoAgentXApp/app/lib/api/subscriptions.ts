import axiosInstance from "../axios";

const unwrap = <T>(payload: any): T => (payload?.success ? payload.data : payload);

const normalizeUpper = (value?: string | null): string => String(value || "").trim().toUpperCase();

const toPlanKey = (planCode?: string | null, billingPeriod?: string | null): string =>
  `${normalizeUpper(planCode)}::${normalizeUpper(billingPeriod)}`;

export interface SubscriptionPlan {
  id: string;
  code: string;
  billing_period: string;
  price_usd?: number;
  price_inr: number;
  included_credits: number;
  features: Record<string, any>;
  is_active: boolean;
  plan_key?: string;
}

export interface SubscriptionPlansGrouped {
  free?: SubscriptionPlan[];
  monthly: SubscriptionPlan[];
  yearly: SubscriptionPlan[];
}

export interface ActiveSubscription {
  id: string;
  user_id: string;
  plan_id: string;
  plan_code: string;
  billing_period: string;
  plan_key?: string;
  price_usd?: number;
  price_inr: number;
  status: string;
  billing_state: string;
  lifecycle_state?: string;
  start_at: string;
  end_at: string;
  renews: boolean;
  included_credits_total: number;
  included_credits_remaining: number;
  next_credit_refill_at?: string | null;
  next_refill_reset_at?: string | null;
  last_credit_refill_at?: string | null;
  created_at: string;
}

export interface SubscriptionCheckoutOrder {
  order_id: string;
  billing_order_id: string;
  payment_record_id: string;
  amount: number;
  amount_inr: number;
  currency: string;
  key_id: string;
  razorpay_key_id: string;
  status: string;
  plan: {
    id: string;
    code: string;
    billing_period: string;
    price_usd?: number;
    price_inr: number;
    included_credits: number;
  };
}

export interface SubscriptionVerifyResult {
  success: boolean;
  payment_id: string;
  order_id: string;
  billing_order_id?: string;
  status: string;
  idempotent: boolean;
  subscription: ActiveSubscription;
  message: string;
}

export const subscriptionsApi = {
  getPlans: async (): Promise<SubscriptionPlansGrouped> => {
    const response = await axiosInstance.get("/api/v1/subscriptions/plans");
    const grouped = unwrap<SubscriptionPlansGrouped>(response.data) || { monthly: [], yearly: [] };
    const normalizePlan = (plan: SubscriptionPlan): SubscriptionPlan => {
      const code = normalizeUpper(plan?.code);
      const billingPeriod = normalizeUpper(plan?.billing_period);
      return {
        ...plan,
        code,
        billing_period: billingPeriod,
        plan_key: plan?.plan_key || toPlanKey(code, billingPeriod),
      };
    };

    return {
      free: Array.isArray(grouped.free) ? grouped.free.map(normalizePlan) : [],
      monthly: Array.isArray(grouped.monthly) ? grouped.monthly.map(normalizePlan) : [],
      yearly: Array.isArray(grouped.yearly) ? grouped.yearly.map(normalizePlan) : [],
    };
  },

  getMySubscription: async (): Promise<ActiveSubscription | null> => {
    const response = await axiosInstance.get("/api/v1/subscriptions/me");
    const sub = unwrap<ActiveSubscription | null>(response.data);
    if (!sub) return null;
    const planCode = normalizeUpper(sub.plan_code);
    const billingPeriod = normalizeUpper(sub.billing_period);
    return {
      ...sub,
      plan_code: planCode,
      billing_period: billingPeriod,
      plan_key: sub.plan_key || toPlanKey(planCode, billingPeriod),
      status: normalizeUpper(sub.status),
      billing_state: normalizeUpper(sub.billing_state),
      lifecycle_state: normalizeUpper(sub.lifecycle_state),
    };
  },

  createOrder: async (payload: { plan_code: string; billing_period: string }): Promise<SubscriptionCheckoutOrder> => {
    const response = await axiosInstance.post("/api/v1/subscriptions/razorpay/create-order", payload);
    return unwrap<SubscriptionCheckoutOrder>(response.data);
  },

  verifyPayment: async (payload: {
    order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }): Promise<SubscriptionVerifyResult> => {
    const response = await axiosInstance.post("/api/v1/subscriptions/razorpay/verify", payload);
    return unwrap<SubscriptionVerifyResult>(response.data);
  },

  markFailure: async (payload: { order_id: string; reason?: string; code?: string }) => {
    const response = await axiosInstance.post("/api/v1/subscriptions/razorpay/failure", payload);
    return unwrap<any>(response.data);
  },

  activateFree: async (payload: { plan_code: string; billing_period: string }) => {
    const response = await axiosInstance.post("/api/v1/subscriptions/upgrade", payload);
    return unwrap<any>(response.data);
  },
};
