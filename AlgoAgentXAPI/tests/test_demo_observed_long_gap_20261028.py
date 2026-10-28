"""Pure offline tests. Does not assert official market closure or strategy parity."""
from datetime import datetime, timezone, timedelta
from app.services.live.candle_catchup import observed_broker_gap_eligible, plan_recovery

T0=datetime(2026,10,27,20,55,tzinfo=timezone.utc)
def t(n):return T0+timedelta(minutes=n)

def check(first,followup,first_source='TRADELOCKER',followup_source='TRADELOCKER',previous_source='TRADELOCKER'):
    return observed_broker_gap_eligible(previous=t(0),first_pending=first,first_source=first_source,
             followup_open=followup,followup_source=followup_source,previous_source=previous_source,
             timeframe_seconds=300,min_missing_bars=6)

def test_one_hour_market_break_like_gap_two_real_candles():
    assert check(t(65),t(70))
    d=plan_recovery(last_processed=t(0),first_pending=t(65),newest=t(75),timeframe_seconds=300,verified_resume_open=t(65))
    assert d.action == 'PROCESS_AFTER_VERIFIED_NO_BAR_GAP' and d.target == t(65)

def test_short_holes_never_soft_skip():
    for gap in range(1,6):
        assert not check(t(5*(gap+1)),t(5*(gap+2)))

def test_two_successive_broker_candles_required():
    assert not check(t(65),None)
    assert not check(t(65),t(75))

def test_no_other_data_sources_accepted():
    assert not check(t(65),t(70),first_source='CSV')
    assert not check(t(65),t(70),previous_source='MANUAL')

def test_weekend_gap_allowed_with_two_real_candles():
    assert check(t(60*48),t(60*48+5))

def test_gap_must_be_m5_aligned():
    assert not check(t(67),t(72))

def test_still_not_proven_without_operator_optin():
    d=plan_recovery(last_processed=t(0),first_pending=t(65),newest=t(75),timeframe_seconds=300)
    assert d.action == 'WAIT_FOR_BACKFILL'
