from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .base_strategy import BaseStrategy


@dataclass
class ResistanceZone:
    zone_id: str
    pivot_index: int
    available_index: int
    zone_low: float
    zone_high: float
    strength: float
    reactions: int = 1
    lifecycle: str = "FRESH"
    broken: bool = False
    consumed: bool = False
    last_interaction_index: Optional[int] = None


@dataclass
class ActiveSetup:
    setup_id: str
    zone: ResistanceZone
    state: str = "RESISTANCE_FOUND"
    interaction_type: Optional[str] = None
    rejection_index: Optional[int] = None
    rejection_high: Optional[float] = None
    rejection_low: Optional[float] = None
    sweep_high: Optional[float] = None
    expires_at: Optional[int] = None


class XAUUSD5MResistanceRejectionV1(BaseStrategy):
    """Single-timeframe XAUUSD 5M resistance-rejection SHORT strategy.

    Backward compatibility: generate() still returns the normal DataFrame with a
    Position column. Strategy diagnostics are added as optional columns and in
    ``DataFrame.attrs['strategy_diagnostics']``.
    """

    def __init__(
        self,
        df,
        swing_left: int = 3,
        swing_right: int = 3,
        zone_width: float = 2.5,
        minimum_reaction: float = 2.0,
        minimum_strength: float = 1.0,
        max_zone_age: int = 180,
        minimum_distance: float = 4.0,
        merge_distance: float = 1.5,
        approach_distance: float = 5.0,
        minimum_body_ratio: float = 0.20,
        minimum_upper_wick_ratio: float = 0.25,
        minimum_zone_penetration: float = 0.05,
        maximum_close_position: float = 0.55,
        entry_confirmation: str = "BREAK_REJECTION_LOW",
        confirmation_bars: int = 4,
        sl_mode: str = "REJECTION_HIGH",
        sl_buffer: float = 0.5,
        fixed_sl_distance: float = 4.0,
        atr_period: int = 14,
        atr_buffer_multiplier: float = 0.25,
        tp_mode: str = "FIXED_RR",
        minimum_rr: float = 1.5,
        target_rr: float = 2.0,
        breakout_rule: str = "CLOSE_ABOVE_ZONE_BY_BUFFER",
        breakout_buffer: float = 0.5,
        breakout_consecutive_closes: int = 2,
        setup_expiry_bars: int = 12,
        debug_mode: bool = False,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.swing_left = max(1, int(swing_left))
        self.swing_right = max(1, int(swing_right))
        self.zone_width = max(0.01, float(zone_width))
        self.minimum_reaction = max(0.0, float(minimum_reaction))
        self.minimum_strength = max(0.0, float(minimum_strength))
        self.max_zone_age = max(1, int(max_zone_age))
        self.minimum_distance = max(0.0, float(minimum_distance))
        self.merge_distance = max(0.0, float(merge_distance))
        self.approach_distance = max(0.0, float(approach_distance))
        self.minimum_body_ratio = max(0.0, min(1.0, float(minimum_body_ratio)))
        self.minimum_upper_wick_ratio = max(0.0, min(1.0, float(minimum_upper_wick_ratio)))
        self.minimum_zone_penetration = max(0.0, min(1.0, float(minimum_zone_penetration)))
        self.maximum_close_position = max(0.0, min(1.0, float(maximum_close_position)))
        self.entry_confirmation = str(entry_confirmation or "BREAK_REJECTION_LOW").upper()
        self.confirmation_bars = max(1, int(confirmation_bars))
        self.sl_mode = str(sl_mode or "REJECTION_HIGH").upper()
        self.sl_buffer = max(0.0, float(sl_buffer))
        self.fixed_sl_distance = max(0.01, float(fixed_sl_distance))
        self.atr_period = max(2, int(atr_period))
        self.atr_buffer_multiplier = max(0.0, float(atr_buffer_multiplier))
        self.tp_mode = str(tp_mode or "FIXED_RR").upper()
        self.minimum_rr = max(0.01, float(minimum_rr))
        self.target_rr = max(0.01, float(target_rr))
        self.breakout_rule = str(breakout_rule or "CLOSE_ABOVE_ZONE_BY_BUFFER").upper()
        self.breakout_buffer = max(0.0, float(breakout_buffer))
        self.breakout_consecutive_closes = max(1, int(breakout_consecutive_closes))
        self.setup_expiry_bars = max(1, int(setup_expiry_bars))
        self.debug_mode = bool(debug_mode)

        self._diagnostic_rows: List[Dict[str, Any]] = []
        self._rejection_reasons: Dict[str, int] = {}
        self._counts: Dict[str, int] = {
            "total_zones": 0,
            "zone_interactions": 0,
            "rejection_setups": 0,
            "confirmed_setups": 0,
            "executed_trades": 0,
            "rejected_setups": 0,
        }

    @staticmethod
    def _safe_range(row: pd.Series) -> float:
        return max(0.0, float(row["High"]) - float(row["Low"]))

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        prev_close = df["Close"].shift(1)
        tr = pd.concat(
            [
                df["High"] - df["Low"],
                (df["High"] - prev_close).abs(),
                (df["Low"] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.rolling(self.atr_period, min_periods=1).mean()

    def _is_swing_high(self, df: pd.DataFrame, pivot: int) -> bool:
        if pivot < self.swing_left or pivot + self.swing_right >= len(df):
            return False
        high = float(df.iloc[pivot]["High"])
        left = df.iloc[pivot - self.swing_left : pivot]["High"]
        right = df.iloc[pivot + 1 : pivot + 1 + self.swing_right]["High"]
        return high > float(left.max()) and high >= float(right.max())

    def _candidate_zone(self, df: pd.DataFrame, pivot: int, available: int, sequence: int) -> Optional[ResistanceZone]:
        high = float(df.iloc[pivot]["High"])
        follow = df.iloc[pivot + 1 : min(len(df), pivot + 1 + max(self.swing_right, 2))]
        reaction = high - float(follow["Low"].min()) if not follow.empty else 0.0
        if reaction < self.minimum_reaction:
            return None
        strength = reaction / max(self.zone_width, 1e-9)
        if strength < self.minimum_strength:
            return None
        half = self.zone_width / 2.0
        return ResistanceZone(
            zone_id=f"RRZ-{sequence:05d}",
            pivot_index=pivot,
            available_index=available,
            zone_low=high - half,
            zone_high=high + half,
            strength=float(strength),
        )

    def _merge_or_add(self, zones: List[ResistanceZone], candidate: ResistanceZone) -> bool:
        center = (candidate.zone_low + candidate.zone_high) / 2.0
        for zone in reversed(zones):
            if zone.broken or zone.consumed:
                continue
            zcenter = (zone.zone_low + zone.zone_high) / 2.0
            if abs(center - zcenter) <= self.merge_distance:
                zone.zone_low = min(zone.zone_low, candidate.zone_low)
                zone.zone_high = max(zone.zone_high, candidate.zone_high)
                zone.reactions += 1
                zone.strength = max(zone.strength, candidate.strength) + 0.25
                return False
        zones.append(candidate)
        self._counts["total_zones"] += 1
        return True

    def _zone_breakout(self, df: pd.DataFrame, i: int, zone: ResistanceZone) -> bool:
        close = float(df.iloc[i]["Close"])
        if self.breakout_rule == "CLOSE_ABOVE_ZONE":
            return close > zone.zone_high
        if self.breakout_rule == "CONSECUTIVE_CLOSES_ABOVE":
            n = self.breakout_consecutive_closes
            if i - n + 1 < 0:
                return False
            closes = df.iloc[i - n + 1 : i + 1]["Close"]
            return bool((closes > zone.zone_high).all())
        return close > zone.zone_high + self.breakout_buffer

    def _interaction(self, row: pd.Series, zone: ResistanceZone) -> Optional[str]:
        high, low, close = float(row["High"]), float(row["Low"]), float(row["Close"])
        if high < zone.zone_low or low > zone.zone_high + self.breakout_buffer:
            return None
        if high > zone.zone_high and close < zone.zone_low:
            return "SWEEP"
        if close < zone.zone_low and high >= zone.zone_low:
            return "REJECTION"
        return "TOUCH"

    def _rejection(self, row: pd.Series, zone: ResistanceZone) -> bool:
        high, low, open_, close = map(float, (row["High"], row["Low"], row["Open"], row["Close"]))
        rng = max(high - low, 1e-9)
        body = abs(close - open_)
        upper_wick = high - max(open_, close)
        body_ratio = body / rng
        upper_wick_ratio = upper_wick / rng
        close_position = (close - low) / rng
        penetration = max(0.0, high - zone.zone_low) / max(zone.zone_high - zone.zone_low, 1e-9)
        failed_higher = close < zone.zone_low
        candle_shape = body_ratio >= self.minimum_body_ratio or upper_wick_ratio >= self.minimum_upper_wick_ratio
        return bool(
            high >= zone.zone_low
            and failed_higher
            and candle_shape
            and penetration >= self.minimum_zone_penetration
            and close_position <= self.maximum_close_position
        )

    def _record_rejection(self, reason: str) -> None:
        key = str(reason)
        self._counts["rejected_setups"] += 1
        self._rejection_reasons[key] = self._rejection_reasons.get(key, 0) + 1

    def _sl(self, df: pd.DataFrame, i: int, setup: ActiveSetup) -> float:
        entry = float(df.iloc[i]["Close"])
        if self.sl_mode == "SWEEP_HIGH" and setup.sweep_high is not None:
            return float(setup.sweep_high) + self.sl_buffer
        if self.sl_mode == "ZONE_HIGH":
            return float(setup.zone.zone_high) + self.sl_buffer
        if self.sl_mode == "FIXED_DISTANCE":
            return entry + self.fixed_sl_distance
        if self.sl_mode == "ATR_BUFFER":
            atr = float(df.iloc[i].get("_rr_atr", 0.0) or 0.0)
            base = float(setup.rejection_high or setup.zone.zone_high)
            return base + (atr * self.atr_buffer_multiplier) + self.sl_buffer
        return float(setup.rejection_high or setup.zone.zone_high) + self.sl_buffer

    def _tp(self, df: pd.DataFrame, i: int, entry: float, sl: float) -> float:
        risk = sl - entry
        if self.tp_mode in {"PREVIOUS_SUPPORT", "SWING_LOW", "LIQUIDITY_TARGET"}:
            lookback = df.iloc[max(0, i - 40) : i]
            if not lookback.empty:
                structural = float(lookback["Low"].min())
                if structural < entry:
                    return structural
        return entry - risk * self.target_rr

    def _emit_diag(self, df: pd.DataFrame, i: int, setup: ActiveSetup, decision: str, reason: Optional[str], rr: Optional[float] = None, entry: Optional[float] = None, sl: Optional[float] = None, tp: Optional[float] = None) -> None:
        self._diagnostic_rows.append(
            {
                "setup_id": setup.setup_id,
                "zone_id": setup.zone.zone_id,
                "timestamp": pd.Timestamp(df.iloc[i]["Date"]).isoformat(),
                "direction": "SHORT",
                "state": setup.state,
                "zone_low": float(setup.zone.zone_low),
                "zone_high": float(setup.zone.zone_high),
                "zone_strength": float(setup.zone.strength),
                "interaction_type": setup.interaction_type,
                "rejection_detected": setup.rejection_index is not None,
                "confirmation_detected": decision == "SHORT",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "rr": rr,
                "final_decision": decision,
                "rejection_reason": reason,
            }
        )

    def generate(self):
        df = self.df.copy()
        required = ["Date", "Open", "High", "Low", "Close"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        df["Date"] = pd.to_datetime(df["Date"])
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["Position"] = 0
        df["strategy_stop_loss"] = pd.NA
        df["strategy_target"] = pd.NA
        df["signal_reason"] = pd.NA
        df["rr_setup_id"] = pd.NA
        df["rr_zone_id"] = pd.NA
        df["rr_state"] = "WAITING"
        df["rr_interaction"] = pd.NA
        df["rr_zone_low"] = pd.NA
        df["rr_zone_high"] = pd.NA
        df["_rr_atr"] = self._atr(df)

        zones: List[ResistanceZone] = []
        active: Optional[ActiveSetup] = None
        zone_sequence = 0
        setup_sequence = 0

        for i in range(len(df)):
            # Confirm a historical swing only after swing_right bars have closed.
            pivot = i - self.swing_right
            if self._is_swing_high(df, pivot):
                zone_sequence += 1
                candidate = self._candidate_zone(df, pivot, i, zone_sequence)
                if candidate is not None:
                    self._merge_or_add(zones, candidate)

            # Lifecycle and clean breakout invalidation.
            for zone in zones:
                if zone.broken or zone.consumed:
                    continue
                age = i - zone.available_index
                if age > self.max_zone_age:
                    zone.lifecycle = "EXPIRED"
                    continue
                if self._zone_breakout(df, i, zone):
                    zone.broken = True
                    zone.lifecycle = "BROKEN"
                    if active and active.zone.zone_id == zone.zone_id:
                        active.state = "ZONE_BROKEN"
                        self._record_rejection("BREAKOUT")
                        self._emit_diag(df, i, active, "NO_TRADE", "BREAKOUT")
                        active = None

            if active is not None:
                zone = active.zone
                if zone.broken or zone.consumed:
                    active = None
                    continue
                if active.expires_at is not None and i > active.expires_at:
                    active.state = "SETUP_EXPIRED"
                    self._record_rejection("ZONE_EXPIRED")
                    self._emit_diag(df, i, active, "NO_TRADE", "ZONE_EXPIRED")
                    active = None
                    continue

                if active.state == "REJECTION_DETECTED":
                    confirmed = False
                    if self.entry_confirmation == "REJECTION_CLOSE":
                        confirmed = i == active.rejection_index
                    elif i > int(active.rejection_index or i) and i <= int(active.rejection_index or i) + self.confirmation_bars:
                        confirmed = float(df.iloc[i]["Low"]) < float(active.rejection_low)
                    if confirmed:
                        active.state = "ENTRY_CONFIRMATION"
                        self._counts["confirmed_setups"] += 1
                        entry = float(df.iloc[i]["Close"])
                        sl = self._sl(df, i, active)
                        if sl <= entry:
                            self._record_rejection("RR_TOO_LOW")
                            self._emit_diag(df, i, active, "NO_TRADE", "RR_TOO_LOW", entry=entry, sl=sl)
                            active = None
                            continue
                        tp = self._tp(df, i, entry, sl)
                        risk = abs(sl - entry)
                        reward = abs(entry - tp)
                        rr = reward / risk if risk > 0 else 0.0
                        if rr < self.minimum_rr:
                            active.state = "RR_INVALID"
                            self._record_rejection("RR_TOO_LOW")
                            self._emit_diag(df, i, active, "NO_TRADE", "RR_TOO_LOW", rr=rr, entry=entry, sl=sl, tp=tp)
                            active = None
                            continue
                        df.at[df.index[i], "Position"] = -1
                        df.at[df.index[i], "strategy_stop_loss"] = sl
                        df.at[df.index[i], "strategy_target"] = tp
                        df.at[df.index[i], "signal_reason"] = f"Resistance rejection {active.interaction_type}; {self.entry_confirmation}"
                        df.at[df.index[i], "rr_setup_id"] = active.setup_id
                        df.at[df.index[i], "rr_zone_id"] = zone.zone_id
                        df.at[df.index[i], "rr_state"] = "SHORT_ENTRY"
                        df.at[df.index[i], "rr_interaction"] = active.interaction_type
                        df.at[df.index[i], "rr_zone_low"] = zone.zone_low
                        df.at[df.index[i], "rr_zone_high"] = zone.zone_high
                        self._counts["executed_trades"] += 1
                        active.state = "SHORT_ENTRY"
                        self._emit_diag(df, i, active, "SHORT", None, rr=rr, entry=entry, sl=sl, tp=tp)
                        zone.consumed = True
                        zone.lifecycle = "RETESTED"
                        active.state = "SETUP_CONSUMED"
                        active = None
                    elif i >= int(active.rejection_index or i) + self.confirmation_bars:
                        active.state = "REJECTION_FAILED"
                        self._record_rejection("NO_ENTRY_CONFIRMATION")
                        self._emit_diag(df, i, active, "NO_TRADE", "NO_ENTRY_CONFIRMATION")
                        active = None
                    continue

            if active is None:
                close = float(df.iloc[i]["Close"])
                # Prefer the nearest valid overhead zone that price approaches from below.
                candidates = [
                    z for z in zones
                    if not z.broken and not z.consumed and z.lifecycle != "EXPIRED"
                    and i >= z.available_index
                    and close <= z.zone_high + self.breakout_buffer
                    and (z.zone_low - self.approach_distance) <= close <= (z.zone_high + self.breakout_buffer)
                ]
                candidates.sort(key=lambda z: abs(z.zone_low - close))
                for zone in candidates:
                    interaction = self._interaction(df.iloc[i], zone)
                    if interaction is None:
                        continue
                    self._counts["zone_interactions"] += 1
                    zone.last_interaction_index = i
                    zone.lifecycle = "ACTIVE" if zone.reactions <= 1 else "RETESTED"
                    setup_sequence += 1
                    active = ActiveSetup(
                        setup_id=f"SR-{pd.Timestamp(df.iloc[i]['Date']).year:04d}{pd.Timestamp(df.iloc[i]['Date']).month:02d}{pd.Timestamp(df.iloc[i]['Date']).day:02d}-{setup_sequence:04d}",
                        zone=zone,
                        state="ZONE_REACHED",
                        interaction_type=interaction,
                        expires_at=i + self.setup_expiry_bars,
                    )
                    df.at[df.index[i], "rr_setup_id"] = active.setup_id
                    df.at[df.index[i], "rr_zone_id"] = zone.zone_id
                    df.at[df.index[i], "rr_interaction"] = interaction
                    df.at[df.index[i], "rr_zone_low"] = zone.zone_low
                    df.at[df.index[i], "rr_zone_high"] = zone.zone_high
                    if interaction == "TOUCH":
                        df.at[df.index[i], "rr_state"] = "ZONE_REACHED"
                        # Keep watching this setup for a later rejection.
                        active.state = "ZONE_REACHED"
                    elif interaction in {"REJECTION", "SWEEP"} and self._rejection(df.iloc[i], zone):
                        active.state = "REJECTION_DETECTED"
                        active.rejection_index = i
                        active.rejection_high = float(df.iloc[i]["High"])
                        active.rejection_low = float(df.iloc[i]["Low"])
                        active.sweep_high = float(df.iloc[i]["High"]) if interaction == "SWEEP" else None
                        self._counts["rejection_setups"] += 1
                        df.at[df.index[i], "rr_state"] = "REJECTION_DETECTED"
                        if self.entry_confirmation == "REJECTION_CLOSE":
                            # Process close-confirmation on this candle without duplicating setup creation.
                            entry = float(df.iloc[i]["Close"])
                            sl = self._sl(df, i, active)
                            tp = self._tp(df, i, entry, sl)
                            risk = abs(sl - entry)
                            rr = abs(entry - tp) / risk if risk > 0 else 0.0
                            self._counts["confirmed_setups"] += 1
                            if risk > 0 and sl > entry and rr >= self.minimum_rr:
                                df.at[df.index[i], "Position"] = -1
                                df.at[df.index[i], "strategy_stop_loss"] = sl
                                df.at[df.index[i], "strategy_target"] = tp
                                df.at[df.index[i], "signal_reason"] = f"Resistance rejection {interaction}; REJECTION_CLOSE"
                                df.at[df.index[i], "rr_state"] = "SHORT_ENTRY"
                                self._counts["executed_trades"] += 1
                                self._emit_diag(df, i, active, "SHORT", None, rr=rr, entry=entry, sl=sl, tp=tp)
                                zone.consumed = True
                                active = None
                            else:
                                self._record_rejection("RR_TOO_LOW")
                                self._emit_diag(df, i, active, "NO_TRADE", "RR_TOO_LOW", rr=rr, entry=entry, sl=sl, tp=tp)
                                active = None
                    else:
                        # It reached resistance but has not met rejection quality yet.
                        active.state = "ZONE_REACHED"
                        df.at[df.index[i], "rr_state"] = "ZONE_REACHED"
                    break

            # A touch-only active setup may turn into rejection on subsequent candles.
            if active is not None and active.state == "ZONE_REACHED" and i >= (active.zone.last_interaction_index or i):
                interaction = self._interaction(df.iloc[i], active.zone)
                if interaction in {"REJECTION", "SWEEP"} and self._rejection(df.iloc[i], active.zone):
                    active.interaction_type = interaction
                    active.state = "REJECTION_DETECTED"
                    active.rejection_index = i
                    active.rejection_high = float(df.iloc[i]["High"])
                    active.rejection_low = float(df.iloc[i]["Low"])
                    active.sweep_high = float(df.iloc[i]["High"]) if interaction == "SWEEP" else None
                    self._counts["rejection_setups"] += 1
                    df.at[df.index[i], "rr_state"] = "REJECTION_DETECTED"
                    df.at[df.index[i], "rr_interaction"] = interaction

        diagnostics = {
            **self._counts,
            "rejection_reasons": dict(self._rejection_reasons),
            "setups": self._diagnostic_rows if self.debug_mode else [],
            "debug_mode": self.debug_mode,
            "strategy": "XAUUSD 5M Resistance Rejection V1",
        }
        df.attrs["strategy_diagnostics"] = diagnostics
        return df


# Alias makes this class usable by the dynamic/static strategy conventions.
Strategy = XAUUSD5MResistanceRejectionV1
