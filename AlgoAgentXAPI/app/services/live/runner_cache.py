"""Conservative process-local scheduling caches for the legacy REST runner.

Only positive history observations and advisory scheduling hints are cached.
The deployment status, kill switch, broker positions, and order idempotency are
ALWAYS checked by the authoritative execution path before an order.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def _status(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    return str(value or "").upper()


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


@dataclass
class WarmupHold:
    required: int
    created: float
    next_probe: float
    fallback_at: float


class WarmupDispatchGate:
    """Throttle repeated 80K history checks while Celery backfills.

    A READY Redis status is only an *invitation to retry* the authoritative SQL
    query. Missing Redis/status always falls back to SQL after bounded time;
    neither the Redis record nor this cache grants trading permission.
    """

    def __init__(self, *, probe_seconds: float = 5.0, fallback_seconds: float = 20.0, clock=time.monotonic):
        self.probe_seconds = probe_seconds
        self.fallback_seconds = fallback_seconds
        self.clock = clock
        self._holds: dict[str, WarmupHold] = {}

    def record_missing(self, deployment_id: Any, required: int) -> None:
        now = self.clock()
        key = str(deployment_id)
        previous = self._holds.get(key)
        if previous and previous.required == int(required):
            # Do not indefinitely extend fallback when the worker retries.
            return
        self._holds[key] = WarmupHold(int(required), now, now + self.probe_seconds, now + self.fallback_seconds)
        logger.info('RUNNER_WARMUP_WAIT deployment=%s required=%s probe_s=%.1f', key, required, self.probe_seconds)

    def clear(self, deployment_id: Any) -> None:
        self._holds.pop(str(deployment_id), None)

    def blocked(self, deployment_id: Any, *, redis_status: dict | None = None) -> bool:
        """Pure decision for deterministic unit tests; caller controls Redis poll."""
        key = str(deployment_id)
        hold = self._holds.get(key)
        if hold is None:
            return False
        now = self.clock()
        if now >= hold.fallback_at:
            self.clear(key)
            logger.info('RUNNER_WARMUP_SQL_RECHECK deployment=%s reason=bounded_fallback', key)
            return False
        if redis_status is not None:
            data = {_status(k).lower(): v for k, v in redis_status.items()}
            state = _status(data.get('status'))
            if state == 'READY' and _int(data.get('stored_count')) >= hold.required:
                self.clear(key)
                logger.info('RUNNER_WARMUP_READY deployment=%s source=redis_hint_sql_recheck', key)
                return False
            if state == 'FAILED':
                self.clear(key)
                logger.warning('RUNNER_WARMUP_FAILED deployment=%s SQL_recheck=true', key)
                return False
        if now >= hold.next_probe:
            hold.next_probe = now + self.probe_seconds
        return True

    def due_for_probe(self, deployment_id: Any) -> bool:
        hold = self._holds.get(str(deployment_id))
        return bool(hold and self.clock() >= hold.next_probe)

    def contains(self, deployment_id: Any) -> bool:
        return str(deployment_id) in self._holds


@dataclass
class ReadyObservation:
    required: int
    deployment_signature: str
    through: datetime | None
    expires_at: float


def utc(t: datetime | None) -> datetime | None:
    if t is None:
        return None
    return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)


class HistoryReadyCache:
    """Short positive-only cache, never an order/strategy result cache.

    The 80K data load still verifies minimum row count on every FULL_HISTORY
    calculation. Any short load immediately invalidates this optimization.
    """

    def __init__(self, *, ttl_seconds: float = 20.0, clock=time.monotonic):
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._observations: dict[str, ReadyObservation] = {}

    def remember(self, deployment_id: Any, *, required: int, signature: str, through: datetime | None) -> None:
        self._observations[str(deployment_id)] = ReadyObservation(int(required), signature, utc(through), self.clock()+self.ttl_seconds)

    def can_reuse(self, deployment_id: Any, *, required: int, signature: str, through: datetime | None) -> bool:
        record = self._observations.get(str(deployment_id))
        if not record:
            return False
        eligible = (record.required == int(required)
                    and record.deployment_signature == signature
                    and self.clock() < record.expires_at
                    and (record.through is None or (through is not None and utc(through) >= record.through)))
        if not eligible:
            self.invalidate(deployment_id)
        return eligible

    def invalidate(self, deployment_id: Any) -> None:
        self._observations.pop(str(deployment_id), None)


class EligibleScanCache:
    """Very short advisory ID cache. Every execution re-reads DB status."""

    def __init__(self, *, ttl_seconds: float = 2.0, clock=time.monotonic):
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._expires = 0.0
        self._key: tuple[bool, bool] | None = None
        self._ids: tuple[Any, ...] = ()

    def get(self, *, event_pipeline_enabled: bool, market_worker_enabled: bool) -> tuple[Any, ...] | None:
        key = (event_pipeline_enabled, market_worker_enabled)
        if self._key == key and self.clock() < self._expires:
            return self._ids
        return None

    def store(self, ids: list[Any], *, event_pipeline_enabled: bool, market_worker_enabled: bool) -> None:
        self._key = (event_pipeline_enabled, market_worker_enabled)
        self._ids = tuple(ids)
        self._expires = self.clock() + self.ttl_seconds


warmup_gate = WarmupDispatchGate()
history_ready_cache = HistoryReadyCache()
eligible_scan_cache = EligibleScanCache()
