-- Phase 16: Upstox gated order execution
-- Safe/idempotent migration for PostgreSQL.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE strategy_deployments
  ADD COLUMN IF NOT EXISTS product_type VARCHAR(30) NOT NULL DEFAULT 'MIS',
  ADD COLUMN IF NOT EXISTS order_variety VARCHAR(30) NOT NULL DEFAULT 'REGULAR',
  ADD COLUMN IF NOT EXISTS quantity_mode VARCHAR(30) NOT NULL DEFAULT 'RISK_BASED',
  ADD COLUMN IF NOT EXISTS fixed_quantity NUMERIC(18,8),
  ADD COLUMN IF NOT EXISTS max_quantity NUMERIC(18,8),
  ADD COLUMN IF NOT EXISTS max_order_value NUMERIC(18,4),
  ADD COLUMN IF NOT EXISTS square_off_time VARCHAR(20),
  ADD COLUMN IF NOT EXISTS upstox_order_confirmed BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE platform_trading_settings
  ADD COLUMN IF NOT EXISTS upstox_order_execution_enabled BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_strategy_deployments_product_type
  ON strategy_deployments (product_type);

CREATE INDEX IF NOT EXISTS idx_live_orders_broker_order_id
  ON live_orders (broker_order_id);

UPDATE broker_providers
SET
  supports_market_data = TRUE,
  supports_orders = FALSE,
  supports_live = FALSE,
  is_enabled = TRUE,
  admin_notes = 'Phase 16: Upstox order adapter code installed but order execution is gated by platform_trading_settings.upstox_order_execution_enabled and per-deployment user confirmation. Keep supports_orders false until production approval.',
  updated_at = now()
WHERE UPPER(code) = 'UPSTOX';

INSERT INTO platform_trading_settings (
  paper_trading_enabled,
  demo_trading_enabled,
  live_trading_enabled,
  global_kill_switch,
  upstox_order_execution_enabled
)
SELECT TRUE, TRUE, FALSE, FALSE, FALSE
WHERE NOT EXISTS (SELECT 1 FROM platform_trading_settings);

UPDATE platform_trading_settings
SET live_trading_enabled = FALSE,
    upstox_order_execution_enabled = COALESCE(upstox_order_execution_enabled, FALSE),
    updated_at = now();
