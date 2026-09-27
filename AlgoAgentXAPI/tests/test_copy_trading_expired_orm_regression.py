import asyncio
import sys
import types
from types import SimpleNamespace
from uuid import uuid4

if "redis.asyncio" not in sys.modules:
    redis_pkg = types.ModuleType("redis")
    redis_asyncio = types.ModuleType("redis.asyncio")
    redis_asyncio.Redis = object
    redis_asyncio.from_url = lambda *args, **kwargs: None
    redis_pkg.asyncio = redis_asyncio
    sys.modules.setdefault("redis", redis_pkg)
    sys.modules.setdefault("redis.asyncio", redis_asyncio)

from app.services.live import execution_engine


class _ExplodingDeployment:
    """Mimic an expired ORM object: only raw __dict__ access is safe."""
    def __init__(self, state):
        object.__setattr__(self, "__dict__", dict(state))

    def __getattribute__(self, name):
        if name in {"__dict__", "__class__"}:
            return object.__getattribute__(self, name)
        raise AssertionError(f"implicit ORM attribute access attempted: {name}")


class _Signal:
    def __init__(self, state):
        object.__setattr__(self, "__dict__", dict(state))


class _NoAutoflush:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _Nested:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _MappingsResult:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return self

    def one_or_none(self):
        return self.row


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDB:
    def __init__(self, dep_row, sig_row, primary_broker, copy_broker):
        self.no_autoflush = _NoAutoflush()
        self._responses = [
            _MappingsResult(dep_row),
            _MappingsResult(sig_row),
            _ScalarResult(primary_broker),
            _ScalarResult(copy_broker),
        ]

    async def execute(self, statement):
        assert self._responses, "unexpected DB query"
        return self._responses.pop(0)

    def begin_nested(self):
        return _Nested()


def test_copy_router_never_reads_expired_primary_orm_after_primary(monkeypatch):
    dep_id = uuid4()
    user_id = uuid4()
    primary_id = uuid4()
    copy_id = uuid4()
    sig_id = uuid4()

    dep_state = {
        "id": dep_id,
        "user_id": user_id,
        "broker_account_id": primary_id,
        "copy_trading_enabled": True,
        "copy_broker_account_ids": [copy_id],
        "account_policy_type": "STANDARD",
    }
    sig_state = {
        "id": sig_id,
        "status": "RECEIVED",
        "rejection_reason": None,
        "symbol": "XAUUSDm",
        "signal_type": "BUY",
    }
    deployment = _ExplodingDeployment(dep_state)
    signal = _Signal(sig_state)

    dep_row = {
        **dep_state,
        "instrument": "XAUUSDm",
        "broker_symbol": "XAUUSDm",
        "instrument_key": None,
        "mode": "DEMO",
    }
    sig_row = {**sig_state, "raw_payload": {}}
    broker_primary = SimpleNamespace(id=primary_id, mode="DEMO", status="CONNECTED")
    broker_copy = SimpleNamespace(id=copy_id, mode="DEMO", status="CONNECTED")
    db = _FakeDB(dep_row, sig_row, broker_primary, broker_copy)

    calls = []

    async def fake_executor(db_arg, dep_arg, sig_arg):
        calls.append(dep_arg)
        if dep_arg is deployment:
            sig_arg.status = "EXECUTED"
            return SimpleNamespace(id=uuid4(), status="FILLED")
        assert dep_arg.broker_account_id == copy_id
        return SimpleNamespace(id=uuid4(), status="FILLED")

    async def fake_log(*args, **kwargs):
        return None

    async def fake_canonical(*args, **kwargs):
        return "XAUUSD"

    monkeypatch.setattr(execution_engine.settings, "live_copy_trading_enabled", True)
    monkeypatch.setattr(execution_engine, "_execute_signal_for_account", fake_executor)
    monkeypatch.setattr(execution_engine, "_log", fake_log)
    monkeypatch.setattr(execution_engine, "_canonical_copy_symbol", fake_canonical)

    result = asyncio.run(execution_engine.execute_signal(db, deployment, signal))

    assert result.status == "FILLED"
    assert calls[0] is deployment
    assert calls[1].broker_account_id == copy_id
    assert signal.status == "EXECUTED"
