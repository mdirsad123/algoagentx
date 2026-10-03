import pandas as pd

from app.services.strategy_registry import resolve_strategy


DYNAMIC_SOURCE = r"""
class Strategy:
    def __init__(self, df, stop_points=2.0):
        self.df = df.copy()
        self.stop_points = float(stop_points)

    def generate(self):
        out = self.df.copy()
        out["Position"] = 0
        out["strategy_stop_loss"] = float("nan")
        if len(out):
            out.loc[out.index[-1], "Position"] = 1
            out.loc[out.index[-1], "strategy_stop_loss"] = float(out.loc[out.index[-1], "Close"]) - self.stop_points
        return out
"""


def test_dynamic_db_strategy_resolves_through_shared_registry():
    strategy_class, params, name = resolve_strategy(
        "uuid-v132",
        "Trend-Following Breakout V1.32",
        {
            "engine_mode": "DYNAMIC_DB",
            "source_code": DYNAMIC_SOURCE,
            "strategy_params": {"stop_points": 3.5},
        },
    )
    df = pd.DataFrame({"Close": [100.0, 101.0]})
    generated = strategy_class(df, **params).generate()
    assert name == "Trend-Following Breakout V1.32"
    assert float(generated.iloc[-1]["strategy_stop_loss"]) == 97.5


def test_unmapped_legacy_source_code_falls_back_to_dynamic_loader():
    strategy_class, params, name = resolve_strategy(
        "legacy-uuid",
        "Custom DB Strategy Without Static Mapping",
        {"source_code": DYNAMIC_SOURCE, "strategy_params": {"stop_points": 1.0}},
    )
    df = pd.DataFrame({"Close": [50.0]})
    generated = strategy_class(df, **params).generate()
    assert name == "Custom DB Strategy Without Static Mapping"
    assert float(generated.iloc[-1]["strategy_stop_loss"]) == 49.0


def test_attached_source_wins_over_resistance_rejection_static_mapping_without_engine_mode():
    strategy_class, params, name = resolve_strategy(
        "uuid-v35",
        "XAUUSD 5M Resistance Rejection V3.5",
        {"source_code": DYNAMIC_SOURCE, "strategy_params": {"stop_points": 4.0}},
    )
    df = pd.DataFrame({"Close": [100.0]})
    generated = strategy_class(df, **params).generate()
    assert name == "XAUUSD 5M Resistance Rejection V3.5"
    assert float(generated.iloc[-1]["strategy_stop_loss"]) == 96.0


def test_broken_attached_source_never_falls_back_to_v1():
    import pytest

    with pytest.raises(ValueError, match="Static fallback is disabled"):
        resolve_strategy(
            "uuid-v35-broken",
            "XAUUSD 5M Resistance Rejection V3.5",
            {"source_code": "this is not valid python !!!"},
        )


def test_unknown_resistance_rejection_version_without_source_hard_fails():
    import pytest

    with pytest.raises(ValueError, match="No executable strategy mapping"):
        resolve_strategy(
            "uuid-v36",
            "XAUUSD 5M Resistance Rejection V3.6",
            {},
        )


def test_exact_v35_static_fallback_is_registered():
    strategy_class, _params, name = resolve_strategy(
        None,
        "XAUUSD 5M Resistance Rejection V3.5",
        {},
    )
    assert strategy_class.__name__ == "XAUUSD5MSupplyDemandRejectionV35CandidateA"
    assert name == "XAUUSD 5M Resistance Rejection V3.5"


def test_exact_trend_breakout_v137_static_fallback_is_registered():
    strategy_class, _params, name = resolve_strategy(
        None,
        "Trend-Following Breakout V1.37",
        {},
    )
    assert strategy_class.__name__ == "XAUUSD5MTrendBreakoutV137"
    assert name == "Trend-Following Breakout V1.37"


def test_dynamic_loader_cache_refreshes_when_source_changes():
    from app.services.dynamic_strategy_loader import load_dynamic_strategy_class

    first = load_dynamic_strategy_class(DYNAMIC_SOURCE)
    second = load_dynamic_strategy_class(DYNAMIC_SOURCE)
    changed_source = DYNAMIC_SOURCE.replace("stop_points=2.0", "stop_points=2.5")
    changed = load_dynamic_strategy_class(changed_source)
    assert first is second
    assert changed is not first
