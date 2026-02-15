"""Add strategy_requests table

Revision ID: add_strategy_requests_table
Revises: add_notifications_table
Create Date: 2026-02-11 15:49:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_strategy_requests_table'
down_revision = 'add_notifications_table'
branch_labels = None
depends_on = None


def upgrade():
    # Create strategy_requests table
    op.create_table(
        'strategy_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('strategy_type', sa.Text, nullable=True),
        sa.Column('market', sa.Text, nullable=True),
        sa.Column('timeframe', sa.Text, nullable=True),
        sa.Column('indicators', postgresql.JSONB, nullable=True),
        sa.Column('entry_rules', sa.Text, nullable=False),
        sa.Column('exit_rules', sa.Text, nullable=False),
        sa.Column('risk_rules', sa.Text, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('status', sa.Text, nullable=False, server_default='UNDER_DEVELOPMENT'),
        sa.Column('admin_notes', sa.Text, nullable=True),
        sa.Column('assigned_to', sa.Text, nullable=True),
        sa.Column('deployed_strategy_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create indexes as specified in requirements
    op.create_index('idx_strategy_requests_user_created', 'strategy_requests', ['user_id', sa.text('created_at DESC')])
    op.create_index('idx_strategy_requests_status_created', 'strategy_requests', ['status', sa.text('created_at DESC')])
    
    # Create index on deployed_strategy_id for better query performance
    op.create_index('idx_strategy_requests_deployed_strategy_id', 'strategy_requests', ['deployed_strategy_id'])


def downgrade():
    op.drop_index('idx_strategy_requests_deployed_strategy_id', table_name='strategy_requests')
    op.drop_index('idx_strategy_requests_status_created', table_name='strategy_requests')
    op.drop_index('idx_strategy_requests_user_created', table_name='strategy_requests')
    op.drop_table('strategy_requests')