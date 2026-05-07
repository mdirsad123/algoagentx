-- PAY-BILL-7 Admin Billing Analytics + Audit
-- Safe/idempotent helper indexes only. No balance, payment, subscription, or order data is modified.

DO $$
BEGIN
  IF to_regclass('public.billing_orders') IS NOT NULL THEN
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_billing_orders_created_at ON public.billing_orders (created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_billing_orders_status ON public.billing_orders (status);
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_billing_orders_method ON public.billing_orders (payment_method);
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_billing_orders_purchase ON public.billing_orders (purchase_type);
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_billing_orders_coupon ON public.billing_orders (coupon_code);
  END IF;

  IF to_regclass('public.payments') IS NOT NULL THEN
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_payments_created_at ON public.payments (created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_payments_status ON public.payments (status);
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_payments_billing_order_id ON public.payments (billing_order_id);
  END IF;

  IF to_regclass('public.billing_coupon_redemptions') IS NOT NULL THEN
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_coupon_redemptions_code ON public.billing_coupon_redemptions (coupon_code);
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_coupon_redemptions_redeemed_at ON public.billing_coupon_redemptions (redeemed_at DESC);
  END IF;

  IF to_regclass('public.credit_transactions') IS NOT NULL THEN
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_credit_transactions_source ON public.credit_transactions (source);
    CREATE INDEX IF NOT EXISTS idx_pay_bill7_credit_transactions_created_at ON public.credit_transactions (created_at DESC);
  END IF;
END $$;
