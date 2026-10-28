"""Offline regression: a live process must not masquerade as a live market feed."""
from datetime import datetime, timedelta, timezone
import pytest
from app.services.live.candle_worker_health import collector_status, collector_owns_broker_ingestion
from app.services.live.candle_poll_schedule import next_poll_delay, next_candle_probe

NOW = datetime(2026, 10, 28, 11, 40, tzinfo=timezone.utc)

def t(seconds):
    return (NOW - timedelta(seconds=seconds)).isoformat()

@pytest.mark.parametrize('age,expected', [(0, 'STARTING'), (89, 'STARTING'), (90, 'DEGRADED'), (600, 'DEGRADED')])
def test_collector_without_first_poll_cannot_start_forever(age, expected):
    assert collector_status({'deployments':1,'started_at':t(age)}, NOW) == expected

@pytest.mark.parametrize('age,expected', [(0, 'HEALTHY'), (299, 'HEALTHY'), (419, 'HEALTHY'), (421, 'DEGRADED'), (2000, 'DEGRADED')])
def test_last_successful_poll_becomes_stale(age, expected):
    assert collector_status({'deployments':1,'started_at':t(3000),'last_poll_completed_at':t(age)}, NOW) == expected

def test_zero_deployments_does_not_report_healthy():
    assert collector_status({'deployments':0,'started_at':t(3000)}, NOW) == 'IDLE'

def test_broker_error_degrades_even_if_last_poll_was_recent():
    assert collector_status({'deployments':1,'last_error':'timeout','last_poll_completed_at':t(2)}, NOW) == 'DEGRADED'

def test_completed_broker_poll_with_no_new_candle_still_counts_as_polling():
    assert collector_status({'deployments':1,'last_poll_completed_at':t(100), 'market_data_state':'NO_NEW_CANDLE'},NOW) == 'HEALTHY'

def test_health_requires_real_completed_poll_and_fresh_heartbeat():
    good={'status':'HEALTHY','last_poll_completed_at':t(9), 'heartbeat_at':t(1)}
    assert collector_owns_broker_ingestion(good, NOW)
    for bad in ({'status':'STARTING','heartbeat_at':t(1)},
                {'status':'DEGRADED','last_poll_completed_at':t(9), 'heartbeat_at':t(1)},
                {'status':'HEALTHY','heartbeat_at':t(1)},
                {'status':'HEALTHY','last_poll_completed_at':t(421), 'heartbeat_at':t(1)},
                {'status':'HEALTHY','last_poll_completed_at':t(9), 'heartbeat_at':t(92)},
                {}, None):
        assert not collector_owns_broker_ingestion(bad, NOW)

def test_m5_normal_interval_retries_and_weekend():
    at=NOW.replace(minute=40,second=3)
    assert next_poll_delay(at,'M5',ready=True)>295
    assert next_poll_delay(at,'M5',ready=False,empty_streak=1,fast_retries=2)==8.0
    assert next_poll_delay(at,'M5',ready=False,empty_streak=4,fast_retries=2,idle_grace_seconds=10)>295

def test_no_new_broker_candles_never_invents_a_market_bar():
    at=NOW.replace(minute=40, second=3)
    assert next_candle_probe(at, 'M5') == NOW.replace(minute=45,second=2)
    assert next_poll_delay(at, 'M5', ready=True) > 295
