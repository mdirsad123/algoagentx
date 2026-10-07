from __future__ import annotations

import numpy as np
import pandas as pd


class XAUUSD5MTrendBreakoutV137:
    LIVE_HISTORY_BARS = 20000

    """XAUUSD 5M Trend-Following Breakout / Breakdown V1.37.

    V1.27 retains the complete locally verified V1.26 stack and adds one new
    threshold-robust continuation-SHORT residual weak-cluster rejection filter. The research contract remains strict:
    each accepted rule must remove at least 3 losses per winner sacrificed on the
    sequential residual executed set and survive full max-one-position replay.

    Runtime/backtest contract retained:
      - XAUUSD 5-minute candles.
      - Previous 12 completed candles define resistance/support.
      - LONG when close > prior 12-bar high; SHORT when close < prior 12-bar low.
      - Continuation/re-breakout signals are allowed.
      - New signals blocked only from 00:00 <= IST < 05:00.
      - Strategy SL = ATR(14) * 1.5 from the signal-candle close.
      - strategy_target = NaN; AlgoAgentX computes TP from next-candle-open entry.
      - AlgoAgentX RR = 2.0.
      - Exit On Opposite Signal = OFF.
      - Max Open Positions = 1.

    Existing accepted stack retained unchanged:
      - V1.12 + V1.13 + V1.14.
      - V1.15 ten Priority-1 filters.
      - V1.16 four continuation-SHORT P2/P3 filters.

    V1.17 strict residual filters (all FIRST SHORT):
      S1: 5m mom3/ATR in [-8.7810694567, -2.7268962162] AND
          1h mom3/ATR in [-1.4913943100, -0.6101269976].
      S2: 5m ADX14 in [23.2162860942, 26.1543280116] AND
          daily efficiency12 in [0.2077761372, 0.3699613434].
      S3: 30m pre-range6/ATR in [2.6216878327, 2.8869788091] AND
          daily body percentage in [0.8025162498, 0.9856146183].
      S4: 4h pre-range6/ATR in [3.8398713087, 7.1132306942] AND
          daily pre-range24/ATR in [3.9957951869, 4.4335870606].

    V1.19 adds only two large residual FIRST-LONG weak-cluster filters after
    V1.18 robustness validation:
      L1: 15m ADX14 in [21.6718792771, 26.4824573429] AND
          4h range/ATR14 in [0.7612020413, 0.8297001806].
      L2: completed-daily mom6/ATR14 in [-5.9467729098, -1.6114993043] AND
          15m range/ATR14 in [0.8312945147, 0.9655841342].

    V1.23 adds four strict residual filters after the locally verified V1.19 baseline.
    Every filter had >=3 losses per winner sacrificed on the residual sequence and
    improved full max-one-position replay without damaging any research year.
      N1 FIRST SHORT: daily EMA50 slope12/ATR14 in [0.8042387810, 1.0656475167]
         AND 4h DMI spread in [-2.8245668329, 0.4007073105].
      N2 FIRST SHORT: same daily EMA50 slope12/ATR14 band
         AND 5m efficiency12 in [0.1068200876, 0.1541269299].
      N3 FIRST LONG: 15m ADX14 in [20.2025760546, 24.6161463792]
         AND 15m ATR14/ATR50 in [1.0223217001, 1.0651227880].
      N4 FIRST LONG: 15m ADX14 in [21.6718792771, 24.6161463792]
         AND 30m mom3/ATR14 in [-0.7657313233, -0.3022596028].

    V1.24 adds five threshold-robust residual weak-cluster filters after the
    locally verified V1.23 baseline. Each rule retains >=3 losses per winner
    sacrificed on its sequential residual executed set and improves full replay
    with no research-year R damage:
      Q1 FIRST SHORT: 30m pre-range6/ATR in [2.3709655089, 3.0520396862]
         AND 5m EMA50 slope24/ATR in [-0.7227882220, -0.1730798212].
      Q2 FIRST LONG: daily body/range in [0.6659175667, 0.7836260019]
         AND 4h (EMA50-EMA100)/ATR in [0.4758055175, 0.9566301916].
      Q3 FIRST SHORT: daily pre-range6/ATR in [2.1425887898, 2.4018351735]
         AND 5m mom48/ATR in [-3.4741246690, -2.3352359870].
      Q4 FIRST LONG: 1h RSI14 in [43.7505740764, 48.1991531130]
         AND 5m efficiency48 in [0.2071427389, 0.2756997262].
      Q5 FIRST SHORT: 1h mom12/ATR in [0.7032429055, 2.6131869786]
         AND 30m (EMA20-EMA50)/ATR in [-1.3818422432, -0.7240207919].


    V1.25 adds five new threshold-robust residual filters after the locally
    verified V1.24 baseline. Each rule keeps the strict minimum >=3 losses
    removed per winner sacrificed on the sequential residual executed set:
      R1 FIRST SHORT: 15m prior-12-bar range/ATR in [4.7877309968, 8.2687452250]
         AND daily ATR14/ATR50 in [1.1771525817, 1.3491173887].
      R2 FIRST LONG: 1h mom3/ATR in [0.3574554357, 0.6374825122]
         AND 30m body/range in [0.0982378639, 0.1957493478].
      R3 FIRST SHORT: 1h prior-24-bar range/ATR in [5.3135029545, 5.7680183400]
         AND 30m DMI spread in [16.2653148244, 53.1374390625].
      R4 FIRST SHORT: 5m candle range/ATR in [1.6015545792, 1.7953360070]
         AND 15m body/ATR in [0.2177544615, 0.3249426084].
      R5 FIRST LONG: 1h EMA50 slope3/ATR in [-0.1043279896, -0.0248473427]
         AND 1h ATR14/ATR100 in [0.8101837802, 0.8648618600].

    V1.26 adds five new residual filters after the locally verified V1.25 baseline:
      T1 FIRST SHORT: 5m breakout distance/ATR in [0.3701182902, 0.5076948777]
         AND 15m prior-12-bar range/ATR in [3.6593077183, 4.0297126770].
      T2 FIRST LONG: 1h mom3/ATR in [0.7967089117, 1.3812967539]
         AND 1h efficiency12 in [0.2707477212, 0.3518402465].
      T3 FIRST SHORT: 5m +DI-minus--DI in [-17.1166977882, -13.6595921516]
         AND 1h close location in [0.1575653441, 0.2603150457].
      T4 FIRST SHORT: 5m EMA20-EMA50/ATR in [0.4695834294, 0.9608252645]
         AND daily ATR14/ATR50 in [1.2745355368, 2.2095172405].
      T5 FIRST SHORT: 30m prior-12-bar range/ATR in [4.7320714593, 8.4064006805]
         AND 4h EMA50-EMA100/ATR in [0.4285192788, 0.8740809560].

    V1.27 adds one robust residual CONTINUATION-SHORT filter after the locally
    verified V1.26 baseline:
      U1 CONT SHORT: 1h DMI spread (+DI minus -DI) in [14.4142003059, 42.4612922668]
         AND completed-daily candle body / ATR14 in [1.1263068914, 2.9820482731].

    A second candidate (5m/30m DMI interaction) was rejected despite in-sample
    improvement because it reduced the small unseen 16-23 Sep 2026 check by 3R.

    V1.28 adds five cross-year / walk-forward residual filters discovered on
    2022-2024 and validated without threshold refitting on 2025-2026:
      W1 FIRST LONG: 30m efficiency12 in [0.4845301151, 1.0]
         AND 4h RSI14 in [51.9246711731, 55.5411109924].
      W2 CONT LONG: 4h ATR14/ATR100 in [1.0983357430, 1.2455777526]
         AND 15m ADX14 in [20.5149085999, 24.5773429871].
      W3 CONT SHORT: 5m close location in [0.3924613893, 0.8718723059]
         AND 4h EMA50 slope3/ATR in [-0.2096049458, -0.0441477142].
      W4 FIRST SHORT: 1h mom6/ATR in [-1.4199699163, -0.9584665596]
         AND 30m volume/20-bar-average in [0.9593228579, 1.0638521910].
      W5 FIRST SHORT: 5m EMA100 slope12/ATR in [-0.6960670948, -0.4856413603]
         AND the same 30m volume-ratio band.

    V1.29 adds two additional cross-year residual filters after the locally verified V1.28 baseline:
      X1 CONT SHORT: 30m range/ATR in [0.1708231568, 0.7277669191]
         AND 4h mom3/ATR in [-0.6843645930, -0.4295875400].
      X2 CONT SHORT: 30m efficiency12 <= 0.2168189660 AND
         5m upper-wick/range > 0.3824375421 AND
         15m prior-12-bar range/ATR <= 3.2175476551.

    V1.30 adds one walk-forward residual common-loss filter after the locally verified V1.29 baseline:
      Y1 CONT LONG: completed-15m efficiency12 <= 0.3848053554 AND
         completed-1h prior-48-bar range/ATR14 > 10.3202227764 AND
         completed-1h efficiency6 > 0.5920152148 AND
         completed-4h ADX14 > 23.2647884561.

    V1.31 switches the research regime to 2024 through 15-Sep-2026 and adds
    one cross-year residual weak-cluster filter:
      Z1 FIRST SHORT: completed-30m DMI spread (+DI minus -DI)
         in [-4.7505041524, -1.4808815977] AND completed-1h
         prior-24-bar range / ATR14 in [5.5230587144, 6.0552353510].

    Z1 was discovered on 2024-2025 and remained directly loss-making in 2026.
    Direct executed cluster on V1.30: 35 trades = 6W / 29L (4.83:1).

    V1.32 adds three new 2024+ regime residual weak-cluster filters after the
    locally verified V1.31 baseline. Each rule was discovered from the V1.31
    residual executed sequence, remained directly loss-making in 2024/2025/2026,
    retained >=3 losses per winner sacrificed sequentially, improved full replay,
    and passed neighboring-threshold sensitivity checks:
      AA1 CONT LONG: 5m mom24/ATR14 <= 0.724521816845061 AND
          5m CCI40 <= 42.676860081478424.
      AA2 CONT LONG: completed-daily upper-wick/range <= 0.04386618253210123 AND
          completed-1h CHOP28 <= 39.44448064779493.
      AA3 CONT SHORT: prior-192-bar raw LONG signal count in [16, 21] AND
          5m mom192/ATR14 >= 8.025282314262077.


    V1.33 through V1.37 add sequential residual weak-cluster filters researched
    against the accepted live exit model (90% partial at +1.70R, 10% runner to +2R):
      AB1 V1.33 CONT SHORT: completed-daily RSI14 >= 82.0.
      AB2 V1.34 CONT LONG: 5m mom96/ATR14 in [-4.6, -3.7].
      AB3 V1.35 FIRST LONG: completed-1h efficiency12 > 0.70 AND
          5m EMA20 slope12/ATR14 > 2.10.
      AB4 V1.36 CONT LONG (2024+ regime): completed-1h range/ATR <= 2.50 AND
          completed-4h prior-12 range/ATR > 3.80 AND
          completed-1h mom6/ATR > 2.30.
      AB5 V1.37 FIRST LONG: 96-bar linear-regression R^2 > 0.47 AND
          40-bar Bollinger width/ATR <= 3.00 AND ATR14 six-bar slope <= 0.17.

    V1.38 residual research was rejected; no further rule survived the strict
    current-regime + full-history sanity contract in this research cycle.

    FIRST/continuation context is evaluated from the UNFILTERED V1.10 raw signal
    stream. Rejected raw signals do not reclassify later raw signals.

    V1.32 primary research window:
      01-Jan-2024 through 15-Sep-2026, RR=2, next-candle-open,
      Exit On Opposite Signal OFF, Max Open Positions=1.
    Full-history sanity check:
      01-Jan-2022 through 15-Sep-2026.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        breakout_lookback: int = 12,
        atr_period: int = 14,
        atr_multiplier: float = 1.5,
        min_breakout_points: float = 0.0,
        allow_long: bool = True,
        allow_short: bool = True,
        **kwargs,
    ):
        self.df = df.copy()
        self.breakout_lookback = max(2, int(breakout_lookback or 12))
        self.atr_period = max(2, int(atr_period or 14))
        self.atr_multiplier = max(0.01, float(atr_multiplier or 1.5))
        self.min_breakout_points = max(0.0, float(min_breakout_points or 0.0))
        self.allow_long = bool(allow_long)
        self.allow_short = bool(allow_short)

        self.block_start_minutes_ist = 0
        self.block_end_minutes_ist = 5 * 60
        self.research_rr = 2.0

    def _prepare(self, frame: pd.DataFrame) -> pd.DataFrame:
        df = frame.copy().reset_index(drop=True)

        required = ("Open", "High", "Low", "Close", "Volume")
        missing = [column for column in required if column not in df.columns]
        if missing:
            raise ValueError(
                "V1.24 requires OHLCV data. Missing columns: " + str(missing)
            )

        for column in required:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        if "Date" not in df.columns:
            raise ValueError("Date column is required for the V1.24 IST session filter")

        parsed_utc = pd.to_datetime(df["Date"], errors="coerce", utc=True)
        ist_clock = parsed_utc + pd.Timedelta(hours=5, minutes=30)

        df["_tfb_v1_17_ist_minutes"] = ist_clock.dt.hour * 60 + ist_clock.dt.minute
        df["_tfb_v1_17_ist_clock"] = ist_clock.dt.strftime("%H:%M")
        df["Date"] = parsed_utc.dt.tz_localize(None)

        df["Position"] = 0
        df["signal"] = 0
        df["strategy_stop_loss"] = float("nan")
        df["strategy_target"] = float("nan")
        df["signal_reason"] = None

        # Diagnostics; execution still uses Position/SL/TP only.
        df["tfb_v1_17_type"] = None
        df["tfb_v1_17_level"] = float("nan")
        df["tfb_v1_17_atr"] = float("nan")
        df["tfb_v1_17_breakout_distance"] = float("nan")
        df["tfb_v1_17_breakout_distance_atr"] = float("nan")
        df["tfb_v1_17_lookback"] = self.breakout_lookback
        df["tfb_v1_17_ist_time"] = None
        df["tfb_v1_17_rr"] = self.research_rr
        df["tfb_v1_17_continuation_allowed"] = True
        df["tfb_v1_17_first_long"] = False
        df["tfb_v1_17_first_short"] = False
        df["tfb_v1_17_bars_since_same_signal"] = float("nan")
        for rank in range(1, 11):
            df[f"tfb_v1_17_p1_reject_{rank}"] = False
        df["tfb_v1_17_p2_atr_reject"] = False
        df["tfb_v1_17_p3_1h_ema_reject"] = False
        df["tfb_v1_17_p3_15m_mom_reject"] = False
        df["tfb_v1_17_p3_daily_mom_reject"] = False
        for rank in range(1, 5):
            df[f"tfb_v1_17_strict_reject_{rank}"] = False
        for rank in range(1, 3):
            df[f"tfb_v1_19_large_reject_{rank}"] = False
        for rank in range(1, 5):
            df[f"tfb_v1_23_reject_{rank}"] = False
        for rank in range(1, 6):
            df[f"tfb_v1_24_reject_{rank}"] = False
        for rank in range(1, 6):
            df[f"tfb_v1_25_reject_{rank}"] = False
        for rank in range(1, 6):
            df[f"tfb_v1_26_reject_{rank}"] = False
        df["tfb_v1_27_reject_1"] = False
        df["tfb_v1_31_reject_1"] = False
        for rank in range(1, 4):
            df[f"tfb_v1_32_reject_{rank}"] = False
        df["tfb_v1_33_reject_1"] = False
        df["tfb_v1_34_reject_1"] = False
        df["tfb_v1_35_reject_1"] = False
        df["tfb_v1_36_reject_1"] = False
        df["tfb_v1_37_reject_1"] = False
        for rank in range(1, 6):
            df[f"tfb_v1_28_reject_{rank}"] = False
        df["tfb_v1_17_rejected"] = False
        df["tfb_v1_17_reject_rule"] = None

        return df

    @staticmethod
    def _true_range(df: pd.DataFrame) -> pd.Series:
        previous_close = df["Close"].shift(1)
        range_1 = df["High"] - df["Low"]
        range_2 = (df["High"] - previous_close).abs()
        range_3 = (df["Low"] - previous_close).abs()
        return pd.concat([range_1, range_2, range_3], axis=1).max(axis=1)

    @staticmethod
    def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        avg_up = up.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_down = down.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        rs = avg_up / avg_down.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _adx_wilder(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        up = high.diff()
        down = -low.diff()
        plus_dm = up.where((up > down) & (up > 0), 0.0)
        minus_dm = down.where((down > up) & (down > 0), 0.0)
        tr = pd.concat(
            [
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr_wilder = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        plus = 100 * plus_dm.ewm(
            alpha=1 / period, adjust=False, min_periods=period
        ).mean() / atr_wilder
        minus = 100 * minus_dm.ewm(
            alpha=1 / period, adjust=False, min_periods=period
        ).mean() / atr_wilder
        dx = 100 * (plus - minus).abs() / (plus + minus).replace(0, np.nan)
        adx = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        return adx, plus, minus

    @classmethod
    def _make_htf_features(
        cls,
        df: pd.DataFrame,
        freq: str,
        minutes: int,
    ) -> pd.DataFrame:
        """Build features only from completed higher-timeframe candles.

        For a 30-minute bucket starting at 10:00, the bar becomes available at
        10:25, the timestamp of its final 5-minute candle. This matches the
        lookahead-safe research feature construction.
        """
        x = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        x["_bucket"] = x["Date"].dt.floor(freq)
        agg = (
            x.groupby("_bucket", sort=True)
            .agg(
                Open=("Open", "first"),
                High=("High", "max"),
                Low=("Low", "min"),
                Close=("Close", "last"),
                Volume=("Volume", "sum"),
            )
            .reset_index()
        )
        agg["avail_time"] = agg["_bucket"] + pd.Timedelta(minutes=minutes - 5)

        high = agg["High"].astype(float)
        low = agg["Low"].astype(float)
        close = agg["Close"].astype(float)
        previous_close = close.shift(1)
        tr = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr14 = tr.rolling(14, min_periods=14).mean()
        atr50 = tr.rolling(50, min_periods=30).mean()
        atr100 = tr.rolling(100, min_periods=50).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        ema100 = close.ewm(span=100, adjust=False).mean()
        rsi14 = cls._rsi(close, 14)
        adx14, plus_di, minus_di = cls._adx_wilder(high, low, close, 14)
        candle_range = high - low
        candle_body = (close - agg["Open"].astype(float)).abs()
        candle_upper_wick = high - pd.concat([agg["Open"].astype(float), close], axis=1).max(axis=1)

        out = pd.DataFrame({"avail_time": agg["avail_time"]})
        out["close_location"] = (close - low) / candle_range.replace(0, np.nan)
        out["range_atr"] = candle_range / atr14
        out["body_atr"] = candle_body / atr14
        out["body_pct"] = candle_body / candle_range.replace(0, np.nan)
        out["upper_wick_pct"] = candle_upper_wick / candle_range.replace(0, np.nan)
        range28 = (
            high.rolling(28, min_periods=28).max()
            - low.rolling(28, min_periods=28).min()
        ).replace(0, np.nan)
        out["chop28"] = 100.0 * np.log10(
            tr.rolling(28, min_periods=28).sum() / range28
        ) / np.log10(28.0)
        out["atr14_50_ratio"] = atr14 / atr50
        out["atr14_100_ratio"] = atr14 / atr100
        out["ema20_50_atr"] = (ema20 - ema50) / atr14
        out["ema50_100_atr"] = (ema50 - ema100) / atr14
        out["rsi14"] = rsi14
        out["adx14"] = adx14
        out["pdi_minus_mdi"] = plus_di - minus_di
        out["ema50_slope3_atr"] = (ema50 - ema50.shift(3)) / atr14
        out["ema50_slope12_atr"] = (ema50 - ema50.shift(12)) / atr14
        out["mom3_atr"] = (close - close.shift(3)) / atr14
        out["mom6_atr"] = (close - close.shift(6)) / atr14
        out["mom12_atr"] = (close - close.shift(12)) / atr14
        out["volume_ratio20"] = agg["Volume"].astype(float) / (
            agg["Volume"].astype(float).shift(1).rolling(20, min_periods=20).mean()
        )
        out["pre_range6_atr"] = (
            high.shift(1).rolling(6, min_periods=6).max()
            - low.shift(1).rolling(6, min_periods=6).min()
        ) / atr14
        out["pre_range12_atr"] = (
            high.shift(1).rolling(12, min_periods=12).max()
            - low.shift(1).rolling(12, min_periods=12).min()
        ) / atr14
        out["pre_range24_atr"] = (
            high.shift(1).rolling(24, min_periods=24).max()
            - low.shift(1).rolling(24, min_periods=24).min()
        ) / atr14
        out["pre_range48_atr"] = (
            high.shift(1).rolling(48, min_periods=48).max()
            - low.shift(1).rolling(48, min_periods=48).min()
        ) / atr14
        close_shift1 = close.shift(1)
        out["eff6"] = (
            (close_shift1 - close.shift(7)).abs()
            / close_shift1.diff().abs().rolling(6, min_periods=6).sum().replace(0, np.nan)
        )
        out["eff12"] = (
            (close_shift1 - close.shift(13)).abs()
            / close_shift1.diff().abs().rolling(12, min_periods=12).sum().replace(0, np.nan)
        )
        return out

    @staticmethod
    def _between(series: pd.Series, low: float, high: float) -> np.ndarray:
        values = series.to_numpy(float)
        return np.isfinite(values) & (values >= low) & (values <= high)

    def generate(self) -> pd.DataFrame:
        df = self._prepare(self.df)

        prior_high = (
            df["High"]
            .shift(1)
            .rolling(self.breakout_lookback, min_periods=self.breakout_lookback)
            .max()
        )
        prior_low = (
            df["Low"]
            .shift(1)
            .rolling(self.breakout_lookback, min_periods=self.breakout_lookback)
            .min()
        )

        true_range = self._true_range(df)
        atr = true_range.rolling(self.atr_period, min_periods=self.atr_period).mean()
        atr50_5m = true_range.rolling(50, min_periods=30).mean()
        atr14_atr50_ratio = atr / atr50_5m
        mom3_atr_5m = (df["Close"] - df["Close"].shift(3)) / atr
        adx14_5m, _pdi_5m, _mdi_5m = self._adx_wilder(
            df["High"], df["Low"], df["Close"], 14
        )

        # ---------------------------
        # Existing V1.12-V1.14 fields
        # ---------------------------
        prior_range6 = (
            df["High"].shift(1).rolling(6, min_periods=6).max()
            - df["Low"].shift(1).rolling(6, min_periods=6).min()
        )
        short_mom6_atr = (df["Close"].shift(6) - df["Close"]) / atr
        pre_range6_atr = prior_range6 / atr

        ema20 = df["Close"].ewm(span=20, adjust=False).mean()
        ema50 = df["Close"].ewm(span=50, adjust=False).mean()
        ema100_5m = df["Close"].ewm(span=100, adjust=False).mean()
        ema100_slope12_atr_5m = (ema100_5m - ema100_5m.shift(12)) / atr
        candle_close_location_5m = (df["Close"] - df["Low"]) / (df["High"] - df["Low"]).replace(0, np.nan)
        atr100 = true_range.rolling(100, min_periods=30).mean()
        bull_ema_align_atr = (ema20 - ema50) / atr
        atr_ratio100 = atr / atr100
        short_ema50_extension_atr = (ema50 - df["Close"]) / atr

        # ---------------------------
        # Raw V1.10 signal stream
        # ---------------------------
        n = len(df)
        warmup = max(self.breakout_lookback + 1, self.atr_period + 1)

        open_arr = df["Open"].to_numpy(float)
        high_arr = df["High"].to_numpy(float)
        low_arr = df["Low"].to_numpy(float)
        close_arr = df["Close"].to_numpy(float)
        resistance_arr = prior_high.to_numpy(float)
        support_arr = prior_low.to_numpy(float)
        atr_arr = atr.to_numpy(float)
        ist_minutes_arr = df["_tfb_v1_17_ist_minutes"].to_numpy(float)

        valid = (
            pd.notna(df["Open"]).to_numpy()
            & pd.notna(df["High"]).to_numpy()
            & pd.notna(df["Low"]).to_numpy()
            & pd.notna(df["Close"]).to_numpy()
            & pd.notna(prior_high).to_numpy()
            & pd.notna(prior_low).to_numpy()
            & pd.notna(atr).to_numpy()
            & pd.notna(df["_tfb_v1_17_ist_minutes"]).to_numpy()
        )
        valid[:warmup] = False
        valid &= (
            (open_arr > 0)
            & (high_arr > 0)
            & (low_arr > 0)
            & (close_arr > 0)
            & (atr_arr > 0)
        )

        blocked = (ist_minutes_arr >= self.block_start_minutes_ist) & (
            ist_minutes_arr < self.block_end_minutes_ist
        )
        eligible = valid & (~blocked)

        raw_long = eligible & self.allow_long & (
            close_arr > resistance_arr + self.min_breakout_points
        )
        raw_short = eligible & self.allow_short & (
            close_arr < support_arr - self.min_breakout_points
        )
        both = raw_long & raw_short
        raw_long[both] = False
        raw_short[both] = False

        raw_signal = pd.Series(0, index=df.index, dtype="int8")
        raw_signal.loc[raw_long] = 1
        raw_signal.loc[raw_short] = -1

        previous_raw_signal = raw_signal.shift(1).fillna(0).astype("int8")
        first_long = raw_long & previous_raw_signal.ne(1).to_numpy()
        first_short = raw_short & previous_raw_signal.ne(-1).to_numpy()
        continuation_long = raw_long & previous_raw_signal.eq(1).to_numpy()
        continuation_short = raw_short & previous_raw_signal.eq(-1).to_numpy()
        first_any = first_long | first_short

        raw_long_count192 = (
            raw_signal.eq(1).shift(1).rolling(192, min_periods=1).sum()
        )

        # Bars since previous raw signal of the same direction.
        bars_since_same = np.full(n, np.nan, dtype=float)
        last_index = {1: None, -1: None}
        raw_arr = raw_signal.to_numpy(np.int8)
        for index, side in enumerate(raw_arr):
            if side in (1, -1):
                previous_index = last_index[int(side)]
                if previous_index is not None:
                    bars_since_same[index] = index - previous_index
                last_index[int(side)] = index
        bars_since_same_signal = pd.Series(bars_since_same, index=df.index)

        # ---------------------------
        # V1.17 Priority-1 features
        # ---------------------------
        candle_upper_wick_atr = (
            df["High"] - pd.concat([df["Open"], df["Close"]], axis=1).max(axis=1)
        ) / atr
        candle_upper_wick_pct = (
            df["High"] - pd.concat([df["Open"], df["Close"]], axis=1).max(axis=1)
        ) / (df["High"] - df["Low"]).replace(0, np.nan)

        close_shift1 = df["Close"].shift(1)
        efficiency12 = (
            (close_shift1 - df["Close"].shift(13)).abs()
            / close_shift1.diff().abs().rolling(12, min_periods=12).sum().replace(0, np.nan)
        )
        efficiency24 = (
            (close_shift1 - df["Close"].shift(25)).abs()
            / close_shift1.diff().abs().rolling(24, min_periods=24).sum().replace(0, np.nan)
        )
        efficiency48 = (
            (close_shift1 - df["Close"].shift(49)).abs()
            / close_shift1.diff().abs().rolling(48, min_periods=48).sum().replace(0, np.nan)
        )
        mom12_atr_5m = (df["Close"] - df["Close"].shift(12)) / atr
        mom24_atr_5m = (df["Close"] - df["Close"].shift(24)) / atr
        mom48_atr_5m = (df["Close"] - df["Close"].shift(48)) / atr
        mom96_atr_5m = (df["Close"] - df["Close"].shift(96)) / atr
        ema20_slope12_atr_5m = (ema20 - ema20.shift(12)) / atr

        # V1.37 structural trend features (known at signal-candle close).
        lr_window = 96
        lr_x = np.arange(lr_window, dtype=float)
        lr_sx = float(lr_x.sum())
        lr_sx2 = float((lr_x * lr_x).sum())
        lr_den_x = float(lr_window * lr_sx2 - lr_sx * lr_sx)
        close_values = df["Close"].to_numpy(float)
        lr_weighted = np.full(len(df), np.nan, dtype=float)
        if len(df) >= lr_window:
            lr_weighted[lr_window - 1 :] = np.convolve(
                np.nan_to_num(close_values, nan=0.0), lr_x[::-1], mode="valid"
            )
        lr_sum_y = df["Close"].rolling(lr_window, min_periods=lr_window).sum().to_numpy(float)
        lr_sum_y2 = (df["Close"] ** 2).rolling(lr_window, min_periods=lr_window).sum().to_numpy(float)
        lr_num = lr_window * lr_weighted - lr_sx * lr_sum_y
        lr_den_y = lr_window * lr_sum_y2 - lr_sum_y * lr_sum_y
        lr_r2_values = np.where(
            lr_den_y > 0,
            (lr_num * lr_num) / (lr_den_x * lr_den_y),
            0.0,
        )
        lr_r2_96_5m = pd.Series(lr_r2_values, index=df.index)
        bb_width40_atr_5m = (
            4.0 * df["Close"].rolling(40, min_periods=40).std() / atr
        )
        atr_slope6_5m = (atr - atr.shift(6)) / atr
        mom192_atr_5m = (df["Close"] - df["Close"].shift(192)) / atr
        typical_price_5m = (df["High"] + df["Low"] + df["Close"]) / 3.0
        cci40_sma_5m = typical_price_5m.rolling(40, min_periods=40).mean()
        cci40_mean_dev_5m = (typical_price_5m - cci40_sma_5m).abs().rolling(40, min_periods=40).mean()
        cci40_5m = (typical_price_5m - cci40_sma_5m) / (0.015 * cci40_mean_dev_5m.replace(0, np.nan))
        candle_range_atr_5m = (df["High"] - df["Low"]) / atr
        ema50_slope24_atr_5m = (ema50 - ema50.shift(24)) / atr

        pre_range96_atr = (
            df["High"].shift(1).rolling(96, min_periods=96).max()
            - df["Low"].shift(1).rolling(96, min_periods=96).min()
        ) / atr

        volume_ratio20 = df["Volume"] / (
            df["Volume"].shift(1).rolling(20, min_periods=20).mean()
        )

        htf_features: dict[str, pd.Series] = {}
        for label, freq, minutes in (
            ("15m", "15min", 15),
            ("30m", "30min", 30),
            ("1h", "1h", 60),
            ("4h", "4h", 240),
            ("1d", "1d", 1440),
        ):
            htf = self._make_htf_features(df, freq, minutes).sort_values("avail_time")
            mapped = pd.merge_asof(
                df[["Date"]].sort_values("Date"),
                htf,
                left_on="Date",
                right_on="avail_time",
                direction="backward",
            )
            for column in htf.columns:
                if column != "avail_time":
                    htf_features[f"{label}_{column}"] = pd.Series(
                        mapped[column].to_numpy(), index=df.index
                    )

        # V1.26 residual-search features already known at signal close.
        pdi_minus_mdi_5m = _pdi_5m - _mdi_5m
        breakout_dist_atr_5m = pd.Series(
            np.where(
                raw_long,
                (close_arr - resistance_arr) / atr_arr,
                np.where(raw_short, (support_arr - close_arr) / atr_arr, np.nan),
            ),
            index=df.index,
        )

        # ---------------------------
        # Existing accepted rejections
        # ---------------------------
        mom6_arr = short_mom6_atr.to_numpy(float)
        range6_arr = pre_range6_atr.to_numpy(float)
        align_arr = bull_ema_align_atr.to_numpy(float)
        vol_ratio_arr = atr_ratio100.to_numpy(float)
        extension_arr = short_ema50_extension_atr.to_numpy(float)

        reject_v112 = (
            first_short
            & pd.notna(short_mom6_atr).to_numpy()
            & pd.notna(pre_range6_atr).to_numpy()
            & (mom6_arr > 1.0)
            & (mom6_arr <= 1.4)
            & (range6_arr <= 1.6)
        )
        reject_v113 = (
            first_short
            & pd.notna(bull_ema_align_atr).to_numpy()
            & pd.notna(atr_ratio100).to_numpy()
            & (align_arr >= 0.4)
            & (align_arr < 1.1)
            & (vol_ratio_arr > 1.18)
            & (vol_ratio_arr <= 1.28)
        )
        reject_v114 = (
            first_short
            & pd.notna(short_ema50_extension_atr).to_numpy()
            & (extension_arr > 1.55)
            & (extension_arr <= 1.95)
        )

        # ---------------------------
        # V1.17: exact ten Priority-1 rejection rules
        # ---------------------------
        r1 = (
            first_any
            & first_long
            & self._between(htf_features["30m_close_location"], 0.8572618269413008, 0.8956614178133462)
            & self._between(htf_features["30m_mom3_atr"], -0.886419396328158, -0.30975667621247244)
        )
        r2 = (
            first_short
            & self._between(bars_since_same_signal, 61.0, 75.0)
            & self._between(efficiency12, 0.178341344816918, 0.23234063972606525)
        )
        r3 = (
            first_short
            & self._between(htf_features["15m_close_location"], 0.06556337317933186, 0.08347107438025599)
            & self._between(pre_range96_atr, 7.916006559865935, 8.78655897250501)
        )
        r4 = (
            first_short
            & self._between(efficiency12, 0.178341344816918, 0.23234063972606525)
            & self._between(bars_since_same_signal, 61.0, 73.0)
        )
        r5 = (
            first_short
            & self._between(htf_features["30m_rsi14"], 58.37656065793341, 60.67642108614787)
            & self._between(htf_features["30m_pdi_minus_mdi"], 16.19556091706551, 21.19328154844283)
        )
        r6 = (
            first_short
            & self._between(htf_features["4h_mom6_atr"], 2.919091409057745, 5.936564162976812)
            & raw_short
            & self._between(htf_features["1h_rsi14"], 58.12597745214375, 63.30441608614863)
        )
        r7 = (
            first_any
            & self._between(candle_upper_wick_atr, 0.03547887404821817, 0.053750738334404406)
            & first_short
            & self._between(htf_features["30m_range_atr"], 1.7153418749158755, 5.7644764595852855)
        )
        r8 = (
            raw_short
            & self._between(candle_upper_wick_atr, 0.03438624692587611, 0.05113855155668282)
            & first_short
            & self._between(htf_features["30m_range_atr"], 1.7153418749158755, 5.7644764595852855)
        )
        r9 = (
            first_short
            & self._between(volume_ratio20, 1.9880513563574103, 2.280898968626277)
            & raw_short
            & self._between(htf_features["1h_rsi14"], 58.12597745214375, 63.30441608614863)
        )
        r10 = (
            raw_short
            & self._between(htf_features["1h_atr14_50_ratio"], 1.0876508592589211, 1.1276073233859578)
            & self._between(htf_features["1h_rsi14"], 58.12597745214375, 63.30441608614863)
        )

        p1_rules = [r1, r2, r3, r4, r5, r6, r7, r8, r9, r10]
        reject_v115 = np.logical_or.reduce(p1_rules)

        # ---------------------------
        # V1.17 residual continuation-SHORT rejection rules
        # ---------------------------
        p2_atr = (
            continuation_short
            & self._between(atr14_atr50_ratio, 0.9695940859494612, 1.0060369987456526)
        )
        p3_1h_ema = (
            continuation_short
            & self._between(htf_features["1h_ema20_50_atr"], 0.8415859851378676, 1.0872990926046842)
        )
        p3_15m_mom = (
            continuation_short
            & self._between(htf_features["15m_mom6_atr"], -0.5507126295462053, -0.3293495432378316)
        )
        p3_daily_mom = (
            continuation_short
            & self._between(htf_features["1d_mom3_atr"], -3.591944402696945, -1.6416009799536282)
        )
        v116_rules = [p2_atr, p3_1h_ema, p3_15m_mom, p3_daily_mom]
        reject_v116 = np.logical_or.reduce(v116_rules)

        # ---------------------------
        # V1.17 strict residual weak-cluster rejection rules
        # ---------------------------
        strict_1 = (
            first_short
            & self._between(mom3_atr_5m, -8.781069456684632, -2.726896216157478)
            & self._between(htf_features["1h_mom3_atr"], -1.4913943099827942, -0.6101269975564185)
        )
        strict_2 = (
            first_short
            & self._between(adx14_5m, 23.216286094244758, 26.154328011551772)
            & self._between(htf_features["1d_eff12"], 0.20777613724249486, 0.36996134337149594)
        )
        strict_3 = (
            first_short
            & self._between(htf_features["30m_pre_range6_atr"], 2.6216878327233455, 2.886978809103166)
            & self._between(htf_features["1d_body_pct"], 0.802516249753787, 0.9856146182521643)
        )
        strict_4 = (
            first_short
            & self._between(htf_features["4h_pre_range6_atr"], 3.8398713086937284, 7.113230694235703)
            & self._between(htf_features["1d_pre_range24_atr"], 3.995795186907818, 4.433587060562459)
        )
        strict_rules = [strict_1, strict_2, strict_3, strict_4]
        reject_v117 = np.logical_or.reduce(strict_rules)

        # ---------------------------
        # V1.19 large residual FIRST-LONG weak-cluster filters
        # ---------------------------
        large_1 = (
            first_long
            & self._between(htf_features["15m_adx14"], 21.671879277066118, 26.4824573428916)
            & self._between(htf_features["4h_range_atr"], 0.7612020412604905, 0.8297001805815998)
        )
        large_2 = (
            first_long
            & self._between(htf_features["1d_mom6_atr"], -5.946772909849992, -1.6114993042936154)
            & self._between(htf_features["15m_range_atr"], 0.8312945146887637, 0.9655841341621829)
        )
        large_rules = [large_1, large_2]
        reject_v119 = np.logical_or.reduce(large_rules)

        # ---------------------------
        # V1.23 strict residual weak-cluster filters (locally verified V1.19 baseline)
        # ---------------------------
        next_1 = (
            first_short
            & self._between(htf_features["1d_ema50_slope12_atr"], 0.8042387809916371, 1.0656475166893475)
            & self._between(htf_features["4h_pdi_minus_mdi"], -2.8245668328962594, 0.4007073105180101)
        )
        next_2 = (
            first_short
            & self._between(htf_features["1d_ema50_slope12_atr"], 0.8042387809916371, 1.0656475166893475)
            & self._between(efficiency12, 0.10682008763205855, 0.15412692993435617)
        )
        next_3 = (
            first_long
            & self._between(htf_features["15m_adx14"], 20.202576054632736, 24.61614637919848)
            & self._between(htf_features["15m_atr14_50_ratio"], 1.0223217000867926, 1.0651227880339968)
        )
        next_4 = (
            first_long
            & self._between(htf_features["15m_adx14"], 21.67187927706612, 24.61614637919848)
            & self._between(htf_features["30m_mom3_atr"], -0.7657313233215812, -0.3022596028088727)
        )
        v123_rules = [next_1, next_2, next_3, next_4]
        reject_v123 = np.logical_or.reduce(v123_rules)

        # ---------------------------
        # V1.24 threshold-robust residual weak-cluster filters
        # ---------------------------
        q1 = (
            first_short
            & self._between(htf_features["30m_pre_range6_atr"], 2.370965508892505, 3.0520396862442833)
            & self._between(ema50_slope24_atr_5m, -0.7227882219979995, -0.17307982121546245)
        )
        q2 = (
            first_long
            & self._between(htf_features["1d_body_pct"], 0.6659175667252488, 0.7836260019459734)
            & self._between(htf_features["4h_ema50_100_atr"], 0.4758055175009494, 0.9566301916084617)
        )
        q3 = (
            first_short
            & self._between(htf_features["1d_pre_range6_atr"], 2.1425887897947824, 2.401835173466111)
            & self._between(mom48_atr_5m, -3.474124669016345, -2.335235986986624)
        )
        q4 = (
            first_long
            & self._between(htf_features["1h_rsi14"], 43.75057407643352, 48.19915311300538)
            & self._between(efficiency48, 0.20714273890741425, 0.27569972622690103)
        )
        q5 = (
            first_short
            & self._between(htf_features["1h_mom12_atr"], 0.7032429055345879, 2.613186978565601)
            & self._between(htf_features["30m_ema20_50_atr"], -1.3818422431895678, -0.7240207918926668)
        )
        v124_rules = [q1, q2, q3, q4, q5]
        reject_v124 = np.logical_or.reduce(v124_rules)

        # ---------------------------
        # V1.25 threshold-robust residual weak-cluster filters
        # ---------------------------
        r125_1 = (
            first_short
            & self._between(htf_features["15m_pre_range12_atr"], 4.787730996831881, 8.268745225015417)
            & self._between(htf_features["1d_atr14_50_ratio"], 1.1771525817207213, 1.349117388712313)
        )
        r125_2 = (
            first_long
            & self._between(htf_features["1h_mom3_atr"], 0.35745543573287225, 0.6374825121942034)
            & self._between(htf_features["30m_body_pct"], 0.09823786394928041, 0.1957493477609033)
        )
        r125_3 = (
            first_short
            & self._between(htf_features["1h_pre_range24_atr"], 5.31350295454218, 5.768018339973772)
            & self._between(htf_features["30m_pdi_minus_mdi"], 16.2653148243728, 53.13743906249327)
        )
        r125_4 = (
            first_short
            & self._between(candle_range_atr_5m, 1.6015545792497634, 1.7953360069796827)
            & self._between(htf_features["15m_body_atr"], 0.21775446149159816, 0.32494260841290096)
        )
        r125_5 = (
            first_long
            & self._between(htf_features["1h_ema50_slope3_atr"], -0.10432798955481132, -0.02484734266787173)
            & self._between(htf_features["1h_atr14_100_ratio"], 0.8101837801845776, 0.8648618600116612)
        )
        v125_rules = [r125_1, r125_2, r125_3, r125_4, r125_5]
        reject_v125 = np.logical_or.reduce(v125_rules)

        # ---------------------------
        # V1.26 threshold-robust residual weak-cluster filters
        # ---------------------------
        r126_1 = (
            first_short
            & self._between(breakout_dist_atr_5m, 0.37011829018592834, 0.5076948776841164)
            & self._between(htf_features["15m_pre_range12_atr"], 3.6593077182769775, 4.0297130)
        )
        r126_2 = (
            first_long
            & self._between(htf_features["1h_mom3_atr"], 0.7967089116573334, 1.3812967538833618)
            & self._between(htf_features["1h_eff12"], 0.27074772119522095, 0.3518402464687824)
        )
        r126_3 = (
            first_short
            & self._between(pdi_minus_mdi_5m, -17.116697788238525, -13.659592151641846)
            & self._between(htf_features["1h_close_location"], 0.15756534412503242, 0.26031504571437836)
        )
        r126_4 = (
            first_short
            & self._between(bull_ema_align_atr, 0.4695834293961525, 0.9608252644538879)
            & self._between(htf_features["1d_atr14_50_ratio"], 1.2745355367660522, 2.209517240524292)
        )
        r126_5 = (
            first_short
            & self._between(htf_features["30m_pre_range12_atr"], 4.7320714592933655, 8.406400680541992)
            & self._between(htf_features["4h_ema50_100_atr"], 0.42851927876472473, 0.8740809559822083)
        )
        v126_rules = [r126_1, r126_2, r126_3, r126_4, r126_5]
        reject_v126 = np.logical_or.reduce(v126_rules)

        # ---------------------------
        # V1.27 robust residual CONTINUATION-SHORT filter
        # ---------------------------
        r127_1 = (
            continuation_short
            & self._between(htf_features["1h_pdi_minus_mdi"], 14.414200305938728, 42.4612922668457)
            & self._between(htf_features["1d_body_atr"], 1.1263068914413452, 2.982048273086548)
        )
        v127_rules = [r127_1]
        reject_v127 = r127_1

        # ---------------------------
        # V1.28 cross-year / walk-forward common-loss filters
        # ---------------------------
        r128_1 = (
            first_long
            & self._between(htf_features["30m_eff12"], 0.4845301151275635, 1.0)
            & self._between(htf_features["4h_rsi14"], 51.9246711730957, 55.54111099243164)
        )
        r128_2 = (
            continuation_long
            & self._between(htf_features["4h_atr14_100_ratio"], 1.0983357429504395, 1.2455777525901794)
            & self._between(htf_features["15m_adx14"], 20.514908599853516, 24.577342987060547)
        )
        r128_3 = (
            continuation_short
            & self._between(candle_close_location_5m, 0.3924613893032074, 0.8718723058700562)
            & self._between(htf_features["4h_ema50_slope3_atr"], -0.20960494577884675, -0.04414771422743797)
        )
        r128_4 = (
            first_short
            & self._between(htf_features["1h_mom6_atr"], -1.419969916343689, -0.9584665596485133)
            & self._between(htf_features["30m_volume_ratio20"], 0.9593228578567505, 1.0638521909713745)
        )
        r128_5 = (
            first_short
            & self._between(ema100_slope12_atr_5m, -0.6960670948028564, -0.4856413602828978)
            & self._between(htf_features["30m_volume_ratio20"], 0.9593228578567505, 1.0638521909713745)
        )
        v128_rules = [r128_1, r128_2, r128_3, r128_4, r128_5]
        reject_v128 = np.logical_or.reduce(v128_rules)

        # ---------------------------
        # V1.29 cross-year residual common-loss filters
        # ---------------------------
        r129_1 = (
            continuation_short
            & self._between(htf_features["30m_range_atr"], 0.1708231568336486, 0.7277669191360474)
            & self._between(htf_features["4h_mom3_atr"], -0.6843645930290222, -0.4295875400304794)
        )
        r129_2 = (
            continuation_short
            & (htf_features["30m_eff12"].to_numpy(float) <= 0.21681896597146988)
            & (candle_upper_wick_pct.to_numpy(float) > 0.3824375420808792)
            & (htf_features["15m_pre_range12_atr"].to_numpy(float) <= 3.217547655105591)
        )
        v129_rules = [r129_1, r129_2]
        reject_v129 = np.logical_or.reduce(v129_rules)

        # ---------------------------
        # V1.30 walk-forward residual common-loss filter
        # ---------------------------
        r130_1 = (
            continuation_long
            & (htf_features["15m_eff12"].to_numpy(float) <= 0.3848053553797234)
            & (htf_features["1h_pre_range48_atr"].to_numpy(float) > 10.320222776393635)
            & (htf_features["1h_eff6"].to_numpy(float) > 0.5920152148320305)
            & (htf_features["4h_adx14"].to_numpy(float) > 23.264788456050365)
        )
        v130_rules = [r130_1]
        reject_v130 = r130_1

        # ---------------------------
        # V1.31 2024+ residual common-loss filter
        # ---------------------------
        r131_1 = (
            first_short
            & self._between(htf_features["30m_pdi_minus_mdi"], -4.750504152434328, -1.480881597690212)
            & self._between(htf_features["1h_pre_range24_atr"], 5.523058714426272, 6.055235350995851)
        )
        reject_v131 = r131_1

        # ---------------------------
        # V1.32 2024+ new-family residual filters
        # ---------------------------
        r132_1 = (
            continuation_long
            & (mom24_atr_5m.to_numpy(float) <= 0.724521816845061)
            & (cci40_5m.to_numpy(float) <= 42.676860081478424)
            & np.isfinite(mom24_atr_5m.to_numpy(float))
            & np.isfinite(cci40_5m.to_numpy(float))
        )
        r132_2 = (
            continuation_long
            & (htf_features["1d_upper_wick_pct"].to_numpy(float) <= 0.04386618253210123)
            & (htf_features["1h_chop28"].to_numpy(float) <= 39.44448064779493)
            & np.isfinite(htf_features["1d_upper_wick_pct"].to_numpy(float))
            & np.isfinite(htf_features["1h_chop28"].to_numpy(float))
        )
        r132_3 = (
            continuation_short
            & self._between(raw_long_count192, 16.0, 21.0)
            & (mom192_atr_5m.to_numpy(float) >= 8.025282314262077)
            & np.isfinite(mom192_atr_5m.to_numpy(float))
        )
        v132_rules = [r132_1, r132_2, r132_3]
        reject_v132 = r132_1 | r132_2 | r132_3

        # ---------------------------
        # V1.33-V1.37 residual filters researched with 90%@1.70R + 10%@2R
        # ---------------------------
        r133_1 = (
            continuation_short
            & np.isfinite(htf_features["1d_rsi14"].to_numpy(float))
            & (htf_features["1d_rsi14"].to_numpy(float) >= 82.0)
        )
        reject_v133 = r133_1

        r134_1 = (
            continuation_long
            & np.isfinite(mom96_atr_5m.to_numpy(float))
            & (mom96_atr_5m.to_numpy(float) >= -4.6)
            & (mom96_atr_5m.to_numpy(float) <= -3.7)
        )
        reject_v134 = r134_1

        r135_1 = (
            first_long
            & np.isfinite(htf_features["1h_eff12"].to_numpy(float))
            & (htf_features["1h_eff12"].to_numpy(float) > 0.70)
            & np.isfinite(ema20_slope12_atr_5m.to_numpy(float))
            & (ema20_slope12_atr_5m.to_numpy(float) > 2.10)
        )
        reject_v135 = r135_1

        r136_1 = (
            continuation_long
            & np.isfinite(htf_features["1h_range_atr"].to_numpy(float))
            & (htf_features["1h_range_atr"].to_numpy(float) <= 2.50)
            & np.isfinite(htf_features["4h_pre_range12_atr"].to_numpy(float))
            & (htf_features["4h_pre_range12_atr"].to_numpy(float) > 3.80)
            & np.isfinite(htf_features["1h_mom6_atr"].to_numpy(float))
            & (htf_features["1h_mom6_atr"].to_numpy(float) > 2.30)
        )
        reject_v136 = r136_1

        r137_1 = (
            first_long
            & np.isfinite(lr_r2_96_5m.to_numpy(float))
            & (lr_r2_96_5m.to_numpy(float) > 0.47)
            & np.isfinite(bb_width40_atr_5m.to_numpy(float))
            & (bb_width40_atr_5m.to_numpy(float) <= 3.00)
            & np.isfinite(atr_slope6_5m.to_numpy(float))
            & (atr_slope6_5m.to_numpy(float) <= 0.17)
        )
        reject_v137 = r137_1

        rejected = (
            reject_v112 | reject_v113 | reject_v114 | reject_v115 | reject_v116 |
            reject_v117 | reject_v119 | reject_v123 | reject_v124 | reject_v125 | reject_v126 | reject_v127 | reject_v128 | reject_v129 | reject_v130 | reject_v131 | reject_v132 |
            reject_v133 | reject_v134 | reject_v135 | reject_v136 | reject_v137
        )

        effective_signal = raw_signal.to_numpy(copy=True)
        effective_signal[rejected] = 0
        df["Position"] = effective_signal
        df["signal"] = effective_signal

        long_mask = effective_signal == 1
        short_mask = effective_signal == -1
        stop_arr = pd.Series(float("nan"), index=df.index, dtype=float)
        stop_arr.loc[long_mask] = close_arr[long_mask] - atr_arr[long_mask] * self.atr_multiplier
        stop_arr.loc[short_mask] = close_arr[short_mask] + atr_arr[short_mask] * self.atr_multiplier
        df["strategy_stop_loss"] = stop_arr
        df["strategy_target"] = float("nan")

        # ---------------------------
        # Diagnostics
        # ---------------------------
        level = pd.Series(float("nan"), index=df.index, dtype=float)
        level.loc[long_mask] = resistance_arr[long_mask]
        level.loc[short_mask] = support_arr[short_mask]
        breakout_distance = pd.Series(float("nan"), index=df.index, dtype=float)
        breakout_distance.loc[long_mask] = close_arr[long_mask] - resistance_arr[long_mask]
        breakout_distance.loc[short_mask] = support_arr[short_mask] - close_arr[short_mask]

        df["tfb_v1_17_type"] = None
        df.loc[long_mask, "tfb_v1_17_type"] = "BREAKOUT_LONG"
        df.loc[short_mask, "tfb_v1_17_type"] = "BREAKDOWN_SHORT"
        df["tfb_v1_17_level"] = level
        df["tfb_v1_17_atr"] = atr.where(effective_signal != 0)
        df["tfb_v1_17_breakout_distance"] = breakout_distance
        df["tfb_v1_17_breakout_distance_atr"] = breakout_distance / atr
        df["tfb_v1_17_ist_time"] = None
        df.loc[effective_signal != 0, "tfb_v1_17_ist_time"] = df.loc[
            effective_signal != 0, "_tfb_v1_17_ist_clock"
        ]
        df["tfb_v1_17_first_long"] = first_long
        df["tfb_v1_17_first_short"] = first_short
        df["tfb_v1_17_bars_since_same_signal"] = bars_since_same_signal
        df["tfb_v1_17_efficiency12"] = efficiency12
        df["tfb_v1_17_pre_range96_atr"] = pre_range96_atr
        df["tfb_v1_17_candle_upper_wick_atr"] = candle_upper_wick_atr
        df["tfb_v1_17_volume_ratio20"] = volume_ratio20
        for key, value in htf_features.items():
            if key in {
                "15m_close_location",
                "30m_close_location",
                "30m_range_atr",
                "30m_rsi14",
                "30m_pdi_minus_mdi",
                "30m_mom3_atr",
                "1h_rsi14",
                "1h_atr14_50_ratio",
                "4h_mom6_atr",
            }:
                df[f"tfb_v1_17_{key}"] = value

        for rank, mask in enumerate(p1_rules, 1):
            df[f"tfb_v1_17_p1_reject_{rank}"] = mask
        df["tfb_v1_17_p2_atr_reject"] = p2_atr
        df["tfb_v1_17_p3_1h_ema_reject"] = p3_1h_ema
        df["tfb_v1_17_p3_15m_mom_reject"] = p3_15m_mom
        df["tfb_v1_17_p3_daily_mom_reject"] = p3_daily_mom
        for rank, mask in enumerate(strict_rules, 1):
            df[f"tfb_v1_17_strict_reject_{rank}"] = mask
        for rank, mask in enumerate(large_rules, 1):
            df[f"tfb_v1_19_large_reject_{rank}"] = mask
        for rank, mask in enumerate(v123_rules, 1):
            df[f"tfb_v1_23_reject_{rank}"] = mask
        for rank, mask in enumerate(v124_rules, 1):
            df[f"tfb_v1_24_reject_{rank}"] = mask
        for rank, mask in enumerate(v125_rules, 1):
            df[f"tfb_v1_25_reject_{rank}"] = mask
        for rank, mask in enumerate(v126_rules, 1):
            df[f"tfb_v1_26_reject_{rank}"] = mask
        df["tfb_v1_27_reject_1"] = r127_1
        for rank, mask in enumerate(v128_rules, 1):
            df[f"tfb_v1_28_reject_{rank}"] = mask
        df["tfb_v1_30_reject_1"] = r130_1
        df["tfb_v1_31_reject_1"] = r131_1
        for rank, mask in enumerate(v132_rules, 1):
            df[f"tfb_v1_32_reject_{rank}"] = mask
        df["tfb_v1_33_reject_1"] = r133_1
        df["tfb_v1_34_reject_1"] = r134_1
        df["tfb_v1_35_reject_1"] = r135_1
        df["tfb_v1_36_reject_1"] = r136_1
        df["tfb_v1_37_reject_1"] = r137_1
        df["tfb_v1_17_continuation_short"] = continuation_short
        df["tfb_v1_17_atr14_atr50_ratio"] = atr14_atr50_ratio
        df["tfb_v1_17_1h_ema20_50_atr"] = htf_features["1h_ema20_50_atr"]
        df["tfb_v1_17_15m_mom6_atr"] = htf_features["15m_mom6_atr"]
        df["tfb_v1_17_daily_mom3_atr"] = htf_features["1d_mom3_atr"]
        df["tfb_v1_17_efficiency24"] = efficiency24
        df["tfb_v1_17_rejected"] = rejected

        rule_names = np.full(n, None, dtype=object)
        for rank, mask in enumerate(p1_rules, 1):
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = f"P1-{rank}"
                else:
                    rule_names[index] = f"{rule_names[index]}+P1-{rank}"
        for label, mask in (
            ("P2-ATR", p2_atr),
            ("P3-1H-EMA", p3_1h_ema),
            ("P3-15M-MOM", p3_15m_mom),
            ("P3-DAILY-MOM", p3_daily_mom),
        ):
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for rank, mask in enumerate(strict_rules, 1):
            label = f"STRICT-{rank}"
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for rank, mask in enumerate(large_rules, 1):
            label = f"V1.19-LARGE-{rank}"
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for rank, mask in enumerate(v123_rules, 1):
            label = f"V1.23-STRICT-{rank}"
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for rank, mask in enumerate(v124_rules, 1):
            label = f"V1.24-ROBUST-{rank}"
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for rank, mask in enumerate(v125_rules, 1):
            label = f"V1.25-ROBUST-{rank}"
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for rank, mask in enumerate(v126_rules, 1):
            label = f"V1.26-ROBUST-{rank}"
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for rank, mask in enumerate(v127_rules, 1):
            label = f"V1.27-ROBUST-{rank}"
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for rank, mask in enumerate(v128_rules, 1):
            label = f"V1.29-WALKFORWARD-{rank}"
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for rank, mask in enumerate(v132_rules, 1):
            label = f"V1.32-2024PLUS-{rank}"
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for label, mask in (
            ("V1.33-DAILY-RSI", r133_1),
            ("V1.34-MOM96", r134_1),
            ("V1.35-FIRST-LONG-TREND", r135_1),
            ("V1.36-2024PLUS-REGIME", r136_1),
            ("V1.37-FIRST-LONG-STRUCTURE", r137_1),
        ):
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        for label, mask in (("V1.12", reject_v112), ("V1.13", reject_v113), ("V1.14", reject_v114)):
            for index in np.flatnonzero(mask):
                if rule_names[index] is None:
                    rule_names[index] = label
                else:
                    rule_names[index] = f"{rule_names[index]}+{label}"
        df["tfb_v1_17_reject_rule"] = rule_names

        reasons = [None] * n
        ist_clock_arr = df["_tfb_v1_17_ist_clock"].to_numpy(object)
        for index in pd.Index(df.index[effective_signal != 0]):
            direction = int(effective_signal[index])
            stop_loss = float(stop_arr.iat[index])
            dist_atr = float(breakout_distance.iat[index] / atr_arr[index])
            ist_time = str(ist_clock_arr[index])
            if direction == 1:
                reasons[index] = (
                    "TFB V1.37 LONG breakout; "
                    f"first_long={bool(first_long[index])}; lookback={self.breakout_lookback}; "
                    f"IST={ist_time}; resistance={resistance_arr[index]:.8f}; "
                    f"close={close_arr[index]:.8f}; breakout_distance_atr={dist_atr:.6f}; "
                    f"ATR({self.atr_period})={atr_arr[index]:.8f}; SL={stop_loss:.8f}; "
                    "accepted_filters=V1.12+V1.13+V1.14+V1.15_P1x10+V1.16_P2P3x4+V1.17_STRICTx4+V1.19_LARGEx2+V1.23_STRICTx4+V1.24_ROBUSTx5+V1.25_ROBUSTx5+V1.26_ROBUSTx5+V1.27_ROBUSTx1+V1.28_WALKFORWARDx5+V1.29_COMMONx2+V1.30_COMMONx1+V1.31_2024PLUSx1+V1.32_2024PLUSx3+V1.33x1+V1.34x1+V1.35x1+V1.36_2024PLUSx1+V1.37x1; "
                    "TP handled by AlgoAgentX RR engine (set RR=2.0)."
                )
            else:
                reasons[index] = (
                    "TFB V1.37 SHORT breakdown; "
                    f"first_short={bool(first_short[index])}; lookback={self.breakout_lookback}; "
                    f"IST={ist_time}; support={support_arr[index]:.8f}; "
                    f"close={close_arr[index]:.8f}; breakout_distance_atr={dist_atr:.6f}; "
                    f"ATR({self.atr_period})={atr_arr[index]:.8f}; SL={stop_loss:.8f}; "
                    "accepted_filters=V1.12+V1.13+V1.14+V1.15_P1x10+V1.16_P2P3x4+V1.17_STRICTx4+V1.19_LARGEx2+V1.23_STRICTx4+V1.24_ROBUSTx5+V1.25_ROBUSTx5+V1.26_ROBUSTx5+V1.27_ROBUSTx1+V1.28_WALKFORWARDx5+V1.29_COMMONx2+V1.30_COMMONx1+V1.31_2024PLUSx1+V1.32_2024PLUSx3+V1.33x1+V1.34x1+V1.35x1+V1.36_2024PLUSx1+V1.37x1; "
                    "TP handled by AlgoAgentX RR engine (set RR=2.0)."
                )
        df["signal_reason"] = reasons

        df.drop(
            columns=["_tfb_v1_17_ist_minutes", "_tfb_v1_17_ist_clock"],
            inplace=True,
            errors="ignore",
        )
        return df


# AlgoAgentX dynamic upload/runtime loader contract.
Strategy = XAUUSD5MTrendBreakoutV137