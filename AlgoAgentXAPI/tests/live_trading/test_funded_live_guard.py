from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.live_trading import (
    FundedRiskPlanUpdate,
    StrategyDeploymentCreate,
    StrategyDeploymentUpdate,
)
from app.services.live.funded_guard_service import (
    FundedLiveGuardDecision,
    _rule_clock,
    broker_funded_state,
    validate_risk_tiers,
)


def _tier(name, order, low, high, risk="0.01", active=True):
    return {
        "name": name,
        "sort_order": order,
        "min_account_return_pct": low,
        "max_account_return_pct": high,
        "risk_percent": risk,
        "is_active": active,
    }


def _deployment(rule_timezone="UTC", reset="00:00"):
    return SimpleNamespace(
        funded_profile_snapshot={"profile": {"account_size": "5000", "account_currency": "USD", "rules_json": {"rule_timezone": rule_timezone, "daily_reset_time": reset}}},
    )


def _broker(meta, *, updated_at=None, status="CONNECTED"):
    return SimpleNamespace(
        metadata_json=meta,
        last_connected_at=None,
        updated_at=updated_at or datetime.now(timezone.utc),
        status=status,
    )


def test_valid_dynamic_risk_ladder():
    rows = validate_risk_tiers([
        _tier("Defense", 1, None, "0" , "0.005"),
        _tier("Normal", 2, "0", "0.02", "0.01"),
        _tier("Growth", 3, "0.02", None, "0.0125"),
    ])
    assert [r["name"] for r in rows] == ["Defense", "Normal", "Growth"]


def test_dynamic_ladder_first_bound_must_be_open():
    with pytest.raises(ValueError, match="open lower bound"):
        validate_risk_tiers([_tier("A", 1, "-0.1", None)])


def test_dynamic_ladder_last_bound_must_be_open():
    with pytest.raises(ValueError, match="open upper bound"):
        validate_risk_tiers([_tier("A", 1, None, "0.1")])


def test_dynamic_ladder_rejects_gap():
    with pytest.raises(ValueError, match="no gaps or overlaps"):
        validate_risk_tiers([_tier("A", 1, None, "0"), _tier("B", 2, "0.01", None)])


def test_dynamic_ladder_rejects_overlap():
    with pytest.raises(ValueError, match="no gaps or overlaps"):
        validate_risk_tiers([_tier("A", 1, None, "0.02"), _tier("B", 2, "0.01", None)])


def test_dynamic_ladder_rejects_duplicate_sort_order():
    with pytest.raises(ValueError, match="unique"):
        validate_risk_tiers([_tier("A", 1, None, "0"), _tier("B", 1, "0", None)])


def test_dynamic_ladder_rejects_risk_over_system_cap():
    with pytest.raises(ValueError, match="<= 10%"):
        validate_risk_tiers([_tier("A", 1, None, None, "0.11")])


def test_rule_clock_uses_configured_reset_before_boundary():
    d = _deployment("UTC", "05:00")
    rule_date, tz, reset = _rule_clock(d, datetime(2026, 9, 3, 4, 59, tzinfo=timezone.utc))
    assert str(rule_date) == "2026-09-02"
    assert tz == "UTC"
    assert reset == "05:00"


def test_rule_clock_rolls_at_boundary():
    d = _deployment("UTC", "05:00")
    rule_date, _, _ = _rule_clock(d, datetime(2026, 9, 3, 5, 0, tzinfo=timezone.utc))
    assert str(rule_date) == "2026-09-03"


def test_rule_clock_is_not_frontend_ist_clock():
    d = _deployment("Asia/Kolkata", "00:00")
    rule_date, tz, _ = _rule_clock(d, datetime(2026, 9, 2, 19, 0, tzinfo=timezone.utc))
    assert str(rule_date) == "2026-09-03"
    assert tz == "Asia/Kolkata"


def test_rule_clock_rejects_invalid_timezone():
    with pytest.raises(ValueError, match="Invalid funded rule timezone"):
        _rule_clock(_deployment("Not/AZone"), datetime.now(timezone.utc))


def test_rule_clock_rejects_invalid_reset_time():
    with pytest.raises(ValueError, match="Invalid funded daily_reset_time"):
        _rule_clock(_deployment("UTC", "25:99"), datetime.now(timezone.utc))


def test_broker_state_reads_fresh_balance_equity_and_currency():
    now = datetime.now(timezone.utc)
    state = broker_funded_state(_broker({"last_test": {"balance": "5000", "equity": "4990", "free_margin": "4900", "currency": "usd", "synced_at": now.isoformat()}}))
    assert state["balance"] == Decimal("5000")
    assert state["equity"] == Decimal("4990")
    assert state["currency"] == "USD"
    assert state["fresh"] is True


def test_broker_state_marks_old_sync_stale():
    old = datetime.now(timezone.utc) - timedelta(minutes=10)
    state = broker_funded_state(_broker({"last_test": {"balance": "5000", "equity": "5000", "currency": "USD", "synced_at": old.isoformat()}}), max_age_seconds=120)
    assert state["fresh"] is False


def test_guard_decision_serializes_decimal_and_date():
    decision = FundedLiveGuardDecision(True, None, "READY", balance=Decimal("5000"), effective_risk_amount=Decimal("50"), rule_date=datetime(2026, 9, 3, tzinfo=timezone.utc).date())
    payload = decision.to_dict()
    assert payload["balance"] == "5000"
    assert payload["effective_risk_amount"] == "50"
    assert payload["rule_date"] == "2026-09-03"


def _create_payload(**overrides):
    payload = dict(
        strategy_id="strategy", name="Test", instrument="XAUUSD", timeframe="M5", mode="DEMO",
        broker_account_id=uuid4(), risk_per_trade=Decimal("0.01"), rr_ratio=Decimal("2"),
        price_risk_pct=Decimal("0.002"), max_daily_loss=Decimal("5000"), max_trades_per_day=10,
        max_open_positions=1, allow_short=True, auto_trade_enabled=False,
    )
    payload.update(overrides)
    return payload


def test_standard_deployment_schema_unchanged():
    row = StrategyDeploymentCreate(**_create_payload())
    assert row.account_policy_type == "STANDARD"


def test_funded_deployment_requires_profile():
    with pytest.raises(ValidationError):
        StrategyDeploymentCreate(**_create_payload(account_policy_type="FUNDED", funded_risk_mode="DYNAMIC"))


def test_funded_deployment_requires_risk_mode():
    with pytest.raises(ValidationError):
        StrategyDeploymentCreate(**_create_payload(account_policy_type="FUNDED", funded_profile_id=uuid4()))


def test_funded_fixed_risk_requires_positive_percentage():
    with pytest.raises(ValidationError):
        StrategyDeploymentCreate(**_create_payload(account_policy_type="FUNDED", funded_profile_id=uuid4(), funded_risk_mode="FIXED", funded_fixed_risk_pct=Decimal("0")))


def test_funded_safety_buffer_rejects_one_hundred_percent():
    with pytest.raises(ValidationError):
        StrategyDeploymentCreate(**_create_payload(account_policy_type="FUNDED", funded_profile_id=uuid4(), funded_risk_mode="DYNAMIC", funded_safety_buffer_pct=Decimal("1")))


def test_funded_configured_max_risk_rejects_zero():
    with pytest.raises(ValidationError):
        StrategyDeploymentCreate(**_create_payload(account_policy_type="FUNDED", funded_profile_id=uuid4(), funded_risk_mode="DYNAMIC", funded_configured_max_risk_pct=Decimal("0")))


def test_funded_configured_max_risk_rejects_over_ten_percent():
    with pytest.raises(ValidationError):
        StrategyDeploymentCreate(**_create_payload(account_policy_type="FUNDED", funded_profile_id=uuid4(), funded_risk_mode="DYNAMIC", funded_configured_max_risk_pct=Decimal("0.11")))


def test_risk_plan_fixed_validates():
    plan = FundedRiskPlanUpdate(risk_mode="fixed", fixed_risk_pct=Decimal("0.01"), safety_buffer_pct=Decimal("0.05"), risk_tiers=[])
    assert plan.risk_mode == "FIXED"


def test_risk_plan_dynamic_requires_active_tier():
    with pytest.raises(ValidationError):
        FundedRiskPlanUpdate(risk_mode="DYNAMIC", safety_buffer_pct=Decimal("0.05"), risk_tiers=[])


def test_risk_plan_tier_rejects_bad_range():
    with pytest.raises(ValidationError):
        FundedRiskPlanUpdate(risk_mode="DYNAMIC", safety_buffer_pct=Decimal("0.05"), risk_tiers=[{
            "name": "Bad", "sort_order": 1, "min_account_return_pct": Decimal("0.02"), "max_account_return_pct": Decimal("0.01"), "risk_percent": Decimal("0.01"), "is_active": True,
        }])


def test_strategy_deployment_update_normalizes_funded_enums():
    row = StrategyDeploymentUpdate(account_policy_type="funded", funded_risk_mode="fixed", funded_attach_mode="new_or_reset_account")
    assert row.account_policy_type == "FUNDED"
    assert row.funded_risk_mode == "FIXED"
    assert row.funded_attach_mode == "NEW_OR_RESET_ACCOUNT"


def test_broker_state_does_not_treat_generic_row_update_as_fresh():
    """Funded capital freshness must come from broker metrics/heartbeat, not DB edits."""
    state = broker_funded_state(_broker({"last_test": {"balance": "5000", "equity": "5000", "currency": "USD"}}, updated_at=datetime.now(timezone.utc)))
    assert state["fresh"] is False
    assert state["synced_at"] is None
