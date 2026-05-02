"""
EMA 9/20 Trend Momentum Strategy for Forex / Gold / BTC.

Signal model:
- Signal is confirmed on crossover candle close.
- Backtest engine enters on the next candle open.
- Strategy provides Position and strategy_stop_loss.
- Engine calculates target from real next-candle entry price.
"""

import numpy as np
import pandas as pd


class StockBurnerEMA920:
    """EMA 9/20 Trend Momentum Strategy, Forex / Gold / BTC compatible."""

    def __init__(
        self,
        df: pd.DataFrame,
        rr_ratio: float = 2.0,
        swing_lookback: int = 5,
        use_atr_sl: bool = True,
        atr_period: int = 14,
        atr_multiplier: float = 1.5,
        body_ratio_min: float = 0.5,
        use_ema_200_filter: bool = True,
    ):
        self.df = df.copy()
        self.rr_ratio = float(rr_ratio)
        self.swing_lookback = int(swing_lookback)
        self.use_atr_sl = bool(use_atr_sl)
        self.atr_period = int(atr_period)
        self.atr_multiplier = float(atr_multiplier)
        self.body_ratio_min = float(body_ratio_min)
        self.use_ema_200_filter = bool(use_ema_200_filter)

    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift(1)).abs()
        low_close = (df["Low"] - df["Close"].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=self.atr_period).mean()

    def generate(self) -> pd.DataFrame:
        df = self.df.copy()

        required_columns = ["Open", "High", "Low", "Close"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=required_columns).copy()

        df["ema_9"] = df["Close"].ewm(span=9, adjust=False).mean()
        df["ema_20"] = df["Close"].ewm(span=20, adjust=False).mean()
        df["ema_200"] = df["Close"].ewm(span=200, adjust=False).mean()
        df["atr"] = self._calculate_atr(df)

        # Use previous candles only for swing SL. Do not use current signal candle high/low.
        df["swing_low"] = df["Low"].shift(1).rolling(window=self.swing_lookback).min()
        df["swing_high"] = df["High"].shift(1).rolling(window=self.swing_lookback).max()

        df["body"] = (df["Close"] - df["Open"]).abs()
        df["candle_range"] = (df["High"] - df["Low"]).replace(0, np.nan)
        df["body_ratio"] = (df["body"] / df["candle_range"]).replace([np.inf, -np.inf], np.nan).fillna(0)

        df["Position"] = 0
        df["signal_reason"] = None
        df["strategy_stop_loss"] = np.nan
        df["strategy_target"] = np.nan

        min_start = max(201, self.atr_period + 2, self.swing_lookback + 2)

        for i in range(min_start, len(df)):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]

            bullish_cross = prev["ema_9"] <= prev["ema_20"] and curr["ema_9"] > curr["ema_20"]
            bearish_cross = prev["ema_9"] >= prev["ema_20"] and curr["ema_9"] < curr["ema_20"]
            bullish_candle = curr["Close"] > curr["Open"]
            bearish_candle = curr["Close"] < curr["Open"]
            strong_body = curr["body_ratio"] >= self.body_ratio_min

            long_trend_ok = True if not self.use_ema_200_filter else curr["Close"] > curr["ema_200"]
            short_trend_ok = True if not self.use_ema_200_filter else curr["Close"] < curr["ema_200"]

            if bullish_cross and long_trend_ok and bullish_candle and strong_body:
                signal_close = float(curr["Close"])
                if self.use_atr_sl and not pd.isna(curr["atr"]) and curr["atr"] > 0:
                    stop_loss = signal_close - (float(curr["atr"]) * self.atr_multiplier)
                else:
                    stop_loss = curr["swing_low"]
                if pd.isna(stop_loss) or float(stop_loss) >= signal_close:
                    continue
                df.at[df.index[i], "Position"] = 1
                df.at[df.index[i], "signal_reason"] = "EMA9 crossed above EMA20 + trend + momentum"
                df.at[df.index[i], "strategy_stop_loss"] = float(stop_loss)

            elif bearish_cross and short_trend_ok and bearish_candle and strong_body:
                signal_close = float(curr["Close"])
                if self.use_atr_sl and not pd.isna(curr["atr"]) and curr["atr"] > 0:
                    stop_loss = signal_close + (float(curr["atr"]) * self.atr_multiplier)
                else:
                    stop_loss = curr["swing_high"]
                if pd.isna(stop_loss) or float(stop_loss) <= signal_close:
                    continue
                df.at[df.index[i], "Position"] = -1
                df.at[df.index[i], "signal_reason"] = "EMA9 crossed below EMA20 + trend + momentum"
                df.at[df.index[i], "strategy_stop_loss"] = float(stop_loss)

        return df
