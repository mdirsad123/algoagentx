from copy import deepcopy
from decimal import Decimal

import pytest

from app.schemas.funded_backtests import FundedProfileCreate
from app.services.funded_backtest.consistency import consistency_percentage
from app.services.funded_backtest.risk_policy import apply_effective_risk_guard, resolve_dynamic_risk
from app.services.funded_backtest.rule_engine import qualifying_profit_threshold, start_of_day_balance_floor, static_initial_balance_floor
from app.services.funded_backtest.snapshots import build_profile_snapshot


def tiers():
    return [
        {"id": "1", "name": "Recovery 1", "sort_order": 1, "min_account_return_pct": None, "max_account_return_pct": Decimal("-0.04"), "risk_percent": Decimal("0.0025"), "is_active": True},
        {"id": "2", "name": "Recovery 2", "sort_order": 2, "min_account_return_pct": Decimal("-0.04"), "max_account_return_pct": Decimal("-0.02"), "risk_percent": Decimal("0.005"), "is_active": True},
        {"id": "3", "name": "Base", "sort_order": 3, "min_account_return_pct": Decimal("-0.02"), "max_account_return_pct": Decimal("0.02"), "risk_percent": Decimal("0.01"), "is_active": True},
        {"id": "4", "name": "Growth", "sort_order": 4, "min_account_return_pct": Decimal("0.02"), "max_account_return_pct": Decimal("0.04"), "risk_percent": Decimal("0.015"), "is_active": True},
        {"id": "5", "name": "High", "sort_order": 5, "min_account_return_pct": Decimal("0.04"), "max_account_return_pct": None, "risk_percent": Decimal("0.02"), "is_active": True},
    ]


def test_a_static_max_dd_floor():
    assert static_initial_balance_floor(5000, Decimal("0.10")) == Decimal("4500.00")


def test_b_start_of_day_daily_floor():
    assert start_of_day_balance_floor(5200, Decimal("0.05")) == Decimal("4940.00")


def test_c_qualifying_threshold():
    assert qualifying_profit_threshold(5000, Decimal("0.005")) == Decimal("25.000")


def test_d_consistency():
    pct = consistency_percentage(120, 500)
    assert pct == Decimal("0.24")
    assert pct > Decimal("0.15")


@pytest.mark.parametrize("balance,expected", [(4750,"0.0025"),(4850,"0.005"),(5000,"0.01"),(5150,"0.015"),(5250,"0.02")])
def test_e_dynamic_risk(balance, expected):
    assert resolve_dynamic_risk(5000, balance, tiers()).requested_risk_percentage == Decimal(expected)


def test_f_guard_reduces_risk_near_daily_boundary():
    decision = apply_effective_risk_guard(current_balance=5000, requested_risk_percentage=Decimal("0.01"), remaining_daily_capacity=20, remaining_max_capacity=200, safety_buffer_percentage=Decimal("0.05"))
    assert decision.effective_risk_amount == Decimal("19.00")
    assert decision.effective_risk_percentage < Decimal("0.01")
    assert decision.limiting_rule == "DAILY_DD"


def test_g_snapshot_is_immutable_copy():
    profile = {"name": "Original", "account_size": Decimal("5000")}
    phase = {"phase_number": 1, "profit_target_pct": Decimal("0.08")}
    risk = tiers()
    snapshot = build_profile_snapshot(profile, [phase], risk)
    profile["name"] = "Changed"
    phase["profit_target_pct"] = Decimal("0.99")
    risk[0]["risk_percent"] = Decimal("0.09")
    assert snapshot["profile"]["name"] == "Original"
    assert snapshot["phases"][0]["profit_target_pct"] == "0.08"
    assert snapshot["risk_tiers"][0]["risk_percent"] == "0.0025"


def test_profile_validation_rejects_overlapping_tiers():
    payload = {
        "name":"Bad", "challenge_type":"ONE_STEP", "account_size":"5000",
        "phases":[{"phase_number":1,"phase_name":"P1","profit_target_pct":"0.08","daily_drawdown_pct":"0.05","daily_drawdown_mode":"STATIC_INITIAL_BALANCE","max_drawdown_pct":"0.10","max_drawdown_mode":"STATIC_INITIAL_BALANCE","sequence":1}],
        "risk_tiers":[
            {"name":"A","sort_order":1,"min_account_return_pct":None,"max_account_return_pct":"0.01","risk_percent":"0.01"},
            {"name":"B","sort_order":2,"min_account_return_pct":"0.00","max_account_return_pct":None,"risk_percent":"0.01"},
        ]
    }
    with pytest.raises(ValueError, match="overlap"):
        FundedProfileCreate.model_validate(payload)


def test_h_user_a_cannot_access_user_b_resource():
    from app.services.funded_backtest.ownership import can_access_funded_resource
    assert can_access_funded_resource(owner_user_id="user-b", requesting_user_id="user-a") is False
    assert can_access_funded_resource(owner_user_id="user-b", requesting_user_id="user-a", is_template=True) is True
    assert can_access_funded_resource(owner_user_id="user-b", requesting_user_id="user-a", is_template=True, write=True) is False


def test_static_initial_daily_dd_uses_fixed_allowance_but_resets_each_day():
    from app.services.funded_backtest.rule_engine import calculate_daily_floor
    # $5K account, 5% daily DD => fixed $250 daily allowance.
    # If a later day starts at $4,900, that day's floor is $4,650.
    assert calculate_daily_floor(
        "STATIC_INITIAL_BALANCE",
        initial_balance="5000",
        start_balance="4900",
        start_equity="4900",
        drawdown_pct="0.05",
    ) == Decimal("4650.00")


def test_legacy_outer_edge_risk_tier_falls_back_to_first_tier():
    legacy = [
        {"id": "1", "name": "Deep Defensive", "sort_order": 1, "min_account_return_pct": Decimal("-0.06"), "max_account_return_pct": Decimal("-0.04"), "risk_percent": Decimal("0.0025"), "is_active": True},
        {"id": "2", "name": "Defensive", "sort_order": 2, "min_account_return_pct": Decimal("-0.04"), "max_account_return_pct": Decimal("-0.02"), "risk_percent": Decimal("0.005"), "is_active": True},
        {"id": "3", "name": "Normal", "sort_order": 3, "min_account_return_pct": Decimal("-0.02"), "max_account_return_pct": Decimal("0.02"), "risk_percent": Decimal("0.01"), "is_active": True},
        {"id": "4", "name": "Growth", "sort_order": 4, "min_account_return_pct": Decimal("0.02"), "max_account_return_pct": Decimal("0.04"), "risk_percent": Decimal("0.015"), "is_active": True},
        {"id": "5", "name": "Aggressive", "sort_order": 5, "min_account_return_pct": Decimal("0.04"), "max_account_return_pct": None, "risk_percent": Decimal("0.02"), "is_active": True},
    ]
    decision = resolve_dynamic_risk(Decimal("5000"), Decimal("4693.17"), legacy)
    assert decision.requested_risk_percentage == Decimal("0.0025")
    assert decision.selected_tier_name == "Deep Defensive"
    assert "open-ended fallback" in decision.reason


def test_profile_requires_open_ended_outer_risk_tiers():
    from app.schemas.funded_backtests import FundedProfileCreate
    import pytest
    payload = {
        "name": "Bad outer coverage", "challenge_type": "ONE_STEP", "account_size": "5000", "account_currency": "USD",
        "phases": [{"phase_number":1,"phase_name":"Phase 1","profit_target_pct":"0.08","daily_drawdown_pct":"0.05","daily_drawdown_mode":"STATIC_INITIAL_BALANCE","max_drawdown_pct":"0.10","max_drawdown_mode":"STATIC_INITIAL_BALANCE","minimum_trading_days":0,"qualifying_day_mode":"ANY_TRADE_DAY","profit_target_required":True,"reset_balance_after_pass":False,"sequence":1}],
        "risk_tiers": [{"name":"Finite first","sort_order":1,"min_account_return_pct":"-0.06","max_account_return_pct":None,"risk_percent":"0.0025","is_active":True}],
    }
    with pytest.raises(ValueError, match="open lower bound"):
        FundedProfileCreate.model_validate(payload)
