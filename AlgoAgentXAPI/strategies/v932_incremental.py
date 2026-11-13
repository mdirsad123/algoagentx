"""EXPERIMENTAL fail-closed V9.32 hybrid retained calculation.

Original V9.32 source remains untouched in the DB (and v932_original_db_source).
Retains the stateful V3.5 subsystem; the V4.31B trendline, V8/V9 entry
families, portfolio arbitration, and all V9.32 filters still replay all
retained candles. This IS NOT an O(1) fully incremental implementation.
The operator MUST measure live wall time and full 80K parity before approval.
"""
from __future__ import annotations

import pandas as pd
from .v932_pinned_strategy import V932_FilterOnly_Research
from .v64_hybrid_incremental import XAUUSD5MSupplyDemandRejectionV35CandidateA as StatefulV35
from .v932_trendline_stream import TrendlineCache, activate, deactivate


class Strategy(V932_FilterOnly_Research):
    LIVE_INCREMENTAL_VERSION = 1

    def __init__(self, df, **kwargs):
        super().__init__(df, **kwargs)
        self._v932_engine = None
        self._v932_hor_history = None
        self._v932_raw_history = None
        self._v932_primed = False
        self._v932_cached_hor_history = None
        self._v932_trendline_cache = TrendlineCache()

    def generate(self):
        # Exact frozen source calculation on cold start; no incremental cache.
        if self._v932_primed:
            raise RuntimeError("V932_GENERATE_NOT_PERMITTED_AFTER_PRIME")
        token = activate(self._v932_trendline_cache)
        try:
            result = super().generate()
        finally:
            deactivate(token)
        engine = StatefulV35(self.df)
        horizontal = engine.generate()
        if not getattr(engine, "_live_v35_state", None):
            raise RuntimeError("V932_STATEFUL_V35_PRIME_FAILED")
        # Guard cold parity of the stateful horizontal adaptation against
        # the frozen horizontal component; otherwise don't prime state.
        original_horizontal = self._v932_original_hor_history
        for key in ("Position", "strategy_stop_loss", "strategy_target", "signal_reason"):
            left = original_horizontal[key].reset_index(drop=True)
            right = horizontal[key].reset_index(drop=True)
            if key in ("strategy_stop_loss", "strategy_target"):
                import numpy as np
                if not np.allclose(pd.to_numeric(left, errors="coerce").to_numpy(float),
                                   pd.to_numeric(right, errors="coerce").to_numpy(float),
                                   rtol=0, atol=1e-8, equal_nan=True):
                    raise RuntimeError("V932_HOR_PRIME_PARITY_FAIL_" + key)
            elif not left.equals(right):
                raise RuntimeError("V932_HOR_PRIME_PARITY_FAIL_" + key)
        # Cold original cache was used only for strict horizontal parity.
        del self._v932_original_hor_history
        self._v932_engine = engine
        self._v932_hor_history = horizontal
        self._v932_raw_history = self.df.copy().reset_index(drop=True)
        return result

    def start_live_incremental(self, generated):
        if not isinstance(generated, pd.DataFrame) or generated.empty:
            return False
        if self._v932_engine is None or self._v932_raw_history is None:
            return False
        if len(generated) != len(self._v932_raw_history):
            return False
        self._v932_primed = True
        return True

    def on_closed_candle(self, candle):
        if not self._v932_primed:
            raise RuntimeError("V932_UNPRIMED_STATE")
        c = dict(candle)
        c["Date"] = pd.Timestamp(c["Date"])
        for key in ("Open", "High", "Low", "Close"):
            c[key] = float(c[key])
        c["Volume"] = float(c.get("Volume", 0))
        previous = pd.Timestamp(self._v932_raw_history.iloc[-1]["Date"])
        if c["Date"] != previous + pd.Timedelta(minutes=5):
            raise RuntimeError("V932_NONCONTIGUOUS_INPUT")
        raw = pd.concat([self._v932_raw_history, pd.DataFrame([c])],ignore_index=True)
        new_h = self._v932_engine.advance_live_v35(c)
        hor = pd.concat([self._v932_hor_history, new_h], ignore_index=True)
        self.df = raw
        self._v932_cached_hor_history = hor
        try:
            # This replays V4 trendline, full combination, and V8/V9 filters.
            # It can be slow; DO NOT APPROVE until 80K benchmarks pass.
            token = activate(self._v932_trendline_cache)
            try:
                output = super().generate()
            finally:
                deactivate(token)
        finally:
            self._v932_cached_hor_history = None
        if not pd.Timestamp(output.iloc[-1]["Date"]) == c["Date"]:
            raise RuntimeError("V932_FINAL_ROW_MISMATCH")
        self._v932_raw_history = raw
        self._v932_hor_history = hor
        return output.tail(1).copy()
