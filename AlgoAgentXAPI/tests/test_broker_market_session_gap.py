"""Offline policy tests: no broker calls, no candles fabricated, no orders."""
from datetime import datetime, timezone
from pathlib import Path
import ast

import pytest
from app.services.live.broker_session_gap import classify_missing_slots


def stamp(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def calendar(tz='UTC'):
    weekdays = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday')
    return {
        'timeZone': tz, 'blockTrading': False,
        'session_regular': {
            day: [{'start': '00:00', 'end': '22:00'},
                  {'start': '23:00', 'end': '24:00'}]
            for day in weekdays
        },
        'holidays': [],
    }


def test_gold_daily_break_is_verified_closed_without_fabricating_candle():
    # 2026-11-16 is Monday UTC. Only broker-provided calendar can authorize.
    assert classify_missing_slots(calendar=calendar(),
        missing_open=stamp('2026-11-16T22:00:00'),
        first_pending=stamp('2026-11-16T23:00:00')) == 'CLOSED'


def test_open_trading_session_missing_bar_remains_blocked():
    assert classify_missing_slots(calendar=calendar(),
        missing_open=stamp('2026-11-16T21:55:00'),
        first_pending=stamp('2026-11-16T22:05:00')) == 'OPEN'


def test_unknown_broker_schedule_fails_closed():
    assert classify_missing_slots(calendar={'timeZone': 'UTC', 'session_regular': {'open': 'all_day'}},
        missing_open=stamp('2026-11-16T22:00:00'), first_pending=stamp('2026-11-16T23:00:00')) == 'UNKNOWN'
    assert classify_missing_slots(calendar={**calendar(), 'timeZone': 'NO_SUCH_BROKER_TIMEZONE'},
        missing_open=stamp('2026-11-16T22:00:00'), first_pending=stamp('2026-11-16T23:00:00')) == 'UNKNOWN'
    assert classify_missing_slots(calendar={**calendar(), 'session_aftermarket': {'opaque': {'x': 2}}},
        missing_open=stamp('2026-11-16T22:00:00'), first_pending=stamp('2026-11-16T23:00:00')) == 'UNKNOWN'


def test_weekend_and_broker_declared_holiday():
    assert classify_missing_slots(calendar=calendar(),
        missing_open=stamp('2026-11-14T10:00:00'), first_pending=stamp('2026-11-14T11:00:00')) == 'CLOSED'
    c = calendar()
    c['holidays'] = ['2026-11-16']
    assert classify_missing_slots(calendar=c,
        missing_open=stamp('2026-11-16T13:00:00'), first_pending=stamp('2026-11-16T14:00:00')) == 'CLOSED'


def test_timezone_dst_switch_conservative():
    c = calendar('America/New_York')
    c['session_regular'] = {d: [{'start': '09:30', 'end': '16:00'}]
                            for d in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday')}
    # Nov 17 15:00 UTC = 10 AM New York standard time (open)
    assert classify_missing_slots(calendar=c, missing_open=stamp('2026-11-17T15:00:00'),
                                   first_pending=stamp('2026-11-17T15:05:00')) == 'OPEN'
    # July 17 13:00 UTC = 9 AM New York daylight time (closed)
    assert classify_missing_slots(calendar=c, missing_open=stamp('2026-07-17T13:00:00'),
                                   first_pending=stamp('2026-07-17T13:05:00')) == 'CLOSED'


def test_gap_reseed_source_approval_strict_without_live_or_posting():
    from app.services.live.gap_reseed_capability import approved_for_gap_reseed
    from app.services.live.incremental_adapter_registry import AdapterSelection
    from app.services.live.v932_hybrid_gate import V932_NORMALIZED_SHA256
    from strategies.v932_incremental import Strategy
    frozen = Path(__file__).resolve().parents[1] / 'strategies/v932_original_db_source.py'
    code = frozen.read_text().strip()
    from hashlib import sha256
    assert sha256(code.encode()).hexdigest() == V932_NORMALIZED_SHA256
    allowed = AdapterSelection(Strategy, 'v932_hybrid_v1', 'selected', False, V932_NORMALIZED_SHA256)
    assert approved_for_gap_reseed(selection=allowed, source_code=code, mode='DEMO', suppressed=True, enabled=True)
    assert approved_for_gap_reseed(selection=allowed, source_code=code, mode='LIVE', suppressed=True, enabled=True)
    assert not approved_for_gap_reseed(selection=allowed, source_code=code, mode='PAPER', suppressed=True, enabled=True)
    assert not approved_for_gap_reseed(selection=allowed, source_code=code, mode='LIVE', suppressed=False, enabled=True)
    assert not approved_for_gap_reseed(selection=allowed, source_code=code, mode='DEMO', suppressed=False, enabled=True)
    assert not approved_for_gap_reseed(selection=allowed, source_code=code+'\n# changed', mode='DEMO', suppressed=True, enabled=True)
    assert not approved_for_gap_reseed(selection=AdapterSelection(None, None, '', False, ''), source_code=code,
                                       mode='DEMO', suppressed=True, enabled=True)


def test_order_suppressed_queued_reseed_and_bounded_backfill_source_contract():
    base = Path(__file__).resolve().parents[1] / 'app/services/live'
    runner = (base/'auto_runner_service.py').read_text()
    task = (base.parent.parent/'tasks.py').read_text()
    assert '_DEMO_GAP_MAX_FETCH_ATTEMPTS = 3' in runner
    assert '_DEMO_GAP_FETCH_SPACING_SECONDS = 300.0' in runner
    assert "'historical_orders_suppressed': True" in runner
    assert 'suppress_broker_order_for_catchup=True' in task
    assert "queue='live_history'" in (base/'gap_reseed_queue.py').read_text()

@pytest.mark.asyncio
async def test_calendar_verified_through_instrument_session_endpoints():
    from app.services.live.broker_session_gap import verified_tradelocker_gap_status

    class FakeTradeLocker:
        def __init__(self):
            self.calls = []
        async def _instrument(self, symbol):
            assert symbol == 'XAUUSD.X'
            return {'tradableInstrumentId': 111, 'routes': [{'type': 'TRADE', 'id': 222}]}
        async def _request(self, method, path, *, params=None):
            self.calls.append((method, path, params))
            if path == '/trade/instruments/111':
                return {'d': {'tradeSessionId': 333}}
            if path == '/trade/sessions/333':
                return {'d': calendar()}
            raise RuntimeError('Unexpected API request')

    broker = FakeTradeLocker()
    assert await verified_tradelocker_gap_status(broker, 'XAUUSD.X',
        stamp('2026-11-16T22:00:00'), stamp('2026-11-16T23:00:00')) == 'CLOSED'
    assert broker.calls == [
        ('GET', '/trade/instruments/111', {'routeId': 222}),
        ('GET', '/trade/sessions/333', None)]


@pytest.mark.asyncio
async def test_unavailable_broker_session_never_approves_skip():
    from app.services.live.broker_session_gap import verified_tradelocker_gap_status

    class FakeTradeLocker:
        async def _instrument(self, symbol):
            return {'tradableInstrumentId': 111, 'routes': [{'type': 'TRADE', 'id': 222}]}
        async def _request(self, method, path, *, params=None):
            raise RuntimeError('HTTP 429 simulated')

    assert await verified_tradelocker_gap_status(FakeTradeLocker(), 'XAUUSD.X',
        stamp('2026-11-16T22:00:00'), stamp('2026-11-16T23:00:00')) == 'UNKNOWN'


def test_completed_reseed_must_advance_durable_cursor_and_avoid_retry_loop():
    root = Path(__file__).resolve().parents[1]
    runner = (root/'app/services/live/auto_runner_service.py').read_text()
    tasks = (root/'app/tasks.py').read_text()
    assert 'recovery_cursor_valid' in tasks
    assert "result.get('recovery_cursor_valid') is True" in tasks
    from app.services.live.verified_recovery import recovery_status_blocks
    assert recovery_status_blocks({'status': 'RUNNING', 'started_at': 100}, now=200)
    assert not recovery_status_blocks({'status': 'RUNNING', 'started_at': 100}, now=2700)
    assert recovery_status_blocks({'status': 'REQUIRES_ATTENTION'}, now=2700)
    assert recovery_status_blocks({'status': 'RETRYABLE', 'attempts': 3}, now=2700)
    assert "await redis.set(redis_key, json.dumps(state))" in runner
    assert "TRANSIENT_RECOVERY_REASONS" in tasks
    assert "attempts < MAX_ATTEMPTS" in tasks
    assert 'suppress_broker_order_for_catchup=True' in tasks
