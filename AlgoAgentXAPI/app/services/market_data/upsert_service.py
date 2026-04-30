from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import and_, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import MarketData
from .normalizer import normalize_candles
from .types import CandleImportSummary
from .validator import validate_and_prepare_candles


async def _count_existing_rows(
    db: AsyncSession,
    *,
    instrument_id: int,
    timeframe: str,
    timestamps: list,
) -> int:
    if not timestamps:
        return 0
    result = await db.execute(
        select(func.count())
        .select_from(MarketData)
        .where(
            MarketData.instrument_id == instrument_id,
            MarketData.timeframe == timeframe,
            MarketData.timestamp.in_(timestamps),
        )
    )
    return int(result.scalar() or 0)


async def upsert_market_data_candles(
    db: AsyncSession,
    *,
    instrument_id: int,
    timeframe: str,
    candles: Iterable[Any],
    source: str | None = None,
    dry_run: bool = False,
    commit: bool = False,
) -> CandleImportSummary:
    """Normalize, validate, dedupe, and safely upsert market_data candles.

    This function is intentionally provider-agnostic. It accepts mapping-like rows
    from CSV, MT5, Upstox, Binance, or future broker adapters.

    Notes:
    - Existing `market_data` currently has no source/provider column, so `source`
      is accepted for forward compatibility but not persisted yet.
    - Primary key/upsert target is instrument_id + timeframe + timestamp.
    - If `commit=False` (default), caller controls the transaction.
    """
    if not timeframe or not str(timeframe).strip():
        raise ValueError("timeframe is required")

    normalized, normalize_errors, total_input_rows = normalize_candles(candles)
    prepared, summary = validate_and_prepare_candles(
        normalized,
        total_input_rows=total_input_rows,
        normalize_errors=normalize_errors,
        dry_run=dry_run,
    )

    if not prepared:
        summary.skipped_rows = summary.total_input_rows
        if commit:
            await db.commit()
        return summary

    timestamps = [candle.timestamp for candle in prepared]
    existing_count = await _count_existing_rows(
        db,
        instrument_id=instrument_id,
        timeframe=timeframe,
        timestamps=timestamps,
    )

    if dry_run:
        summary.inserted_rows = 0
        summary.updated_rows = 0
        summary.skipped_rows = summary.invalid_rows + summary.duplicate_rows
        return summary

    values = [candle.to_insert_dict(instrument_id=instrument_id, timeframe=timeframe.strip()) for candle in prepared]
    table = MarketData.__table__
    insert_stmt = pg_insert(table).values(values)
    update_columns = {
        "open": insert_stmt.excluded.open,
        "high": insert_stmt.excluded.high,
        "low": insert_stmt.excluded.low,
        "close": insert_stmt.excluded.close,
        "volume": insert_stmt.excluded.volume,
    }
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[table.c.instrument_id, table.c.timeframe, table.c.timestamp],
        set_=update_columns,
    )

    await db.execute(upsert_stmt)
    if commit:
        await db.commit()

    summary.updated_rows = existing_count
    summary.inserted_rows = max(len(prepared) - existing_count, 0)
    summary.skipped_rows = summary.invalid_rows + summary.duplicate_rows
    return summary
