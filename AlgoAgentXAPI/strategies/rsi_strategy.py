import pandas as pd
from strategies.base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    def __init__(
        self,
        df,
        rr_ratio=2,          # 🔥 accept but not used
        period=14,
        buy_level=30,
        sell_level=70
    ):
        super().__init__(df)
        self.period = period
        self.buy_level = buy_level
        self.sell_level = sell_level

    def generate(self):
        df = self.df.copy()

        # --- RSI Calculation ---
        delta = df["Close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(self.period).mean()
        avg_loss = loss.rolling(self.period).mean()

        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # --- Signals ---
        df["signal"] = 0
        df.loc[df["rsi"] < self.buy_level, "signal"] = 1
        df.loc[df["rsi"] > self.sell_level, "signal"] = -1

        # --- Engine-compatible position ---
        df["Position"] = df["signal"].shift(1).fillna(0)

        return df
