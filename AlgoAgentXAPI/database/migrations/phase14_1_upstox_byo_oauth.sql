-- Phase 14.1: Upstox BYO OAuth credentials per user broker account
-- Safe to run multiple times in PostgreSQL / DBeaver.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE broker_accounts
  ADD COLUMN IF NOT EXISTS oauth_client_id VARCHAR(255),
  ADD COLUMN IF NOT EXISTS encrypted_client_secret TEXT,
  ADD COLUMN IF NOT EXISTS oauth_redirect_uri VARCHAR(1000);

CREATE TABLE IF NOT EXISTS broker_oauth_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  broker_provider_code VARCHAR(50) NOT NULL,
  broker_account_id UUID NULL,
  state VARCHAR(255) NOT NULL UNIQUE,
  redirect_after VARCHAR(500),
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE broker_oauth_states
  ADD COLUMN IF NOT EXISTS broker_account_id UUID NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_broker_oauth_states_broker_account_id'
  ) THEN
    ALTER TABLE broker_oauth_states
      ADD CONSTRAINT fk_broker_oauth_states_broker_account_id
      FOREIGN KEY (broker_account_id) REFERENCES broker_accounts(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_broker_accounts_upstox_user
  ON broker_accounts(user_id, broker_code)
  WHERE broker_code = 'UPSTOX';

CREATE INDEX IF NOT EXISTS idx_broker_accounts_oauth_client_id
  ON broker_accounts(oauth_client_id);

CREATE INDEX IF NOT EXISTS idx_broker_oauth_states_user_provider
  ON broker_oauth_states(user_id, broker_provider_code);

CREATE INDEX IF NOT EXISTS idx_broker_oauth_states_account
  ON broker_oauth_states(broker_account_id);

CREATE INDEX IF NOT EXISTS idx_broker_oauth_states_expires
  ON broker_oauth_states(expires_at);

INSERT INTO broker_providers (
  code, name, market_type, auth_type,
  supports_paper, supports_demo, supports_live,
  supports_market_data, supports_orders, supports_websocket,
  is_enabled, admin_notes, config_schema
)
VALUES (
  'UPSTOX', 'Upstox India', 'INDIAN_EQUITY', 'OAUTH2',
  false, true, false,
  true, false, true,
  true,
  'Phase 14.1 BYO OAuth enabled. Orders/live execution remain disabled.',
  '{"fields":["account_label","client_id","client_secret","redirect_uri"],"credential_mode":"BYO"}'::jsonb
)
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  market_type = EXCLUDED.market_type,
  auth_type = EXCLUDED.auth_type,
  supports_market_data = true,
  supports_websocket = true,
  supports_orders = false,
  supports_live = false,
  is_enabled = true,
  admin_notes = EXCLUDED.admin_notes,
  config_schema = EXCLUDED.config_schema,
  updated_at = now();


DO $$
BEGIN
  IF to_regclass('public.platform_trading_settings') IS NOT NULL THEN
    UPDATE platform_trading_settings
    SET live_trading_enabled = false,
        updated_at = now()
    WHERE live_trading_enabled IS DISTINCT FROM false;
  END IF;
END $$;
