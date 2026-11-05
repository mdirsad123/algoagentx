"""Offline regression checks for this hotfix's pure logic.

Load the real definitions via AST because the full AlgoAgentX test environment
needs asyncpg, Celery, Redis and a running PostgreSQL/Redis broker stack.
These tests are not a substitute for DEMO integration acceptance.
"""
import ast
import asyncio
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
from types import SimpleNamespace
import time

import pytest

ROOT = Path(__file__).resolve().parents[1] / 'app'


def load_def(path, function, env, parent_class=None):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = tree.body
    if parent_class:
        nodes = next(node.body for node in nodes if isinstance(node, ast.ClassDef) and node.name == parent_class)
    node = next(node for node in nodes if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function)
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(module, str(path), 'exec'), env)
    return env[function]


def equity_rows():
    def timestamp(point, fallback):
        return point.get('timestamp') or fallback
    def ensure_aware(value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    env = dict(date=date, datetime=datetime, time=datetime.min.time, timedelta=timedelta,
               _equity_point_timestamp=timestamp, _ensure_aware_datetime=ensure_aware,
               _equity_point_value=lambda point: point)
    from datetime import time as dt_time
    env['time'] = dt_time
    return load_def(ROOT / 'api/v1/backtests.py', '_service_equity_rows', env)


def test_equity_duplicate_first_timestamp_keeps_latest_actual_value():
    start = datetime(2026, 10, 11, 21, 5, tzinfo=timezone.utc)
    service = SimpleNamespace(result=SimpleNamespace(
        equity_curve=[5000, 5040, 5060],
        equity_timestamps=[start, start, start + timedelta(minutes=5)]))
    rows = equity_rows()(service, date(2026, 10, 11))
    assert len(rows) == 2
    assert rows[0]['equity'] == 5040
    assert rows[1]['equity'] == 5060
    assert rows[0]['timestamp'] == start.isoformat()


def test_equity_missing_timestamps_uses_unique_fallbacks():
    service = SimpleNamespace(result=SimpleNamespace(equity_curve=[5000, 5010, 5020], equity_timestamps=[]))
    rows = equity_rows()(service, date(2026, 10, 11))
    assert len(rows) == len({x['timestamp'] for x in rows}) == 3


class RedisLease:
    def __init__(self):
        self.expires = {}
        self.values = {}
    async def set(self, key, value, *, nx=False, px=None, ex=None):
        now = time.monotonic()
        if nx and self.expires.get(key, 0) > now:
            return False
        self.values[key] = value
        self.expires[key] = now + (px / 1000 if px else ex or 3600)
        return True
    async def pttl(self, key):
        return max(-2, int((self.expires.get(key, 0) - time.monotonic()) * 1000))
    async def get(self, key):
        return self.values.get(key)


def throttle(redis):
    env = dict(os=os, time=time, asyncio=asyncio,
               redis_manager=SimpleNamespace(client=redis),
               _LOCAL_REQUEST_LOCKS={}, _LOCAL_REQUEST_SLOTS={},
               order_request_context=SimpleNamespace(get=lambda: None))
    fun = load_def(ROOT / 'services/brokers/tradelocker.py', '_pace_request', env, parent_class='TradeLockerAdapter')
    class Adapter:
        environment = 'demo'
        _pace_request = fun
        async def _yield_background(self): pass
        async def _cooldown(self): return 0
    return Adapter


def test_shared_pacing_across_independent_adapters(monkeypatch):
    monkeypatch.setenv('TRADELOCKER_SHARED_REQUEST_SPACING_MS', '110')
    Adapter = throttle(RedisLease())
    async def scenario():
        start = time.monotonic()
        await asyncio.gather(Adapter()._pace_request(time.time() + 3), Adapter()._pace_request(time.time() + 3))
        return time.monotonic() - start
    assert asyncio.run(scenario()) >= 0.10


def test_shared_pacing_does_not_outlive_deadline(monkeypatch):
    monkeypatch.setenv('TRADELOCKER_SHARED_REQUEST_SPACING_MS', '300')
    Adapter = throttle(RedisLease())
    async def scenario():
        await Adapter()._pace_request(time.time() + 1)
        with pytest.raises(RuntimeError, match='request budget'):
            await Adapter()._pace_request(time.time() + 0.01)
    asyncio.run(scenario())


def test_broker_metadata_reused_cross_instance(monkeypatch):
    class Account:
        _config_cache = None
        _instrument_cache = None
        _session_key = 'hash-credential-and-account'
        account_id = 'account-1'
        def _require_selected(self):
            return None
        async def _request(self, *args, **kwargs):
            raise AssertionError('Second instance should not refetch static broker metadata')
    cache = RedisLease()
    env = dict(redis_manager=SimpleNamespace(client=cache), json=json,
               time=time, _SESSION_CACHE={})
    config_func = load_def(ROOT / 'services/brokers/tradelocker.py', '_config', env, parent_class='TradeLockerAdapter')
    instruments_func = load_def(ROOT / 'services/brokers/tradelocker.py', '_instruments', env, parent_class='TradeLockerAdapter')
    Account._config = config_func
    Account._instruments = instruments_func
    cache.values['tradelocker:metadata:hash-credential-and-account:config'] = json.dumps({'positionsConfig': {'columns': ['id']}})
    cache.values['tradelocker:metadata:hash-credential-and-account:instruments'] = json.dumps([{'name': 'XAUUSD.X'}])
    async def scenario():
        inst = Account()
        assert (await inst._config())['positionsConfig']['columns'] == ['id']
        assert (await inst._instruments())[0]['name'] == 'XAUUSD.X'
    asyncio.run(scenario())
