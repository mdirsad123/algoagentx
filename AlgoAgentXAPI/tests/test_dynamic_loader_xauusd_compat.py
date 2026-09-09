from pathlib import Path

import pandas as pd
import pytest

from app.services.dynamic_strategy_loader import (
    DynamicStrategySecurityError,
    load_dynamic_strategy_class,
    validate_dynamic_strategy_source,
)


def _source() -> str:
    return (Path(__file__).resolve().parents[1] / "strategies" / "xauusd_5m_resistance_rejection_v1.py").read_text()


def test_static_xauusd_source_is_dynamic_db_compatible():
    source = _source()
    result = validate_dynamic_strategy_source(source)
    assert "XAUUSD5MResistanceRejectionV1" in result["classes"]
    strategy_class = load_dynamic_strategy_class(source)
    assert strategy_class.__name__ == "XAUUSD5MResistanceRejectionV1"


def test_dynamic_loaded_xauusd_generates_position_dataframe():
    strategy_class = load_dynamic_strategy_class(_source())
    rows = []
    price = 2000.0
    for i in range(30):
        rows.append({
            "Date": pd.Timestamp("2026-07-01") + pd.Timedelta(minutes=5 * i),
            "Open": price,
            "High": price + 1.0,
            "Low": price - 1.0,
            "Close": price + 0.2,
        })
        price += 0.1
    out = strategy_class(pd.DataFrame(rows)).generate()
    assert "Position" in out.columns
    assert out.attrs.get("strategy_diagnostics", {}).get("strategy") == "XAUUSD 5M Resistance Rejection V1"


def test_dynamic_loader_still_blocks_dangerous_imports():
    with pytest.raises(DynamicStrategySecurityError):
        validate_dynamic_strategy_source("import os\nclass Strategy:\n    def generate(self):\n        return None\n")


def test_dynamic_loaded_xauusd_executes_zone_rejection_path_without_missing_safe_builtins():
    strategy_class = load_dynamic_strategy_class(_source())
    prices = [100, 101, 102, 106, 102, 100, 99, 100, 102, 104.8, 106.2, 103.0, 101.5]
    rows = []
    for i, close in enumerate(prices):
        open_ = close - 0.2
        high = close + 0.8
        low = close - 0.8
        if i == 3:
            high = 108.0
        if i == 10:
            open_, high, low, close = 105.8, 108.2, 102.5, 103.0
        rows.append({
            "Date": pd.Timestamp("2026-07-01") + pd.Timedelta(minutes=5 * i),
            "Open": open_, "High": high, "Low": low, "Close": close,
        })
    out = strategy_class(
        pd.DataFrame(rows),
        swing_left=2, swing_right=2, zone_width=2.0,
        minimum_reaction=1.0, minimum_strength=0.5,
        minimum_distance=0.0, merge_distance=1.0, approach_distance=8.0,
        minimum_body_ratio=0.1, minimum_upper_wick_ratio=0.1,
        minimum_zone_penetration=0.0, maximum_close_position=0.8,
        entry_confirmation="REJECTION_CLOSE", sl_buffer=0.2,
        target_rr=2.0, minimum_rr=1.0, debug_mode=True,
    ).generate()
    assert int((out["Position"] == -1).sum()) == 1
    diag = out.attrs["strategy_diagnostics"]
    assert diag["executed_trades"] == 1
