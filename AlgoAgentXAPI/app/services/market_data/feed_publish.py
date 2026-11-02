"""Publish approved, source-isolated broker candles into canonical backtest history.

Only absent timestamps are inserted; older canonical prices are never rewritten.
The legacy market_data.timestamp column is timestamp WITHOUT time zone in
existing installations, whereas market_data_feed_candles.timestamp is TIMESTAMPTZ.
All comparisons and writes must therefore use a UTC PostgreSQL transaction.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import and_, func, literal, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import MarketData, MarketDataFeedCandle, MarketDataCanonicalProvenance

logger = logging.getLogger(__name__)


async def _utc_transaction(db: AsyncSession) -> None:
    """Force explicit UTC for the CURRENT transaction, not the DB/session globally.

    A timestamp-without-time-zone and a timestamptz compare differently when the
    PostgreSQL session timezone is not UTC. SET LOCAL avoids an offset shift
    when source candles are compared/inserted into existing legacy candles.
    """
    await db.execute(text("SET LOCAL TIME ZONE 'UTC'"))


def canonical_join(config):
    return and_(MarketData.instrument_id == config.instrument_id,
                MarketData.timeframe == config.timeframe,
                MarketData.timestamp == MarketDataFeedCandle.timestamp)


async def preview_publication(db: AsyncSession, config) -> dict:
    """Read-only counts; duplicates and different-price overlaps are not overwritten."""
    await _utc_transaction(db)
    joined = canonical_join(config)
    differs = (MarketData.open.is_distinct_from(MarketDataFeedCandle.open) |
               MarketData.high.is_distinct_from(MarketDataFeedCandle.high) |
               MarketData.low.is_distinct_from(MarketDataFeedCandle.low) |
               MarketData.close.is_distinct_from(MarketDataFeedCandle.close))
    row = (await db.execute(select(
        func.count(MarketDataFeedCandle.timestamp),
        func.count(MarketData.timestamp),
        func.count(MarketDataFeedCandle.timestamp) - func.count(MarketData.timestamp),
        func.count().filter(MarketData.timestamp.is_not(None), differs),
        func.min(MarketDataFeedCandle.timestamp), func.max(MarketDataFeedCandle.timestamp),
    ).select_from(MarketDataFeedCandle).outerjoin(MarketData, joined).where(
        MarketDataFeedCandle.feed_id == config.id))).one()
    return {"source_rows": int(row[0]), "overlapping_rows": int(row[1]),
            "missing_rows": int(row[2]), "different_ohlc_overlaps_preserved": int(row[3]),
            "source_first": row[4], "source_last": row[5],
            "mode": "INSERT_MISSING_ONLY", "overwrites": 0}


def _as_utc(value: datetime) -> datetime:
    """The PostgreSQL RETURNING timestamp can be naive (legacy UTC storage).

    Provenance is a TIMESTAMPTZ column. Never rely on the DB session timezone
    to interpret a returned naive timestamp; the legacy convention is UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _rounded_ohlc(column):
    """At most 5 meaningful decimal places for NEW canonical prices only.

    The existing numeric(65,30) column will still display zero padding in
    some DB clients. The verification SQL exposes a 5dp read-only projection.
    """
    return func.round(column, 5)


async def insert_with_provenance(db: AsyncSession, config, select_rows) -> int:
    """Atomic INSERT-only canonical update plus provenance. Caller commits.

    The select_rows comes exclusively from the named feed, never from the
    generic provider registry. The INSERT RETURNING timestamps identify exactly
    the rows actually inserted, even when concurrent jobs hit ON CONFLICT.
    """
    await _utc_transaction(db)
    insert_stmt = pg_insert(MarketData.__table__).from_select(
        ["instrument_id", "timeframe", "timestamp", "open", "high", "low", "close", "volume"], select_rows
    ).on_conflict_do_nothing(index_elements=["instrument_id", "timeframe", "timestamp"]).returning(MarketData.timestamp)
    inserted_times = list((await db.execute(insert_stmt)).scalars().all())
    if inserted_times:
        values = [{"instrument_id": config.instrument_id, "timeframe": config.timeframe,
                   "timestamp": _as_utc(ts), "feed_id": config.id} for ts in inserted_times]
        await db.execute(pg_insert(MarketDataCanonicalProvenance.__table__).values(values).on_conflict_do_nothing(
            index_elements=["instrument_id", "timeframe", "timestamp"]))
    return len(inserted_times)


async def publish_selected_candles(db: AsyncSession, config, timestamps: list) -> int:
    """Publish verified, closed source rows from the exact approved feed.

    Duplicate historical timestamps don't overwrite existing canonical rows.
    An approved feed is required even for automatic/Run Now imports.
    """
    if not timestamps or not (config.is_primary and config.publish_approved) or config.is_archived:
        return 0
    await _utc_transaction(db)
    q = select(
        literal(config.instrument_id), literal(config.timeframe),
        MarketDataFeedCandle.timestamp,
        _rounded_ohlc(MarketDataFeedCandle.open),
        _rounded_ohlc(MarketDataFeedCandle.high),
        _rounded_ohlc(MarketDataFeedCandle.low),
        _rounded_ohlc(MarketDataFeedCandle.close),
        MarketDataFeedCandle.volume,
    ).where(MarketDataFeedCandle.feed_id == config.id,
            MarketDataFeedCandle.timestamp.in_(timestamps))
    return await insert_with_provenance(db, config, q)


async def publish_all_missing(db: AsyncSession, config, run) -> str:
    """Backfill SAVED source history in bounded idempotent pages.

    A retry starts at the first source timestamp and skips already-published
    rows; every page commits its inserted rows and provenance together.
    """
    if config.is_archived or not (config.is_primary and config.publish_approved):
        raise ValueError("Canonical publishing requires an active, approved Primary feed")
    limit = max(100, min(2000, int(os.getenv("MARKET_DATA_PUBLISH_PAGE_SIZE", "1000"))))
    cursor = None
    old_last = (await db.execute(select(func.max(MarketData.timestamp)).where(
        MarketData.instrument_id == config.instrument_id,
        MarketData.timeframe == config.timeframe))).scalar_one_or_none()
    run.last_before = _as_utc(old_last) if old_last is not None else None
    while True:
        query = select(MarketDataFeedCandle.timestamp).where(MarketDataFeedCandle.feed_id == config.id)
        if cursor is not None:
            query = query.where(MarketDataFeedCandle.timestamp > cursor)
        times = list((await db.execute(query.order_by(MarketDataFeedCandle.timestamp).limit(limit))).scalars().all())
        if not times:
            break
        inserted = await publish_selected_candles(db, config, times)
        run.fetched += len(times)       # reviewed source rows, NOT broker API calls
        run.inserted += inserted       # NEW canonical backtest rows
        run.skipped += len(times) - inserted
        cursor = times[-1]
        new_last = (await db.execute(select(func.max(MarketData.timestamp)).where(
            MarketData.instrument_id == config.instrument_id,
            MarketData.timeframe == config.timeframe))).scalar_one_or_none()
        run.last_after = _as_utc(new_last) if new_last is not None else None
        await db.commit()
        logger.info("Canonical publish page completed feed=%s canonical_added=%d source_checked=%d",
                    config.id, inserted, len(times))
        await asyncio.sleep(0)
    return "UP_TO_DATE" if run.fetched else "NO_NEW_CANDLE"
