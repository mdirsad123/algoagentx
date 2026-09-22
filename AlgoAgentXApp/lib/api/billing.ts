import axiosInstance from "../axios";

const unwrap = <T>(payload: any): T => (payload?.success ? payload.data : payload);

export type PaymentMethod = "RAZORPAY_UPI" | "CARD" | "CRYPTO";
export type PurchaseType = "SUBSCRIPTION" | "CREDITS";

export interface BillingPublicSettings {
  base_currency: "USD";
  inr_conversion_rate: number;
  gst_percent: number;
  payment_methods: {
    razorpay_upi: boolean;
    card: boolean;
    crypto: boolean;
  };
}

export interface CheckoutPreviewRequest {
  purchase_type: PurchaseType;
  plan_code?: string;
  billing_period?: string;
  credit_amount?: number;
  pack_code?: string;
  coupon_code?: string | null;
  payment_method: PaymentMethod;
}


export interface CheckoutCreateOrderResponse {
  order_id: string;
  payment_record_id?: string;
  purchase_type: PurchaseType;
  payment_method: PaymentMethod;
  provider: "RAZORPAY" | "CARD_PROVIDER" | "CRYPTO" | string;
  razorpay_order_id?: string;
  currency: "USD" | "INR";
  amount: number;
  amount_paise?: number;
  key_id?: string;
  razorpay_key_id?: string;
  status?: string;
  message?: string;
  checkout?: { key_id?: string; name?: string; description?: string };
  preview?: CheckoutPreviewResponse;
}

export interface RazorpayVerifyPayload {
  order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface CheckoutPreviewResponse {
  valid: boolean;
  message: string;
  purchase_type: PurchaseType;
  plan_code?: string | null;
  billing_period?: string | null;
  credit_amount?: number | null;
  pack_code?: string | null;
  pack_title?: string | null;
  base_credits?: number | null;
  bonus_credits?: number | null;
  pack?: {
    code: string;
    title: string;
    credits: number;
    bonus_credits: number;
    total_credits: number;
    price_usd: number;
    is_popular?: boolean;
    description?: string | null;
  } | null;
  plan?: {
    id: string;
    code: string;
    billing_period: string;
    included_credits: number;
    price_usd: number;
    features?: Record<string, any>;
  } | null;
  base_currency: "USD";
  subtotal_usd: number;
  coupon_code?: string | null;
  discount_usd: number;
  tax_usd: number;
  final_usd: number;
  payment_method: PaymentMethod;
  inr_conversion_rate?: number;
  gst_percent?: number;
  gst_inr?: number;
  final_inr?: number | null;
  payment_currency: "USD" | "INR";
  payment_amount: number;
  payment_methods?: BillingPublicSettings["payment_methods"];
}

export const billingApi = {
  getPublicSettings: async (): Promise<BillingPublicSettings> => {
    const response = await axiosInstance.get("/api/v1/billing/settings/public");
    return unwrap<BillingPublicSettings>(response.data);
  },

  previewCheckout: async (payload: CheckoutPreviewRequest): Promise<CheckoutPreviewResponse> => {
    const response = await axiosInstance.post("/api/v1/billing/checkout/preview", payload);
    return unwrap<CheckoutPreviewResponse>(response.data);
  },

  createCheckoutOrder: async (payload: CheckoutPreviewRequest): Promise<CheckoutCreateOrderResponse> => {
    const response = await axiosInstance.post("/api/v1/billing/checkout/create-order", payload);
    return unwrap<CheckoutCreateOrderResponse>(response.data);
  },

  verifyRazorpayCheckout: async (purchaseType: PurchaseType, payload: RazorpayVerifyPayload): Promise<any> => {
    const path = purchaseType === "SUBSCRIPTION" ? "/api/v1/subscriptions/razorpay/verify" : "/api/v1/payments/razorpay/verify";
    const response = await axiosInstance.post(path, payload);
    return unwrap<any>(response.data);
  },

  markRazorpayFailure: async (purchaseType: PurchaseType, payload: { order_id: string; reason?: string; code?: string }): Promise<any> => {
    const path = purchaseType === "SUBSCRIPTION" ? "/api/v1/subscriptions/razorpay/failure" : "/api/v1/payments/razorpay/failure";
    const response = await axiosInstance.post(path, payload);
    return unwrap<any>(response.data);
  },
};
