"""Regression tests for cache safety and bounded warmup backoff."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.services.live.runner_cache import (
    WarmupDispatchGate, HistoryReadyCache, EligibleScanCache,
)


class Ticker:
    def __init__(self): self.t = 0.
    def __call__(self): return self.t
    def advance(self, seconds): self.t += seconds


def test_warmup_gate_throttles_and_recovers_on_ready():
    t = Ticker()
    gate = WarmupDispatchGate(probe_seconds=5., fallback_seconds=20., clock=t)
    deployment = uuid4()
    assert not gate.blocked(deployment)
    gate.record_missing(deployment, 80000)
    assert gate.blocked(deployment)
    t.advance(5)
    assert gate.due_for_probe(deployment)
    assert gate.blocked(deployment, redis_status={b'status': b'RUNNING', b'stored_count': b'79650'})
    assert not gate.due_for_probe(deployment)
    t.advance(5)
    assert gate.due_for_probe(deployment)
    assert not gate.blocked(deployment, redis_status={b'status': b'READY', b'stored_count': b'80005'})
    assert not gate.contains(deployment)


def test_warmup_never_waits_indefinitely_when_redis_is_lost():
    t = Ticker()
    gate = WarmupDispatchGate(probe_seconds=5., fallback_seconds=20., clock=t)
    gate.record_missing('d', 80000)
    for i in range(3):
        t.advance(5)
        assert gate.blocked('d', redis_status=None)
    t.advance(5)
    assert not gate.blocked('d', redis_status=None)
    assert not gate.contains('d')


def test_warmup_failed_status_releases_hold():
    gate = WarmupDispatchGate()
    gate.record_missing('d', 80000)
    assert not gate.blocked('d', redis_status={'status':'FAILED'})


def test_history_ready_cache_positive_only_exact_contract():
    t = Ticker()
    cache = HistoryReadyCache(ttl_seconds=20., clock=t)
    now = datetime(2026,10,27,15,30, tzinfo=timezone.utc)
    assert not cache.can_reuse('d', required=80000, signature='a', through=now)
    cache.remember('d', required=80000, signature='a', through=now)
    assert cache.can_reuse('d', required=80000, signature='a', through=now+timedelta(minutes=5))
    assert not cache.can_reuse('d', required=80000, signature='changed', through=now)
    cache.remember('d', required=80000, signature='a', through=now)
    t.advance(21)
    assert not cache.can_reuse('d', required=80000, signature='a', through=now)


def test_history_cache_cannot_reuse_future_confirmation():
    cache = HistoryReadyCache()
    confirmed = datetime(2026,10,27,15,30,tzinfo=timezone.utc)
    cache.remember('d', required=80000, signature='a', through=confirmed)
    assert not cache.can_reuse('d', required=80000, signature='a', through=confirmed-timedelta(minutes=5))


def test_eligible_id_cache_expires_and_switches_pipeline_mode():
    t = Ticker()
    cache = EligibleScanCache(ttl_seconds=2., clock=t)
    assert cache.get(event_pipeline_enabled=False, market_worker_enabled=False) is None
    cache.store(['a'], event_pipeline_enabled=False, market_worker_enabled=False)
    assert cache.get(event_pipeline_enabled=False, market_worker_enabled=False) == ('a',)
    assert cache.get(event_pipeline_enabled=True, market_worker_enabled=False) is None
    t.advance(2.1)
    assert cache.get(event_pipeline_enabled=False, market_worker_enabled=False) is None
