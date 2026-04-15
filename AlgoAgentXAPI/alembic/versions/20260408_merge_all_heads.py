"""Merge all Alembic heads for a single upgrade path

Revision ID: 20260408_merge_all_heads
Revises: add_subscription_system, add_screener_tables, add_strategy_requests_table, add_support_tickets_table, 20260408_backend_schema_compat
Create Date: 2026-04-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260408_merge_all_heads'
down_revision = (
    'add_subscription_system',
    'add_screener_tables',
    'add_strategy_requests_table',
    'add_support_tickets_table',
    '20260408_backend_schema_compat',
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
