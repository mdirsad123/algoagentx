-- Safe migration for credit top-up Razorpay stabilization
-- Compatible with existing legacy schema

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS billing_order_id VARCHAR(64);

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS failure_reason TEXT;

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_payments_user_created
    ON payments(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_payments_billing_order_id
    ON payments(billing_order_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_billing_order_id_not_null
    ON payments(billing_order_id)
    WHERE billing_order_id IS NOT NULL;
