"""Add index on market_data table for instrument_id, timeframe, timestamp

Revision ID: add_market_data_index
Revises: add_job_status_table
Create Date: 2026-02-06 16:53:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_market_data_index'
down_revision: Union[str, None] = 'add_job_status_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create index on market_data table for instrument_id, timeframe, timestamp
    op.create_index(
        'idx_market_data_instrument_tf_ts',
        'market_data',
        ['instrument_id', 'timeframe', 'timestamp']
    )


def downgrade() -> None:
    # Drop the index
    op.drop_index('idx_market_data_instrument_tf_ts', table_name='market_data')