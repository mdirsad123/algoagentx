"""Pure, testable health policy for the independent TradeLocker candle collector.

A live process heartbeat does NOT imply broker polling has progressed.
Only actual recent completed poll cycles establish collector ownership.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


def _timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        timestamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def collector_status(stats: dict, now: datetime, *, stale_seconds: int = 420, startup_seconds: int = 90) -> str:
    """Return STARTING/HEALTHY/DEGRADED/IDLE based on actual polling, not mere process liveness."""
    if stats.get('last_error'):
        return 'DEGRADED'
    if int(stats.get('deployments') or 0) == 0:
        return 'IDLE'  # Zero matched deployments is not a healthy trading feed.
    last_completed = _timestamp(stats.get('last_poll_completed_at'))
    if last_completed is not None:
        return 'HEALTHY' if 0 <= (now - last_completed).total_seconds() <= stale_seconds else 'DEGRADED'
    started = _timestamp(stats.get('started_at'))
    return 'STARTING' if started and 0 <= (now - started).total_seconds() < startup_seconds else 'DEGRADED'


def collector_owns_broker_ingestion(heartbeat: dict | None, now: datetime, *, stale_seconds: int = 420) -> bool:
    """Runner trusts collector only if its heartbeat AND its poll progress are fresh.

    Old containers that lack last_poll_completed_at are intentionally considered
    unverified: they must not hold the scheduler in permanent DB-only wait.
    """
    if not isinstance(heartbeat, dict) or heartbeat.get('status') != 'HEALTHY':
        return False
    completed = _timestamp(heartbeat.get('last_poll_completed_at'))
    heartbeat_at = _timestamp(heartbeat.get('heartbeat_at'))
    return bool(completed and heartbeat_at and
                0 <= (now - completed).total_seconds() <= stale_seconds and
                0 <= (now - heartbeat_at).total_seconds() <= 90)
