from app.services.live.strategy_history_profile import resolve_live_strategy_profile, runtime_contract_violations


class XAUUSD5MTrendBreakoutV137:
    pass


class ExplicitContractStrategy:
    LIVE_RUNTIME_CONTRACT = {"execution.exit_on_opposite_signal": False}


def test_generic_strategy_uses_platform_default_without_name_based_history_forcing():
    profile = resolve_live_strategy_profile(XAUUSD5MTrendBreakoutV137, {})
    assert profile.required_history_bars == 2000
    assert profile.runtime_contract is None


def test_generic_strategy_settings_are_not_rejected_by_name():
    cfg = {
        "execution": {"entry_mode": "NEXT_CANDLE_OPEN", "exit_on_opposite_signal": False, "max_open_positions": 2},
        "sl_tp": {"sl_mode": "FIXED_PERCENT", "rr_ratio": 3.0},
        "trade_management": {"partial_exit_enabled": False, "partial_exit_at_r": 1.0, "partial_exit_percent": 0.5},
    }
    assert runtime_contract_violations(XAUUSD5MTrendBreakoutV137, cfg, {}) == []


def test_explicit_strategy_authored_contract_is_still_supported():
    good = {"execution": {"exit_on_opposite_signal": False}}
    bad = {"execution": {"exit_on_opposite_signal": True}}
    assert runtime_contract_violations(ExplicitContractStrategy, good, {}) == []
    issues = runtime_contract_violations(ExplicitContractStrategy, bad, {})
    assert issues and issues[0]["path"] == "execution.exit_on_opposite_signal"
