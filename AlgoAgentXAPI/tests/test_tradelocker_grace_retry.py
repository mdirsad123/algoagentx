"""Deterministic scheduler regressions; no real DB, Redis, broker or orders.

The worker functions are exercised with isolated I/O doubles. These are timing
tests, not proof of actual broker candles, persistence or strategy parity.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.services.live.candle_poll_schedule import next_poll_delay


BOUNDARY = datetime(2026, 10, 28, 12, 45, tzinfo=timezone.utc)
DEPLOYMENT = UUID('0349cc95-6677-4a7e-b7d1-e4c8cbd46b88')


def at(seconds):
    return BOUNDARY + timedelta(seconds=seconds)


def test_grace_processed_after_deadline_does_not_skip_current_m5():
    # Existing API alone reproduces the 299.9-second scheduling error.
    assert next_poll_delay(at(2.10), 'M5', skip_reason='grace') == pytest.approx(0.1)


@pytest.mark.parametrize('handled,expected', [(1, 1), (1.98, .1), (2, .1), (2.1, .1), (301, .1)])
def test_exact_grace_deadline_survives_delayed_handling(handled, expected):
    assert next_poll_delay(at(handled), 'M5', skip_reason='grace',
                           retry_at=at(2)) == pytest.approx(expected)


def test_ist_deadline_and_utc_deadline_are_identical():
    ist = timezone(timedelta(hours=5, minutes=30))
    assert next_poll_delay(at(1), 'M5', skip_reason='grace',
                           retry_at=at(2).astimezone(ist)) == 1


@pytest.mark.parametrize('now', [BOUNDARY, datetime(2026, 11, 1, tzinfo=timezone.utc)])
def test_empty_responses_remain_bounded_on_trading_day_and_weekend(now):
    # Only retry times are simulated, never market candles or session calendars.
    now += timedelta(seconds=2)
    for streak in (1, 2):
        delay = next_poll_delay(now, 'M5', empty_streak=streak)
        assert delay == 8
        now += timedelta(seconds=delay)
    assert next_poll_delay(now, 'M5', empty_streak=3) == 284


@pytest.mark.parametrize('seconds', [6, 10, 15])
def test_success_after_late_publication_returns_to_boundary(seconds):
    assert next_poll_delay(at(seconds), 'M5', ready=True) == 302 - seconds


def test_reopening_success_resets_schedule_despite_old_empty_streak():
    assert next_poll_delay(at(10), 'M5', ready=True, empty_streak=900) == 292


def test_duplicate_already_stored_does_not_trigger_fast_retry():
    assert next_poll_delay(at(3), 'M5', skip_reason='already_stored') == 299


@pytest.fixture
def worker(monkeypatch):
    # Import the actual module; replace all paths used for external I/O below.
    from app.services.live import live_tradelocker_candle_worker as module
    monkeypatch.setattr(module, 'settings', SimpleNamespace(
        live_tradelocker_boundary_poll_enabled=True,
        live_tradelocker_gap_backfill_enabled=False,
        live_tradelocker_registry_refresh_seconds=15,
        live_tradelocker_fast_empty_retries=2,
        live_tradelocker_empty_retry_seconds=8,
        live_tradelocker_idle_boundary_grace_seconds=10,
    ))
    return module


def install_clock(monkeypatch, worker, clock):
    class ClockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = at(clock[0])
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    monkeypatch.setattr(worker, 'datetime', ClockDatetime)
    monkeypatch.setattr(worker, 'time', SimpleNamespace(monotonic=lambda: clock[0]))


@pytest.mark.parametrize('read_finished,fetch_expected', [(1.99, False), (2.10, True)])
def test_readiness_uses_time_after_deployment_lookup(monkeypatch, worker, read_finished, fetch_expected):
    clock = [1.98]
    install_clock(monkeypatch, worker, clock)
    deployment = SimpleNamespace(status='RUNNING', auto_runner_enabled=True,
                                 timeframe='M5', broker_account_id=None,
                                 broker_symbol='XAUUSD.X', instrument='XAUUSD.X', mode='DEMO')

    class Session:
        calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def execute(self, statement):
            self.calls += 1
            clock[0] = read_finished
            value = deployment if self.calls == 1 else None
            return SimpleNamespace(scalar_one_or_none=lambda: value)

        async def rollback(self):
            pass

    monkeypatch.setattr(worker, 'async_session', Session)
    fetch = AsyncMock(return_value={'latest_candle_time': None})
    monkeypatch.setattr(worker, 'refresh_deployment_candles', fetch)
    result = asyncio.run(worker._poll_one(DEPLOYMENT, at(1.98)))
    assert fetch.await_count == int(fetch_expected)
    if not fetch_expected:
        assert result['skip'] == 'grace'
        assert result['retry_at'] == at(2).isoformat()
        assert result['open'] == (BOUNDARY - timedelta(minutes=5)).isoformat()


@pytest.mark.parametrize('boundary_enabled', [True, False])
def test_run_consumes_overdue_retry_at_and_retries_same_cycle(monkeypatch, worker, boundary_enabled):
    worker.settings.live_tradelocker_boundary_poll_enabled = boundary_enabled
    clock = [1.98]
    install_clock(monkeypatch, worker, clock)
    attempts = []
    scans = []

    class Stop:
        def is_set(self):
            return len(attempts) >= 2 or clock[0] > 303

        async def wait(self):
            # Advance virtual time by 100ms per idle wakeup, never wall-clock sleep.
            clock[0] += .1
            raise asyncio.TimeoutError

    async def registry():
        scans.append(clock[0])
        return [DEPLOYMENT]

    async def poll(deployment_id, now):
        attempts.append(clock[0])
        if len(attempts) == 1:
            clock[0] = 2.10
            return {'skip': 'grace', 'timeframe': 'M5', 'retry_at': at(2).isoformat()}
        return {'ready': True, 'timeframe': 'M5'}

    monkeypatch.setattr(worker, '_deployment_ids', registry)
    monkeypatch.setattr(worker, '_poll_one', poll)
    asyncio.run(worker._run(Stop(), {}))
    assert len(attempts) == 2
    assert 2.19 <= attempts[1] <= 2.31
    assert len(scans) == 1


@pytest.mark.parametrize('failure', [OSError('DNS unavailable'), TimeoutError('request timed out'),
                                    RuntimeError('429'), RuntimeError('503')])
def test_poll_error_does_not_starve_other_deployment_and_recovers(monkeypatch, worker, failure):
    clock = [3.0]
    install_clock(monkeypatch, worker, clock)
    other = UUID(int=1)
    attempts = []

    class Stop:
        def is_set(self):
            return len(attempts) >= 3 or clock[0] > 20

        async def wait(self):
            clock[0] += .1
            raise asyncio.TimeoutError

    async def poll(deployment_id, now):
        attempts.append((deployment_id, clock[0]))
        if len(attempts) == 1:
            raise failure
        return {'ready': True, 'timeframe': 'M5'}

    monkeypatch.setattr(worker, '_deployment_ids', AsyncMock(return_value=[DEPLOYMENT, other]))
    monkeypatch.setattr(worker, '_poll_one', poll)
    stats = {}
    asyncio.run(worker._run(Stop(), stats))
    assert [deployment for deployment, _ in attempts] == [DEPLOYMENT, other, DEPLOYMENT]
    assert 8 <= attempts[-1][1] < 8.2
    assert stats['last_error'] is None


def test_registry_zero_to_one_and_refresh_preserve_pending_retry(monkeypatch, worker):
    worker.settings.live_tradelocker_registry_refresh_seconds = 5
    clock = [1.0]
    install_clock(monkeypatch, worker, clock)
    attempts = []
    scans = []

    class Stop:
        def is_set(self):
            return len(attempts) >= 2 or clock[0] > 20

        async def wait(self):
            clock[0] += .1
            raise asyncio.TimeoutError

    async def registry():
        scans.append(clock[0])
        return [] if len(scans) == 1 else [DEPLOYMENT]

    async def poll(deployment_id, now):
        attempts.append(clock[0])
        return {'ready': False, 'timeframe': 'M5'}

    monkeypatch.setattr(worker, '_deployment_ids', registry)
    monkeypatch.setattr(worker, '_poll_one', poll)
    asyncio.run(worker._run(Stop(), {}))
    assert len(attempts) == 2
    assert len(scans) >= 3
    assert 8 <= attempts[1] - attempts[0] < 8.2


@pytest.mark.parametrize('skip', ['grace', 'inactive'])
def test_skipped_attempt_does_not_claim_completed_poll(monkeypatch, worker, skip):
    clock = [1.0]
    install_clock(monkeypatch, worker, clock)
    done = []

    class Stop:
        def is_set(self):
            return bool(done)

        async def wait(self):
            raise asyncio.TimeoutError

    async def poll(*args):
        done.append(True)
        return {'skip': skip, 'timeframe': 'M5', 'retry_at': at(2).isoformat()}

    monkeypatch.setattr(worker, '_deployment_ids', AsyncMock(return_value=[DEPLOYMENT]))
    monkeypatch.setattr(worker, '_poll_one', poll)
    stats = {'last_error': 'previous timeout'}
    asyncio.run(worker._run(Stop(), stats))
    assert 'last_poll_completed_at' not in stats
    assert stats['last_error'] == 'previous timeout'


def test_registry_failure_keeps_cached_deployment_polling(monkeypatch, worker):
    worker.settings.live_tradelocker_registry_refresh_seconds = 5
    clock = [3.0]
    install_clock(monkeypatch, worker, clock)
    attempts = []
    scans = []

    class Stop:
        def is_set(self):
            return len(attempts) >= 2 or clock[0] > 25

        async def wait(self):
            clock[0] += .1
            raise asyncio.TimeoutError

    async def registry():
        scans.append(clock[0])
        if len(scans) > 1:
            raise OSError('registry unavailable')
        return [DEPLOYMENT]

    async def poll(*args):
        attempts.append(clock[0])
        return {'ready': False, 'timeframe': 'M5'}

    monkeypatch.setattr(worker, '_deployment_ids', registry)
    monkeypatch.setattr(worker, '_poll_one', poll)
    asyncio.run(worker._run(Stop(), {}))
    assert len(attempts) == 2
    assert 8 <= attempts[1] - attempts[0] < 8.2


def test_empty_retry_budget_renews_at_next_actual_boundary(monkeypatch, worker):
    clock = [2.0]
    install_clock(monkeypatch, worker, clock)
    attempts = []

    class Stop:
        def is_set(self):
            return len(attempts) >= 5 or clock[0] > 325

        async def wait(self):
            clock[0] += .1
            raise asyncio.TimeoutError

    async def poll(*args):
        attempts.append(clock[0])
        opened = worker.expected_closed_open(at(clock[0]), 'M5')[0]
        return {'ready': False, 'timeframe': 'M5', 'open': opened.isoformat()}

    monkeypatch.setattr(worker, '_deployment_ids', AsyncMock(return_value=[DEPLOYMENT]))
    monkeypatch.setattr(worker, '_poll_one', poll)
    asyncio.run(worker._run(Stop(), {}))
    assert len(attempts) == 5
    assert 309.9 <= attempts[3] <= 310.2
    assert 8 <= attempts[4] - attempts[3] < 8.2