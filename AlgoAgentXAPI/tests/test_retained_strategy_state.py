"""Fast deterministic tests: no broker, DB, Docker, or order execution required."""
from datetime import datetime, timedelta, timezone
import pandas as pd

from app.services.live.retained_strategy_state import RetainedStateCache, is_opted_in, signature


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
                         next_candle_time=row['Date'], timeframe_seconds=300, candle=row) is None
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
