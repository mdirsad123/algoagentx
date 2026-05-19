"""live order idempotency fix 1

Revision ID: live_order_idempotency_fix_1
Revises: live_approval_unique_pending_approved
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = "live_order_idempotency_fix_1"
down_revision = "live_approval_unique_pending_approved"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE live_orders ADD COLUMN IF NOT EXISTS client_order_id VARCHAR(255)")
    op.execute("ALTER TABLE live_positions ADD COLUMN IF NOT EXISTS broker_position_id VARCHAR(255)")
    op.execute("ALTER TABLE live_positions ADD COLUMN IF NOT EXISTS broker_opened_at TIMESTAMPTZ")
    op.execute("ALTER TABLE live_positions ADD COLUMN IF NOT EXISTS broker_opened_at_raw VARCHAR(100)")

    op.execute("CREATE INDEX IF NOT EXISTS idx_live_orders_client_order_id ON live_orders(client_order_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_live_orders_signal_status ON live_orders(signal_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_live_positions_broker_position ON live_positions(deployment_id, broker_account_id, broker_position_id)")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_live_orders_client_order_id
        ON live_orders(client_order_id)
        WHERE client_order_id IS NOT NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_mt5_place_order_idempotency_key
        ON mt5_agent_commands ((request_payload->>'idempotency_key'))
        WHERE command_type = 'PLACE_ORDER'
          AND request_payload ? 'idempotency_key'
          AND COALESCE(request_payload->>'idempotency_key', '') <> ''
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_live_engine_signal_idempotency_lookup
        ON live_signals(deployment_id, source, symbol, timeframe, signal_type, candle_time)
    """)
    op.execute("""
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY deployment_id, source, symbol, timeframe, signal_type, candle_time
                       ORDER BY created_at ASC, id ASC
                   ) AS rn
            FROM live_signals
            WHERE source = 'ENGINE'
              AND signal_type IN ('BUY','SELL','EXIT')
              AND candle_time IS NOT NULL
              AND COALESCE(status, '') <> 'DUPLICATE'
        )
        UPDATE live_signals ls
        SET status = 'DUPLICATE',
            rejection_reason = COALESCE(ls.rejection_reason, 'Marked duplicate by live_order_idempotency_fix_1 migration')
        FROM ranked r
        WHERE ls.id = r.id AND r.rn > 1
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_live_engine_signal_once_per_candle
        ON live_signals(deployment_id, source, symbol, timeframe, signal_type, candle_time)
        WHERE source = 'ENGINE'
          AND signal_type IN ('BUY','SELL','EXIT')
          AND candle_time IS NOT NULL
          AND COALESCE(status, '') <> 'DUPLICATE'
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_live_engine_signal_once_per_candle")
    op.execute("DROP INDEX IF EXISTS idx_live_engine_signal_idempotency_lookup")
    op.execute("DROP INDEX IF EXISTS uq_mt5_place_order_idempotency_key")
    op.execute("DROP INDEX IF EXISTS uq_live_orders_client_order_id")
    op.execute("DROP INDEX IF EXISTS idx_live_positions_broker_position")
    op.execute("DROP INDEX IF EXISTS idx_live_orders_signal_status")
    op.execute("DROP INDEX IF EXISTS idx_live_orders_client_order_id")
    op.execute("ALTER TABLE live_positions DROP COLUMN IF EXISTS broker_opened_at_raw")
    op.execute("ALTER TABLE live_positions DROP COLUMN IF EXISTS broker_opened_at")
    op.execute("ALTER TABLE live_positions DROP COLUMN IF EXISTS broker_position_id")
    op.execute("ALTER TABLE live_orders DROP COLUMN IF EXISTS client_order_id")
