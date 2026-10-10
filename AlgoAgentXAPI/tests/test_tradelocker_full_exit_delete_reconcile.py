"""Focused isolated tests for FULL_EXIT order history delete-time reconciliation."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from sqlalchemy import column, select, table

FILE = Path(__file__).resolve().parents[1] / "app/api/v1/live_deployments.py"
ORDER = table('live_orders', column('deployment_id'), column('broker_account_id'), column('action'), column('status'), column('broker_order_id'))

class Result:
    def __init__(self, ids): self.ids=ids
    def scalars(self): return self
    def all(self): return self.ids

class DB:
    def __init__(self, ids): self.ids=ids
    async def execute(self, q): return Result(self.ids)


def load_function(adapter, reconcile):
    tree=ast.parse(FILE.read_text())
    fn=next(x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='_reconcile_tradelocker_full_exit_orders_before_delete')
    ns={'AsyncSession':object,'StrategyDeployment':object,'BrokerAccount':object,'UUID':str,'LiveOrder':SimpleNamespace(**{c.name:c for c in ORDER.c}),
        'select':select,'_DELETE_UNCONFIRMED_ORDER_STATUSES':('PENDING','PLACED','SUBMITTED','ACCEPTED','PENDING_DEMO'),
        'get_broker_adapter':lambda broker,db:adapter, 'SimpleNamespace':SimpleNamespace}
    # The production import is inside the function; inject an equivalent
    # before compiling in this isolated namespace using a narrow AST edit.
    fn.body=[line for line in fn.body if not isinstance(line,ast.ImportFrom)]
    ns['reconcile_orders']=reconcile
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(FILE),'exec'),ns)
    return ns[fn.name]


def test_full_exit_checks_exact_account_order_ids_and_reconciles_final():
    adapter=SimpleNamespace(get_order_history=AsyncMock(return_value=[{'id':'o1','status':'Filled'}]))
    reconcile=AsyncMock(return_value={'orders_updated':1})
    fn=load_function(adapter,reconcile)
    dep=SimpleNamespace(id='dep-A')
    res=asyncio.run(fn(DB(['o1','o1','o2']),dep,'account-A',object()))
    assert res==1
    adapter.get_order_history.assert_awaited_once_with(['o1','o2'])
    args=reconcile.await_args.args
    assert args[1].id=='dep-A' and args[1].broker_account_id=='account-A'
    assert args[3]=='TRADELOCKER'


def test_missing_history_cannot_clear_unresolved_order():
    adapter=SimpleNamespace(get_order_history=AsyncMock(return_value=[]))
    reconcile=AsyncMock()
    fn=load_function(adapter,reconcile)
    assert asyncio.run(fn(DB(['o1']),SimpleNamespace(id='dep'),'acc',object()))==0
    reconcile.assert_not_awaited()


def test_missing_broker_id_cannot_auto_clear_order():
    adapter=SimpleNamespace(get_order_history=AsyncMock())
    reconcile=AsyncMock()
    fn=load_function(adapter,reconcile)
    assert asyncio.run(fn(DB([None,'']),SimpleNamespace(id='dep'),'acc',object()))==0
    adapter.get_order_history.assert_not_awaited()


def test_rate_limit_propagates_and_deletion_must_remain_blocked():
    adapter=SimpleNamespace(get_order_history=AsyncMock(side_effect=RuntimeError('429')))
    reconcile=AsyncMock()
    fn=load_function(adapter,reconcile)
    try: asyncio.run(fn(DB(['o1']),SimpleNamespace(id='dep'),'acc',object()))
    except RuntimeError as exc: assert '429' in str(exc)
    else: assert False,'Should not assume success when history is throttled'
    reconcile.assert_not_awaited()


def test_no_order_sync_on_invalid_history_shape():
    adapter=SimpleNamespace(get_order_history=AsyncMock(return_value={'unexpected':'shape'}))
    reconcile=AsyncMock()
    fn=load_function(adapter,reconcile)
    try: asyncio.run(fn(DB(['o1']),SimpleNamespace(id='dep'),'acc',object()))
    except RuntimeError as exc: assert 'unavailable' in str(exc)
    else: assert False
    reconcile.assert_not_awaited()
