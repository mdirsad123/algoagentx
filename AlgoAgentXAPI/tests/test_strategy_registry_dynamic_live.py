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
