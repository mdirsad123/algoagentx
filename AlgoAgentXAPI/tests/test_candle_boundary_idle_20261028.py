"""Pure scheduling tests; broker never contacted."""
from datetime import datetime, timedelta, timezone
from app.services.live.candle_poll_schedule import next_candle_probe, next_poll_delay, runner_no_data_probe_time


def T(hour, minute, second):
    return datetime(2026, 10, 28, hour, minute, second, tzinfo=timezone.utc)


def test_first_poll_at_next_M5_close_plus_2s():
    assert next_candle_probe(T(21, 2, 5), 'M5') == T(21, 5, 2)
    assert next_candle_probe(T(21, 4, 59), 'M5') == T(21, 5, 2)
    assert next_candle_probe(T(21, 5, 1), 'M5') == T(21, 5, 2)
    assert next_candle_probe(T(21, 5, 3), 'M5') == T(21, 10, 2)


def test_broker_closed_no_data_5min_aligned_after_two_fast_retries():
    now = T(21, 5, 4)
    assert next_poll_delay(now, 'M5', empty_streak=1) == 8
    assert next_poll_delay(now, 'M5', empty_streak=2) == 8
    assert next_poll_delay(now, 'M5', empty_streak=3) == 298


def test_success_does_not_repoll_every_second():
    assert next_poll_delay(T(21, 5, 7), 'M5', ready=True) == 295


def test_weekend_unchanged_and_dst_no_hardcoded_market_hours():
    saturday = datetime(2026, 10, 31, 2, 45, 4, tzinfo=timezone.utc)
    sunday = datetime(2026, 11, 1, 3, 20, 4, tzinfo=timezone.utc)
    assert next_poll_delay(saturday, 'M5', empty_streak=3) == 298
    assert next_poll_delay(sunday, 'M5', empty_streak=3) == 298


def test_multi_timeframe_alignment():
    assert next_candle_probe(T(21, 5, 3), 'M15') == T(21, 15, 2)
    assert next_candle_probe(T(21, 5, 3), 'M1') == T(21, 6, 2)


def test_grace_does_not_skip_first_due_candle():
    assert next_poll_delay(T(21, 5, 1), 'M5', skip_reason='grace') == 1


def test_runner_no_candle_db_probe_is_bounded():
    assert runner_no_data_probe_time(T(21, 5, 3), 'M5', 1) == T(21, 5, 8)
    assert runner_no_data_probe_time(T(21, 5, 13), 'M5', 3) == T(21, 5, 43)


def test_no_data_does_not_change_strategy_or_80k_warmup():
    # Only polling timestamps change; no strategy implementation touched.
    assert next_poll_delay(T(21, 5, 4), 'M5', empty_streak=3) > 290


def test_late_candle_has_at_most_30_seconds_extra_db_probe_delay():
    assert runner_no_data_probe_time(T(21, 6, 12), 'M5', 8) == T(21, 6, 42)
    assert runner_no_data_probe_time(T(21, 9, 45), 'M5', 8) == T(21, 10, 2)
