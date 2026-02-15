"""Add job status table for background tasks

Revision ID: add_job_status_table
Revises: update_backtest_schema
Create Date: 2026-01-23 00:19:20.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_job_status_table'
down_revision: Union[str, None] = 'update_backtest_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create job_status table
    op.create_table('job_status',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=True, default=0),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=True, default=3),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('job_data', sa.Text(), nullable=True),
        sa.Column('result_data', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop job_status table
    op.drop_table('job_status')
