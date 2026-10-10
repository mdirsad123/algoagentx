"""No-network regression tests: TradeLocker primary/copy risk and rate limit safeguards."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.services.brokers import tradelocker as tl
from app.services.brokers.base import BrokerOrderRequest
from app.services.live import broker_sync_service as sync


class _Result:
    def __init__(self, row=None, many=None): self.row=row; self.many=many or []
    def scalar_one_or_none(self): return self.row
    def scalars(self): return self
    def all(self): return self.many


class _DB:
    def __init__(self, broker, pending=()): self.broker=broker; self.pending=list(pending); self.calls=0; self.added=[]
    async def execute(self, sql):
        self.calls += 1
        return _Result(row=self.broker) if self.calls==1 else _Result(many=self.pending)
    def add(self, obj): self.added.append(obj)


@pytest.mark.asyncio
async def test_primary_fresh_account_positions_without_history_requests(monkeypatch):
    broker=SimpleNamespace(id=uuid4(),broker_code='TRADELOCKER')
    dep=SimpleNamespace(id=uuid4(),user_id=uuid4(),broker_account_id=broker.id)
    db=_DB(broker)
    adapter=SimpleNamespace(get_positions=AsyncMock(return_value=[]),get_orders=AsyncMock(),get_order_history=AsyncMock())
    monkeypatch.setattr(sync,'get_broker_adapter',lambda *args:adapter)
    monkeypatch.setattr(sync,'reconcile_positions',AsyncMock(return_value={'positions_closed':1,'open_positions_count':0}))
    result=await sync.sync_tradelocker_pretrade_positions(db,dep)
    assert result['positions_closed']==1 and result['open_positions_count']==0
    adapter.get_positions.assert_awaited_once_with()
    adapter.get_orders.assert_not_awaited()
    adapter.get_order_history.assert_not_awaited()
    assert db.added[-1].event_type=='TRADELOCKER_PRE_TRADE_POSITIONS_SYNCED'


@pytest.mark.asyncio
async def test_pretrade_rate_limit_never_assumes_zero_positions(monkeypatch):
    broker=SimpleNamespace(id=uuid4(),broker_code='TRADELOCKER')
    dep=SimpleNamespace(id=uuid4(),user_id=uuid4(),broker_account_id=broker.id)
    adapter=SimpleNamespace(get_positions=AsyncMock(side_effect=RuntimeError('TradeLocker API rate limit reached')))
    monkeypatch.setattr(sync,'get_broker_adapter',lambda *args:adapter)
    patched=AsyncMock()
    monkeypatch.setattr(sync,'reconcile_positions',patched)
    with pytest.raises(RuntimeError,match='rate limit'):
        await sync.sync_tradelocker_pretrade_positions(_DB(broker),dep)
    patched.assert_not_awaited()


@pytest.mark.asyncio
async def test_pending_broker_entry_is_reconciled_before_new_entry(monkeypatch):
    broker=SimpleNamespace(id=uuid4(),broker_code='TRADELOCKER')
    dep=SimpleNamespace(id=uuid4(),user_id=uuid4(),broker_account_id=broker.id)
    db=_DB(broker, pending=['accepted-123'])
    adapter=SimpleNamespace(get_positions=AsyncMock(return_value=[]),get_orders=AsyncMock(return_value=[]),
                            get_order_history=AsyncMock(return_value=[{'id':'accepted-123','status':'Filled'}]))
    monkeypatch.setattr(sync,'get_broker_adapter',lambda *args:adapter)
    monkeypatch.setattr(sync,'reconcile_positions',AsyncMock(return_value={'open_positions_count':0}))
    reconcile=AsyncMock(return_value={'orders_updated':1})
    monkeypatch.setattr(sync,'reconcile_orders',reconcile)
    result=await sync.sync_tradelocker_pretrade_positions(db,dep)
    assert result['orders_updated']==1
    adapter.get_positions.assert_awaited_once_with()
    adapter.get_order_history.assert_awaited_once_with(['accepted-123'])
    assert reconcile.await_args.args[3]=='TRADELOCKER'


@pytest.mark.asyncio
async def test_order_history_rate_limit_keeps_pending_guard(monkeypatch):
    broker=SimpleNamespace(id=uuid4(),broker_code='TRADELOCKER')
    dep=SimpleNamespace(id=uuid4(),user_id=uuid4(),broker_account_id=broker.id)
    db=_DB(broker,pending=['accepted-123'])
    adapter=SimpleNamespace(get_positions=AsyncMock(return_value=[]),get_orders=AsyncMock(side_effect=RuntimeError('429')))
    monkeypatch.setattr(sync,'get_broker_adapter',lambda *args:adapter)
    monkeypatch.setattr(sync,'reconcile_positions',AsyncMock(return_value={'open_positions_count':0}))
    reconcile=AsyncMock()
    monkeypatch.setattr(sync,'reconcile_orders',reconcile)
    await sync.sync_tradelocker_pretrade_positions(db,dep)
    reconcile.assert_not_awaited()
    assert any(x.event_type=='TRADELOCKER_PENDING_ORDER_UNVERIFIED' for x in db.added)


@pytest.mark.asyncio
async def test_position_response_missing_array_is_not_empty(monkeypatch):
    obj=tl.TradeLockerAdapter.__new__(tl.TradeLockerAdapter)
    obj.account_id='111';obj.acc_num=1;obj._config_cache={'positionsConfig':{'columns':['id']}}
    obj._request=AsyncMock(return_value={'d':{}})
    with pytest.raises(RuntimeError,match='missing valid positions list'):
        await obj._table('positions','positionsConfig')


@pytest.mark.asyncio
async def test_ambiguous_order_post_is_not_retried(monkeypatch):
    monkeypatch.setenv('TRADELOCKER_ORDER_EXECUTION_ENABLED','true')
    obj=tl.TradeLockerAdapter.__new__(tl.TradeLockerAdapter)
    obj.environment='demo'; obj.account_id='111';obj.acc_num=1
    obj._instrument=AsyncMock(return_value={'name':'BTCUSD.X','tradableInstrumentId':321,'routes':[{'type':'TRADE','id':45}]})
    obj._request=AsyncMock(side_effect=httpx.ReadTimeout('response lost'))
    result=await obj.place_market_order(BrokerOrderRequest(symbol='BTCUSD.X',side='BUY',qty=Decimal('0.02'),price=Decimal('83025'),stop_loss=Decimal('82979'),target=Decimal('83117'),order_type='MARKET'))
    assert not result.success and result.status=='UNCERTAIN'
    assert result.raw_response['order_outcome_unknown'] is True
    assert obj._request.await_count==1


@pytest.mark.asyncio
async def test_shared_credentials_cache_but_not_different_accounts(monkeypatch):
    tl._SESSION_CACHE.clear()
    def make(acc):
        x=tl.TradeLockerAdapter.__new__(tl.TradeLockerAdapter)
        x.account_id=acc; x.acc_num=1; x.email='user@example.com'; x.password='pass'; x.server='server';x.environment='demo'
        x._session_key=tl._account_key('demo',x.email,x.server,acc,x.password)
        x._access_token=None;x._access_expiry=0
        x._request=AsyncMock(return_value={'d':{'accessToken':f'token_{acc}','expiresIn':600}})
        return x
    a,b,c=make('one'),make('one'),make('two')
    assert await a._token()=='token_one'
    assert await b._token()=='token_one'
    b._request.assert_not_awaited()
    assert await c._token()=='token_two'
    c._request.assert_awaited_once()
    tl._SESSION_CACHE.clear()
