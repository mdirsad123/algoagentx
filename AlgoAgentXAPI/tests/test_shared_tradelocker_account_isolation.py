"""No-network regression checks for shared-account NAS100/GOLD copy isolation.

Run: python -m pytest AlgoAgentXAPI/tests/test_shared_tradelocker_account_isolation.py -q
Does not connect to a broker, database, or Redis; never sends orders.
"""
import ast
import asyncio
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def extract(relative, *names, context):
    source = (ROOT / relative).read_text()
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    assert len(nodes) == len(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(relative), 'exec'), context)
    return context


def test_shared_account_symbol_filter():
    context = extract('app/services/live/broker_sync_service.py', '_symbol_key', '_symbols_match',
                      '_tradelocker_position_matches_deployment', context={'StrategyDeployment': object})
    matches = context['_tradelocker_position_matches_deployment']
    nas100 = SimpleNamespace(broker_symbol='NAS100.X', instrument='NAS100')
    gold = SimpleNamespace(broker_symbol='XAUUSD.X', instrument='XAUUSD')
    assert matches(nas100, 'NAS100.X')
    assert not matches(nas100, 'XAUUSD.X')
    assert matches(gold, 'XAUUSD.X')
    assert matches(gold, 'XAUUSD')
    assert not matches(gold, 'NAS100.X')
    assert not matches(SimpleNamespace(broker_symbol='NAS100.X', instrument='XAUUSD'), 'XAUUSD.X')
    assert matches(SimpleNamespace(broker_symbol=None, instrument='XAUUSD'), 'XAUUSD.X')
    assert not matches(SimpleNamespace(broker_symbol=None, instrument=None), 'XAUUSD.X')


def test_shared_account_copy_pending_conflict_rules():
    context = extract('app/services/live/execution_engine.py', '_symbol_compact',
                      '_copy_pending_entry_conflicts', context={})
    blocks = context['_copy_pending_entry_conflicts']
    gold_id, nas_id = uuid4(), uuid4()
    pending_nas = [SimpleNamespace(deployment_id=nas_id, symbol='NAS100.X')]
    pending_gold = [SimpleNamespace(deployment_id=gold_id, symbol='XAUUSD.X')]
    assert not blocks(pending_nas, gold_id, 'XAUUSD')
    assert blocks(pending_gold, gold_id, 'XAUUSD')
    assert blocks(pending_nas, nas_id, 'XAUUSD')  # Same deployment always blocks
    assert blocks(pending_gold, nas_id, 'XAUUSD')  # Same market, other deployment blocks
    assert blocks([SimpleNamespace(deployment_id=nas_id, symbol=None)], gold_id, 'XAUUSD')
    assert blocks(pending_nas, gold_id, None)  # Unknown symbol fails closed
    assert not blocks([], gold_id, None)


class Column:
    def __eq__(self, other): return True
    def __ne__(self, other): return True
    def in_(self, other): return True
    def notin_(self, other): return True


class DummyStatement:
    def where(self, *args): return self
    def limit(self, *args): return self


def dummy_select(*args): return DummyStatement()


class Position:
    id = deployment_id = broker_account_id = broker_position_id = status = live_position_id = partial_status = Column()
    def __init__(self, **kwargs):
        self.id = uuid4()
        self.__dict__.update(kwargs)


class DB:
    def __init__(self, foreign_owner=False):
        self.created = []
        self.foreign_owner = foreign_owner
        self.calls = 0
    async def execute(self, statement):
        self.calls += 1
        if self.calls == 1:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
        return SimpleNamespace(scalar_one_or_none=lambda: uuid4() if self.foreign_owner else None)
    def add(self, entity): self.created.append(entity)
    async def flush(self): pass


def context_for_reconcile():
    context = dict(Decimal=Decimal, Any=Any, StrategyDeployment=object, AsyncSession=object, select=dummy_select, LivePosition=Position,
                   LivePositionManagementState=Position, datetime=__import__('datetime').datetime,
                   timezone=__import__('datetime').timezone, UUID=__import__('uuid').UUID,
                   _write_log=None)
    extract('app/services/live/broker_sync_service.py', '_symbol_key', '_symbols_match',
            '_dec', '_tradelocker_position_values', '_tradelocker_position_matches_deployment',
            'reconcile_positions', context=context)
    async def noop(*args, **kwargs): return None
    context['_save_event'] = noop
    context['_write_log'] = noop
    return context


def gold_broker_position():
    return {'id': 'broker-pos-991', 'symbol': 'XAUUSD.X', 'side': 'SELL', 'qty': '0.06',
            'avgPrice': '3780.90', 'openDate': '1794990000000', 'unrealizedPl': '0',
            'protection': {'stop_loss': '3788.20', 'target': '3766.54'}}


def test_nas100_sync_never_creates_gold_position():
    context = context_for_reconcile()
    nas = SimpleNamespace(id=uuid4(), user_id=uuid4(), broker_account_id=uuid4(),
                          broker_symbol='NAS100.X', instrument='NAS100')
    db = DB()
    result = asyncio.run(context['reconcile_positions'](db, nas, [gold_broker_position()], 'TRADELOCKER'))
    assert result['positions_created'] == 0
    assert result['positions_unrelated_skipped'] == 1
    assert result['open_positions_count'] == 0
    assert db.created == []


def test_gold_copy_creates_gold_position_once():
    context = context_for_reconcile()
    gold = SimpleNamespace(id=uuid4(), user_id=uuid4(), broker_account_id=uuid4(),
                           broker_symbol='XAUUSD.X', instrument='XAUUSD')
    db = DB()
    result = asyncio.run(context['reconcile_positions'](db, gold, [gold_broker_position()], 'TRADELOCKER'))
    assert result['positions_created'] == 1
    assert db.created[0].deployment_id == gold.id
    assert db.created[0].broker_position_id == 'broker-pos-991'
    assert db.created[0].symbol == 'XAUUSD.X'


def test_same_broker_position_open_under_other_deployment_not_duplicated():
    context = context_for_reconcile()
    gold = SimpleNamespace(id=uuid4(), user_id=uuid4(), broker_account_id=uuid4(),
                           broker_symbol='XAUUSD.X', instrument='XAUUSD')
    db = DB(foreign_owner=True)
    result = asyncio.run(context['reconcile_positions'](db, gold, [gold_broker_position()], 'TRADELOCKER'))
    assert result['positions_created'] == 0
    assert result['positions_foreign_owner_conflicts'] == 1
    assert db.created == []
