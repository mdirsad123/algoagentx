"""Add is_active and updated_at to users

Revision ID: 20260330_add_user_activity_columns
Revises: add_fullname_mobile
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa


revision = '20260330_add_user_activity_columns'
down_revision = 'add_fullname_mobile'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')))


def downgrade():
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'is_active')
