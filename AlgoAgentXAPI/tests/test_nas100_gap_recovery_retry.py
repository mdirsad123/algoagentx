"""NAS100/XAUUSD market-closed recovery retry regression checks.

Offline only: no broker HTTP, database changes, orders, or cursor edits.
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.live.broker_session_gap import classify_missing_slots
from app.services.live.verified_recovery import (
    TRANSIENT_RECOVERY_REASONS, recovery_retry_delay_seconds,
    recovery_status_blocks,
)


def t(iso):
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def nas100_calendar():
    # Synthetic session shaped to match the confirmed CLOSED interval in the
    # 18 Nov 2026 Oracle logs, not a hardcoded schedule in production code.
    return {'timeZone': 'America/New_York', 'blockTrading': False,
            'session_regular': {day: [
                {'start': '00:00', 'end': '17:05'},
                {'start': '17:25', 'end': '24:00'}]
                for day in ('monday','tuesday','wednesday','thursday','friday')},
            'holidays': []}


def test_nas100_confirmed_close_only_skips_actual_session_slots():
    assert classify_missing_slots(calendar=nas100_calendar(),
        missing_open=t('2026-11-17T22:10:00'),
        first_pending=t('2026-11-17T22:25:00')) == 'CLOSED'
    assert classify_missing_slots(calendar=nas100_calendar(),
        missing_open=t('2026-11-17T22:00:00'),
        first_pending=t('2026-11-17T22:15:00')) == 'OPEN'
    assert classify_missing_slots(calendar={},
        missing_open=t('2026-11-17T22:10:00'),
        first_pending=t('2026-11-17T22:25:00')) == 'UNKNOWN'


def test_legacy_third_broker_unknown_retry_automatically_after_backoff():
    # Old celery behavior marked REQUIRES_ATTENTION after 3 metadata requests,
    # stranding a later broker-confirmed CLOSED gap indefinitely.
    s = {'status':'REQUIRES_ATTENTION', 'reason':'broker_session_unknown',
         'attempts':'3', 'retry_at':'1000', 'started_at':'650'}
    assert recovery_status_blocks(s, now=999)
    assert not recovery_status_blocks(s, now=1000)


@pytest.mark.parametrize('reason', [
    'HOLD_INCREMENTAL_PRIME_FAILED', 'HOLD_GAP_RESEED_NOT_APPROVED',
    'RECOVERY_STATE_VALIDATION_FAILED', 'ValueError', 'broker_session_open',
    'RECOVERY_CHECKPOINT_NOT_PERSISTED',
])
def test_parity_and_source_and_history_failures_stay_blocked(reason):
    assert reason not in TRANSIENT_RECOVERY_REASONS
    assert recovery_status_blocks({'status':'REQUIRES_ATTENTION', 'reason': reason,
                                   'retry_at': '100'}, now=9999999)
    assert recovery_status_blocks({'status':'RETRYABLE', 'reason': reason,
                                   'retry_at': '100'}, now=9999999)


def test_task_running_lease_prevents_concurrent_reseed():
    s={'status':'RUNNING','started_at':'1000'}
    assert recovery_status_blocks(s, now=3499)
    assert not recovery_status_blocks(s, now=3500)
    assert recovery_status_blocks({'status':'RECOVERED'}, now=999999)


def test_transient_db_and_lock_rearm_is_cooldown_bounded():
    for reason in ('LOCK_SKIPPED','TimeoutError','ConnectionError','OperationalError'):
        s={'status':'REQUIRES_ATTENTION','reason':reason,
           'started_at':'1000', 'retry_at':'1600'}
        assert recovery_status_blocks(s, now=1599)
        assert not recovery_status_blocks(s, now=1600)
    # Older transient failures had no retry_at. Wait for the worker lease.
    assert recovery_status_blocks({'status':'REQUIRES_ATTENTION',
        'reason':'TimeoutError','started_at':'1000'}, now=2000)
    assert not recovery_status_blocks({'status':'REQUIRES_ATTENTION',
        'reason':'TimeoutError','started_at':'1000'}, now=3501)


def test_metadata_retry_backoff_capped_and_independent_of_history_fetch_budget():
    assert [recovery_retry_delay_seconds(n) for n in (1,2,3,4,5,99)] == [300,600,1200,1800,1800,1800]
    assert recovery_status_blocks({'status':'RETRYABLE','attempts':'3'}, now=999999)
    assert not recovery_status_blocks({'status':'RETRYABLE','attempts':'3',
         'reason':'broker_session_unknown','retry_at':'1600'}, now=1600)


def test_real_scheduler_and_worker_keep_order_suppression_and_cursor_gates():
    root=Path(__file__).resolve().parents[1]
    scheduler=(root/'app/services/live/auto_runner_service.py').read_text()
    tasks=(root/'app/tasks.py').read_text()
    strategy=(root/'app/services/live/strategy_runner.py').read_text()
    assert "broker_calendar_result=CLOSED historical_orders_suppressed=true" in scheduler
    assert 'RUNNER_RECOVERY_STATUS_BLOCKED' in scheduler
    assert 'RUNNER_RECOVERY_TRANSIENT_REARM' in scheduler
    assert 'RUNNER_RECOVERY_TASK_STATUS' in tasks
    assert 'recovery_cursor_valid' in tasks
    assert 'suppress_broker_order_for_catchup=True' in tasks
    assert '_DEMO_GAP_MAX_FETCH_ATTEMPTS = 3' in scheduler
    assert 'validate_recovery_candles' in strategy
    assert 'validate_recovery_state' in strategy
