"""Dynamic strategy regression: imported base is not executable strategy."""
import pandas as pd
from app.services.dynamic_strategy_loader import load_dynamic_strategy_class


def test_authored_subclass_selected_instead_of_imported_base():
    source = """from .base_strategy import BaseStrategy
class TrendFollowingV262(BaseStrategy):
    def generate(self):
        return self.df.copy()
"""
    strategy_class = load_dynamic_strategy_class(source)
    assert strategy_class.__name__ == "TrendFollowingV262"
    df = pd.DataFrame({"Close": [1.0]})
    assert strategy_class(df).generate().equals(df)


def test_multiclass_source_prefers_named_strategy():
    source = """class Helper:
    def generate(self): return None
class Strategy:
    def __init__(self, df): self.df = df
    def generate(self): return self.df
"""
    assert load_dynamic_strategy_class(source).__name__ == "Strategy"
