import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.services.live.live_market_worker import FeedRegistration, LiveMarketWorker


class _UnusedRedis:
    pass


def _bar(minute: int, close_delta: int = 1000):
    return {
        "period": 1,
        "utcTimestampInMinutes": minute,
        "low": 10_000_000,
        "deltaOpen": 1000,
        "deltaHigh": 2000,
        "deltaClose": close_delta,
        "volume": 10,
    }


def _feed(account_id: int = 1):
    return FeedRegistration(
        deployment_id=uuid4(), broker_account_id=uuid4(), environment="DEMO",
        account_id=account_id, symbol="EURUSD", symbol_id=100, timeframe="M1", period=1,
        client_id="client", client_secret="secret", access_token="token",
    )


def test_new_bar_closes_previous_once_for_each_deployment():
    worker = LiveMarketWorker(_UnusedRedis())
    first = _feed()
    second = _feed()
    worker.feeds = {first.deployment_id: first, second.deployment_id: second}
    base_minute = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() // 60)

    worker._handle_spot_event("DEMO", {"payload": {
        "ctidTraderAccountId": 1, "symbolId": 100, "trendbar": [_bar(base_minute)],
    }})
    assert worker._candle_queue.qsize() == 0

    next_event = {"payload": {
        "ctidTraderAccountId": 1, "symbolId": 100, "trendbar": [_bar(base_minute + 1)],
    }}
    worker._handle_spot_event("DEMO", next_event)
    assert worker._candle_queue.qsize() == 2

    # A duplicate update for the same new bar must not close it a second time.
    worker._handle_spot_event("DEMO", next_event)
    assert worker._candle_queue.qsize() == 2


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
