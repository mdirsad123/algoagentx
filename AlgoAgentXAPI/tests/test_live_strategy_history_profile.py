from app.services.live.strategy_history_profile import (
    resolve_live_strategy_profile,
    runtime_contract_violations,
)
from app.services.live.strategy_history_profile import settings as history_settings
from strategies.xauusd_5m_resistance_rejection_v3_5 import XAUUSD5MSupplyDemandRejectionV35CandidateA
from strategies.xauusd_5m_trend_breakout_v1_37 import XAUUSD5MTrendBreakoutV137


def test_strategy_specific_history_contracts():
    assert resolve_live_strategy_profile(XAUUSD5MTrendBreakoutV137, {}).required_history_bars == 20_000
    assert resolve_live_strategy_profile(XAUUSD5MSupplyDemandRejectionV35CandidateA, {}).required_history_bars == 2_000


def test_dynamic_source_daily_stack_infers_long_history():
    class DynamicStrategy:
        pass

    params = {"source_code": 'for label, freq, minutes in (("1d", "1d", 1440),):\n    x = "1d_atr14_50_ratio"'}
    assert resolve_live_strategy_profile(DynamicStrategy, params).required_history_bars == 20_000


def test_admin_history_override_is_supported_and_capped():
    assert resolve_live_strategy_profile(XAUUSD5MTrendBreakoutV137, {"live_history_bars": 25_000}).required_history_bars == 25_000
    assert resolve_live_strategy_profile(XAUUSD5MTrendBreakoutV137, {"live_history_bars": 999_999}).required_history_bars == 100_000


def test_no_name_based_runtime_contract_is_forced():
    cfg = {
        "execution": {"exit_on_opposite_signal": False, "max_open_positions": 3},
        "sl_tp": {"sl_mode": "FIXED_PERCENT", "rr_ratio": 3.0},
        "trade_management": {"partial_exit_enabled": False},
    }
    assert resolve_live_strategy_profile(XAUUSD5MTrendBreakoutV137, {}).runtime_contract is None
    assert runtime_contract_violations(XAUUSD5MTrendBreakoutV137, cfg, {}) == []


def test_temporary_history_override_is_operational_only(monkeypatch):
    monkeypatch.setattr(history_settings, "live_strategy_history_override_bars", 1000)
    assert resolve_live_strategy_profile(XAUUSD5MTrendBreakoutV137, {}).required_history_bars == 1000
    assert resolve_live_strategy_profile(XAUUSD5MSupplyDemandRejectionV35CandidateA, {}).required_history_bars == 1000

    monkeypatch.setattr(history_settings, "live_strategy_history_override_bars", 0)
    assert resolve_live_strategy_profile(XAUUSD5MTrendBreakoutV137, {}).required_history_bars == 20_000
    assert resolve_live_strategy_profile(XAUUSD5MSupplyDemandRejectionV35CandidateA, {}).required_history_bars == 2_000
