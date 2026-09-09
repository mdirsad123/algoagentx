from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.services.billing import live_subscription_gate as gate


@pytest.mark.asyncio
async def test_funded_live_remains_subscriber_only_when_generic_live_gate_is_disabled(monkeypatch):
    monkeypatch.setattr(gate, "live_trading_requires_subscription", AsyncMock(return_value=False))
    monkeypatch.setattr(gate, "get_recommended_coupon_code", AsyncMock(return_value="HELLO"))
    monkeypatch.setattr(gate, "get_active_paid_subscription", AsyncMock(return_value=(None, None)))

    status = await gate.build_live_trading_access_status(object(), "user-1")

    assert status["allowed"] is True
    assert status["requires_subscription"] is False
    assert status["funded_live"]["allowed"] is False
    assert status["funded_live"]["requires_subscription"] is True
    assert status["funded_live"]["code"] == "FUNDED_LIVE_SUBSCRIPTION_REQUIRED"


@pytest.mark.asyncio
async def test_funded_live_allowed_with_active_paid_subscription(monkeypatch):
    sub = SimpleNamespace(id="sub-1", status="ACTIVE", end_at=None)
    plan = SimpleNamespace(code="PRO", billing_period="MONTHLY")
    monkeypatch.setattr(gate, "live_trading_requires_subscription", AsyncMock(return_value=True))
    monkeypatch.setattr(gate, "get_recommended_coupon_code", AsyncMock(return_value=None))
    monkeypatch.setattr(gate, "get_active_paid_subscription", AsyncMock(return_value=(sub, plan)))

    status = await gate.build_live_trading_access_status(object(), "user-1")

    assert status["allowed"] is True
    assert status["funded_live"]["allowed"] is True
    assert status["funded_live"]["subscription"]["plan_code"] == "PRO"


@pytest.mark.asyncio
async def test_funded_live_paid_gate_rejects_non_subscriber(monkeypatch):
    monkeypatch.setattr(gate, "get_active_paid_subscription", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(gate, "get_recommended_coupon_code", AsyncMock(return_value="HELLO"))

    with pytest.raises(HTTPException) as exc_info:
        await gate.require_active_paid_subscription_for_funded_live_trading(object(), "user-1")

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["code"] == "FUNDED_LIVE_SUBSCRIPTION_REQUIRED"
