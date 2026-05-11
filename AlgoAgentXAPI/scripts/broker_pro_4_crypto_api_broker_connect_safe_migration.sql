-- BROKER-PRO-4 Crypto API Broker Connect safe migration + seed
-- Safe to run multiple times in DBeaver.

ALTER TABLE broker_accounts
  ADD COLUMN IF NOT EXISTS encrypted_api_key TEXT,
  ADD COLUMN IF NOT EXISTS encrypted_api_secret TEXT,
  ADD COLUMN IF NOT EXISTS encrypted_api_passphrase TEXT,
  ADD COLUMN IF NOT EXISTS last_connection_result JSONB;

-- Move crypto providers from placeholder to connectable API key mode.
INSERT INTO broker_providers (
  code, name, display_name, market_type, broker_category, auth_type,
  supports_paper, supports_demo, supports_live, supports_market_data, supports_orders, supports_websocket,
  is_enabled, is_live_enabled, description, setup_mode, admin_notes, config_schema
) VALUES
('BINANCE', 'BINANCE', 'Binance', 'CRYPTO', 'Crypto API Broker', 'API_KEY', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE, 'Binance crypto API broker using encrypted API key and secret. BROKER-PRO-4 only tests account/balance access; live orders remain disabled.', 'API_KEY_SECRET', 'Create API key with read/trade permission only. Never enable withdrawal permission.', '{"requires_passphrase": false, "implemented_phase": "BROKER-PRO-4"}'::jsonb),
('BYBIT', 'BYBIT', 'Bybit', 'CRYPTO', 'Crypto API Broker', 'API_KEY', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE, 'Bybit crypto API broker using encrypted API key and secret. BROKER-PRO-4 only tests account/balance access; live orders remain disabled.', 'API_KEY_SECRET', 'Create API key with read/trade permission only. Never enable withdrawal permission.', '{"requires_passphrase": false, "implemented_phase": "BROKER-PRO-4"}'::jsonb),
('OKX', 'OKX', 'OKX', 'CRYPTO', 'Crypto API Broker', 'API_KEY', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE, 'OKX crypto API broker using encrypted API key, secret, and passphrase. BROKER-PRO-4 only tests account/balance access; live orders remain disabled.', 'API_KEY_SECRET', 'Create API key with read/trade permission only. Never enable withdrawal permission.', '{"requires_passphrase": true, "implemented_phase": "BROKER-PRO-4"}'::jsonb)
ON CONFLICT (code) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  market_type = EXCLUDED.market_type,
  broker_category = EXCLUDED.broker_category,
  auth_type = EXCLUDED.auth_type,
  supports_paper = EXCLUDED.supports_paper,
  supports_demo = EXCLUDED.supports_demo,
  supports_live = EXCLUDED.supports_live,
  supports_market_data = EXCLUDED.supports_market_data,
  supports_orders = EXCLUDED.supports_orders,
  supports_websocket = EXCLUDED.supports_websocket,
  is_enabled = TRUE,
  is_live_enabled = FALSE,
  description = EXCLUDED.description,
  setup_mode = 'API_KEY_SECRET',
  admin_notes = EXCLUDED.admin_notes,
  config_schema = EXCLUDED.config_schema,
  updated_at = NOW();

-- Crypto live order execution is intentionally disabled in this phase.
UPDATE broker_providers
SET supports_live = FALSE, is_live_enabled = FALSE
WHERE code IN ('BINANCE','BYBIT','OKX');
