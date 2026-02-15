"""Update backtest schema to performance_metrics

Revision ID: update_backtest_schema
Revises: <previous_revision>
Create Date: 2024-01-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_backtest_schema'
down_revision = None  # Set to actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Rename table backtests to performance_metrics
    op.rename_table('backtests', 'performance_metrics')

    # Change id column from VARCHAR to UUID
    # First, add a new UUID column
    op.add_column('performance_metrics', sa.Column('id_new', postgresql.UUID(as_uuid=True), default=sa.text('gen_random_uuid()')))

    # Copy data: assuming existing id is string, generate new UUID
    # In production, you might need to map existing string IDs to UUIDs
    op.execute('UPDATE performance_metrics SET id_new = gen_random_uuid()')

    # Drop old id column and rename new one
    op.drop_column('performance_metrics', 'id')
    op.alter_column('performance_metrics', 'id_new', new_column_name='id')

    # Add new columns
    op.add_column('performance_metrics', sa.Column('sortino_ratio', sa.Numeric(), nullable=True))
    op.add_column('performance_metrics', sa.Column('calmar_ratio', sa.Numeric(), nullable=True))
    op.add_column('performance_metrics', sa.Column('win_rate', sa.Numeric(), nullable=True))
    op.add_column('performance_metrics', sa.Column('total_trades', sa.Integer(), nullable=True))
    op.add_column('performance_metrics', sa.Column('winning_trades', sa.Integer(), nullable=True))
    op.add_column('performance_metrics', sa.Column('losing_trades', sa.Integer(), nullable=True))
    op.add_column('performance_metrics', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))

    # Update foreign keys in related tables
    op.drop_constraint('trades_backtest_id_fkey', 'trades', type_='foreignkey')
    op.create_foreign_key('trades_backtest_id_fkey', 'trades', 'performance_metrics', ['backtest_id'], ['id'])

    op.drop_constraint('equity_curve_backtest_id_fkey', 'equity_curve', type_='foreignkey')
    op.create_foreign_key('equity_curve_backtest_id_fkey', 'equity_curve', 'performance_metrics', ['backtest_id'], ['id'])

    op.drop_constraint('pnl_calendar_backtest_id_fkey', 'pnl_calendar', type_='foreignkey')
    op.create_foreign_key('pnl_calendar_backtest_id_fkey', 'pnl_calendar', 'performance_metrics', ['backtest_id'], ['id'])

    # Update backtest_id in related tables to UUID
    # This assumes backtest_id was VARCHAR matching the old id
    # In production, map properly
    op.alter_column('trades', 'backtest_id', type_=postgresql.UUID(as_uuid=True))
    op.alter_column('equity_curve', 'backtest_id', type_=postgresql.UUID(as_uuid=True))
    op.alter_column('pnl_calendar', 'backtest_id', type_=postgresql.UUID(as_uuid=True))


def downgrade():
    # Reverse operations
    op.alter_column('pnl_calendar', 'backtest_id', type_=sa.String())
    op.alter_column('equity_curve', 'backtest_id', type_=sa.String())
    op.alter_column('trades', 'backtest_id', type_=sa.String())

    op.drop_constraint('pnl_calendar_backtest_id_fkey', 'pnl_calendar', type_='foreignkey')
    op.create_foreign_key('pnl_calendar_backtest_id_fkey', 'pnl_calendar', 'backtests', ['backtest_id'], ['id'])

    op.drop_constraint('equity_curve_backtest_id_fkey', 'equity_curve', type_='foreignkey')
    op.create_foreign_key('equity_curve_backtest_id_fkey', 'equity_curve', 'backtests', ['backtest_id'], ['id'])

    op.drop_constraint('trades_backtest_id_fkey', 'trades', type_='foreignkey')
    op.create_foreign_key('trades_backtest_id_fkey', 'trades', 'backtests', ['backtest_id'], ['id'])

    op.drop_column('performance_metrics', 'updated_at')
    op.drop_column('performance_metrics', 'losing_trades')
    op.drop_column('performance_metrics', 'winning_trades')
    op.drop_column('performance_metrics', 'total_trades')
    op.drop_column('performance_metrics', 'win_rate')
    op.drop_column('performance_metrics', 'calmar_ratio')
    op.drop_column('performance_metrics', 'sortino_ratio')

    op.alter_column('performance_metrics', 'id', type_=sa.String())
    op.rename_table('performance_metrics', 'backtests')
