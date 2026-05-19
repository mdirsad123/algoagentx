from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy


class EveryTwoCandleColorDemoStrategy(BaseStrategy):
    """High-frequency candle-colour strategy for AlgoAgentX live/demo QA.

    This strategy is intentionally simple and noisy. It is not designed for
    profitability. It exists so PAPER/DEMO live trading can be tested end to end.

    Engine contract:
    - Position: 1 buy, -1 sell, 0 hold
    - strategy_stop_loss: suggested protective SL for STRATEGY_SUGGESTED mode
    - strategy_target: NaN so the AlgoAgentX RR engine calculates target
    - signal_reason: readable reason for reports/logs
    """

    def __init__(
        self,
        df: pd.DataFrame,
        signal_every_n_candles: int = 2,
        warmup_bars: int = 2,
        ignore_doji: bool = True,
        min_body_points: float = 0.0,
        sl_buffer_points: float = 0.0,
        sl_buffer_pct: float = 0.0,
        allow_long: bool = True,
        allow_short: bool = True,
        signal_latest_candle: bool = True,
        **kwargs,
    ):
        super().__init__(df)
        self.signal_every_n_candles = max(int(signal_every_n_candles or 2), 1)
        self.warmup_bars = max(int(warmup_bars or 2), 1)
        self.ignore_doji = bool(ignore_doji)
        self.min_body_points = float(min_body_points or 0.0)
        self.sl_buffer_points = float(sl_buffer_points or 0.0)
        self.sl_buffer_pct = float(sl_buffer_pct or 0.0)
        self.allow_long = bool(allow_long)
        self.allow_short = bool(allow_short)
        self.signal_latest_candle = bool(signal_latest_candle)

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy().reset_index(drop=True)
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        df["Position"] = 0
        df["signal"] = 0
        df["strategy_stop_loss"] = np.nan
        df["strategy_target"] = np.nan
        df["signal_reason"] = None
        df["demo_candle_color"] = None
        df["demo_signal_bar"] = False
        return df

    def _sl_buffer(self, reference_price: float) -> float:
        pct_buffer = abs(reference_price) * self.sl_buffer_pct if reference_price > 0 else 0.0
        return max(self.sl_buffer_points, pct_buffer)

    def _is_signal_bar(self, i: int, last_i: int) -> bool:
        if self.signal_latest_candle:
            # Live runner reads only the latest row. This makes the latest closed
            # candle eligible, then every N candles backwards in history.
            return ((last_i - i) % self.signal_every_n_candles) == 0
        return (i % self.signal_every_n_candles) == 0

    def generate(self) -> pd.DataFrame:
        df = self._prepare(self.df)
        n = len(df)
        if n == 0:
            return df

        last_i = n - 1
        for i in range(self.warmup_bars, n):
            if not self._is_signal_bar(i, last_i):
                continue

            open_price = df.at[i, "Open"]
            high_price = df.at[i, "High"]
            low_price = df.at[i, "Low"]
            close_price = df.at[i, "Close"]
            if pd.isna(open_price) or pd.isna(high_price) or pd.isna(low_price) or pd.isna(close_price):
                continue

            open_price = float(open_price)
            high_price = float(high_price)
            low_price = float(low_price)
            close_price = float(close_price)
            if min(open_price, high_price, low_price, close_price) <= 0:
                continue

            body = abs(close_price - open_price)
            if body <= self.min_body_points:
                continue

            df.at[i, "demo_signal_bar"] = True

            if close_price > open_price:
                df.at[i, "demo_candle_color"] = "GREEN"
                if not self.allow_long:
                    continue
                buffer = self._sl_buffer(low_price)
                stop_loss = low_price - buffer
                if stop_loss <= 0 or stop_loss >= close_price:
                    continue
                df.at[i, "Position"] = 1
                df.at[i, "signal"] = 1
                df.at[i, "strategy_stop_loss"] = float(stop_loss)
                df.at[i, "strategy_target"] = np.nan
                df.at[i, "signal_reason"] = (
                    "BUY DEMO TEST: latest eligible candle closed GREEN; "
                    f"open={open_price:.5f}, close={close_price:.5f}; "
                    f"SL below candle low={low_price:.5f}; target handled by RR engine."
                )

            elif close_price < open_price:
                df.at[i, "demo_candle_color"] = "RED"
                if not self.allow_short:
                    continue
                buffer = self._sl_buffer(high_price)
                stop_loss = high_price + buffer
                if stop_loss <= close_price:
                    continue
                df.at[i, "Position"] = -1
                df.at[i, "signal"] = -1
                df.at[i, "strategy_stop_loss"] = float(stop_loss)
                df.at[i, "strategy_target"] = np.nan
                df.at[i, "signal_reason"] = (
                    "SELL DEMO TEST: latest eligible candle closed RED; "
                    f"open={open_price:.5f}, close={close_price:.5f}; "
                    f"SL above candle high={high_price:.5f}; target handled by RR engine."
                )

            else:
                df.at[i, "demo_candle_color"] = "DOJI"
                if not self.ignore_doji:
                    df.at[i, "Position"] = 0
                    df.at[i, "signal"] = 0

        return df
