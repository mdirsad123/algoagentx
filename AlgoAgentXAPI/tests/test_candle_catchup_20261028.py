"""Pure tests; no broker credentials, network calls or DB mutation."""
from datetime import datetime, timedelta, timezone
import pytest
from app.services.live.candle_catchup import plan_recovery, required_broker_fetch_bars

T = datetime(2026, 10, 27, 19, 40, tzinfo=timezone.utc)


def dt(n):
    return T + timedelta(minutes=n)


def test_latest_1950_with_1945_present_must_process_1945_first():
    plan = plan_recovery(last_processed=dt(0), first_pending=dt(5), newest=dt(10), timeframe_seconds=300)
    assert plan.action == 'PROCESS_NEXT'
    assert plan.target == dt(5)
    assert plan.pending_bars == 2


def test_latest_1950_with_1945_missing_must_block_not_skip():
    plan = plan_recovery(last_processed=dt(0), first_pending=dt(10), newest=dt(10), timeframe_seconds=300)
    assert plan.action == 'WAIT_FOR_BACKFILL'
    assert plan.target is None
    assert plan.missing_open == dt(5)


def test_after_broker_backfill_1945_can_process():
    plan = plan_recovery(last_processed=dt(0), first_pending=dt(5), newest=dt(10), timeframe_seconds=300)
    assert plan.action == 'PROCESS_NEXT'
    next_plan = plan_recovery(last_processed=dt(5), first_pending=dt(10), newest=dt(10), timeframe_seconds=300)
    assert next_plan.target == dt(10)
    assert next_plan.pending_bars == 1


def test_no_unprocessed_candles():
    assert plan_recovery(last_processed=dt(5), first_pending=None, newest=dt(5), timeframe_seconds=300).action == 'UP_TO_DATE'


def test_no_cursor_requires_normal_cold_start():
    assert plan_recovery(last_processed=None, first_pending=dt(5), newest=dt(10), timeframe_seconds=300).action == 'NO_CURSOR'


def test_missing_broker_session_gap_never_fabricated():
    plan = plan_recovery(last_processed=dt(0), first_pending=dt(60 * 48), newest=dt(60 * 48), timeframe_seconds=300)
    assert plan.action == 'WAIT_FOR_BACKFILL'
    assert plan.missing_open == dt(5)
    assert required_broker_fetch_bars(newest=dt(60 * 48), previous=dt(0), timeframe_seconds=300, limit=120) is None


def test_refetch_count_is_bounded_and_covers_recent_gap():
    assert required_broker_fetch_bars(newest=dt(10), previous=dt(0), timeframe_seconds=300, limit=120) == 36
    assert required_broker_fetch_bars(newest=dt(60 * 5), previous=dt(0), timeframe_seconds=300, limit=120) == 76


def test_bad_timeframe_is_rejected():
    with pytest.raises(ValueError):
        plan_recovery(last_processed=dt(0), first_pending=dt(5), newest=dt(10), timeframe_seconds=0)


def test_timezone_normalization():
    assert plan_recovery(last_processed=dt(0).replace(tzinfo=None), first_pending=dt(5), newest=dt(10), timeframe_seconds=300).target == dt(5)
