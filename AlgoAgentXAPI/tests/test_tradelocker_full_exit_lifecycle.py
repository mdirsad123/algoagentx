"""No-network regression checks: TradeLocker FULL_EXIT audit/reconciliation.

These are not broker API integration tests. All broker responses are mocked.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.services.live import broker_sync_service as sync


class _Scalars:
    def __init__(self, ids): self.ids = ids
    def scalars(self): return self
    def all(self): return self.ids


class _DB:
    def __init__(self, ids): self.ids = ids; self.statements=[]
    async def execute(self, stmt):
        self.statements.append(stmt)
        return _Scalars(self.ids)


@pytest.fixture(autouse=True)
def _reset_cooldown():
    sync._tl_full_exit_last_check.clear()
    yield
    sync._tl_full_exit_last_check.clear()


@pytest.fixture
def deployment():
    return SimpleNamespace(id=uuid4(), broker_account_id=uuid4())


@pytest.mark.asyncio
async def test_confirmed_full_exit_only_and_scoped_sql(monkeypatch, deployment):
    db=_DB(['exit-1','exit-1','exit-2'])
    adapter=SimpleNamespace(get_order_history=AsyncMock(return_value=[
        {'id':'exit-1','status':'Filled'},
        {'id':'exit-2','status':'PLACED'},
        {'id':'other-account-order','status':'Filled'},
    ]))
    reconcile=AsyncMock(return_value={'orders_updated':1})
    monkeypatch.setattr(sync,'reconcile_orders',reconcile)
    res=await sync.reconcile_tradelocker_pending_full_exits(db, deployment, adapter=adapter)
    assert res['full_exit_unconfirmed']==2
    assert res['full_exit_orders_updated']==1
    adapter.get_order_history.assert_awaited_once_with(['exit-1','exit-2'])
    sent=reconcile.await_args.args
    assert sent[1].broker_account_id == deployment.broker_account_id
    assert [x['id'] for x in sent[2]] == ['exit-1']
    sql,params=str(db.statements[0].compile()),db.statements[0].compile().params
    assert 'broker_account_id' in sql and 'FULL_EXIT' in params.values()
    assert str(deployment.broker_account_id) in [str(v) for v in params.values()]


@pytest.mark.asyncio
async def test_no_history_never_guesses_filled(monkeypatch, deployment):
    db=_DB(['exit-1'])
    adapter=SimpleNamespace(get_order_history=AsyncMock(return_value=[]))
    reconcile=AsyncMock()
    monkeypatch.setattr(sync,'reconcile_orders',reconcile)
    res=await sync.reconcile_tradelocker_pending_full_exits(db, deployment, adapter=adapter)
    assert res['full_exit_orders_updated']==0
    reconcile.assert_not_awaited()


@pytest.mark.asyncio
async def test_rate_limit_is_cooldown_and_fail_closed(monkeypatch, deployment):
    db=_DB(['exit-1'])
    adapter=SimpleNamespace(get_order_history=AsyncMock(side_effect=RuntimeError('429')))
    reconcile=AsyncMock()
    monkeypatch.setattr(sync,'reconcile_orders',reconcile)
    with pytest.raises(RuntimeError,match='429'):
        await sync.reconcile_tradelocker_pending_full_exits(db, deployment, adapter=adapter)
    res=await sync.reconcile_tradelocker_pending_full_exits(db, deployment, adapter=adapter)
    assert res['full_exit_history_skipped']=='rate_limit_cooldown'
    adapter.get_order_history.assert_awaited_once()
    reconcile.assert_not_awaited()


@pytest.mark.asyncio
async def test_cooldown_is_separate_per_account(monkeypatch, deployment):
    db=_DB(['exit-1'])
    adapter=SimpleNamespace(get_order_history=AsyncMock(return_value=[{'id':'exit-1','status':'Cancelled'}]))
    reconcile=AsyncMock(return_value={'orders_updated':1})
    monkeypatch.setattr(sync,'reconcile_orders',reconcile)
    other=SimpleNamespace(id=deployment.id,broker_account_id=uuid4())
    a=await sync.reconcile_tradelocker_pending_full_exits(db, deployment,adapter=adapter)
    b=await sync.reconcile_tradelocker_pending_full_exits(db, other, adapter=adapter)
    assert a['full_exit_orders_updated']==1 and b['full_exit_orders_updated']==1
    assert adapter.get_order_history.await_count==2


@pytest.mark.asyncio
async def test_no_pending_ids_no_broker_call(deployment):
    adapter=SimpleNamespace(get_order_history=AsyncMock())
    res=await sync.reconcile_tradelocker_pending_full_exits(_DB([]),deployment,adapter=adapter)
    assert res['full_exit_unconfirmed']==0
    adapter.get_order_history.assert_not_awaited()


def test_background_worker_only_requests_exit_audit_for_tradelocker():
    from pathlib import Path
    worker=Path(__file__).resolve().parents[1]/'app/services/live/live_reconcile_worker.py'
    source=worker.read_text()
    assert 'reconcile_full_exits=(code == "TRADELOCKER")' in source
    service=Path(__file__).resolve().parents[1]/'app/services/live/broker_sync_service.py'
    content=service.read_text()
    assert 'reconcile_full_exits: bool = False' in content
    assert 'reconcile_tradelocker_pending_full_exits(' in content
