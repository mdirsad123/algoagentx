"""Lossless ordered equity events and bounded persistence, independent of routes.

Sequence is the occurrence number at the *real* timestamp. No fabricated times,
last-value-wins overwrite, rounding, or conflict suppression is permitted.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from itertools import islice
from math import isfinite

import pandas as pd
from sqlalchemy import text

def iter_equity_events(result):
    values = result.equity_curve
    timestamps = getattr(result, "equity_timestamps", ())
    if len(values) != len(timestamps):
        raise ValueError("Equity values and real timestamps must have equal length")
    previous = None
    sequence = 0
    for value, raw_timestamp in zip(values, timestamps):
        if raw_timestamp is None or pd.isna(raw_timestamp):
            raise ValueError("Equity event has no real timestamp")
        timestamp = raw_timestamp
        if not isinstance(timestamp, datetime):
            timestamp = pd.Timestamp(timestamp).to_pydatetime()
        elif isinstance(timestamp, pd.Timestamp):
            if timestamp.nanosecond:
                raise ValueError("Sub-microsecond equity timestamp cannot be stored losslessly")
            timestamp = timestamp.to_pydatetime()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)
        if previous is not None and timestamp < previous:
            raise ValueError("Equity timestamps must be chronological")
        sequence = sequence + 1 if timestamp == previous else 0
        previous = timestamp
        equity = float(value)
        if not isfinite(equity):
            raise ValueError("Equity must be finite")
        yield {"timestamp": timestamp, "event_sequence": sequence, "equity": equity}


def equity_preview(result, max_points=5000):
    """Sample by event index without materializing the entire event collection."""
    if max_points < 2:
        raise ValueError("Equity preview requires at least two points")
    size = len(result.equity_curve)
    indexes = {round(i * (size - 1) / (max_points - 1)) for i in range(max_points)} if size > max_points else None
    return [
        {**row, "timestamp": row["timestamp"].isoformat()}
        for index, row in enumerate(iter_equity_events(result))
        if indexes is None or index in indexes
    ]


async def persist_equity_events(db, backtest_id, result, *, batch_size=1000):
    """Caller owns transaction and exclusive job claim. Conflicts fail atomically.

Idempotency belongs to the durable job's finalization transaction, not to an
ON CONFLICT clause that could conceal a different result for the same event.
"""
    if not 1 <= batch_size <= 5000:
        raise ValueError("Equity batch size must be between 1 and 5000")
    # Production has legacy TEXT IDs and naive UTC timestamps; do not blindly
    # change their types or bind using an incompatible ORM UUID/TIMESTAMPTZ type.
    metadata = (await db.execute(text("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema=current_schema() AND table_name='equity_curve'
    """))).mappings().all()
    types = {row["column_name"]: row["data_type"] for row in metadata}
    if "event_sequence" not in types:
        raise RuntimeError("Ordered equity migration has not been applied")
    naive = types.get("timestamp") == "timestamp without time zone"
    statement = text("""INSERT INTO equity_curve (backtest_id, timestamp, event_sequence, equity)
        VALUES (:backtest_id, :timestamp, :event_sequence, :equity)""")
    events = iter_equity_events(result)
    inserted = 0
    while batch := list(islice(events, batch_size)):
        from app.services.backtest_control import checkpoint
        checkpoint("equity_persistence", inserted, len(result.equity_curve))
        for row in batch:
            row["backtest_id"] = str(backtest_id)
            if naive:
                row["timestamp"] = row["timestamp"].replace(tzinfo=None)
            row["equity"] = Decimal(str(row["equity"]))
        await db.execute(statement, batch)
        inserted += len(batch)
    return inserted