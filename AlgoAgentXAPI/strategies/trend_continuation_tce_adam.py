import pandas as pd
import numpy as np


class TrendContinuationTCE:
    """
    Adam Khoo – Trend Continuation (Backtest Friendly Version)

    Output required by engine:
    - Column: Position
        1  = Long
       -1  = Short
        0  = No trade
    """

    def __init__(self, df, rr_ratio=2):
        self.df = df.copy()
        self.rr_ratio = rr_ratio

    def generate(self):
        df = self.df

        # =========================
        # INDICATORS
        # =========================
        df["EMA_18"] = df["Close"].ewm(span=18, adjust=False).mean()
        df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
        df["SMA_200"] = df["Close"].rolling(200).mean()

        # =========================
        # SWING STRUCTURE
        # =========================
        df["swing_high"] = (
            (df["High"] > df["High"].shift(1)) &
            (df["High"] > df["High"].shift(-1))
        )

        df["swing_low"] = (
            (df["Low"] < df["Low"].shift(1)) &
            (df["Low"] < df["Low"].shift(-1))
        )

        df["last_swing_high"] = df["High"].where(df["swing_high"]).ffill()
        df["prev_swing_high"] = df["last_swing_high"].shift(1)

        df["last_swing_low"] = df["Low"].where(df["swing_low"]).ffill()
        df["prev_swing_low"] = df["last_swing_low"].shift(1)

        # =========================
        # TREND CONDITIONS
        # =========================
        df["uptrend"] = (
            (df["Close"] > df["EMA_18"]) &
            (df["EMA_18"] > df["EMA_50"]) &
            (df["EMA_50"] > df["SMA_200"]) &
            (df["last_swing_high"] > df["prev_swing_high"]) &
            (df["last_swing_low"] > df["prev_swing_low"])
        )

        df["downtrend"] = (
            (df["Close"] < df["EMA_18"]) &
            (df["EMA_18"] < df["EMA_50"]) &
            (df["EMA_50"] < df["SMA_200"]) &
            (df["last_swing_high"] < df["prev_swing_high"]) &
            (df["last_swing_low"] < df["prev_swing_low"])
        )

        # =========================
        # EMA PULLBACK ZONE
        # =========================
        df["pullback_long"] = (
            (df["Low"] <= df["EMA_18"]) |
            (df["Low"] <= df["EMA_50"])
        )

        df["pullback_short"] = (
            (df["High"] >= df["EMA_18"]) |
            (df["High"] >= df["EMA_50"])
        )

        # =========================
        # ENGULFING PATTERNS
        # =========================
        df["bullish_engulfing"] = (
            (df["Close"] > df["Open"]) &
            (df["Close"].shift(1) < df["Open"].shift(1)) &
            (df["Close"] > df["Open"].shift(1)) &
            (df["Open"] < df["Close"].shift(1))
        )

        df["bearish_engulfing"] = (
            (df["Close"] < df["Open"]) &
            (df["Close"].shift(1) > df["Open"].shift(1)) &
            (df["Open"] > df["Close"].shift(1)) &
            (df["Close"] < df["Open"].shift(1))
        )

        # =========================
        # FINAL SIGNAL
        # =========================
        df["Position"] = 0

        df.loc[
            df["uptrend"] &
            df["pullback_long"] &
            df["bullish_engulfing"],
            "Position"
        ] = 1

        df.loc[
            df["downtrend"] &
            df["pullback_short"] &
            df["bearish_engulfing"],
            "Position"
        ] = -1

        return df
