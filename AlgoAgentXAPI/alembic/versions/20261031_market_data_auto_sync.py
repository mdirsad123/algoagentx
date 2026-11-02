"""isolated broker market data sync

Revision ID: 20261031_market_data_auto_sync
Revises: 20260925_copy_trading_fanout
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261031_market_data_auto_sync"
down_revision = "20260925_copy_trading_fanout"
branch_labels = None
depends_on = None


def upgrade():
    u = postgresql.UUID(as_uuid=True)
    op.create_table("market_data_sync_configs",
        sa.Column("id", u, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("broker_account_id", u, sa.ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instrument_id", sa.Integer, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("subaccount_id", sa.String(120), nullable=False),
        sa.Column("broker_symbol", sa.String(120), nullable=False),
        sa.Column("timeframe", sa.String(20), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("publish_approved", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("initial_start", sa.DateTime(timezone=True)),
        sa.Column("checkpoint", sa.DateTime(timezone=True)),
        sa.Column("last_status", sa.String(32), nullable=False, server_default="NEEDS_INITIAL_IMPORT"),
        sa.Column("last_error", sa.String(300)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("broker_account_id", "subaccount_id", "instrument_id", "timeframe", "broker_symbol", name="uq_market_sync_source"))
    op.create_index("ix_market_sync_enabled", "market_data_sync_configs", ["enabled"])
    op.create_index("uq_market_sync_primary", "market_data_sync_configs", ["instrument_id", "timeframe"], unique=True, postgresql_where=sa.text("is_primary = true"))
    op.create_table("market_data_feed_candles",
        sa.Column("feed_id", u, sa.ForeignKey("market_data_sync_configs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("open", sa.Numeric, nullable=False), sa.Column("high", sa.Numeric, nullable=False),
        sa.Column("low", sa.Numeric, nullable=False), sa.Column("close", sa.Numeric, nullable=False),
        sa.Column("volume", sa.Numeric, nullable=False, server_default="0"),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_market_feed_candle_time", "market_data_feed_candles", ["feed_id", "timestamp"])
    op.create_table("market_data_sync_batches",
        sa.Column("scheduled_date", sa.Date, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)))
    op.create_table("market_data_sync_runs",
        sa.Column("id", u, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("feed_id", u, sa.ForeignKey("market_data_sync_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_key", sa.String(180), nullable=False),
        sa.Column("scheduled_date", sa.Date),
        sa.Column("requested_start", sa.DateTime(timezone=True)),
        sa.Column("requested_end", sa.DateTime(timezone=True)),
        sa.Column("dry_run", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(32), nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("last_before", sa.DateTime(timezone=True)), sa.Column("last_after", sa.DateTime(timezone=True)),
        sa.Column("fetched", sa.Integer, nullable=False, server_default="0"),
        sa.Column("inserted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer, nullable=False, server_default="0"),
        sa.Column("invalid", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_key", name="uq_market_sync_run_key"))
    op.create_index("ix_market_sync_runs_feed_created", "market_data_sync_runs", ["feed_id", "created_at"])


def downgrade():
    op.drop_table("market_data_sync_runs")
    op.drop_table("market_data_sync_batches")
    op.drop_table("market_data_feed_candles")
    op.drop_table("market_data_sync_configs")
