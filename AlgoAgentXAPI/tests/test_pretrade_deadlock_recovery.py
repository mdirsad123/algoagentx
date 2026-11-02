"""No-network regression coverage for a PostgreSQL pre-trade deadlock."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError

from app.services.live import execution_engine as engine
from app.services.live import order_preview_service as preview
from app.services.live import broker_sync_service as sync


@pytest.mark.asyncio
async def test_pretrade_deadlock_rollback_before_logging(monkeypatch):
    """After a flush deadlock do NOT access expired ORM props or continue to order POST."""
    dep = SimpleNamespace(id=uuid4(), user_id=uuid4(), mode='DEMO',
                          broker_account_id=uuid4(), _copy_execution_target=False)
    broker = SimpleNamespace(id=dep.broker_account_id, broker_code='TRADELOCKER')
    sig = SimpleNamespace(id=uuid4(), signal_type='BUY', trace_id=None,
                          status='RECEIVED', rejection_reason=None)
    db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: broker)),
                         rollback=AsyncMock(), is_active=False)
    logs = AsyncMock()
    monkeypatch.setattr(engine, '_log', logs)
    monkeypatch.setattr(engine, '_trace_service', lambda: SimpleNamespace(mark=AsyncMock()))
    deadlock = DBAPIError('UPDATE broker_accounts', {}, Exception('deadlock detected'))
    monkeypatch.setattr(engine, 'sync_tradelocker_pretrade_positions', AsyncMock(side_effect=deadlock))
    with pytest.raises(DBAPIError, match='deadlock'):
        await engine._execute_signal_for_account_inner(db, dep, sig)
    db.rollback.assert_awaited_once()
    assert all(call.args[2] != 'PRE_TRADE_BROKER_SYNC_FAILED' for call in logs.await_args_list)
    assert sig.status == 'RECEIVED'  # no unsafe rejected status inside failed transaction


@pytest.mark.asyncio
async def test_preview_uses_fresh_session_capital_not_stale_persisted_json(monkeypatch):
    broker_id = uuid4()
    dep = SimpleNamespace(id=uuid4(), broker_account_id=broker_id, capital=Decimal('100000'))
    broker = SimpleNamespace(id=broker_id, metadata_json={'account_info': {'equity': '99000', 'balance': '99000'}})
    db = SimpleNamespace(info={'tradelocker_pretrade_financial_snapshots': {
        str(broker_id): {'connected': True, 'equity': '4900', 'balance': '5000'}
    }}, execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: broker)))
    capital = await preview._safe_capital_snapshot(db, dep)
    assert capital.effective_capital == Decimal('4900')
    assert capital.effective_capital_source == 'BROKER_EQUITY'
    assert broker.metadata_json['account_info']['equity'] == '99000'


@pytest.mark.asyncio
async def test_pretrade_non_db_broker_failure_is_fail_closed(monkeypatch):
    dep = SimpleNamespace(id=uuid4(), user_id=uuid4(), mode='DEMO',
                          broker_account_id=uuid4(), _copy_execution_target=False)
    broker = SimpleNamespace(id=dep.broker_account_id, broker_code='TRADELOCKER')
    sig = SimpleNamespace(id=uuid4(), signal_type='BUY', trace_id=None,
                          status='RECEIVED', rejection_reason=None)
    db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: broker)),
                         rollback=AsyncMock(), is_active=True)
    logs = AsyncMock()
    monkeypatch.setattr(engine, '_log', logs)
    monkeypatch.setattr(engine, '_trace_service', lambda: SimpleNamespace(mark=AsyncMock()))
    monkeypatch.setattr(engine, 'sync_tradelocker_pretrade_positions',
                        AsyncMock(side_effect=RuntimeError('TradeLocker 429')))
    result = await engine._execute_signal_for_account_inner(db, dep, sig)
    assert result is None and sig.status == 'REJECTED'
    assert '429' in sig.rejection_reason
    db.rollback.assert_not_awaited()
