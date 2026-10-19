"""TradeLocker OHLC and background warmup regressions. No broker or DB access."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
import pytest

from app.services.brokers.tradelocker import TradeLockerAdapter


@pytest.fixture
def adapter():
    client = TradeLockerAdapter.__new__(TradeLockerAdapter)
    client._instrument = AsyncMock(return_value={"tradableInstrumentId": 123, "routes": [{"type": "INFO", "id": 456}]})
    client._route = lambda inst, kind: 456
    return client


def bar(at, close, *, low=None):
    value = close if low is None else low
    return {'t': int(at.timestamp()*1000), 'o': close + 0.6,
            'h': close + 1.2, 'l': value, 'c': close, 'v': 123}


def test_normalization_preserves_real_close_not_low_and_raw_payload():
    ts = datetime(2026, 10, 9, 12, 30, tzinfo=timezone.utc)
    rows = TradeLockerAdapter._normalize_history_bars([bar(ts, 4210.2, low=4209.4)], symbol='XAUUSD.X')
    assert len(rows) == 1
    assert rows[0]['close'] == 4210.2
    assert rows[0]['low'] == 4209.4
    assert rows[0]['raw_payload']['c'] == 4210.2
    assert rows[0]['candle_time'] == ts


def test_valid_close_equal_low_accepted():
    ts = datetime(2026, 10, 9, 12, 30, tzinfo=timezone.utc)
    rows = TradeLockerAdapter._normalize_history_bars([bar(ts, 4210.2)], symbol='XAUUSD.X')
    assert len(rows) == 1 and rows[0]['close'] == rows[0]['low']


def test_corrupt_missing_and_impossible_candles_skipped():
    ts = datetime(2026, 10, 9, 12, 30, tzinfo=timezone.utc)
    bad = [bar(ts, 4200, low=4300), {'t': int(ts.timestamp()*1000), 'o': 1, 'h': 2, 'l': 0},
           bar(ts, float('nan')), {**bar(ts, 4200), 't': 0}]
    assert TradeLockerAdapter._normalize_history_bars(bad, symbol='XAUUSD.X') == []


def test_duplicate_bars_removed_and_sorted():
    ts = datetime(2026, 10, 9, 12, 30, tzinfo=timezone.utc)
    raw = [bar(ts + timedelta(minutes=5), 4210), bar(ts, 4200), bar(ts, 4200)]
    rows = TradeLockerAdapter._normalize_history_bars(raw, symbol='XAUUSD.X')
    assert [r['close'] for r in rows] == [4200, 4210]


@pytest.mark.asyncio
async def test_short_live_refresh_keeps_one_bounded_request(adapter, monkeypatch):
    monkeypatch.setattr('app.services.brokers.tradelocker.time.time', lambda: 1791600000)
    adapter._request = AsyncMock(return_value={'s': 'ok', 'd': {'barDetails': []}})
    assert await adapter.get_rates('XAUUSD.X', 'M5', 12) == []
    assert adapter._request.await_count == 1
    params = adapter._request.await_args.kwargs['params']
    assert params['resolution'] == '5m' and params['tradableInstrumentId'] == 123
    assert params['to'] > params['from']
    assert params['to'] - params['from'] < 20_000 * 5 * 60 * 1000


@pytest.mark.asyncio
async def test_background_history_uses_cursor_and_fetches_more_than_6000(adapter, monkeypatch):
    end = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr('app.services.brokers.tradelocker.time.time', lambda: end.timestamp())
    all_bars = [bar(end - timedelta(minutes=5*(i+1)), 4200 + i/10, low=4199 + i/10)
                for i in range(7100)]
    all_bars.sort(key=lambda x: x['t'])
    requested_windows = []

    async def fake_request(_method, _path, *, params):
        requested_windows.append((params['from'], params['to']))
        candidates = [x for x in all_bars if params['from'] <= x['t'] <= params['to']]
        return {'s': 'ok', 'd': {'barDetails': candidates}}

    adapter._request = fake_request
    rows = await adapter.get_rates_history('XAUUSD.X', 'M5', 7000)
    assert len(rows) == 7000
    assert rows == sorted(rows, key=lambda x: x['candle_time'])
    assert len({r['candle_time'] for r in rows}) == 7000
    assert rows[-1]['candle_time'] == end - timedelta(minutes=5)
    assert len(requested_windows) >= 5
    assert all(0 < right - left < 20_000 * 300_000 for left, right in requested_windows)
    assert all(requested_windows[i+1][1] < requested_windows[i][1] for i in range(len(requested_windows)-1))


@pytest.mark.asyncio
async def test_history_before_cursor_excludes_boundary(adapter):
    cutoff = datetime(2026, 10, 9, 14, 0, tzinfo=timezone.utc)
    older = cutoff - timedelta(minutes=5)
    adapter._request = AsyncMock(return_value={'s': 'ok', 'd': {'barDetails': [bar(cutoff, 4200), bar(older, 4201)]}})
    rows = await adapter.get_rates_history('XAUUSD.X', 'M5', 1, before=cutoff)
    assert len(rows) == 1 and rows[0]['candle_time'] == older


@pytest.mark.asyncio
async def test_unsupported_timeframe_fails_closed(adapter):
    with pytest.raises(ValueError, match='Unsupported TradeLocker timeframe'):
        await adapter.get_rates('XAUUSD.X', 'M2', 2)

@pytest.mark.asyncio
async def test_no_data_stops_without_synthetic_candles(adapter):
    adapter._request = AsyncMock(return_value={'s': 'no_data', 'd': {}})
    result = await adapter.get_rates_history('XAUUSD.X', 'M5', 2000)
    assert result == []
    assert adapter._request.await_count == 1


@pytest.mark.asyncio
async def test_history_warmup_requests_over_20000_in_multiple_api_pages(adapter, monkeypatch):
    end = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr('app.services.brokers.tradelocker.time.time', lambda: end.timestamp())
    # 20,005 bars requires more than the broker's 20k *per request* maximum.
    full = [bar(end - timedelta(minutes=5*(i+1)), 4200 + i/10, low=4199 + i/10)
            for i in range(20100)]
    timestamps = [x['t'] for x in full]
    full.reverse()
    calls = []

    async def fake_request(method, path, *, params):
        calls.append(params)
        assert (params['to'] - params['from']) // 300_000 < 20_000
        return {'s': 'ok', 'd': {'barDetails': [x for x in full if params['from'] <= x['t'] <= params['to']]}}

    adapter._request = fake_request
    rows = await adapter.get_rates_history('XAUUSD.X', 'M5', 20005)
    assert len(rows) == 20005
    assert rows[-1]['candle_time'] == end - timedelta(minutes=5)
    assert len(calls) >= 14

@pytest.mark.asyncio
async def test_backwards_cursor_resumes_without_refetching_latest_page(adapter, monkeypatch):
    """Regression: after storing a first page, resume strictly before oldest bar."""
    end = datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr('app.services.brokers.tradelocker.time.time', lambda: end.timestamp())
    all_bars = [bar(end - timedelta(minutes=5*(i + 1)), 4200 + i / 10,
                    low=4199 + i / 10) for i in range(4000)]
    requested = []

    async def fake_request(method, path, *, params):
        requested.append(params)
        return {'s': 'ok', 'd': {'barDetails': [x for x in all_bars
                                               if params['from'] <= x['t'] <= params['to']]}}

    adapter._request = fake_request
    newest = await adapter.get_rates_history('XAUUSD.X', 'M5', 1500)
    older = await adapter.get_rates_history('XAUUSD.X', 'M5', 1500,
                                            before=newest[0]['candle_time'])
    assert len(newest) == len(older) == 1500
    assert max(r['candle_time'] for r in older) < min(r['candle_time'] for r in newest)
    assert len(set(r['candle_time'] for r in newest + older)) == 3000
