from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from app.services.funded_backtest import billing_service


@pytest.mark.asyncio
async def test_funded_credit_quote_uses_filtered_selected_candle_count(monkeypatch):
    market_df = pd.DataFrame({
        "Date": pd.date_range("2026-01-01", periods=100, freq="5min"),
        "Open": [1.0] * 100,
        "High": [1.0] * 100,
        "Low": [1.0] * 100,
        "Close": [1.0] * 100,
    })
    filtered_df = market_df.iloc[:40].copy()

    monkeypatch.setattr(
        billing_service.BacktestService,
        "_fetch_market_data",
        AsyncMock(return_value=market_df),
    )
    monkeypatch.setattr(
        billing_service,
        "apply_advanced_filters",
        lambda *args, **kwargs: (
            filtered_df,
            {
                "enabled": True,
                "total_candles_before_filter": 100,
                "total_candles_after_filter": 40,
                "candles_removed": 60,
                "warnings": [],
            },
        ),
    )

    calculate = AsyncMock(return_value={
        "credit_cost": 3,
        "total_cost": 3,
        "pricing_rule": "Default Backtest",
        "breakdown": {"candle_count": 40},
    })
    monkeypatch.setattr(
        billing_service.CreditCostService,
        "calculate_backtest_credit_cost",
        calculate,
    )
    monkeypatch.setattr(
        billing_service.CreditManagementService,
        "get_credit_capacity",
        AsyncMock(return_value={
            "included_balance": 5,
            "wallet_balance": 7,
            "total_available": 12,
            "subscription_state": "ACTIVE",
        }),
    )

    payload = SimpleNamespace(
        instrument_id=1,
        timeframe="5m",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        advanced_filters=SimpleNamespace(enabled=True),
    )
    instrument = SimpleNamespace(id=1, symbol="XAUUSD", market="FOREX")

    quote, returned_df = await billing_service.build_funded_credit_quote(
        object(), payload=payload, instrument=instrument, user_id="00000000-0000-0000-0000-000000000001"
    )

    assert len(returned_df) == 100
    assert quote["candles_before_filters"] == 100
    assert quote["billable_candles"] == 40
    assert quote["candles_removed"] == 60
    assert quote["credit_cost"] == 3
    assert quote["balances"]["total_available"] == 12
    assert quote["balances"]["balance_after_run"] == 9
    assert quote["has_enough_credits"] is True
    assert quote["can_run"] is True

    kwargs = calculate.await_args.kwargs
    assert kwargs["candle_count"] == 40
    assert kwargs["instrument_id"] == 1
    assert kwargs["timeframe"] == "5m"


@pytest.mark.asyncio
async def test_funded_credit_quote_blocks_when_credits_are_insufficient(monkeypatch):
    market_df = pd.DataFrame({
        "Date": pd.date_range("2026-01-01", periods=25, freq="5min"),
        "Open": [1.0] * 25,
        "High": [1.0] * 25,
        "Low": [1.0] * 25,
        "Close": [1.0] * 25,
    })
    monkeypatch.setattr(billing_service.BacktestService, "_fetch_market_data", AsyncMock(return_value=market_df))
    monkeypatch.setattr(
        billing_service,
        "apply_advanced_filters",
        lambda df, *args, **kwargs: (
            df,
            {
                "enabled": False,
                "total_candles_before_filter": 25,
                "total_candles_after_filter": 25,
                "candles_removed": 0,
                "warnings": [],
            },
        ),
    )
    monkeypatch.setattr(
        billing_service.CreditCostService,
        "calculate_backtest_credit_cost",
        AsyncMock(return_value={"credit_cost": 8, "total_cost": 8, "breakdown": {"candle_count": 25}}),
    )
    monkeypatch.setattr(
        billing_service.CreditManagementService,
        "get_credit_capacity",
        AsyncMock(return_value={"included_balance": 2, "wallet_balance": 3, "total_available": 5, "subscription_state": "ACTIVE"}),
    )

    payload = SimpleNamespace(
        instrument_id=1,
        timeframe="5m",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        advanced_filters=SimpleNamespace(enabled=False),
    )
    instrument = SimpleNamespace(id=1, symbol="XAUUSD", market="FOREX")

    quote, _ = await billing_service.build_funded_credit_quote(
        object(), payload=payload, instrument=instrument, user_id="00000000-0000-0000-0000-000000000001"
    )

    assert quote["credit_cost"] == 8
    assert quote["has_enough_credits"] is False
    assert quote["can_run"] is False
    assert quote["balances"]["balance_after_run"] == 5
