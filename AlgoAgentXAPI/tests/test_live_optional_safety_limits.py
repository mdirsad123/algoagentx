import asyncio
import os
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.live_trading import StrategyDeploymentCreate
from app.services.brokers.mt5 import MT5Adapter
import app.services.live.risk_manager as risk_manager


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


class _FakeDB:
    def __init__(self, values):
        self.values = list(values)
        self.added = []

    async def execute(self, statement):
        return _ScalarResult(self.values.pop(0))

    def add(self, value):
        self.added.append(value)


class _FakeMT5:
    @staticmethod
    def symbol_info(symbol):
        return {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}


def test_new_deployment_daily_limits_default_to_none():
    payload = StrategyDeploymentCreate(
        strategy_id="demo-strategy",
        name="Demo",
        instrument="XAUUSD",
        timeframe="M5",
        broker_account_id=uuid4(),
    )
    assert payload.max_daily_loss is None
    assert payload.max_trades_per_day is None
    assert payload.mt5_demo_max_lot is None


def test_standard_none_limits_do_not_block_valid_signal(monkeypatch):
    deployment = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), broker_account_id=uuid4(),
        account_policy_type="STANDARD", status="RUNNING", auto_trade_enabled=True,
        mode="DEMO", allow_short=True, max_daily_loss=None,
        max_trades_per_day=None, max_open_positions=1,
    )
    signal = SimpleNamespace(
        id=uuid4(), signal_type="BUY", price=Decimal("4300"),
        candle_time=None,
    )
    db = _FakeDB([999, Decimal("-999999"), None])

    async def _no_positions(*args, **kwargs):
        return []

    monkeypatch.setattr(risk_manager, "get_open_positions", _no_positions)
    result = asyncio.run(risk_manager.validate_signal_for_execution(db, deployment, signal))
    assert result.allowed is True
    assert result.action == "OPEN"


def test_mt5_none_cap_uses_native_broker_max_not_env_cap(monkeypatch):
    monkeypatch.setenv("MT5_DEMO_MAX_LOT", "0.01")
    broker = SimpleNamespace(metadata_json={}, server_name=None, login_id=None, encrypted_password=None, encrypted_token=None)
    adapter = MT5Adapter(broker)
    adapter.mt5 = _FakeMT5()

    normalized, debug = adapter._normalize_market_volume("XAUUSD", Decimal("5.00"), max_lot=None, apply_demo_cap=True)
    assert normalized == Decimal("5")
    assert debug["effective_max"] == "100.0"

    capped, capped_debug = adapter._normalize_market_volume("XAUUSD", Decimal("5.00"), max_lot=Decimal("1.00"), apply_demo_cap=True)
    assert capped == Decimal("1")
    assert capped_debug["effective_max"] == "1.00"
