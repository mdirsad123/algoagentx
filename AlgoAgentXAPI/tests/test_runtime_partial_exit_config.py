from app.services.trading.runtime_config_service import validate_runtime_config


def test_partial_exit_90_percent_at_1_7r_is_valid():
    result = validate_runtime_config({
        "execution": {"exit_on_opposite_signal": False, "max_open_positions": 1},
        "sl_tp": {"rr_ratio": 2, "sl_mode": "STRATEGY_SUGGESTED"},
        "trade_management": {
            "break_even_enabled": False,
            "trailing_enabled": False,
            "partial_exit_enabled": True,
            "partial_exit_at_r": 1.7,
            "partial_exit_percent": 0.9,
        },
    })
    assert result["valid"] is True, result["errors"]
    assert result["config"]["trade_management"]["partial_exit_at_r"] == 1.7
    assert result["config"]["trade_management"]["partial_exit_percent"] == 0.9


def test_partial_exit_100_percent_is_rejected_as_not_partial():
    result = validate_runtime_config({
        "trade_management": {
            "partial_exit_enabled": True,
            "partial_exit_at_r": 1.7,
            "partial_exit_percent": 1.0,
        },
    })
    assert result["valid"] is False
    assert any("less than 100%" in message for message in result["errors"])
