"""No-network test for legacy runner independent heartbeat.

Run: python production_patch/test_independent_runner_heartbeat.py
Uses AST extraction so it can run without installed app/redis dependencies.
"""
import ast
import asyncio
import json
import logging
from pathlib import Path
import threading
import time
from datetime import datetime, timezone
from types import SimpleNamespace

WORKER = Path(__file__).resolve().parents[1] / 'AlgoAgentXAPI/app/services/live/live_legacy_runner_worker.py'
SERVICE = Path(__file__).resolve().parents[1] / 'AlgoAgentXAPI/app/services/live/auto_runner_service.py'

class FakeRedis:
    def __init__(self):
        self.messages = []
        self.closed = False
        self.lock = threading.Lock()

    def set(self, key, value, ex):
        with self.lock:
            self.messages.append((key, json.loads(value), ex))

    def close(self):
        self.closed = True


def load_defs():
    source = ast.parse(WORKER.read_text())
    names = {'_iso', 'RunnerMonitor', 'publish_heartbeat_forever'}
    nodes = [n for n in source.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    # The source uses type union annotations; provide names for evaluated hints.
    env = {'datetime': datetime, 'timezone': timezone, 'threading': threading,
           'json':json, 'settings':SimpleNamespace(live_worker_health_ttl_seconds=20),
           'redis_manager':SimpleNamespace(_get_redis_url=lambda: 'redis://fake'),
           'worker_identity':lambda r:r+'-unit-test', 'HEALTH_KEY_PREFIX':'live:worker_health:',
           'logger':logging.getLogger(__name__)}
    exec(compile(ast.Module(body=nodes, type_ignores=[]),str(WORKER),'exec'),env)
    return env


def test_heartbeat_survives_event_loop_stall():
    env = load_defs()
    fake = FakeRedis()
    monitor = env['RunnerMonitor']()
    stop = threading.Event()
    factory = lambda *args, **kwargs: fake
    pulse = threading.Thread(target=env['publish_heartbeat_forever'],
                             args=(stop, monitor),
                             kwargs={'interval_seconds':0.03,'redis_factory':factory})
    pulse.start()
    async def blocked_async_loop():
        monitor.observe_cycle('STARTED')
        # Represents synchronous generate() blocking the actual asyncio loop.
        time.sleep(.22)
        monitor.observe_cycle('FINISHED')
    asyncio.run(blocked_async_loop())
    time.sleep(.06)
    stop.set(); pulse.join(1)
    assert not pulse.is_alive()
    assert fake.closed
    assert len(fake.messages) >= 4, fake.messages
    assert all(k == 'live:worker_health:live_legacy_runner_worker' and ttl == 20
               for k, _, ttl in fake.messages)
    assert all(p['status']=='HEALTHY' for _,p,_ in fake.messages)
    assert any(p['phase']=='PROCESSING' for _,p,_ in fake.messages)
    assert fake.messages[-1][1]['phase']=='WAITING'
    print('PASS independent heartbeat survives 220ms asyncio blockage, processing + waiting observed')


def test_runner_observer_always_finishes():
    tree=ast.parse(SERVICE.read_text())
    func=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='auto_runner_loop')
    assert len(func.args.args)==1 and func.args.args[0].arg=='cycle_observer'
    assert any(isinstance(n,ast.Try) and any(isinstance(x,ast.Call) and getattr(x.func,'id',None)=='cycle_observer'
               for y in n.finalbody for x in ast.walk(y)) for n in ast.walk(func))
    print('PASS scheduler observer finally callback wired')


def test_default_order_guard_off():
    config=Path(__file__).resolve().parents[1]/'AlgoAgentXAPI/app/core/config.py'
    text=config.read_text()
    assert 'live_runner_stale_order_guard_enabled: bool = Field(default=False' in text
    assert 'live_incremental_enabled: bool = Field(default=False' in text
    print('PASS stale-order guard and unverified incremental mode remain OFF by default')

if __name__=='__main__':
    test_heartbeat_survives_event_loop_stall()
    test_runner_observer_always_finishes()
    test_default_order_guard_off()
