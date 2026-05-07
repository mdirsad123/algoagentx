-- PAY-BILL Credit Top-up Razorpay Verify Failure Hotfix
-- Run this once in DBeaver before testing if your database was upgraded through older PAY-BILL phases.

BEGIN;

-- Coupon analytics/audit column used by PAY-BILL-2+ and admin coupon reporting.
ALTER TABLE billing_coupon_redemptions
  ADD COLUMN IF NOT EXISTS coupon_code TEXT NULL;

-- Backfill missing coupon_code values from coupon master where possible.
UPDATE billing_coupon_redemptions r
SET coupon_code = c.code
FROM billing_coupons c
WHERE r.coupon_id = c.id
  AND (r.coupon_code IS NULL OR r.coupon_code = '');

-- Helpful indexes for idempotency checks and admin analytics.
CREATE INDEX IF NOT EXISTS idx_billing_coupon_redemptions_coupon_user_order
  ON billing_coupon_redemptions (coupon_id, user_id, order_id);

CREATE INDEX IF NOT EXISTS idx_billing_coupon_redemptions_coupon_code
  ON billing_coupon_redemptions (UPPER(coupon_code));

COMMIT;
