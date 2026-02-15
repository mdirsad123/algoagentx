"""Add notifications table

Revision ID: add_notifications_table
Revises: update_backtest_schema
Create Date: 2026-02-06 20:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_notifications_table'
down_revision = 'update_backtest_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('is_read', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create index on user_id for better query performance
    op.create_index('idx_notifications_user_id', 'notifications', ['user_id'])
    
    # Create index on type for filtering by notification type
    op.create_index('idx_notifications_type', 'notifications', ['type'])
    
    # Create index on is_read for filtering read/unread notifications
    op.create_index('idx_notifications_is_read', 'notifications', ['is_read'])


def downgrade():
    op.drop_index('idx_notifications_is_read', table_name='notifications')
    op.drop_index('idx_notifications_type', table_name='notifications')
    op.drop_index('idx_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')