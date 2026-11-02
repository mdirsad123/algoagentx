"""Publish broker feed's missing candles into existing canonical backtest dataset, with audit.

Revision ID: 20261031_market_gap_publish
Revises: 20261031_market_data_auto_sync
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261031_market_gap_publish"
down_revision = "20261031_market_data_auto_sync"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("market_data_sync_configs", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_table("market_data_canonical_provenance",
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id"), primary_key=True),
        sa.Column("timeframe", sa.String(20), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("feed_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("market_data_sync_configs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_market_canonical_provenance_feed", "market_data_canonical_provenance", ["feed_id", "timestamp"])

def downgrade():
    op.drop_index("ix_market_canonical_provenance_feed", table_name="market_data_canonical_provenance")
    op.drop_table("market_data_canonical_provenance")
    op.drop_column("market_data_sync_configs", "is_archived")
