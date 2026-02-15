import pandas as pd
import numpy as np

class SMCStrategy:
    """
    Smart Money Concept Backtest Strategy (mechanical version)

    Output required by engine:
    - Position column -> 1 (BUY), -1 (SELL), 0 (NO TRADE)
    """

    def __init__(self, df, rr_ratio=2):
        self.df = df.copy()
        self.rr_ratio = rr_ratio

    def _detect_swings(self, df):
        df["swing_high"] = (df["High"] > df["High"].shift(1)) & (df["High"] > df["High"].shift(-1))
        df["swing_low"] = (df["Low"] < df["Low"].shift(1)) & (df["Low"] < df["Low"].shift(-1))
        return df

    def _detect_bos(self, df):
        df["last_swing_high"] = df["High"].where(df["swing_high"]).ffill()
        df["prev_swing_high"] = df["last_swing_high"].shift(1)
        df["last_swing_low"] = df["Low"].where(df["swing_low"]).ffill()
        df["prev_swing_low"] = df["last_swing_low"].shift(1)

        df["bos_up"] = df["Close"] > df["prev_swing_high"]
        df["bos_down"] = df["Close"] < df["prev_swing_low"]
        return df

    def _detect_fvg(self, df):
        df["fvg_up"] = (df["Low"] > df["High"].shift(2))
        df["fvg_dn"] = (df["High"] < df["Low"].shift(2))
        return df

    def _detect_order_blocks(self, df):
        df["bull_ob"] = np.where(
            (df["Close"].shift(1) < df["Open"].shift(1)) & df["bos_up"],
            df["Low"].shift(1),
            np.nan
        )
        df["bear_ob"] = np.where(
            (df["Close"].shift(1) > df["Open"].shift(1)) & df["bos_down"],
            df["High"].shift(1),
            np.nan
        )
        df["bull_ob"] = df["bull_ob"].ffill()
        df["bear_ob"] = df["bear_ob"].ffill()
        return df

    def generate(self):
        df = self.df
        df = self._detect_swings(df)
        df = self._detect_bos(df)
        df = self._detect_fvg(df)
        df = self._detect_order_blocks(df)

        df["Position"] = 0

        # LONG ENTRY: liquidity sweep + bos_up + price returns to OB + optional FVG
        long_signal = (
            (df["Low"] < df["prev_swing_low"]) &   # sweep
            (df["bos_up"]) &
            (df["Low"] <= df["bull_ob"]) &
            (df["fvg_up"])
        )

        # SHORT ENTRY
        short_signal = (
            (df["High"] > df["prev_swing_high"]) &
            (df["bos_down"]) &
            (df["High"] >= df["bear_ob"]) &
            (df["fvg_dn"])
        )

        df.loc[long_signal, "Position"] = 1
        df.loc[short_signal, "Position"] = -1

        return df
