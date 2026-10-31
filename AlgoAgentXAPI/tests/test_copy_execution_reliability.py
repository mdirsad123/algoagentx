"""Offline regression tests: no credentials, database writes, or broker network."""
import asyncio
import json
import hashlib
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.services.brokers import tradelocker as tl
from app.services.brokers.request_context import OrderRequestContext, order_request_context
from app.services.live import execution_engine as engine


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    tl._SESSION_CACHE.clear()
    tl._METADATA_LOCKS.clear()
    tl._RATE_LIMIT_UNTIL.clear()
    monkeypatch.setattr(tl, 'redis_manager', SimpleNamespace(client=None))


def adapter(account='479'):
    obj = tl.TradeLockerAdapter.__new__(tl.TradeLockerAdapter)
    obj.account_id, obj.acc_num = account, 1
    obj.environment, obj.base, obj.server = 'demo', 'https://broker.invalid', 'test'
    obj._session_key = f'test-{account}'
    obj._config_cache = {'accountDetailsConfig': {'columns': ['balance', 'equity']}}
    obj._token = AsyncMock(return_value='test-only')
    return obj


@pytest.mark.asyncio
async def test_account_metadata_cached_but_equity_always_fresh():
    a, b = adapter(), adapter()
    calls = []
    async def request(method, path):
        calls.append(path)
        if path == '/trade/accounts':
            return {'d': [{'id': '479', 'accNum': 1, 'currency': 'USD', 'balance': 99999}]}
        return {'d': {'accountDetailsData': [5000, 4900 - len(calls)]}}
    a._request = b._request = request
    one, two = await a.get_account_info(), await b.get_account_info()
    assert calls.count('/trade/accounts') == 1
    assert calls.count('/trade/accounts/479/state') == 2
    assert one['equity'] != two['equity']
    assert 'balance' not in one['account']


@pytest.mark.asyncio
async def test_concurrent_metadata_cache_miss_single_flight():
    a, b = adapter(), adapter()
    request = AsyncMock(return_value={'d': [{'id': '479', 'accNum': 1}]})
    a._request = b._request = request
    await asyncio.gather(a._selected_account_metadata(), b._selected_account_metadata())
    assert request.await_count == 1


@pytest.mark.asyncio
async def test_metadata_never_crosses_accounts_or_accepts_accnum_mismatch():
    a = adapter()
    a._request = AsyncMock(return_value={'d': [{'id': '479', 'accNum': 2}]})
    with pytest.raises(ValueError, match='accNum'):
        await a._selected_account_metadata()
    assert 'selected_account' not in tl._SESSION_CACHE.get(a._session_key, {})


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [429, 502, 503, 504])
async def test_safe_read_bounded_recovery(monkeypatch, status):
    obj = adapter()
    responses = [httpx.Response(status, headers={'Retry-After': '0'}), httpx.Response(200, json={'d': []})]
    client = SimpleNamespace(request=AsyncMock(side_effect=responses))
    obj._http_client = lambda: client
    monkeypatch.setattr(tl.asyncio, 'sleep', AsyncMock())
    assert await obj._request('GET', '/trade/accounts') == {'d': []}
    assert client.request.await_count == 2


@pytest.mark.asyncio
async def test_429_long_wait_never_outlives_signal():
    obj = adapter()
    client = SimpleNamespace(request=AsyncMock(return_value=httpx.Response(429, headers={'Retry-After': '900'})))
    obj._http_client = lambda: client
    token = order_request_context.set(OrderRequestContext(time.time() + 0.5, 's', 'a', time.time()))
    try:
        with pytest.raises(RuntimeError, match='budget'):
            await obj._request('GET', '/trade/accounts')
        assert client.request.await_count == 1
        assert await obj._cooldown() > 890
    finally:
        order_request_context.reset(token)


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [500, 502, 503, 504, 507])
async def test_ambiguous_post_not_retried(status):
    obj = adapter()
    client = SimpleNamespace(request=AsyncMock(return_value=httpx.Response(status)))
    obj._http_client = lambda: client
    with pytest.raises(httpx.TransportError):
        await obj._request('POST', '/trade/accounts/479/orders', body={})
    assert client.request.await_count == 1


def test_retry_after_http_date_and_uncapped_seconds():
    assert tl._retry_after_seconds('900') == 900
    future = datetime.now(timezone.utc) + timedelta(seconds=300)
    assert 298 < tl._retry_after_seconds(future.strftime('%a, %d %b %Y %H:%M:%S GMT')) <= 300


def test_stale_signal_deadline_uses_original_candle_not_dispatch():
    candle = datetime.now(timezone.utc) - timedelta(minutes=10)
    deadline = engine._copy_deadline({'timeframe': 'M5'}, {'candle_time': candle})
    with pytest.raises(TimeoutError):
        OrderRequestContext(deadline, 's', 'a', time.time()).check()
    with pytest.raises(ValueError):
        engine._copy_deadline({'timeframe': 'M5'}, {})


@pytest.mark.asyncio
async def test_copy_router_starts_siblings_before_any_finishes(monkeypatch):
    from test_copy_trading_expired_orm_regression import _FakeDB, _Signal, _ExplodingDeployment
    primary, a, b = uuid4(), uuid4(), uuid4()
    dep = dict(id=uuid4(), user_id=uuid4(), broker_account_id=primary, copy_trading_enabled=True,
               copy_broker_account_ids=[a, b], account_policy_type='STANDARD', timeframe='M5')
    sig = dict(id=uuid4(), status='RECEIVED', rejection_reason=None, signal_type='SELL', symbol='XAUUSD')
    db = _FakeDB(dep, sig, SimpleNamespace(mode='DEMO', broker_code='TRADELOCKER'), None)
    primary_order = SimpleNamespace(id=uuid4(), status='FILLED')
    monkeypatch.setattr(engine, '_execute_signal_for_account', AsyncMock(return_value=primary_order))
    monkeypatch.setattr(engine, '_log', AsyncMock())
    monkeypatch.setattr(engine, '_canonical_copy_symbol', AsyncMock(return_value='XAUUSD'))
    started = []
    both_started = asyncio.Event()
    async def dispatch(**kw):
        started.append(kw['account_id'])
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), 0.5)
        if kw['account_id'] == a:
            raise RuntimeError('isolated account failure')
        return SimpleNamespace(id=uuid4(), status='FILLED')
    monkeypatch.setattr(engine, '_dispatch_copy_account', dispatch)
    result = await engine.execute_signal(db, _ExplodingDeployment(dep), _Signal(sig))
    assert result is primary_order
    assert set(started) == {a, b}


@pytest.mark.asyncio
async def test_reservation_commits_before_submission_and_duplicate_does_not_claim(monkeypatch):
    existing = SimpleNamespace(id=uuid4(), status='PENDING')
    events = []
    class DB:
        async def flush(self): events.append('flush')
        async def execute(self, statement):
            assert 'ON CONFLICT DO NOTHING' in str(statement)
            return SimpleNamespace(scalar_one_or_none=lambda: None)
        async def commit(self): events.append('commit')
    monkeypatch.setattr(engine, '_existing_order_for_client_id', AsyncMock(return_value=existing))
    dep = SimpleNamespace(id=uuid4(), user_id=uuid4(), broker_account_id=uuid4())
    sig = SimpleNamespace(id=uuid4())
    order, claimed = await engine._reserve_entry(DB(), dep, sig, 'client', 'key', 'XAUUSD', 'SELL', Decimal('.01'), Decimal(4000), Decimal(4010), Decimal(3980))
    assert order is existing and not claimed
    assert events == ['flush', 'commit']


@pytest.mark.asyncio
@pytest.mark.parametrize('payload', [[], None, 'invalid'])
async def test_non_object_write_acknowledgement_is_uncertain(payload):
    obj = adapter()
    client = SimpleNamespace(request=AsyncMock(return_value=httpx.Response(200, content=json.dumps(payload))))
    obj._http_client = lambda: client
    with pytest.raises(httpx.TransportError):
        await obj._request('POST', '/trade/accounts/479/orders', body={})
    assert client.request.await_count == 1


@pytest.mark.asyncio
async def test_history_recovers_only_exact_strategy_identifiers():
    obj = adapter()
    obj._table = AsyncMock(return_value=[
        {'id': 'known', 'strategyId': 'other'},
        {'id': 'lost-ack', 'strategyId': 'AX-exact'},
        {'id': 'unrelated', 'strategyId': 'AX-exact-other'},
    ])
    rows = await obj.get_order_history(['known'], strategy_ids=['AX-exact'])
    assert [row['id'] for row in rows] == ['known', 'lost-ack']
    obj._table.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('signal_type,primary_status,dispatches', [
    ('EXIT', None, 1), ('EXIT', 'PLACED', 1),
    ('BUY', None, 0), ('BUY', 'PLACED', 0), ('BUY', 'FILLED', 1),
])
async def test_primary_fill_gate_does_not_suppress_explicit_exits(monkeypatch, signal_type, primary_status, dispatches):
    from test_copy_trading_expired_orm_regression import _FakeDB, _Signal, _ExplodingDeployment
    primary, target = uuid4(), uuid4()
    dep = dict(id=uuid4(), user_id=uuid4(), broker_account_id=primary, copy_trading_enabled=True,
               copy_broker_account_ids=[target], account_policy_type='STANDARD', timeframe='M5')
    sig = dict(id=uuid4(), status='RECEIVED', rejection_reason=None, signal_type=signal_type, symbol='XAUUSD')
    db = _FakeDB(dep, sig, SimpleNamespace(mode='DEMO', broker_code='TRADELOCKER'), None)
    order = SimpleNamespace(id=uuid4(), status=primary_status) if primary_status else None
    monkeypatch.setattr(engine.settings, 'live_copy_trading_enabled', True)
    monkeypatch.setattr(engine, '_execute_signal_for_account', AsyncMock(return_value=order))
    monkeypatch.setattr(engine, '_log', AsyncMock())
    monkeypatch.setattr(engine, '_canonical_copy_symbol', AsyncMock(return_value='XAUUSD'))
    dispatch = AsyncMock(return_value=None)
    monkeypatch.setattr(engine, '_dispatch_copy_account', dispatch)
    await engine.execute_signal(db, _ExplodingDeployment(dep), _Signal(sig))
    assert dispatch.await_count == dispatches


@pytest.mark.asyncio
async def test_dispatch_sessions_and_contexts_are_isolated_and_exit_has_no_entry_expiry(monkeypatch):
    accounts = [uuid4(), uuid4()]
    sessions, observed = [], []
    ready = asyncio.Event()

    class Session:
        def __init__(self):
            sessions.append(self)
            self.queries = 0
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def execute(self, statement, *args):
            self.queries += 1
            if self.queries == 1:
                return SimpleNamespace(scalar=lambda: True)
            return SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace(status='CONNECTED', mode='DEMO', broker_code='CTRADER'))
        async def commit(self): pass
        async def rollback(self): pass

    async def execute(db, dep, sig):
        context = order_request_context.get()
        observed.append((db, dep.broker_account_id, context))
        if len(observed) == 2:
            ready.set()
        await asyncio.wait_for(ready.wait(), 1)
        assert order_request_context.get() is context
        assert context.deadline == float('inf')
        return None

    monkeypatch.setattr(engine, 'async_session', Session)
    monkeypatch.setattr(engine, '_execute_signal_for_account', execute)
    monkeypatch.setattr(engine, '_log', AsyncMock())
    dep = dict(id=uuid4(), user_id=uuid4(), timeframe='M5')
    sig = dict(id=uuid4(), signal_type='EXIT', status='RECEIVED', rejection_reason=None,
               candle_time=datetime.now(timezone.utc) - timedelta(days=1))
    await asyncio.gather(*(engine._dispatch_copy_account(
        account_id=account, deployment_snapshot=dep, signal_snapshot=sig, canonical_symbol='XAUUSD',
        primary_signal_symbol='XAUUSD', primary_mode='DEMO', primary_broker_code='TRADELOCKER',
        primary_completed_at=time.time()) for account in accounts))
    assert len(observed) == 2
    assert observed[0][0] is not observed[1][0]
    assert observed[0][2] is not observed[1][2]
    assert {row[2].account_id for row in observed} == {str(account) for account in accounts}
    assert order_request_context.get() is None


@pytest.mark.asyncio
async def test_lost_ack_history_is_requested_and_fresh_equity_replaces_old_snapshot(monkeypatch):
    from app.services.live import broker_sync_service as sync
    dep = SimpleNamespace(id=uuid4(), broker_account_id=uuid4())
    broker = SimpleNamespace(broker_code='TRADELOCKER', metadata_json={
        'account_info': {'balance': '9999', 'equity': '9999'},
    })
    key = 'durable-lost-ack-key'
    results = iter([
        SimpleNamespace(scalar_one_or_none=lambda: broker),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [None])),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [key])),
    ])
    db = SimpleNamespace(execute=AsyncMock(side_effect=lambda *args: next(results)))
    adapter = SimpleNamespace(
        get_positions=AsyncMock(return_value=[]),
        get_orders=AsyncMock(return_value=[]),
        get_order_history=AsyncMock(return_value=[{'id': 'recovered'}]),
        get_account_info=AsyncMock(return_value={
            'connected': True, 'balance': Decimal('5000'), 'equity': Decimal('4900'),
            'free_margin': Decimal('4800'),
        }),
    )
    monkeypatch.setattr(sync, 'get_broker_adapter', lambda *args: adapter)
    monkeypatch.setattr(sync, 'reconcile_positions', AsyncMock(return_value={}))
    reconcile = AsyncMock(return_value={'orders_updated': 1})
    monkeypatch.setattr(sync, 'reconcile_orders', reconcile)
    monkeypatch.setattr(sync, '_write_log', AsyncMock())
    result = await sync.sync_tradelocker_pretrade_positions(db, dep)
    adapter.get_order_history.assert_awaited_once_with(
        [], strategy_ids=['AX-' + hashlib.sha256(key.encode()).hexdigest()[:28]])
    assert reconcile.await_args.args[2] == [{'id': 'recovered'}]
    assert result['orders_updated'] == 1
    assert broker.metadata_json['account_info']['equity'] == '4900'
    assert broker.metadata_json['account_info']['balance'] == '5000'


@pytest.mark.asyncio
@pytest.mark.parametrize('matches', [True, False])
async def test_lost_ack_reconciliation_requires_exact_durable_identity(monkeypatch, matches):
    from app.services.live import broker_sync_service as sync
    dep = SimpleNamespace(id=uuid4(), broker_account_id=uuid4())
    key = 'durable-lost-ack-key'
    local = SimpleNamespace(idempotency_key=key, broker_order_id=None, status='PENDING', raw_response={})
    results = iter([
        SimpleNamespace(scalar_one_or_none=lambda: None),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [local])),
    ])
    db = SimpleNamespace(execute=AsyncMock(side_effect=lambda *args: next(results)))
    monkeypatch.setattr(sync, '_save_event', AsyncMock())
    strategy_id = 'AX-' + hashlib.sha256((key if matches else 'other').encode()).hexdigest()[:28]
    result = await sync.reconcile_orders(db, dep, [
        {'id': 'recovered', 'strategyId': strategy_id, 'status': 'Filled'},
    ], 'TRADELOCKER')
    assert result['orders_updated'] == int(matches)
    assert local.broker_order_id == ('recovered' if matches else None)
    assert local.status == ('FILLED' if matches else 'PENDING')