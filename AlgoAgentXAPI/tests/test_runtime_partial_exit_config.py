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


def test_sl_tp_engine_accepts_1_7_rr_and_calculates_decimal_target():
    import pandas as pd
    from app.services.trading.sl_tp_engine import calculate_sl_tp

    df = pd.DataFrame({
        "Date": pd.date_range("2026-01-01", periods=2, freq="5min"),
        "Open": [100.0, 100.0], "High": [100.2, 100.2],
        "Low": [99.8, 99.8], "Close": [100.0, 100.0],
    })
    result = calculate_sl_tp(
        df=df, signal_index=0, entry_price=100.0, side="BUY",
        runtime_config={"sl_tp": {"rr_ratio": 1.7, "sl_mode": "STRATEGY_SUGGESTED"}},
        suggested_stop_loss=99.0, suggested_target=None,
    )
    assert result["status"] == "OK"
    assert result["rr_ratio"] == 1.7
    assert result["risk_points"] == 1.0
    assert result["target"] == 101.7
