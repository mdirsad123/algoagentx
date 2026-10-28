"""Deterministic, source-specific performance patch; no change to V6.4 filters."""
from pathlib import Path
import sys

src=Path(sys.argv[1]).read_text(encoding='utf8')
text=src

def replace_one(original,replacement,description):
    global text
    if text.count(original)!=1:
        raise RuntimeError(f'{description}: expected 1 occurrence, got {text.count(original)}')
    text=text.replace(original,replacement)

replace_one('''    def _is_swing_high(self, df, pivot):
        if pivot < self.swing_left or pivot + self.swing_right >= len(df):
            return False
        value = float(df.iloc[pivot]["High"])
        left = df.iloc[pivot - self.swing_left : pivot]["High"]
        right = df.iloc[pivot + 1 : pivot + 1 + self.swing_right]["High"]
        return value > float(left.max()) and value >= float(right.max())

    def _is_swing_low(self, df, pivot):
        if pivot < self.swing_left or pivot + self.swing_right >= len(df):
            return False
        value = float(df.iloc[pivot]["Low"])
        left = df.iloc[pivot - self.swing_left : pivot]["Low"]
        right = df.iloc[pivot + 1 : pivot + 1 + self.swing_right]["Low"]
        return value < float(left.min()) and value <= float(right.min())
''','''    def _is_swing_high(self, df, pivot):
        if pivot < self.swing_left or pivot + self.swing_right >= len(df):
            return False
        highs = df["High"].to_numpy(copy=False)
        value = float(highs[pivot])
        return value > float(highs[pivot-self.swing_left:pivot].max()) and value >= float(highs[pivot+1:pivot+1+self.swing_right].max())

    def _is_swing_low(self, df, pivot):
        if pivot < self.swing_left or pivot + self.swing_right >= len(df):
            return False
        lows = df["Low"].to_numpy(copy=False)
        value = float(lows[pivot])
        return value < float(lows[pivot-self.swing_left:pivot].min()) and value <= float(lows[pivot+1:pivot+1+self.swing_right].min())
''','swing detection')
replace_one('''    def _candidate_zone(self, df, pivot, available, sequence, side):
        half = self.zone_width / 2.0
        follow_end = min(len(df), pivot + 1 + max(self.swing_right, 2))
        follow = df.iloc[pivot + 1 : follow_end]

        if side == "RESISTANCE":
            pivot_price = float(df.iloc[pivot]["High"])
            reaction = pivot_price - float(follow["Low"].min()) if not follow.empty else 0.0
            prefix = "RRZ"
        else:
            pivot_price = float(df.iloc[pivot]["Low"])
            reaction = float(follow["High"].max()) - pivot_price if not follow.empty else 0.0
            prefix = "SRZ"
''','''    def _candidate_zone(self, df, pivot, available, sequence, side):
        half = self.zone_width / 2.0
        follow_end = min(len(df), pivot + 1 + max(self.swing_right, 2))
        highs = df["High"].to_numpy(copy=False)
        lows = df["Low"].to_numpy(copy=False)
        if side == "RESISTANCE":
            pivot_price = float(highs[pivot])
            follow = lows[pivot+1:follow_end]
            reaction = pivot_price - float(follow.min()) if len(follow) else 0.0
            prefix = "RRZ"
        else:
            pivot_price = float(lows[pivot])
            follow = highs[pivot+1:follow_end]
            reaction = float(follow.max()) - pivot_price if len(follow) else 0.0
            prefix = "SRZ"
''','candidate zone')
replace_one('''    def _zone_breakout(self, df, i, zone):
        close = float(df.iloc[i]["Close"])
        if zone.side == "RESISTANCE":
            if self.breakout_rule == "CLOSE_ABOVE_ZONE":
                return close > zone.zone_high
            if self.breakout_rule == "CONSECUTIVE_CLOSES_ABOVE":
                n = self.breakout_consecutive_closes
                if i - n + 1 < 0:
                    return False
                closes = df.iloc[i - n + 1 : i + 1]["Close"]
                return bool((closes > zone.zone_high).all())
            return close > zone.zone_high + self.breakout_buffer

        if self.breakout_rule == "CONSECUTIVE_CLOSES_ABOVE":
            n = self.breakout_consecutive_closes
            if i - n + 1 < 0:
                return False
            closes = df.iloc[i - n + 1 : i + 1]["Close"]
            return bool((closes < zone.zone_low).all())
        if self.breakout_rule == "CLOSE_ABOVE_ZONE":
            return close < zone.zone_low
        return close < zone.zone_low - self.breakout_buffer
''','''    def _zone_breakout(self, df, i, zone):
        closes = df["Close"].to_numpy(copy=False)
        close = float(closes[i])
        if zone.side == "RESISTANCE":
            if self.breakout_rule == "CLOSE_ABOVE_ZONE":
                return close > zone.zone_high
            if self.breakout_rule == "CONSECUTIVE_CLOSES_ABOVE":
                n = self.breakout_consecutive_closes
                if i - n + 1 < 0:
                    return False
                return bool((closes[i-n+1:i+1] > zone.zone_high).all())
            return close > zone.zone_high + self.breakout_buffer
        if self.breakout_rule == "CONSECUTIVE_CLOSES_ABOVE":
            n = self.breakout_consecutive_closes
            if i - n + 1 < 0:
                return False
            return bool((closes[i-n+1:i+1] < zone.zone_low).all())
        if self.breakout_rule == "CLOSE_ABOVE_ZONE":
            return close < zone.zone_low
        return close < zone.zone_low - self.breakout_buffer
''','breakout')
start=text.index('    def _attach_15m_context(self, df, source_minutes):')
end=text.index('    def _update_internal_trade(self, df, i):',start)
text=text[:start]+'''    def _attach_15m_context(self, df, source_minutes):
        df["htf_15m_bias"] = "NEUTRAL"
        df["htf_15m_structure_reason"] = "INSUFFICIENT_CONFIRMED_SWINGS"
        names = ("last_swing_high", "previous_swing_high", "last_swing_low", "previous_swing_low")
        for name in names:
            df["htf_15m_" + name] = pd.NA
        if not self.htf_context_enabled:
            df["htf_15m_structure_reason"] = "HTF_CONTEXT_DISABLED"
            return df
        htf = self._build_complete_15m(df, source_minutes)
        self._htf_bar_count = len(htf)
        if htf.empty:
            return df
        snapshots = self._build_15m_structure_snapshots(htf)
        # Search the same <= available_time boundary as the original pointer
        # loop. All inputs are existing CLOSED HTF bars; no look-ahead.
        import numpy as _np
        available = pd.to_datetime([s["available_time"] for s in snapshots], utc=True).asi8
        decisions = pd.to_datetime(df["Date"], utc=True).astype("int64").to_numpy() + int(source_minutes) * 60_000_000_000
        indices = _np.searchsorted(available, decisions, side="right") - 1
        if bool((indices >= 0).any()):
            snap_rows = [snapshots[int(i)] if i >= 0 else None for i in indices]
            df["htf_15m_bias"] = [s["bias"] if s else "NEUTRAL" for s in snap_rows]
            df["htf_15m_structure_reason"] = [s["reason"] if s else "INSUFFICIENT_CONFIRMED_SWINGS" for s in snap_rows]
            for name in names:
                df["htf_15m_" + name] = [s[name] if (s and s[name] is not None) else pd.NA for s in snap_rows]
        return df


'''+text[end:]
# dead zone compaction: broken/consumed zones cannot reenter _merge_or_add or _find_candidate_zone;
# do not prune EXPIRED because they participate in legacy merge logic.
replace_one('''            current_month = self._month_key_from_timestamp(ts)

            self._update_internal_trade(df, i)''','''            current_month = self._month_key_from_timestamp(ts)
            if (i & 63) == 0 and zones:
                zones = [z for z in zones if not (z.broken or z.consumed)]

            self._update_internal_trade(df, i)''','remove dead zones only')
Path(sys.argv[2]).write_text(text,encoding='utf8')
print('generated optimized strategy, source bytes',len(text))
