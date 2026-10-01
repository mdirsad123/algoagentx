import pandas as pd
import pytest

from engine.backtest_engine import BacktestParams, run_backtest_engine


class OneLongSignalStrategy:
    def __init__(self, df):
        self.df = df.copy()

    def generate(self):
        out = self.df.copy()
        out["Position"] = 0
        out["strategy_stop_loss"] = float("nan")
        out["strategy_target"] = float("nan")
        out.loc[0, "Position"] = 1
        out.loc[0, "strategy_stop_loss"] = 99.0
        return out


def test_engine_executes_90_percent_partial_at_1_7r_and_runner_at_2r():
    df = pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=4, freq="5min"),
            "Open": [100.0, 100.0, 100.4, 101.8],
            "High": [100.2, 100.5, 101.8, 102.1],
            "Low": [99.8, 99.5, 100.2, 101.5],
            "Close": [100.0, 100.4, 101.7, 102.0],
        }
    )
    params = BacktestParams(
        initial_capital=100000.0,
        rr_ratio=2.0,
        capital_risk_pct=0.01,
        use_strategy_sl_tp=True,
        runtime_config={
            "execution": {"exit_on_opposite_signal": False, "allow_long": True, "allow_short": True, "max_open_positions": 1},
            "trade_management": {
                "break_even_enabled": False,
                "trailing_enabled": False,
                "partial_exit_enabled": True,
                "partial_exit_at_r": 1.7,
                "partial_exit_percent": 0.9,
            },
        },
    )

    result = run_backtest_engine(df, OneLongSignalStrategy, backtest_params=params)

    assert result.total_trades == 1
    trade = result.trades[0]
    partials = [event for event in trade.lifecycle_events if event.get("event_type") == "PARTIAL_EXIT"]
    assert len(partials) == 1
    assert partials[0]["partial_exit_percent"] == pytest.approx(0.9)
    assert partials[0]["price"] == pytest.approx(101.7)
    assert trade.exit_price == pytest.approx(102.0)
    assert trade.pnl == pytest.approx(1730.0)
    assert result.final_capital == pytest.approx(101730.0)
