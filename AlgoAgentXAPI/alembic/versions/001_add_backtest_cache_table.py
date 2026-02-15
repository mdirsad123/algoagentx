"""Add backtest_runs table for caching backtest results

Revision ID: 001_add_backtest_cache_table
Revises: add_notifications_table
Create Date: 2026-02-06 20:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_backtest_cache_table'
down_revision = 'add_notifications_table'
branch_labels = None
depends_on = None


def upgrade():
    # Create backtest_runs table
    op.create_table('backtest_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('cache_key', sa.String(length=255), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'cache_key', name='uq_user_cache_key')
    )

    # Create indexes for better performance
    op.create_index('ix_backtest_runs_user_id', 'backtest_runs', ['user_id'])
    op.create_index('ix_backtest_runs_cache_key', 'backtest_runs', ['cache_key'])
    op.create_index('ix_backtest_runs_job_id', 'backtest_runs', ['job_id'])
    op.create_index('ix_backtest_runs_created_at', 'backtest_runs', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_backtest_runs_created_at', table_name='backtest_runs')
    op.drop_index('ix_backtest_runs_job_id', table_name='backtest_runs')
    op.drop_index('ix_backtest_runs_cache_key', table_name='backtest_runs')
    op.drop_index('ix_backtest_runs_user_id', table_name='backtest_runs')

    # Drop table
    op.drop_table('backtest_runs')