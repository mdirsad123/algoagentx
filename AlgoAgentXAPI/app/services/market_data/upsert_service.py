from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import MarketData
from .normalizer import normalize_candles
from .types import CandleImportSummary
from .validator import validate_and_prepare_candles


def _chunked(values: Sequence[Any], size: int) -> list[Sequence[Any]]:
    safe_size = max(int(size or 1000), 1)
    return [values[index : index + safe_size] for index in range(0, len(values), safe_size)]


async def _count_existing_rows(
    db: AsyncSession,
    *,
    instrument_id: int,
    timeframe: str,
    timestamps: list,
    batch_size: int = 1000,
) -> int:
    if not timestamps:
        return 0

    total = 0
    for batch in _chunked(timestamps, batch_size):
        result = await db.execute(
            select(func.count())
            .select_from(MarketData)
            .where(
                MarketData.instrument_id == instrument_id,
                MarketData.timeframe == timeframe,
                MarketData.timestamp.in_(list(batch)),
            )
        )
        total += int(result.scalar() or 0)
    return total


async def upsert_market_data_candles(
    db: AsyncSession,
    *,
    instrument_id: int,
    timeframe: str,
    candles: Iterable[Any],
    source: str | None = None,
    dry_run: bool = False,
    commit: bool = False,
    batch_size: int = 1000,
) -> CandleImportSummary:
    """Normalize, validate, dedupe, and safely upsert market_data candles.

    Large intraday imports are executed in chunks so 5m MT5/Upstox imports do
    not create one giant INSERT..ON CONFLICT statement that can timeout.
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
        batch_size=batch_size,
    )

    if dry_run:
        summary.inserted_rows = 0
        summary.updated_rows = 0
        summary.skipped_rows = summary.invalid_rows + summary.duplicate_rows
        return summary

    values = [candle.to_insert_dict(instrument_id=instrument_id, timeframe=timeframe.strip()) for candle in prepared]
    table = MarketData.__table__

    for batch in _chunked(values, batch_size):
        insert_stmt = pg_insert(table).values(list(batch))
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
