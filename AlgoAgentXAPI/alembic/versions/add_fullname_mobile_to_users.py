"""Add fullname and mobile columns to users table

Revision ID: add_fullname_mobile
Revises: add_unique_constraints_screener
Create Date: 2026-02-13 22:13:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_fullname_mobile'
down_revision = 'add_unique_constraints_screener'
branch_labels = None
depends_on = None


def upgrade():
    # Add fullname column
    op.add_column('users', sa.Column('fullname', sa.String(), nullable=True))
    
    # Add mobile column  
    op.add_column('users', sa.Column('mobile', sa.String(), nullable=True))


def downgrade():
    # Remove fullname column
    op.drop_column('users', 'fullname')
    
    # Remove mobile column
    op.drop_column('users', 'mobile')