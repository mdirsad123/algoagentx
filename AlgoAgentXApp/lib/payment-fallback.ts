"use client";

export interface DemoPaymentResult {
  success: boolean;
  creditsGranted: number;
  message: string;
}

export interface DemoSubscriptionResult {
  success: boolean;
  planCode: string;
  period: string;
  message: string;
}

export class PaymentProcessor {
  async isBackendAvailable(): Promise<boolean> {
    return true;
  }

  async processCreditPurchase(
    creditsToBuy: number,
    onSuccess: (result: DemoPaymentResult) => void,
    onError: (error: string) => void,
  ) {
    try {
      const { processPayment } = await import("./razorpay");
      await processPayment(
        creditsToBuy,
        (creditsGranted) =>
          onSuccess({
            success: true,
            creditsGranted,
            message: `Payment successful. ${creditsGranted} credits added to wallet.`,
          }),
        onError,
      );
    } catch (error: any) {
      onError(error?.message || "Failed to process payment");
    }
  }

  async processSubscription(
    planCode: string,
    billingPeriod: string,
    onSuccess: (result: DemoSubscriptionResult) => void,
    onError: (error: string) => void,
  ) {
    try {
      const { processSubscription } = await import("./razorpay");
      await processSubscription(
        planCode,
        billingPeriod,
        () =>
          onSuccess({
            success: true,
            planCode,
            period: billingPeriod,
            message: `Subscription successful. ${planCode} plan activated.`,
          }),
        onError,
      );
    } catch (error: any) {
      onError(error?.message || "Failed to process subscription");
    }
  }

  async refreshBackendStatus(): Promise<boolean> {
    return true;
  }
}

export function createPaymentProcessor(): PaymentProcessor {
  return new PaymentProcessor();
}

export async function checkBackendStatus(): Promise<boolean> {
  return true;
}
