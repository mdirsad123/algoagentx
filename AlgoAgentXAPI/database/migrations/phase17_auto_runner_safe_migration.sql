-- Phase 17: Automatic strategy runner scheduler
-- Safe/idempotent migration for DBeaver/PostgreSQL.

ALTER TABLE strategy_deployments
    ADD COLUMN IF NOT EXISTS auto_runner_enabled boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS last_runner_at timestamptz NULL,
    ADD COLUMN IF NOT EXISTS last_processed_candle_time timestamptz NULL,
    ADD COLUMN IF NOT EXISTS runner_error_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS runner_last_error text NULL;

UPDATE strategy_deployments
SET auto_runner_enabled = COALESCE(auto_runner_enabled, false),
    runner_error_count = COALESCE(runner_error_count, 0)
WHERE auto_runner_enabled IS NULL OR runner_error_count IS NULL;

CREATE INDEX IF NOT EXISTS idx_strategy_deployments_auto_runner
    ON strategy_deployments (status, auto_runner_enabled, auto_trade_enabled, last_runner_at);

CREATE INDEX IF NOT EXISTS idx_strategy_deployments_processed_candle
    ON strategy_deployments (last_processed_candle_time);
