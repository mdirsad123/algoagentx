"""Offline TradeLocker partial-close / hedged-position safety regressions."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

from app.services.brokers.tradelocker import TradeLockerAdapter
from app.services.live.live_partial_exit_service import (
    _linked_broker_position_id, _tradelocker_linked_entry, IN_FLIGHT
)


def adapter():
    obj = TradeLockerAdapter.__new__(TradeLockerAdapter)
    obj.environment = 'demo'
    obj.account_id = '5678'
    obj.acc_num = 123
    obj._request = AsyncMock(return_value={'s': 'ok'})
    return obj


@pytest.mark.asyncio
async def test_partial_close_sends_exact_lots_not_percentage(monkeypatch):
    monkeypatch.setenv('TRADELOCKER_ORDER_EXECUTION_ENABLED', 'true')
    obj = adapter()
    result = await obj.close_position('1234567890', 'LONG', Decimal('0.03'))
    assert result.success is True
    assert result.status == 'PLACED'  # Not filled until broker position reconciles
    assert obj._request.await_args.args == ('DELETE', '/trade/positions/1234567890')
    assert obj._request.await_args.kwargs['body'] == {'qty': 0.03}


@pytest.mark.asyncio
async def test_partial_close_timeout_is_uncertain_not_automatic_retry(monkeypatch):
    monkeypatch.setenv('TRADELOCKER_ORDER_EXECUTION_ENABLED', 'true')
    obj = adapter()
    obj._request.side_effect = TimeoutError('broker response lost')
    result = await obj.close_position('1234567890', 'LONG', Decimal('0.02'))
    assert not result.success and result.status == 'UNCERTAIN'
    assert 'MANUAL_REVIEW' in IN_FLIGHT
    assert obj._request.await_count == 1


@pytest.mark.asyncio
async def test_partial_close_rejects_symbol_position_id(monkeypatch):
    monkeypatch.setenv('TRADELOCKER_ORDER_EXECUTION_ENABLED', 'true')
    obj = adapter()
    result = await obj.close_position('XAUUSD.X', 'LONG', Decimal('0.02'))
    assert result.status == 'REJECTED' and not result.success
    obj._request.assert_not_awaited()


def test_history_link_requires_explicit_position_id():
    assert _linked_broker_position_id({'broker_sync': {'positionId': '123'}}) == '123'
    assert _linked_broker_position_id({'broker_sync': {'id': 'ORDER-321'}}) is None
    assert _linked_broker_position_id({'position_id': '321'}) == '321'
    assert _linked_broker_position_id({'orderId': '321'}) is None


@pytest.mark.asyncio
async def test_entry_protection_only_linked_to_matching_hedged_broker_position():
    p = SimpleNamespace(broker_position_id='888')
    good = SimpleNamespace(id='a', stop_loss=Decimal('4250'), raw_response={'broker_sync': {'positionId': '888'}})
    other = SimpleNamespace(id='b', stop_loss=Decimal('4200'), raw_response={'broker_sync': {'positionId': '889'}})
    assert await _tradelocker_linked_entry(None, p, [other, good]) is good
    assert await _tradelocker_linked_entry(None, p, [good, SimpleNamespace(id='c', stop_loss=Decimal('4255'), raw_response={'positionId': '888'})]) is None

@pytest.mark.asyncio
async def test_partial_exit_trade_and_copy_account_are_scoped_and_reconcile_before_done(monkeypatch):
    """Faked broker ACK, no network/DB: 50% of 0.06 lots closes 0.03 lots."""
    from uuid import uuid4
    from app.services.brokers.base import BrokerOrderResult
    from app.services.live import live_partial_exit_service as svc

    class Result:
        def __init__(self, row): self.row = row
        def scalar_one_or_none(self): return self.row

    class FakeDb:
        def __init__(self, broker): self.broker=broker; self.calls=0; self.added=[]
        async def execute(self, _query):
            self.calls += 1
            return Result(self.broker if self.calls == 1 else None)
        def add(self, row): self.added.append(row)
        async def flush(self): pass

    account_id = uuid4()
    primary_id = uuid4()
    broker=SimpleNamespace(id=account_id, status='CONNECTED', mode='DEMO', broker_code='TRADELOCKER', broker_provider=None)
    deployment=SimpleNamespace(id=uuid4(), user_id=uuid4(), broker_account_id=primary_id)
    position=SimpleNamespace(id=uuid4(), symbol='BTCUSD.X', side='LONG', qty=Decimal('0.06'))
    state=SimpleNamespace(id=uuid4(), broker_account_id=account_id, broker_position_id='987654',
        partial_exit_percent=Decimal('0.5'), partial_exit_at_r=Decimal('1.0'), quantity_mode='LOTS', instrument_spec_snapshot={'min_lot':0.01,'lot_step':0.01},
        idempotency_key='AXPX-TEST', entry_signal_id=uuid4(), runtime_config_snapshot={}, entry_order_id=None,
        attempt_count=0, triggered_at=None)
    db=FakeDb(broker)
    close=AsyncMock(return_value=BrokerOrderResult(True, 'PLACED', 'ACK', broker_order_id='987654'))
    adapter_obj=SimpleNamespace(close_position=close)
    monkeypatch.setattr(svc, 'get_broker_adapter', lambda *_:adapter_obj)
    monkeypatch.setattr(svc.settings, 'live_position_manager_demo_only', True)
    monkeypatch.setattr(svc.settings, 'live_position_manager_broker_send_enabled', True)
    order=await svc.execute_partial_close(db, deployment, state, position, Decimal('3000'), 'BID')
    close.assert_awaited_once_with('987654', 'LONG', Decimal('0.03'))
    assert state.planned_runner_size==Decimal('0.03')
    assert state.partial_status=='AWAITING_RECONCILE' and order.status=='PLACED'
    assert order.broker_account_id==account_id and order.broker_account_id!=deployment.broker_account_id
    assert any(getattr(x, 'event_type', '')=='PARTIAL_EXIT_CLOSE_REQUESTED' for x in db.added)
