-- PAY-UI-1 Coupon Announcement Bar settings migration
-- Safe to run multiple times in DBeaver.

CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(120) PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    description TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO app_settings (key, value, description)
VALUES
    ('coupon_bar_enabled', 'false', 'Enable or disable the logged-in user coupon announcement bar'),
    ('coupon_bar_message', 'Haven''t purchased yet? Use code HELLO & Get 20% OFF now on your first purchase!', 'Coupon announcement message shown to logged-in users'),
    ('coupon_bar_code', 'HELLO', 'Coupon code highlighted in the coupon announcement bar')
ON CONFLICT (key) DO NOTHING;
