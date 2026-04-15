"""backend schema compatibility fixes

Revision ID: 20260408_backend_schema_compat
Revises: 20260330_add_user_activity_columns
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260408_backend_schema_compat'
down_revision = '20260330_add_user_activity_columns'
branch_labels = None
depends_on = None


def _has_table(bind, table_name):
    insp = sa.inspect(bind)
    return table_name in insp.get_table_names()


def _has_column(bind, table_name, column_name):
    insp = sa.inspect(bind)
    return any(col['name'] == column_name for col in insp.get_columns(table_name))


def upgrade():
    bind = op.get_bind()
    if _has_table(bind, 'users') and not _has_column(bind, 'users', 'is_active'):
        op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))

    if _has_table(bind, 'payments') and not _has_column(bind, 'payments', 'updated_at'):
        op.add_column('payments', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    if _has_table(bind, 'strategy_requests') and not _has_column(bind, 'strategy_requests', 'deployed_strategy_id'):
        op.add_column('strategy_requests', sa.Column('deployed_strategy_id', postgresql.UUID(as_uuid=True), nullable=True))

    if not _has_table(bind, 'support_tickets'):
        ticket_status = postgresql.ENUM('open', 'in_progress', 'closed', name='ticket_status', create_type=False)
        ticket_priority = postgresql.ENUM('low', 'medium', 'high', name='ticket_priority', create_type=False)
        ticket_status.create(bind, checkfirst=True)
        ticket_priority.create(bind, checkfirst=True)
        op.create_table('support_tickets',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('subject', sa.String(length=255), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('status', ticket_status, nullable=False, server_default='open'),
            sa.Column('priority', ticket_priority, nullable=False, server_default='medium'),
            sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        )

    if not _has_table(bind, 'support_ticket_replies'):
        op.create_table('support_ticket_replies',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('ticket_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('support_tickets.id'), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        )


def downgrade():
    pass
