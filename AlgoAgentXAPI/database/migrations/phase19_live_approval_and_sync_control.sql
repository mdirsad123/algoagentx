-- Phase 19: Live approval gate and controlled broker auto-sync
-- Safe/idempotent migration for PostgreSQL/DBeaver.

ALTER TABLE strategy_deployments
    ADD COLUMN IF NOT EXISTS live_sync_enabled boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS live_sync_interval_seconds integer NOT NULL DEFAULT 10,
    ADD COLUMN IF NOT EXISTS last_live_sync_at timestamptz NULL,
    ADD COLUMN IF NOT EXISTS live_sync_error_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS live_sync_last_error text NULL,
    ADD COLUMN IF NOT EXISTS live_approved boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS live_approved_at timestamptz NULL;

UPDATE strategy_deployments
SET live_sync_enabled = COALESCE(live_sync_enabled, false),
    live_sync_interval_seconds = LEAST(300, GREATEST(5, COALESCE(live_sync_interval_seconds, 10))),
    live_sync_error_count = COALESCE(live_sync_error_count, 0),
    live_approved = COALESCE(live_approved, false);

ALTER TABLE platform_trading_settings
    ADD COLUMN IF NOT EXISTS broker_auto_sync_enabled boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS min_broker_sync_interval_seconds integer NOT NULL DEFAULT 5,
    ADD COLUMN IF NOT EXISTS default_broker_sync_interval_seconds integer NOT NULL DEFAULT 10,
    ADD COLUMN IF NOT EXISTS max_broker_sync_interval_seconds integer NOT NULL DEFAULT 300;

UPDATE platform_trading_settings
SET broker_auto_sync_enabled = COALESCE(broker_auto_sync_enabled, true),
    min_broker_sync_interval_seconds = LEAST(300, GREATEST(5, COALESCE(min_broker_sync_interval_seconds, 5))),
    max_broker_sync_interval_seconds = LEAST(300, GREATEST(5, COALESCE(max_broker_sync_interval_seconds, 300))),
    default_broker_sync_interval_seconds = LEAST(
        LEAST(300, GREATEST(5, COALESCE(max_broker_sync_interval_seconds, 300))),
        GREATEST(LEAST(300, GREATEST(5, COALESCE(min_broker_sync_interval_seconds, 5))), COALESCE(default_broker_sync_interval_seconds, 10))
    );

CREATE TABLE IF NOT EXISTS live_trading_approvals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_account_id uuid NULL REFERENCES broker_accounts(id) ON DELETE SET NULL,
    approved_by uuid NULL REFERENCES users(id) ON DELETE SET NULL,
    status varchar(30) NOT NULL DEFAULT 'PENDING',
    approved_markets jsonb NULL,
    max_daily_loss numeric(18,4) NULL,
    max_order_value numeric(18,4) NULL,
    max_trades_per_day integer NULL,
    notes text NULL,
    risk_disclaimer_accepted_at timestamptz NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_live_trading_approvals_user_status
    ON live_trading_approvals (user_id, status);

CREATE INDEX IF NOT EXISTS idx_live_trading_approvals_broker_status
    ON live_trading_approvals (broker_account_id, status);

CREATE INDEX IF NOT EXISTS idx_live_trading_approvals_created
    ON live_trading_approvals (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_deployments_live_sync
    ON strategy_deployments (status, live_sync_enabled, last_live_sync_at);

CREATE INDEX IF NOT EXISTS idx_strategy_deployments_live_approved
    ON strategy_deployments (live_approved, mode);
