from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.timezone import ensure_utc, iso_utc


def timeframe_to_minutes(timeframe: str | None) -> int:
    value = str(timeframe or "5m").strip().lower()
    mapping = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "60m": 60,
        "4h": 240,
        "240m": 240,
        "1d": 1440,
        "d": 1440,
        "day": 1440,
    }
    if value in mapping:
        return mapping[value]
    try:
        if value.endswith("m"):
            return max(1, int(value[:-1]))
        if value.endswith("h"):
            return max(1, int(value[:-1]) * 60)
        if value.endswith("d"):
            return max(1, int(value[:-1]) * 1440)
    except Exception:
        pass
    return 5


async def _market_timestamp_timezone_mode(db: AsyncSession) -> bool:
    """Return True when market_data.timestamp is timezone-aware.

    AlgoAgentX has legacy deployments where the physical PostgreSQL column is
    TIMESTAMP WITHOUT TIME ZONE even though the current SQLAlchemy model is
    DateTime(timezone=True). Raw SQL must bind a matching datetime type or
    asyncpg raises an offset-aware/offset-naive datetime error. This was the
    chart regression exposed by the IST display patch.
    """
    bind = db.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    if dialect == "sqlite":
        return False
    try:
        value = (
            await db.execute(
                text(
                    """
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'market_data'
                      AND column_name = 'timestamp'
                    LIMIT 1
                    """
                )
            )
        ).scalar()
        normalized = str(value or "").strip().lower()
        if "without time zone" in normalized:
            return False
        if "with time zone" in normalized:
            return True
    except Exception:
        pass
    # Current schema/model contract is timestamptz. Prefer that if metadata is
    # unavailable; callers still get a clean warning rather than a crash.
    return True


def _db_datetime(value: Any, *, timezone_aware: bool) -> datetime | None:
    dt = ensure_utc(value)
    if dt is None:
        return None
    return dt if timezone_aware else dt.replace(tzinfo=None)


def _serialize_rows(rows: list[Any]) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    for row in rows:
        item = row if isinstance(row, dict) else dict(getattr(row, "_mapping", row))
        ts = item.get("timestamp")
        candles.append(
            {
                "timestamp": iso_utc(ts) or (str(ts) if ts is not None else ""),
                "open": float(item.get("open") or 0),
                "high": float(item.get("high") or 0),
                "low": float(item.get("low") or 0),
                "close": float(item.get("close") or 0),
                "volume": float(item.get("volume") or 0),
            }
        )
    dedup = {candle["timestamp"]: candle for candle in candles if candle.get("timestamp")}
    return sorted(dedup.values(), key=lambda item: item["timestamp"])


async def _query_window(
    db: AsyncSession,
    *,
    instrument_id: Any,
    timeframe: str,
    entry_time: datetime,
    exit_time: datetime,
    timezone_aware: bool,
    candles_before: int,
    candles_after: int,
) -> list[dict[str, Any]]:
    entry_param = _db_datetime(entry_time, timezone_aware=timezone_aware)
    exit_param = _db_datetime(exit_time, timezone_aware=timezone_aware)
    if entry_param is None or exit_param is None:
        return []

    dt_type = DateTime(timezone=timezone_aware)
    prev_stmt = text(
        """
        SELECT timestamp, open, high, low, close, volume
        FROM market_data
        WHERE instrument_id = :instrument_id
          AND timeframe = :timeframe
          AND timestamp < :entry_time
        ORDER BY timestamp DESC
        LIMIT :candles_before
        """
    ).bindparams(bindparam("entry_time", type_=dt_type))
    range_stmt = text(
        """
        SELECT timestamp, open, high, low, close, volume
        FROM market_data
        WHERE instrument_id = :instrument_id
          AND timeframe = :timeframe
          AND timestamp >= :entry_time
          AND timestamp <= :exit_time
        ORDER BY timestamp ASC
        """
    ).bindparams(bindparam("entry_time", type_=dt_type), bindparam("exit_time", type_=dt_type))
    after_stmt = text(
        """
        SELECT timestamp, open, high, low, close, volume
        FROM market_data
        WHERE instrument_id = :instrument_id
          AND timeframe = :timeframe
          AND timestamp > :exit_time
        ORDER BY timestamp ASC
        LIMIT :candles_after
        """
    ).bindparams(bindparam("exit_time", type_=dt_type))

    common = {"instrument_id": instrument_id, "timeframe": timeframe}
    prev_rows = (
        await db.execute(prev_stmt, {**common, "entry_time": entry_param, "candles_before": candles_before})
    ).mappings().all()
    range_rows = (
        await db.execute(range_stmt, {**common, "entry_time": entry_param, "exit_time": exit_param})
    ).mappings().all()
    after_rows = (
        await db.execute(after_stmt, {**common, "exit_time": exit_param, "candles_after": candles_after})
    ).mappings().all()
    return _serialize_rows(list(reversed(prev_rows)) + list(range_rows) + list(after_rows))


async def load_trade_chart_candles(
    db: AsyncSession,
    *,
    instrument_id: Any,
    timeframe: str | None,
    entry_time: Any,
    exit_time: Any = None,
    candles_before: int = 50,
    candles_after: int = 30,
    allow_legacy_ist_shift_fallback: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load the visual candle window without changing canonical stored times.

    Primary lookup is the exact UTC instant. If an old row was historically
    persisted with an IST wall-clock value but no zone, a final compatibility
    lookup tries +/-05:30 only when the canonical lookup returns zero candles.
    This fallback is explicitly reported in metadata and never mutates DB data.
    """
    entry = ensure_utc(entry_time)
    if entry is None:
        return [], {"warning": "Trade entry time is missing or invalid."}
    exit_dt = ensure_utc(exit_time)
    if exit_dt is None:
        exit_dt = entry + timedelta(minutes=timeframe_to_minutes(timeframe) * 30)

    timezone_aware = await _market_timestamp_timezone_mode(db)
    meta: dict[str, Any] = {
        "market_timestamp_storage": "TIMESTAMPTZ" if timezone_aware else "TIMESTAMP_WITHOUT_TIME_ZONE",
        "lookup_shift_minutes": 0,
        "lookup_entry_time": iso_utc(entry),
        "lookup_exit_time": iso_utc(exit_dt),
    }

    candles = await _query_window(
        db,
        instrument_id=instrument_id,
        timeframe=str(timeframe or "5m"),
        entry_time=entry,
        exit_time=exit_dt,
        timezone_aware=timezone_aware,
        candles_before=candles_before,
        candles_after=candles_after,
    )
    if candles or not allow_legacy_ist_shift_fallback:
        return candles, meta

    # Compatibility only for legacy records. Canonical UTC remains the source
    # of truth for all new writes.
    for shift_minutes in (-330, 330):
        shifted_entry = entry + timedelta(minutes=shift_minutes)
        shifted_exit = exit_dt + timedelta(minutes=shift_minutes)
        shifted = await _query_window(
            db,
            instrument_id=instrument_id,
            timeframe=str(timeframe or "5m"),
            entry_time=shifted_entry,
            exit_time=shifted_exit,
            timezone_aware=timezone_aware,
            candles_before=candles_before,
            candles_after=candles_after,
        )
        if shifted:
            meta.update(
                {
                    "lookup_shift_minutes": shift_minutes,
                    "lookup_entry_time": iso_utc(shifted_entry),
                    "lookup_exit_time": iso_utc(shifted_exit),
                    "warning": (
                        "Chart candles were recovered with legacy IST/UTC timestamp alignment "
                        f"({shift_minutes:+d} minutes). Stored trade timestamps were not modified."
                    ),
                }
            )
            return shifted, meta

    meta["warning"] = "No candle data found for this trade context."
    return [], meta
