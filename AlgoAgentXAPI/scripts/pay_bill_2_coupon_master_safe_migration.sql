-- PAY-BILL-2 Coupon Master + Discount Engine
-- Safe to run multiple times in DBeaver.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS billing_coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    description TEXT NULL,
    discount_type TEXT NOT NULL DEFAULT 'PERCENT',
    discount_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
    applies_to TEXT NOT NULL DEFAULT 'ALL',
    plan_code TEXT NULL,
    billing_period TEXT NULL,
    min_order_usd NUMERIC(12, 2) NULL,
    max_discount_usd NUMERIC(12, 2) NULL,
    max_redemptions INTEGER NULL,
    per_user_limit INTEGER NULL DEFAULT 1,
    starts_at TIMESTAMPTZ NULL,
    expires_at TIMESTAMPTZ NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_billing_coupons_discount_type CHECK (discount_type IN ('PERCENT', 'FIXED_USD')),
    CONSTRAINT ck_billing_coupons_applies_to CHECK (applies_to IN ('ALL', 'SUBSCRIPTION', 'CREDITS')),
    CONSTRAINT ck_billing_coupons_discount_value CHECK (discount_value > 0),
    CONSTRAINT ck_billing_coupons_percent_max CHECK (discount_type <> 'PERCENT' OR discount_value <= 100),
    CONSTRAINT ck_billing_coupons_positive_limits CHECK (
        (max_redemptions IS NULL OR max_redemptions > 0)
        AND (per_user_limit IS NULL OR per_user_limit > 0)
    ),
    CONSTRAINT ck_billing_coupons_date_order CHECK (expires_at IS NULL OR starts_at IS NULL OR expires_at >= starts_at)
);

ALTER TABLE billing_coupons ADD COLUMN IF NOT EXISTS min_order_usd NUMERIC(12, 2) NULL;
ALTER TABLE billing_coupons ADD COLUMN IF NOT EXISTS max_discount_usd NUMERIC(12, 2) NULL;
ALTER TABLE billing_coupons ADD COLUMN IF NOT EXISTS max_redemptions INTEGER NULL;
ALTER TABLE billing_coupons ADD COLUMN IF NOT EXISTS per_user_limit INTEGER NULL DEFAULT 1;
ALTER TABLE billing_coupons ADD COLUMN IF NOT EXISTS starts_at TIMESTAMPTZ NULL;
ALTER TABLE billing_coupons ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ NULL;
ALTER TABLE billing_coupons ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS billing_coupon_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id UUID NOT NULL REFERENCES billing_coupons(id) ON DELETE CASCADE,
    user_id UUID NULL,
    order_id UUID NULL,
    purchase_type TEXT NULL,
    subtotal_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
    discount_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
    final_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
    redeemed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_billing_coupons_code_upper ON billing_coupons (UPPER(code));
CREATE INDEX IF NOT EXISTS idx_billing_coupons_active ON billing_coupons (is_active);
CREATE INDEX IF NOT EXISTS idx_billing_coupons_scope ON billing_coupons (applies_to, plan_code, billing_period);
CREATE INDEX IF NOT EXISTS idx_billing_coupon_redemptions_coupon_user ON billing_coupon_redemptions (coupon_id, user_id);
CREATE INDEX IF NOT EXISTS idx_billing_coupon_redemptions_redeemed_at ON billing_coupon_redemptions (redeemed_at DESC);

-- Optional seed: only creates HELLO when it does not already exist.
INSERT INTO billing_coupons (
    code, description, discount_type, discount_value, applies_to,
    max_redemptions, per_user_limit, is_active
)
VALUES (
    'HELLO', 'Welcome offer coupon for first checkout preview', 'PERCENT', 20, 'ALL', NULL, 1, TRUE
)
ON CONFLICT (code) DO NOTHING;
