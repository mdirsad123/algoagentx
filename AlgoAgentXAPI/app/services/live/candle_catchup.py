"""Pure candle-backlog classification. Never fabricate broker candles or orders.

Times represent candle OPEN UTC timestamps. Exact timeframe sequencing is
required when replaying a deployed strategy; exchange session closures and
missing broker candles must not be guessed away.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


def utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class RecoveryDecision:
    action: str  # PROCESS_NEXT, WAIT_FOR_BACKFILL, UP_TO_DATE, NO_CURSOR
    target: datetime | None
    missing_open: datetime | None
    pending_bars: int


def plan_recovery(*, last_processed: datetime | None, first_pending: datetime | None,
                  newest: datetime | None, timeframe_seconds: int) -> RecoveryDecision:
    if timeframe_seconds <= 0:
        raise ValueError('timeframe_seconds must be positive')
    if last_processed is None:
        return RecoveryDecision('NO_CURSOR', None, None, 0)
    previous = utc(last_processed)
    if newest is None or utc(newest) <= previous:
        return RecoveryDecision('UP_TO_DATE', None, None, 0)
    latest = utc(newest)
    expected = previous + timedelta(seconds=timeframe_seconds)
    pending = max(1, int((latest - previous).total_seconds() // timeframe_seconds))
    if first_pending is None or utc(first_pending) > expected:
        return RecoveryDecision('WAIT_FOR_BACKFILL', None, expected, pending)
    if utc(first_pending) < expected:
        raise ValueError('first_pending must be strictly after cursor')
    return RecoveryDecision('PROCESS_NEXT', expected, None, pending)


def required_broker_fetch_bars(*, newest: datetime, previous: datetime,
                               timeframe_seconds: int, margin: int = 16, limit: int = 2000) -> int | None:
    """Returns None when the missing bar predates the safe broker lookback."""
    steps = max(0, int((utc(newest) - utc(previous)).total_seconds() // timeframe_seconds))
    count = max(36, steps + margin)
    return count if count <= limit else None
