-- PAY-BILL-1 Currency + Billing Settings Foundation
-- Safe/idempotent migration for DBeaver. Can be run multiple times.

CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(120) PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    description TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO app_settings (key, value, description)
VALUES
    ('billing_base_currency', 'USD', 'Base billing currency for AlgoAgentX pricing'),
    ('billing_inr_conversion_rate', '83', 'INR conversion rate for one USD'),
    ('billing_gst_percent', '18', 'GST percent used for future invoices and payment summaries'),
    ('billing_enable_razorpay_upi', 'true', 'Enable Razorpay UPI payment option'),
    ('billing_enable_card_payment', 'true', 'Enable card payment option'),
    ('billing_enable_crypto_payment', 'true', 'Enable crypto payment option')
ON CONFLICT (key) DO NOTHING;

ALTER TABLE plans ADD COLUMN IF NOT EXISTS price_usd NUMERIC(10, 2) NOT NULL DEFAULT 0;

UPDATE plans
SET price_usd = ROUND((COALESCE(price_inr, 0)::numeric / 83), 2)
WHERE COALESCE(price_usd, 0) = 0
  AND COALESCE(price_inr, 0) > 0;

UPDATE plans
SET price_usd = 0
WHERE UPPER(COALESCE(code, '')) = 'FREE';
