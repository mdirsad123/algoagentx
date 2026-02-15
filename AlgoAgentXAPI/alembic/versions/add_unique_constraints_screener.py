"""Add unique constraints for screener tables

Revision ID: add_unique_constraints_screener
Revises: 003_add_missing_indexes_constraints
Create Date: 2026-02-13 14:57:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_unique_constraints_screener'
down_revision = '003_add_missing_indexes_constraints'
branch_labels = None
depends_on = None


def upgrade():
    # Add unique constraint for screener_news table
    op.create_unique_constraint(
        'uq_news_symbol_date_title',
        'screener_news',
        ['symbol', 'news_date', 'title']
    )
    
    # Add unique constraint for screener_announcements table
    op.create_unique_constraint(
        'uq_announcements_symbol_date_title_exchange',
        'screener_announcements',
        ['symbol', 'announce_date', 'title', 'exchange']
    )


def downgrade():
    # Drop unique constraints
    op.drop_constraint('uq_news_symbol_date_title', 'screener_news', type_='unique')
    op.drop_constraint('uq_announcements_symbol_date_title_exchange', 'screener_announcements', type_='unique')