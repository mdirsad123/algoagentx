import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.live import observer_cache as cache
from app.services.live.live_event_bus import LiveEventBus


def test_cache_key_scopes_user_role_query_and_deployment_state():
    deployment = SimpleNamespace(id=uuid4(), status='RUNNING')
    user = {'user_id': str(uuid4()), 'role': 'user'}
    key = cache.observer_key('candles', deployment, user, limit=50)
    assert key != cache.observer_key('candles', deployment, user, limit=100)
    assert key != cache.observer_key('summary', deployment, user, limit=50)
    assert key != cache.observer_key('candles', deployment, {**user, 'role': 'admin'}, limit=50)
    assert key != cache.observer_key('candles', deployment, {**user, 'user_id': str(uuid4())}, limit=50)
    deployment.status = 'PAUSED'
    assert key != cache.observer_key('candles', deployment, user, limit=50)


def test_cache_roundtrip_and_ttl(monkeypatch):
    client = SimpleNamespace(get=AsyncMock(), set=AsyncMock())
    monkeypatch.setattr(cache, 'redis_manager', SimpleNamespace(client=client))

    async def check():
        response = {'success': True, 'data': {'at': datetime(2026, 10, 29, tzinfo=timezone.utc)}}
        assert await cache.store_observer_cache('key', response, ttl=1) is response
        args = client.set.call_args
        assert args.kwargs == {'ex': 1}
        client.get.return_value = args.args[1].encode()
        assert (await cache.read_observer_cache('key'))['data']['at'].startswith('2026-10-29')
    asyncio.run(check())


@pytest.mark.parametrize('raw', [None, b'invalid', b'[]', b'{"success":false}'])
def test_malformed_or_failed_results_are_not_hits(monkeypatch, raw):
    monkeypatch.setattr(cache, 'redis_manager', SimpleNamespace(client=SimpleNamespace(get=AsyncMock(return_value=raw))))
    assert asyncio.run(cache.read_observer_cache('key')) is None


def test_cache_outage_and_cancellation(monkeypatch):
    client = SimpleNamespace(get=AsyncMock(side_effect=OSError()), set=AsyncMock(side_effect=OSError()))
    monkeypatch.setattr(cache, 'redis_manager', SimpleNamespace(client=client))
    async def check():
        assert await cache.read_observer_cache('key') is None
        assert await cache.store_observer_cache('key', {'success': True}) == {'success': True}
        client.get.side_effect = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await cache.read_observer_cache('key')
    asyncio.run(check())


def test_cache_timeout_is_bounded(monkeypatch):
    async def stalled(*args):
        await asyncio.sleep(10)
    monkeypatch.setattr(cache, 'CACHE_IO_TIMEOUT', .001)
    monkeypatch.setattr(cache, 'redis_manager', SimpleNamespace(client=SimpleNamespace(get=stalled)))
    assert asyncio.run(cache.read_observer_cache('key')) is None


def test_health_reads_use_one_mget():
    redis = SimpleNamespace(mget=AsyncMock(return_value=[b'{"status":"HEALTHY"}', None, b'broken']))
    result = asyncio.run(LiveEventBus(redis).get_health_many(('a', 'b', 'c')))
    assert result == {'a': {'status': 'HEALTHY'}, 'b': None, 'c': None}
    redis.mget.assert_awaited_once_with(['live:worker_health:a', 'live:worker_health:b', 'live:worker_health:c'])


@pytest.mark.parametrize('name,extra', [
    ('get_deployment_summary', {'refresh_broker': False}),
    ('get_deployment_latency', {'limit': 50}),
    ('get_deployment_latest_latency', {}),
    ('get_deployment_pipeline_health', {}),
    ('get_deployment_broker_candles', {'limit': 50}),
])
def test_every_cache_hit_still_requires_fresh_authorization(monkeypatch, name, extra):
    from app.api.v1 import live_deployments as routes
    auth = AsyncMock(side_effect=HTTPException(status_code=404))
    read = AsyncMock(return_value={'success': True, 'data': 'private'})
    monkeypatch.setattr(routes, 'get_deployment_or_404', auth)
    monkeypatch.setattr(routes, 'read_observer_cache', read)
    with pytest.raises(HTTPException):
        asyncio.run(getattr(routes, name)(deployment_id=uuid4(), db=object(), current_user={'user_id': str(uuid4())}, **extra))
    read.assert_not_awaited()


def test_explicit_summary_refresh_bypasses_cache(monkeypatch):
    from app.api.v1 import live_deployments as routes
    monkeypatch.setattr(routes, 'get_deployment_or_404', AsyncMock(return_value=object()))
    summary = AsyncMock(return_value={'fresh': True})
    monkeypatch.setattr(routes, '_summary', summary)
    read = AsyncMock()
    monkeypatch.setattr(routes, 'read_observer_cache', read)
    result = asyncio.run(routes.get_deployment_summary(uuid4(), refresh_broker=True, db=object(), current_user={}))
    assert result['data'] == {'fresh': True}
    read.assert_not_awaited()