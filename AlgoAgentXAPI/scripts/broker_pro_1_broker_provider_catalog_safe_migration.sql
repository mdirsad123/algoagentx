-- BROKER-PRO-1 / BROKER-PRO-2 safe broker provider catalog migration + seed
-- Safe to run multiple times in DBeaver.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE broker_providers
  ADD COLUMN IF NOT EXISTS display_name VARCHAR(255),
  ADD COLUMN IF NOT EXISTS broker_category VARCHAR(80) NOT NULL DEFAULT 'Cloud Broker',
  ADD COLUMN IF NOT EXISTS is_live_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS setup_mode VARCHAR(50) NOT NULL DEFAULT 'COMING_SOON';

UPDATE broker_providers
SET display_name = COALESCE(display_name, name),
    broker_category = COALESCE(NULLIF(broker_category, ''), 'Cloud Broker'),
    setup_mode = COALESCE(NULLIF(setup_mode, ''), CASE WHEN code = 'MT5' THEN 'MT5_AGENT' WHEN code = 'UPSTOX' THEN 'OAUTH' ELSE 'COMING_SOON' END),
    is_live_enabled = COALESCE(is_live_enabled, FALSE);

-- Upsert full catalog. Only MT5 and Upstox are enabled by default; other providers remain visible as Coming Soon.
INSERT INTO broker_providers (
  code, name, display_name, market_type, broker_category, auth_type,
  supports_paper, supports_demo, supports_live, supports_market_data, supports_orders, supports_websocket,
  is_enabled, is_live_enabled, description, setup_mode, admin_notes, config_schema
) VALUES
('UPSTOX', 'UPSTOX', 'Upstox', 'INDIAN_EQUITY', 'Cloud Broker', 'OAUTH2', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE, 'Indian equity broker using user-owned Upstox Developer OAuth credentials.', 'OAUTH', 'Cloud broker. Live requires admin approval.', '{}'::jsonb),
('ZERODHA', 'ZERODHA', 'Zerodha Kite', 'INDIAN_EQUITY', 'Cloud Broker', 'OAUTH2', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, FALSE, 'Zerodha Kite integration placeholder.', 'COMING_SOON', 'Coming soon provider.', '{}'::jsonb),
('ANGEL_ONE', 'ANGEL_ONE', 'Angel One', 'INDIAN_EQUITY', 'Cloud Broker', 'API_KEY', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, FALSE, 'Angel One SmartAPI integration placeholder.', 'COMING_SOON', 'Coming soon provider.', '{}'::jsonb),
('DHAN', 'DHAN', 'Dhan', 'INDIAN_EQUITY', 'Cloud Broker', 'API_KEY', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, FALSE, 'Dhan API integration placeholder.', 'COMING_SOON', 'Coming soon provider.', '{}'::jsonb),
('GROWW', 'GROWW', 'Groww', 'INDIAN_EQUITY', 'Cloud Broker', 'OAUTH2', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, FALSE, 'Groww broker integration placeholder.', 'COMING_SOON', 'Coming soon provider.', '{}'::jsonb),
('BINANCE', 'BINANCE', 'Binance', 'CRYPTO', 'Crypto API Broker', 'API_KEY', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, FALSE, 'Binance crypto API broker placeholder.', 'COMING_SOON', 'Coming soon provider.', '{}'::jsonb),
('BYBIT', 'BYBIT', 'Bybit', 'CRYPTO', 'Crypto API Broker', 'API_KEY', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, FALSE, 'Bybit crypto API broker placeholder.', 'COMING_SOON', 'Coming soon provider.', '{}'::jsonb),
('OKX', 'OKX', 'OKX', 'CRYPTO', 'Crypto API Broker', 'API_KEY', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, FALSE, 'OKX crypto API broker placeholder.', 'COMING_SOON', 'Coming soon provider.', '{}'::jsonb),
('MT5', 'MT5', 'MetaTrader 5 Agent', 'FOREX', 'MT5 Agent Broker', 'MT5_AGENT', TRUE, TRUE, FALSE, TRUE, TRUE, FALSE, TRUE, FALSE, 'Forex/CFD trading via AlgoAgentX MT5 Agent running on Windows PC or VPS.', 'MT5_AGENT', 'Agent-based MT5 setup. Do not expose Docker/Python terminal messages to users.', '{}'::jsonb),
('CTRADER_API', 'CTRADER_API', 'cTrader API', 'FOREX', 'MT5 Agent Broker', 'OAUTH2', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, FALSE, 'Future cTrader API integration placeholder.', 'COMING_SOON', 'Coming soon provider.', '{}'::jsonb)
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
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
  is_enabled = CASE WHEN broker_providers.code IN ('UPSTOX','MT5') THEN TRUE ELSE broker_providers.is_enabled END,
  is_live_enabled = COALESCE(broker_providers.is_live_enabled, FALSE),
  description = EXCLUDED.description,
  setup_mode = CASE WHEN broker_providers.code IN ('UPSTOX','MT5') THEN EXCLUDED.setup_mode ELSE COALESCE(NULLIF(broker_providers.setup_mode, ''), EXCLUDED.setup_mode) END,
  admin_notes = COALESCE(broker_providers.admin_notes, EXCLUDED.admin_notes),
  config_schema = COALESCE(broker_providers.config_schema, EXCLUDED.config_schema),
  updated_at = NOW();

UPDATE broker_providers SET is_live_enabled = FALSE WHERE COALESCE(supports_live, FALSE) = FALSE;
