"""Pure engine regression tests: no database/broker access required.

Run: cd AlgoAgentXAPI && python -m pytest tests/test_backtest_warmup_window.py -q
"""
from datetime import date

import pandas as pd
import pytest

from engine.backtest_engine import BacktestParams, run_backtest_engine


class ExampleStatefulStrategy:
    """Signals depend on preceding rows; no indicator lookahead."""
    def __init__(self, df, **kwargs):
        self.df = df

    def generate(self):
        df = self.df.copy()
        df["Position"] = 0
        df["strategy_stop_loss"] = float("nan")
        df["strategy_target"] = float("nan")
        # LONG executed Sep 30, remains open on Oct 1, exits Oct 2.
        df.loc[df.Date == pd.Timestamp("2026-09-29"), ["Position", "strategy_stop_loss", "strategy_target"]] = [1, 90.0, 120.0]
        # SHORT executed Oct 3 after prior warmup LONG has closed.
        df.loc[df.Date == pd.Timestamp("2026-10-02"), ["Position", "strategy_stop_loss", "strategy_target"]] = [-1, 105.0, 90.0]
        return df


@pytest.fixture
def candles():
    dates = pd.to_datetime([
        "2026-09-28", "2026-09-29", "2026-09-30",
        "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
    ])
    rows = [
        (100, 103, 97, 100),
        (100, 103, 97, 100),
        (100, 103, 97, 100),
        (100, 103, 97, 100),
        (100, 121, 96, 100),  # close warmup LONG via TP, not reported
        (100, 101, 98, 100),  # entry SHORT
        (100, 101, 88, 90),  # short TP
    ]
    return pd.DataFrame(
        {"Date": dates, "Open": [r[0] for r in rows],
         "High": [r[1] for r in rows], "Low": [r[2] for r in rows],
         "Close": [r[3] for r in rows]},
    )


def test_warmup_reconstructs_position_but_excludes_warmup_pnl(candles):
    params = BacktestParams(
        initial_capital=5000.0, capital_risk_pct=0.01,
        use_strategy_sl_tp=True, report_start_date=date(2026, 10, 1),
        runtime_config={"execution": {"exit_on_opposite_signal": False}},
    )
    result = run_backtest_engine(candles, ExampleStatefulStrategy, backtest_params=params)
    assert result.total_trades == 1
    assert result.trades[0].direction == "SHORT"
    assert result.trades[0].entry_datetime == pd.Timestamp("2026-10-03")
    assert result.trades[0].exit_datetime == pd.Timestamp("2026-10-04")
    assert result.win_rate == 1.0
    assert result.trades[0].pnl == pytest.approx(100.0)
    assert result.final_capital == pytest.approx(5100.0)
    assert result.total_return == pytest.approx(0.02)
    assert result.summary["carry_in_position_excluded"] is True
    assert all(pd.Timestamp(ts).date() >= date(2026, 10, 1) for ts in result.equity_timestamps)
    assert result.summary["forced_end_of_backtest_exits"] == 0


def test_legacy_full_replay_still_counts_all_trades(candles):
    params = BacktestParams(
        initial_capital=5000.0, capital_risk_pct=0.01,
        use_strategy_sl_tp=True,
        runtime_config={"execution": {"exit_on_opposite_signal": False}},
    )
    result = run_backtest_engine(candles, ExampleStatefulStrategy, backtest_params=params)
    assert result.total_trades == 2
    assert result.trades[0].entry_datetime == pd.Timestamp("2026-09-30")
    assert result.trades[1].entry_datetime == pd.Timestamp("2026-10-03")


def test_carry_in_forced_close_does_not_create_trade_or_warning(candles):
    cand = candles.iloc[:4].copy()  # carry-in still open as selected range ends
    params = BacktestParams(
        initial_capital=5000.0, capital_risk_pct=0.01,
        use_strategy_sl_tp=True,
        report_start_date=date(2026, 10, 1),
    )
    result = run_backtest_engine(cand, ExampleStatefulStrategy, backtest_params=params)
    assert result.total_trades == 0
    assert result.final_capital == pytest.approx(5000.0)
    assert result.summary["forced_end_of_backtest_exits"] == 0
    assert not any("closed at the final candle" in w for w in result.warnings)


def test_report_single_day_includes_entry_from_previous_day_signal(candles):
    params = BacktestParams(
        initial_capital=5000.0, capital_risk_pct=0.01,
        use_strategy_sl_tp=True,
        report_start_date=date(2026, 10, 3),
        runtime_config={"execution": {"exit_on_opposite_signal": False}},
    )
    result = run_backtest_engine(candles, ExampleStatefulStrategy, backtest_params=params)
    assert result.total_trades == 1
    assert result.trades[0].entry_datetime == pd.Timestamp("2026-10-03")
    assert result.trades[0].pnl == pytest.approx(100.0)


def test_warmup_sql_fetch_is_prior_only_and_keeps_chronology(monkeypatch):
    import asyncio
    from app.services.backtest_service import BacktestService

    selected = pd.DataFrame([
        (pd.Timestamp("2026-10-01"), 1., 2., 0.5, 1.5, 10.),
        (pd.Timestamp("2026-10-02"), 1.5, 2.5, 1., 2., 10.),
    ], columns=["Date", "Open", "High", "Low", "Close", "Volume"])

    async def fake_selected(*args, **kwargs):
        return selected

    monkeypatch.setattr(BacktestService, "_fetch_market_data", staticmethod(fake_selected))

    class Result:
        def all(self):
            # SQL's descending order, to be re-sorted by the loader.
            return [
                (pd.Timestamp("2026-09-30"), 1., 2., 0.5, 1.5, 10.),
                (pd.Timestamp("2026-09-29"), 1., 2., 0.5, 1.5, 10.),
            ]

    class DB:
        async def execute(self, stmt):
            sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
            assert "market_data.timestamp < '2026-10-01" in sql
            assert "DESC" in sql
            assert "LIMIT 80000" in sql
            return Result()

    frame, selected_count, warmup_count = asyncio.run(
        BacktestService._fetch_market_data_with_warmup(
            DB(), 10, "5m", date(2026, 10, 1), date(2026, 10, 2)
        )
    )
    assert selected_count == 2
    assert warmup_count == 2
    assert list(frame.Date) == list(pd.to_datetime([
        "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"
    ]))


def test_shared_standard_and_funded_warmup_limit():
    """Backtest endpoints share one 80K constant instead of diverging."""
    from pathlib import Path
    from app.services.backtest_service import BacktestService

    assert BacktestService.HISTORICAL_WARMUP_CANDLES == 80_000
    api_dir = Path(__file__).resolve().parents[1] / "app" / "api" / "v1"
    call = "warmup_candles=BacktestService.HISTORICAL_WARMUP_CANDLES"
    assert call in (api_dir / "backtests.py").read_text(encoding="utf-8")
    assert call in (api_dir / "funded_backtests.py").read_text(encoding="utf-8")
