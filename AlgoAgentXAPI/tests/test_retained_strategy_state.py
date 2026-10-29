"""Fast deterministic tests: no broker, DB, Docker, or order execution required."""
from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest
from decimal import Decimal
from types import SimpleNamespace

from app.services.live.retained_strategy_state import RetainedStateCache, is_opted_in, signature
from app.services.live.retained_strategy_state import signal_runtime_identity, fingerprint_fields


class StreamingExample:
    LIVE_INCREMENTAL_VERSION = 1

    def __init__(self, df):
        self.df = df
        self.values = None

    def generate(self):
        out = self.df.copy()
        out['signal'] = (out['Close'].rolling(3).mean() < out['Close']).astype(int)
        return out

    def start_live_incremental(self, generated):
        self.values = list(self.df.Close.astype(float))
        return True

    def on_closed_candle(self, candle):
        self.values.append(float(candle['Close']))
        row = dict(candle)
        row['signal'] = int(len(self.values) >= 3 and self.values[-1] > sum(self.values[-3:]) / 3)
        return pd.DataFrame([row])


def _history(n=12):
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    return pd.DataFrame([{'Date': start+timedelta(minutes=5*i), 'Open': 100+i, 'High': 101+i,
                          'Low': 99+i, 'Close': 100+i+(i%3), 'Volume': 1} for i in range(n)])


def _fingerprint(extra=''):
    return signature(strategy_id='fixture', params={'source_hash': extra}, runtime={'rr': 2},
                     history_bars=8, timeframe='M5', instrument='XAUUSD')


def test_requires_explicit_parity_and_interface():
    klass = StreamingExample
    assert not is_opted_in(klass, {'live_incremental_enabled': True, 'live_incremental_parity_verified': True}, global_enabled=False)
    assert not is_opted_in(klass, {'live_incremental_enabled': True}, global_enabled=True)
    assert is_opted_in(klass, {'live_incremental_enabled': True, 'live_incremental_parity_verified': True}, global_enabled=True)
    assert not is_opted_in(type('Legacy', (), {}), {'live_incremental_enabled': True, 'live_incremental_parity_verified': True}, global_enabled=True)


def test_same_outputs_on_sequential_bars_and_invalidate_on_gap():
    full = _history()
    warm = full.iloc[:8].copy()
    inst = StreamingExample(warm)
    initial = inst.generate()
    cache = RetainedStateCache()
    f = _fingerprint()
    assert cache.prime('d', fingerprint=f, candle_time=warm.iloc[-1]['Date'],
                       strategy=inst, generated=initial, candle_count=len(warm), latest_candle=warm.iloc[-1].to_dict())
    cursor = warm.iloc[-1]['Date']
    for j in range(8, 11):
        row = full.iloc[j].to_dict()
        increment = cache.advance('d', fingerprint=f, last_processed=cursor,
                                  next_candle_time=row['Date'], timeframe_seconds=300, candle=row,
                                  previous_candle=full.iloc[j-1].to_dict())
        assert increment is not None
        actual, count = increment
        expected = StreamingExample(full.iloc[:j+1]).generate()
        assert actual.iloc[-1]['signal'] == expected.iloc[-1]['signal']
        assert count == j+1
        cursor = row['Date']
    skipped = full.iloc[11].to_dict()
    # Pretend bar at 11:00 has been skipped; do not advance an invalid state.
    assert cache.advance('d', fingerprint=f, last_processed=full.iloc[8]['Date'],
                         next_candle_time=skipped['Date'], timeframe_seconds=300, candle=skipped) is None
    assert cache._entries.get('d') is None


def test_source_or_parameter_change_invalidates():
    warm = _history(8)
    cache = RetainedStateCache()
    inst = StreamingExample(warm)
    cache.prime('d', fingerprint=_fingerprint(), candle_time=warm.iloc[-1]['Date'],
                strategy=inst, generated=inst.generate(), candle_count=8, latest_candle=warm.iloc[-1].to_dict())
    assert cache.get_for_next_candle('d', fingerprint=_fingerprint('changed'),
        last_processed=warm.iloc[-1]['Date'], next_candle_time=warm.iloc[-1]['Date'] + timedelta(minutes=5),
        timeframe_seconds=300) is None


def test_failed_mutating_update_never_reused():
    class Broken(StreamingExample):
        def on_closed_candle(self, candle):
            self.values.append(1234)
            raise RuntimeError('partial state mutation')
    warm = _history(8)
    cache = RetainedStateCache()
    inst = Broken(warm)
    cache.prime('d', fingerprint=_fingerprint(), candle_time=warm.iloc[-1]['Date'],
                strategy=inst, generated=inst.generate(), candle_count=8, latest_candle=warm.iloc[-1].to_dict())
    row = _history(9).iloc[-1].to_dict()
    assert cache.advance('d', fingerprint=_fingerprint(), last_processed=warm.iloc[-1]['Date'],
                         next_candle_time=row['Date'], timeframe_seconds=300, candle=row,
                         previous_candle=warm.iloc[-1].to_dict()) is None
    assert 'd' not in cache._entries


def test_dynamic_metadata_not_passed_to_strategy_constructor():
    from app.services.dynamic_strategy_loader import extract_dynamic_strategy_params
    kwargs = extract_dynamic_strategy_params({
        'source_code': 'class Strategy: pass',
        'live_incremental_enabled': True,
        'live_incremental_parity_verified': True,
        'window': 20,
    })
    assert kwargs == {'window': 20}


def test_broker_candle_revision_invalidates_retained_state():
    warm = _history(8)
    cache = RetainedStateCache()
    inst = StreamingExample(warm)
    cache.prime('d', fingerprint=_fingerprint(), candle_time=warm.iloc[-1]['Date'],
                strategy=inst, generated=inst.generate(), candle_count=8, latest_candle=warm.iloc[-1].to_dict())
    modified = warm.iloc[-1].to_dict()
    modified['Close'] = modified['Close'] + 1
    assert cache.get_for_next_candle('d', fingerprint=_fingerprint(),
        last_processed=warm.iloc[-1]['Date'],
        next_candle_time=warm.iloc[-1]['Date'] + timedelta(minutes=5),
        timeframe_seconds=300, previous_candle=modified) is None


def primed_cache():
    warm = _history(8)
    cache = RetainedStateCache()
    inst = StreamingExample(warm)
    cache.prime('d', fingerprint=_fingerprint(), candle_time=warm.iloc[-1]['Date'],
                strategy=inst, generated=inst.generate(), candle_count=8,
                latest_candle=warm.iloc[-1].to_dict(), fields={'runtime.risk.risk_percent': 'before'})
    return cache, warm.iloc[-1].to_dict()


@pytest.mark.parametrize('failure', ['fingerprint_changed', 'cursor_mismatch', 'nonconsecutive_candle',
                                   'previous_candle_missing', 'previous_ohlcv_revised', 'previous_candle_invalid'])
def test_precise_invalidation_diagnostics(caplog, failure):
    cache, last = primed_cache()
    args = dict(fingerprint=_fingerprint(), last_processed=last['Date'],
                next_candle_time=last['Date'] + timedelta(minutes=5), timeframe_seconds=300,
                previous_candle=dict(last), fields={'runtime.risk.risk_percent': 'after'})
    if failure == 'fingerprint_changed': args['fingerprint'] = _fingerprint('edit')
    if failure == 'cursor_mismatch': args['last_processed'] = None
    if failure == 'nonconsecutive_candle': args['next_candle_time'] += timedelta(minutes=5)
    if failure == 'previous_candle_missing': args['previous_candle'] = None
    if failure == 'previous_ohlcv_revised': args['previous_candle']['Volume'] += 1
    if failure == 'previous_candle_invalid': args['previous_candle']['Close'] = None
    assert cache.get_for_next_candle('d', **args) is None
    assert f"failures=['{failure}']" in caplog.text
    assert 'expected_next=' in caplog.text and 'db_cursor=' in caplog.text
    if failure == 'fingerprint_changed': assert 'runtime.risk.risk_percent' in caplog.text
    if failure == 'previous_ohlcv_revised': assert "'Volume': ['1', '2']" in caplog.text


def test_equity_churn_does_not_reset_v64_or_freeze_sizing():
    from app.services.live.capital_service import get_effective_trading_capital
    deployment = SimpleNamespace(capital=Decimal('10000'))
    identities, capitals, old_signatures = [], [], []
    for equity in ('10001.25', '9998.25', '10012.75'):
        snapshot = get_effective_trading_capital(deployment, SimpleNamespace(metadata_json={'account_info': {'equity': equity}}))
        runtime = {'risk': {'initial_capital': float(snapshot.effective_capital), 'risk_percent': .01}, 'sl_tp': {'rr_ratio': 2}}
        identities.append(signal_runtime_identity(runtime, capital_independent=True, configured_capital=deployment.capital))
        old_signatures.append(signature(strategy_id='v64', params={}, runtime=runtime, history_bars=80000, timeframe='M5', instrument='XAUUSD.X'))
        capitals.append(snapshot.effective_capital)
        assert runtime['risk']['initial_capital'] == float(equity)
        assert snapshot.effective_capital_source == 'BROKER_EQUITY'
    assert len(set(old_signatures)) == 3  # Reproduces the old unnecessary reset.
    assert identities[0] == identities[1] == identities[2]
    assert len(set(capitals)) == 3  # Execution capital was NOT frozen or changed.
    assert signal_runtime_identity(runtime, capital_independent=False, configured_capital=deployment.capital) == runtime
    assert signal_runtime_identity(runtime, capital_independent=True, configured_capital=11000) != identities[0]
    runtime['risk']['risk_percent'] = .02
    assert signal_runtime_identity(runtime, capital_independent=True, configured_capital=deployment.capital) != identities[0]


def test_stop_start_same_cursor_resumes_and_process_restart_cold_starts():
    cache, last = primed_cache()
    args = dict(fingerprint=_fingerprint(), last_processed=last['Date'],
                next_candle_time=last['Date'] + timedelta(minutes=5), timeframe_seconds=300, previous_candle=last)
    # STOP/START leaves DB cursor unchanged; no calls to the cache while stopped.
    assert cache.get_for_next_candle('d', **args) is not None
    assert RetainedStateCache().get_for_next_candle('d', **args) is None
    args['next_candle_time'] += timedelta(minutes=10)
    assert cache.get_for_next_candle('d', **args) is None


def test_48_advances_then_full_window_rebase():
    cache, last = primed_cache()
    frame = _history(57)
    cache._entries['d'].candle_count = 80000
    for index in range(8, 56):
        assert not cache.rebase_due('d', history_bars=80000, max_advances=48)
        result = cache.advance('d', fingerprint=_fingerprint(), last_processed=last['Date'],
                               next_candle_time=frame.iloc[index]['Date'], timeframe_seconds=300,
                               candle=frame.iloc[index].to_dict(), previous_candle=last)
        assert result is not None
        last = frame.iloc[index].to_dict()
    assert cache.rebase_due('d', history_bars=80000, max_advances=48)
    cache.invalidate('d', 'hybrid_periodic_rolling_80k_rebase')
    assert not cache.rebase_due('d', history_bars=80000, max_advances=48)


def test_previous_candle_decimal_and_timezone_normalization():
    cache, last = primed_cache()
    previous = {key.lower(): Decimal(str(value)) for key, value in last.items() if key != 'Date'}
    previous['candle_time'] = last['Date'].tz_convert('Asia/Kolkata')
    assert cache.get_for_next_candle('d', fingerprint=_fingerprint(), last_processed=last['Date'],
        next_candle_time=last['Date'] + timedelta(minutes=5), timeframe_seconds=300, previous_candle=previous)


def test_fingerprint_diagnostics_never_include_source_or_secret_values():
    digests = fingerprint_fields(params={'source_code': 'private source'}, runtime={'risk': {'initial_capital': 123}})
    assert set(digests) == {'parameters.source_code', 'runtime.risk.initial_capital'}
    assert all(len(value) == 64 for value in digests.values())
    assert 'private source' not in str(digests)
