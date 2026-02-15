"""Add screener tables

Revision ID: add_screener_tables
Revises: add_notifications_table
Create Date: 2026-02-12 20:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_screener_tables'
down_revision = 'add_notifications_table'
branch_labels = None
depends_on = None


def upgrade():
    # Create screener_news table
    op.create_table(
        'screener_news',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('stock_name', sa.String(200), nullable=False),
        sa.Column('news_date', sa.Date, nullable=False, index=True),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('url', sa.Text, nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('sentiment_label', sa.String(20), nullable=False),
        sa.Column('sentiment_score', sa.Float, nullable=False),
        sa.Column('confidence', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create screener_announcements table
    op.create_table(
        'screener_announcements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('stock_name', sa.String(200), nullable=False),
        sa.Column('exchange', sa.String(10), nullable=False),
        sa.Column('announce_date', sa.Date, nullable=False, index=True),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('url', sa.Text, nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create screener_runs table
    op.create_table(
        'screener_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('run_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('meta', postgresql.JSONB, nullable=True),
    )


def downgrade():
    op.drop_table('screener_runs')
    op.drop_table('screener_announcements')
    op.drop_table('screener_news')