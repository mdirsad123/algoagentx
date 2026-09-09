"""remove live trading approvals table

Revision ID: remove_live_trading_approvals_table
Revises: live_candle_close_scheduler_1
Create Date: 2026-05-24 00:00:00.000000
"""
from alembic import op

revision = "remove_live_trading_approvals_table"
down_revision = "live_candle_close_scheduler_1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_live_approval_one_approved_per_broker")
    op.execute("DROP INDEX IF EXISTS uq_live_approval_one_pending_per_broker")
    op.execute("DROP TABLE IF EXISTS live_trading_approvals")


def downgrade() -> None:
    pass
