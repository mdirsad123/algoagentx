-- Phase 18: Broker order sync, position reconciliation, and broker order events
-- Safe/idempotent migration for PostgreSQL/DBeaver.

ALTER TABLE strategy_deployments
    ADD COLUMN IF NOT EXISTS last_broker_sync_at timestamptz NULL;

CREATE TABLE IF NOT EXISTS broker_order_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    broker_provider_code varchar(50) NOT NULL,
    broker_account_id uuid NULL REFERENCES broker_accounts(id) ON DELETE SET NULL,
    deployment_id uuid NULL REFERENCES strategy_deployments(id) ON DELETE SET NULL,
    broker_order_id varchar(255) NULL,
    event_type varchar(80) NOT NULL,
    raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    processed boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_broker_order_events_provider_created
    ON broker_order_events (broker_provider_code, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_broker_order_events_deployment_created
    ON broker_order_events (deployment_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_broker_order_events_order
    ON broker_order_events (broker_order_id);

CREATE INDEX IF NOT EXISTS idx_broker_order_events_processed
    ON broker_order_events (processed);

CREATE INDEX IF NOT EXISTS idx_strategy_deployments_last_broker_sync
    ON strategy_deployments (last_broker_sync_at);

CREATE INDEX IF NOT EXISTS idx_live_orders_broker_order_id
    ON live_orders (broker_order_id);
