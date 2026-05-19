"""Add partial unique indexes for live broker approvals

Revision ID: live_approval_unique_pending_approved
Revises: add_subscription_system
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "live_approval_unique_pending_approved"
down_revision: Union[str, None] = "add_subscription_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_live_approval_one_pending_per_broker
        ON live_trading_approvals(user_id, broker_account_id)
        WHERE status = 'PENDING' AND broker_account_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_live_approval_one_approved_per_broker
        ON live_trading_approvals(user_id, broker_account_id)
        WHERE status = 'APPROVED' AND broker_account_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_live_approval_one_approved_per_broker")
    op.execute("DROP INDEX IF EXISTS uq_live_approval_one_pending_per_broker")
