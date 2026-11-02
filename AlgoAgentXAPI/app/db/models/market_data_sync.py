"""Isolated historical broker feeds. Never reuse live_market_candles or overwrite legacy market_data."""
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from ..base import Base


class MarketDataSyncConfig(Base):
    __tablename__ = "market_data_sync_configs"
    __table_args__ = (
        UniqueConstraint("broker_account_id", "subaccount_id", "instrument_id", "timeframe", "broker_symbol", name="uq_market_sync_source"),
        Index("ix_market_sync_enabled", "enabled"),
        Index("uq_market_sync_primary", "instrument_id", "timeframe", unique=True, postgresql_where=text("is_primary = true")),
    )
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    broker_account_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    provider = Column(String(50), nullable=False)
    subaccount_id = Column(String(120), nullable=False)
    broker_symbol = Column(String(120), nullable=False)
    timeframe = Column(String(20), nullable=False)
    enabled = Column(Boolean, nullable=False, server_default=text("false"))
    is_archived = Column(Boolean, nullable=False, server_default=text("false"))
    is_primary = Column(Boolean, nullable=False, server_default=text("false"))
    # Publishing is intentionally opt-out until an independent source-adoption/migration audit.
    # No UI flag enables publish to a legacy market_data table with unknown provenance.
    publish_approved = Column(Boolean, nullable=False, server_default=text("false"))
    initial_start = Column(DateTime(timezone=True), nullable=True)
    checkpoint = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(String(32), nullable=False, server_default="NEEDS_INITIAL_IMPORT")
    last_error = Column(String(300), nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class MarketDataFeedCandle(Base):
    __tablename__ = "market_data_feed_candles"
    __table_args__ = (Index("ix_market_feed_candle_time", "feed_id", "timestamp"),)
    feed_id = Column(PG_UUID(as_uuid=True), ForeignKey("market_data_sync_configs.id", ondelete="CASCADE"), primary_key=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True)
    open = Column(Numeric, nullable=False)
    high = Column(Numeric, nullable=False)
    low = Column(Numeric, nullable=False)
    close = Column(Numeric, nullable=False)
    volume = Column(Numeric, nullable=False, server_default="0")
    stored_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MarketDataSyncBatch(Base):
    __tablename__ = "market_data_sync_batches"
    scheduled_date = Column(Date, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    dispatched_at = Column(DateTime(timezone=True), nullable=True)


class MarketDataSyncRun(Base):
    __tablename__ = "market_data_sync_runs"
    __table_args__ = (
        UniqueConstraint("run_key", name="uq_market_sync_run_key"),
        Index("ix_market_sync_runs_feed_created", "feed_id", "created_at"),
    )
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    feed_id = Column(PG_UUID(as_uuid=True), ForeignKey("market_data_sync_configs.id", ondelete="CASCADE"), nullable=False)
    run_key = Column(String(180), nullable=False)
    scheduled_date = Column(Date, nullable=True)
    requested_start = Column(DateTime(timezone=True), nullable=True)
    requested_end = Column(DateTime(timezone=True), nullable=True)
    dry_run = Column(Boolean, nullable=False, server_default=text("false"))
    status = Column(String(32), nullable=False, server_default="QUEUED")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    last_before = Column(DateTime(timezone=True), nullable=True)
    last_after = Column(DateTime(timezone=True), nullable=True)
    fetched = Column(Integer, nullable=False, server_default="0")
    inserted = Column(Integer, nullable=False, server_default="0")
    updated = Column(Integer, nullable=False, server_default="0")
    skipped = Column(Integer, nullable=False, server_default="0")
    invalid = Column(Integer, nullable=False, server_default="0")
    retry_count = Column(Integer, nullable=False, server_default="0")
    error = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MarketDataCanonicalProvenance(Base):
    """For every newly inserted canonical candle, record the exact source feed.

    Pre-existing legacy candles intentionally have no provenance, and are not overwritten.
    """
    __tablename__ = "market_data_canonical_provenance"
    instrument_id = Column(Integer, ForeignKey("instruments.id"), primary_key=True)
    timeframe = Column(String(20), primary_key=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True)
    feed_id = Column(PG_UUID(as_uuid=True), ForeignKey("market_data_sync_configs.id", ondelete="RESTRICT"), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (Index("ix_market_canonical_provenance_feed", "feed_id", "timestamp"),)
