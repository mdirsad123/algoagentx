-- Phase 13: Broker provider framework for MT5, Upstox, Zerodha, Binance
-- Run manually in DBeaver after replacing API/App code.
-- This migration does NOT enable real-money LIVE trading.

BEGIN;

CREATE TABLE IF NOT EXISTS broker_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    market_type VARCHAR(50) NOT NULL DEFAULT 'MULTI',
    auth_type VARCHAR(50) NOT NULL DEFAULT 'PASSWORD',
    supports_paper BOOLEAN NOT NULL DEFAULT TRUE,
    supports_demo BOOLEAN NOT NULL DEFAULT FALSE,
    supports_live BOOLEAN NOT NULL DEFAULT FALSE,
    supports_market_data BOOLEAN NOT NULL DEFAULT FALSE,
    supports_orders BOOLEAN NOT NULL DEFAULT FALSE,
    supports_websocket BOOLEAN NOT NULL DEFAULT FALSE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    admin_notes TEXT NULL,
    config_schema JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_broker_providers_enabled ON broker_providers(is_enabled);
CREATE INDEX IF NOT EXISTS idx_broker_providers_market ON broker_providers(market_type);

INSERT INTO broker_providers (
    code, name, market_type, auth_type,
    supports_paper, supports_demo, supports_live,
    supports_market_data, supports_orders, supports_websocket,
    is_enabled, admin_notes, config_schema
)
VALUES
('MT5', 'MetaTrader 5', 'FOREX', 'PASSWORD', TRUE, TRUE, FALSE, TRUE, TRUE, FALSE, TRUE,
 'MT5 DEMO is enabled. LIVE remains blocked until explicit future approval.',
 '{"fields":["server_name","login_id","password"],"mode":"DEMO_ONLY_FOR_NOW"}'::jsonb),
('UPSTOX', 'Upstox India', 'INDIAN_EQUITY', 'OAUTH2', TRUE, FALSE, FALSE, TRUE, FALSE, TRUE, TRUE,
 'Provider catalog entry only. OAuth and order execution are planned for the next phase.',
 '{"fields":["client_id","redirect_uri"],"status":"COMING_NEXT_PHASE"}'::jsonb),
('ZERODHA', 'Zerodha Kite', 'INDIAN_EQUITY', 'API_KEY', TRUE, FALSE, FALSE, TRUE, FALSE, TRUE, FALSE,
 'Disabled placeholder for future broker support.',
 '{"status":"FUTURE"}'::jsonb),
('BINANCE', 'Binance', 'CRYPTO', 'API_KEY', TRUE, FALSE, FALSE, TRUE, FALSE, TRUE, FALSE,
 'Disabled placeholder for future crypto support.',
 '{"status":"FUTURE"}'::jsonb)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    market_type = EXCLUDED.market_type,
    auth_type = EXCLUDED.auth_type,
    supports_paper = EXCLUDED.supports_paper,
    supports_demo = EXCLUDED.supports_demo,
    supports_live = FALSE,
    supports_market_data = EXCLUDED.supports_market_data,
    supports_orders = EXCLUDED.supports_orders,
    supports_websocket = EXCLUDED.supports_websocket,
    admin_notes = EXCLUDED.admin_notes,
    config_schema = EXCLUDED.config_schema,
    updated_at = NOW();

ALTER TABLE broker_accounts
ADD COLUMN IF NOT EXISTS broker_provider_id UUID NULL,
ADD COLUMN IF NOT EXISTS broker_code VARCHAR(50) NULL,
ADD COLUMN IF NOT EXISTS auth_type VARCHAR(50) NULL,
ADD COLUMN IF NOT EXISTS encrypted_refresh_token TEXT NULL,
ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_broker_accounts_provider'
    ) THEN
        ALTER TABLE broker_accounts
        ADD CONSTRAINT fk_broker_accounts_provider
        FOREIGN KEY (broker_provider_id) REFERENCES broker_providers(id) ON DELETE SET NULL;
    END IF;
END $$;

UPDATE broker_accounts ba
SET broker_provider_id = bp.id,
    broker_code = COALESCE(ba.broker_code, UPPER(COALESCE(ba.broker_name, bp.code))),
    auth_type = COALESCE(ba.auth_type, bp.auth_type),
    broker_name = COALESCE(NULLIF(ba.broker_name, ''), bp.code),
    updated_at = NOW()
FROM broker_providers bp
WHERE UPPER(COALESCE(ba.broker_code, ba.broker_name, 'MT5')) = bp.code;

UPDATE broker_accounts
SET broker_code = UPPER(COALESCE(broker_code, broker_name, 'MT5')),
    auth_type = COALESCE(auth_type, CASE WHEN UPPER(COALESCE(broker_code, broker_name, 'MT5')) = 'MT5' THEN 'PASSWORD' ELSE 'OAUTH2' END),
    updated_at = NOW()
WHERE broker_code IS NULL OR auth_type IS NULL;

CREATE INDEX IF NOT EXISTS idx_broker_accounts_provider_id ON broker_accounts(broker_provider_id);
CREATE INDEX IF NOT EXISTS idx_broker_accounts_broker_code ON broker_accounts(broker_code);
CREATE INDEX IF NOT EXISTS idx_broker_accounts_token_expiry ON broker_accounts(token_expires_at);

-- Keep LIVE blocked globally in Phase 13.
UPDATE platform_trading_settings
SET live_trading_enabled = FALSE,
    updated_at = NOW()
WHERE live_trading_enabled IS DISTINCT FROM FALSE;

COMMIT;
