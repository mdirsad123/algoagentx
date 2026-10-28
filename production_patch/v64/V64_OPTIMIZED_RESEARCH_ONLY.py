

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
    """V3.5 research candidate built on frozen V3.4 research logic."""

    @staticmethod
    def _day_key_from_timestamp(ts):
        return "%04d-%02d-%02d" % (int(ts.year), int(ts.month), int(ts.day))

    @staticmethod
    def _month_key_from_timestamp(ts):
        return "%04d-%02d" % (int(ts.year), int(ts.month))

    @staticmethod
    def _timestamp_text(ts):
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
        neutral_long_shallow_wick_penetration_filter=True,
        neutral_long_shallow_wick_min=0.50,
        neutral_long_shallow_wick_max=0.60,
        neutral_long_shallow_max_penetration=0.20,
        neutral_short_high_body_filter=True,
        neutral_short_high_body_min=0.75,
        neutral_short_high_body_max=0.90,
        neutral_long_midclose_penetration_filter=True,
        neutral_long_midclose_min_close=0.40,
        neutral_long_midclose_max_close=0.50,
        neutral_long_midclose_min_penetration=0.20,
        neutral_long_midclose_max_penetration=0.50,
        neutral_long_stale_weak_confirmation_filter=True,
        neutral_long_stale_min_zone_age=40,
        neutral_long_stale_min_confirmation_displacement=0.10,
        neutral_long_stale_max_confirmation_displacement=0.30,
        neutral_long_medium_pen_weak_confirmation_filter=True,
        neutral_long_medium_pen_min_penetration=0.20,
        neutral_long_medium_pen_max_penetration=0.30,
        neutral_long_medium_pen_min_confirmation_displacement=0.05,
        neutral_long_medium_pen_max_confirmation_displacement=0.20,
        neutral_short_weak_body_midclose_filter=True,
        neutral_short_weak_body_midclose_min_body=0.20,
        neutral_short_weak_body_midclose_max_body=0.40,
        neutral_short_weak_body_midclose_min_close=0.30,
        neutral_short_weak_body_midclose_max_close=0.50,
        neutral_long_high_body_shallow_pen_filter=True,
        neutral_long_high_body_shallow_pen_min_body=0.70,
        neutral_long_high_body_shallow_pen_max_body=0.90,
        neutral_long_high_body_shallow_pen_min_penetration=0.10,
        neutral_long_high_body_shallow_pen_max_penetration=0.20,
        neutral_long_medium_pen_midhigh_confirmation_filter=True,
        neutral_long_medium_pen_midhigh_min_penetration=0.20,
        neutral_long_medium_pen_midhigh_max_penetration=0.30,
        neutral_long_medium_pen_midhigh_min_confirmation_displacement=0.40,
        neutral_long_medium_pen_midhigh_max_confirmation_displacement=0.80,
        bearish_short_sweep_weak_confirmation_filter=True,
        bearish_short_sweep_min_close=0.10,
        bearish_short_sweep_max_close=0.50,
        bearish_short_sweep_min_confirmation_displacement=0.00,
        bearish_short_sweep_max_confirmation_displacement=0.30,
        bullish_long_sweep_mid_confirmation_filter=True,
        bullish_long_sweep_min_close=0.00,
        bullish_long_sweep_max_close=0.40,
        bullish_long_sweep_min_confirmation_displacement=0.40,
        bullish_long_sweep_max_confirmation_displacement=0.60,
        neutral_long_deep_pen_mid_confirmation_filter=True,
        neutral_long_deep_pen_mid_confirmation_min_penetration=0.40,
        neutral_long_deep_pen_mid_confirmation_max_penetration=0.50,
        neutral_long_deep_pen_mid_confirmation_min_displacement=0.20,
        neutral_long_deep_pen_mid_confirmation_max_displacement=0.40,
        neutral_long_weak_body_mid_strength_filter=True,
        neutral_long_weak_body_mid_strength_min_body=0.10,
        neutral_long_weak_body_mid_strength_max_body=0.40,
        neutral_long_weak_body_mid_strength_min_zone_strength=2.50,
        neutral_long_weak_body_mid_strength_max_zone_strength=4.00,
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

        self.neutral_short_high_body_filter = bool(neutral_short_high_body_filter)
        self.neutral_short_high_body_min = max(
            0.0, min(1.0, float(neutral_short_high_body_min))
        )
        self.neutral_short_high_body_max = max(
            self.neutral_short_high_body_min,
            min(1.0, float(neutral_short_high_body_max)),
        )

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

        self.proposal_a_expansion_enabled = bool(proposal_a_expansion_enabled)
        self.proposal_a_min_body_ratio = max(
            0.0, min(1.0, float(proposal_a_min_body_ratio))
        )
        self.proposal_a_max_body_ratio = max(
            self.proposal_a_min_body_ratio,
            min(1.0, float(proposal_a_max_body_ratio)),
        )

        self.proposal_b_expansion_enabled = bool(proposal_b_expansion_enabled)
        self.proposal_b_min_zone_age = max(0, int(proposal_b_min_zone_age))
        self.proposal_b_max_zone_age = max(
            self.proposal_b_min_zone_age, int(proposal_b_max_zone_age)
        )

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

        self._open_trade = None
        self._same_day_loss_streak = 0
        self._loss_streak_day = None
        self._cooldown_remaining = 0


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
        highs = df["High"].to_numpy(copy=False)
        value = float(highs[pivot])
        return value > float(highs[pivot-self.swing_left:pivot].max()) and value >= float(highs[pivot+1:pivot+1+self.swing_right].max())

    def _is_swing_low(self, df, pivot):
        if pivot < self.swing_left or pivot + self.swing_right >= len(df):
            return False
        lows = df["Low"].to_numpy(copy=False)
        value = float(lows[pivot])
        return value < float(lows[pivot-self.swing_left:pivot].min()) and value <= float(lows[pivot+1:pivot+1+self.swing_right].min())

    def _candidate_zone(self, df, pivot, available, sequence, side):
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
        if self._loss_streak_day is not None and current_day != self._loss_streak_day:
            self._same_day_loss_streak = 0
            self._loss_streak_day = current_day
            self._cooldown_remaining = 0


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

        if bias == "NEUTRAL" and interaction != "REJECTION":
            return "NEUTRAL_REQUIRES_REJECTION"

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

        reason = self._neutral_long_shallow_wick_penetration_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_short_high_body_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_midclose_penetration_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_stale_weak_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_medium_pen_weak_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_short_weak_body_midclose_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_high_body_shallow_pen_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._neutral_long_medium_pen_midhigh_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._bearish_short_sweep_weak_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._bullish_long_sweep_mid_confirmation_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

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

        reason = self._v3_2_candidate_a_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._v3_3_candidate_a_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

        reason = self._v3_4_candidate_a_rejection_reason(df, i, active)
        if reason is not None:
            self._reject_confirmed_setup(df, i, active, reason)
            return False

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

        candidates.sort(key=lambda item: (item[0], item[1]))
        for _, __, zone in candidates:
            interaction = self._interaction(df.iloc[i], zone)
            if interaction is not None:
                return zone, interaction
        return None, None


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
            if (i & 63) == 0 and zones:
                zones = [z for z in zones if not (z.broken or z.consumed)]

            self._update_internal_trade(df, i)
            self._reset_day_state_if_needed(current_day)

            idx = df.index[i]
            df.at[idx, "same_day_loss_streak"] = self._same_day_loss_streak
            df.at[idx, "cooldown_remaining"] = self._cooldown_remaining
            df.at[idx, "monthly_entry_count"] = self._entries_by_month.get(current_month, 0)
            df.at[idx, "daily_entry_count"] = self._entries_by_day.get(current_day, 0)

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
                confirmed.sort(key=lambda a: self._confirmation_quality_tuple(df, i, a), reverse=True)
                for a in confirmed:
                    self._try_entry(df, i, a)
                    if a.direction == "SHORT":
                        active_short = None
                    else:
                        active_long = None

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

"""XAUUSD M5 TRENDLINE — V4.23 EXPERIMENTAL STRATEGY BASED ON FROZEN V4.20.

Independent of horizontal support/resistance V3.5. This strategy's outputs
contain TRENDLINE signals exclusively, never imports or executes V3.5.
Causal confirmed-pivot trendline detection, confirmation-after-rejection,
completed HTF candles, 2R targets; returns AlgoAgentX Position/SL/TP columns.
NOT APPROVED FOR LIVE TRADING. V4.23 research-only retest candidate (not accepted). Preserves V4.20 ATR-floor, D1 engulfing veto, and extra wick family; never modify frozen V4.20. Dynamic DB loader compatible; no future-open reads.
V3.8A original engulfing rules retained; adds strong non-engulfing bodies ONLY when
body/range>=0.65, body/ATR>=0.80, confirmed HTF aligned with signal direction.
This is an experimental hypothesis, NOT an accepted profitable trading system.
M5 timezone, costs and actual broker fills must be verified.

Provenance: detector originally authored in AlgoAgentX V3.6 research sidecar;
confirmation and 15M regime code from the offline V3.7 study. Exposed as
standalone strategy for independently reproducible execution replays.
"""
import pandas as pd
import numpy as np
DEFAULTS = dict(left=3, right=3, atr_period=14, min_anchor_separation=6,
                max_anchor_separation=90, max_line_age=180, min_abs_slope_atr=0.025,
                touch_band_atr=0.25, reset_distance_atr=0.50,
                invalidate_close_atr=0.50, tick_size=0.001)


def rolling_atr(df,period):
    prior=df.Close.shift(1)
    tr=pd.concat([df.High-df.Low,(df.High-prior).abs(),(df.Low-prior).abs()],axis=1).max(axis=1)
    return tr.rolling(period,min_periods=period).mean().tolist()

def candle_features(open_,high,low,close,prev_open,prev_close,atr,tick):
    rng=max(high-low,tick)
    body=abs(close-open_)
    return {'body_to_range':body/rng,'body_to_atr':body/max(atr,tick),
            'upper_wick_to_range':(high-max(close,open_))/rng,
            'lower_wick_to_range':(min(close,open_)-low)/rng,
            'close_from_low':(close-low)/rng,
            'bearish_engulfing':bool(close<open_ and prev_close>prev_open and open_>=prev_close and close<=prev_open),
            'bullish_engulfing':bool(close>open_ and prev_close<prev_open and open_<=prev_close and close>=prev_open)}

def detect_trendline_events(df,params=None):
    """Causal high/low pivots; pair adjacent confirmed same-side pivots.

    A newly confirmed anchor is usable from the FOLLOWING candle. Pivots become
    confirmed only after R subsequent closed bars. Each line's first two touches
    are its anchor pivots; a revisit only counts after a full move away and back.
    """
    p={**DEFAULTS,**(params or {})}; n=len(df)
    o,h,l,c=[df[k].to_numpy(dtype=float) for k in ('Open','High','Low','Close')]
    dates=df.Date.tolist(); atr=rolling_atr(df,p['atr_period'])
    last={'SHORT':None,'LONG':None}; lines=[]; events=[]; anchors=[]
    for i in range(n):
        av=atr[i]
        if pd.notna(av) and av>0 and i>0:
            retained=[]
            for line in lines:
                if line['invalidated']: continue
                age=i-line['confirmed_index']
                if age>p['max_line_age']: continue
                side=line['direction']; price=line['anchor2_price']+line['slope']*(i-line['anchor2_index'])
                band=p['touch_band_atr']*av
                reset=p['reset_distance_atr']*av
                if side=='SHORT':
                    away=h[i]<(price-band-reset)
                    overlap=(h[i]>=price-band and l[i]<=price+band)
                    broken=c[i]>(price+p['invalidate_close_atr']*av)
                    rejected=c[i]<price-band
                else:
                    away=l[i]>(price+band+reset)
                    overlap=(l[i]<=price+band and h[i]>=price-band)
                    broken=c[i]<(price-p['invalidate_close_atr']*av)
                    rejected=c[i]>price+band
                if broken:
                    line['invalidated']=True
                    line['invalidated_index']=i
                    continue
                if away:line['armed']=True
                if overlap and line['armed']:
                    line['touches']+=1;line['armed']=False
                    cf=candle_features(o[i],h[i],l[i],c[i],o[i-1],c[i-1],av,p['tick_size'])
                    events.append(dict(event_id=f"{line['line_id']}:{i}",index=i,
                         timestamp=str(dates[i]),direction=side,line_id=line['line_id'],
                         anchor1_index=line['anchor1_index'],anchor2_index=line['anchor2_index'],
                         anchor1_time=str(dates[line['anchor1_index']]),anchor2_time=str(dates[line['anchor2_index']]),
                         anchor1_price=line['anchor1_price'],anchor2_price=line['anchor2_price'],
                         anchor2_confirm_time=str(dates[line['confirmed_index']]),
                         confirmed_index=line['confirmed_index'],slope_price_per_bar=line['slope'],
                         slope_atr=line['slope_atr'],line_price=price,atr=av,
                         touch_number=line['touches'],line_age_bars=age,
                         distance_close_atr=(c[i]-price)/av,
                         state='REJECTION' if rejected else 'TOUCH',
                         **cf))
                retained.append(line)
            lines=retained
        j=i-p['right']
        if j < p['left'] or j<0:continue
        for side,v,arr in [('SHORT',h[j],h),('LONG',l[j],l)]:
            left=arr[j-p['left']:j]; right=arr[j+1:i+1]
            yes=(v>max(left) and v>=max(right)) if side=='SHORT' else (v<min(left) and v<=min(right))
            if not yes:continue
            anchor={'direction':side,'index':j,'time':str(dates[j]),'price':float(v),
                    'confirmed_index':i,'confirmed_time':str(dates[i])}
            anchors.append(anchor)
            a=last[side];last[side]=anchor
            if a is None or not pd.notna(atr[j]) or atr[j]<=0:continue
            sep=j-a['index']
            if sep<p['min_anchor_separation'] or sep>p['max_anchor_separation']:continue
            slope=(float(v)-a['price'])/sep
            slope_atr=slope/atr[j]
            if side=='SHORT' and slope_atr>=-p['min_abs_slope_atr']:continue
            if side=='LONG' and slope_atr<=p['min_abs_slope_atr']:continue
            line_id=f"TL-{side}-{a['index']:07d}-{j:07d}"
            lines.append(dict(line_id=line_id,direction=side,anchor1_index=a['index'],
                              anchor1_price=a['price'],anchor2_index=j,
                              anchor2_price=float(v),confirmed_index=i,
                              slope=slope,slope_atr=slope_atr,touches=2,
                              armed=False,invalidated=False))
    return pd.DataFrame(events),pd.DataFrame(anchors)

def htf_bias(raw):
    """Match V3.5 complete-15m and confirmed-HTF-swings logic (2 left/2 right), by M5 close time."""
    m5=raw[['Date','Open','High','Low','Close']].copy()
    m5=m5.set_index('Date')
    rule='15min';oh=m5.resample(rule,closed='left',label='left').agg({'Open':'first','High':'max','Low':'min','Close':'last'})
    count=m5.Close.resample(rule,closed='left',label='left').count()
    oh=oh[count.eq(3)].dropna(subset=['Open','High','Low','Close']).reset_index()
    highs=oh.High.to_numpy();lows=oh.Low.to_numpy();n=len(oh)
    values=np.zeros(n,dtype=np.int8)
    confirmed_high=[];confirmed_low=[]
    for j in range(n):
        k=j-2
        if k>=2:
            v=highs[k]
            if v>max(highs[k-2:k]) and v>=max(highs[k+1:j+1]):confirmed_high.append(v)
            v=lows[k]
            if v<min(lows[k-2:k]) and v<=min(lows[k+1:j+1]):confirmed_low.append(v)
        if len(confirmed_high)>=2 and len(confirmed_low)>=2:
            a,b=confirmed_high[-2:];c,d=confirmed_low[-2:]
            values[j]=1 if b>a and d>c else (-1 if b<a and d<c else 0)
    available=(oh.Date+pd.Timedelta(minutes=15)).to_numpy(dtype='datetime64[ns]')
    dec=(raw.Date+pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
    idx=np.searchsorted(available,dec,side='right')-1
    res=np.zeros(len(raw),dtype=np.int8);valid=idx>=0;res[valid]=values[idx[valid]]
    return res

def generate_candidates(raw,events,bias,predeclared=None):
    """At event/rejection bar i, find FIRST confirmation among next four CLOSED M5 bars.
    All line pivots/anchors and event are known by i close. Signals at bar j CLOSE,
    consumed at j+1 OPEN. Stop from rejection-candle extreme +/- 0.50; target 2R
    using confirmation close, exactly like V3.5's indicative semantics.
    """
    n=len(raw); dt=pd.Index(raw.Date); o=raw.Open.to_numpy();h=raw.High.to_numpy();l=raw.Low.to_numpy();c=raw.Close.to_numpy()
    minutes=raw.Date.diff().dt.total_seconds().fillna(0).div(60).to_numpy()
    ev=events.loc[events.state.eq('REJECTION')].copy()
    times=pd.to_datetime(ev.timestamp);ix=dt.get_indexer(times)
    ev=ev.loc[ix>=0].copy();ix=ix[ix>=0]
    proposed=[];statistics={'events_total':len(events),'rejection_events':len(ev),'eligible_event_without_signal':0,
                           'context_veto':0,'invalid_stop':0,'invalid_next_open':0,'same_bar_conflicts':0,'not_confirmed':0,'confirmed_proposals':0}
    for k,(entry,i) in enumerate(zip(ev.itertuples(index=False),ix)):
        side=entry.direction; sign=-1 if side=='SHORT' else 1
        if i<30 or i>=n-1:continue
        if entry.touch_number<3:continue
        if entry.confirmed_index>=entry.index:raise AssertionError('Future-pivot leakage')
        found=False
        for j in range(int(i)+1,min(int(i)+5,n)):
            if minutes[j]!=5:break
            if (sign==-1 and c[j]<l[i]) or (sign==1 and c[j]>h[i]):
                found=True;statistics['confirmed_proposals']+=1
                if (sign==-1 and bias[j]==1) or (sign==1 and bias[j]==-1):
                    statistics['context_veto']+=1;break
                stop=float(h[i]+0.5) if sign==-1 else float(l[i]-0.5)
                risk=abs(float(c[j])-stop)
                target=float(c[j]-2*risk) if sign==-1 else float(c[j]+2*risk)
                if risk<=0 or (sign==-1 and stop<=c[j]) or (sign==1 and stop>=c[j]):
                    statistics['invalid_stop']+=1;break
                proposed.append({'signal_index':int(j),'signal_time':str(raw.Date.iloc[j]),
                  'entry_time':None,'side':side,'signal':sign,'sl':stop,'tp':target,
                  'indicative_entry':float(c[j]),'expected_next_open':None,
                  'line_id':entry.line_id,'event_id':entry.event_id,'rejection_index':int(i),
                  'rejection_time':str(raw.Date.iloc[i]),'anchor_confirm_time':entry.anchor2_confirm_time,
                  'touch_number':int(entry.touch_number),'body_to_range':float(entry.body_to_range),
                  'body_to_atr':float(entry.body_to_atr),'atr':float(entry.atr),
                  'slope_atr':float(entry.slope_atr),'htf_bias_at_confirmation':int(bias[j]),
                  'event_bearish_engulfing':str(entry.bearish_engulfing),
                  'event_bullish_engulfing':str(entry.bullish_engulfing),
                  'confirmation_bars':int(j-i)})
                break
        if not found:statistics['not_confirmed']+=1
    props=pd.DataFrame(proposed)
    if props.empty:return props,statistics
    props=props.sort_values(['signal_index','rejection_index','line_id']).drop_duplicates('signal_index',keep='first').reset_index(drop=True)
    statistics['unique_signal_bars']=len(props)
    return props,statistics


def generate_confirmed_zone_retests(m5, events, bias, atr_period=14):
    """Causal broken-zone retest. Signals at retest k CLOSE; executed k+1 OPEN.
    Breakout j must be after a confirmed trendline touch i and occurs within
    4 contiguous M5 bars; retest k within 12 subsequent contiguous M5 bars.
    At k, all source bars, trendline anchors, ATR and completed M15 bias are known.
    NO outcome lookups, no future-open data, no V3.5 trade sources.
    """
    n=len(m5)
    o,h,l,c=[m5[x].to_numpy(dtype=float) for x in ('Open','High','Low','Close')]
    dates=m5.Date.to_numpy()
    dt=pd.Index(m5.Date)
    gap=m5.Date.diff().dt.total_seconds().div(60).fillna(0).to_numpy()
    a=np.asarray(rolling_atr(m5,atr_period),dtype=float)
    proposed=[]
    if events.empty:return pd.DataFrame()
    for r in events.itertuples(index=False):
        if int(r.touch_number)<3:continue
        i=int(r.index)
        if i<20 or i>=n-1 or int(r.confirmed_index)>=i:continue
        side=1 if str(r.direction)=='SHORT' else -1
        for j in range(i+1,min(i+5,n)):
            if gap[j]!=5:break
            av=a[j]
            if not np.isfinite(av) or av<=0:continue
            line=float(r.line_price)+float(r.slope_price_per_bar)*(j-i)
            if side==1:
                crossed=c[j]>line+.50*av
                already_outside=c[j-1]>line+.50*av
            else:
                crossed=c[j]<line-.50*av
                already_outside=c[j-1]<line-.50*av
            if not crossed:continue
            if already_outside:break
            span=max(float(h[j]-l[j]),.001)
            body_atr=abs(float(c[j]-o[j]))/av
            proposed.append({'break_index':j,'reference_index':i,'line_id':str(r.line_id),
                 'event_id':str(r.event_id),'slope':float(r.slope_price_per_bar),'line_price':float(r.line_price),
                 'side':side,'body_atr':body_atr,'m15_at_break':int(bias[j]), 'source_touch':int(r.touch_number)})
            break
    if not proposed:return pd.DataFrame()
    breaks=pd.DataFrame(proposed)
    breaks=breaks.sort_values(['break_index','body_atr','event_id'],ascending=[True,False,True],kind='stable').drop_duplicates('break_index').reset_index(drop=True)
    ret=[]
    for b in breaks.itertuples(index=False):
        j=int(b.break_index);i=int(b.reference_index);side=int(b.side)
        for k in range(j+1,min(j+13,n)):
            if gap[k]!=5:break
            av=a[k]
            if not np.isfinite(av) or av<=0:continue
            line=float(b.line_price)+float(b.slope)*(k-i)
            band=.35*av
            span=max(float(h[k]-l[k]),.001)
            if side==1:
                contact=(l[k]<=line+band and h[k]>=line-band)
                good=(c[k]>line+band*.25 and c[k]>o[k] and (c[k]-l[k])/span>=.60)
                stop=float(l[k]-.50)
            else:
                contact=(h[k]>=line-band and l[k]<=line+band)
                good=(c[k]<line-band*.25 and c[k]<o[k] and (h[k]-c[k])/span>=.60)
                stop=float(h[k]+.50)
            if contact and good and side*(c[k]-stop)>0:
                body=abs(float(c[k]-o[k]))/av
                risk=abs(float(c[k]-stop))
                ret.append({'signal_index':k,'signal_time':str(m5.Date.iloc[k]),
                   'signal':side,'side':'LONG' if side==1 else 'SHORT',
                   'sl':stop,'tp':float(c[k]+2*side*risk),'body_atr_retest':body,
                   'aligned_break':bool(int(b.m15_at_break)==side),
                   'event_id':'RETEST:'+str(b.event_id)+':'+str(j)+':'+str(k),
                   'line_id':b.line_id,'rejection_index':int(b.reference_index)})
                break
    if not ret:return pd.DataFrame()
    tab=pd.DataFrame(ret).sort_values(['signal_index','body_atr_retest','event_id'],ascending=[True,False,True],kind='stable')
    return tab.drop_duplicates('signal_index').reset_index(drop=True)

class XAUUSD_M5_Trendline_V424_LongRetestOnly_EXPERIMENT:
    """Standalone XAUUSD M5 trendline-only strategy compatible with AlgoAgentX data frame semantics.

    Constructor defaults: frozen V4.20 engulfing, strong-body and extra-wick families plus existing V4.19 causal veto rules. Each added V4.22/V4.23 feature is research-only and
    requires forward validation before any live use.
    """
    LIVE_HISTORY_BARS = 2000  # Match research V3.8A; warm-up length needs forward parity verification
    def __init__(self,df,**kwargs):
        self.df=df.copy()
        self.min_body_ratio=float(kwargs.get('min_body_ratio',0.0))
        self.min_body_atr=float(kwargs.get('min_body_atr',0.0))
        self.max_confirmation_bars=int(kwargs.get('max_confirmation_bars',4))
        self.max_touch_number=int(kwargs.get('max_touch_number',0))
        self.direction=str(kwargs.get('direction','BOTH')).upper()
        self.require_engulfing=bool(kwargs.get('require_engulfing',True))
        self.add_strong_non_engulf=bool(kwargs.get('add_strong_non_engulf',True))
        self.expansion_min_body_range=float(kwargs.get('expansion_min_body_range',0.65))
        self.expansion_min_body_atr=float(kwargs.get('expansion_min_body_atr',0.80))
        self.min_atr_regime=float(kwargs.get('min_atr_regime',0.65))
        self.skip_prev_day_aligned_engulf=bool(kwargs.get('skip_prev_day_aligned_engulf',True))
        self.add_wick_counter_htf=bool(kwargs.get('add_wick_counter_htf',True))
        self.enable_v423_retest=bool(kwargs.get('enable_v423_retest',True))
        self.v423_min_retest_body_atr=float(kwargs.get('v423_min_retest_body_atr',0.60))
        self.v423_require_m15_break_alignment=bool(kwargs.get('v423_require_m15_break_alignment',True))
        self.v424_retest_long_only=bool(kwargs.get('v424_retest_long_only',True))
        self.detector_params=kwargs.get('detector_params',{})
        self._diagnostics={}

    def generate(self):
        df=self.df.copy().reset_index(drop=True)
        required={'Date','Open','High','Low','Close'}
        if not required.issubset(df.columns):
            raise ValueError('Missing columns: '+str(sorted(required-set(df.columns))))
        df['Date']=pd.to_datetime(df.Date)
        if df.Date.duplicated().any() or not df.Date.is_monotonic_increasing:
            raise ValueError('Requires strictly increasing unique M5 timestamps')
        diffs=df.Date.diff().dt.total_seconds().div(60)
        start=int(np.flatnonzero(diffs.eq(5).to_numpy())[0])-1 if bool(diffs.eq(5).any()) else 0
        if start < 0:start=0
        m5=df.iloc[start:].copy().reset_index(drop=True)
        if len(m5)<40:raise ValueError('At least 40 M5 candles required')
        if float(m5.Date.diff().dt.total_seconds().div(60).dropna().median())!=5:
            raise ValueError('Source is not predominantly M5')
        events, pivots=detect_trendline_events(m5,self.detector_params)
        if not events.empty:
            bias=htf_bias(m5)
            candidate,stats=generate_candidates(m5,events,bias)
        else: candidate=pd.DataFrame();stats={}
        if not candidate.empty:
            if self.direction in ('SHORT','LONG'):
                candidate=candidate[candidate.side.eq(self.direction)]
            if self.min_body_ratio>0:
                candidate=candidate[candidate.body_to_range>=self.min_body_ratio]
            if self.min_body_atr>0:
                candidate=candidate[candidate.body_to_atr>=self.min_body_atr]
            if self.max_confirmation_bars<4:
                candidate=candidate[candidate.confirmation_bars<=self.max_confirmation_bars]
            if self.max_touch_number>0:
                candidate=candidate[candidate.touch_number<=self.max_touch_number]
            if self.require_engulfing:
                engulf=((candidate.side.eq('SHORT') & candidate.event_bearish_engulfing.astype(str).str.lower().eq('true')) | (candidate.side.eq('LONG') & candidate.event_bullish_engulfing.astype(str).str.lower().eq('true')))
                if self.add_strong_non_engulf:
                    extra=(~engulf & (candidate.body_to_range>=self.expansion_min_body_range) & (candidate.body_to_atr>=self.expansion_min_body_atr) & (candidate.htf_bias_at_confirmation==candidate.signal))
                    wick_extra=pd.Series(False,index=candidate.index)
                    if self.add_wick_counter_htf:
                        ri=candidate.rejection_index.to_numpy(dtype=int)
                        op=m5.Open.to_numpy(dtype=float)[ri]
                        hi=m5.High.to_numpy(dtype=float)[ri]
                        lo=m5.Low.to_numpy(dtype=float)[ri]
                        cl=m5.Close.to_numpy(dtype=float)[ri]
                        span=np.maximum(hi-lo,0.001)
                        upp=(hi-np.maximum(op,cl))/span
                        low=(np.minimum(op,cl)-lo)/span
                        close_pos=(cl-lo)/span
                        side=candidate.signal.to_numpy(dtype=int)
                        rejecting_wick=np.where(side<0,upp,low)
                        close_quality=np.where(side<0,1.0-close_pos,close_pos)
                        counter_htf=candidate.htf_bias_at_confirmation.to_numpy(dtype=int)!=side
                        wick_extra=pd.Series(
                            (~engulf.to_numpy(dtype=bool)) &
                            (~extra.to_numpy(dtype=bool)) &
                            counter_htf &
                            (rejecting_wick>=0.45) &
                            (close_quality>=0.75) &
                            (candidate.body_to_atr.to_numpy(dtype=float)>=0.40),
                            index=candidate.index)
                    candidate=candidate[engulf | extra | wick_extra]
                else:
                    candidate=candidate[engulf]
        if not candidate.empty and self.skip_prev_day_aligned_engulf:
            daily=m5.set_index('Date')[['Open','Close']].resample('1D',closed='left',label='left').agg({'Open':'first','Close':'last'})
            daily_count=m5.set_index('Date')['Close'].resample('1D',closed='left',label='left').count()
            daily.loc[daily_count.lt(30), ['Open','Close']]=float('nan')
            prev_dates=pd.to_datetime(candidate.signal_time).dt.normalize()-pd.Timedelta(days=1)
            d1=daily.reindex(pd.DatetimeIndex(prev_dates))
            prev_direction=np.sign((d1.Close-d1.Open).to_numpy(dtype=float))
            engulf=((candidate.side.eq('SHORT') & candidate.event_bearish_engulfing.astype(str).str.lower().eq('true')) | (candidate.side.eq('LONG') & candidate.event_bullish_engulfing.astype(str).str.lower().eq('true')))
            skip=engulf.to_numpy(dtype=bool) & np.isfinite(prev_direction) & (prev_direction==candidate.signal.to_numpy(dtype=int))
            candidate=candidate.loc[~skip].copy()
        if not candidate.empty and self.min_atr_regime>0:
            a14=pd.Series(rolling_atr(m5,14),dtype=float)
            previous_median=a14.shift(1).rolling(288,min_periods=144).median()
            loc=candidate.signal_index.to_numpy(dtype=int)
            reference=previous_median.iloc[loc].to_numpy(dtype=float)
            regime=candidate.atr.to_numpy(dtype=float)/reference
            candidate=candidate.loc[np.isfinite(regime)&(regime>=self.min_atr_regime)].copy()
        if self.enable_v423_retest and not events.empty:
            retests=generate_confirmed_zone_retests(m5,events,bias)
            if not retests.empty:
                if self.v423_require_m15_break_alignment:
                    retests=retests.loc[retests.aligned_break].copy()
                if self.v423_min_retest_body_atr>0:
                    retests=retests.loc[retests.body_atr_retest>=self.v423_min_retest_body_atr].copy()
                if self.v424_retest_long_only:
                    retests=retests.loc[retests.signal==1].copy()
                if not retests.empty:
                    occupied=set(candidate.signal_index.to_list()) if not candidate.empty else set()
                    retests=retests.loc[~retests.signal_index.isin(occupied)].copy()
                    if not retests.empty:
                        candidate=pd.concat([candidate,retests],ignore_index=True,sort=False)
                        candidate=candidate.sort_values('signal_index',kind='stable')
        df['Position']=0
        df['strategy_stop_loss']=float('nan')
        df['strategy_target']=float('nan')
        df['signal_reason']=''
        if not candidate.empty:
            for r in candidate.itertuples(index=False):
                j=int(r.signal_index)+start
                df.at[j,'Position']=int(r.signal)
                df.at[j,'strategy_stop_loss']=float(r.sl)
                df.at[j,'strategy_target']=float(r.tp)
                df.at[j,'signal_reason']='TRENDLINE_V424_LONG_RETEST_RESEARCH|'+str(r.event_id)
        self._diagnostics={'events':len(events),'pivots':len(pivots),
                           'raw_candidates':stats.get('unique_signal_bars',0),
                           'selected_signals':len(candidate),
                           'excluded_nonm5_prefix_rows':start,
                           'selection_params':{'min_body_ratio':self.min_body_ratio,'min_body_atr':self.min_body_atr,
                                               'max_confirmation_bars':self.max_confirmation_bars,
                                               'max_touch_number':self.max_touch_number,
                                               'direction':self.direction,'require_engulfing':self.require_engulfing,
                                               'add_strong_non_engulf':self.add_strong_non_engulf,
                                               'min_atr_regime':self.min_atr_regime,
                                               'skip_prev_day_aligned_engulf':self.skip_prev_day_aligned_engulf,
                                               'add_wick_counter_htf':self.add_wick_counter_htf,
                                               'expansion_min_body_range':self.expansion_min_body_range,
                                               'expansion_min_body_atr':self.expansion_min_body_atr}}
        df.attrs['trendline_research_diagnostics']=self._diagnostics
        return df

Strategy=XAUUSD_M5_Trendline_V424_LongRetestOnly_EXPERIMENT


def generate_event_signals(m5,events,bias,family='ZONE_WICK',params=None):
 p={'min_touch':3,'min_wick':.45,'min_close':.65,'min_body_atr':.15,'zone_atr':.20,'confirmation':1,'risk_min':.6,'risk_max':25.,'bias_required':0,'min_slope':0.025}
 p.update(params or {}); n=len(m5)
 o,h,l,c=[m5[k].to_numpy(dtype=float) for k in ('Open','High','Low','Close')]; dt=m5.Date; minutes=dt.diff().dt.total_seconds().div(60).fillna(0).to_numpy()
 candidates=[]
 for r in events.itertuples(index=False):
  i=int(r.index);side=1 if str(r.direction)=='LONG' else -1
  if i<290 or i>=n-1 or minutes[i+1]!=5 or int(r.touch_number)<p['min_touch'] or abs(float(r.slope_atr))<p['min_slope']: continue
  av=float(r.atr)
  if not np.isfinite(av) or av<=0:continue
  span=max(h[i]-l[i],.001); wick=(min(o[i],c[i])-l[i])/span if side==1 else (h[i]-max(o[i],c[i]))/span
  close=(c[i]-l[i])/span if side==1 else (h[i]-c[i])/span
  line=float(r.line_price)
  penetration=(line-l[i])/av if side==1 else (h[i]-line)/av
  if family=='ZONE_WICK':
   if str(r.state)!='REJECTION' or wick<p['min_wick'] or close<p['min_close'] or abs(c[i]-o[i])/av<p['min_body_atr']:continue
  elif family=='SWEEP_RECLAIM':
   if wick<p['min_wick'] or close<p['min_close'] or penetration<p['zone_atr']:continue
   if not (side*(c[i]-line)>0):continue
  elif family=='COUNTER_SLOPE':
   if str(r.state)!='REJECTION' or wick<p['min_wick'] or close<p['min_close']:continue
  else: raise ValueError(family)
  j=i+int(p['confirmation'])
  if j>=n or np.any(minutes[i+1:j+1]!=5):continue
  if p['confirmation']==1:
   directional=side*(c[j]-o[j])>0 and side*(c[j]-c[i])>0
  else:
   directional=side*(c[j]-o[j])>0 and side*(c[j]-c[i])>0 and side*(c[j]-c[j-1])>0
  if not directional:continue
  if p['bias_required']==1 and int(bias[j])!=side:continue
  if p['bias_required']==-1 and int(bias[j])==-side:continue
  sl=float(l[i]-.5) if side==1 else float(h[i]+.5)
  risk=side*(c[j]-sl)
  if risk<p['risk_min'] or risk>p['risk_max']:continue
  tp=float(c[j]+2*side*risk)
  candidates.append({'signal_index':j,'Date':dt.iloc[j],'Position':side,'strategy_stop_loss':sl,'strategy_target':tp,
   'signal_reason':f'{family}|{r.line_id}|{i}|{j}', 'family':family,'touch':int(r.touch_number),'atr':av,'wick':float(wick),'close_pos':float(close),
   'body_atr':float(abs(c[i]-o[i])/av),'slope_atr':float(r.slope_atr),'confirmation':j-i,'bias':int(bias[j]),'risk':float(risk),
   'hour_utc':int(dt.iloc[j].hour),'year':int(dt.iloc[j].year),'source_index':i,'line_id':str(r.line_id)})
 if not candidates:return pd.DataFrame(columns=['signal_index','Date','Position','strategy_stop_loss','strategy_target','signal_reason','family'])
 t=pd.DataFrame(candidates).sort_values(['signal_index','wick','source_index','line_id'],ascending=[True,False,True,True],kind='stable').drop_duplicates('signal_index').reset_index(drop=True)
 return t


class XAUUSD_Trendline_V427_TwoBarZone_RESEARCH_ONLY(XAUUSD_M5_Trendline_V424_LongRetestOnly_EXPERIMENT):
    """SANDBOX RESEARCH ONLY. Preserves V4.24 core unchanged; adds causal 2-bar zone signals.
    Screen was chosen from inspected history; no untouched future data validates it.
    No live permission. Refer to companion report for secondary CSV limits.
    """
    def generate(self):
        base = super().generate()
        m5 = base[['Date', 'Open', 'High', 'Low', 'Close']].copy().reset_index(drop=True)
        diffs = m5.Date.diff().dt.total_seconds().div(60)
        ix = int(np.flatnonzero(diffs.eq(5).to_numpy())[0])-1 if bool(diffs.eq(5).any()) else 0
        ix = max(0,ix)
        genuine = m5.iloc[ix:].reset_index(drop=True)
        ev, _ = detect_trendline_events(genuine, self.detector_params)
        if ev.empty: return base
        bias = htf_bias(genuine)
        new = generate_event_signals(genuine, ev, bias, 'ZONE_WICK',
             {'confirmation':2,'min_wick':.35,'min_close':.60})
        if new.empty: return base
        new = new.loc[(new.wick >= 0.35) &
            (new.close_pos >= 0.55) &
            (new.body_atr >= 0.1) &
            (new.touch >= 3) &
            (new.slope_atr.abs() >= 0.1) &
            (new.risk <= 10.0)].copy()
        new = new.loc[new.bias != -new.Position].copy()
        new = new.loc[new.Date.dt.hour.between(0,7)].copy()
        for r in new.itertuples(index=False):
            j = int(r.signal_index) + ix
            if j < 0 or j >= len(base) or int(base.at[j,'Position']) != 0:
                continue
            base.at[j,'Position'] = int(r.Position)
            base.at[j,'strategy_stop_loss'] = float(r.strategy_stop_loss)
            base.at[j,'strategy_target'] = float(r.strategy_target)
            base.at[j,'signal_reason'] = 'TRENDLINE_V427_RESEARCH_ONLY|' + str(r.signal_reason)
        return base

Strategy = XAUUSD_Trendline_V427_TwoBarZone_RESEARCH_ONLY


class V428_FilteredZone_RESEARCH_ONLY(XAUUSD_Trendline_V427_TwoBarZone_RESEARCH_ONLY):
    def generate(self):
        df=super().generate()
        date=pd.to_datetime(df['Date'])
        prev=df['Close'].shift(1)
        tr=pd.concat([df.High-df.Low,(df.High-prev).abs(),(df.Low-prev).abs()],axis=1).max(axis=1)
        atr=tr.rolling(14,min_periods=14).mean()
        historical_med=atr.shift(1).rolling(288,min_periods=144).median()
        atr_ratio=atr/historical_med
        span=(df.High-df.Low).clip(lower=.001)
        pos=df['Position'].to_numpy(dtype=int)
        long_quality=((df.Close-df.Low)/span).to_numpy(dtype=float)
        short_quality=((df.High-df.Close)/span).to_numpy(dtype=float)
        quality=np.where(pos==1,long_quality,short_quality)
        stop_distance=(df.Close-df.strategy_stop_loss).abs()
        tag=df['signal_reason'].astype(str).str.startswith('TRENDLINE_V427_RESEARCH_ONLY|')
        valid=(atr_ratio.ge(.60) & (quality>=.65) & stop_distance.ge(1.0) & stop_distance.le(15.0))
        drop=tag & ~valid
        df.loc[drop,'Position']=0
        df.loc[drop,'strategy_stop_loss']=float('nan')
        df.loc[drop,'strategy_target']=float('nan')
        df.loc[drop,'signal_reason']=''
        df.attrs['v428_research']={'rule': 'ATR regime >=.60 AND last-confirmation close position >=.65 AND indicative stop risk >=1 USD/oz; inspected-stress exploratory','rejected_new_signals':int(drop.sum()),'retained_new_signals':int((tag&valid).sum())}
        return df

Strategy=V428_FilteredZone_RESEARCH_ONLY


class V429_TrainSelectedATRSession_RESEARCH_ONLY(V428_FilteredZone_RESEARCH_ONLY):
    def generate(self):
        frame=super().generate()
        ts=pd.to_datetime(frame['Date'])
        prev=frame['Close'].shift(1)
        tr=pd.concat([frame.High-frame.Low,
                      (frame.High-prev).abs(),(frame.Low-prev).abs()],axis=1).max(axis=1)
        atr=tr.rolling(14,min_periods=14).mean()
        med=atr.shift(1).rolling(288,min_periods=144).median()
        regime=atr/med
        stop_distance=(frame.Close-frame.strategy_stop_loss).abs()
        allow=(regime>=0.65)&(regime<=20)&(stop_distance<=25)&(ts.dt.hour<8)
        new_zone=frame.signal_reason.astype(str).str.startswith('TRENDLINE_V427_RESEARCH_ONLY|')
        veto=new_zone & ~allow
        frame.loc[veto,'Position']=0
        frame.loc[veto,'strategy_stop_loss']=float('nan')
        frame.loc[veto,'strategy_target']=float('nan')
        frame.loc[veto,'signal_reason']=''
        frame.attrs['V429_SANDBOX_FILTERS']={'veto_new_zone':int(veto.sum()),
                                             'filter_source':'2022-2023, historically inspected',
                                             'activation':'RESEARCH_ONLY'}
        return frame
Strategy=V429_TrainSelectedATRSession_RESEARCH_ONLY


def _v430_completed_bar_direction(candles, rule, count_required, duration_min):
    d = candles.set_index('Date')
    bars = d[['Open','Close']].resample(rule, closed='left', label='left').agg({'Open':'first','Close':'last'})
    count = d.Close.resample(rule, closed='left', label='left').count()
    completed = bars[count.eq(count_required)].dropna()
    available = (completed.index + pd.Timedelta(minutes=duration_min)).to_numpy(dtype='datetime64[ns]')
    candle_closes = (candles.Date + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
    idx = np.searchsorted(available, candle_closes, side='right') - 1
    out = np.zeros(len(candles), dtype=np.int8)
    valid = idx >= 0
    if valid.any():
        out[valid] = np.sign((completed.Close-completed.Open).to_numpy(dtype=float))[idx[valid]].astype(np.int8)
    return out


def _v430_add_new_entries(owner, frozen_frame, variant):
    out = frozen_frame.copy()
    d = out.Date.diff().dt.total_seconds().div(60)
    first = int(np.flatnonzero(d.eq(5).to_numpy())[0])-1 if bool(d.eq(5).any()) else 0
    first = max(first, 0)
    m5 = out.iloc[first:][['Date','Open','High','Low','Close']].copy().reset_index(drop=True)
    if len(m5) < 300:
        return out
    events, _ = detect_trendline_events(m5, owner.detector_params)
    if events.empty:
        return out
    bias = htf_bias(m5)
    if variant == 'A':
        conf, min_quality, min_ratio, risk_max, min_wick, htf = 2, .80, .60, 10.0, .30, 'BOTH'
    elif variant == 'B':
        conf, min_quality, min_ratio, risk_max, min_wick, htf = 1, .55, 1.00, 20.0, .30, 'H1'
    else:
        raise ValueError('Unknown V430 research variant')
    proposed = generate_event_signals(m5, events, bias, 'SWEEP_RECLAIM', {
        'confirmation':conf, 'min_touch':3, 'min_wick':.30, 'min_close':.55,
        'min_body_atr':.0, 'zone_atr':.05, 'risk_min':.50,
        'risk_max':30.0, 'min_slope':.025})
    if proposed.empty:
        return out
    ix = proposed.signal_index.to_numpy(dtype=int)
    preceding = m5.Close.shift(1)
    tr = pd.concat([m5.High-m5.Low, (m5.High-preceding).abs(),
                    (m5.Low-preceding).abs()],axis=1).max(axis=1)
    atr = tr.rolling(14,min_periods=14).mean()
    atr_regime = (atr / atr.shift(1).rolling(288,min_periods=144).median()).iloc[ix].to_numpy()
    span = np.maximum((m5.High-m5.Low).iloc[ix].to_numpy(dtype=float),.001)
    closeq = np.where(proposed.Position.to_numpy(dtype=int)==1,
          ((m5.Close-m5.Low).iloc[ix].to_numpy(dtype=float)/span),
          ((m5.High-m5.Close).iloc[ix].to_numpy(dtype=float)/span))
    direction = proposed.Position.to_numpy(dtype=int)
    h1 = _v430_completed_bar_direction(m5,'1h',12,60)[ix]
    h4 = _v430_completed_bar_direction(m5,'4h',48,240)[ix]
    aligned = (h1==direction) if htf=='H1' else ((h1==direction)&(h4==direction))
    selected = ((direction==-1) & (closeq>=min_quality) &
                (atr_regime>=min_ratio) & (proposed.risk.to_numpy(dtype=float)<=risk_max) &
                (proposed.risk.to_numpy(dtype=float)>=.5) &
                (proposed.wick.to_numpy(dtype=float)>=min_wick) &
                (proposed.touch.to_numpy(dtype=int)>=3) & aligned)
    new = proposed.loc[selected].copy()
    count_added=0
    for r in new.itertuples(index=False):
        global_index = int(r.signal_index)+first
        if global_index>=len(out) or int(out.at[global_index,'Position'])!=0:
            continue  # V4.29 always retains signal priority
        out.at[global_index,'Position']=int(r.Position)
        out.at[global_index,'strategy_stop_loss']=float(r.strategy_stop_loss)
        out.at[global_index,'strategy_target']=float(r.strategy_target)
        out.at[global_index,'signal_reason']='TRENDLINE_V430'+variant+'_RESEARCH_ONLY|'+str(r.signal_reason)
        count_added+=1
    out.attrs['v430_research']={'variant':variant,'new_selected':int(len(new)),
        'added_signal_bars':count_added,'historical_inspected_data':True,
        'deploy_to_live':False}
    return out

class V430A_Sweep2_RESEARCH_ONLY(V429_TrainSelectedATRSession_RESEARCH_ONLY):
    def generate(self):
        return _v430_add_new_entries(self,super().generate(),'A')

class V430B_Sweep1_RESEARCH_ONLY(V429_TrainSelectedATRSession_RESEARCH_ONLY):
    def generate(self):
        return _v430_add_new_entries(self,super().generate(),'B')


Strategy=V430B_Sweep1_RESEARCH_ONLY

def _v431_add_entries(owner, frozen_frame, mode):
    out=frozen_frame.copy()
    gaps=out.Date.diff().dt.total_seconds().div(60)
    start=int(np.flatnonzero(gaps.eq(5).to_numpy())[0])-1 if bool(gaps.eq(5).any()) else 0
    start=max(0,start)
    m5=out.iloc[start:][['Date','Open','High','Low','Close']].copy().reset_index(drop=True)
    if len(m5)<300:return out
    events,_=detect_trendline_events(m5,owner.detector_params)
    if events.empty:return out
    bias=htf_bias(m5)
    if mode=='A':
        family='ZONE_WICK';confirmation=3
        min_close,min_ratio,min_wick,max_risk,min_touch,bodymin=.85,1.10,.60,10.,4,0.
        htf='NONE'
    elif mode=='B':
        family='SWEEP_RECLAIM';confirmation=2
        min_close,min_ratio,min_wick,max_risk,min_touch,bodymin=.55,.80,.45,20.,3,.40
        htf='H1'
    else:raise ValueError('Invalid research mode')
    proposals=generate_event_signals(m5,events,bias,family,{
      'confirmation':confirmation,'min_touch':3,'min_wick':.30,
      'min_close':.55,'min_body_atr':0.,'zone_atr':.05,
      'risk_min':.5,'risk_max':30.,'min_slope':.025})
    if proposals.empty:return out
    ix=proposals.signal_index.to_numpy(dtype=int)
    previous=m5.Close.shift(1)
    true_range=pd.concat([m5.High-m5.Low,(m5.High-previous).abs(),(m5.Low-previous).abs()],axis=1).max(axis=1)
    atr=true_range.rolling(14,min_periods=14).mean()
    regime=(atr/atr.shift(1).rolling(288,min_periods=144).median()).iloc[ix].to_numpy(dtype=float)
    span=np.maximum((m5.High-m5.Low).iloc[ix].to_numpy(dtype=float),.001)
    side=proposals.Position.to_numpy(dtype=int)
    closeq=np.where(side>0,((m5.Close-m5.Low).iloc[ix].to_numpy(dtype=float)/span),
                             ((m5.High-m5.Close).iloc[ix].to_numpy(dtype=float)/span))
    same_h1=_v430_completed_bar_direction(m5,'1h',12,60)[ix]==side
    keep=(closeq>=min_close)&(regime>=min_ratio)&(proposals.wick.to_numpy(dtype=float)>=min_wick)&(
        proposals.risk.to_numpy(dtype=float)>=.50)&(proposals.risk.to_numpy(dtype=float)<=max_risk)&(
        proposals.touch.to_numpy(dtype=int)>=min_touch)&(proposals.body_atr.to_numpy(dtype=float)>=bodymin)
    if htf=='H1':keep &=same_h1
    selected=proposals.loc[keep]
    added=0
    for r in selected.itertuples(index=False):
        gi=int(r.signal_index)+start
        if gi>=len(out) or int(out.at[gi,'Position'])!=0:continue
        out.at[gi,'Position']=int(r.Position)
        out.at[gi,'strategy_stop_loss']=float(r.strategy_stop_loss)
        out.at[gi,'strategy_target']=float(r.strategy_target)
        out.at[gi,'signal_reason']='TRENDLINE_V431'+mode+'_RESEARCH_ONLY|'+str(r.signal_reason)
        added+=1
    out.attrs['v431_research']={'variant':mode,'selected_intents':int(len(selected)),
      'new_signal_bars':int(added),'historical_research_only':True,'live_approved':False}
    return out

class V431_RESEARCH_ONLY(V430B_Sweep1_RESEARCH_ONLY):
    """Standalone V4.30B + causally defined new signals; sandbox research only."""
    def generate(self):return _v431_add_entries(self,super().generate(),RESEARCH_MODE)

RESEARCH_MODE='B'
Strategy=V431_RESEARCH_ONLY



class AlgoAgentX_V62_NewEntries_RESEARCH_ONLY:
    """V3.5 and V4.31B frozen signal generators + deterministic portfolio gate.

    Signal at completed candle i CLOSE; next candle i+1 OPEN may enter.
    Only one accepted position at a time in a conservative stop-first shadow
    tracker. Both source strategies run on identical input candles.
    No lookahead: the next open is read only when processing the next bar.
    """
    LIVE_HISTORY_BARS = 24000  # research hint; full-history parity unverified

    def __init__(self, df, same_bar_priority='V35', conflict_policy='SKIP', v5_filter_enabled=True, v5_filter_rule='RECENT_EXTREME_CLOSE', v52_filter_enabled=True, v52_filter_rule='MOMENTUM_WICK_SESSION', v54_filter_enabled=True, v55_filter_enabled=True, v56_filter_enabled=True, v57_filter_enabled=True, v57_filter_rule="CHOP_EXPANSION", v58_new_entries_enabled=True, v58_rule="STRICT_EARLY_ATR3", v59_new_entries_enabled=True, v61_fvg_new_entries_enabled=True, v62_failed_break_new_entries_enabled=False, v62_compression_long_enabled=True, v63_resist96_enabled=True, v64_gate_enabled=True, **kwargs):
        self.df = df.copy()
        self.same_bar_priority = str(same_bar_priority).upper()
        self.conflict_policy = str(conflict_policy).upper()
        self.v5_filter_enabled = bool(v5_filter_enabled)
        self.v5_filter_rule = str(v5_filter_rule).upper()
        self.v54_filter_enabled = bool(v54_filter_enabled)
        self.v55_filter_enabled = bool(v55_filter_enabled)
        self.v56_filter_enabled = bool(v56_filter_enabled)
        self.v57_filter_enabled = bool(v57_filter_enabled)
        self.v58_new_entries_enabled = bool(v58_new_entries_enabled)
        self.v58_rule = str(v58_rule).upper()
        self.v59_new_entries_enabled = bool(v59_new_entries_enabled)
        self.v61_fvg_new_entries_enabled = bool(v61_fvg_new_entries_enabled)
        self.v62_failed_break_new_entries_enabled = bool(v62_failed_break_new_entries_enabled)
        self.v62_compression_long_enabled = bool(v62_compression_long_enabled)
        self.v63_resist96_enabled = bool(v63_resist96_enabled)
        self.v64_gate_enabled = bool(v64_gate_enabled)
        if self.v58_rule not in ("ATR_MOM48", "STRICT_EARLY", "STRICT_EARLY_ATR3"): raise ValueError("Invalid V5.8 rule")
        self.v57_filter_rule = str(v57_filter_rule).upper()
        if self.v57_filter_rule not in ("FLAT_TREND","CHOP_EXPANSION"):
            raise ValueError("Unsupported v57 filter")
        self.v52_filter_enabled = bool(v52_filter_enabled)
        self.v52_filter_rule = str(v52_filter_rule).upper()
        if self.v52_filter_rule not in ('MOMENTUM_WICK_SESSION', 'LOW_ATR_CLOSE', 'OFF'):
            raise ValueError('Invalid v52_filter_rule')
        if self.v5_filter_rule not in ('RECENT_EXTREME_CLOSE','TRAIN_COUNTERTREND_BODY'):
            raise ValueError('v5_filter_rule must be RECENT_EXTREME_CLOSE or TRAIN_COUNTERTREND_BODY')
        if self.same_bar_priority not in ('V35', 'V431B'):
            raise ValueError('same_bar_priority must be V35 or V431B')
        if self.conflict_policy not in ('SKIP', 'PRIORITY'):
            raise ValueError('conflict_policy must be SKIP or PRIORITY')
        self._stats = {}

    def generate(self):
        raw = self.df.copy().reset_index(drop=True)
        need = ['Date','Open','High','Low','Close']
        if any(k not in raw.columns for k in need):
            raise ValueError('Requires Date Open High Low Close columns')
        raw['Date'] = pd.to_datetime(raw.Date)
        if raw.Date.isna().any() or raw.Date.duplicated().any() or not raw.Date.is_monotonic_increasing:
            raise ValueError('Input timestamps must be increasing, non-null and unique')
        for k in ('Open','High','Low','Close'):
            raw[k] = pd.to_numeric(raw[k], errors='raise')
            if not np.isfinite(raw[k].to_numpy(dtype=float)).all():
                raise ValueError('Nonfinite OHLC candle')
        hor = XAUUSD5MSupplyDemandRejectionV35CandidateA(raw).generate()
        tr = V431_RESEARCH_ONLY(raw).generate()
        def align(f):
            k = f[['Date','Position','strategy_stop_loss','strategy_target','signal_reason']].copy()
            k['Date'] = pd.to_datetime(k.Date)
            if k.Date.duplicated().any():
                raise ValueError('Source engine produced duplicate candle timestamps')
            k = k.set_index('Date').reindex(pd.DatetimeIndex(raw.Date))
            if k.Position.isna().all():
                raise ValueError('Strategy output does not align with input dates')
            return k.reset_index(drop=True)
        h = align(hor)
        t = align(tr)
        out = raw.copy()
        out['Position'] = 0
        out['strategy_stop_loss'] = float('nan')
        out['strategy_target'] = float('nan')
        out['signal_reason'] = ''
        out['v432_source'] = ''
        out['v432_confluence'] = False
        N = len(raw)
        _o = raw['Open'].to_numpy(dtype=float)
        _h = raw['High'].to_numpy(dtype=float)
        _l = raw['Low'].to_numpy(dtype=float)
        _c = raw['Close'].to_numpy(dtype=float)
        _span = np.maximum(_h - _l, 1.e-9)
        _body_ratio = np.abs(_c - _o) / _span
        _prev = raw['Close'].shift(1)
        _tr = pd.concat([(raw.High-raw.Low), (raw.High-_prev).abs(),
                         (raw.Low-_prev).abs()],axis=1).max(axis=1)
        _atr14 = _tr.rolling(14,min_periods=14).mean().to_numpy(dtype=float)
        _ma20 = raw['Close'].rolling(20,min_periods=20).mean().to_numpy(dtype=float)
        _momentum20 = raw['Close'].shift(19).to_numpy(dtype=float)
        _momentum12 = raw['Close'].shift(12).to_numpy(dtype=float)
        _median_prior_atr = pd.Series(_atr14).shift(1).rolling(144,min_periods=72).median().to_numpy(dtype=float)
        _ist_entry_hour = (pd.DatetimeIndex(raw.Date) + pd.Timedelta(minutes=335)).hour.to_numpy()
        _utc_entry_hour = (pd.DatetimeIndex(raw.Date) + pd.Timedelta(minutes=5)).hour.to_numpy()
        _delta = raw.Close.diff().abs()
        _er48 = ((raw.Close-raw.Close.shift(48)).abs() /
                 (_delta.rolling(48,min_periods=48).sum()+1.e-7)).to_numpy()
        _er20 = ((raw.Close-raw.Close.shift(20)).abs() /
                 (_delta.rolling(20,min_periods=20).sum()+1.e-7)).to_numpy()
        _ma120 = raw.Close.rolling(120,min_periods=120).mean()
        _ma_slope = ((_ma120-_ma120.shift(24))/(_atr14+1.e-7)).to_numpy()
        _atr_acc = _atr14/(pd.Series(_atr14).shift(48).to_numpy()+1.e-7)
        _tr_expand = _tr.to_numpy() / (_tr.shift(1).rolling(48,min_periods=48).median().to_numpy()+1.e-7)
        _flip = (raw.Close.diff().apply(lambda v: 1 if v>0 else (-1 if v<0 else 0)).diff().ne(0).rolling(9).sum()/9).to_numpy()
        _lvl = raw.High.shift(1).rolling(24,min_periods=24).max().to_numpy(dtype=float)
        _median_atr = pd.Series(_atr14).shift(1).rolling(144,min_periods=60).median().to_numpy(dtype=float)
        _sw_ok = np.zeros(N,dtype=bool)
        _sw_stop = np.full(N,np.nan)
        if N>200:
            s=np.arange(N-1)
            i1=s+1
            span_s=np.maximum(_h[s]-_l[s],1e-9)
            wick_s=(_h[s]-np.maximum(_o[s],_c[s]))/span_s
            reg_s=_atr14[s]/np.maximum(_median_atr[s],1e-9)
            mom_s=(_c[s]-pd.Series(_c).shift(48).to_numpy(dtype=float)[s])/np.maximum(_atr14[s],1e-9)
            ok=(_h[s]>_lvl[s]+0.025*_atr14[s]) & (_c[s]<_lvl[s]) & (_c[s]<_o[s]) & (wick_s>0.15)
            ok &= (_c[i1]<_o[i1]) & (_c[i1]<_lvl[s]) & (_c[i1]<_l[s]+0.6*span_s)
            gap=(raw.Date.iloc[1:].to_numpy()-raw.Date.iloc[:-1].to_numpy())==np.timedelta64(5,'m')
            ok &= gap & np.isfinite(_lvl[s]) & np.isfinite(_atr14[s])
            if self.v58_rule=="ATR_MOM48": ok &= (reg_s>=1.05) & (mom_s<=0)
            else:
                hour=((pd.DatetimeIndex(raw.Date)+pd.Timedelta(hours=5,minutes=30)).hour.to_numpy())[i1]
                ok &= (hour<=8) & (reg_s>=1.05) & ((_c[s]-_ma20[s])/np.maximum(_atr14[s],1e-9)<=2.)
                if self.v58_rule=="STRICT_EARLY_ATR3": ok &= (_atr14[s]>=3.0)
            sl=_h[s]+0.10*_atr14[s]
            r=sl-_c[i1]
            ok &= (r>0.35*_atr14[s]) & (r<5.0*_atr14[s])
            _sw_ok[i1]=ok
            _sw_stop[i1]=sl
        # V5.9 bearish engulfing at resistance (bar-close causal, no future candles)
        _eng_ok = np.zeros(N, dtype=bool)
        _eng_stop = np.full(N, np.nan)
        if self.v59_new_entries_enabled and N>250:
            _res48 = raw.High.shift(2).rolling(48,min_periods=48).max().to_numpy(dtype=float)
            _ma240 = raw.Close.rolling(240,min_periods=240).mean().to_numpy(dtype=float)
            j = np.arange(240,N,dtype=int); prior=j-1
            prior_body = np.maximum(_c[prior]-_o[prior], 1.e-8)
            body = _o[j]-_c[j]
            contiguous = (raw.Date.iloc[1:].to_numpy()-raw.Date.iloc[:-1].to_numpy()) == np.timedelta64(5,'m')
            valid = (_c[prior]>_o[prior]) & (body>0) & (_o[j]>=_c[prior]-.35*_atr14[j])
            valid &= (_c[j]<=_o[prior]+.05*_atr14[j]) & (body/prior_body>=.6)
            valid &= (body/np.maximum(_atr14[j],1.e-8)>=.15)
            valid &= (np.maximum(_h[j],_h[prior])>=_res48[j]-.8*_atr14[j])
            valid &= ((_atr14[j]/np.maximum(_median_atr[j],1.e-8))>=1.25)
            valid &= ((-(_c[j]-_momentum12[j]))/np.maximum(_atr14[j],1.e-8)<=-2.)
            valid &= ((-(_c[j]-_ma240[j]))/np.maximum(_atr14[j],1.e-8)>=0.)
            valid &= contiguous[j-1] & np.isfinite(_res48[j]) & np.isfinite(_ma240[j])
            stopv = np.maximum(_h[j],_h[prior])+.1*_atr14[j]
            riskv = stopv-_c[j]
            valid &= (riskv>.3*_atr14[j]) & (riskv<5.*_atr14[j])
            _eng_ok[j]=valid
            _eng_stop[j]=stopv
        # V6.1 research-only LONG: counter-trend bullish fair-value-gap displacement.
        # Signal at completed candle i; no future bars are used for eligibility.
        # New entry only if existing V5.9 signal families have no valid intent.
        _fvg_ok = np.zeros(N, dtype=bool)
        _fvg_stop = np.full(N, np.nan, dtype=float)
        if self.v61_fvg_new_entries_enabled and N > 200:
            _fvg_reg = _atr14 / (_tr.shift(1).rolling(72, min_periods=72).median().to_numpy(dtype=float)+1.e-9)
            _fvg_mom48 = (raw.Close - raw.Close.shift(48)).to_numpy(dtype=float) / np.maximum(_atr14, 1.e-9)
            _fvg_hi24 = raw.High.shift(1).rolling(24, min_periods=24).max().to_numpy(dtype=float)
            _fvg_idx = np.arange(150, N-1, dtype=int)
            _fvg_gap_ok = ((raw.Date.iloc[1:].to_numpy()-raw.Date.iloc[:-1].to_numpy())==np.timedelta64(5,'m'))
            _fvg_body = _c[_fvg_idx]-_o[_fvg_idx]
            _fvg_cond = (_l[_fvg_idx]>_h[_fvg_idx-2]+.02*_atr14[_fvg_idx])
            _fvg_cond &= (_fvg_body > .6*_atr14[_fvg_idx])
            _fvg_cond &= (_c[_fvg_idx] > _fvg_hi24[_fvg_idx]) & (_c[_fvg_idx] > _ma20[_fvg_idx])
            _fvg_cond &= ((_c[_fvg_idx]-_momentum12[_fvg_idx]) > .5*_atr14[_fvg_idx])
            _fvg_cond &= (_fvg_mom48[_fvg_idx]<-1.0) & (_fvg_reg[_fvg_idx]>=1.1)
            _fvg_cond &= (_ist_entry_hour[_fvg_idx]<12)
            _fvg_cond &= _fvg_gap_ok[_fvg_idx-1]
            _fvg_cond &= np.isfinite(_atr14[_fvg_idx]) & np.isfinite(_fvg_reg[_fvg_idx])
            _fvg_sl = np.minimum(np.minimum(_l[_fvg_idx],_l[_fvg_idx-1]),_l[_fvg_idx-2])-.1*_atr14[_fvg_idx]
            _fvg_risk = _c[_fvg_idx]-_fvg_sl
            _fvg_cond &= (_fvg_risk>.25*_atr14[_fvg_idx]) & (_fvg_risk<5.*_atr14[_fvg_idx])
            _fvg_ok[_fvg_idx]=_fvg_cond
            _fvg_stop[_fvg_idx]=_fvg_sl
        # V6.2 research-only: bearish failed breakout above confirmed 48-bar resistance.
        # Sweep is completed bar i-1; decision is completed confirmation bar i.
        # All data is <=i; next open is consumed by original controller on bar i+1.
        _fb_ok = np.zeros(N, dtype=bool)
        _fb_stop = np.full(N, np.nan, dtype=float)
        if self.v62_failed_break_new_entries_enabled and N > 200:
            _fb_res48 = raw.High.shift(1).rolling(48, min_periods=48).max().to_numpy(dtype=float)
            _fb_med = _tr.shift(1).rolling(72, min_periods=72).median().to_numpy(dtype=float)
            _fb_idx = np.arange(200, N-1, dtype=int)
            _fb_prev = _fb_idx-1
            _fb_upwick = (_h[_fb_idx]-np.maximum(_o[_fb_idx],_c[_fb_idx])) / _span[_fb_idx]
            _fb_reg = _atr14[_fb_idx] / np.maximum(_fb_med[_fb_idx],1e-9)
            _fb_ma_dist = (_c[_fb_idx]-_ma20[_fb_idx]) / np.maximum(_atr14[_fb_idx],1e-9)
            _fb_contiguous = (raw.Date.iloc[1:].to_numpy()-raw.Date.iloc[:-1].to_numpy())==np.timedelta64(5,'m')
            _fb_cond = (_h[_fb_prev] > _fb_res48[_fb_prev] + .05*_atr14[_fb_prev])
            _fb_cond &= (_c[_fb_prev] < _fb_res48[_fb_prev])
            _fb_cond &= (_c[_fb_idx]-_o[_fb_idx] < -.35*_atr14[_fb_idx])
            _fb_cond &= (_c[_fb_idx] < _l[_fb_prev]) & (_fb_upwick > .08)
            _fb_cond &= (_fb_ma_dist >= 2.0) & (_fb_reg >= 1.4) & (_ist_entry_hour[_fb_idx] < 8)
            _fb_cond &= _fb_contiguous[_fb_idx-1] & _fb_contiguous[_fb_idx-2]
            _fb_cond &= np.isfinite(_fb_res48[_fb_prev]) & np.isfinite(_fb_reg)
            _fb_sl = np.maximum(np.maximum(_h[_fb_idx], _h[_fb_prev]),_h[_fb_idx-2]) + .1*_atr14[_fb_idx]
            _fb_risk = _fb_sl - _c[_fb_idx]
            _fb_cond &= (_fb_risk > .25*_atr14[_fb_idx]) & (_fb_risk < 5.*_atr14[_fb_idx])
            _fb_ok[_fb_idx] = _fb_cond
            _fb_stop[_fb_idx] = _fb_sl
        # Independent V6.2 candidate B: compressed five-bar range then strong LONG breakout.
        # Entry confirmation is complete at bar i; no future OHLC is referenced.
        _cb_ok = np.zeros(N,dtype=bool)
        _cb_stop = np.full(N,np.nan,dtype=float)
        if self.v62_compression_long_enabled and N > 200:
            _cb_idx = np.arange(200,N-1,dtype=int)
            _cb_prevhi48 = raw.High.shift(1).rolling(48,min_periods=48).max().to_numpy(dtype=float)
            _cb_comp = _tr.shift(1).rolling(5,min_periods=5).mean().to_numpy(dtype=float) / np.maximum(_atr14,1e-9)
            _cb_mom = (_c - raw.Close.shift(12).to_numpy(dtype=float)) / np.maximum(_atr14,1e-9)
            _cb_cond = (_cb_comp[_cb_idx] < .85) & (_c[_cb_idx]-_o[_cb_idx] > .55*_atr14[_cb_idx])
            _cb_cond &= (_c[_cb_idx] > _cb_prevhi48[_cb_idx]) & (_c[_cb_idx] > _ma20[_cb_idx])
            _cb_cond &= (_span[_cb_idx] / np.maximum(_atr14[_cb_idx],1e-9) < 1.0)
            _cb_cond &= (_cb_mom[_cb_idx] >= 2.0) & (_ist_entry_hour[_cb_idx] >= 20)
            _cb_cond &= np.isfinite(_cb_comp[_cb_idx]) & np.isfinite(_cb_prevhi48[_cb_idx])
            _cb_sl = np.minimum(np.minimum(_l[_cb_idx],_l[_cb_idx-1]),_l[_cb_idx-2]) - .1*_atr14[_cb_idx]
            _cb_risk = _c[_cb_idx]-_cb_sl
            _cb_cond &= (_cb_risk > .25*_atr14[_cb_idx]) & (_cb_risk < 5.*_atr14[_cb_idx])
            _cb_ok[_cb_idx]=_cb_cond
            _cb_stop[_cb_idx]=_cb_sl
        # V6.3: 2-bar confirmed resistance liquidity rejection (96 prior M5 candles).
        # Both bars are completed at the decision close; SL is known before next-open fill.
        # A strict quality regime rejects broad/impulsive continuation candles.
        _v63_ok = np.zeros(N,dtype=bool)
        _v63_stop = np.full(N,np.nan,dtype=float)
        if self.v63_resist96_enabled and N > 220:
            _v63_i=np.arange(200,N-1,dtype=int)
            _v63_p=_v63_i-1
            _v63_res=raw.High.shift(2).rolling(96,min_periods=96).max().to_numpy(dtype=float)
            _v63_upwick=(_h[_v63_i]-np.maximum(_o[_v63_i],_c[_v63_i]))/_span[_v63_i]
            _v63_range=_span[_v63_i]/np.maximum(_atr14[_v63_i],1.e-9)
            _v63_ok_i=(_h[_v63_p]>_v63_res[_v63_p]+.02*_atr14[_v63_i])
            _v63_ok_i &= (_c[_v63_p]<_v63_res[_v63_p]) & (_c[_v63_i]<_o[_v63_i])
            _v63_ok_i &= (_c[_v63_i]<_l[_v63_p]) & (_v63_upwick>=.50)
            _v63_ok_i &= (_body_ratio[_v63_i]<=.63) & (_v63_range<=1.00)
            _v63_contiguous=(raw.Date.iloc[1:].to_numpy()-raw.Date.iloc[:-1].to_numpy())==np.timedelta64(5,'m')
            _v63_ok_i &= _v63_contiguous[_v63_i-1] & _v63_contiguous[_v63_i-2]
            _v63_sl=np.maximum(_h[_v63_i],_h[_v63_p])+.12*_atr14[_v63_i]
            _v63_r=_v63_sl-_c[_v63_i]
            _v63_ok_i &= (_v63_r>.20*_atr14[_v63_i]) & (_v63_r<5*_atr14[_v63_i])
            _v63_ok_i &= np.isfinite(_v63_res[_v63_p]) & np.isfinite(_atr14[_v63_i])
            _v63_ok[_v63_i]=_v63_ok_i
            _v63_stop[_v63_i]=_v63_sl
        oh = raw[['Open','High','Low','Close']].to_numpy(dtype=float)
        hs = pd.to_numeric(h.Position,errors='coerce').fillna(0).to_numpy(dtype=int)
        ts = pd.to_numeric(t.Position,errors='coerce').fillna(0).to_numpy(dtype=int)
        hsl = pd.to_numeric(h.strategy_stop_loss,errors='coerce').to_numpy(dtype=float)
        htp = pd.to_numeric(h.strategy_target,errors='coerce').to_numpy(dtype=float)
        tsl = pd.to_numeric(t.strategy_stop_loss,errors='coerce').to_numpy(dtype=float)
        ttp = pd.to_numeric(t.strategy_target,errors='coerce').to_numpy(dtype=float)
        hwhy = h.signal_reason.fillna('').astype(str).tolist()
        twhy = t.signal_reason.fillna('').astype(str).tolist()
        # V6.4 research gate features — all indexed at the COMPLETED signal candle.
        # Prior 288 M5 highs/lows are shifted by one candle. This never uses the next open.
        _v64_tr_ewm14 = _tr.ewm(alpha=1.0/14.0, adjust=False, min_periods=14).mean().to_numpy(dtype=float)
        _v64_prior288hi = raw['High'].shift(1).rolling(288, min_periods=288).max().to_numpy(dtype=float)
        _v64_prior288lo = raw['Low'].shift(1).rolling(288, min_periods=288).min().to_numpy(dtype=float)
        _v64_prev48_medtr = _tr.shift(1).rolling(48, min_periods=48).median().to_numpy(dtype=float)
        filled_dir = 0
        stop = 0.0
        target = 0.0
        entered_bar = -1
        pending = None
        counts = dict(v35_signals=int((hs!=0).sum()),v431b_signals=int((ts!=0).sum()),
                      accepted=0,blocked_while_open=0,same_direction=0,opposite_conflicts=0,
                      bad_stop_target=0,invalid_next_open=0,simulated_stop_exits=0,simulated_target_exits=0,
                      v5_quality_vetoes=0,v52_quality_vetoes=0,v54_quality_vetoes=0,v55_quality_vetoes=0,v56_quality_vetoes=0,v57_quality_vetoes=0,v58_candidates=int(_sw_ok.sum()),v58_accepted=0,
                      v59_candidates=int(_eng_ok.sum()),v59_accepted=0,
                      v61_candidates=int(_fvg_ok.sum()),v61_accepted=0,
                      v62_candidates=int(_fb_ok.sum()),v62_accepted=0,
                      v62_compression_candidates=int(_cb_ok.sum()),v62_compression_accepted=0,
                      v63_resist96_candidates=int(_v63_ok.sum()),v63_resist96_accepted=0,
                      v64_weakgroup_vetoes=0)
        for i in range(N):
            open_i, high_i, low_i, close_i = oh[i]
            if pending is not None:
                sig, sl, tp = pending
                if sig * (open_i-sl) <= 0 or sig * (tp-open_i) <= 0:
                    counts['invalid_next_open'] += 1
                else:
                    filled_dir = sig
                    stop, target = sl, tp
                    entered_bar = i
                pending = None
            if filled_dir != 0 and i > entered_bar:
                stop_hit = low_i <= stop if filled_dir > 0 else high_i >= stop
                tp_hit = high_i >= target if filled_dir > 0 else low_i <= target
                if stop_hit:
                    filled_dir = 0
                    counts['simulated_stop_exits'] += 1
                elif tp_hit:
                    filled_dir = 0
                    counts['simulated_target_exits'] += 1
            a, b = int(hs[i]), int(ts[i])
            liq=bool(self.v58_new_entries_enabled and _sw_ok[i] and a==0 and b==0)
            engulf=bool(self.v59_new_entries_enabled and _eng_ok[i] and a==0 and b==0 and not liq)
            fvg=bool(self.v61_fvg_new_entries_enabled and _fvg_ok[i] and a==0 and b==0 and not liq and not engulf)
            fb=bool(self.v62_failed_break_new_entries_enabled and _fb_ok[i] and a==0 and b==0 and not liq and not engulf and not fvg)
            cb=bool(self.v62_compression_long_enabled and _cb_ok[i] and a==0 and b==0 and not liq and not engulf and not fvg and not fb)
            rs=bool(self.v63_resist96_enabled and _v63_ok[i] and a==0 and b==0 and not liq and not engulf and not fvg and not fb and not cb)
            if a == 0 and b == 0 and not liq and not engulf and not fvg and not fb and not cb and not rs:
                continue
            if filled_dir != 0:
                counts['blocked_while_open'] += 1
                continue
            if a and b and a != b:
                counts['opposite_conflicts'] += 1
                if self.conflict_policy == 'SKIP':
                    continue
            confluent = (a != 0 and a == b)
            if confluent:
                counts['same_direction'] += 1
            if rs:
                source='RESIST96'; sig=-1
                sl=float(_v63_stop[i]); tp=float(close_i-2.0*(sl-close_i))
            elif cb:
                source='COMPRESS_LONG'; sig=1
                sl=float(_cb_stop[i]); tp=float(close_i+2.0*(close_i-sl))
            elif fb:
                source='FAILED_BREAK48'; sig=-1
                sl=float(_fb_stop[i]); tp=float(close_i-2.0*(sl-close_i))
            elif fvg:
                source='BULL_FVG'; sig=1
                sl=float(_fvg_stop[i]); tp=float(close_i+2.0*(close_i-sl))
            elif liq:
                source='LIQ_SWEEP'
                sig=-1
                sl=float(_sw_stop[i])
                tp=float(close_i-2.0*(sl-close_i))
            elif engulf:
                source='ENGULF_RESIST'; sig=-1
                sl=float(_eng_stop[i]); tp=float(close_i-2.0*(sl-close_i))
            else:
                if a and b: source=self.same_bar_priority
                elif a: source='V35'
                else: source='V431B'
                sig=a if source=='V35' else b
                sl=float(hsl[i] if source=='V35' else tsl[i])
                tp=float(htp[i] if source=='V35' else ttp[i])
            if (not np.isfinite(sl) or not np.isfinite(tp) or
                    sig*(close_i-sl) <= 0 or sig*(tp-close_i) <= 0):
                counts['bad_stop_target'] += 1
                continue
            if self.v5_filter_enabled and not (liq or engulf or fvg or fb or cb) and i >= 20 and np.isfinite(_atr14[i]) and _atr14[i]>0:
                _quality = (close_i-low_i)/_span[i] if sig>0 else (high_i-close_i)/_span[i]
                _aligned_ma = sig*(close_i-_ma20[i])/_atr14[i]
                if self.v5_filter_rule == 'RECENT_EXTREME_CLOSE':
                    _veto = (_quality >= 0.9 and _aligned_ma >= 0.5 and
                             16 <= int(_ist_entry_hour[i]) < 20)
                else:
                    _flat20 = abs(close_i-_momentum20[i])/_atr14[i]
                    _veto = (_body_ratio[i] >= 0.4 and _aligned_ma < 0 and _flat20 < 1.0)
                if _veto:
                    counts['v5_quality_vetoes'] += 1
                    continue
            if self.v52_filter_enabled and not (liq or engulf or fvg or fb or cb) and self.v52_filter_rule != 'OFF' and i >= 160 and np.isfinite(_atr14[i]) and _atr14[i] > 0:
                _dir_wick = ((min(open_i, close_i)-low_i) if sig>0 else (high_i-max(open_i,close_i))) / _span[i]
                if self.v52_filter_rule == 'MOMENTUM_WICK_SESSION':
                    _mom12 = sig*(close_i-_momentum12[i])/_atr14[i]
                    _veto52 = (_dir_wick >= 0.10 and _mom12 < -1.0 and
                               8 <= int(_ist_entry_hour[i]) < 16)
                else:
                    _reg = _atr14[i]/max(_median_prior_atr[i],1.e-9)
                    _dir_close = (close_i-low_i)/_span[i] if sig>0 else (high_i-close_i)/_span[i]
                    _veto52 = (_reg < 0.65 and _body_ratio[i] < 0.8 and _dir_close >= 0.70)
                if _veto52:
                    counts['v52_quality_vetoes'] += 1
                    continue
            if (self.v54_filter_enabled and source == 'V431B' and i >= 160 and
                    np.isfinite(_atr14[i]) and _atr14[i] > 0):
                _m12_v54 = sig * (close_i - _momentum12[i]) / _atr14[i]
                if (8 <= int(_utc_entry_hour[i]) < 12 and _m12_v54 <= 0.60):
                    counts['v54_quality_vetoes'] += 1
                    continue
            if (self.v54_filter_enabled and source == 'V35' and i >= 160 and
                    np.isfinite(_atr14[i]) and _atr14[i] > 0):
                _wick54 = ((min(open_i,close_i)-low_i) if sig>0 else
                           (high_i-max(open_i,close_i))) / _span[i]
                _ma54 = sig*(close_i-_ma20[i])/_atr14[i]
                if _wick54 >= 0.33526 and _ma54 >= 0.39731:
                    counts['v54_quality_vetoes'] += 1
                    continue
            if self.v55_filter_enabled and source == 'V35':
                _details = str(hwhy[i])
                try:
                    _age = float(_details.split('zage=')[1].split(';')[0].strip())
                    _wick = float(_details.split('rwick=')[1].split(';')[0].strip())
                    _disp = float(_details.split('cdisp=')[1].split(';')[0].strip())
                    if _age <= 10.0 and _wick <= 0.15 and _disp <= 0.10:
                        counts['v55_quality_vetoes'] += 1
                        continue
                except (IndexError, ValueError):
                    pass
            if self.v56_filter_enabled and source == 'V35':
                try:
                    _disp56 = float(str(hwhy[i]).split('cdisp=')[1].split(';')[0])
                    _wick56 = ((min(open_i, close_i) - low_i) if sig > 0 else
                               (high_i - max(open_i, close_i))) / _span[i]
                    if 0.10 < _disp56 <= 0.20 and _wick56 > 0.20:
                        counts['v56_quality_vetoes'] += 1
                        continue
                except (ValueError, IndexError):
                    pass
            if self.v57_filter_enabled and not (liq or engulf or fvg or fb or cb) and i >= 170:
                if self.v57_filter_rule == 'FLAT_TREND':
                    _v57 = (_ma_slope[i] <= -1.0 and _atr_acc[i] > 0.90 and _er48[i] <= 0.10)
                else:
                    _v57 = (_flip[i] > 0.67 and _er20[i] > 0.10 and _tr_expand[i] > 1.50)
                if _v57:
                    counts['v57_quality_vetoes'] += 1
                    continue
            # V6.4 research veto: pre-entry, chronological and independent of future outcome.
            # Trial thresholds came from earlier historical trades and are not forward-validated.
            if (self.v64_gate_enabled and source == 'V431B' and i >= 301 and
                np.isfinite(_v64_tr_ewm14[i]) and _v64_tr_ewm14[i] > 0 and
                np.isfinite(_v64_prev48_medtr[i]) and _v64_prev48_medtr[i] > 0):
                _v64_signed36 = sig * (close_i - _c[i-36]) / _v64_tr_ewm14[i]
                _v64_edge = ((close_i - _v64_prior288lo[i]) if sig > 0 else
                             (_v64_prior288hi[i] - close_i)) / _v64_tr_ewm14[i]
                _v64_range = float(_tr.iat[i]) / _v64_prev48_medtr[i]
                if (_v64_signed36 < 3.7492 and _v64_edge >= 11.7751 and
                    _v64_range < 1.2224):
                    counts['v64_weakgroup_vetoes'] += 1
                    continue
            out.at[i, 'Position'] = sig
            out.at[i, 'strategy_stop_loss'] = sl
            out.at[i, 'strategy_target'] = tp
            out.at[i, 'v432_source'] = source
            out.at[i, 'v432_confluence'] = bool(confluent)
            reason = ('V63_RESIST96_REJECT_CONFIRM' if rs else ('V62_COMPRESSION_BREAK_LONG' if cb else ('V62_FAILED_BREAK48_BEAR_CONFIRM' if fb else ('V61_BULL_FVG_DISPLACEMENT_PULLBACK' if fvg else ('BEARISH_ENGULFING_RESIST48_PULLBACK' if engulf else ('RESISTANCE_LIQUIDITY_SWEEP_24_CONFIRM' if liq else (hwhy[i] if source == 'V35' else twhy[i])))))))
            if rs: counts['v63_resist96_accepted'] += 1
            if cb: counts['v62_compression_accepted'] += 1
            if fb: counts['v62_accepted'] += 1
            if fvg: counts['v61_accepted'] += 1
            if engulf: counts['v59_accepted'] += 1
            if liq: counts['v58_accepted'] += 1
            out.at[i, 'signal_reason'] = 'V432A_'+source+('_CONFLUENCE' if confluent else '')+'|'+reason
            counts['accepted'] += 1
            pending = (sig,sl,tp)
        self._stats = counts
        out.attrs['strategy_diagnostics'] = dict(
            version='V6.4_V431B_24H_EXTREME_GATE_RESEARCH_ONLY',frozen_sources=['V3.5','V4.31B'],
            one_position=True,live_approved=False,arbitration=counts,
            v5_filter_rule=self.v5_filter_rule,v5_filter_enabled=self.v5_filter_enabled,
            v52_filter_rule=self.v52_filter_rule,v52_filter_enabled=self.v52_filter_enabled,
            v54_filter_enabled=self.v54_filter_enabled,
            v55_filter_enabled=self.v55_filter_enabled,
            v56_filter_enabled=self.v56_filter_enabled,
            v57_filter_enabled=self.v57_filter_enabled,v57_filter_rule=self.v57_filter_rule,
            v58_new_entries_enabled=self.v58_new_entries_enabled,v58_rule=self.v58_rule,
            v59_new_entries_enabled=self.v59_new_entries_enabled,
            v61_fvg_new_entries_enabled=self.v61_fvg_new_entries_enabled,
            v62_failed_break_new_entries_enabled=self.v62_failed_break_new_entries_enabled,
            v62_compression_long_enabled=self.v62_compression_long_enabled,
            v63_resist96_enabled=self.v63_resist96_enabled,
            v64_gate_enabled=self.v64_gate_enabled,
            caution='Both source engines run standalone; source self-suppression and execution differences need full replay parity')
        return out

Strategy = AlgoAgentX_V62_NewEntries_RESEARCH_ONLY
