"use client";

import axiosInstance from "./axios";

const unwrapApiData = (payload: any) => (payload?.success ? payload.data : payload);

const getDetail = (error: any) =>
  error?.response?.data?.detail || error?.message || "Payment request failed";

export interface CreateOrderRequest {
  pack_code?: string;
  credits_to_buy?: number;
}

export interface CreateOrderResponse {
  order_id: string;
  billing_order_id: string;
  payment_record_id: string;
  credits: number;
  amount: number;
  amount_inr: number;
  currency: string;
  razorpay_key_id: string;
  key_id?: string;
  status: string;
}

export interface VerifyPaymentRequest {
  order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface VerifyPaymentResponse {
  success: boolean;
  payment_id: string;
  order_id: string;
  billing_order_id?: string;
  credits_granted: number;
  balance: number;
  status: string;
  idempotent?: boolean;
  message: string;
}

export interface CreateSubscriptionRequest {
  plan_code: string;
  billing_period: string;
}

export interface CreateSubscriptionResponse {
  order_id: string;
  billing_order_id: string;
  payment_record_id: string;
  amount: number;
  amount_inr: number;
  currency: string;
  razorpay_key_id: string;
  key_id?: string;
  status: string;
  plan: {
    id: string;
    code: string;
    billing_period: string;
    price_inr: number;
    included_credits: number;
  };
}

export async function createOrder(request: CreateOrderRequest): Promise<CreateOrderResponse> {
  try {
    const response = await axiosInstance.post("/api/v1/payments/razorpay/create-order", request);
    return unwrapApiData(response.data);
  } catch (error: any) {
    throw new Error(getDetail(error));
  }
}

export async function verifyPayment(request: VerifyPaymentRequest): Promise<VerifyPaymentResponse> {
  try {
    const response = await axiosInstance.post("/api/v1/payments/razorpay/verify", request);
    return unwrapApiData(response.data);
  } catch (error: any) {
    throw new Error(getDetail(error));
  }
}

export async function markPaymentFailure(payload: { order_id: string; reason?: string; code?: string }) {
  try {
    const response = await axiosInstance.post("/api/v1/payments/razorpay/failure", payload);
    return unwrapApiData(response.data);
  } catch (error: any) {
    throw new Error(getDetail(error));
  }
}

export async function createSubscription(request: CreateSubscriptionRequest): Promise<CreateSubscriptionResponse> {
  try {
    const response = await axiosInstance.post("/api/v1/subscriptions/razorpay/create-order", request);
    return unwrapApiData(response.data);
  } catch (error: any) {
    throw new Error(getDetail(error));
  }
}

export async function verifySubscriptionPayment(payload: VerifyPaymentRequest) {
  try {
    const response = await axiosInstance.post("/api/v1/subscriptions/razorpay/verify", payload);
    return unwrapApiData(response.data);
  } catch (error: any) {
    throw new Error(getDetail(error));
  }
}

export async function markSubscriptionFailure(payload: { order_id: string; reason?: string; code?: string }) {
  try {
    const response = await axiosInstance.post("/api/v1/subscriptions/razorpay/failure", payload);
    return unwrapApiData(response.data);
  } catch (error: any) {
    throw new Error(getDetail(error));
  }
}

export function initializeRazorpayCheckout(options: any): any {
  if (typeof window === "undefined" || !(window as any).Razorpay) {
    throw new Error("Razorpay SDK not loaded");
  }

  return new (window as any).Razorpay({
    ...options,
    theme: {
      color: "#8b5cf6",
      backdrop_color: "rgba(0, 0, 0, 0.5)",
      ...options.theme,
    },
  });
}

export async function processPayment(
  creditsToBuy: number,
  onSuccess: (creditsGranted: number) => void,
  onError: (error: string) => void,
) {
  try {
    const orderData = await createOrder({ credits_to_buy: creditsToBuy });
    const rzp = initializeRazorpayCheckout({
      key: orderData.razorpay_key_id || orderData.key_id,
      amount: orderData.amount,
      currency: orderData.currency,
      name: "AlgoAgentX",
      description: `${creditsToBuy} Credits Top-up`,
      image: "/images/algoagentx_icon.jpeg",
      order_id: orderData.order_id,
      notes: {
        billing_order_id: orderData.billing_order_id,
        credits_to_buy: String(creditsToBuy),
      },
      modal: {
        ondismiss: async () => {
          try {
            await markPaymentFailure({ order_id: orderData.order_id, reason: "checkout_closed_by_user" });
          } catch {}
          onError("Checkout cancelled");
        },
      },
      handler: async (response: any) => {
        try {
          const verifyData = await verifyPayment({
            order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          });
          if (!verifyData?.success) throw new Error(verifyData?.message || "Payment verification failed");
          onSuccess(Number(verifyData.credits_granted || 0));
        } catch (error: any) {
          onError(getDetail(error));
        }
      },
    });
    rzp.on("payment.failed", async (failure: any) => {
      try {
        await markPaymentFailure({
          order_id: orderData.order_id,
          reason: failure?.error?.description || "payment_failed",
          code: failure?.error?.code,
        });
      } catch {}
      onError(failure?.error?.description || "Payment failed");
    });
    rzp.open();
  } catch (error: any) {
    onError(getDetail(error));
  }
}

export async function processSubscription(
  planCode: string,
  billingPeriod: string,
  onSuccess: () => void,
  onError: (error: string) => void,
) {
  try {
    const order = await createSubscription({ plan_code: planCode, billing_period: billingPeriod });
    const rzp = initializeRazorpayCheckout({
      key: order.razorpay_key_id || order.key_id,
      amount: order.amount,
      currency: order.currency,
      name: "AlgoAgentX",
      description: `${planCode} ${billingPeriod} Subscription`,
      image: "/images/algoagentx_icon.jpeg",
      order_id: order.order_id,
      notes: {
        billing_order_id: order.billing_order_id,
        plan_code: planCode,
        billing_period: billingPeriod,
      },
      modal: {
        ondismiss: async () => {
          try {
            await markSubscriptionFailure({ order_id: order.order_id, reason: "checkout_closed_by_user" });
          } catch {}
          onError("Checkout cancelled");
        },
      },
      handler: async (response: any) => {
        try {
          const verified = await verifySubscriptionPayment({
            order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          });
          if (!verified?.success) throw new Error(verified?.message || "Subscription verification failed");
          onSuccess();
        } catch (error: any) {
          onError(getDetail(error));
        }
      },
    });
    rzp.on("payment.failed", async (failure: any) => {
      try {
        await markSubscriptionFailure({
          order_id: order.order_id,
          reason: failure?.error?.description || "payment_failed",
          code: failure?.error?.code,
        });
      } catch {}
      onError(failure?.error?.description || "Payment failed");
    });
    rzp.open();
  } catch (error: any) {
    onError(getDetail(error));
  }
}
