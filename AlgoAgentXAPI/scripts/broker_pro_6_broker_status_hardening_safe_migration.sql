-- BROKER-PRO-6 Broker Status/Test/Reconnect/Delete Hardening
-- Safe additive migration. Keeps existing MT5/Upstox data and adds any missing catalog/crypto columns.

ALTER TABLE IF EXISTS broker_providers
  ADD COLUMN IF NOT EXISTS display_name VARCHAR(255),
  ADD COLUMN IF NOT EXISTS broker_category VARCHAR(80) NOT NULL DEFAULT 'Cloud Broker',
  ADD COLUMN IF NOT EXISTS is_live_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS setup_mode VARCHAR(50) NOT NULL DEFAULT 'COMING_SOON';

ALTER TABLE IF EXISTS broker_accounts
  ADD COLUMN IF NOT EXISTS encrypted_api_key TEXT,
  ADD COLUMN IF NOT EXISTS encrypted_api_secret TEXT,
  ADD COLUMN IF NOT EXISTS encrypted_api_passphrase TEXT,
  ADD COLUMN IF NOT EXISTS last_connection_result JSONB;

CREATE INDEX IF NOT EXISTS idx_broker_accounts_status ON broker_accounts(status);
CREATE INDEX IF NOT EXISTS idx_broker_accounts_code_status ON broker_accounts(broker_code, status);

-- Normalize old/legacy statuses into the new standard where safe.
UPDATE broker_accounts SET status = 'DISCONNECTED' WHERE status IS NULL OR status = '';
UPDATE broker_accounts SET status = 'PENDING_AUTH' WHERE broker_code = 'UPSTOX' AND status IN ('EXPIRED');
UPDATE broker_accounts SET status = 'AGENT_OFFLINE' WHERE broker_code = 'MT5' AND status IN ('EXPIRED');

-- Keep crypto live order execution disabled in this phase.
UPDATE broker_providers
SET setup_mode = 'API_KEY_SECRET', broker_category = 'Crypto API Broker', is_live_enabled = FALSE
WHERE code IN ('BINANCE', 'BYBIT', 'OKX');

UPDATE broker_providers
SET setup_mode = 'MT5_AGENT', broker_category = 'MT5 Agent Broker'
WHERE code = 'MT5';

UPDATE broker_providers
SET setup_mode = 'OAUTH', broker_category = 'Cloud Broker'
WHERE code = 'UPSTOX';
