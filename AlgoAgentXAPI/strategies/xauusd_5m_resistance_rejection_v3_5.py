# AlgoAgentX Dynamic DB compatible source
# XAUUSD 5M Support/Resistance Rejection V3.5 Candidate A
#
# Research branch only. V2.8 remains the frozen production/forward baseline.
# V3.1 Candidate A removes only original V1.22-family entries (not Proposals A-D)
# when 0.10 <= rejection wick ratio < 0.40 and
# 0.60 <= confirmation displacement < 0.80.
# V3.2 Candidate A additionally removes SHORT entries when
# 10 <= zone age < 30 and 0.30 <= confirmation displacement < 0.50.
# V3.3 Candidate A removes REJECTION entries when
# 1.50 <= zone strength < 3.00 and 0.40 <= rejection close < 0.60.
# V3.4 Candidate A additionally removes LONG entries when
# 0.50 <= rejection body ratio < 0.80 and
# 0.30 <= rejection close position < 0.50.
# Set v3_4_candidate_a_filter=False to reproduce V3.3 Candidate A.
# Set v3_4_candidate_a_start_year=2025 for the recent-only variant.
# V3.5 Candidate A additionally removes SHORT BASE/non-expansion entries when
# 3 <= zone age < 5 bars. Proposal A-D whitelisted entries are NOT affected.
# This applies to both REJECTION and SWEEP interactions when they are BASE.
# Set v3_5_candidate_a_filter=False to reproduce V3.4 Candidate A exactly.
#
# Frozen baseline: V1.22-LS. V2.6 combines three controlled expansions:
# Proposal A: SHORT + 15M BEARISH + REJECTION + 0.50 <= rbody < 0.70.
# Proposal B: LONG + 15M BULLISH + REJECTION + 40 <= zone age < 60.
# Proposal C: SHORT + 15M BEARISH + REJECTION + 15 <= zone age < 30,
#             excluding setups already admitted by Proposal A.
# Proposal D: LONG + 15M BEARISH + REJECTION
#             + 0.60 <= confirmation displacement < 0.80.
# Every other V1.22 rule remains intact.
#
# Built directly from the tested V1.8-LS baseline. V1.3 support-room and V1.4 cooldown are NOT included.
#
# Core logic:
#   SHORT: resistance rejection -> confirmation CLOSE below rejection low.
#          Reject when confirmed 15M structure is clearly BULLISH (HH + HL).
#   LONG:  support rejection -> confirmation CLOSE above rejection high.
#          Reject when confirmed 15M structure is clearly BEARISH (LH + LL).
#
# V1.5 baseline retained:
#   1) NO monthly/daily trade cap by default. Every valid setup can be taken.
#   2) LONG and SHORT keep independent pending setup states.
#   3) Regime/interaction quality matching:
#        - 15M NEUTRAL: require normal REJECTION (skip SWEEP).
#        - 15M BULLISH LONG: require SWEEP.
#        - 15M BEARISH SHORT: require SWEEP.
#        - Opposite HTF trend blocks remain from V1.2.
#   This is intended to reduce low-quality setups naturally rather than by a quota.
#
# V1.7 retained:
#   - Neutral SHORT + 15M NEUTRAL + REJECTION requires >=35% resistance penetration.
#
# V1.8 controlled refinement (ONE new entry-quality rule only):
#   - For LONG + 15M NEUTRAL + normal REJECTION only, reject the setup when
#     rejection candle body ratio is >=20% and <30% of the candle range.
#   - Preserve pin-bar style rejections with body <20% when the existing wick
#     requirement qualifies them, and preserve stronger body rejections >=30%.
#   - Rejection reason: WEAK_NEUTRAL_LONG_REJECTION_BODY.
#
# V1.9 controlled refinement (ONE new entry-quality rule only):
#   - For LONG + 15M NEUTRAL + normal REJECTION only, reject setups when
#     the rejection candle has a very large lower wick (>=60% of its range)
#     AND the confirmation close is overextended (>=40% of the rejection
#     candle range above the rejection high).
#   - This targets the four-year weak group identified in V1.8 research.
#   - Rejection reason: OVEREXTENDED_NEUTRAL_LONG_CONFIRMATION.
#
# V1.10 controlled refinement (ONE new entry-quality rule only):
#   - For SHORT + 15M NEUTRAL + normal REJECTION only, reject setups when
#     zone strength is <2.0 AND confirmation displacement is <20%.
#   - V1.9 four-year research found this group negative in 2023, 2024,
#     2025, and 2026 (49 trades: 13 winners, 36 losers).
#   - Rejection reason: WEAK_NEUTRAL_SHORT_CONFIRMATION.
#
# V1.11 controlled refinement (ONE new entry-quality rule only):
#   - For SHORT + 15M NEUTRAL + normal REJECTION only, reject setups when
#     the rejection upper-wick ratio is >=20% and <40% of candle range.
#   - V1.10 four-year research found this band negative in every tested year
#     (90 trades: 22 winners, 68 losers; WR ~24.44%; PF ~0.654).
#   - Rejection reason: AMBIGUOUS_NEUTRAL_SHORT_REJECTION_WICK.
#
# V1.12 controlled refinement (ONE new entry-quality rule only):
#   - For LONG + 15M NEUTRAL + normal REJECTION only, reject setups when
#     zone strength is >=2.0 and <2.5 AND rejection close position <20%.
#   - V1.11 four-year research found this cluster negative in every tested year
#     (66 trades: 16 winners, 50 losers; WR ~24.24%; weak-group PF ~0.65).
#   - Rejection reason: WEAK_MODERATE_STRENGTH_NEUTRAL_LONG_REJECTION.
#
# V1.14 controlled refinement (built from V1.12 baseline):
#   - V1.13 is NOT included because it did not clearly beat V1.12.
#   - For LONG + 15M NEUTRAL + normal REJECTION only, reject setups when:
#       5 <= zone age < 10 bars
#       AND 0.20 <= confirmation displacement < 0.30
#   - V1.13 research identified this cluster as persistently weak
#     (21 trades: 3 winners, 18 losers; WR ~14.29%; weak-group PF ~0.33).
#   - Rejection reason: WEAK_YOUNG_NEUTRAL_LONG_CONFIRMATION.
#
# V1.15 controlled refinement (built from V1.14 baseline):
#   - For LONG + 15M NEUTRAL + normal REJECTION only, reject setups when:
#       1.50 <= zone strength < 2.00
#       AND 0.30 <= rejection lower-wick ratio < 0.40
#   - V1.14 four-year research found this cluster persistently weak
#     (22 trades: 5 winners, 17 losers; WR ~22.73%; weak-group PF ~0.59).
#   - Rejection reason: AMBIGUOUS_MODERATE_NEUTRAL_LONG_REJECTION.
#
# V1.16 FINAL controlled refinement (built from V1.15 baseline):
#   - This is the final planned candle/zone-quality refinement in this research cycle.
#   - For LONG + 15M NEUTRAL + normal REJECTION only, reject setups when:
#       1.00 <= zone strength < 1.50
#       AND 0.20 <= rejection lower-wick ratio < 0.30
#   - V1.15 four-year research found this cluster persistently weak
#     (30 trades: 7 winners, 23 losers; L/W ~3.29; weak-group PF ~0.62).
#   - Rejection reason: WEAK_LOW_STRENGTH_NEUTRAL_LONG_REJECTION.
#
# V1.17 dual refinement (built directly from tested V1.16 baseline):
#   FILTER A - Neutral LONG shallow support interaction:
#     - Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
#     - Reject when 0.50 <= rejection lower-wick ratio < 0.60
#       AND support-zone penetration < 0.20.
#     - V1.16 five-year export: 38 trades, 7 winners, 31 losers,
#       WR ~18.42%, total ~-17R, weak-group PF ~0.45.
#     - Rejection reason: SHALLOW_WICK_NEUTRAL_LONG_REJECTION.
#
#   FILTER B - Neutral SHORT high-body rejection band:
#     - Applies ONLY to SHORT + 15M NEUTRAL + normal REJECTION.
#     - Reject when 0.75 <= rejection body ratio < 0.90.
#     - V1.16 five-year export: 44 trades, 9 winners, 35 losers,
#       WR ~20.45%, total ~-17.09R, weak-group PF ~0.51.
#     - IMPORTANT: body ratio >=0.90 is NOT rejected because that band
#       recovered profitability in the V1.16 sample.
#     - Rejection reason: WEAK_HIGH_BODY_NEUTRAL_SHORT_REJECTION.
#
#   No other entry, HTF, SL, TP, RR, frequency, or execution logic changed.
#
# V1.18 dual refinement (built directly from tested V1.17 baseline):
#   FILTER A - Neutral LONG mid-close + medium penetration cluster:
#     - Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
#     - Reject when 0.40 <= rejection close-position (rclose) < 0.50
#       AND 0.20 <= support-zone penetration < 0.50.
#     - V1.17 five-year export: 37 trades, 4 winners, 33 losers,
#       WR ~10.81%, total ~-25.23R, weak-group R-PF ~0.24.
#     - Negative in every tested year (2022-2026).
#     - Rejection reason: WEAK_MIDCLOSE_NEUTRAL_LONG_REJECTION.
#
#   FILTER B - Older Neutral LONG zone + weak confirmation cluster:
#     - Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
#     - Reject when zone age >= 40 bars
#       AND 0.10 <= confirmation displacement < 0.30.
#     - V1.17 five-year export: 32 trades, 6 winners, 26 losers,
#       WR ~18.75%, total ~-14.15R, weak-group R-PF ~0.46.
#     - Negative in every tested year (2022-2026).
#     - Rejection reason: STALE_WEAK_CONFIRMATION_NEUTRAL_LONG_REJECTION.
#
#   The two V1.18 filters had 63 unique matching V1.17 trades in total
#   (10 winners / 53 losers, ~1:5.3 winner-to-loser ratio).
#
#   No other entry, HTF, SL, TP, RR, frequency, or execution logic changed.
#
# V1.19 dual refinement (built directly from tested V1.18 baseline):
#   FILTER A - Neutral LONG medium penetration + weak confirmation:
#     - Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
#     - Reject when 0.20 <= support-zone penetration < 0.30
#       AND 0.05 <= confirmation displacement < 0.20.
#     - V1.18 five-year export: 24 trades, 4 winners, 20 losers,
#       WR ~16.67%, total ~-11.89R, weak-group R-PF ~0.41.
#     - Negative in every tested year (2022-2026).
#     - Rejection reason: WEAK_MEDIUM_PENETRATION_NEUTRAL_LONG_CONFIRMATION.
#
#   FILTER B - Neutral SHORT weak-body + mid-close rejection:
#     - Applies ONLY to SHORT + 15M NEUTRAL + normal REJECTION.
#     - Reject when 0.20 <= rejection body ratio < 0.40
#       AND 0.30 <= rejection close-position (rclose) < 0.50.
#     - V1.18 five-year export: 25 trades, 4 winners, 21 losers,
#       WR ~16.00%, total ~-13.02R, weak-group R-PF ~0.38.
#     - Negative in every tested year (2022-2026).
#     - Rejection reason: WEAK_BODY_MIDCLOSE_NEUTRAL_SHORT_REJECTION.
#
#   Combined V1.18 sample: 49 unique trades, 8 winners / 41 losers
#   (~1 winner removed for every 5.1 losers), total ~-24.90R.
#
#   No other entry, HTF, SL, TP, RR, frequency, or execution logic changed.
#
# V1.20 dual refinement (built directly from tested V1.19 baseline):
#   FILTER A - Neutral LONG high-body + shallow-penetration rejection:
#     - Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
#     - Reject when 0.70 <= rejection body ratio < 0.90
#       AND 0.10 <= support-zone penetration < 0.20.
#     - V1.19 five-year export: 23 trades, 3 winners, 20 losers,
#       WR ~13.04%, total ~-13.98R, weak-group R-PF ~0.30.
#     - Negative in every year in which it appeared (2022-2025).
#     - Rejection reason: WEAK_HIGH_BODY_SHALLOW_PEN_NEUTRAL_LONG_REJECTION.
#
#   FILTER B - Neutral LONG medium penetration + mid/high confirmation:
#     - Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
#     - Reject when 0.20 <= support-zone penetration < 0.30
#       AND 0.40 <= confirmation displacement < 0.80.
#     - V1.19 five-year export: 24 trades, 4 winners, 20 losers,
#       WR ~16.67%, total ~-11.99R, weak-group R-PF ~0.40.
#     - Negative in every tested year (2022-2026).
#     - Rejection reason: WEAK_MEDIUM_PEN_MIDHIGH_CONFIRM_NEUTRAL_LONG_REJECTION.
#
#   Combined V1.19 sample: 47 unique trades, 7 winners / 40 losers
#   (~1 winner removed for every 5.7 losers), total ~-25.97R.
#
#   No other entry, HTF, SL, TP, RR, frequency, or execution logic changed.
#
# V1.21 dual refinement (built directly from tested V1.20 baseline):
#   FILTER A - Bearish SHORT SWEEP weak close + weak confirmation:
#     - Applies ONLY to SHORT + 15M BEARISH + SWEEP.
#     - Reject when 0.10 <= rejection close-position (rclose) < 0.50
#       AND 0.00 <= confirmation displacement < 0.30.
#     - V1.20 five-year export: 21 trades, 3 winners, 18 losers,
#       WR ~14.29%, total ~-12.02R, winner:loser = 1:6.0.
#     - Rejection reason: WEAK_BEARISH_SHORT_SWEEP_CONFIRMATION.
#
#   FILTER B - Bullish LONG SWEEP weak close + mid confirmation:
#     - Applies ONLY to LONG + 15M BULLISH + SWEEP.
#     - Reject when 0.00 <= rejection close-position (rclose) < 0.40
#       AND 0.40 <= confirmation displacement < 0.60.
#     - V1.20 five-year export: 20 trades, 3 winners, 17 losers,
#       WR ~15.00%, total ~-11.06R, winner:loser ~1:5.67.
#     - Rejection reason: WEAK_BULLISH_LONG_SWEEP_CONFIRMATION.
#
#   Combined V1.20 sample: 41 unique trades, 6 winners / 35 losers
#   (~1 winner removed for every 5.83 losers), total ~-23.08R.
#
#   No other entry, HTF, SL, TP, RR, frequency, or execution logic changed.
#
# V1.22 triple refinement (built directly from tested V1.21 baseline):
#   FILTER A - Neutral LONG deeper penetration + mid confirmation:
#     - Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
#     - Reject when 0.40 <= support-zone penetration < 0.50
#       AND 0.20 <= confirmation displacement < 0.40.
#     - V1.21 five-year export: 15 trades, 2 winners, 13 losers,
#       WR ~13.33%, winner:loser = 1:6.5, total ~-8.96R.
#     - Negative in every tested year (2022-2026).
#     - Rejection reason: WEAK_DEEP_PEN_MID_CONFIRM_NEUTRAL_LONG_REJECTION.
#
#   FILTER B - Neutral LONG weak body + medium/strong zone:
#     - Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
#     - Reject when 0.10 <= rejection body ratio < 0.40
#       AND 2.50 <= zone strength < 4.00.
#     - V1.21 five-year export: 16 trades, 2 winners, 14 losers,
#       WR 12.50%, winner:loser = 1:7.0, total ~-10.18R.
#     - Rejection reason: WEAK_BODY_MID_STRENGTH_NEUTRAL_LONG_REJECTION.
#
#   FILTER C - Neutral LONG middle-age + medium/strong zone:
#     - Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
#     - Reject when 15 <= zone age < 30 bars
#       AND 2.50 <= zone strength < 4.00.
#     - V1.21 five-year export: 20 trades, 3 winners, 17 losers,
#       WR 15.00%, winner:loser ~1:5.67, total ~-11.02R.
#     - Rejection reason: WEAK_AGE_MID_STRENGTH_NEUTRAL_LONG_REJECTION.
#
#   FILTER B and FILTER C overlap on 5 V1.21 trades. Combined unique sample:
#     46 trades, 7 winners / 39 losers, winner:loser ~1:5.57,
#     total ~-25.16R.
#
#   No other entry, HTF, SL, TP, RR, frequency, or execution logic changed.
#
# Previous V1.7 controlled refinement:
#   - For SHORT + 15M NEUTRAL + normal REJECTION only, require the
#     rejection candle to penetrate at least 35% into the resistance zone.
#   - If penetration < 0.35, reject with
#     INSUFFICIENT_RESISTANCE_PENETRATION.
#   - LONG rules, trend-aligned SWEEP rules, RR/SL/TP, HTF structure,
#     uncapped frequency, and all other tested V1.6 behavior remain unchanged.
#
#
# Execution-state note:
#   The strategy keeps one internal research trade open at a time so it can
#   determine closed WIN/LOSS outcomes from candle High/Low and apply the V1.4
#   cooldown consistently. When both SL and TP are touched in the same candle,
#   STOP_FIRST is used by default (conservative and configurable).
#
# HTF source:
#   15M candles are built from the SAME input candles used by the backtest.
#   Only complete 15M candles and confirmed HTF swings are used (no look-ahead).
#
# Sandbox compatibility:
#   pandas only; no __future__, dataclasses, typing, relative imports, reversed().

import pandas as pd


class SRZone:
    def __init__(
        self,
        zone_id,
        side,
        pivot_index,
        available_index,
        zone_low,
        zone_high,
        strength,
        reactions=1,
        lifecycle="FRESH",
        broken=False,
        consumed=False,
        last_interaction_index=None,
    ):
        self.zone_id = zone_id
        self.side = side  # RESISTANCE or SUPPORT
        self.pivot_index = pivot_index
        self.available_index = available_index
        self.zone_low = zone_low
        self.zone_high = zone_high
        self.strength = strength
        self.reactions = reactions
        self.lifecycle = lifecycle
        self.broken = broken
        self.consumed = consumed
        self.last_interaction_index = last_interaction_index


class ActiveSetup:
    def __init__(
        self,
        setup_id,
        zone,
        direction,
        state="ZONE_REACHED",
        interaction_type=None,
        rejection_index=None,
        rejection_high=None,
        rejection_low=None,
        sweep_extreme=None,
        expires_at=None,
    ):
        self.setup_id = setup_id
        self.zone = zone
        self.direction = direction  # SHORT or LONG
        self.state = state
        self.interaction_type = interaction_type
        self.rejection_index = rejection_index
        self.rejection_high = rejection_high
        self.rejection_low = rejection_low
        self.sweep_extreme = sweep_extreme
        self.expires_at = expires_at


class XAUUSD5MSupplyDemandRejectionV35CandidateA:
    LIVE_HISTORY_BARS = 2000

    """V3.5 research candidate built on frozen V3.4 research logic."""

    @staticmethod
    def _day_key_from_timestamp(ts):
        # Sandbox-safe replacement for Timestamp.strftime().
        # pandas Timestamp.strftime() may internally import Python's ``time``
        # module, which AlgoAgentX intentionally blocks in dynamic strategy code.
        return "%04d-%02d-%02d" % (int(ts.year), int(ts.month), int(ts.day))

    @staticmethod
    def _month_key_from_timestamp(ts):
        return "%04d-%02d" % (int(ts.year), int(ts.month))

    @staticmethod
    def _timestamp_text(ts):
        # Diagnostic-only ISO-like timestamp without strftime()/time imports.
        return "%04d-%02d-%02dT%02d:%02d:%02d" % (
            int(ts.year),
            int(ts.month),
            int(ts.day),
            int(ts.hour),
            int(ts.minute),
            int(ts.second),
        )

    def __init__(
        self,
        df,
        swing_left=3,
        swing_right=3,
        zone_width=2.5,
        minimum_reaction=2.0,
        minimum_strength=1.0,
        max_zone_age=180,
        minimum_distance=4.0,
        merge_distance=1.5,
        approach_distance=5.0,
        minimum_body_ratio=0.20,
        minimum_upper_wick_ratio=0.25,
        minimum_lower_wick_ratio=0.25,
        minimum_zone_penetration=0.05,
        maximum_close_position=0.55,
        entry_confirmation="CLOSE_BELOW_REJECTION_LOW",
        long_entry_confirmation="CLOSE_ABOVE_REJECTION_HIGH",
        confirmation_bars=4,
        sl_mode="REJECTION_HIGH",
        sl_buffer=0.5,
        fixed_sl_distance=4.0,
        atr_period=14,
        atr_buffer_multiplier=0.25,
        tp_mode="FIXED_RR",
        minimum_rr=1.5,
        target_rr=2.0,
        breakout_rule="CLOSE_ABOVE_ZONE_BY_BUFFER",
        breakout_buffer=0.5,
        breakout_consecutive_closes=2,
        setup_expiry_bars=12,
        htf_context_enabled=True,
        htf_swing_left=2,
        htf_swing_right=2,
        source_timeframe_minutes=0,
        enable_short=True,
        enable_long=True,
        max_entries_per_month=0,
        max_entries_per_day=0,
        min_bars_between_entries=0,
        regime_interaction_filter=True,
        neutral_short_penetration_filter=True,
        neutral_short_min_penetration=0.35,
        neutral_long_body_filter=True,
        neutral_long_weak_body_min=0.20,
        neutral_long_weak_body_max=0.30,
        neutral_long_overextended_filter=True,
        neutral_long_min_overextended_wick=0.60,
        neutral_long_min_overextended_confirmation=0.40,
        neutral_short_weak_confirmation_filter=True,
        neutral_short_max_weak_zone_strength=2.0,
        neutral_short_max_weak_confirmation_displacement=0.20,
        neutral_short_ambiguous_wick_filter=True,
        neutral_short_ambiguous_wick_min=0.20,
        neutral_short_ambiguous_wick_max=0.40,
        neutral_long_moderate_strength_close_filter=True,
        neutral_long_moderate_strength_min=2.0,
        neutral_long_moderate_strength_max=2.5,
        neutral_long_max_close_position=0.20,
        neutral_long_age_confirmation_filter=True,
        neutral_long_age_confirmation_min_age=5,
        neutral_long_age_confirmation_max_age=10,
        neutral_long_age_confirmation_min_displacement=0.20,
        neutral_long_age_confirmation_max_displacement=0.30,
        neutral_long_ambiguous_moderate_filter=True,
        neutral_long_ambiguous_moderate_min_zone_strength=1.50,
        neutral_long_ambiguous_moderate_max_zone_strength=2.00,
        neutral_long_ambiguous_moderate_min_wick=0.30,
        neutral_long_ambiguous_moderate_max_wick=0.40,
        neutral_long_low_strength_wick_filter=True,
        neutral_long_low_strength_min_zone_strength=1.00,
        neutral_long_low_strength_max_zone_strength=1.50,
        neutral_long_low_strength_min_wick=0.20,
        neutral_long_low_strength_max_wick=0.30,
        # V1.17 FILTER A: shallow Neutral LONG wick + penetration cluster.
        neutral_long_shallow_wick_penetration_filter=True,
        neutral_long_shallow_wick_min=0.50,
        neutral_long_shallow_wick_max=0.60,
        neutral_long_shallow_max_penetration=0.20,
        # V1.17 FILTER B: weak high-body Neutral SHORT band.
        neutral_short_high_body_filter=True,
        neutral_short_high_body_min=0.75,
        neutral_short_high_body_max=0.90,
        # V1.18 FILTER A: weak Neutral LONG mid-close + penetration cluster.
        neutral_long_midclose_penetration_filter=True,
        neutral_long_midclose_min_close=0.40,
        neutral_long_midclose_max_close=0.50,
        neutral_long_midclose_min_penetration=0.20,
        neutral_long_midclose_max_penetration=0.50,
        # V1.18 FILTER B: older Neutral LONG zone + weak confirmation cluster.
        neutral_long_stale_weak_confirmation_filter=True,
        neutral_long_stale_min_zone_age=40,
        neutral_long_stale_min_confirmation_displacement=0.10,
        neutral_long_stale_max_confirmation_displacement=0.30,
        # V1.19 FILTER A: Neutral LONG medium penetration + weak confirmation.
        neutral_long_medium_pen_weak_confirmation_filter=True,
        neutral_long_medium_pen_min_penetration=0.20,
        neutral_long_medium_pen_max_penetration=0.30,
        neutral_long_medium_pen_min_confirmation_displacement=0.05,
        neutral_long_medium_pen_max_confirmation_displacement=0.20,
        # V1.19 FILTER B: Neutral SHORT weak-body + mid-close rejection.
        neutral_short_weak_body_midclose_filter=True,
        neutral_short_weak_body_midclose_min_body=0.20,
        neutral_short_weak_body_midclose_max_body=0.40,
        neutral_short_weak_body_midclose_min_close=0.30,
        neutral_short_weak_body_midclose_max_close=0.50,
        # V1.20 FILTER A: Neutral LONG high body + shallow penetration.
        neutral_long_high_body_shallow_pen_filter=True,
        neutral_long_high_body_shallow_pen_min_body=0.70,
        neutral_long_high_body_shallow_pen_max_body=0.90,
        neutral_long_high_body_shallow_pen_min_penetration=0.10,
        neutral_long_high_body_shallow_pen_max_penetration=0.20,
        # V1.20 FILTER B: Neutral LONG medium penetration + mid/high confirmation.
        neutral_long_medium_pen_midhigh_confirmation_filter=True,
        neutral_long_medium_pen_midhigh_min_penetration=0.20,
        neutral_long_medium_pen_midhigh_max_penetration=0.30,
        neutral_long_medium_pen_midhigh_min_confirmation_displacement=0.40,
        neutral_long_medium_pen_midhigh_max_confirmation_displacement=0.80,
        # V1.21 FILTER A: Bearish SHORT SWEEP weak close + weak confirmation.
        bearish_short_sweep_weak_confirmation_filter=True,
        bearish_short_sweep_min_close=0.10,
        bearish_short_sweep_max_close=0.50,
        bearish_short_sweep_min_confirmation_displacement=0.00,
        bearish_short_sweep_max_confirmation_displacement=0.30,
        # V1.21 FILTER B: Bullish LONG SWEEP weak close + mid confirmation.
        bullish_long_sweep_mid_confirmation_filter=True,
        bullish_long_sweep_min_close=0.00,
        bullish_long_sweep_max_close=0.40,
        bullish_long_sweep_min_confirmation_displacement=0.40,
        bullish_long_sweep_max_confirmation_displacement=0.60,
        # V1.22 FILTER A: Neutral LONG deeper penetration + mid confirmation.
        neutral_long_deep_pen_mid_confirmation_filter=True,
        neutral_long_deep_pen_mid_confirmation_min_penetration=0.40,
        neutral_long_deep_pen_mid_confirmation_max_penetration=0.50,
        neutral_long_deep_pen_mid_confirmation_min_displacement=0.20,
        neutral_long_deep_pen_mid_confirmation_max_displacement=0.40,
        # V1.22 FILTER B: Neutral LONG weak body + medium/strong zone.
        neutral_long_weak_body_mid_strength_filter=True,
        neutral_long_weak_body_mid_strength_min_body=0.10,
        neutral_long_weak_body_mid_strength_max_body=0.40,
        neutral_long_weak_body_mid_strength_min_zone_strength=2.50,
        neutral_long_weak_body_mid_strength_max_zone_strength=4.00,
        # V1.22 FILTER C: Neutral LONG middle-age + medium/strong zone.
        neutral_long_mid_age_mid_strength_filter=True,
        neutral_long_mid_age_mid_strength_min_age=15,
        neutral_long_mid_age_mid_strength_max_age=30,
        neutral_long_mid_age_mid_strength_min_zone_strength=2.50,
        neutral_long_mid_age_mid_strength_max_zone_strength=4.00,
        proposal_a_expansion_enabled=True,
        proposal_a_min_body_ratio=0.50,
        proposal_a_max_body_ratio=0.70,
        proposal_b_expansion_enabled=True,
        proposal_b_min_zone_age=40,
        proposal_b_max_zone_age=60,
        proposal_c_expansion_enabled=True,
        proposal_c_min_zone_age=15,
        proposal_c_max_zone_age=30,
        proposal_d_expansion_enabled=True,
        proposal_d_min_confirmation_displacement=0.60,
        proposal_d_max_confirmation_displacement=0.80,
        v3_1_candidate_a_filter=True,
        v3_1_candidate_a_min_rejection_wick=0.10,
        v3_1_candidate_a_max_rejection_wick=0.40,
        v3_1_candidate_a_min_confirmation_displacement=0.60,
        v3_1_candidate_a_max_confirmation_displacement=0.80,
        v3_2_candidate_a_filter=True,
        v3_2_candidate_a_min_zone_age=10,
        v3_2_candidate_a_max_zone_age=30,
        v3_2_candidate_a_min_confirmation_displacement=0.30,
        v3_2_candidate_a_max_confirmation_displacement=0.50,
        v3_3_candidate_a_filter=True,
        v3_3_candidate_a_min_zone_strength=1.50,
        v3_3_candidate_a_max_zone_strength=3.00,
        v3_3_candidate_a_min_rejection_close=0.40,
        v3_3_candidate_a_max_rejection_close=0.60,
        v3_4_candidate_a_filter=True,
        v3_4_candidate_a_start_year=0,
        v3_4_candidate_a_min_rejection_body=0.50,
        v3_4_candidate_a_max_rejection_body=0.80,
        v3_4_candidate_a_min_rejection_close=0.30,
        v3_4_candidate_a_max_rejection_close=0.50,
        # V3.5 Candidate A: SHORT BASE/non-expansion + young zone (3-4 bars).
        v3_5_candidate_a_filter=True,
        v3_5_candidate_a_min_zone_age=3,
        v3_5_candidate_a_max_zone_age=5,
        cooldown_enabled=False,
        cooldown_after_losses=2,
        cooldown_skip_setups=1,
        intrabar_collision_policy="STOP_FIRST",
        debug_mode=False,
        **kwargs,
    ):
        self.df = df.copy()
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
        self.minimum_lower_wick_ratio = max(0.0, min(1.0, float(minimum_lower_wick_ratio)))
        self.minimum_zone_penetration = max(0.0, min(1.0, float(minimum_zone_penetration)))
        self.maximum_close_position = max(0.0, min(1.0, float(maximum_close_position)))
        self.entry_confirmation = str(entry_confirmation or "CLOSE_BELOW_REJECTION_LOW").upper()
        self.long_entry_confirmation = str(long_entry_confirmation or "CLOSE_ABOVE_REJECTION_HIGH").upper()
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

        self.htf_context_enabled = bool(htf_context_enabled)
        self.htf_swing_left = max(1, int(htf_swing_left))
        self.htf_swing_right = max(1, int(htf_swing_right))
        self.source_timeframe_minutes = max(0, int(source_timeframe_minutes))
        self.htf_timeframe_minutes = 15

        self.enable_short = bool(enable_short)
        self.enable_long = bool(enable_long)
        self.max_entries_per_month = max(0, int(max_entries_per_month))
        self.max_entries_per_day = max(0, int(max_entries_per_day))
        self.min_bars_between_entries = max(0, int(min_bars_between_entries))
        self.regime_interaction_filter = bool(regime_interaction_filter)
        self.neutral_short_penetration_filter = bool(neutral_short_penetration_filter)
        self.neutral_short_min_penetration = max(
            0.0, min(1.0, float(neutral_short_min_penetration))
        )
        self.neutral_long_body_filter = bool(neutral_long_body_filter)
        self.neutral_long_weak_body_min = max(
            0.0, min(1.0, float(neutral_long_weak_body_min))
        )
        self.neutral_long_weak_body_max = max(
            self.neutral_long_weak_body_min,
            min(1.0, float(neutral_long_weak_body_max)),
        )
        self.neutral_long_overextended_filter = bool(neutral_long_overextended_filter)
        self.neutral_long_min_overextended_wick = max(
            0.0, min(1.0, float(neutral_long_min_overextended_wick))
        )
        self.neutral_long_min_overextended_confirmation = max(
            0.0, float(neutral_long_min_overextended_confirmation)
        )
        self.neutral_short_weak_confirmation_filter = bool(
            neutral_short_weak_confirmation_filter
        )
        self.neutral_short_max_weak_zone_strength = max(
            0.0, float(neutral_short_max_weak_zone_strength)
        )
        self.neutral_short_max_weak_confirmation_displacement = max(
            0.0, float(neutral_short_max_weak_confirmation_displacement)
        )
        self.neutral_short_ambiguous_wick_filter = bool(
            neutral_short_ambiguous_wick_filter
        )
        self.neutral_short_ambiguous_wick_min = max(
            0.0, min(1.0, float(neutral_short_ambiguous_wick_min))
        )
        self.neutral_short_ambiguous_wick_max = max(
            self.neutral_short_ambiguous_wick_min,
            min(1.0, float(neutral_short_ambiguous_wick_max)),
        )
        self.neutral_long_moderate_strength_close_filter = bool(
            neutral_long_moderate_strength_close_filter
        )
        self.neutral_long_moderate_strength_min = max(
            0.0, float(neutral_long_moderate_strength_min)
        )
        self.neutral_long_moderate_strength_max = max(
            self.neutral_long_moderate_strength_min,
            float(neutral_long_moderate_strength_max),
        )
        self.neutral_long_max_close_position = max(
            0.0, min(1.0, float(neutral_long_max_close_position))
        )
        self.neutral_long_age_confirmation_filter = bool(
            neutral_long_age_confirmation_filter
        )
        self.neutral_long_age_confirmation_min_age = max(
            0, int(neutral_long_age_confirmation_min_age)
        )
        self.neutral_long_age_confirmation_max_age = max(
            self.neutral_long_age_confirmation_min_age,
            int(neutral_long_age_confirmation_max_age),
        )
        self.neutral_long_age_confirmation_min_displacement = max(
            0.0, float(neutral_long_age_confirmation_min_displacement)
        )
        self.neutral_long_age_confirmation_max_displacement = max(
            self.neutral_long_age_confirmation_min_displacement,
            float(neutral_long_age_confirmation_max_displacement),
        )
        self.neutral_long_ambiguous_moderate_filter = bool(
            neutral_long_ambiguous_moderate_filter
        )
        self.neutral_long_ambiguous_moderate_min_zone_strength = max(
            0.0, float(neutral_long_ambiguous_moderate_min_zone_strength)
        )
        self.neutral_long_ambiguous_moderate_max_zone_strength = max(
            self.neutral_long_ambiguous_moderate_min_zone_strength,
            float(neutral_long_ambiguous_moderate_max_zone_strength),
        )
        self.neutral_long_ambiguous_moderate_min_wick = max(
            0.0, min(1.0, float(neutral_long_ambiguous_moderate_min_wick))
        )
        self.neutral_long_ambiguous_moderate_max_wick = max(
            self.neutral_long_ambiguous_moderate_min_wick,
            min(1.0, float(neutral_long_ambiguous_moderate_max_wick)),
        )
        self.neutral_long_low_strength_wick_filter = bool(
            neutral_long_low_strength_wick_filter
        )
        self.neutral_long_low_strength_min_zone_strength = max(
            0.0, float(neutral_long_low_strength_min_zone_strength)
        )
        self.neutral_long_low_strength_max_zone_strength = max(
            self.neutral_long_low_strength_min_zone_strength,
            float(neutral_long_low_strength_max_zone_strength),
        )
        self.neutral_long_low_strength_min_wick = max(
            0.0, min(1.0, float(neutral_long_low_strength_min_wick))
        )
        self.neutral_long_low_strength_max_wick = max(
            self.neutral_long_low_strength_min_wick,
            min(1.0, float(neutral_long_low_strength_max_wick)),
        )

        # V1.17 FILTER A parameters.
        self.neutral_long_shallow_wick_penetration_filter = bool(
            neutral_long_shallow_wick_penetration_filter
        )
        self.neutral_long_shallow_wick_min = max(
            0.0, min(1.0, float(neutral_long_shallow_wick_min))
        )
        self.neutral_long_shallow_wick_max = max(
            self.neutral_long_shallow_wick_min,
            min(1.0, float(neutral_long_shallow_wick_max)),
        )
        self.neutral_long_shallow_max_penetration = max(
            0.0, min(1.0, float(neutral_long_shallow_max_penetration))
        )

        # V1.17 FILTER B parameters.
        self.neutral_short_high_body_filter = bool(neutral_short_high_body_filter)
        self.neutral_short_high_body_min = max(
            0.0, min(1.0, float(neutral_short_high_body_min))
        )
        self.neutral_short_high_body_max = max(
            self.neutral_short_high_body_min,
            min(1.0, float(neutral_short_high_body_max)),
        )

        # V1.18 FILTER A parameters.
        self.neutral_long_midclose_penetration_filter = bool(
            neutral_long_midclose_penetration_filter
        )
        self.neutral_long_midclose_min_close = max(
            0.0, min(1.0, float(neutral_long_midclose_min_close))
        )
        self.neutral_long_midclose_max_close = max(
            self.neutral_long_midclose_min_close,
            min(1.0, float(neutral_long_midclose_max_close)),
        )
        self.neutral_long_midclose_min_penetration = max(
            0.0, min(1.0, float(neutral_long_midclose_min_penetration))
        )
        self.neutral_long_midclose_max_penetration = max(
            self.neutral_long_midclose_min_penetration,
            min(1.0, float(neutral_long_midclose_max_penetration)),
        )

        # V1.18 FILTER B parameters.
        self.neutral_long_stale_weak_confirmation_filter = bool(
            neutral_long_stale_weak_confirmation_filter
        )
        self.neutral_long_stale_min_zone_age = max(
            0, int(neutral_long_stale_min_zone_age)
        )
        self.neutral_long_stale_min_confirmation_displacement = max(
            0.0, float(neutral_long_stale_min_confirmation_displacement)
        )
        self.neutral_long_stale_max_confirmation_displacement = max(
            self.neutral_long_stale_min_confirmation_displacement,
            float(neutral_long_stale_max_confirmation_displacement),
        )

        # V1.19 FILTER A parameters.
        self.neutral_long_medium_pen_weak_confirmation_filter = bool(
            neutral_long_medium_pen_weak_confirmation_filter
        )
        self.neutral_long_medium_pen_min_penetration = max(
            0.0, min(1.0, float(neutral_long_medium_pen_min_penetration))
        )
        self.neutral_long_medium_pen_max_penetration = max(
            self.neutral_long_medium_pen_min_penetration,
            min(1.0, float(neutral_long_medium_pen_max_penetration)),
        )
        self.neutral_long_medium_pen_min_confirmation_displacement = max(
            0.0, float(neutral_long_medium_pen_min_confirmation_displacement)
        )
        self.neutral_long_medium_pen_max_confirmation_displacement = max(
            self.neutral_long_medium_pen_min_confirmation_displacement,
            float(neutral_long_medium_pen_max_confirmation_displacement),
        )

        # V1.19 FILTER B parameters.
        self.neutral_short_weak_body_midclose_filter = bool(
            neutral_short_weak_body_midclose_filter
        )
        self.neutral_short_weak_body_midclose_min_body = max(
            0.0, min(1.0, float(neutral_short_weak_body_midclose_min_body))
        )
        self.neutral_short_weak_body_midclose_max_body = max(
            self.neutral_short_weak_body_midclose_min_body,
            min(1.0, float(neutral_short_weak_body_midclose_max_body)),
        )
        self.neutral_short_weak_body_midclose_min_close = max(
            0.0, min(1.0, float(neutral_short_weak_body_midclose_min_close))
        )
        self.neutral_short_weak_body_midclose_max_close = max(
            self.neutral_short_weak_body_midclose_min_close,
            min(1.0, float(neutral_short_weak_body_midclose_max_close)),
        )

        # V1.20 FILTER A parameters.
        self.neutral_long_high_body_shallow_pen_filter = bool(
            neutral_long_high_body_shallow_pen_filter
        )
        self.neutral_long_high_body_shallow_pen_min_body = max(
            0.0, min(1.0, float(neutral_long_high_body_shallow_pen_min_body))
        )
        self.neutral_long_high_body_shallow_pen_max_body = max(
            self.neutral_long_high_body_shallow_pen_min_body,
            min(1.0, float(neutral_long_high_body_shallow_pen_max_body)),
        )
        self.neutral_long_high_body_shallow_pen_min_penetration = max(
            0.0, min(1.0, float(neutral_long_high_body_shallow_pen_min_penetration))
        )
        self.neutral_long_high_body_shallow_pen_max_penetration = max(
            self.neutral_long_high_body_shallow_pen_min_penetration,
            min(1.0, float(neutral_long_high_body_shallow_pen_max_penetration)),
        )

        # V1.20 FILTER B parameters.
        self.neutral_long_medium_pen_midhigh_confirmation_filter = bool(
            neutral_long_medium_pen_midhigh_confirmation_filter
        )
        self.neutral_long_medium_pen_midhigh_min_penetration = max(
            0.0, min(1.0, float(neutral_long_medium_pen_midhigh_min_penetration))
        )
        self.neutral_long_medium_pen_midhigh_max_penetration = max(
            self.neutral_long_medium_pen_midhigh_min_penetration,
            min(1.0, float(neutral_long_medium_pen_midhigh_max_penetration)),
        )
        self.neutral_long_medium_pen_midhigh_min_confirmation_displacement = max(
            0.0, float(neutral_long_medium_pen_midhigh_min_confirmation_displacement)
        )
        self.neutral_long_medium_pen_midhigh_max_confirmation_displacement = max(
            self.neutral_long_medium_pen_midhigh_min_confirmation_displacement,
            float(neutral_long_medium_pen_midhigh_max_confirmation_displacement),
        )

        # V1.21 FILTER A parameters.
        self.bearish_short_sweep_weak_confirmation_filter = bool(
            bearish_short_sweep_weak_confirmation_filter
        )
        self.bearish_short_sweep_min_close = max(
            0.0, min(1.0, float(bearish_short_sweep_min_close))
        )
        self.bearish_short_sweep_max_close = max(
            self.bearish_short_sweep_min_close,
            min(1.0, float(bearish_short_sweep_max_close)),
        )
        self.bearish_short_sweep_min_confirmation_displacement = max(
            0.0, float(bearish_short_sweep_min_confirmation_displacement)
        )
        self.bearish_short_sweep_max_confirmation_displacement = max(
            self.bearish_short_sweep_min_confirmation_displacement,
            float(bearish_short_sweep_max_confirmation_displacement),
        )

        # V1.21 FILTER B parameters.
        self.bullish_long_sweep_mid_confirmation_filter = bool(
            bullish_long_sweep_mid_confirmation_filter
        )
        self.bullish_long_sweep_min_close = max(
            0.0, min(1.0, float(bullish_long_sweep_min_close))
        )
        self.bullish_long_sweep_max_close = max(
            self.bullish_long_sweep_min_close,
            min(1.0, float(bullish_long_sweep_max_close)),
        )
        self.bullish_long_sweep_min_confirmation_displacement = max(
            0.0, float(bullish_long_sweep_min_confirmation_displacement)
        )
        self.bullish_long_sweep_max_confirmation_displacement = max(
            self.bullish_long_sweep_min_confirmation_displacement,
            float(bullish_long_sweep_max_confirmation_displacement),
        )

        # V1.22 FILTER A parameters.
        self.neutral_long_deep_pen_mid_confirmation_filter = bool(
            neutral_long_deep_pen_mid_confirmation_filter
        )
        self.neutral_long_deep_pen_mid_confirmation_min_penetration = max(
            0.0, min(1.0, float(neutral_long_deep_pen_mid_confirmation_min_penetration))
        )
        self.neutral_long_deep_pen_mid_confirmation_max_penetration = max(
            self.neutral_long_deep_pen_mid_confirmation_min_penetration,
            min(1.0, float(neutral_long_deep_pen_mid_confirmation_max_penetration)),
        )
        self.neutral_long_deep_pen_mid_confirmation_min_displacement = max(
            0.0, float(neutral_long_deep_pen_mid_confirmation_min_displacement)
        )
        self.neutral_long_deep_pen_mid_confirmation_max_displacement = max(
            self.neutral_long_deep_pen_mid_confirmation_min_displacement,
            float(neutral_long_deep_pen_mid_confirmation_max_displacement),
        )

        # V1.22 FILTER B parameters.
        self.neutral_long_weak_body_mid_strength_filter = bool(
            neutral_long_weak_body_mid_strength_filter
        )
        self.neutral_long_weak_body_mid_strength_min_body = max(
            0.0, min(1.0, float(neutral_long_weak_body_mid_strength_min_body))
        )
        self.neutral_long_weak_body_mid_strength_max_body = max(
            self.neutral_long_weak_body_mid_strength_min_body,
            min(1.0, float(neutral_long_weak_body_mid_strength_max_body)),
        )
        self.neutral_long_weak_body_mid_strength_min_zone_strength = max(
            0.0, float(neutral_long_weak_body_mid_strength_min_zone_strength)
        )
        self.neutral_long_weak_body_mid_strength_max_zone_strength = max(
            self.neutral_long_weak_body_mid_strength_min_zone_strength,
            float(neutral_long_weak_body_mid_strength_max_zone_strength),
        )

        # V1.22 FILTER C parameters.
        self.neutral_long_mid_age_mid_strength_filter = bool(
            neutral_long_mid_age_mid_strength_filter
        )
        self.neutral_long_mid_age_mid_strength_min_age = max(
            0, int(neutral_long_mid_age_mid_strength_min_age)
        )
        self.neutral_long_mid_age_mid_strength_max_age = max(
            self.neutral_long_mid_age_mid_strength_min_age,
            int(neutral_long_mid_age_mid_strength_max_age),
        )
        self.neutral_long_mid_age_mid_strength_min_zone_strength = max(
            0.0, float(neutral_long_mid_age_mid_strength_min_zone_strength)
        )
        self.neutral_long_mid_age_mid_strength_max_zone_strength = max(
            self.neutral_long_mid_age_mid_strength_min_zone_strength,
            float(neutral_long_mid_age_mid_strength_max_zone_strength),
        )

        # V2.2 Proposal A.  This is a whitelist exception only to the existing
        # BEARISH_SHORT_REQUIRES_SWEEP regime rule.  It does not bypass context,
        # risk, position, frequency, or any other V1.22 validation.
        self.proposal_a_expansion_enabled = bool(proposal_a_expansion_enabled)
        self.proposal_a_min_body_ratio = max(
            0.0, min(1.0, float(proposal_a_min_body_ratio))
        )
        self.proposal_a_max_body_ratio = max(
            self.proposal_a_min_body_ratio,
            min(1.0, float(proposal_a_max_body_ratio)),
        )

        # V2.4 Proposal B. This whitelist bypasses only the existing
        # BULLISH_LONG_REQUIRES_SWEEP regime rule.
        self.proposal_b_expansion_enabled = bool(proposal_b_expansion_enabled)
        self.proposal_b_min_zone_age = max(0, int(proposal_b_min_zone_age))
        self.proposal_b_max_zone_age = max(
            self.proposal_b_min_zone_age, int(proposal_b_max_zone_age)
        )

        # V2.6 Proposal C. This age-family exception is evaluated only after
        # Proposal A, keeping A/C attribution mutually exclusive.
        self.proposal_c_expansion_enabled = bool(proposal_c_expansion_enabled)
        self.proposal_c_min_zone_age = max(0, int(proposal_c_min_zone_age))
        self.proposal_c_max_zone_age = max(
            self.proposal_c_min_zone_age, int(proposal_c_max_zone_age)
        )

        self.proposal_d_expansion_enabled = bool(proposal_d_expansion_enabled)
        self.proposal_d_min_confirmation_displacement = max(
            0.0, float(proposal_d_min_confirmation_displacement)
        )
        self.proposal_d_max_confirmation_displacement = max(
            self.proposal_d_min_confirmation_displacement,
            float(proposal_d_max_confirmation_displacement),
        )

        # V3.1 Candidate A. This is deliberately downstream of every frozen
        # V2.8 rule and is limited to entries that did not use Proposals A-D.
        self.v3_1_candidate_a_filter = bool(v3_1_candidate_a_filter)
        self.v3_1_candidate_a_min_rejection_wick = max(
            0.0, min(1.0, float(v3_1_candidate_a_min_rejection_wick))
        )
        self.v3_1_candidate_a_max_rejection_wick = max(
            self.v3_1_candidate_a_min_rejection_wick,
            min(1.0, float(v3_1_candidate_a_max_rejection_wick)),
        )
        self.v3_1_candidate_a_min_confirmation_displacement = max(
            0.0, float(v3_1_candidate_a_min_confirmation_displacement)
        )
        self.v3_1_candidate_a_max_confirmation_displacement = max(
            self.v3_1_candidate_a_min_confirmation_displacement,
            float(v3_1_candidate_a_max_confirmation_displacement),
        )
        self.v3_2_candidate_a_filter = bool(v3_2_candidate_a_filter)
        self.v3_2_candidate_a_min_zone_age = max(
            0, int(v3_2_candidate_a_min_zone_age)
        )
        self.v3_2_candidate_a_max_zone_age = max(
            self.v3_2_candidate_a_min_zone_age,
            int(v3_2_candidate_a_max_zone_age),
        )
        self.v3_2_candidate_a_min_confirmation_displacement = max(
            0.0, float(v3_2_candidate_a_min_confirmation_displacement)
        )
        self.v3_2_candidate_a_max_confirmation_displacement = max(
            self.v3_2_candidate_a_min_confirmation_displacement,
            float(v3_2_candidate_a_max_confirmation_displacement),
        )
        self.v3_3_candidate_a_filter = bool(v3_3_candidate_a_filter)
        self.v3_3_candidate_a_min_zone_strength = max(
            0.0, float(v3_3_candidate_a_min_zone_strength)
        )
        self.v3_3_candidate_a_max_zone_strength = max(
            self.v3_3_candidate_a_min_zone_strength,
            float(v3_3_candidate_a_max_zone_strength),
        )
        self.v3_3_candidate_a_min_rejection_close = max(
            0.0, min(1.0, float(v3_3_candidate_a_min_rejection_close))
        )
        self.v3_3_candidate_a_max_rejection_close = max(
            self.v3_3_candidate_a_min_rejection_close,
            min(1.0, float(v3_3_candidate_a_max_rejection_close)),
        )
        self.v3_4_candidate_a_filter = bool(v3_4_candidate_a_filter)
        self.v3_4_candidate_a_start_year = max(0, int(v3_4_candidate_a_start_year))
        self.v3_4_candidate_a_min_rejection_body = max(
            0.0, min(1.0, float(v3_4_candidate_a_min_rejection_body))
        )
        self.v3_4_candidate_a_max_rejection_body = max(
            self.v3_4_candidate_a_min_rejection_body,
            min(1.0, float(v3_4_candidate_a_max_rejection_body)),
        )
        self.v3_4_candidate_a_min_rejection_close = max(
            0.0, min(1.0, float(v3_4_candidate_a_min_rejection_close))
        )
        self.v3_4_candidate_a_max_rejection_close = max(
            self.v3_4_candidate_a_min_rejection_close,
            min(1.0, float(v3_4_candidate_a_max_rejection_close)),
        )

        # V3.5 Candidate A. Keep the bounds configurable so the research rule
        # can be disabled or adjusted without touching the strategy body.
        self.v3_5_candidate_a_filter = bool(v3_5_candidate_a_filter)
        self.v3_5_candidate_a_min_zone_age = max(0, int(v3_5_candidate_a_min_zone_age))
        self.v3_5_candidate_a_max_zone_age = max(
            self.v3_5_candidate_a_min_zone_age,
            int(v3_5_candidate_a_max_zone_age),
        )

        self.cooldown_enabled = bool(cooldown_enabled)
        self.cooldown_after_losses = max(1, int(cooldown_after_losses))
        self.cooldown_skip_setups = max(1, int(cooldown_skip_setups))
        self.intrabar_collision_policy = str(intrabar_collision_policy or "STOP_FIRST").upper()
        if self.intrabar_collision_policy not in ("STOP_FIRST", "TARGET_FIRST"):
            self.intrabar_collision_policy = "STOP_FIRST"

        self.debug_mode = bool(debug_mode)

        self._diagnostic_rows = []
        self._rejection_reasons = {}
        self._counts = {
            "total_zones": 0,
            "resistance_zones": 0,
            "support_zones": 0,
            "zone_interactions": 0,
            "rejection_setups": 0,
            "confirmed_setups": 0,
            "executed_trades": 0,
            "short_entries": 0,
            "long_entries": 0,
            "rejected_setups": 0,
            "htf_bullish_short_rejections": 0,
            "htf_bearish_long_rejections": 0,
            "daily_cap_rejections": 0,
            "monthly_cap_rejections": 0,
            "spacing_rejections": 0,
            "cooldown_rejections": 0,
            "regime_interaction_rejections": 0,
            "neutral_short_penetration_rejections": 0,
            "neutral_long_weak_body_rejections": 0,
            "neutral_long_overextended_rejections": 0,
            "neutral_short_weak_confirmation_rejections": 0,
            "neutral_short_ambiguous_wick_rejections": 0,
            "neutral_long_moderate_strength_close_rejections": 0,
            "neutral_long_age_confirmation_rejections": 0,
            "neutral_long_ambiguous_moderate_rejections": 0,
            "neutral_long_low_strength_wick_rejections": 0,
            "neutral_long_shallow_wick_penetration_rejections": 0,
            "neutral_short_high_body_rejections": 0,
            "neutral_long_midclose_penetration_rejections": 0,
            "neutral_long_stale_weak_confirmation_rejections": 0,
            "neutral_long_medium_pen_weak_confirmation_rejections": 0,
            "neutral_short_weak_body_midclose_rejections": 0,
            "neutral_long_high_body_shallow_pen_rejections": 0,
            "neutral_long_medium_pen_midhigh_confirmation_rejections": 0,
            "bearish_short_sweep_weak_confirmation_rejections": 0,
            "bullish_long_sweep_mid_confirmation_rejections": 0,
            "neutral_long_deep_pen_mid_confirmation_rejections": 0,
            "neutral_long_weak_body_mid_strength_rejections": 0,
            "neutral_long_mid_age_mid_strength_rejections": 0,
            "internal_trade_wins": 0,
            "internal_trade_losses": 0,
            "proposal_a_whitelisted": 0,
            "proposal_a_executed": 0,
            "proposal_b_whitelisted": 0,
            "proposal_b_executed": 0,
            "proposal_c_whitelisted": 0,
            "proposal_c_executed": 0,
            "proposal_d_whitelisted": 0,
            "proposal_d_executed": 0,
            "v3_1_candidate_a_rejections": 0,
            "v3_2_candidate_a_rejections": 0,
            "v3_3_candidate_a_rejections": 0,
            "v3_4_candidate_a_rejections": 0,
            "v3_5_candidate_a_rejections": 0,
        }

        self._detected_source_timeframe_minutes = None
        self._htf_bar_count = 0
        self._entries_by_day = {}
        self._entries_by_month = {}
        self._last_entry_index = None

        # Internal research execution tracker.
        self._open_trade = None
        self._same_day_loss_streak = 0
        self._loss_streak_day = None
        self._cooldown_remaining = 0

    # --------------------------------------------------------------
    # Basic helpers
    # --------------------------------------------------------------

    def _atr(self, df):
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

    def _is_swing_high(self, df, pivot):
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

    def _candidate_zone(self, df, pivot, available, sequence, side):
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

        if reaction < self.minimum_reaction:
            return None
        strength = reaction / max(self.zone_width, 1e-9)
        if strength < self.minimum_strength:
            return None

        return SRZone(
            zone_id="%s-%05d" % (prefix, sequence),
            side=side,
            pivot_index=pivot,
            available_index=available,
            zone_low=pivot_price - half,
            zone_high=pivot_price + half,
            strength=float(strength),
        )

    def _merge_or_add(self, zones, candidate):
        center = (candidate.zone_low + candidate.zone_high) / 2.0
        j = len(zones) - 1
        while j >= 0:
            zone = zones[j]
            if zone.side == candidate.side and not zone.broken and not zone.consumed:
                zcenter = (zone.zone_low + zone.zone_high) / 2.0
                if abs(center - zcenter) <= self.merge_distance:
                    zone.zone_low = min(zone.zone_low, candidate.zone_low)
                    zone.zone_high = max(zone.zone_high, candidate.zone_high)
                    zone.reactions += 1
                    zone.strength = max(zone.strength, candidate.strength) + 0.25
                    return False
            j -= 1

        zones.append(candidate)
        self._counts["total_zones"] += 1
        if candidate.side == "RESISTANCE":
            self._counts["resistance_zones"] += 1
        else:
            self._counts["support_zones"] += 1
        return True

    def _zone_breakout(self, df, i, zone):
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

        # Symmetric support invalidation.
        if self.breakout_rule == "CONSECUTIVE_CLOSES_ABOVE":
            n = self.breakout_consecutive_closes
            if i - n + 1 < 0:
                return False
            closes = df.iloc[i - n + 1 : i + 1]["Close"]
            return bool((closes < zone.zone_low).all())
        if self.breakout_rule == "CLOSE_ABOVE_ZONE":
            return close < zone.zone_low
        return close < zone.zone_low - self.breakout_buffer

    def _interaction(self, row, zone):
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])

        if zone.side == "RESISTANCE":
            if high < zone.zone_low or low > zone.zone_high + self.breakout_buffer:
                return None
            if high > zone.zone_high and close < zone.zone_low:
                return "SWEEP"
            if close < zone.zone_low and high >= zone.zone_low:
                return "REJECTION"
            return "TOUCH"

        if low > zone.zone_high or high < zone.zone_low - self.breakout_buffer:
            return None
        if low < zone.zone_low and close > zone.zone_high:
            return "SWEEP"
        if close > zone.zone_high and low <= zone.zone_high:
            return "REJECTION"
        return "TOUCH"

    def _rejection(self, row, zone):
        high = float(row["High"])
        low = float(row["Low"])
        open_ = float(row["Open"])
        close = float(row["Close"])
        rng = max(high - low, 1e-9)
        body_ratio = abs(close - open_) / rng

        if zone.side == "RESISTANCE":
            upper_wick_ratio = (high - max(open_, close)) / rng
            close_position = (close - low) / rng
            penetration = max(0.0, high - zone.zone_low) / max(zone.zone_high - zone.zone_low, 1e-9)
            failed_side = close < zone.zone_low
            candle_shape = body_ratio >= self.minimum_body_ratio or upper_wick_ratio >= self.minimum_upper_wick_ratio
            return bool(
                high >= zone.zone_low
                and failed_side
                and candle_shape
                and penetration >= self.minimum_zone_penetration
                and close_position <= self.maximum_close_position
            )

        lower_wick_ratio = (min(open_, close) - low) / rng
        close_position_from_high = (high - close) / rng
        penetration = max(0.0, zone.zone_high - low) / max(zone.zone_high - zone.zone_low, 1e-9)
        failed_side = close > zone.zone_high
        candle_shape = body_ratio >= self.minimum_body_ratio or lower_wick_ratio >= self.minimum_lower_wick_ratio
        return bool(
            low <= zone.zone_high
            and failed_side
            and candle_shape
            and penetration >= self.minimum_zone_penetration
            and close_position_from_high <= self.maximum_close_position
        )

    def _record_rejection(self, reason):
        key = str(reason)
        self._counts["rejected_setups"] += 1
        self._rejection_reasons[key] = self._rejection_reasons.get(key, 0) + 1

    def _sl(self, df, i, setup):
        entry = float(df.iloc[i]["Close"])
        if setup.direction == "SHORT":
            if self.sl_mode == "SWEEP_HIGH" and setup.sweep_extreme is not None:
                return float(setup.sweep_extreme) + self.sl_buffer
            if self.sl_mode == "ZONE_HIGH":
                return float(setup.zone.zone_high) + self.sl_buffer
            if self.sl_mode == "FIXED_DISTANCE":
                return entry + self.fixed_sl_distance
            if self.sl_mode == "ATR_BUFFER":
                atr_value = df.iloc[i].get("_rr_atr", 0.0)
                atr = float(atr_value) if pd.notna(atr_value) else 0.0
                base = float(setup.rejection_high if setup.rejection_high is not None else setup.zone.zone_high)
                return base + atr * self.atr_buffer_multiplier + self.sl_buffer
            base = setup.rejection_high if setup.rejection_high is not None else setup.zone.zone_high
            return float(base) + self.sl_buffer

        # LONG symmetry. Legacy short SL-mode values are mirrored automatically.
        if self.sl_mode == "SWEEP_HIGH" and setup.sweep_extreme is not None:
            return float(setup.sweep_extreme) - self.sl_buffer
        if self.sl_mode == "ZONE_HIGH":
            return float(setup.zone.zone_low) - self.sl_buffer
        if self.sl_mode == "FIXED_DISTANCE":
            return entry - self.fixed_sl_distance
        if self.sl_mode == "ATR_BUFFER":
            atr_value = df.iloc[i].get("_rr_atr", 0.0)
            atr = float(atr_value) if pd.notna(atr_value) else 0.0
            base = float(setup.rejection_low if setup.rejection_low is not None else setup.zone.zone_low)
            return base - atr * self.atr_buffer_multiplier - self.sl_buffer
        base = setup.rejection_low if setup.rejection_low is not None else setup.zone.zone_low
        return float(base) - self.sl_buffer

    def _tp(self, df, i, direction, entry, sl):
        risk = abs(entry - sl)
        if direction == "SHORT":
            if self.tp_mode in ("PREVIOUS_SUPPORT", "SWING_LOW", "LIQUIDITY_TARGET"):
                lookback = df.iloc[max(0, i - 40) : i]
                if not lookback.empty:
                    structural = float(lookback["Low"].min())
                    if structural < entry:
                        return structural
            return entry - risk * self.target_rr

        if self.tp_mode in ("PREVIOUS_SUPPORT", "SWING_LOW", "LIQUIDITY_TARGET", "PREVIOUS_RESISTANCE", "SWING_HIGH"):
            lookback = df.iloc[max(0, i - 40) : i]
            if not lookback.empty:
                structural = float(lookback["High"].max())
                if structural > entry:
                    return structural
        return entry + risk * self.target_rr

    # --------------------------------------------------------------
    # 15M no-lookahead structure
    # --------------------------------------------------------------

    def _infer_source_timeframe_minutes(self, df):
        if self.source_timeframe_minutes > 0:
            minutes = self.source_timeframe_minutes
        else:
            diffs = df["Date"].diff().dropna()
            if diffs.empty:
                raise ValueError("Cannot infer source timeframe from fewer than 2 candles")
            minutes = int(round(float(diffs.median().total_seconds()) / 60.0))
        if minutes <= 0:
            raise ValueError("Invalid source timeframe")
        if self.htf_timeframe_minutes % minutes != 0:
            raise ValueError("Source timeframe must divide 15 minutes exactly; got %sM" % minutes)
        return minutes

    def _build_complete_15m(self, df, source_minutes):
        expected = int(self.htf_timeframe_minutes / source_minutes)
        work = df[["Date", "Open", "High", "Low", "Close"]].copy().set_index("Date")
        rule = "%dmin" % self.htf_timeframe_minutes
        ohlc = work.resample(rule, label="left", closed="left").agg(
            {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
        )
        counts = work["Close"].resample(rule, label="left", closed="left").count()
        ohlc["_source_count"] = counts
        ohlc = ohlc.dropna(subset=["Open", "High", "Low", "Close"])
        ohlc = ohlc[ohlc["_source_count"] == expected].reset_index()
        ohlc["_htf_close_time"] = ohlc["Date"] + pd.Timedelta(minutes=self.htf_timeframe_minutes)
        return ohlc

    def _is_htf_swing_high(self, htf, pivot):
        if pivot < self.htf_swing_left or pivot + self.htf_swing_right >= len(htf):
            return False
        value = float(htf.iloc[pivot]["High"])
        left = htf.iloc[pivot - self.htf_swing_left : pivot]["High"]
        right = htf.iloc[pivot + 1 : pivot + 1 + self.htf_swing_right]["High"]
        return value > float(left.max()) and value >= float(right.max())

    def _is_htf_swing_low(self, htf, pivot):
        if pivot < self.htf_swing_left or pivot + self.htf_swing_right >= len(htf):
            return False
        value = float(htf.iloc[pivot]["Low"])
        left = htf.iloc[pivot - self.htf_swing_left : pivot]["Low"]
        right = htf.iloc[pivot + 1 : pivot + 1 + self.htf_swing_right]["Low"]
        return value < float(left.min()) and value <= float(right.min())

    def _build_15m_structure_snapshots(self, htf):
        confirmed_highs = []
        confirmed_lows = []
        snapshots = []
        for j in range(len(htf)):
            pivot = j - self.htf_swing_right
            if self._is_htf_swing_high(htf, pivot):
                confirmed_highs.append(float(htf.iloc[pivot]["High"]))
            if self._is_htf_swing_low(htf, pivot):
                confirmed_lows.append(float(htf.iloc[pivot]["Low"]))

            previous_high = confirmed_highs[-2] if len(confirmed_highs) >= 2 else None
            last_high = confirmed_highs[-1] if len(confirmed_highs) >= 1 else None
            previous_low = confirmed_lows[-2] if len(confirmed_lows) >= 2 else None
            last_low = confirmed_lows[-1] if len(confirmed_lows) >= 1 else None

            bias = "NEUTRAL"
            reason = "INSUFFICIENT_CONFIRMED_SWINGS"
            if previous_high is not None and last_high is not None and previous_low is not None and last_low is not None:
                if last_high > previous_high and last_low > previous_low:
                    bias = "BULLISH"
                    reason = "HH_AND_HL"
                elif last_high < previous_high and last_low < previous_low:
                    bias = "BEARISH"
                    reason = "LH_AND_LL"
                else:
                    bias = "NEUTRAL"
                    reason = "MIXED_STRUCTURE"

            snapshots.append(
                {
                    "available_time": pd.Timestamp(htf.iloc[j]["_htf_close_time"]),
                    "bias": bias,
                    "reason": reason,
                    "last_swing_high": last_high,
                    "previous_swing_high": previous_high,
                    "last_swing_low": last_low,
                    "previous_swing_low": previous_low,
                }
            )
        return snapshots

    def _attach_15m_context(self, df, source_minutes):
        df["htf_15m_bias"] = "NEUTRAL"
        df["htf_15m_structure_reason"] = "INSUFFICIENT_CONFIRMED_SWINGS"
        df["htf_15m_last_swing_high"] = pd.NA
        df["htf_15m_previous_swing_high"] = pd.NA
        df["htf_15m_last_swing_low"] = pd.NA
        df["htf_15m_previous_swing_low"] = pd.NA
        if not self.htf_context_enabled:
            df["htf_15m_structure_reason"] = "HTF_CONTEXT_DISABLED"
            return df

        htf = self._build_complete_15m(df, source_minutes)
        self._htf_bar_count = len(htf)
        if htf.empty:
            return df
        snapshots = self._build_15m_structure_snapshots(htf)
        pointer = -1
        for i in range(len(df)):
            decision_time = pd.Timestamp(df.iloc[i]["Date"]) + pd.Timedelta(minutes=source_minutes)
            while pointer + 1 < len(snapshots) and snapshots[pointer + 1]["available_time"] <= decision_time:
                pointer += 1
            if pointer >= 0:
                snap = snapshots[pointer]
                idx = df.index[i]
                df.at[idx, "htf_15m_bias"] = snap["bias"]
                df.at[idx, "htf_15m_structure_reason"] = snap["reason"]
                if snap["last_swing_high"] is not None:
                    df.at[idx, "htf_15m_last_swing_high"] = snap["last_swing_high"]
                if snap["previous_swing_high"] is not None:
                    df.at[idx, "htf_15m_previous_swing_high"] = snap["previous_swing_high"]
                if snap["last_swing_low"] is not None:
                    df.at[idx, "htf_15m_last_swing_low"] = snap["last_swing_low"]
                if snap["previous_swing_low"] is not None:
                    df.at[idx, "htf_15m_previous_swing_low"] = snap["previous_swing_low"]
        return df

    # --------------------------------------------------------------
    # Internal trade tracker + V1.4 cooldown state
    # --------------------------------------------------------------

    def _update_internal_trade(self, df, i):
        if self._open_trade is None:
            return
        if i <= self._open_trade["entry_index"]:
            return

        row = df.iloc[i]
        high = float(row["High"])
        low = float(row["Low"])
        direction = self._open_trade["direction"]
        sl = float(self._open_trade["sl"])
        tp = float(self._open_trade["tp"])

        if direction == "SHORT":
            hit_sl = high >= sl
            hit_tp = low <= tp
        else:
            hit_sl = low <= sl
            hit_tp = high >= tp

        if not hit_sl and not hit_tp:
            return

        if hit_sl and hit_tp:
            result = "LOSS" if self.intrabar_collision_policy == "STOP_FIRST" else "WIN"
        elif hit_sl:
            result = "LOSS"
        else:
            result = "WIN"

        entry_day = self._open_trade["entry_day"]
        if result == "LOSS":
            self._counts["internal_trade_losses"] += 1
            if self._loss_streak_day == entry_day:
                self._same_day_loss_streak += 1
            else:
                self._loss_streak_day = entry_day
                self._same_day_loss_streak = 1
            if self.cooldown_enabled and self._same_day_loss_streak >= self.cooldown_after_losses:
                self._cooldown_remaining = self.cooldown_skip_setups
        else:
            self._counts["internal_trade_wins"] += 1
            if self._loss_streak_day == entry_day:
                self._same_day_loss_streak = 0
            self._cooldown_remaining = 0

        self._open_trade = None

    def _reset_day_state_if_needed(self, current_day):
        # Cooldown is a same-day rule. Do not carry it into a new calendar day.
        if self._loss_streak_day is not None and current_day != self._loss_streak_day:
            self._same_day_loss_streak = 0
            self._loss_streak_day = current_day
            self._cooldown_remaining = 0

    # --------------------------------------------------------------
    # Entry filters / diagnostics
    # --------------------------------------------------------------

    def _context_rejection_reason(self, df, i, direction):
        if not self.htf_context_enabled:
            return None
        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        if direction == "SHORT" and bias == "BULLISH":
            return "15M_BULLISH_CONTEXT"
        if direction == "LONG" and bias == "BEARISH":
            return "15M_BEARISH_CONTEXT"
        return None

    def _regime_interaction_rejection_reason(self, df, i, active):
        if not self.regime_interaction_filter:
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        direction = active.direction

        # Range / neutral structure: the two-year sample shows normal failed-side
        # rejection is materially stronger than deep sweep entries.
        if bias == "NEUTRAL" and interaction != "REJECTION":
            return "NEUTRAL_REQUIRES_REJECTION"

        # In an aligned 15M trend, require a liquidity sweep rather than a
        # shallow normal rejection. Opposite-trend entries are already blocked
        # by _context_rejection_reason().
        if direction == "LONG" and bias == "BULLISH" and interaction != "SWEEP":
            return "BULLISH_LONG_REQUIRES_SWEEP"
        if direction == "SHORT" and bias == "BEARISH" and interaction != "SWEEP":
            return "BEARISH_SHORT_REQUIRES_SWEEP"

        return None

    def _proposal_a_whitelist_matches(self, df, i, active, reason):
        """V2.2: selectively reopen one Bearish SHORT rejection family."""
        if not self.proposal_a_expansion_enabled:
            return False
        if str(reason) != "BEARISH_SHORT_REQUIRES_SWEEP":
            return False
        if active.direction != "SHORT":
            return False
        if str(df.iloc[i].get("htf_15m_bias", "NEUTRAL")) != "BEARISH":
            return False
        if str(active.interaction_type or "").upper() != "REJECTION":
            return False
        if active.rejection_index is None:
            return False

        rejection_row = df.iloc[int(active.rejection_index)]
        body_ratio = self._rejection_quality_metrics(
            rejection_row, active.zone
        )[0]
        return bool(
            float(body_ratio) >= self.proposal_a_min_body_ratio
            and float(body_ratio) < self.proposal_a_max_body_ratio
        )

    def _proposal_b_whitelist_matches(self, df, i, active, reason):
        """V2.4: selectively reopen one Bullish LONG rejection family."""
        if not self.proposal_b_expansion_enabled:
            return False
        if str(reason) != "BULLISH_LONG_REQUIRES_SWEEP":
            return False
        if active.direction != "LONG":
            return False
        if str(df.iloc[i].get("htf_15m_bias", "NEUTRAL")) != "BULLISH":
            return False
        if str(active.interaction_type or "").upper() != "REJECTION":
            return False
        zone_age = i - int(active.zone.available_index)
        return bool(
            int(zone_age) >= self.proposal_b_min_zone_age
            and int(zone_age) < self.proposal_b_max_zone_age
        )

    def _proposal_c_whitelist_matches(self, df, i, active, reason):
        """V2.6: reopen one Bearish SHORT rejection age family."""
        if not self.proposal_c_expansion_enabled:
            return False
        if str(reason) != "BEARISH_SHORT_REQUIRES_SWEEP":
            return False
        if active.direction != "SHORT":
            return False
        if str(df.iloc[i].get("htf_15m_bias", "NEUTRAL")) != "BEARISH":
            return False
        if str(active.interaction_type or "").upper() != "REJECTION":
            return False
        zone_age = i - int(active.zone.available_index)
        return bool(
            int(zone_age) >= self.proposal_c_min_zone_age
            and int(zone_age) < self.proposal_c_max_zone_age
        )

    def _proposal_d_whitelist_matches(self, df, i, active, reason):
        """V2.8: selectively reopen one counter-trend LONG family."""
        if not self.proposal_d_expansion_enabled:
            return False
        if str(reason) != "15M_BEARISH_CONTEXT":
            return False
        if active.direction != "LONG":
            return False
        if str(df.iloc[i].get("htf_15m_bias", "NEUTRAL")) != "BEARISH":
            return False
        if str(active.interaction_type or "").upper() != "REJECTION":
            return False
        displacement = self._confirmation_quality_tuple(df, i, active)[0]
        return bool(
            float(displacement) >= self.proposal_d_min_confirmation_displacement
            and float(displacement) < self.proposal_d_max_confirmation_displacement
        )

    def _v3_1_candidate_a_rejection_reason(
        self,
        df,
        i,
        active,
        proposal_a_whitelisted,
        proposal_b_whitelisted,
        proposal_c_whitelisted,
        proposal_d_whitelisted,
    ):
        """Research-only weak-family filter discovered on V2.8 executions.

        Proposal flags define whether the setup was admitted by one of the
        V2 expansion branches. Candidate A intentionally leaves those branches
        unchanged and operates only on the original V1.22 survivor cohort.
        """
        if not self.v3_1_candidate_a_filter:
            return None
        if (
            proposal_a_whitelisted
            or proposal_b_whitelisted
            or proposal_c_whitelisted
            or proposal_d_whitelisted
        ):
            return None
        rejection_row = df.iloc[active.rejection_index]
        _body, wick, _close, _penetration = self._rejection_quality_metrics(
            rejection_row, active.zone
        )
        displacement = self._confirmation_quality_tuple(df, i, active)[0]
        if (
            float(wick) >= self.v3_1_candidate_a_min_rejection_wick
            and float(wick) < self.v3_1_candidate_a_max_rejection_wick
            and float(displacement)
            >= self.v3_1_candidate_a_min_confirmation_displacement
            and float(displacement)
            < self.v3_1_candidate_a_max_confirmation_displacement
        ):
            return "V3_1_WEAK_ORIGINAL_MEDIUM_WICK_HIGH_CONFIRMATION"
        return None

    def _v3_2_candidate_a_rejection_reason(self, df, i, active):
        """Research-only V3.2 filter discovered on executed V3.1 trades."""
        if not self.v3_2_candidate_a_filter:
            return None
        if active.direction != "SHORT":
            return None
        zone_age = i - int(active.zone.available_index)
        displacement = self._confirmation_quality_tuple(df, i, active)[0]
        if (
            int(zone_age) >= self.v3_2_candidate_a_min_zone_age
            and int(zone_age) < self.v3_2_candidate_a_max_zone_age
            and float(displacement)
            >= self.v3_2_candidate_a_min_confirmation_displacement
            and float(displacement)
            < self.v3_2_candidate_a_max_confirmation_displacement
        ):
            return "V3_2_WEAK_SHORT_MID_AGE_MID_CONFIRMATION"
        return None

    def _v3_3_candidate_a_rejection_reason(self, df, i, active):
        """Research-only V3.3 filter discovered on executed V3.2 trades."""
        if not self.v3_3_candidate_a_filter:
            return None
        if str(active.interaction_type or "").upper() != "REJECTION":
            return None
        rejection_row = df.iloc[active.rejection_index]
        _body, _wick, close_position, _penetration = self._rejection_quality_metrics(
            rejection_row, active.zone
        )
        strength = float(active.zone.strength)
        if (
            strength >= self.v3_3_candidate_a_min_zone_strength
            and strength < self.v3_3_candidate_a_max_zone_strength
            and float(close_position) >= self.v3_3_candidate_a_min_rejection_close
            and float(close_position) < self.v3_3_candidate_a_max_rejection_close
        ):
            return "V3_3_WEAK_REJECTION_MID_STRENGTH_MIDCLOSE"
        return None

    def _v3_4_candidate_a_rejection_reason(self, df, i, active):
        """Research-only V3.4 filter discovered on executed V3.3 trades."""
        if not self.v3_4_candidate_a_filter:
            return None
        if active.direction != "LONG":
            return None
        current_year = int(df.iloc[i]["Date"].year)
        if self.v3_4_candidate_a_start_year > 0 and current_year < self.v3_4_candidate_a_start_year:
            return None
        rejection_row = df.iloc[active.rejection_index]
        body, _wick, close_position, _penetration = self._rejection_quality_metrics(
            rejection_row, active.zone
        )
        if (
            float(body) >= self.v3_4_candidate_a_min_rejection_body
            and float(body) < self.v3_4_candidate_a_max_rejection_body
            and float(close_position) >= self.v3_4_candidate_a_min_rejection_close
            and float(close_position) < self.v3_4_candidate_a_max_rejection_close
        ):
            return "V3_4_WEAK_LONG_MIDHIGH_BODY_MIDCLOSE"
        return None

    def _v3_5_candidate_a_rejection_reason(
        self,
        df,
        i,
        active,
        proposal_a_whitelisted,
        proposal_b_whitelisted,
        proposal_c_whitelisted,
        proposal_d_whitelisted,
    ):
        """Research-only V3.5 filter discovered on executed V3.4 trades.

        Remove only SHORT BASE/non-expansion setups with zone age 3-4 bars.
        BASE means the setup did not require any Proposal A-D whitelist.
        Interaction type is intentionally unrestricted, so naturally valid
        REJECTION and SWEEP setups are both covered when they are BASE.
        """
        if not self.v3_5_candidate_a_filter:
            return None
        if active.direction != "SHORT":
            return None
        if (
            proposal_a_whitelisted
            or proposal_b_whitelisted
            or proposal_c_whitelisted
            or proposal_d_whitelisted
        ):
            return None

        zone_age = i - int(active.zone.available_index)
        if (
            int(zone_age) >= self.v3_5_candidate_a_min_zone_age
            and int(zone_age) < self.v3_5_candidate_a_max_zone_age
        ):
            return "V3_5_WEAK_SHORT_BASE_YOUNG_ZONE"
        return None

    def _neutral_short_penetration_rejection_reason(self, df, i, active):
        """V1.7: reject shallow neutral SHORT resistance rejections only.

        The penetration measurement is taken from the original rejection candle,
        not the later confirmation candle:

            (rejection_high - zone_low) / (zone_high - zone_low)

        This filter intentionally does NOT apply to LONG setups, SWEEPs, or
        bullish/bearish trend-aligned branches.
        """
        if not self.neutral_short_penetration_filter:
            return None
        if active.direction != "SHORT":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, _, _, penetration = self._rejection_quality_metrics(rejection_row, active.zone)
        if float(penetration) < self.neutral_short_min_penetration:
            return "INSUFFICIENT_RESISTANCE_PENETRATION"
        return None

    def _neutral_long_body_rejection_reason(self, df, i, active):
        """V1.8: reject weak middle-body Neutral LONG support rejections.

        Applies ONLY to:
            LONG + 15M NEUTRAL + normal REJECTION

        Keep the two stronger/clearer rejection families unchanged:
            - pin-bar style: body ratio < 20% (must still satisfy existing wick rule)
            - momentum rejection: body ratio >= 30%

        Reject the empirically weak middle band:
            20% <= body ratio < 30%

        The body ratio is measured on the original rejection candle, not the
        later confirmation candle.
        """
        if not self.neutral_long_body_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        body_ratio, _, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
        if (
            float(body_ratio) >= self.neutral_long_weak_body_min
            and float(body_ratio) < self.neutral_long_weak_body_max
        ):
            return "WEAK_NEUTRAL_LONG_REJECTION_BODY"
        return None

    def _neutral_long_overextended_rejection_reason(self, df, i, active):
        """V1.9: reject overextended Neutral LONG support confirmations.

        Applies ONLY to:
            LONG + 15M NEUTRAL + normal REJECTION

        Reject when BOTH are true:
            - rejection lower-wick ratio >= configured threshold (default 0.60)
            - confirmation displacement >= configured threshold (default 0.40)

        Confirmation displacement for LONG is:
            (confirmation_close - rejection_high) / rejection_candle_range

        Trend-aligned LONG SWEEPs, Neutral SHORTs, and all other branches are
        intentionally unaffected.
        """
        if not self.neutral_long_overextended_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, wick_ratio, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
        confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]

        if (
            float(wick_ratio) >= self.neutral_long_min_overextended_wick
            and float(confirmation_displacement) >= self.neutral_long_min_overextended_confirmation
        ):
            return "OVEREXTENDED_NEUTRAL_LONG_CONFIRMATION"
        return None

    def _neutral_short_weak_confirmation_rejection_reason(self, df, i, active):
        """V1.10: reject weak Neutral SHORT confirmations from weak zones.

        Applies ONLY to:
            SHORT + 15M NEUTRAL + normal REJECTION

        Reject when BOTH are true:
            - zone strength < configured threshold (default 2.0)
            - confirmation displacement < configured threshold (default 0.20)

        Confirmation displacement for SHORT is:
            (rejection_low - confirmation_close) / rejection_candle_range

        This rule intentionally does NOT affect Neutral LONG setups,
        Bullish LONG SWEEPs, Bearish SHORT SWEEPs, or other branches.
        """
        if not self.neutral_short_weak_confirmation_filter:
            return None
        if active.direction != "SHORT":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        zone_strength = float(active.zone.strength)
        confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]

        if (
            zone_strength < self.neutral_short_max_weak_zone_strength
            and float(confirmation_displacement)
            < self.neutral_short_max_weak_confirmation_displacement
        ):
            return "WEAK_NEUTRAL_SHORT_CONFIRMATION"
        return None

    def _neutral_short_ambiguous_wick_rejection_reason(self, df, i, active):
        """V1.11: reject ambiguous middle-wick Neutral SHORT rejections.

        Applies ONLY to:
            SHORT + 15M NEUTRAL + normal REJECTION

        Reject the empirically weak upper-wick band:
            configured_min <= rejection upper-wick ratio < configured_max

        Defaults:
            0.20 <= upper-wick ratio < 0.40

        The wick ratio is measured on the original rejection candle.
        This rule intentionally does NOT affect Neutral LONG setups,
        Bullish LONG SWEEPs, Bearish SHORT SWEEPs, or other branches.
        """
        if not self.neutral_short_ambiguous_wick_filter:
            return None
        if active.direction != "SHORT":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, wick_ratio, _, _ = self._rejection_quality_metrics(
            rejection_row, active.zone
        )

        if (
            float(wick_ratio) >= self.neutral_short_ambiguous_wick_min
            and float(wick_ratio) < self.neutral_short_ambiguous_wick_max
        ):
            return "AMBIGUOUS_NEUTRAL_SHORT_REJECTION_WICK"
        return None

    def _neutral_long_moderate_strength_close_rejection_reason(self, df, i, active):
        """V1.12: reject weak moderate-strength Neutral LONG rejections.

        Applies ONLY to:
            LONG + 15M NEUTRAL + normal REJECTION

        Reject when ALL are true:
            - zone strength >= configured minimum (default 2.0)
            - zone strength < configured maximum (default 2.5)
            - rejection close position < configured threshold (default 0.20)

        For SUPPORT/LONG, rejection close position is measured from the
        rejection candle high:
            (high - close) / candle_range

        This rule intentionally does NOT affect Neutral SHORT setups,
        Bullish LONG SWEEPs, Bearish SHORT SWEEPs, or other branches.
        """
        if not self.neutral_long_moderate_strength_close_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, _, close_position, _ = self._rejection_quality_metrics(
            rejection_row, active.zone
        )
        zone_strength = float(active.zone.strength)

        if (
            zone_strength >= self.neutral_long_moderate_strength_min
            and zone_strength < self.neutral_long_moderate_strength_max
            and float(close_position) < self.neutral_long_max_close_position
        ):
            return "WEAK_MODERATE_STRENGTH_NEUTRAL_LONG_REJECTION"
        return None

    def _neutral_long_age_confirmation_rejection_reason(self, df, i, active):
        """V1.14: reject weak age/displacement Neutral LONG confirmations.

        Built from the V1.12 baseline. V1.13 logic is intentionally excluded.

        Applies ONLY to:
            LONG + 15M NEUTRAL + normal REJECTION

        Reject when ALL are true:
            - zone age >= configured minimum (default 5 bars)
            - zone age < configured maximum (default 10 bars)
            - confirmation displacement >= configured minimum (default 0.20)
            - confirmation displacement < configured maximum (default 0.30)

        Confirmation displacement for LONG:
            (confirmation_close - rejection_high) / rejection_candle_range

        zone_age:
            current_bar_index - zone.available_index
        """
        if not self.neutral_long_age_confirmation_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        zone_age = i - int(active.zone.available_index)
        confirmation_displacement = self._confirmation_quality_tuple(
            df, i, active
        )[0]

        if (
            int(zone_age) >= self.neutral_long_age_confirmation_min_age
            and int(zone_age) < self.neutral_long_age_confirmation_max_age
            and float(confirmation_displacement)
            >= self.neutral_long_age_confirmation_min_displacement
            and float(confirmation_displacement)
            < self.neutral_long_age_confirmation_max_displacement
        ):
            return "WEAK_YOUNG_NEUTRAL_LONG_CONFIRMATION"
        return None

    def _neutral_long_ambiguous_moderate_rejection_reason(self, df, i, active):
        """V1.15: reject ambiguous moderate-quality Neutral LONG rejections.

        Applies ONLY to:
            LONG + 15M NEUTRAL + normal REJECTION

        Reject when ALL are true:
            - zone strength >= configured minimum (default 1.50)
            - zone strength < configured maximum (default 2.00)
            - rejection lower-wick ratio >= configured minimum (default 0.30)
            - rejection lower-wick ratio < configured maximum (default 0.40)

        The wick ratio is measured on the original rejection candle.
        """
        if not self.neutral_long_ambiguous_moderate_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, wick_ratio, _, _ = self._rejection_quality_metrics(
            rejection_row, active.zone
        )
        zone_strength = float(active.zone.strength)

        if (
            zone_strength >= self.neutral_long_ambiguous_moderate_min_zone_strength
            and zone_strength < self.neutral_long_ambiguous_moderate_max_zone_strength
            and float(wick_ratio) >= self.neutral_long_ambiguous_moderate_min_wick
            and float(wick_ratio) < self.neutral_long_ambiguous_moderate_max_wick
        ):
            return "AMBIGUOUS_MODERATE_NEUTRAL_LONG_REJECTION"
        return None

    def _neutral_long_low_strength_wick_rejection_reason(self, df, i, active):
        """V1.16 FINAL: reject weak low-strength Neutral LONG rejections.

        Applies ONLY to:
            LONG + 15M NEUTRAL + normal REJECTION

        Reject when ALL are true:
            - zone strength >= configured minimum (default 1.00)
            - zone strength < configured maximum (default 1.50)
            - rejection lower-wick ratio >= configured minimum (default 0.20)
            - rejection lower-wick ratio < configured maximum (default 0.30)
        """
        if not self.neutral_long_low_strength_wick_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, wick_ratio, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
        zone_strength = float(active.zone.strength)

        if (
            zone_strength >= self.neutral_long_low_strength_min_zone_strength
            and zone_strength < self.neutral_long_low_strength_max_zone_strength
            and float(wick_ratio) >= self.neutral_long_low_strength_min_wick
            and float(wick_ratio) < self.neutral_long_low_strength_max_wick
        ):
            return "WEAK_LOW_STRENGTH_NEUTRAL_LONG_REJECTION"
        return None

    def _neutral_long_shallow_wick_penetration_rejection_reason(self, df, i, active):
        """V1.17 FILTER A: reject shallow Neutral LONG support interactions.

        Applies ONLY to:
            LONG + 15M NEUTRAL + normal REJECTION

        Reject when BOTH are true:
            - configured_min <= rejection lower-wick ratio < configured_max
              (defaults: 0.50 <= wick < 0.60)
            - support-zone penetration < configured maximum
              (default: penetration < 0.20)

        The V1.16 five-year export showed this surviving setup cluster to be
        persistently weak. The rule is deliberately bounded at wick < 0.60
        because the existing V1.9 rule handles the >=0.60 overextended family
        separately and only when confirmation displacement is also excessive.
        """
        if not self.neutral_long_shallow_wick_penetration_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, wick_ratio, _, penetration = self._rejection_quality_metrics(
            rejection_row, active.zone
        )

        if (
            float(wick_ratio) >= self.neutral_long_shallow_wick_min
            and float(wick_ratio) < self.neutral_long_shallow_wick_max
            and float(penetration) < self.neutral_long_shallow_max_penetration
        ):
            return "SHALLOW_WICK_NEUTRAL_LONG_REJECTION"
        return None

    def _neutral_short_high_body_rejection_reason(self, df, i, active):
        """V1.17 FILTER B: reject weak high-body Neutral SHORT rejections.

        Applies ONLY to:
            SHORT + 15M NEUTRAL + normal REJECTION

        Reject the empirically weak body band:
            configured_min <= rejection body ratio < configured_max
            (defaults: 0.75 <= body < 0.90)

        IMPORTANT: body ratios >=0.90 are intentionally preserved because the
        V1.16 research sample showed that stronger extreme-body band recovered
        profitability. The body ratio is measured on the original rejection
        candle, not the confirmation candle.
        """
        if not self.neutral_short_high_body_filter:
            return None
        if active.direction != "SHORT":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        body_ratio, _, _, _ = self._rejection_quality_metrics(
            rejection_row, active.zone
        )

        if (
            float(body_ratio) >= self.neutral_short_high_body_min
            and float(body_ratio) < self.neutral_short_high_body_max
        ):
            return "WEAK_HIGH_BODY_NEUTRAL_SHORT_REJECTION"
        return None

    def _neutral_long_midclose_penetration_rejection_reason(self, df, i, active):
        """V1.18 FILTER A: reject weak Neutral LONG mid-close interactions.

        Applies ONLY to:
            LONG + 15M NEUTRAL + normal REJECTION

        Reject when ALL are true:
            - configured_min_close <= rejection close-position < configured_max_close
              (defaults: 0.40 <= rclose < 0.50)
            - configured_min_penetration <= support-zone penetration
            - support-zone penetration < configured_max_penetration
              (defaults: 0.20 <= penetration < 0.50)

        For SUPPORT/LONG, close-position is the existing strategy metric:
            (rejection_high - rejection_close) / rejection_candle_range

        This rule is evaluated only after all V1.17-and-earlier filters, so it
        removes only setups that survived the tested V1.17 baseline.
        """
        if not self.neutral_long_midclose_penetration_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, _, close_position, penetration = self._rejection_quality_metrics(
            rejection_row, active.zone
        )

        if (
            float(close_position) >= self.neutral_long_midclose_min_close
            and float(close_position) < self.neutral_long_midclose_max_close
            and float(penetration) >= self.neutral_long_midclose_min_penetration
            and float(penetration) < self.neutral_long_midclose_max_penetration
        ):
            return "WEAK_MIDCLOSE_NEUTRAL_LONG_REJECTION"
        return None

    def _neutral_long_stale_weak_confirmation_rejection_reason(self, df, i, active):
        """V1.18 FILTER B: reject older-zone Neutral LONG weak confirmations.

        Applies ONLY to:
            LONG + 15M NEUTRAL + normal REJECTION

        Reject when ALL are true:
            - zone age >= configured minimum (default 40 bars)
            - confirmation displacement >= configured minimum (default 0.10)
            - confirmation displacement < configured maximum (default 0.30)

        Confirmation displacement for LONG:
            (confirmation_close - rejection_high) / rejection_candle_range

        zone_age:
            current_bar_index - zone.available_index

        This rule is evaluated only after all V1.17-and-earlier filters.
        """
        if not self.neutral_long_stale_weak_confirmation_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        zone_age = i - int(active.zone.available_index)
        confirmation_displacement = self._confirmation_quality_tuple(
            df, i, active
        )[0]

        if (
            int(zone_age) >= self.neutral_long_stale_min_zone_age
            and float(confirmation_displacement)
            >= self.neutral_long_stale_min_confirmation_displacement
            and float(confirmation_displacement)
            < self.neutral_long_stale_max_confirmation_displacement
        ):
            return "STALE_WEAK_CONFIRMATION_NEUTRAL_LONG_REJECTION"
        return None

    def _neutral_long_medium_pen_weak_confirmation_rejection_reason(self, df, i, active):
        """V1.19 FILTER A: reject medium-penetration Neutral LONG with weak confirmation.

        Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
        Defaults:
            0.20 <= support-zone penetration < 0.30
            0.05 <= confirmation displacement < 0.20

        This rule is evaluated only after all V1.18-and-earlier filters.
        """
        if not self.neutral_long_medium_pen_weak_confirmation_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, _, _, penetration = self._rejection_quality_metrics(
            rejection_row, active.zone
        )
        confirmation_displacement = self._confirmation_quality_tuple(
            df, i, active
        )[0]

        if (
            float(penetration) >= self.neutral_long_medium_pen_min_penetration
            and float(penetration) < self.neutral_long_medium_pen_max_penetration
            and float(confirmation_displacement)
            >= self.neutral_long_medium_pen_min_confirmation_displacement
            and float(confirmation_displacement)
            < self.neutral_long_medium_pen_max_confirmation_displacement
        ):
            return "WEAK_MEDIUM_PENETRATION_NEUTRAL_LONG_CONFIRMATION"
        return None

    def _neutral_short_weak_body_midclose_rejection_reason(self, df, i, active):
        """V1.19 FILTER B: reject weak-body Neutral SHORT with mid-range close.

        Applies ONLY to SHORT + 15M NEUTRAL + normal REJECTION.
        Defaults:
            0.20 <= rejection body ratio < 0.40
            0.30 <= rejection close-position < 0.50

        This rule is evaluated only after all V1.18-and-earlier filters.
        """
        if not self.neutral_short_weak_body_midclose_filter:
            return None
        if active.direction != "SHORT":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        body_ratio, _, close_position, _ = self._rejection_quality_metrics(
            rejection_row, active.zone
        )

        if (
            float(body_ratio) >= self.neutral_short_weak_body_midclose_min_body
            and float(body_ratio) < self.neutral_short_weak_body_midclose_max_body
            and float(close_position) >= self.neutral_short_weak_body_midclose_min_close
            and float(close_position) < self.neutral_short_weak_body_midclose_max_close
        ):
            return "WEAK_BODY_MIDCLOSE_NEUTRAL_SHORT_REJECTION"
        return None

    def _neutral_long_high_body_shallow_pen_rejection_reason(self, df, i, active):
        """V1.20 FILTER A: reject high-body Neutral LONG shallow interactions.

        Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
        Defaults:
            0.70 <= rejection body ratio < 0.90
            0.10 <= support-zone penetration < 0.20

        This rule is evaluated only after all V1.19-and-earlier filters.
        """
        if not self.neutral_long_high_body_shallow_pen_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        body_ratio, _, _, penetration = self._rejection_quality_metrics(
            rejection_row, active.zone
        )

        if (
            float(body_ratio) >= self.neutral_long_high_body_shallow_pen_min_body
            and float(body_ratio) < self.neutral_long_high_body_shallow_pen_max_body
            and float(penetration) >= self.neutral_long_high_body_shallow_pen_min_penetration
            and float(penetration) < self.neutral_long_high_body_shallow_pen_max_penetration
        ):
            return "WEAK_HIGH_BODY_SHALLOW_PEN_NEUTRAL_LONG_REJECTION"
        return None

    def _neutral_long_medium_pen_midhigh_confirmation_rejection_reason(self, df, i, active):
        """V1.20 FILTER B: reject medium-penetration Neutral LONG with mid/high confirmation.

        Applies ONLY to LONG + 15M NEUTRAL + normal REJECTION.
        Defaults:
            0.20 <= support-zone penetration < 0.30
            0.40 <= confirmation displacement < 0.80

        This rule is evaluated only after all V1.19-and-earlier filters.
        """
        if not self.neutral_long_medium_pen_midhigh_confirmation_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, _, _, penetration = self._rejection_quality_metrics(
            rejection_row, active.zone
        )
        confirmation_displacement = self._confirmation_quality_tuple(
            df, i, active
        )[0]

        if (
            float(penetration) >= self.neutral_long_medium_pen_midhigh_min_penetration
            and float(penetration) < self.neutral_long_medium_pen_midhigh_max_penetration
            and float(confirmation_displacement)
            >= self.neutral_long_medium_pen_midhigh_min_confirmation_displacement
            and float(confirmation_displacement)
            < self.neutral_long_medium_pen_midhigh_max_confirmation_displacement
        ):
            return "WEAK_MEDIUM_PEN_MIDHIGH_CONFIRM_NEUTRAL_LONG_REJECTION"
        return None

    def _bearish_short_sweep_weak_confirmation_rejection_reason(self, df, i, active):
        """V1.21 FILTER A: reject weak Bearish SHORT SWEEP confirmations.

        Applies ONLY to SHORT + 15M BEARISH + SWEEP.
        Defaults:
            0.10 <= rejection close-position < 0.50
            0.00 <= confirmation displacement < 0.30
        """
        if not self.bearish_short_sweep_weak_confirmation_filter:
            return None
        if active.direction != "SHORT":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "BEARISH" or interaction != "SWEEP":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, _, close_position, _ = self._rejection_quality_metrics(
            rejection_row, active.zone
        )
        confirmation_displacement = self._confirmation_quality_tuple(
            df, i, active
        )[0]

        if (
            float(close_position) >= self.bearish_short_sweep_min_close
            and float(close_position) < self.bearish_short_sweep_max_close
            and float(confirmation_displacement)
            >= self.bearish_short_sweep_min_confirmation_displacement
            and float(confirmation_displacement)
            < self.bearish_short_sweep_max_confirmation_displacement
        ):
            return "WEAK_BEARISH_SHORT_SWEEP_CONFIRMATION"
        return None

    def _bullish_long_sweep_mid_confirmation_rejection_reason(self, df, i, active):
        """V1.21 FILTER B: reject weak Bullish LONG SWEEP confirmations.

        Applies ONLY to LONG + 15M BULLISH + SWEEP.
        Defaults:
            0.00 <= rejection close-position < 0.40
            0.40 <= confirmation displacement < 0.60
        """
        if not self.bullish_long_sweep_mid_confirmation_filter:
            return None
        if active.direction != "LONG":
            return None

        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "BULLISH" or interaction != "SWEEP":
            return None
        if active.rejection_index is None:
            return None

        rejection_row = df.iloc[int(active.rejection_index)]
        _, _, close_position, _ = self._rejection_quality_metrics(
            rejection_row, active.zone
        )
        confirmation_displacement = self._confirmation_quality_tuple(
            df, i, active
        )[0]

        if (
            float(close_position) >= self.bullish_long_sweep_min_close
            and float(close_position) < self.bullish_long_sweep_max_close
            and float(confirmation_displacement)
            >= self.bullish_long_sweep_min_confirmation_displacement
            and float(confirmation_displacement)
            < self.bullish_long_sweep_max_confirmation_displacement
        ):
            return "WEAK_BULLISH_LONG_SWEEP_CONFIRMATION"
        return None

    def _neutral_long_deep_pen_mid_confirmation_rejection_reason(self, df, i, active):
        """V1.22 FILTER A: reject deeper-penetration Neutral LONG with mid confirmation."""
        if not self.neutral_long_deep_pen_mid_confirmation_filter:
            return None
        if active.direction != "LONG":
            return None
        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None
        rejection_row = df.iloc[int(active.rejection_index)]
        _, _, _, penetration = self._rejection_quality_metrics(rejection_row, active.zone)
        confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]
        if (
            float(penetration) >= self.neutral_long_deep_pen_mid_confirmation_min_penetration
            and float(penetration) < self.neutral_long_deep_pen_mid_confirmation_max_penetration
            and float(confirmation_displacement) >= self.neutral_long_deep_pen_mid_confirmation_min_displacement
            and float(confirmation_displacement) < self.neutral_long_deep_pen_mid_confirmation_max_displacement
        ):
            return "WEAK_DEEP_PEN_MID_CONFIRM_NEUTRAL_LONG_REJECTION"
        return None

    def _neutral_long_weak_body_mid_strength_rejection_reason(self, df, i, active):
        """V1.22 FILTER B: reject weak-body Neutral LONG in 2.5-4.0 strength zones."""
        if not self.neutral_long_weak_body_mid_strength_filter:
            return None
        if active.direction != "LONG":
            return None
        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        if active.rejection_index is None:
            return None
        rejection_row = df.iloc[int(active.rejection_index)]
        body_ratio, _, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
        zone_strength = float(active.zone.strength)
        if (
            float(body_ratio) >= self.neutral_long_weak_body_mid_strength_min_body
            and float(body_ratio) < self.neutral_long_weak_body_mid_strength_max_body
            and zone_strength >= self.neutral_long_weak_body_mid_strength_min_zone_strength
            and zone_strength < self.neutral_long_weak_body_mid_strength_max_zone_strength
        ):
            return "WEAK_BODY_MID_STRENGTH_NEUTRAL_LONG_REJECTION"
        return None

    def _neutral_long_mid_age_mid_strength_rejection_reason(self, df, i, active):
        """V1.22 FILTER C: reject middle-age Neutral LONG in 2.5-4.0 strength zones."""
        if not self.neutral_long_mid_age_mid_strength_filter:
            return None
        if active.direction != "LONG":
            return None
        bias = str(df.iloc[i].get("htf_15m_bias", "NEUTRAL"))
        interaction = str(active.interaction_type or "").upper()
        if bias != "NEUTRAL" or interaction != "REJECTION":
            return None
        zone_age = i - int(active.zone.available_index)
        zone_strength = float(active.zone.strength)
        if (
            int(zone_age) >= self.neutral_long_mid_age_mid_strength_min_age
            and int(zone_age) < self.neutral_long_mid_age_mid_strength_max_age
            and zone_strength >= self.neutral_long_mid_age_mid_strength_min_zone_strength
            and zone_strength < self.neutral_long_mid_age_mid_strength_max_zone_strength
        ):
            return "WEAK_AGE_MID_STRENGTH_NEUTRAL_LONG_REJECTION"
        return None

    def _rejection_quality_metrics(self, row, zone):
        high = float(row["High"])
        low = float(row["Low"])
        open_ = float(row["Open"])
        close = float(row["Close"])
        rng = max(high - low, 1e-9)
        body_ratio = abs(close - open_) / rng
        zone_range = max(zone.zone_high - zone.zone_low, 1e-9)

        if zone.side == "RESISTANCE":
            wick_ratio = (high - max(open_, close)) / rng
            close_position = (close - low) / rng
            penetration = max(0.0, high - zone.zone_low) / zone_range
        else:
            wick_ratio = (min(open_, close) - low) / rng
            close_position = (high - close) / rng
            penetration = max(0.0, zone.zone_high - low) / zone_range

        return body_ratio, wick_ratio, close_position, penetration

    def _confirmation_quality_tuple(self, df, i, active):
        row = df.iloc[i]
        close = float(row["Close"])
        rejection_range = max(float(active.rejection_high) - float(active.rejection_low), 1e-9)
        if active.direction == "SHORT":
            displacement = max(0.0, float(active.rejection_low) - close) / rejection_range
        else:
            displacement = max(0.0, close - float(active.rejection_high)) / rejection_range
        return (float(displacement), float(active.zone.strength))

    def _frequency_rejection_reason(self, df, i):
        ts = pd.Timestamp(df.iloc[i]["Date"])
        day_key = self._day_key_from_timestamp(ts)
        month_key = self._month_key_from_timestamp(ts)

        if self.max_entries_per_month > 0 and self._entries_by_month.get(month_key, 0) >= self.max_entries_per_month:
            return "MONTHLY_TRADE_CAP"
        if self.max_entries_per_day > 0 and self._entries_by_day.get(day_key, 0) >= self.max_entries_per_day:
            return "DAILY_TRADE_CAP"
        if self.min_bars_between_entries > 0 and self._last_entry_index is not None:
            if i - self._last_entry_index < self.min_bars_between_entries:
                return "ENTRY_SPACING"
        return None

    def _mark_entry_count(self, df, i):
        ts = pd.Timestamp(df.iloc[i]["Date"])
        day_key = self._day_key_from_timestamp(ts)
        month_key = self._month_key_from_timestamp(ts)
        self._entries_by_day[day_key] = self._entries_by_day.get(day_key, 0) + 1
        self._entries_by_month[month_key] = self._entries_by_month.get(month_key, 0) + 1
        self._last_entry_index = i

    def _emit_diag(self, df, i, setup, decision, reason, rr=None, entry=None, sl=None, tp=None):
        row = df.iloc[i]
        self._diagnostic_rows.append(
            {
                "strategy_version": "V1.22-LS",
                "setup_id": setup.setup_id,
                "zone_id": setup.zone.zone_id,
                "timestamp": self._timestamp_text(pd.Timestamp(row["Date"])),
                "direction": setup.direction,
                "zone_side": setup.zone.side,
                "state": setup.state,
                "zone_low": float(setup.zone.zone_low),
                "zone_high": float(setup.zone.zone_high),
                "zone_strength": float(setup.zone.strength),
                "interaction": setup.interaction_type,
                "rejection_high": setup.rejection_high,
                "rejection_low": setup.rejection_low,
                "htf_15m_bias": str(row.get("htf_15m_bias", "NEUTRAL")),
                "htf_15m_structure_reason": str(row.get("htf_15m_structure_reason", "")),
                "entry": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "rr": rr,
                "same_day_loss_streak": self._same_day_loss_streak,
                "cooldown_remaining": self._cooldown_remaining,
                "final_decision": decision,
                "rejection_reason": reason,
            }
        )

    def _reject_confirmed_setup(self, df, i, active, reason, rr=None, entry=None, sl=None, tp=None):
        active.state = "REJECTED"
        self._record_rejection(reason)
        idx = df.index[i]
        df.at[idx, "rr_state"] = "REJECTED"
        df.at[idx, "rejection_reason"] = reason
        df.at[idx, "signal_reason"] = "Blocked %s: %s" % (active.direction, reason)
        df.at[idx, "rr_setup_id"] = active.setup_id
        df.at[idx, "rr_zone_id"] = active.zone.zone_id
        df.at[idx, "rr_zone_low"] = active.zone.zone_low
        df.at[idx, "rr_zone_high"] = active.zone.zone_high
        df.at[idx, "rr_interaction"] = active.interaction_type
        df.at[idx, "rr_direction"] = active.direction

        if reason == "15M_BULLISH_CONTEXT":
            self._counts["htf_bullish_short_rejections"] += 1
        elif reason == "15M_BEARISH_CONTEXT":
            self._counts["htf_bearish_long_rejections"] += 1
        elif reason == "DAILY_TRADE_CAP":
            self._counts["daily_cap_rejections"] += 1
        elif reason == "MONTHLY_TRADE_CAP":
            self._counts["monthly_cap_rejections"] += 1
        elif reason == "ENTRY_SPACING":
            self._counts["spacing_rejections"] += 1
        elif reason == "TWO_LOSS_COOLDOWN":
            self._counts["cooldown_rejections"] += 1
        elif reason in (
            "NEUTRAL_REQUIRES_REJECTION",
            "BULLISH_LONG_REQUIRES_SWEEP",
            "BEARISH_SHORT_REQUIRES_SWEEP",
        ):
            self._counts["regime_interaction_rejections"] += 1
        elif reason == "INSUFFICIENT_RESISTANCE_PENETRATION":
            self._counts["neutral_short_penetration_rejections"] += 1
        elif reason == "WEAK_NEUTRAL_LONG_REJECTION_BODY":
            self._counts["neutral_long_weak_body_rejections"] += 1
        elif reason == "OVEREXTENDED_NEUTRAL_LONG_CONFIRMATION":
            self._counts["neutral_long_overextended_rejections"] += 1
        elif reason == "WEAK_NEUTRAL_SHORT_CONFIRMATION":
            self._counts["neutral_short_weak_confirmation_rejections"] += 1
        elif reason == "AMBIGUOUS_NEUTRAL_SHORT_REJECTION_WICK":
            self._counts["neutral_short_ambiguous_wick_rejections"] += 1
        elif reason == "WEAK_MODERATE_STRENGTH_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_moderate_strength_close_rejections"] += 1
        elif reason == "WEAK_YOUNG_NEUTRAL_LONG_CONFIRMATION":
            self._counts["neutral_long_age_confirmation_rejections"] += 1
        elif reason == "AMBIGUOUS_MODERATE_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_ambiguous_moderate_rejections"] += 1
        elif reason == "WEAK_LOW_STRENGTH_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_low_strength_wick_rejections"] += 1
        elif reason == "SHALLOW_WICK_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_shallow_wick_penetration_rejections"] += 1
        elif reason == "WEAK_HIGH_BODY_NEUTRAL_SHORT_REJECTION":
            self._counts["neutral_short_high_body_rejections"] += 1
        elif reason == "WEAK_MIDCLOSE_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_midclose_penetration_rejections"] += 1
        elif reason == "STALE_WEAK_CONFIRMATION_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_stale_weak_confirmation_rejections"] += 1
        elif reason == "WEAK_MEDIUM_PENETRATION_NEUTRAL_LONG_CONFIRMATION":
            self._counts["neutral_long_medium_pen_weak_confirmation_rejections"] += 1
        elif reason == "WEAK_BODY_MIDCLOSE_NEUTRAL_SHORT_REJECTION":
            self._counts["neutral_short_weak_body_midclose_rejections"] += 1
        elif reason == "WEAK_HIGH_BODY_SHALLOW_PEN_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_high_body_shallow_pen_rejections"] += 1
        elif reason == "WEAK_MEDIUM_PEN_MIDHIGH_CONFIRM_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_medium_pen_midhigh_confirmation_rejections"] += 1
        elif reason == "WEAK_BEARISH_SHORT_SWEEP_CONFIRMATION":
            self._counts["bearish_short_sweep_weak_confirmation_rejections"] += 1
        elif reason == "WEAK_BULLISH_LONG_SWEEP_CONFIRMATION":
            self._counts["bullish_long_sweep_mid_confirmation_rejections"] += 1
        elif reason == "WEAK_DEEP_PEN_MID_CONFIRM_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_deep_pen_mid_confirmation_rejections"] += 1
        elif reason == "WEAK_BODY_MID_STRENGTH_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_weak_body_mid_strength_rejections"] += 1
        elif reason == "WEAK_AGE_MID_STRENGTH_NEUTRAL_LONG_REJECTION":
            self._counts["neutral_long_mid_age_mid_strength_rejections"] += 1
        elif reason == "V3_1_WEAK_ORIGINAL_MEDIUM_WICK_HIGH_CONFIRMATION":
            self._counts["v3_1_candidate_a_rejections"] += 1
        elif reason == "V3_2_WEAK_SHORT_MID_AGE_MID_CONFIRMATION":
            self._counts["v3_2_candidate_a_rejections"] += 1
        elif reason == "V3_3_WEAK_REJECTION_MID_STRENGTH_MIDCLOSE":
            self._counts["v3_3_candidate_a_rejections"] += 1
        elif reason == "V3_4_WEAK_LONG_MIDHIGH_BODY_MIDCLOSE":
            self._counts["v3_4_candidate_a_rejections"] += 1
        elif reason == "V3_5_WEAK_SHORT_BASE_YOUNG_ZONE":
            self._counts["v3_5_candidate_a_rejections"] += 1

        self._emit_diag(df, i, active, "NO_TRADE", reason, rr=rr, entry=entry, sl=sl, tp=tp)
        active.zone.consumed = True
        active.zone.lifecycle = "FILTER_REJECTED"

    def _try_entry(self, df, i, active):
        self._counts["confirmed_setups"] += 1
        direction = active.direction
        proposal_a_whitelisted = False
        proposal_b_whitelisted = False
        proposal_c_whitelisted = False
        proposal_d_whitelisted = False

        reason = self._context_rejection_reason(df, i, direction)
        if reason is not None:
            if self._proposal_d_whitelist_matches(df, i, active, reason):
                proposal_d_whitelisted = True
                self._counts["proposal_d_whitelisted"] += 1
            else:
                self._reject_confirmed_setup(df, i, active, reason)
                return False

        reason = self._regime_interaction_rejection_reason(df, i, active)
        if reason is not None:
            if self._proposal_a_whitelist_matches(df, i, active, reason):
                proposal_a_whitelisted = True
                self._counts["proposal_a_whitelisted"] += 1
            elif self._proposal_b_whitelist_matches(df, i, active, reason):
                proposal_b_whitelisted = True
                self._counts["proposal_b_whitelisted"] += 1
            elif self._proposal_c_whitelist_matches(df, i, active, reason):
                proposal_c_whitelisted = True
                self._counts["proposal_c_whitelisted"] += 1
            else:
                self._reject_confirmed_setup(df, i, active, reason)
                return False

        reason = self._neutral_short_penetration_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_short_weak_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_short_ambiguous_wick_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_moderate_strength_close_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_age_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_ambiguous_moderate_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_low_strength_wick_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_body_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_overextended_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V1.17 dual refinement. Keep these AFTER all V1.16-and-earlier
        # filters so V1.17 only removes setups that survived the tested V1.16
        # baseline; this preserves prior rejection behavior and diagnostics.
        reason = self._neutral_long_shallow_wick_penetration_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_short_high_body_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V1.18 dual refinement. Keep these AFTER all V1.17-and-earlier
        # filters so V1.18 only removes setups that survived the tested V1.17
        # baseline and preserves all prior rejection behavior/diagnostics.
        reason = self._neutral_long_midclose_penetration_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_stale_weak_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V1.19 dual refinement. Keep these AFTER all V1.18-and-earlier
        # filters so V1.19 only removes setups that survived the tested V1.18
        # baseline and preserves all prior rejection behavior/diagnostics.
        reason = self._neutral_long_medium_pen_weak_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_short_weak_body_midclose_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V1.20 dual refinement. Keep these AFTER all V1.19-and-earlier
        # filters so V1.20 only removes setups that survived the tested V1.19
        # baseline and preserves all prior rejection behavior/diagnostics.
        reason = self._neutral_long_high_body_shallow_pen_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_medium_pen_midhigh_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V1.21 dual refinement. These rules target only trend-aligned SWEEP
        # branches and are evaluated after all V1.20-and-earlier filters.
        reason = self._bearish_short_sweep_weak_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._bullish_long_sweep_mid_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V1.22 triple refinement. Run only after every V1.21-and-earlier rule.
        reason = self._neutral_long_deep_pen_mid_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_weak_body_mid_strength_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_mid_age_mid_strength_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V3.1 research branch only. Evaluate after every frozen V2.8 filter and
        # after Proposal A-D attribution so the V2.8 behavior is recoverable by
        # setting v3_1_candidate_a_filter=False.
        reason = self._v3_1_candidate_a_rejection_reason(
            df,
            i,
            active,
            proposal_a_whitelisted,
            proposal_b_whitelisted,
            proposal_c_whitelisted,
            proposal_d_whitelisted,
        )
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V3.2 research branch. Evaluate only after the complete frozen V3.1
        # logic so disabling this flag reproduces V3.1 Candidate A exactly.
        reason = self._v3_2_candidate_a_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V3.3 research branch. Disabling it reproduces V3.2 Candidate A.
        reason = self._v3_3_candidate_a_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V3.4 research branch. Disabling it reproduces V3.3 Candidate A.
        reason = self._v3_4_candidate_a_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        # V3.5 Candidate A. Evaluate only after the complete V3.4 logic and
        # Proposal A-D attribution. Disabling this flag reproduces V3.4 exactly.
        reason = self._v3_5_candidate_a_rejection_reason(
            df,
            i,
            active,
            proposal_a_whitelisted,
            proposal_b_whitelisted,
            proposal_c_whitelisted,
            proposal_d_whitelisted,
        )
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        entry = float(df.iloc[i]["Close"])
        sl = self._sl(df, i, active)
        if direction == "SHORT" and sl <= entry:
            self._reject_confirmed_setup(df, i, active, "RR_TOO_LOW", entry=entry, sl=sl)
            return False
        if direction == "LONG" and sl >= entry:
            self._reject_confirmed_setup(df, i, active, "RR_TOO_LOW", entry=entry, sl=sl)
            return False

        tp = self._tp(df, i, direction, entry, sl)
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0.0
        if rr < self.minimum_rr:
            self._reject_confirmed_setup(df, i, active, "RR_TOO_LOW", rr=rr, entry=entry, sl=sl, tp=tp)
            return False

        # Internal tracker mirrors one-open-trade execution. Do not emit another
        # signal until the prior internally tracked trade has closed.
        if self._open_trade is not None:
            self._reject_confirmed_setup(df, i, active, "TRADE_ALREADY_OPEN", rr=rr, entry=entry, sl=sl, tp=tp)
            return False

        freq_reason = self._frequency_rejection_reason(df, i)
        if freq_reason is not None:
            self._reject_confirmed_setup(df, i, active, freq_reason, rr=rr, entry=entry, sl=sl, tp=tp)
            return False

        if self.cooldown_enabled and self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1
            self._same_day_loss_streak = 0
            self._reject_confirmed_setup(df, i, active, "TWO_LOSS_COOLDOWN", rr=rr, entry=entry, sl=sl, tp=tp)
            return False

        idx = df.index[i]
        pos = -1 if direction == "SHORT" else 1
        df.at[idx, "Position"] = pos
        df.at[idx, "strategy_stop_loss"] = sl
        df.at[idx, "strategy_target"] = tp
        df.at[idx, "rr_setup_id"] = active.setup_id
        df.at[idx, "rr_zone_id"] = active.zone.zone_id
        df.at[idx, "rr_state"] = "%s_ENTRY" % direction
        df.at[idx, "rr_interaction"] = active.interaction_type
        df.at[idx, "rr_zone_low"] = active.zone.zone_low
        df.at[idx, "rr_zone_high"] = active.zone.zone_high
        df.at[idx, "rr_direction"] = direction
        if proposal_a_whitelisted:
            df.at[idx, "expansion_source"] = "PROPOSAL_A"
        elif proposal_b_whitelisted:
            df.at[idx, "expansion_source"] = "PROPOSAL_B"
        elif proposal_c_whitelisted:
            df.at[idx, "expansion_source"] = "PROPOSAL_C"
        elif proposal_d_whitelisted:
            df.at[idx, "expansion_source"] = "PROPOSAL_D"
        rej_row = df.iloc[active.rejection_index]
        rq_body, rq_wick, rq_close, rq_pen = self._rejection_quality_metrics(rej_row, active.zone)
        cq = self._confirmation_quality_tuple(df, i, active)[0]
        zone_age = i - int(active.zone.available_index)
        df.at[idx, "signal_reason"] = (
            "%s rejection %s; confirmed; 15M=%s; zstr=%.3f; zage=%d; "
            "rbody=%.3f; rwick=%.3f; rclose=%.3f; pen=%.3f; cdisp=%.3f"
            % (
                active.zone.side,
                active.interaction_type,
                df.iloc[i]["htf_15m_bias"],
                float(active.zone.strength),
                int(zone_age),
                float(rq_body),
                float(rq_wick),
                float(rq_close),
                float(rq_pen),
                float(cq),
            )
        )
        if proposal_a_whitelisted:
            df.at[idx, "signal_reason"] = "%s; expansion=PROPOSAL_A" % str(
                df.at[idx, "signal_reason"]
            )
        elif proposal_b_whitelisted:
            df.at[idx, "signal_reason"] = "%s; expansion=PROPOSAL_B" % str(
                df.at[idx, "signal_reason"]
            )
        elif proposal_c_whitelisted:
            df.at[idx, "signal_reason"] = "%s; expansion=PROPOSAL_C" % str(
                df.at[idx, "signal_reason"]
            )
        elif proposal_d_whitelisted:
            df.at[idx, "signal_reason"] = "%s; expansion=PROPOSAL_D" % str(
                df.at[idx, "signal_reason"]
            )

        self._counts["executed_trades"] += 1
        if direction == "SHORT":
            self._counts["short_entries"] += 1
        else:
            self._counts["long_entries"] += 1
        if proposal_a_whitelisted:
            self._counts["proposal_a_executed"] += 1
        elif proposal_b_whitelisted:
            self._counts["proposal_b_executed"] += 1
        elif proposal_c_whitelisted:
            self._counts["proposal_c_executed"] += 1
        elif proposal_d_whitelisted:
            self._counts["proposal_d_executed"] += 1
        self._mark_entry_count(df, i)

        ts = pd.Timestamp(df.iloc[i]["Date"])
        self._open_trade = {
            "direction": direction,
            "entry_index": i,
            "entry_day": self._day_key_from_timestamp(ts),
            "entry": entry,
            "sl": sl,
            "tp": tp,
        }

        active.state = "%s_ENTRY" % direction
        self._emit_diag(df, i, active, direction, None, rr=rr, entry=entry, sl=sl, tp=tp)
        active.zone.consumed = True
        active.zone.lifecycle = "RETESTED"
        return True

    def _confirmation_passed(self, df, i, active):
        if active.rejection_index is None:
            return False
        if i <= active.rejection_index:
            return False
        if i > active.rejection_index + self.confirmation_bars:
            return False

        if active.direction == "SHORT":
            return float(df.iloc[i]["Close"]) < float(active.rejection_low)
        return float(df.iloc[i]["Close"]) > float(active.rejection_high)

    def _find_candidate_zone(self, zones, df, i, required_side=None):
        close = float(df.iloc[i]["Close"])
        candidates = []
        for z in zones:
            if z.broken or z.consumed or z.lifecycle == "EXPIRED" or i < z.available_index:
                continue
            if required_side is not None and z.side != required_side:
                continue
            if z.side == "RESISTANCE":
                if not self.enable_short:
                    continue
                if close <= z.zone_high + self.breakout_buffer and (z.zone_low - self.approach_distance) <= close:
                    candidates.append((abs(z.zone_low - close), -float(z.strength), z))
            else:
                if not self.enable_long:
                    continue
                if close >= z.zone_low - self.breakout_buffer and close <= (z.zone_high + self.approach_distance):
                    candidates.append((abs(close - z.zone_high), -float(z.strength), z))

        # Nearest valid level first; if equally near, prefer the stronger zone.
        candidates.sort(key=lambda item: (item[0], item[1]))
        for _, __, zone in candidates:
            interaction = self._interaction(df.iloc[i], zone)
            if interaction is not None:
                return zone, interaction
        return None, None

    # --------------------------------------------------------------
    # Main strategy
    # --------------------------------------------------------------

    def generate(self):
        df = self.df.copy()
        required = ["Date", "Open", "High", "Low", "Close"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError("Missing required columns: %s" % ", ".join(missing))

        df["Date"] = pd.to_datetime(df["Date"])
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=required).sort_values("Date").reset_index(drop=True)

        source_minutes = self._infer_source_timeframe_minutes(df)
        self._detected_source_timeframe_minutes = source_minutes

        df["Position"] = 0
        df["strategy_stop_loss"] = pd.NA
        df["strategy_target"] = pd.NA
        df["signal_reason"] = pd.NA
        df["rejection_reason"] = pd.NA
        df["rr_setup_id"] = pd.NA
        df["rr_zone_id"] = pd.NA
        df["rr_state"] = "WAITING"
        df["rr_interaction"] = pd.NA
        df["rr_direction"] = pd.NA
        df["rr_zone_low"] = pd.NA
        df["rr_zone_high"] = pd.NA
        df["expansion_source"] = pd.NA
        df["same_day_loss_streak"] = 0
        df["cooldown_remaining"] = 0
        df["monthly_entry_count"] = 0
        df["daily_entry_count"] = 0
        df["_rr_atr"] = self._atr(df)
        df = self._attach_15m_context(df, source_minutes)

        zones = []
        active_short = None
        active_long = None
        resistance_sequence = 0
        support_sequence = 0
        setup_sequence = 0

        for i in range(len(df)):
            ts = pd.Timestamp(df.iloc[i]["Date"])
            current_day = self._day_key_from_timestamp(ts)
            current_month = self._month_key_from_timestamp(ts)

            self._update_internal_trade(df, i)
            self._reset_day_state_if_needed(current_day)

            idx = df.index[i]
            df.at[idx, "same_day_loss_streak"] = self._same_day_loss_streak
            df.at[idx, "cooldown_remaining"] = self._cooldown_remaining
            df.at[idx, "monthly_entry_count"] = self._entries_by_month.get(current_month, 0)
            df.at[idx, "daily_entry_count"] = self._entries_by_day.get(current_day, 0)

            # Confirm new supply/demand zones only after swing_right bars have closed.
            pivot = i - self.swing_right
            if self._is_swing_high(df, pivot):
                resistance_sequence += 1
                candidate = self._candidate_zone(df, pivot, i, resistance_sequence, "RESISTANCE")
                if candidate is not None:
                    self._merge_or_add(zones, candidate)
            if self._is_swing_low(df, pivot):
                support_sequence += 1
                candidate = self._candidate_zone(df, pivot, i, support_sequence, "SUPPORT")
                if candidate is not None:
                    self._merge_or_add(zones, candidate)

            # Zone lifecycle and invalidation. A broken zone only cancels the
            # pending setup that belongs to that exact zone/direction.
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
                    if active_short is not None and active_short.zone.zone_id == zone.zone_id:
                        active_short.state = "ZONE_BROKEN"
                        self._record_rejection("BREAKOUT")
                        self._emit_diag(df, i, active_short, "NO_TRADE", "BREAKOUT")
                        active_short = None
                    if active_long is not None and active_long.zone.zone_id == zone.zone_id:
                        active_long.state = "ZONE_BROKEN"
                        self._record_rejection("BREAKOUT")
                        self._emit_diag(df, i, active_long, "NO_TRADE", "BREAKOUT")
                        active_long = None

            confirmed = []

            # Process SHORT and LONG pending setups independently. Waiting for
            # confirmation on one side no longer prevents the other side from
            # being evaluated.
            if active_short is not None:
                a = active_short
                if a.zone.broken or a.zone.consumed:
                    active_short = None
                elif a.expires_at is not None and i > a.expires_at:
                    a.state = "SETUP_EXPIRED"
                    self._record_rejection("ZONE_EXPIRED")
                    self._emit_diag(df, i, a, "NO_TRADE", "ZONE_EXPIRED")
                    active_short = None
                elif a.state == "REJECTION_DETECTED":
                    if self._confirmation_passed(df, i, a):
                        a.state = "ENTRY_CONFIRMATION"
                        confirmed.append(a)
                    elif i >= a.rejection_index + self.confirmation_bars:
                        a.state = "REJECTION_FAILED"
                        self._record_rejection("NO_ENTRY_CONFIRMATION")
                        self._emit_diag(df, i, a, "NO_TRADE", "NO_ENTRY_CONFIRMATION")
                        active_short = None

            if active_long is not None:
                a = active_long
                if a.zone.broken or a.zone.consumed:
                    active_long = None
                elif a.expires_at is not None and i > a.expires_at:
                    a.state = "SETUP_EXPIRED"
                    self._record_rejection("ZONE_EXPIRED")
                    self._emit_diag(df, i, a, "NO_TRADE", "ZONE_EXPIRED")
                    active_long = None
                elif a.state == "REJECTION_DETECTED":
                    if self._confirmation_passed(df, i, a):
                        a.state = "ENTRY_CONFIRMATION"
                        confirmed.append(a)
                    elif i >= a.rejection_index + self.confirmation_bars:
                        a.state = "REJECTION_FAILED"
                        self._record_rejection("NO_ENTRY_CONFIRMATION")
                        self._emit_diag(df, i, a, "NO_TRADE", "NO_ENTRY_CONFIRMATION")
                        active_long = None

            if confirmed:
                # If LONG and SHORT confirm on the same candle, prefer the setup
                # with the stronger close displacement beyond the rejection
                # extreme; zone strength is the tie breaker. This affects only
                # simultaneous confirmations and avoids arbitrary direction order.
                confirmed.sort(key=lambda a: self._confirmation_quality_tuple(df, i, a), reverse=True)
                for a in confirmed:
                    self._try_entry(df, i, a)
                    if a.direction == "SHORT":
                        active_short = None
                    else:
                        active_long = None

            # While flat, allow both directions to establish independent pending
            # setups on the same candle. No daily/monthly quota is applied when
            # max_entries_per_day/month are left at their V1.5 defaults of 0.
            if self._open_trade is None and not confirmed:
                if active_short is None and self.enable_short:
                    zone, interaction = self._find_candidate_zone(zones, df, i, "RESISTANCE")
                    if zone is not None:
                        self._counts["zone_interactions"] += 1
                        zone.last_interaction_index = i
                        zone.lifecycle = "ACTIVE" if zone.reactions <= 1 else "RETESTED"
                        setup_sequence += 1
                        setup_id = "SD-%04d%02d%02d-%04d" % (ts.year, ts.month, ts.day, setup_sequence)
                        active_short = ActiveSetup(
                            setup_id=setup_id,
                            zone=zone,
                            direction="SHORT",
                            state="ZONE_REACHED",
                            interaction_type=interaction,
                            expires_at=i + self.setup_expiry_bars,
                        )
                        if interaction in ("REJECTION", "SWEEP") and self._rejection(df.iloc[i], zone):
                            active_short.state = "REJECTION_DETECTED"
                            active_short.rejection_index = i
                            active_short.rejection_high = float(df.iloc[i]["High"])
                            active_short.rejection_low = float(df.iloc[i]["Low"])
                            if interaction == "SWEEP":
                                active_short.sweep_extreme = active_short.rejection_high
                            self._counts["rejection_setups"] += 1

                if active_long is None and self.enable_long:
                    zone, interaction = self._find_candidate_zone(zones, df, i, "SUPPORT")
                    if zone is not None:
                        self._counts["zone_interactions"] += 1
                        zone.last_interaction_index = i
                        zone.lifecycle = "ACTIVE" if zone.reactions <= 1 else "RETESTED"
                        setup_sequence += 1
                        setup_id = "SD-%04d%02d%02d-%04d" % (ts.year, ts.month, ts.day, setup_sequence)
                        active_long = ActiveSetup(
                            setup_id=setup_id,
                            zone=zone,
                            direction="LONG",
                            state="ZONE_REACHED",
                            interaction_type=interaction,
                            expires_at=i + self.setup_expiry_bars,
                        )
                        if interaction in ("REJECTION", "SWEEP") and self._rejection(df.iloc[i], zone):
                            active_long.state = "REJECTION_DETECTED"
                            active_long.rejection_index = i
                            active_long.rejection_high = float(df.iloc[i]["High"])
                            active_long.rejection_low = float(df.iloc[i]["Low"])
                            if interaction == "SWEEP":
                                active_long.sweep_extreme = active_long.rejection_low
                            self._counts["rejection_setups"] += 1

            # A touch can become a rejection on later candles. Process each side
            # independently so a pending LONG never freezes SHORT evaluation.
            if active_short is not None and active_short.state == "ZONE_REACHED":
                interaction = self._interaction(df.iloc[i], active_short.zone)
                if interaction in ("REJECTION", "SWEEP") and self._rejection(df.iloc[i], active_short.zone):
                    active_short.interaction_type = interaction
                    active_short.state = "REJECTION_DETECTED"
                    active_short.rejection_index = i
                    active_short.rejection_high = float(df.iloc[i]["High"])
                    active_short.rejection_low = float(df.iloc[i]["Low"])
                    if interaction == "SWEEP":
                        active_short.sweep_extreme = active_short.rejection_high
                    self._counts["rejection_setups"] += 1

            if active_long is not None and active_long.state == "ZONE_REACHED":
                interaction = self._interaction(df.iloc[i], active_long.zone)
                if interaction in ("REJECTION", "SWEEP") and self._rejection(df.iloc[i], active_long.zone):
                    active_long.interaction_type = interaction
                    active_long.state = "REJECTION_DETECTED"
                    active_long.rejection_index = i
                    active_long.rejection_high = float(df.iloc[i]["High"])
                    active_long.rejection_low = float(df.iloc[i]["Low"])
                    if interaction == "SWEEP":
                        active_long.sweep_extreme = active_long.rejection_low
                    self._counts["rejection_setups"] += 1

        diagnostics = {
            "strategy": "XAUUSD 5M Resistance Rejection V3.5 CANDIDATE A",
            "strategy_version": "V3.5-CANDIDATE-A-RESEARCH",
            "base_version": "V3.4-CANDIDATE-A-RESEARCH-FROZEN",
            "v1_3_included": False,
            "v1_4_cooldown_included": False,
            "direction_mode": "LONG_AND_SHORT_INDEPENDENT_PENDING",
            "total_zones": self._counts["total_zones"],
            "resistance_zones": self._counts["resistance_zones"],
            "support_zones": self._counts["support_zones"],
            "zone_interactions": self._counts["zone_interactions"],
            "rejection_setups": self._counts["rejection_setups"],
            "confirmed_setups": self._counts["confirmed_setups"],
            "executed_trades": self._counts["executed_trades"],
            "short_entries": self._counts["short_entries"],
            "long_entries": self._counts["long_entries"],
            "rejected_setups": self._counts["rejected_setups"],
            "htf_bullish_short_rejections": self._counts["htf_bullish_short_rejections"],
            "htf_bearish_long_rejections": self._counts["htf_bearish_long_rejections"],
            "regime_interaction_rejections": self._counts["regime_interaction_rejections"],
            "neutral_short_penetration_rejections": self._counts["neutral_short_penetration_rejections"],
            "neutral_long_weak_body_rejections": self._counts["neutral_long_weak_body_rejections"],
            "neutral_long_overextended_rejections": self._counts["neutral_long_overextended_rejections"],
            "neutral_short_weak_confirmation_rejections": self._counts["neutral_short_weak_confirmation_rejections"],
            "neutral_short_ambiguous_wick_rejections": self._counts["neutral_short_ambiguous_wick_rejections"],
            "neutral_long_moderate_strength_close_rejections": self._counts["neutral_long_moderate_strength_close_rejections"],
            "neutral_long_age_confirmation_rejections": self._counts["neutral_long_age_confirmation_rejections"],
            "neutral_long_ambiguous_moderate_rejections": self._counts["neutral_long_ambiguous_moderate_rejections"],
            "neutral_long_low_strength_wick_rejections": self._counts["neutral_long_low_strength_wick_rejections"],
            "neutral_long_shallow_wick_penetration_rejections": self._counts["neutral_long_shallow_wick_penetration_rejections"],
            "neutral_short_high_body_rejections": self._counts["neutral_short_high_body_rejections"],
            "neutral_long_midclose_penetration_rejections": self._counts["neutral_long_midclose_penetration_rejections"],
            "neutral_long_stale_weak_confirmation_rejections": self._counts["neutral_long_stale_weak_confirmation_rejections"],
            "neutral_long_medium_pen_weak_confirmation_rejections": self._counts["neutral_long_medium_pen_weak_confirmation_rejections"],
            "neutral_short_weak_body_midclose_rejections": self._counts["neutral_short_weak_body_midclose_rejections"],
            "neutral_long_high_body_shallow_pen_rejections": self._counts["neutral_long_high_body_shallow_pen_rejections"],
            "neutral_long_medium_pen_midhigh_confirmation_rejections": self._counts["neutral_long_medium_pen_midhigh_confirmation_rejections"],
            "bearish_short_sweep_weak_confirmation_rejections": self._counts["bearish_short_sweep_weak_confirmation_rejections"],
            "bullish_long_sweep_mid_confirmation_rejections": self._counts["bullish_long_sweep_mid_confirmation_rejections"],
            "neutral_long_deep_pen_mid_confirmation_rejections": self._counts["neutral_long_deep_pen_mid_confirmation_rejections"],
            "neutral_long_weak_body_mid_strength_rejections": self._counts["neutral_long_weak_body_mid_strength_rejections"],
            "neutral_long_mid_age_mid_strength_rejections": self._counts["neutral_long_mid_age_mid_strength_rejections"],
            "v3_1_candidate_a_rejections": self._counts["v3_1_candidate_a_rejections"],
            "v3_1_candidate_a": {
                "enabled": self.v3_1_candidate_a_filter,
                "status": "RESEARCH_ONLY_NOT_PROMOTED",
                "applies_to": "ORIGINAL_V1.22_SURVIVORS_ONLY; PROPOSALS_A_TO_D_UNCHANGED",
                "minimum_rejection_wick_inclusive": self.v3_1_candidate_a_min_rejection_wick,
                "maximum_rejection_wick_exclusive": self.v3_1_candidate_a_max_rejection_wick,
                "minimum_confirmation_displacement_inclusive": self.v3_1_candidate_a_min_confirmation_displacement,
                "maximum_confirmation_displacement_exclusive": self.v3_1_candidate_a_max_confirmation_displacement,
                "rejection_reason": "V3_1_WEAK_ORIGINAL_MEDIUM_WICK_HIGH_CONFIRMATION",
                "disable_to_reproduce_v2_8": True,
            },
            "v3_2_candidate_a_rejections": self._counts["v3_2_candidate_a_rejections"],
            "v3_2_candidate_a": {
                "enabled": self.v3_2_candidate_a_filter,
                "status": "RESEARCH_ONLY_NOT_PROMOTED",
                "applies_to": "ALL_SHORT_ENTRIES_AFTER_COMPLETE_V3.1_LOGIC",
                "minimum_zone_age_inclusive": self.v3_2_candidate_a_min_zone_age,
                "maximum_zone_age_exclusive": self.v3_2_candidate_a_max_zone_age,
                "minimum_confirmation_displacement_inclusive": self.v3_2_candidate_a_min_confirmation_displacement,
                "maximum_confirmation_displacement_exclusive": self.v3_2_candidate_a_max_confirmation_displacement,
                "rejection_reason": "V3_2_WEAK_SHORT_MID_AGE_MID_CONFIRMATION",
                "disable_to_reproduce_v3_1": True,
            },
            "v3_3_candidate_a_rejections": self._counts["v3_3_candidate_a_rejections"],
            "v3_3_candidate_a": {
                "enabled": self.v3_3_candidate_a_filter,
                "status": "RESEARCH_ONLY_NOT_PROMOTED",
                "applies_to": "REJECTION_INTERACTIONS_AFTER_COMPLETE_V3.2_LOGIC",
                "minimum_zone_strength_inclusive": self.v3_3_candidate_a_min_zone_strength,
                "maximum_zone_strength_exclusive": self.v3_3_candidate_a_max_zone_strength,
                "minimum_rejection_close_inclusive": self.v3_3_candidate_a_min_rejection_close,
                "maximum_rejection_close_exclusive": self.v3_3_candidate_a_max_rejection_close,
                "rejection_reason": "V3_3_WEAK_REJECTION_MID_STRENGTH_MIDCLOSE",
                "disable_to_reproduce_v3_2": True,
            },
            "v3_4_candidate_a_rejections": self._counts["v3_4_candidate_a_rejections"],
            "v3_4_candidate_a": {
                "enabled": self.v3_4_candidate_a_filter,
                "status": "RESEARCH_ONLY_NOT_PROMOTED",
                "applies_to": "LONG_ENTRIES_AFTER_COMPLETE_V3.3_LOGIC",
                "start_year_zero_means_global": self.v3_4_candidate_a_start_year,
                "minimum_rejection_body_inclusive": self.v3_4_candidate_a_min_rejection_body,
                "maximum_rejection_body_exclusive": self.v3_4_candidate_a_max_rejection_body,
                "minimum_rejection_close_inclusive": self.v3_4_candidate_a_min_rejection_close,
                "maximum_rejection_close_exclusive": self.v3_4_candidate_a_max_rejection_close,
                "rejection_reason": "V3_4_WEAK_LONG_MIDHIGH_BODY_MIDCLOSE",
                "disable_to_reproduce_v3_3": True,
            },
            "v3_5_candidate_a_rejections": self._counts["v3_5_candidate_a_rejections"],
            "v3_5_candidate_a": {
                "enabled": self.v3_5_candidate_a_filter,
                "status": "RESEARCH_ONLY_NOT_PROMOTED",
                "applies_to": "SHORT_BASE_NON_EXPANSION_AFTER_COMPLETE_V3.4_LOGIC",
                "interaction_scope": "REJECTION_AND_SWEEP",
                "minimum_zone_age_inclusive": self.v3_5_candidate_a_min_zone_age,
                "maximum_zone_age_exclusive": self.v3_5_candidate_a_max_zone_age,
                "proposal_a_d_whitelists_excluded": True,
                "rejection_reason": "V3_5_WEAK_SHORT_BASE_YOUNG_ZONE",
                "disable_to_reproduce_v3_4": True,
            },
            "internal_trade_wins": self._counts["internal_trade_wins"],
            "internal_trade_losses": self._counts["internal_trade_losses"],
            "proposal_a": {
                "enabled": self.proposal_a_expansion_enabled,
                "applies_to": "SHORT + 15M_BEARISH + REJECTION_ONLY",
                "minimum_rejection_body_ratio_inclusive": self.proposal_a_min_body_ratio,
                "maximum_rejection_body_ratio_exclusive": self.proposal_a_max_body_ratio,
                "bypassed_rejection_reason": "BEARISH_SHORT_REQUIRES_SWEEP",
                "whitelisted_setups": self._counts["proposal_a_whitelisted"],
                "executed_entries": self._counts["proposal_a_executed"],
                "note": "All other V1.22 filters and execution guards remain active.",
            },
            "proposal_b": {
                "enabled": self.proposal_b_expansion_enabled,
                "applies_to": "SHORT + 15M_BEARISH + REJECTION_ONLY",
                "minimum_zone_age_inclusive": self.proposal_b_min_zone_age,
                "maximum_zone_age_exclusive": self.proposal_b_max_zone_age,
                "bypassed_rejection_reason": "BEARISH_SHORT_REQUIRES_SWEEP",
                "whitelisted_setups": self._counts["proposal_b_whitelisted"],
                "executed_entries": self._counts["proposal_b_executed"],
                "note": "All other V1.22 filters and execution guards remain active.",
            },
            "proposal_c": {
                "enabled": self.proposal_c_expansion_enabled,
                "applies_to": "LONG + 15M_BULLISH + REJECTION_ONLY",
                "minimum_zone_age_inclusive": self.proposal_c_min_zone_age,
                "maximum_zone_age_exclusive": self.proposal_c_max_zone_age,
                "bypassed_rejection_reason": "BULLISH_LONG_REQUIRES_SWEEP",
                "whitelisted_setups": self._counts["proposal_c_whitelisted"],
                "executed_entries": self._counts["proposal_c_executed"],
                "note": "All other V1.22 filters and execution guards remain active.",
            },
            "proposal_d": {
                "enabled": self.proposal_d_expansion_enabled,
                "applies_to": "LONG + 15M_BEARISH + REJECTION_ONLY",
                "minimum_confirmation_displacement_inclusive": self.proposal_d_min_confirmation_displacement,
                "maximum_confirmation_displacement_exclusive": self.proposal_d_max_confirmation_displacement,
                "bypassed_rejection_reason": "15M_BEARISH_CONTEXT",
                "whitelisted_setups": self._counts["proposal_d_whitelisted"],
                "executed_entries": self._counts["proposal_d_executed"],
                "note": "All V2.6 rules and execution guards remain active.",
            },
            "rejection_reasons": dict(self._rejection_reasons),
            "frequency_guard": {
                "max_entries_per_month": self.max_entries_per_month,
                "max_entries_per_day": self.max_entries_per_day,
                "min_bars_between_entries": self.min_bars_between_entries,
                "note": "V2.8 preserves frozen V2.6 and adds Proposal D. Frequency remains uncapped by default (0).",
            },
            "quality_filter": {
                "enabled": self.regime_interaction_filter,
                "neutral": "REJECTION_ONLY",
                "bullish_long": "SWEEP_ONLY",
                "bearish_short": "SWEEP_ONLY",
                "opposite_trend": "BLOCKED_BY_V1.2_HTF_CONTEXT",
            },
            "v1_7_penetration_filter": {
                "enabled": self.neutral_short_penetration_filter,
                "applies_to": "SHORT + 15M_NEUTRAL + REJECTION_ONLY",
                "minimum_penetration": self.neutral_short_min_penetration,
                "rejection_reason": "INSUFFICIENT_RESISTANCE_PENETRATION",
            },
            "v1_8_neutral_long_body_filter": {
                "enabled": self.neutral_long_body_filter,
                "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                "weak_body_min_inclusive": self.neutral_long_weak_body_min,
                "weak_body_max_exclusive": self.neutral_long_weak_body_max,
                "rejection_reason": "WEAK_NEUTRAL_LONG_REJECTION_BODY",
            },
            "v1_9_neutral_long_overextended_filter": {
                "enabled": self.neutral_long_overextended_filter,
                "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                "minimum_lower_wick_ratio": self.neutral_long_min_overextended_wick,
                "minimum_confirmation_displacement": self.neutral_long_min_overextended_confirmation,
                "rejection_reason": "OVEREXTENDED_NEUTRAL_LONG_CONFIRMATION",
            },
            "v1_10_neutral_short_weak_confirmation_filter": {
                "enabled": self.neutral_short_weak_confirmation_filter,
                "applies_to": "SHORT + 15M_NEUTRAL + REJECTION_ONLY",
                "maximum_zone_strength_exclusive": self.neutral_short_max_weak_zone_strength,
                "maximum_confirmation_displacement_exclusive": self.neutral_short_max_weak_confirmation_displacement,
                "rejection_reason": "WEAK_NEUTRAL_SHORT_CONFIRMATION",
            },
            "v1_11_neutral_short_ambiguous_wick_filter": {
                "enabled": self.neutral_short_ambiguous_wick_filter,
                "applies_to": "SHORT + 15M_NEUTRAL + REJECTION_ONLY",
                "minimum_upper_wick_ratio_inclusive": self.neutral_short_ambiguous_wick_min,
                "maximum_upper_wick_ratio_exclusive": self.neutral_short_ambiguous_wick_max,
                "rejection_reason": "AMBIGUOUS_NEUTRAL_SHORT_REJECTION_WICK",
            },
            "v1_12_neutral_long_moderate_strength_close_filter": {
                "enabled": self.neutral_long_moderate_strength_close_filter,
                "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                "minimum_zone_strength_inclusive": self.neutral_long_moderate_strength_min,
                "maximum_zone_strength_exclusive": self.neutral_long_moderate_strength_max,
                "maximum_rejection_close_position_exclusive": self.neutral_long_max_close_position,
                "rejection_reason": "WEAK_MODERATE_STRENGTH_NEUTRAL_LONG_REJECTION",
            },
            "v1_14_neutral_long_age_confirmation_filter": {
                "enabled": self.neutral_long_age_confirmation_filter,
                "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                "minimum_zone_age_inclusive": self.neutral_long_age_confirmation_min_age,
                "maximum_zone_age_exclusive": self.neutral_long_age_confirmation_max_age,
                "minimum_confirmation_displacement_inclusive": self.neutral_long_age_confirmation_min_displacement,
                "maximum_confirmation_displacement_exclusive": self.neutral_long_age_confirmation_max_displacement,
                "rejection_reason": "WEAK_YOUNG_NEUTRAL_LONG_CONFIRMATION",
                "built_from": "V1.12-LS",
                "v1_13_included": False,
            },
            "v1_15_neutral_long_ambiguous_moderate_filter": {
                "enabled": self.neutral_long_ambiguous_moderate_filter,
                "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                "minimum_zone_strength_inclusive": self.neutral_long_ambiguous_moderate_min_zone_strength,
                "maximum_zone_strength_exclusive": self.neutral_long_ambiguous_moderate_max_zone_strength,
                "minimum_lower_wick_ratio_inclusive": self.neutral_long_ambiguous_moderate_min_wick,
                "maximum_lower_wick_ratio_exclusive": self.neutral_long_ambiguous_moderate_max_wick,
                "rejection_reason": "AMBIGUOUS_MODERATE_NEUTRAL_LONG_REJECTION",
                "built_from": "V1.14-LS",
            },
            "v1_16_neutral_long_low_strength_wick_filter": {
                "enabled": self.neutral_long_low_strength_wick_filter,
                "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                "minimum_zone_strength_inclusive": self.neutral_long_low_strength_min_zone_strength,
                "maximum_zone_strength_exclusive": self.neutral_long_low_strength_max_zone_strength,
                "minimum_lower_wick_ratio_inclusive": self.neutral_long_low_strength_min_wick,
                "maximum_lower_wick_ratio_exclusive": self.neutral_long_low_strength_max_wick,
                "rejection_reason": "WEAK_LOW_STRENGTH_NEUTRAL_LONG_REJECTION",
                "built_from": "V1.15-LS",
                "final_planned_filter": False,
                "superseded_by": "V1.17-LS",
            },
            "v1_17_dual_refinement": {
                "built_from": "V1.16-LS",
                "filter_count": 2,
                "filter_a_neutral_long_shallow_wick_penetration": {
                    "enabled": self.neutral_long_shallow_wick_penetration_filter,
                    "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_lower_wick_ratio_inclusive": self.neutral_long_shallow_wick_min,
                    "maximum_lower_wick_ratio_exclusive": self.neutral_long_shallow_wick_max,
                    "maximum_zone_penetration_exclusive": self.neutral_long_shallow_max_penetration,
                    "rejection_reason": "SHALLOW_WICK_NEUTRAL_LONG_REJECTION",
                    "v1_16_research_sample": "38 trades; 7W/31L; WR~18.42%; total~-17R; PF~0.45",
                },
                "filter_b_neutral_short_high_body": {
                    "enabled": self.neutral_short_high_body_filter,
                    "applies_to": "SHORT + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_body_ratio_inclusive": self.neutral_short_high_body_min,
                    "maximum_body_ratio_exclusive": self.neutral_short_high_body_max,
                    "preserve_body_ratio_gte": self.neutral_short_high_body_max,
                    "rejection_reason": "WEAK_HIGH_BODY_NEUTRAL_SHORT_REJECTION",
                    "v1_16_research_sample": "44 trades; 9W/35L; WR~20.45%; total~-17.09R; PF~0.51",
                },
            },
            "v1_18_dual_refinement": {
                "built_from": "V1.17-LS",
                "filter_count": 2,
                "filter_a_neutral_long_midclose_penetration": {
                    "enabled": self.neutral_long_midclose_penetration_filter,
                    "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_rejection_close_position_inclusive": self.neutral_long_midclose_min_close,
                    "maximum_rejection_close_position_exclusive": self.neutral_long_midclose_max_close,
                    "minimum_zone_penetration_inclusive": self.neutral_long_midclose_min_penetration,
                    "maximum_zone_penetration_exclusive": self.neutral_long_midclose_max_penetration,
                    "rejection_reason": "WEAK_MIDCLOSE_NEUTRAL_LONG_REJECTION",
                    "v1_17_research_sample": "37 trades; 4W/33L; WR~10.81%; total~-25.23R; R-PF~0.24; negative every tested year",
                },
                "filter_b_neutral_long_stale_weak_confirmation": {
                    "enabled": self.neutral_long_stale_weak_confirmation_filter,
                    "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_zone_age_inclusive": self.neutral_long_stale_min_zone_age,
                    "minimum_confirmation_displacement_inclusive": self.neutral_long_stale_min_confirmation_displacement,
                    "maximum_confirmation_displacement_exclusive": self.neutral_long_stale_max_confirmation_displacement,
                    "rejection_reason": "STALE_WEAK_CONFIRMATION_NEUTRAL_LONG_REJECTION",
                    "v1_17_research_sample": "32 trades; 6W/26L; WR~18.75%; total~-14.15R; R-PF~0.46; negative every tested year",
                },
                "combined_unique_v1_17_sample": "63 trades; 10W/53L; winner:loser ~1:5.3; total~-33.38R",
            },
            "v1_19_dual_refinement": {
                "built_from": "V1.18-LS",
                "filter_count": 2,
                "filter_a_neutral_long_medium_pen_weak_confirmation": {
                    "enabled": self.neutral_long_medium_pen_weak_confirmation_filter,
                    "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_zone_penetration_inclusive": self.neutral_long_medium_pen_min_penetration,
                    "maximum_zone_penetration_exclusive": self.neutral_long_medium_pen_max_penetration,
                    "minimum_confirmation_displacement_inclusive": self.neutral_long_medium_pen_min_confirmation_displacement,
                    "maximum_confirmation_displacement_exclusive": self.neutral_long_medium_pen_max_confirmation_displacement,
                    "rejection_reason": "WEAK_MEDIUM_PENETRATION_NEUTRAL_LONG_CONFIRMATION",
                    "v1_18_research_sample": "24 trades; 4W/20L; WR~16.67%; total~-11.89R; R-PF~0.41; negative every tested year",
                },
                "filter_b_neutral_short_weak_body_midclose": {
                    "enabled": self.neutral_short_weak_body_midclose_filter,
                    "applies_to": "SHORT + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_body_ratio_inclusive": self.neutral_short_weak_body_midclose_min_body,
                    "maximum_body_ratio_exclusive": self.neutral_short_weak_body_midclose_max_body,
                    "minimum_rejection_close_position_inclusive": self.neutral_short_weak_body_midclose_min_close,
                    "maximum_rejection_close_position_exclusive": self.neutral_short_weak_body_midclose_max_close,
                    "rejection_reason": "WEAK_BODY_MIDCLOSE_NEUTRAL_SHORT_REJECTION",
                    "v1_18_research_sample": "25 trades; 4W/21L; WR~16.00%; total~-13.02R; R-PF~0.38; negative every tested year",
                },
                "combined_unique_v1_18_sample": "49 trades; 8W/41L; winner:loser ~1:5.1; total~-24.90R",
            },
            "v1_20_dual_refinement": {
                "built_from": "V1.19-LS",
                "filter_count": 2,
                "filter_a_neutral_long_high_body_shallow_pen": {
                    "enabled": self.neutral_long_high_body_shallow_pen_filter,
                    "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_body_ratio_inclusive": self.neutral_long_high_body_shallow_pen_min_body,
                    "maximum_body_ratio_exclusive": self.neutral_long_high_body_shallow_pen_max_body,
                    "minimum_zone_penetration_inclusive": self.neutral_long_high_body_shallow_pen_min_penetration,
                    "maximum_zone_penetration_exclusive": self.neutral_long_high_body_shallow_pen_max_penetration,
                    "rejection_reason": "WEAK_HIGH_BODY_SHALLOW_PEN_NEUTRAL_LONG_REJECTION",
                    "v1_19_research_sample": "23 trades; 3W/20L; WR~13.04%; total~-13.98R; R-PF~0.30; negative every year present (2022-2025)",
                },
                "filter_b_neutral_long_medium_pen_midhigh_confirmation": {
                    "enabled": self.neutral_long_medium_pen_midhigh_confirmation_filter,
                    "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_zone_penetration_inclusive": self.neutral_long_medium_pen_midhigh_min_penetration,
                    "maximum_zone_penetration_exclusive": self.neutral_long_medium_pen_midhigh_max_penetration,
                    "minimum_confirmation_displacement_inclusive": self.neutral_long_medium_pen_midhigh_min_confirmation_displacement,
                    "maximum_confirmation_displacement_exclusive": self.neutral_long_medium_pen_midhigh_max_confirmation_displacement,
                    "rejection_reason": "WEAK_MEDIUM_PEN_MIDHIGH_CONFIRM_NEUTRAL_LONG_REJECTION",
                    "v1_19_research_sample": "24 trades; 4W/20L; WR~16.67%; total~-11.99R; R-PF~0.40; negative every tested year",
                },
                "combined_unique_v1_19_sample": "47 trades; 7W/40L; winner:loser ~1:5.7; total~-25.97R",
            },
            "v1_21_dual_refinement": {
                "built_from": "V1.20-LS",
                "filter_count": 2,
                "filter_a_bearish_short_sweep_weak_confirmation": {
                    "enabled": self.bearish_short_sweep_weak_confirmation_filter,
                    "applies_to": "SHORT + 15M_BEARISH + SWEEP_ONLY",
                    "minimum_rejection_close_position_inclusive": self.bearish_short_sweep_min_close,
                    "maximum_rejection_close_position_exclusive": self.bearish_short_sweep_max_close,
                    "minimum_confirmation_displacement_inclusive": self.bearish_short_sweep_min_confirmation_displacement,
                    "maximum_confirmation_displacement_exclusive": self.bearish_short_sweep_max_confirmation_displacement,
                    "rejection_reason": "WEAK_BEARISH_SHORT_SWEEP_CONFIRMATION",
                    "v1_20_research_sample": "21 trades; 3W/18L; WR~14.29%; winner:loser=1:6.0; total~-12.02R",
                },
                "filter_b_bullish_long_sweep_mid_confirmation": {
                    "enabled": self.bullish_long_sweep_mid_confirmation_filter,
                    "applies_to": "LONG + 15M_BULLISH + SWEEP_ONLY",
                    "minimum_rejection_close_position_inclusive": self.bullish_long_sweep_min_close,
                    "maximum_rejection_close_position_exclusive": self.bullish_long_sweep_max_close,
                    "minimum_confirmation_displacement_inclusive": self.bullish_long_sweep_min_confirmation_displacement,
                    "maximum_confirmation_displacement_exclusive": self.bullish_long_sweep_max_confirmation_displacement,
                    "rejection_reason": "WEAK_BULLISH_LONG_SWEEP_CONFIRMATION",
                    "v1_20_research_sample": "20 trades; 3W/17L; WR~15.00%; winner:loser~1:5.67; total~-11.06R",
                },
                "combined_unique_v1_20_sample": "41 trades; 6W/35L; winner:loser ~1:5.83; total~-23.08R",
            },
            "v1_22_triple_refinement": {
                "built_from": "V1.21-LS",
                "filter_count": 3,
                "filter_a_neutral_long_deep_pen_mid_confirmation": {
                    "enabled": self.neutral_long_deep_pen_mid_confirmation_filter,
                    "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_zone_penetration_inclusive": self.neutral_long_deep_pen_mid_confirmation_min_penetration,
                    "maximum_zone_penetration_exclusive": self.neutral_long_deep_pen_mid_confirmation_max_penetration,
                    "minimum_confirmation_displacement_inclusive": self.neutral_long_deep_pen_mid_confirmation_min_displacement,
                    "maximum_confirmation_displacement_exclusive": self.neutral_long_deep_pen_mid_confirmation_max_displacement,
                    "rejection_reason": "WEAK_DEEP_PEN_MID_CONFIRM_NEUTRAL_LONG_REJECTION",
                    "v1_21_research_sample": "15 trades; 2W/13L; WR~13.33%; winner:loser=1:6.5; total~-8.96R; negative every tested year",
                },
                "filter_b_neutral_long_weak_body_mid_strength": {
                    "enabled": self.neutral_long_weak_body_mid_strength_filter,
                    "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_rejection_body_ratio_inclusive": self.neutral_long_weak_body_mid_strength_min_body,
                    "maximum_rejection_body_ratio_exclusive": self.neutral_long_weak_body_mid_strength_max_body,
                    "minimum_zone_strength_inclusive": self.neutral_long_weak_body_mid_strength_min_zone_strength,
                    "maximum_zone_strength_exclusive": self.neutral_long_weak_body_mid_strength_max_zone_strength,
                    "rejection_reason": "WEAK_BODY_MID_STRENGTH_NEUTRAL_LONG_REJECTION",
                    "v1_21_research_sample": "16 trades; 2W/14L; WR=12.50%; winner:loser=1:7.0; total~-10.18R",
                },
                "filter_c_neutral_long_mid_age_mid_strength": {
                    "enabled": self.neutral_long_mid_age_mid_strength_filter,
                    "applies_to": "LONG + 15M_NEUTRAL + REJECTION_ONLY",
                    "minimum_zone_age_inclusive": self.neutral_long_mid_age_mid_strength_min_age,
                    "maximum_zone_age_exclusive": self.neutral_long_mid_age_mid_strength_max_age,
                    "minimum_zone_strength_inclusive": self.neutral_long_mid_age_mid_strength_min_zone_strength,
                    "maximum_zone_strength_exclusive": self.neutral_long_mid_age_mid_strength_max_zone_strength,
                    "rejection_reason": "WEAK_AGE_MID_STRENGTH_NEUTRAL_LONG_REJECTION",
                    "v1_21_research_sample": "20 trades; 3W/17L; WR=15.00%; winner:loser~1:5.67; total~-11.02R",
                },
                "combined_unique_v1_21_sample": "46 trades; 7W/39L; winner:loser ~1:5.57; total~-25.16R; B/C overlap=5 trades",
            },
            "htf_context": {
                "enabled": self.htf_context_enabled,
                "timeframe_minutes": 15,
                "source_timeframe_minutes": self._detected_source_timeframe_minutes,
                "complete_15m_bars": self._htf_bar_count,
                "short_block": "BULLISH_HH_HL",
                "long_block": "BEARISH_LH_LL",
            },
            "setups": self._diagnostic_rows if self.debug_mode else [],
            "debug_mode": self.debug_mode,
        }
        df.attrs["strategy_diagnostics"] = diagnostics
        return df


Strategy = XAUUSD5MSupplyDemandRejectionV35CandidateA