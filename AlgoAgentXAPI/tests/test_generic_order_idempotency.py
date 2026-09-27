import sys
import types

if "redis.asyncio" not in sys.modules:
    redis_pkg = types.ModuleType("redis")
    redis_asyncio = types.ModuleType("redis.asyncio")
    redis_asyncio.Redis = object
    redis_asyncio.from_url = lambda *args, **kwargs: None
    redis_pkg.asyncio = redis_asyncio
    sys.modules.setdefault("redis", redis_pkg)
    sys.modules.setdefault("redis.asyncio", redis_asyncio)

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.live.execution_engine import _client_order_id


def _signal(signal_id=None):
    return SimpleNamespace(
        id=signal_id or uuid4(),
        strategy_id=uuid4(),
        candle_time=datetime(2026, 9, 25, 14, 45, tzinfo=timezone.utc),
        signal_type="BUY",
    )


def test_generic_client_order_id_is_compact_account_scoped_and_retry_stable():
    strategy_id = uuid4()
    candle_time = datetime(2026, 9, 25, 14, 45, tzinfo=timezone.utc)
    deployment_id = uuid4()
    account_a = uuid4()
    account_b = uuid4()

    first_signal = SimpleNamespace(id=uuid4(), strategy_id=strategy_id, candle_time=candle_time, signal_type="BUY")
    retry_signal = SimpleNamespace(id=uuid4(), strategy_id=strategy_id, candle_time=candle_time, signal_type="BUY")

    dep_a = SimpleNamespace(id=deployment_id, broker_account_id=account_a, strategy_id=strategy_id)
    dep_b = SimpleNamespace(id=deployment_id, broker_account_id=account_b, strategy_id=strategy_id)

    first = _client_order_id(dep_a, first_signal, "ENTRY")
    retry = _client_order_id(dep_a, retry_signal, "ENTRY")
    other_account = _client_order_id(dep_b, first_signal, "ENTRY")
    exit_id = _client_order_id(dep_a, first_signal, "EXIT")

    assert first == retry
    assert first != other_account
    assert first != exit_id
    assert len(first) < 128
    assert len(first) <= 50
