"""Source-based regression tests for copy timing and bounded deferred fan-out.

These run without broker credentials, Redis/Postgres containers or asyncpg.
They do NOT replace integration tests against DEMO broker state.
"""
import ast
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1] / 'app/services/live/execution_engine.py'


def load(name, context):
    module = ast.parse(ROOT.read_text(encoding='utf-8'))
    node = next(n for n in module.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    compiled = compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(ROOT), 'exec')
    exec(compiled, context)
    return context[name]


def test_copy_entry_timing_anchored_to_confirmed_primary_not_candle():
    env = {'settings': SimpleNamespace(live_copy_max_age_after_primary_seconds=180)}
    deadline = load('_copy_execution_deadline', env)
    anchor = time.time()
    assert abs(deadline(anchor) - (anchor + 180)) < 0.001
    src = ROOT.read_text()
    assert "deadline = (_copy_execution_deadline(primary_completed_at)" in src
    assert "if time.time() >= copy_cutoff" not in src


class Column:
    def __init__(self, name=''):
        self.name = name
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __gt__(self, other): return self
    def in_(self, other): return self
    def is_not(self, other): return self
    def desc(self): return self


class Table:
    def __init__(self):
        self.id = Column('id')


class Model:
    __table__ = Table()
    def __getattr__(self, name): return Column(name)


class Query:
    def where(self, *args): return self
    def order_by(self, *args): return self
    def limit(self, *args): return self


class Response:
    def __init__(self, one=None, many=None): self.one_value, self.many = one, many
    def scalar_one_or_none(self): return self.one_value
    def scalars(self): return self
    def mappings(self): return self
    def all(self): return self.many or []
    def one_or_none(self): return self.one_value
    def one(self): return self.one_value


class DB:
    def __init__(self, response_list): self.responses = iter(response_list)
    async def execute(self, query): return next(self.responses)


class DBContext:
    def __init__(self, db): self.db = db
    async def __aenter__(self): return self.db
    async def __aexit__(self, *args): return False


def test_deferred_broker_confirmed_fill_fans_out_to_both_accounts_despite_slow_candle():
    depid, pid, sigid, aid, bid = [uuid4() for _ in range(5)]
    candle = datetime.now(timezone.utc) - timedelta(minutes=12)
    created = datetime.now(timezone.utc) - timedelta(seconds=7)
    source = SimpleNamespace(
        deployment_id=depid, broker_account_id=pid, signal_id=sigid,
        symbol='XAUUSD.X', status='FILLED', created_at=created,
        raw_response={'copy_dispatch_intent': {'version': 2, 'targets': [str(aid), str(bid)]}},
    )
    dep = SimpleNamespace(id=depid, status='RUNNING', auto_trade_enabled=True,
                          copy_trading_enabled=True, account_policy_type='STANDARD',
                          broker_account_id=pid)
    sig = {'id': sigid, 'candle_time': candle, 'signal_type': 'BUY', 'symbol': 'XAUUSD.X'}
    rows = [Response(dep), Response({'id': depid, 'user_id': uuid4(), 'timeframe': 'M5'}),
            Response(many=[source]), Response(SimpleNamespace(mode='DEMO')),
            Response(sig), Response(None),
            Response(many=[SimpleNamespace(side='LONG', symbol='XAUUSD.X')])]
    calls=[]
    async def canonical(*args): return 'XAUUSD'
    async def existing(*args): return None
    async def dispatch(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id=uuid4(), status='FILLED')
    setting = SimpleNamespace(live_copy_trading_enabled=True,
                              live_copy_fill_followup_seconds=600,
                              live_copy_max_concurrency=4)
    model = Model()
    environment = {
        'async_session': lambda: DBContext(DB(rows)),
        'StrategyDeployment': model, 'BrokerAccount': model,
        'LiveOrder': model, 'LiveSignal': model, 'LivePosition': model,
        'select': lambda *args: Query(), 'SimpleNamespace': SimpleNamespace,
        'get_broker_code': lambda *args: 'TRADELOCKER',
        '_canonical_symbol_fallback': lambda symbol: str(symbol).upper(),
        '_canonical_copy_symbol': canonical,
        '_existing_order_for_client_id': existing,
        '_client_order_id': lambda *args: 'unique',
        '_dispatch_copy_account': dispatch,
        'datetime': datetime, 'timezone': timezone, 'time': time,
        'asyncio': asyncio, 'settings': setting,
        '_trace_logger': SimpleNamespace(warning=lambda *args: None),
    }
    followup = load('dispatch_confirmed_copy_orders', environment)
    result = asyncio.run(followup(depid))
    assert result['submitted'] == 2
    assert {c['account_id'] for c in calls} == {aid, bid}
    assert all(c['signal_snapshot']['candle_time'] == candle for c in calls)
    assert all(c['primary_completed_at'] > created.timestamp() for c in calls)


def test_deferred_recovery_refuses_unmarked_historical_primary():
    depid, pid, sigid = [uuid4() for _ in range(3)]
    dep=SimpleNamespace(id=depid, status='RUNNING', auto_trade_enabled=True,
                        copy_trading_enabled=True, account_policy_type='STANDARD',broker_account_id=pid)
    candidate=SimpleNamespace(signal_id=sigid, raw_response={},status='FILLED')
    result_rows=[Response(dep),Response({'id':depid}),Response(many=[candidate]),Response(SimpleNamespace(mode='DEMO'))]
    model=Model()
    env={'async_session':lambda:DBContext(DB(result_rows)), 'StrategyDeployment':model,
         'BrokerAccount':model,'LiveOrder':model, 'select':lambda *args:Query(),
         'settings':SimpleNamespace(live_copy_trading_enabled=True,live_copy_fill_followup_seconds=600),
         'get_broker_code':lambda *args:'TRADELOCKER', 'datetime':datetime,'timezone':timezone}
    followup=load('dispatch_confirmed_copy_orders',env)
    result=asyncio.run(followup(depid))
    assert result == {'eligible':0,'submitted':0,'skipped':0,'errors':0}


def test_reconcile_worker_obeys_broker_cooldown_before_poll():
    path = ROOT.with_name('live_reconcile_worker.py')
    node = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'LiveReconcileWorker')
    fun = next(n for n in node.body if isinstance(n, ast.AsyncFunctionDef) and n.name == '_tradelocker_poll_due')
    module = ast.fix_missing_locations(ast.Module(body=[fun], type_ignores=[]))
    calls=[]
    class Redis:
        async def pttl(self, key):
            calls.append(('pttl', key))
            return 60000 if key == 'tradelocker:cooldown:demo' else -2
        async def set(self, *args, **kwargs):
            calls.append(('set', args[0]))
            return True
    ctx={'redis_manager': SimpleNamespace(client=Redis()), 'time':time}
    exec(compile(module, str(path),'exec'),ctx)
    worker=SimpleNamespace(_tl_next_poll={})
    assert asyncio.run(ctx['_tradelocker_poll_due'](worker,'account')) is False
    assert not any(op == 'set' for op,_ in calls)


def test_reconcile_background_sync_failure_records_account_backoff():
    path = ROOT.with_name('live_reconcile_worker.py')
    node = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'LiveReconcileWorker')
    fun = next(n for n in node.body if isinstance(n, ast.AsyncFunctionDef) and n.name == '_tradelocker_sync_failed')
    module = ast.fix_missing_locations(ast.Module(body=[fun], type_ignores=[]))
    calls=[]
    class Redis:
        async def set(self, key, value, *, ex): calls.append((key,ex))
    ctx={'redis_manager': SimpleNamespace(client=Redis()), 'time':time}
    exec(compile(module, str(path),'exec'),ctx)
    worker=SimpleNamespace(_tl_error_count={},_tl_next_poll={})
    asyncio.run(ctx['_tradelocker_sync_failed'](worker,'copy-account',RuntimeError('HTTP 429')))
    assert calls == [('tradelocker:background-backoff:copy-account',60)]


def test_only_provably_pre_submit_copy_reservations_can_be_reclaimed():
    env = {'LiveOrder': SimpleNamespace}
    reclaim = load('_safe_to_reclaim_copy_pre_submit',env)
    good = SimpleNamespace(status='SKIPPED', broker_order_id=None,
                           raw_response={'safe_pre_submit_retry': True})
    assert reclaim(good)
    assert not reclaim(SimpleNamespace(status='PENDING',broker_order_id=None,
                                      raw_response={'safe_pre_submit_retry': True}))
    assert not reclaim(SimpleNamespace(status='SKIPPED',broker_order_id='BRK-123',
                                      raw_response={'safe_pre_submit_retry': True}))
    assert not reclaim(SimpleNamespace(status='SKIPPED',broker_order_id=None,
                                      raw_response={'safe_pre_submit_retry': False}))
