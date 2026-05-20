"""live candle close scheduler 1

Revision ID: live_candle_close_scheduler_1
Revises: live_order_idempotency_fix_1
Create Date: 2026-05-20
"""
from alembic import op

revision = "live_candle_close_scheduler_1"
down_revision = "live_order_idempotency_fix_1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE strategy_deployments ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMPTZ")
    op.execute("ALTER TABLE strategy_deployments ADD COLUMN IF NOT EXISTS last_runner_wakeup_at TIMESTAMPTZ")
    op.execute("ALTER TABLE strategy_deployments ADD COLUMN IF NOT EXISTS last_processed_candle_time TIMESTAMPTZ")
    op.execute("ALTER TABLE strategy_deployments ADD COLUMN IF NOT EXISTS runner_interval_mode VARCHAR(32) DEFAULT 'CANDLE_CLOSE'")
    op.execute("ALTER TABLE strategy_deployments ADD COLUMN IF NOT EXISTS broker_delay_seconds INTEGER DEFAULT 3")
    op.execute("ALTER TABLE strategy_deployments ADD COLUMN IF NOT EXISTS missed_candle_retry_seconds INTEGER DEFAULT 10")
    op.execute("ALTER TABLE live_orders ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_strategy_deployments_next_run_at ON strategy_deployments(status, auto_runner_enabled, next_run_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_live_orders_idempotency_key ON live_orders(idempotency_key)")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_live_orders_idempotency_key
        ON live_orders(idempotency_key)
        WHERE idempotency_key IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_live_orders_idempotency_key")
    op.execute("DROP INDEX IF EXISTS idx_live_orders_idempotency_key")
    op.execute("DROP INDEX IF EXISTS idx_strategy_deployments_next_run_at")
    op.execute("ALTER TABLE live_orders DROP COLUMN IF EXISTS idempotency_key")
    op.execute("ALTER TABLE strategy_deployments DROP COLUMN IF EXISTS missed_candle_retry_seconds")
    op.execute("ALTER TABLE strategy_deployments DROP COLUMN IF EXISTS broker_delay_seconds")
    op.execute("ALTER TABLE strategy_deployments DROP COLUMN IF EXISTS runner_interval_mode")
    op.execute("ALTER TABLE strategy_deployments DROP COLUMN IF EXISTS last_runner_wakeup_at")
    op.execute("ALTER TABLE strategy_deployments DROP COLUMN IF EXISTS next_run_at")
