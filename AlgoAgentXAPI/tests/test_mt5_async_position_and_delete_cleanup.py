import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import sys
from types import SimpleNamespace
from types import ModuleType
from uuid import uuid4

# The lightweight CI image used for these unit tests does not include the Redis
# client package. The modules under test only need Redis type/module symbols at
# import time; no Redis call is exercised here.
if "redis.asyncio" not in sys.modules:
    redis_module = ModuleType("redis")
    redis_asyncio_module = ModuleType("redis.asyncio")
    redis_asyncio_module.Redis = object
    redis_asyncio_module.from_url = lambda *args, **kwargs: None
    redis_module.asyncio = redis_asyncio_module
    sys.modules["redis"] = redis_module
    sys.modules["redis.asyncio"] = redis_asyncio_module

from app.services.brokers.base import BrokerOrderResult
import app.services.live.execution_engine as execution_engine


class _ScalarOneOrNoneResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeExecutionDB:
    def __init__(self, broker):
        self.broker = broker
        self.added = []

    async def execute(self, statement):
        return _ScalarOneOrNoneResult(self.broker)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None


class _FakeAdapter:
    async def place_market_order(self, order_request):
        return BrokerOrderResult(
            success=True,
            status="PLACED",
            message="queued",
            broker_order_id="cmd-1",
            executed_price=None,
            raw_response={"execution_mode": "AGENT"},
        )


def test_async_mt5_queued_order_does_not_create_optimistic_open_position(monkeypatch):
    broker_id = uuid4()
    broker = SimpleNamespace(id=broker_id, status="CONNECTED")
    db = _FakeExecutionDB(broker)
    deployment = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        broker_account_id=broker_id,
        strategy_id="demo-strategy",
        broker_symbol="XAUUSD",
        mt5_demo_max_lot=None,
        _copy_execution_target=True,
        _copy_source_broker_code="CTRADER",
    )
    signal = SimpleNamespace(
        id=uuid4(),
        strategy_id="demo-strategy",
        signal_type="BUY",
        symbol="XAUUSD",
        candle_time=datetime.now(timezone.utc),
        status="RECEIVED",
        rejection_reason=None,
        trace_id=None,
    )

    opened = {"count": 0}

    async def _existing(*args, **kwargs):
        return None

    async def _log(*args, **kwargs):
        return None

    async def _open(*args, **kwargs):
        opened["count"] += 1

    monkeypatch.setattr(execution_engine, "_existing_order_for_client_id", _existing)
    monkeypatch.setattr(execution_engine, "get_broker_adapter", lambda broker, db: _FakeAdapter())
    monkeypatch.setattr(execution_engine, "_log", _log)
    monkeypatch.setattr(execution_engine, "open_position", _open)

    order = asyncio.run(execution_engine._execute_demo_entry(
        db,
        deployment,
        signal,
        "BUY",
        "LONG",
        Decimal("0.10"),
        Decimal("4280.00"),
        Decimal("4274.00"),
        Decimal("4292.00"),
    ))

    assert order.status == "PLACED"
    assert signal.status == "EXECUTED"
    assert opened["count"] == 0

