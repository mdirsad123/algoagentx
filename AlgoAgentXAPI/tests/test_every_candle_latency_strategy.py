from datetime import datetime, timedelta, timezone

import pandas as pd

from strategies.every_candle_color_live_latency_test import (
    EveryCandleColorLiveLatencyTestStrategy,
)


def test_latest_closed_bar_always_has_a_trade_signal_including_doji():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    frame = pd.DataFrame({
        "Date": [start + timedelta(minutes=index) for index in range(5)],
        "Open": [100, 100, 102, 101, 105],
        "High": [102, 103, 103, 102, 106],
        "Low": [99, 99, 100, 99, 104],
        "Close": [101, 102, 101, 101, 105],  # rows 3 and 4 are doji
    })
    result = EveryCandleColorLiveLatencyTestStrategy(frame, warmup_bars=1).generate()

    assert result.loc[1:, "latency_test_signal_bar"].all()
    assert set(result.loc[1:, "Position"].astype(int)).issubset({-1, 1})
    assert int(result.iloc[-1]["Position"]) == 1
    assert float(result.iloc[-1]["strategy_stop_loss"]) < float(result.iloc[-1]["Close"])
    assert "LIVE LATENCY TEST" in str(result.iloc[-1]["signal_reason"])


def test_no_every_n_index_gate_changes_latest_signal():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = pd.DataFrame({
        "Date": [base + timedelta(minutes=i) for i in range(3)],
        "Open": [100, 100, 100], "High": [102, 102, 102],
        "Low": [99, 99, 99], "Close": [101, 101, 101],
    })
    second = pd.concat([first, pd.DataFrame([{
        "Date": base + timedelta(minutes=3), "Open": 101, "High": 102,
        "Low": 98, "Close": 99,
    }])], ignore_index=True)

    assert int(EveryCandleColorLiveLatencyTestStrategy(first, warmup_bars=1).generate().iloc[-1]["Position"]) == 1
    assert int(EveryCandleColorLiveLatencyTestStrategy(second, warmup_bars=1).generate().iloc[-1]["Position"]) == -1

