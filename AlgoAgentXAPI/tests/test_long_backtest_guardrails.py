from app.services.trading.guardrails import validate_backtest_guardrails


def test_large_backtest_is_allowed_and_warned_instead_of_rejected():
    result = validate_backtest_guardrails(
        {"risk": {"risk_percent": 0.01}},
        {
            "symbol": "XAUUSD",
            "quantity_mode": "LOTS",
            "tick_size": 0.01,
            "tick_value_per_lot": 1.0,
            "lot_step": 0.01,
            "min_lot": 0.01,
            "account_currency": "USD",
        },
        capital=5000.0,
        candle_count=1_500_000,
    )

    assert result["valid"] is True
    assert result["errors"] == []
    assert any("Large dataset selected" in warning for warning in result["warnings"])
