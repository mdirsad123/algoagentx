"""Add support tickets tables

Revision ID: add_support_tickets_table
Revises: add_notifications_table
Create Date: 2026-02-15 20:11:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_support_tickets_table'
down_revision = 'add_notifications_table'
branch_labels = None
depends_on = None


def upgrade():
    # Create ticket_status enum
    ticket_status = postgresql.ENUM('open', 'in_progress', 'closed', name='ticket_status')
    ticket_status.create(op.get_bind())
    
    # Create ticket_priority enum
    ticket_priority = postgresql.ENUM('low', 'medium', 'high', name='ticket_priority')
    ticket_priority.create(op.get_bind())
    
    # Create support_tickets table
    op.create_table(
        'support_tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('status', ticket_status, default='open', nullable=False),
        sa.Column('priority', ticket_priority, default='medium', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    
    # Create support_ticket_replies table
    op.create_table(
        'support_ticket_replies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('support_tickets.id'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),  # nullable for system messages
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_support_tickets_user_id', 'support_tickets', ['user_id'])
    op.create_index('idx_support_tickets_status', 'support_tickets', ['status'])
    op.create_index('idx_support_tickets_priority', 'support_tickets', ['priority'])
    op.create_index('idx_support_tickets_created_at', 'support_tickets', ['created_at'])
    op.create_index('idx_support_ticket_replies_ticket_id', 'support_ticket_replies', ['ticket_id'])
    op.create_index('idx_support_ticket_replies_user_id', 'support_ticket_replies', ['user_id'])


def downgrade():
    op.drop_index('idx_support_ticket_replies_user_id', table_name='support_ticket_replies')
    op.drop_index('idx_support_ticket_replies_ticket_id', table_name='support_ticket_replies')
    op.drop_index('idx_support_tickets_created_at', table_name='support_tickets')
    op.drop_index('idx_support_tickets_priority', table_name='support_tickets')
    op.drop_index('idx_support_tickets_status', table_name='support_tickets')
    op.drop_index('idx_support_tickets_user_id', table_name='support_tickets')
    op.drop_table('support_ticket_replies')
    op.drop_table('support_tickets')
    op.execute('DROP TYPE ticket_priority')
    op.execute('DROP TYPE ticket_status')