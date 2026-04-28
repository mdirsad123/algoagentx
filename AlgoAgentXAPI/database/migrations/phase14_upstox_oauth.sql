-- Phase 14: Upstox OAuth connection framework
-- Run manually in DBeaver after replacing API/App code.
-- This migration enables SaaS-safe Upstox OAuth account connection only.
-- Upstox order execution and real-money LIVE trading remain disabled.

BEGIN;

CREATE TABLE IF NOT EXISTS broker_oauth_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_provider_code VARCHAR(50) NOT NULL,
    state VARCHAR(255) NOT NULL UNIQUE,
    redirect_after VARCHAR(500) NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_broker_oauth_states_user_provider
ON broker_oauth_states(user_id, broker_provider_code);

CREATE INDEX IF NOT EXISTS idx_broker_oauth_states_expires
ON broker_oauth_states(expires_at);

-- Make sure Upstox provider exists and is enabled for OAuth connection.
INSERT INTO broker_providers (
    code, name, market_type, auth_type,
    supports_paper, supports_demo, supports_live,
    supports_market_data, supports_orders, supports_websocket,
    is_enabled, admin_notes, config_schema
)
VALUES (
    'UPSTOX', 'Upstox India', 'INDIAN_EQUITY', 'OAUTH2',
    TRUE, FALSE, FALSE,
    TRUE, TRUE, TRUE,
    TRUE,
    'OAuth account connection enabled in Phase 14. Order execution remains disabled until the dedicated Upstox order phase.',
    '{"fields":["client_id","client_secret","redirect_uri"],"env":["UPSTOX_CLIENT_ID","UPSTOX_CLIENT_SECRET","UPSTOX_REDIRECT_URI"],"status":"OAUTH_ENABLED_ORDERS_DISABLED"}'::jsonb
)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    market_type = EXCLUDED.market_type,
    auth_type = EXCLUDED.auth_type,
    supports_market_data = TRUE,
    supports_orders = TRUE,
    supports_websocket = TRUE,
    supports_live = FALSE,
    is_enabled = TRUE,
    admin_notes = EXCLUDED.admin_notes,
    config_schema = EXCLUDED.config_schema,
    updated_at = NOW();

-- Keep future providers consistent and LIVE blocked.
UPDATE broker_providers
SET supports_live = FALSE,
    updated_at = NOW()
WHERE supports_live IS DISTINCT FROM FALSE;

UPDATE platform_trading_settings
SET live_trading_enabled = FALSE,
    updated_at = NOW()
WHERE live_trading_enabled IS DISTINCT FROM FALSE;

COMMIT;
