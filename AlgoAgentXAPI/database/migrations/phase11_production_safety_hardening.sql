CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS platform_trading_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_trading_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    demo_trading_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    live_trading_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    global_kill_switch BOOLEAN NOT NULL DEFAULT FALSE,
    max_global_demo_orders_per_day INTEGER NULL,
    max_user_demo_orders_per_day INTEGER NULL,
    updated_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_platform_trading_settings_updated_by
    ON platform_trading_settings(updated_by);

INSERT INTO platform_trading_settings (paper_trading_enabled, demo_trading_enabled, live_trading_enabled, global_kill_switch)
SELECT TRUE, TRUE, FALSE, FALSE
WHERE NOT EXISTS (SELECT 1 FROM platform_trading_settings);

-- Hard safety: LIVE stays disabled until final production review.
UPDATE platform_trading_settings
SET live_trading_enabled = FALSE
WHERE live_trading_enabled = TRUE;
