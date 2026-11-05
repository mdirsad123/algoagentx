"""Offline acceptance contracts. Transport, persistence and Redis are simulated.

The tests never call a broker, use real credentials or create database orders.
"""
import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.services.brokers import tradelocker as tl, shared_cache, auth_failure_guard
from app.services.brokers.base import BrokerOrderRequest
from app.services.brokers.request_context import OrderRequestContext, order_request_context
from app.services.brokers.tradelocker_protection import verify_protection
from app.services.live import broker_sync_service as sync
from app.services.live.protection_reporting import attach_protection


class Redis:
    """Minimal atomic Redis lease semantics with actual expiry for concurrency tests."""
    def __init__(self):
        self.values = {}
        self.expires = {}

    async def get(self, key):
        if self.expires.get(key, 0) <= time.monotonic():
            return None
        return self.values.get(key)

    async def exists(self, key):
        return bool(await self.get(key))

    async def set(self, key, value, *, nx=False, px=None, ex=None):
        if nx and await self.exists(key):
            return False
        self.values[key] = value
        self.expires[key] = time.monotonic() + (px / 1000 if px is not None else ex or 3600)
        return True

    async def pttl(self, key):
        return int((self.expires.get(key, 0) - time.monotonic()) * 1000) if await self.exists(key) else -2

    async def delete(self, key):
        self.values.pop(key, None)
        self.expires.pop(key, None)

    async def eval(self, script, count, *args):
        keys, values = args[:count], args[count:]
        if "psetex" in script:
            if await self.pttl(keys[0]) < int(values[0]):
                await self.set(keys[0], '1', px=int(values[0]))
            return 1
        if await self.get(keys[0]) != values[0]:
            return 0
        if count == 2:
            await self.set(keys[1], values[1], ex=int(values[2]))
        else:
            await self.delete(keys[0])
        return 1


@pytest.fixture(autouse=True)
def isolation(monkeypatch):
    redis = Redis()
    manager = SimpleNamespace(client=redis)
    for module in (tl, shared_cache, auth_failure_guard):
        monkeypatch.setattr(module, 'redis_manager', manager)
    tl._SESSION_CACHE.clear()
    tl._RATE_LIMIT_UNTIL.clear()
    shared_cache._VALUES.clear()
    shared_cache._LOCKS.clear()
    auth_failure_guard._INVALID.clear()
    monkeypatch.setenv('SECRET_KEY', 'offline-test-only-encryption-key')
    monkeypatch.setenv('TRADELOCKER_SHARED_REQUEST_SPACING_MS', '1')
    monkeypatch.setenv('TRADELOCKER_ORDER_EXECUTION_ENABLED', 'true')
    yield redis
    auth_failure_guard._INVALID.clear()


def adapter(number):
    return tl.TradeLockerAdapter(SimpleNamespace(
        id=uuid4(), metadata_json={'tradelocker_environment': 'demo',
                                  'tradelocker_account_id': str(number), 'tradelocker_acc_num': number},
        login_id='offline@example.invalid', server_name='offline', encrypted_password='test-only'))


@pytest.mark.asyncio
async def test_three_accounts_share_one_encrypted_session_not_account_metadata(isolation):
    accounts = [adapter(i) for i in (1, 2, 3)]
    calls = []
    async def request(method, path, **kwargs):
        calls.append(path)
        await asyncio.sleep(0.01)
        return {'d': {'accessToken': 'demo-test-token', 'expiresIn': 600}}
    for account in accounts:
        account._request = request
    assert len({a._login_key for a in accounts}) == 1
    assert len({a._session_key for a in accounts}) == 3
    assert await asyncio.gather(*(a._token() for a in accounts)) == ['demo-test-token'] * 3
    assert calls == ['/auth/jwt/token']
    assert 'demo-test-token' not in str(isolation.values)
    # Simulate another worker without any local cache/locks.
    shared_cache._LOCKS.clear()
    shared_cache._VALUES.clear()
    fourth = adapter(4)
    fourth._request = AsyncMock(side_effect=AssertionError('duplicate authentication'))
    assert await fourth._token() == 'demo-test-token'
    for account in accounts:
        account._request = AsyncMock(return_value={'d': [{'id': account.account_id, 'accNum': account.acc_num}]})
    assert [x['id'] for x in await asyncio.gather(*(a._selected_account_metadata() for a in accounts))] == ['1', '2', '3']


@pytest.mark.asyncio
async def test_expired_session_get_refreshes_once_and_write_never_replays():
    obj = adapter(1)
    obj._token = AsyncMock(side_effect=['expired', 'renewed'])
    client = SimpleNamespace(request=AsyncMock(side_effect=[httpx.Response(401), httpx.Response(200, json={'d': []})]))
    obj._http_client = lambda: client
    assert await obj._request('GET', '/trade/accounts') == {'d': []}
    assert obj._token.await_count == 2
    obj._token = AsyncMock(return_value='expired')
    client.request = AsyncMock(return_value=httpx.Response(401))
    with pytest.raises(RuntimeError, match='401'):
        await obj._request('POST', '/trade/accounts/1/orders', body={})
    assert client.request.await_count == 1


@pytest.mark.asyncio
async def test_three_copy_orders_independent_unknown_rejected_and_ack(isolation):
    accounts = [adapter(i) for i in (1, 2, 3)]
    posted = []
    request = BrokerOrderRequest(symbol='XAUUSD.X', side='BUY', qty=Decimal('.01'),
                                price=Decimal('4000'), stop_loss=Decimal('3990'), target=Decimal('4020'))
    async def execute(account):
        account._instrument = AsyncMock(return_value={'tradableInstrumentId': 1, 'routes': [{'type': 'TRADE', 'id': 1}]})
        account._token = AsyncMock(return_value='test')
        async def wire(*args, **kwargs):
            posted.append(account.account_id)
            await asyncio.sleep(0.005)
            if account.account_id == '2':
                raise httpx.ReadTimeout('lost acknowledgement')
            if account.account_id == '3':
                return httpx.Response(400)
            return httpx.Response(200, json={'d': {'orderId': 'filled-later-1'}})
        account._http_client = lambda: SimpleNamespace(request=wire)
        token = order_request_context.set(OrderRequestContext(time.time() + 2, 'signal', account.account_id, time.time()))
        try:
            return await account.place_market_order(request)
        finally:
            order_request_context.reset(token)
    results = await asyncio.gather(*(execute(a) for a in accounts))
    assert [r.status for r in results] == ['PLACED', 'UNCERTAIN', 'ERROR']
    assert sorted(posted) == ['1', '2', '3']  # Exactly one POST each.
    assert results[0].broker_order_id == 'filled-later-1'


@pytest.mark.asyncio
async def test_429_blocks_all_workers_then_recovers_without_write_retry(isolation):
    one, two, three = [adapter(i) for i in (1, 2, 3)]
    one._token = two._token = three._token = AsyncMock(return_value='test')
    failed = SimpleNamespace(request=AsyncMock(return_value=httpx.Response(429, headers={'Retry-After': '0.05'})))
    one._http_client = lambda: failed
    with pytest.raises(RuntimeError, match='budget'):
        await one._request('GET', '/trade/accounts/1/positions')
    successful = SimpleNamespace(request=AsyncMock(return_value=httpx.Response(200, json={'d': []})))
    two._http_client = three._http_client = lambda: successful
    for a in (two, three):
        with pytest.raises(RuntimeError, match='cooldown'):
            await a._request('GET', f'/trade/accounts/{a.account_id}/positions')
    successful.request.assert_not_awaited()
    await asyncio.sleep(.06)
    await two._request('GET', '/trade/accounts/2/positions')
    assert successful.request.await_count == 1


@pytest.mark.asyncio
async def test_background_cannot_take_slot_during_entry_priority(isolation):
    await isolation.set('tradelocker:entry-priority:demo', '1', ex=1)
    obj = adapter(1)
    obj._token = AsyncMock(return_value='test')
    for path in ('/trade/quotes', '/trade/history', '/trade/accounts/1/state', '/trade/accounts/1/positions'):
        with pytest.raises(RuntimeError, match='deferred'):
            await obj._request('GET', path)
    obj._token.assert_not_awaited()


@pytest.mark.asyncio
async def test_route_quota_shared_by_three_accounts(isolation):
    accounts = [adapter(i) for i in (1, 2, 3)]
    times = []
    async def take(a):
        a._config_cache = {'rateLimits': [{'rateLimitType': 'GET_POSITIONS', 'measure': 'SECONDS', 'intervalNum': .03, 'limit': 1}]}
        token = order_request_context.set(OrderRequestContext(time.time() + 2, 's', a.account_id, time.time()))
        try:
            await a._pace_route('GET', f'/trade/accounts/{a.account_id}/positions', time.time() + 2)
            times.append(time.monotonic())
        finally:
            order_request_context.reset(token)
    await asyncio.gather(*(take(a) for a in accounts))
    assert len(times) == 3
    assert min(b - a for a, b in zip(times, times[1:])) >= .03


@pytest.mark.asyncio
async def test_background_sync_never_reads_financials(monkeypatch):
    broker = SimpleNamespace(id=uuid4(), broker_code='TRADELOCKER')
    db = SimpleNamespace(info={}, execute=AsyncMock(side_effect=[
        SimpleNamespace(scalar_one_or_none=lambda: broker),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),
    ]))
    obj = SimpleNamespace(get_positions=AsyncMock(return_value=[]), get_account_info=AsyncMock())
    monkeypatch.setattr(sync, 'get_broker_adapter', lambda *a: obj)
    monkeypatch.setattr(sync, 'reconcile_positions', AsyncMock(return_value={}))
    monkeypatch.setattr(sync, '_write_log', AsyncMock())
    await sync.sync_tradelocker_pretrade_positions(db, SimpleNamespace(id=uuid4(), broker_account_id=broker.id), refresh_financials=False)
    obj.get_positions.assert_awaited_once()
    obj.get_account_info.assert_not_awaited()


def protection_fixture():
    position = {'id': 'p', 'side': 'buy', 'qty': '.01', 'stopLossId': 'sl', 'takeProfitId': 'tp'}
    orders = [{'id': 'sl', 'positionId': 'p', 'side': 'sell', 'qty': '.01', 'type': 'stop', 'status': 'New', 'stopPrice': '3990'},
              {'id': 'tp', 'positionId': 'p', 'side': 'sell', 'qty': '.01', 'type': 'limit', 'status': 'New', 'price': '4020'}]
    return position, orders


@pytest.mark.asyncio
async def test_cache_deadline_includes_local_lock_wait():
    key = 'test:local-contention'
    lock = shared_cache._LOCKS.setdefault((asyncio.get_running_loop(), key), asyncio.Lock())
    loader = AsyncMock(return_value={})
    async with lock:
        with pytest.raises(TimeoutError):
            await shared_cache.cached(key, 60, loader, deadline=time.time() + .03)
    loader.assert_not_awaited()


@pytest.mark.asyncio
async def test_cache_deadline_cancels_loader_and_releases_lease(isolation):
    async def slow():
        await asyncio.sleep(10)
    with pytest.raises(TimeoutError):
        await shared_cache.cached('test:slow', 60, slow, deadline=time.time() + .03)
    assert await isolation.get('test:slow') is None
    assert await isolation.get('test:slow:lock') is None


@pytest.mark.asyncio
async def test_cache_lost_lease_does_not_return_or_publish_stale_value(isolation):
    async def load():
        await isolation.set('test:lease:lock', 'new-owner', ex=30)
        return {'stale': True}
    with pytest.raises(RuntimeError, match='lease expired'):
        await shared_cache.cached('test:lease', 60, load)
    assert await isolation.get('test:lease') is None
    assert await isolation.get('test:lease:lock') == 'new-owner'


@pytest.mark.asyncio
async def test_cache_key_missing_fails_before_authentication(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.delenv('ALGOAGENTX_CREDENTIAL_SECRET', raising=False)
    loader = AsyncMock(return_value={'token': 'never-created'})
    with pytest.raises(RuntimeError, match='encryption key unavailable'):
        await shared_cache.cached('test:no-key', 60, loader, secret=True)
    loader.assert_not_awaited()


@pytest.mark.asyncio
async def test_old_rejection_does_not_invalidate_new_local_token(monkeypatch):
    monkeypatch.setattr(shared_cache, 'redis_manager', SimpleNamespace(client=None))
    shared_cache._VALUES['test:token'] = (time.monotonic() + 60, {'token': 'new'})
    await shared_cache.invalidate_secret('test:token', 'old')
    assert shared_cache._VALUES['test:token'][1]['token'] == 'new'


@pytest.mark.parametrize('change', ['missing_link', 'missing_position_id', 'invalid_side',
                                  'zero_position', 'partial_status', 'partial_quantity', 'nan'])
def test_malformed_or_partially_filled_protection_is_unverified(change):
    position, orders = protection_fixture()
    if change == 'missing_link':
        position.pop('stopLossId')
        orders[0].pop('id')
    if change == 'missing_position_id':
        position.pop('id')
        orders[0].pop('positionId')
    if change == 'invalid_side': position['side'] = 'unknown'
    if change == 'zero_position': position['qty'] = '0'
    if change == 'partial_status': orders[0]['status'] = 'PartiallyFilled'
    if change == 'partial_quantity': orders[0]['filledQty'] = '.001'
    if change == 'nan': position['qty'] = 'NaN'
    assert verify_protection(position, orders)['status'] == 'UNVERIFIED'


@pytest.mark.asyncio
@pytest.mark.parametrize('payload', [[], {'positions': None}, {'positions': [None]},
                                    {'positions': [{'id': 'p', 'protection': ['invalid']}]}])
async def test_malformed_protection_event_is_unverified(payload):
    event = SimpleNamespace(raw_payload=payload)
    db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: event)))
    rows = [{'broker_account_id': str(uuid4()), 'broker_code': 'TRADELOCKER', 'broker_position_id': 'p'}]
    await attach_protection(db, uuid4(), rows)
    assert rows[0]['protection_status'] == 'UNVERIFIED'
    assert rows[0]['stop_loss'] is None and rows[0]['target'] is None


@pytest.mark.parametrize('change', ['none', 'wrong_position', 'cancelled', 'undersized', 'missing'])
def test_protection_only_from_active_exact_linked_orders(change):
    position, orders = protection_fixture()
    if change == 'wrong_position': orders[0]['positionId'] = 'other'
    if change == 'cancelled': orders[0]['status'] = 'Cancelled'
    if change == 'undersized': orders[0]['qty'] = '.001'
    if change == 'missing': orders = []
    result = verify_protection(position, orders)
    assert (result['status'] == 'VERIFIED') == (change == 'none')
    if change == 'none': assert result['stop_loss'] == '3990'


@pytest.mark.asyncio
async def test_ui_never_presents_stale_or_requested_prices_as_protected():
    position, orders = protection_fixture()
    proof = verify_protection(position, orders)
    proof['checked_at'] = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    event = SimpleNamespace(raw_payload={'positions': [{'id': 'p', 'protection': proof}]})
    db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: event)))
    rows = [{'broker_account_id': str(uuid4()), 'broker_code': 'TRADELOCKER', 'broker_position_id': 'p', 'stop_loss': '3990', 'target': '4020'}]
    await attach_protection(db, uuid4(), rows)
    assert rows[0]['stop_loss'] is None and rows[0]['target'] is None
    assert rows[0]['protection_status'] == 'UNVERIFIED'
    assert rows[0]['protection_warning']


@pytest.mark.asyncio
async def test_ctrader_invalid_token_does_not_break_healthy_reconnect():
    from app.services.brokers.ctrader_connection_manager import PersistentCTraderConnection, TrendbarSubscription
    connection = PersistentCTraderConnection(environment='DEMO', client_id='test', client_secret='test')
    connection._account_tokens = {1: 'expired', 2: 'healthy'}
    connection._spot_subscriptions = {1: {100}, 2: {100}}
    connection._trendbar_subscriptions = {TrendbarSubscription(1, 100, 5), TrendbarSubscription(2, 100, 5)}
    async def request(pt, payload, expected):
        if payload.get('accessToken') == 'expired': raise ValueError('CH_ACCESS_TOKEN_INVALID')
        return {}
    connection._request_connected = AsyncMock(side_effect=request)
    await connection._restore_registry()
    assert connection._authorized_accounts == {2}
    assert connection._active_spot_subscriptions == {(2, 100)}
    await auth_failure_guard.check_token('renewed')
    with pytest.raises(ValueError, match='quarantined'):
        await auth_failure_guard.check_token('expired')