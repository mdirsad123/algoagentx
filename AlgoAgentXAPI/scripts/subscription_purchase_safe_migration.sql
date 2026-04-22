-- Safe migration for subscription purchase lifecycle stabilization
-- Additive only (legacy-safe)

-- =========================
-- plans uniqueness + period normalization
-- =========================
-- Ensure billing period is always present and normalized.
UPDATE plans
SET billing_period = CASE
    WHEN UPPER(COALESCE(code, '')) = 'FREE' THEN 'NONE'
    ELSE 'MONTHLY'
END
WHERE billing_period IS NULL OR TRIM(billing_period) = '';

UPDATE plans
SET billing_period = CASE
    WHEN UPPER(billing_period) = 'ANNUAL' THEN 'YEARLY'
    ELSE UPPER(billing_period)
END;

-- Drop legacy unique(code) if present, keep unique(code,billing_period) only.
DO $$
DECLARE
    c RECORD;
BEGIN
    FOR c IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'plans'::regclass
          AND contype = 'u'
          AND conkey = ARRAY[
              (SELECT attnum FROM pg_attribute WHERE attrelid = 'plans'::regclass AND attname = 'code')
          ]
    LOOP
        EXECUTE format('ALTER TABLE plans DROP CONSTRAINT %I', c.conname);
    END LOOP;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'plans'::regclass
          AND contype = 'u'
          AND conname = 'uq_plans_code_billing_period'
    ) THEN
        ALTER TABLE plans
            ADD CONSTRAINT uq_plans_code_billing_period UNIQUE (code, billing_period);
    END IF;
END $$;

-- =========================
-- payments table extensions
-- =========================
ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS plan_id UUID;

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS plan_code VARCHAR(50);

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS billing_period VARCHAR(20);

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS subscription_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_payments_plan_code
    ON payments(plan_code);

CREATE INDEX IF NOT EXISTS idx_payments_subscription_id
    ON payments(subscription_id);

-- ==================================
-- user_subscriptions table extensions
-- ==================================
ALTER TABLE user_subscriptions
    ADD COLUMN IF NOT EXISTS plan_code_snapshot VARCHAR(50);

ALTER TABLE user_subscriptions
    ADD COLUMN IF NOT EXISTS billing_period_snapshot VARCHAR(20);

ALTER TABLE user_subscriptions
    ADD COLUMN IF NOT EXISTS plan_price_inr INTEGER;

ALTER TABLE user_subscriptions
    ADD COLUMN IF NOT EXISTS included_credits_total INTEGER;

ALTER TABLE user_subscriptions
    ADD COLUMN IF NOT EXISTS included_credits_remaining INTEGER;

ALTER TABLE user_subscriptions
    ADD COLUMN IF NOT EXISTS last_credit_refill_at TIMESTAMPTZ;

ALTER TABLE user_subscriptions
    ADD COLUMN IF NOT EXISTS next_credit_refill_at TIMESTAMPTZ;

ALTER TABLE user_subscriptions
    ADD COLUMN IF NOT EXISTS source_payment_id UUID;

ALTER TABLE user_subscriptions
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_plan_code_snapshot
    ON user_subscriptions(plan_code_snapshot);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_next_credit_refill_at
    ON user_subscriptions(next_credit_refill_at);

-- Backfill optional snapshots for existing rows (best-effort)
UPDATE user_subscriptions us
SET
    plan_code_snapshot = COALESCE(us.plan_code_snapshot, p.code),
    billing_period_snapshot = COALESCE(us.billing_period_snapshot, p.billing_period),
    plan_price_inr = COALESCE(us.plan_price_inr, p.price_inr),
    included_credits_total = COALESCE(us.included_credits_total, p.included_credits),
    included_credits_remaining = COALESCE(us.included_credits_remaining, p.included_credits)
FROM plans p
WHERE us.plan_id = p.id;
