import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

# Lightweight test-environment fallbacks only: the deployed worker still
# requires real Redis + asyncpg. Candle unit tests do not connect to either.
import importlib.util
import sys
import types
if importlib.util.find_spec("redis") is None:
    redis_pkg = types.ModuleType("redis")
    redis_pkg.__path__ = []
    redis_async = types.ModuleType("redis.asyncio")
    redis_async.Redis = type("Redis", (), {})
    redis_async.from_url = lambda *a, **k: None
    redis_pkg.asyncio = redis_async
    sys.modules.setdefault("redis", redis_pkg)
    sys.modules.setdefault("redis.asyncio", redis_async)
if importlib.util.find_spec("asyncpg") is None:
    fake_session = types.ModuleType("app.db.session")
    fake_session.async_session = lambda: None
    sys.modules.setdefault("app.db.session", fake_session)

from app.services.live.live_market_worker import (
    FeedRegistration, LiveMarketWorker, _decode_trendbar,
)


class _UnusedRedis:
    pass


def _bar(minute: int, close_delta: int | None = 1000):
    data = {
        "period": 1,
        "utcTimestampInMinutes": minute,
        "low": 10_000_000,
        "deltaOpen": 1000,
        "deltaHigh": 2000,
        "volume": 10,
    }
    if close_delta is not None:
        data["deltaClose"] = close_delta
    return data


def _feed(account_id: int = 1):
    return FeedRegistration(
        deployment_id=uuid4(), broker_account_id=uuid4(), environment="DEMO",
        account_id=account_id, symbol="EURUSD", symbol_id=100, timeframe="M1", period=1,
        client_id="client", client_secret="secret", access_token="token",
    )


def test_ctrader_missing_delta_close_is_never_faked_as_low():
    minute = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() // 60)
    raw = _bar(minute, None)
    with pytest.raises(ValueError, match="deltaClose"):
        _decode_trendbar(raw, symbol="EURUSD", timeframe="M1")
    provisional = _decode_trendbar(raw, symbol="EURUSD", timeframe="M1", require_close=False)
    assert provisional["close"] is None
    valid_low_close = _decode_trendbar(_bar(minute, 0), symbol="EURUSD", timeframe="M1")
    assert valid_low_close["close"] == valid_low_close["low"]


def test_ctrader_rejects_invalid_price_range():
    minute = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() // 60)
    with pytest.raises(ValueError, match="outside"):
        _decode_trendbar(_bar(minute, 9000), symbol="EURUSD", timeframe="M1")


def test_new_bar_recovers_one_historical_close_for_each_deployment():
    async def scenario():
        worker = LiveMarketWorker(_UnusedRedis())
        first = _feed()
        second = _feed()
        worker.feeds = {first.deployment_id: first, second.deployment_id: second}
        base_minute = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() // 60)
        authoritative = _decode_trendbar(_bar(base_minute, 1500), symbol="EURUSD", timeframe="M1")
        calls = []

        async def verified_fetch(_feed, count):
            calls.append(count)
            return [authoritative]

        worker._fetch_bars = verified_fetch
        worker._handle_spot_event("DEMO", {"payload": {
            "ctidTraderAccountId": 1, "symbolId": 100,
            "trendbar": [_bar(base_minute, None)],
        }})
        assert worker._candle_queue.qsize() == 0
        next_event = {"payload": {
            "ctidTraderAccountId": 1, "symbolId": 100,
            "trendbar": [_bar(base_minute + 1, None)],
        }}
        worker._handle_spot_event("DEMO", next_event)
        worker._handle_spot_event("DEMO", next_event)
        await asyncio.gather(*worker._tasks)
        assert calls == [5]
        assert worker._candle_queue.qsize() == 2
        for _ in range(2):
            feed, candle, source, _received = worker._candle_queue.get_nowait()
            assert feed in (first, second)
            assert source == "CTRADER_LIVE_VERIFIED"
            assert candle["close"] > candle["low"]
    asyncio.run(scenario())


def test_broker_history_not_ready_does_not_publish_fake_spot_close():
    async def scenario():
        worker = LiveMarketWorker(_UnusedRedis())
        feed = _feed()
        worker.feeds = {feed.deployment_id: feed}
        base_minute = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() // 60)
        worker._fetch_bars = lambda *_args: asyncio.sleep(0, result=[])
        worker._handle_spot_event("DEMO", {"payload": {
            "ctidTraderAccountId": 1, "symbolId": 100, "trendbar": [_bar(base_minute, None)],
        }})
        worker._handle_spot_event("DEMO", {"payload": {
            "ctidTraderAccountId": 1, "symbolId": 100, "trendbar": [_bar(base_minute + 1, None)],
        }})
        await asyncio.gather(*worker._tasks)
        assert worker._candle_queue.empty()
    asyncio.run(scenario())


def test_missing_candle_watchdog_uses_only_plus_3_and_plus_8_recovery_checks():
    async def scenario():
        worker = LiveMarketWorker(_UnusedRedis())
        feed = _feed()
        feed.timeframe = "M5"
        feed.period = 5
        feed.last_closed_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        worker.feeds = {feed.deployment_id: feed}
        calls = []

        async def fake_backfill(registration, *, publish_missing):
            calls.append((registration.deployment_id, publish_missing))

        worker._backfill_feed = fake_backfill
        close = datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)
        await worker._watchdog_check_once(close + timedelta(seconds=2))
        assert calls == []
        await worker._watchdog_check_once(close + timedelta(seconds=3))
        assert len(calls) == 1
        await worker._watchdog_check_once(close + timedelta(seconds=7))
        assert len(calls) == 1
        await worker._watchdog_check_once(close + timedelta(seconds=8))
        assert len(calls) == 2
        await worker._watchdog_check_once(close + timedelta(seconds=20))
        assert len(calls) == 2
    asyncio.run(scenario())


def test_slow_deployment_does_not_block_another_candle():
    async def scenario():
        worker = LiveMarketWorker(_UnusedRedis())
        slow, fast = _feed(1), _feed(2)
        slow_release = asyncio.Event()
        fast_done = asyncio.Event()
        started = asyncio.Event()

        async def fake_persist(feed, *_args):
            if feed.deployment_id == slow.deployment_id:
                started.set()
                await slow_release.wait()
            else:
                fast_done.set()

        worker._persist_and_publish = fake_persist
        task = asyncio.create_task(worker._candle_processor_loop())
        try:
            await worker._candle_queue.put((slow, {}, "TEST", datetime.now(timezone.utc)))
            await asyncio.wait_for(started.wait(), timeout=1)
            await worker._candle_queue.put((fast, {}, "TEST", datetime.now(timezone.utc)))
            await asyncio.wait_for(fast_done.wait(), timeout=1)
        finally:
            slow_release.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await worker._candle_queue.join()
    asyncio.run(scenario())
