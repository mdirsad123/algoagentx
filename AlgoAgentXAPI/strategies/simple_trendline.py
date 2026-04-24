import pandas as pd
from strategies.base_strategy import BaseStrategy


class SimpleTrendlineStrategy(BaseStrategy):
    """Simple breakout-style trendline proxy strategy for SaaS execution.

    Since user-defined trendline strategies from the UI do not yet compile into
    executable Python, this class provides a deterministic engine-safe mapping.
    """

    def __init__(self, df, lookback: int = 3, breakout_buffer: float = 0.0, **kwargs):
        super().__init__(df)
        self.lookback = max(int(lookback or 3), 2)
        self.breakout_buffer = float(breakout_buffer or 0.0)

    def generate(self):
        df = self.df.copy()
        adaptive_lookback = min(self.lookback, max(len(df) // 3, 2))
        df["rolling_high"] = df["High"].rolling(adaptive_lookback).max().shift(1)
        df["rolling_low"] = df["Low"].rolling(adaptive_lookback).min().shift(1)
        df["momentum_up"] = df["Close"] > df["Close"].shift(1)
        df["momentum_down"] = df["Close"] < df["Close"].shift(1)
        df["signal"] = 0
        df.loc[(df["Close"] >= (df["rolling_high"] * (1 + self.breakout_buffer))) & df["momentum_up"], "signal"] = 1
        df.loc[(df["Close"] <= (df["rolling_low"] * (1 - self.breakout_buffer))) & df["momentum_down"], "signal"] = -1
        df["Position"] = df["signal"].replace(0, pd.NA).ffill().fillna(0).shift(1).fillna(0)
        return df
