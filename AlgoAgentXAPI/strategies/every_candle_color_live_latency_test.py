from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

try:
    from strategies.base_strategy import BaseStrategy
except ImportError:
    class BaseStrategy:
        """Standalone upload fallback matching the AlgoAgentX constructor contract."""

        def __init__(self, df: pd.DataFrame):
            self.df = df.copy()


class EveryCandleColorLiveLatencyTestStrategy(BaseStrategy):
    """Execution/latency QA strategy: one BUY or SELL on every valid closed bar.

    This is intentionally not a profitability strategy.  It exists to exercise
    candle ingestion, strategy execution, risk/SL/TP, broker ACK/fill, duplicate
    protection and synchronization in a cTrader DEMO account.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        warmup_bars: int = 2,
        min_body_points: float = 0.0,
        sl_buffer_points: float = 0.0,
        sl_buffer_pct: float = 0.0,
        minimum_sl_distance_pct: float = 0.0001,
        allow_long: bool = True,
        allow_short: bool = True,
        doji_side: str = "BUY",
        **kwargs,
    ):
        super().__init__(df)
        self.warmup_bars = max(1, int(warmup_bars or 2))
        self.min_body_points = max(0.0, float(min_body_points or 0.0))
        self.sl_buffer_points = max(0.0, float(sl_buffer_points or 0.0))
        self.sl_buffer_pct = max(0.0, float(sl_buffer_pct or 0.0))
        self.minimum_sl_distance_pct = max(0.0, float(minimum_sl_distance_pct or 0.0001))
        self.allow_long = bool(allow_long)
        self.allow_short = bool(allow_short)
        self.doji_side = str(doji_side or "BUY").strip().upper()
        if self.doji_side not in {"BUY", "SELL"}:
            self.doji_side = "BUY"

    def _prepare(self, frame: pd.DataFrame) -> pd.DataFrame:
        df = frame.copy().reset_index(drop=True)
        for column in ("Open", "High", "Low", "Close"):
            df[column] = pd.to_numeric(df[column], errors="coerce")
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce", utc=True)
        df["Position"] = 0
        df["signal"] = 0
        df["strategy_stop_loss"] = np.nan
        df["strategy_target"] = np.nan
        df["signal_reason"] = None
        df["latency_test_candle_color"] = None
        df["latency_test_signal_bar"] = False
        df["latency_strategy_generated_at_utc"] = None
        return df

    def _buffer(self, reference: float, close: float) -> float:
        configured = max(self.sl_buffer_points, abs(reference) * self.sl_buffer_pct)
        fallback = abs(close) * self.minimum_sl_distance_pct
        return max(configured, fallback)

    def generate(self) -> pd.DataFrame:
        df = self._prepare(self.df)
        generated_at = datetime.now(timezone.utc).isoformat()
        for index in range(self.warmup_bars, len(df)):
            values = [df.at[index, column] for column in ("Open", "High", "Low", "Close")]
            if any(pd.isna(value) for value in values):
                continue
            open_price, high_price, low_price, close_price = (float(value) for value in values)
            if min(open_price, high_price, low_price, close_price) <= 0:
                continue

            body = abs(close_price - open_price)
            if close_price > open_price:
                color, side = "GREEN", "BUY"
            elif close_price < open_price:
                color, side = "RED", "SELL"
            else:
                color, side = "DOJI", self.doji_side

            # Every valid closed candle is eligible.  There is deliberately no
            # index/modulo/every-N gating in this benchmark.
            df.at[index, "latency_test_candle_color"] = color
            df.at[index, "latency_test_signal_bar"] = True
            df.at[index, "latency_strategy_generated_at_utc"] = generated_at

            if body < self.min_body_points and color != "DOJI":
                # Keep the every-candle contract by using candle direction even
                # when the body is small; the threshold is diagnostic metadata.
                threshold_note = f" body={body:.8f} below configured threshold;"
            else:
                threshold_note = ""

            if side == "BUY" and not self.allow_long:
                side = "SELL" if self.allow_short else ""
            elif side == "SELL" and not self.allow_short:
                side = "BUY" if self.allow_long else ""
            if not side:
                continue

            if side == "BUY":
                buffer = self._buffer(low_price, close_price)
                stop_loss = min(low_price - buffer, close_price - buffer)
                if stop_loss <= 0 or stop_loss >= close_price:
                    continue
                df.at[index, "Position"] = 1
                df.at[index, "signal"] = 1
                df.at[index, "strategy_stop_loss"] = float(stop_loss)
            else:
                buffer = self._buffer(high_price, close_price)
                stop_loss = max(high_price + buffer, close_price + buffer)
                if stop_loss <= close_price:
                    continue
                df.at[index, "Position"] = -1
                df.at[index, "signal"] = -1
                df.at[index, "strategy_stop_loss"] = float(stop_loss)

            # NaN intentionally delegates TP to the existing AlgoAgentX RR engine.
            df.at[index, "strategy_target"] = np.nan
            candle_time = df.at[index, "Date"] if "Date" in df.columns else index
            df.at[index, "signal_reason"] = (
                f"{side} LIVE LATENCY TEST: closed candle={color}; "
                f"candle_open_time={candle_time}; open={open_price:.8f}; "
                f"close={close_price:.8f}; stop_loss={stop_loss:.8f};"
                f"{threshold_note} target handled by AlgoAgentX RR engine."
            )
        return df


# The upload/runtime loader used by AlgoAgentX accepts a class named Strategy.
Strategy = EveryCandleColorLiveLatencyTestStrategy
