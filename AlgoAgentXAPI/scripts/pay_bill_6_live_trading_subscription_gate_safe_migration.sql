-- PAY-BILL-6 Live Trading Subscription Gate safe migration
-- Safe to run multiple times in DBeaver.

CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(120) PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    description TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO app_settings (key, value, description)
VALUES (
    'billing_live_trading_requires_subscription',
    'true',
    'Require active paid subscription for live trading deployment and start actions'
)
ON CONFLICT (key) DO NOTHING;

-- Optional support for older coupon redemption migrations that may not have this column yet.
ALTER TABLE IF EXISTS billing_coupon_redemptions
    ADD COLUMN IF NOT EXISTS coupon_code TEXT NULL;
