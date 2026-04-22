-- Safe migration for first-class billing orders table
-- This script is additive-only and keeps compatibility with legacy payments flows.

CREATE TABLE IF NOT EXISTS billing_orders (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    payment_id VARCHAR(64) NULL,
    subscription_id VARCHAR(64) NULL,

    billing_order_id VARCHAR(64) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    purpose VARCHAR(50) NOT NULL,
    amount_inr INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    status VARCHAR(20) NOT NULL,

    plan_id VARCHAR(64) NULL,
    plan_code VARCHAR(50) NULL,
    billing_period VARCHAR(20) NULL,

    razorpay_order_id VARCHAR(100) NULL,
    razorpay_payment_id VARCHAR(100) NULL,

    failure_reason TEXT NULL,
    metadata_json TEXT NULL,
    verified_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_billing_orders_user_created ON billing_orders(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_billing_orders_billing_order_id ON billing_orders(billing_order_id);
CREATE INDEX IF NOT EXISTS idx_billing_orders_payment_id ON billing_orders(payment_id);
CREATE INDEX IF NOT EXISTS idx_billing_orders_purpose ON billing_orders(purpose);

-- Backfill from payments in a best-effort idempotent way.
INSERT INTO billing_orders (
    id,
    user_id,
    payment_id,
    subscription_id,
    billing_order_id,
    provider,
    purpose,
    amount_inr,
    currency,
    status,
    plan_id,
    plan_code,
    billing_period,
    razorpay_order_id,
    razorpay_payment_id,
    failure_reason,
    verified_at,
    created_at,
    updated_at
)
SELECT
    COALESCE(NULLIF(CAST(p.billing_order_id AS TEXT), ''), CAST(p.id AS TEXT)) AS id,
    CAST(p.user_id AS TEXT) AS user_id,
    CAST(p.id AS TEXT) AS payment_id,
    CAST(p.subscription_id AS TEXT) AS subscription_id,
    COALESCE(NULLIF(CAST(p.billing_order_id AS TEXT), ''), CAST(p.id AS TEXT)) AS billing_order_id,
    COALESCE(CAST(p.provider AS TEXT), 'RAZORPAY') AS provider,
    COALESCE(CAST(p.purpose AS TEXT), 'UNKNOWN') AS purpose,
    COALESCE(p.amount_inr, 0) AS amount_inr,
    COALESCE(CAST(p.currency AS TEXT), 'INR') AS currency,
    COALESCE(CAST(p.status AS TEXT), 'CREATED') AS status,
    CAST(p.plan_id AS TEXT) AS plan_id,
    CAST(p.plan_code AS TEXT) AS plan_code,
    CAST(p.billing_period AS TEXT) AS billing_period,
    CAST(p.razorpay_order_id AS TEXT) AS razorpay_order_id,
    CAST(p.razorpay_payment_id AS TEXT) AS razorpay_payment_id,
    CAST(p.failure_reason AS TEXT) AS failure_reason,
    p.verified_at,
    COALESCE(p.created_at, NOW()) AS created_at,
    p.updated_at
FROM payments p
WHERE NOT EXISTS (
    SELECT 1
    FROM billing_orders bo
    WHERE bo.payment_id = CAST(p.id AS TEXT)
);
