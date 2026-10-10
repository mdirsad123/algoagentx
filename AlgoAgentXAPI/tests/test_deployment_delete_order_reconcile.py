"""Small dependency-isolated tests for the TradeLocker delete safety gate.

The API module imports optional Redis/JWT/MT5 dependencies not installed in
this offline runner, so compile its actual helper functions from source rather
than duplicating the code under test.
"""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from sqlalchemy import column, select, table, Column, String
from sqlalchemy.orm import declarative_base

FILE = Path(__file__).resolve().parents[1] / 'app/api/v1/live_deployments.py'
ORDER = table('live_orders', column('broker_account_id'), column('deployment_id'), column('status'))
Base = declarative_base()
class BrokerAccountModel(Base):
    __tablename__ = 'broker_accounts_for_test'
    id = Column(String, primary_key=True)



class _Result:
    def __init__(self, *, accounts=None, broker=None):
        self.accounts = accounts
        self.broker = broker

    def scalars(self):
        return self

    def all(self):
        return self.accounts

    def scalar_one_or_none(self):
        return self.broker


class _Savepoint:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DB:
    def __init__(self, accounts, brokers):
        self.accounts = accounts
        self.brokers = list(brokers)
        self.calls = 0

    async def execute(self, statement):
        self.calls += 1
        if self.calls == 1:
            return _Result(accounts=self.accounts)
        return _Result(broker=self.brokers.pop(0))

    def begin_nested(self):
        return _Savepoint()


async def _noop():
    return 0


def _load_helpers(sync, provider='TRADELOCKER'):
    tree = ast.parse(FILE.read_text())
    names = {'_refresh_unconfirmed_tradelocker_orders_before_delete', '_deletion_order_block_message'}
    functions = [n for n in tree.body if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name in names]
    assert len(functions) == 2
    namespace = {
        'AsyncSession': object,
        'StrategyDeployment': object,
        'SimpleNamespace': SimpleNamespace,
        'select': select,
        'LiveOrder': SimpleNamespace(**{c.name: c for c in ORDER.c}),
        'BrokerAccount': BrokerAccountModel,
        '_DELETE_UNCONFIRMED_ORDER_STATUSES': ('PENDING','PLACED','SUBMITTED','PENDING_DEMO','ACCEPTED'),
        'get_broker_code': lambda broker: broker.provider,
        'sync_copy_target_positions': sync,
        '_reconcile_tradelocker_full_exit_orders_before_delete': (lambda *args: _noop()),
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(FILE), 'exec'), namespace)
    return namespace


def _deployment(primary):
    return SimpleNamespace(id=uuid4(), user_id=uuid4(), broker_account_id=primary,
                           instrument='BTCUSD', broker_symbol='BTCUSD.X', instrument_key=None)


def test_primary_and_copy_accounts_are_reconciled_once():
    primary, copy = uuid4(), uuid4()
    calls = []

    async def sync(db, account_target):
        calls.append((account_target.id, account_target.broker_account_id))

    helper = _load_helpers(sync)['_refresh_unconfirmed_tradelocker_orders_before_delete']
    dep = _deployment(primary)
    db = _DB([primary, copy, copy], [SimpleNamespace(provider='TRADELOCKER')]*2)
    assert asyncio.run(helper(db, dep)) == []
    assert calls == [(dep.id, primary), (dep.id, copy)]


def test_null_account_id_falls_back_to_primary_and_failure_blocks_delete():
    primary = uuid4()

    async def sync(db, account_target):
        raise RuntimeError('429 Too Many Requests')

    helper = _load_helpers(sync)['_refresh_unconfirmed_tradelocker_orders_before_delete']
    errors = asyncio.run(helper(_DB([None], [SimpleNamespace(provider='TRADELOCKER')]), _deployment(primary)))
    assert len(errors) == 1 and '429' in errors[0]


def test_other_brokers_unchanged():
    acct = uuid4()
    calls = []

    async def sync(db, account_target):
        calls.append(True)

    helper = _load_helpers(sync)['_refresh_unconfirmed_tradelocker_orders_before_delete']
    errors = asyncio.run(helper(_DB([acct], [SimpleNamespace(provider='MT5')]), _deployment(acct)))
    assert errors == [] and calls == []


def test_uncertain_order_block_explains_statuses_and_broker_warning():
    msg = _load_helpers(lambda *_: None)['_deletion_order_block_message'](
        3, [('PLACED', 2), ('PENDING', 1)], ['account: rate limited'])
    assert 'PLACED: 2' in msg
    assert 'PENDING: 1' in msg
    assert 'rate limited' in msg
    assert 'zero open positions' in msg


def test_delete_route_preserves_safety_guard_and_rechecks_positions():
    tree = ast.parse(FILE.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'delete_deployment')
    src = ast.get_source_segment(FILE.read_text(), fn)
    assert src.index('_refresh_unconfirmed_tradelocker_orders_before_delete') < src.index('remaining_order_statuses')
    assert src.count('LivePosition.status == "OPEN"') == 2
    assert 'if active_orders_count:' in src
    assert 'await db.delete(row)' in src
