-- Phase 15: Upstox market-data snapshots for live strategy runner
-- Safe/idempotent migration for PostgreSQL.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Deployment metadata for broker-specific symbols / Upstox instrument keys.
ALTER TABLE strategy_deployments
  ADD COLUMN IF NOT EXISTS broker_symbol VARCHAR(255),
  ADD COLUMN IF NOT EXISTS instrument_key VARCHAR(255),
  ADD COLUMN IF NOT EXISTS exchange VARCHAR(50),
  ADD COLUMN IF NOT EXISTS segment VARCHAR(80);

CREATE INDEX IF NOT EXISTS idx_strategy_deployments_broker_symbol
  ON strategy_deployments (broker_symbol);
CREATE INDEX IF NOT EXISTS idx_strategy_deployments_instrument_key
  ON strategy_deployments (instrument_key);

-- Broker instrument master table. Seed manually/import later from Upstox instruments JSON.
CREATE TABLE IF NOT EXISTS broker_instruments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  broker_provider_code VARCHAR(50) NOT NULL,
  exchange VARCHAR(50),
  trading_symbol VARCHAR(100) NOT NULL,
  instrument_key VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  segment VARCHAR(80),
  lot_size INTEGER,
  tick_size NUMERIC(18,8),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  metadata_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_broker_instruments_provider_key UNIQUE (broker_provider_code, instrument_key)
);

CREATE INDEX IF NOT EXISTS idx_broker_instruments_provider_symbol
  ON broker_instruments (broker_provider_code, trading_symbol);
CREATE INDEX IF NOT EXISTS idx_broker_instruments_search
  ON broker_instruments (broker_provider_code, exchange, segment);
CREATE INDEX IF NOT EXISTS idx_broker_instruments_active
  ON broker_instruments (is_active);

-- Keep live market candles as the dedicated live runner candle store.
ALTER TABLE live_market_candles
  ADD COLUMN IF NOT EXISTS raw_payload JSONB;

CREATE INDEX IF NOT EXISTS idx_live_market_candles_source
  ON live_market_candles (source);

-- Keep Upstox provider enabled for OAuth + market data snapshot only.
UPDATE broker_providers
SET
  is_enabled = TRUE,
  supports_market_data = TRUE,
  supports_orders = FALSE,
  supports_live = FALSE,
  supports_websocket = FALSE,
  updated_at = now()
WHERE UPPER(code) = 'UPSTOX';

INSERT INTO broker_providers (
  code, name, market_type, auth_type, supports_paper, supports_demo,
  supports_live, supports_market_data, supports_orders, supports_websocket,
  is_enabled, admin_notes, config_schema
)
SELECT
  'UPSTOX',
  'Upstox India',
  'INDIAN_EQUITY',
  'OAUTH2',
  TRUE,
  TRUE,
  FALSE,
  TRUE,
  FALSE,
  FALSE,
  TRUE,
  'Phase 15: OAuth + market data snapshots enabled. Orders/live trading disabled.',
  '{"requires_user_oauth": true, "market_data_snapshot": true, "orders_enabled": false}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM broker_providers WHERE UPPER(code) = 'UPSTOX');

-- Optional helpful seeds. You can add more from Upstox instruments JSON later.
INSERT INTO broker_instruments (
  broker_provider_code, exchange, trading_symbol, instrument_key, name, segment, lot_size, tick_size, metadata_json
)
VALUES
  ('UPSTOX', 'NSE_EQ', 'RELIANCE', 'NSE_EQ|INE002A01018', 'Reliance Industries Limited', 'EQ', 1, 0.05, '{"seed":"phase15"}'::jsonb),
  ('UPSTOX', 'NSE_EQ', 'TCS', 'NSE_EQ|INE467B01029', 'Tata Consultancy Services Limited', 'EQ', 1, 0.05, '{"seed":"phase15"}'::jsonb),
  ('UPSTOX', 'NSE_EQ', 'INFY', 'NSE_EQ|INE009A01021', 'Infosys Limited', 'EQ', 1, 0.05, '{"seed":"phase15"}'::jsonb)
ON CONFLICT (broker_provider_code, instrument_key) DO UPDATE
SET
  trading_symbol = EXCLUDED.trading_symbol,
  name = EXCLUDED.name,
  exchange = EXCLUDED.exchange,
  segment = EXCLUDED.segment,
  is_active = TRUE,
  updated_at = now();

-- Safety: keep production live trading disabled.
UPDATE platform_trading_settings
SET live_trading_enabled = FALSE,
    updated_at = now()
WHERE live_trading_enabled IS DISTINCT FROM FALSE;
