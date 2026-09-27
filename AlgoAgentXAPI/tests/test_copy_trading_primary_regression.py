import asyncio
import sys
import types
from types import SimpleNamespace

# The CI/container used for this focused regression test may not install Redis.
# execution_engine only needs the module import to succeed for these unit tests.
if "redis.asyncio" not in sys.modules:
    redis_pkg = types.ModuleType("redis")
    redis_asyncio = types.ModuleType("redis.asyncio")
    redis_asyncio.Redis = object
    redis_asyncio.from_url = lambda *args, **kwargs: None
    redis_pkg.asyncio = redis_asyncio
    sys.modules.setdefault("redis", redis_pkg)
    sys.modules.setdefault("redis.asyncio", redis_asyncio)

from app.services.live import execution_engine


class _Signal:
    status = "RECEIVED"
    rejection_reason = None


class _Deployment(SimpleNamespace):
    pass


def test_copy_disabled_bypasses_router_and_preserves_primary_object(monkeypatch):
    deployment = _Deployment(
        broker_account_id="primary",
        copy_trading_enabled=False,
        copy_broker_account_ids=["copy-a"],
        account_policy_type="STANDARD",
    )
    signal = _Signal()
    seen = {}

    async def fake_account_executor(db, received_deployment, received_signal):
        seen["deployment"] = received_deployment
        seen["signal"] = received_signal
        return "PRIMARY_ORDER"

    monkeypatch.setattr(execution_engine.settings, "live_copy_trading_enabled", True)
    monkeypatch.setattr(execution_engine, "_execute_signal_for_account", fake_account_executor)

    result = asyncio.run(execution_engine.execute_signal(object(), deployment, signal))

    assert result == "PRIMARY_ORDER"
    assert seen["deployment"] is deployment
    assert seen["signal"] is signal


def test_copy_enabled_without_targets_still_uses_primary_path(monkeypatch):
    deployment = _Deployment(
        broker_account_id="primary",
        copy_trading_enabled=True,
        copy_broker_account_ids=[],
        account_policy_type="STANDARD",
    )
    signal = _Signal()
    seen = {}

    async def fake_account_executor(db, received_deployment, received_signal):
        seen["deployment"] = received_deployment
        return "PRIMARY_ORDER"

    monkeypatch.setattr(execution_engine.settings, "live_copy_trading_enabled", True)
    monkeypatch.setattr(execution_engine, "_execute_signal_for_account", fake_account_executor)

    result = asyncio.run(execution_engine.execute_signal(object(), deployment, signal))

    assert result == "PRIMARY_ORDER"
    assert seen["deployment"] is deployment
