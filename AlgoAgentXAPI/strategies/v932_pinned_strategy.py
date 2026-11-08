# AUTOMATICALLY DERIVED from the EXACT source attached by the user.
# Only live change: accept a checked, precomputed V3.5 history in V62.generate().
# Standalone generate() semantics remain the frozen source's semantics.
import pandas as pd

class SRZone:

  def __init__(self, zone_id, side, pivot_index, available_index, zone_low, zone_high, strength, reactions=1, lifecycle='FRESH', broken=False, consumed=False, last_interaction_index=None):
    self.zone_id = zone_id
    self.side = side
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

  def __init__(self, setup_id, zone, direction, state='ZONE_REACHED', interaction_type=None, rejection_index=None, rejection_high=None, rejection_low=None, sweep_extreme=None, expires_at=None):
    self.setup_id = setup_id
    self.zone = zone
    self.direction = direction
    self.state = state
    self.interaction_type = interaction_type
    self.rejection_index = rejection_index
    self.rejection_high = rejection_high
    self.rejection_low = rejection_low
    self.sweep_extreme = sweep_extreme
    self.expires_at = expires_at

class XAUUSD5MSupplyDemandRejectionV35CandidateA:
  pass

  @staticmethod
  def _day_key_from_timestamp(ts):
    return '%04d-%02d-%02d' % (int(ts.year), int(ts.month), int(ts.day))

  @staticmethod
  def _month_key_from_timestamp(ts):
    return '%04d-%02d' % (int(ts.year), int(ts.month))

  @staticmethod
  def _timestamp_text(ts):
    return '%04d-%02d-%02dT%02d:%02d:%02d' % (int(ts.year), int(ts.month), int(ts.day), int(ts.hour), int(ts.minute), int(ts.second))

  def __init__(self, df, swing_left=3, swing_right=3, zone_width=2.5, minimum_reaction=2.0, minimum_strength=1.0, max_zone_age=180, minimum_distance=4.0, merge_distance=1.5, approach_distance=5.0, minimum_body_ratio=0.2, minimum_upper_wick_ratio=0.25, minimum_lower_wick_ratio=0.25, minimum_zone_penetration=0.05, maximum_close_position=0.55, entry_confirmation='CLOSE_BELOW_REJECTION_LOW', long_entry_confirmation='CLOSE_ABOVE_REJECTION_HIGH', confirmation_bars=4, sl_mode='REJECTION_HIGH', sl_buffer=0.5, fixed_sl_distance=4.0, atr_period=14, atr_buffer_multiplier=0.25, tp_mode='FIXED_RR', minimum_rr=1.5, target_rr=2.0, breakout_rule='CLOSE_ABOVE_ZONE_BY_BUFFER', breakout_buffer=0.5, breakout_consecutive_closes=2, setup_expiry_bars=12, htf_context_enabled=True, htf_swing_left=2, htf_swing_right=2, source_timeframe_minutes=0, enable_short=True, enable_long=True, max_entries_per_month=0, max_entries_per_day=0, min_bars_between_entries=0, regime_interaction_filter=True, neutral_short_penetration_filter=True, neutral_short_min_penetration=0.35, neutral_long_body_filter=True, neutral_long_weak_body_min=0.2, neutral_long_weak_body_max=0.3, neutral_long_overextended_filter=True, neutral_long_min_overextended_wick=0.6, neutral_long_min_overextended_confirmation=0.4, neutral_short_weak_confirmation_filter=True, neutral_short_max_weak_zone_strength=2.0, neutral_short_max_weak_confirmation_displacement=0.2, neutral_short_ambiguous_wick_filter=True, neutral_short_ambiguous_wick_min=0.2, neutral_short_ambiguous_wick_max=0.4, neutral_long_moderate_strength_close_filter=True, neutral_long_moderate_strength_min=2.0, neutral_long_moderate_strength_max=2.5, neutral_long_max_close_position=0.2, neutral_long_age_confirmation_filter=True, neutral_long_age_confirmation_min_age=5, neutral_long_age_confirmation_max_age=10, neutral_long_age_confirmation_min_displacement=0.2, neutral_long_age_confirmation_max_displacement=0.3, neutral_long_ambiguous_moderate_filter=True, neutral_long_ambiguous_moderate_min_zone_strength=1.5, neutral_long_ambiguous_moderate_max_zone_strength=2.0, neutral_long_ambiguous_moderate_min_wick=0.3, neutral_long_ambiguous_moderate_max_wick=0.4, neutral_long_low_strength_wick_filter=True, neutral_long_low_strength_min_zone_strength=1.0, neutral_long_low_strength_max_zone_strength=1.5, neutral_long_low_strength_min_wick=0.2, neutral_long_low_strength_max_wick=0.3, neutral_long_shallow_wick_penetration_filter=True, neutral_long_shallow_wick_min=0.5, neutral_long_shallow_wick_max=0.6, neutral_long_shallow_max_penetration=0.2, neutral_short_high_body_filter=True, neutral_short_high_body_min=0.75, neutral_short_high_body_max=0.9, neutral_long_midclose_penetration_filter=True, neutral_long_midclose_min_close=0.4, neutral_long_midclose_max_close=0.5, neutral_long_midclose_min_penetration=0.2, neutral_long_midclose_max_penetration=0.5, neutral_long_stale_weak_confirmation_filter=True, neutral_long_stale_min_zone_age=40, neutral_long_stale_min_confirmation_displacement=0.1, neutral_long_stale_max_confirmation_displacement=0.3, neutral_long_medium_pen_weak_confirmation_filter=True, neutral_long_medium_pen_min_penetration=0.2, neutral_long_medium_pen_max_penetration=0.3, neutral_long_medium_pen_min_confirmation_displacement=0.05, neutral_long_medium_pen_max_confirmation_displacement=0.2, neutral_short_weak_body_midclose_filter=True, neutral_short_weak_body_midclose_min_body=0.2, neutral_short_weak_body_midclose_max_body=0.4, neutral_short_weak_body_midclose_min_close=0.3, neutral_short_weak_body_midclose_max_close=0.5, neutral_long_high_body_shallow_pen_filter=True, neutral_long_high_body_shallow_pen_min_body=0.7, neutral_long_high_body_shallow_pen_max_body=0.9, neutral_long_high_body_shallow_pen_min_penetration=0.1, neutral_long_high_body_shallow_pen_max_penetration=0.2, neutral_long_medium_pen_midhigh_confirmation_filter=True, neutral_long_medium_pen_midhigh_min_penetration=0.2, neutral_long_medium_pen_midhigh_max_penetration=0.3, neutral_long_medium_pen_midhigh_min_confirmation_displacement=0.4, neutral_long_medium_pen_midhigh_max_confirmation_displacement=0.8, bearish_short_sweep_weak_confirmation_filter=True, bearish_short_sweep_min_close=0.1, bearish_short_sweep_max_close=0.5, bearish_short_sweep_min_confirmation_displacement=0.0, bearish_short_sweep_max_confirmation_displacement=0.3, bullish_long_sweep_mid_confirmation_filter=True, bullish_long_sweep_min_close=0.0, bullish_long_sweep_max_close=0.4, bullish_long_sweep_min_confirmation_displacement=0.4, bullish_long_sweep_max_confirmation_displacement=0.6, neutral_long_deep_pen_mid_confirmation_filter=True, neutral_long_deep_pen_mid_confirmation_min_penetration=0.4, neutral_long_deep_pen_mid_confirmation_max_penetration=0.5, neutral_long_deep_pen_mid_confirmation_min_displacement=0.2, neutral_long_deep_pen_mid_confirmation_max_displacement=0.4, neutral_long_weak_body_mid_strength_filter=True, neutral_long_weak_body_mid_strength_min_body=0.1, neutral_long_weak_body_mid_strength_max_body=0.4, neutral_long_weak_body_mid_strength_min_zone_strength=2.5, neutral_long_weak_body_mid_strength_max_zone_strength=4.0, neutral_long_mid_age_mid_strength_filter=True, neutral_long_mid_age_mid_strength_min_age=15, neutral_long_mid_age_mid_strength_max_age=30, neutral_long_mid_age_mid_strength_min_zone_strength=2.5, neutral_long_mid_age_mid_strength_max_zone_strength=4.0, proposal_a_expansion_enabled=True, proposal_a_min_body_ratio=0.5, proposal_a_max_body_ratio=0.7, proposal_b_expansion_enabled=True, proposal_b_min_zone_age=40, proposal_b_max_zone_age=60, proposal_c_expansion_enabled=True, proposal_c_min_zone_age=15, proposal_c_max_zone_age=30, proposal_d_expansion_enabled=True, proposal_d_min_confirmation_displacement=0.6, proposal_d_max_confirmation_displacement=0.8, v3_1_candidate_a_filter=True, v3_1_candidate_a_min_rejection_wick=0.1, v3_1_candidate_a_max_rejection_wick=0.4, v3_1_candidate_a_min_confirmation_displacement=0.6, v3_1_candidate_a_max_confirmation_displacement=0.8, v3_2_candidate_a_filter=True, v3_2_candidate_a_min_zone_age=10, v3_2_candidate_a_max_zone_age=30, v3_2_candidate_a_min_confirmation_displacement=0.3, v3_2_candidate_a_max_confirmation_displacement=0.5, v3_3_candidate_a_filter=True, v3_3_candidate_a_min_zone_strength=1.5, v3_3_candidate_a_max_zone_strength=3.0, v3_3_candidate_a_min_rejection_close=0.4, v3_3_candidate_a_max_rejection_close=0.6, v3_4_candidate_a_filter=True, v3_4_candidate_a_start_year=0, v3_4_candidate_a_min_rejection_body=0.5, v3_4_candidate_a_max_rejection_body=0.8, v3_4_candidate_a_min_rejection_close=0.3, v3_4_candidate_a_max_rejection_close=0.5, v3_5_candidate_a_filter=True, v3_5_candidate_a_min_zone_age=3, v3_5_candidate_a_max_zone_age=5, cooldown_enabled=False, cooldown_after_losses=2, cooldown_skip_setups=1, intrabar_collision_policy='STOP_FIRST', debug_mode=False, **kwargs):
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
    self.entry_confirmation = str(entry_confirmation or 'CLOSE_BELOW_REJECTION_LOW').upper()
    self.long_entry_confirmation = str(long_entry_confirmation or 'CLOSE_ABOVE_REJECTION_HIGH').upper()
    self.confirmation_bars = max(1, int(confirmation_bars))
    self.sl_mode = str(sl_mode or 'REJECTION_HIGH').upper()
    self.sl_buffer = max(0.0, float(sl_buffer))
    self.fixed_sl_distance = max(0.01, float(fixed_sl_distance))
    self.atr_period = max(2, int(atr_period))
    self.atr_buffer_multiplier = max(0.0, float(atr_buffer_multiplier))
    self.tp_mode = str(tp_mode or 'FIXED_RR').upper()
    self.minimum_rr = max(0.01, float(minimum_rr))
    self.target_rr = max(0.01, float(target_rr))
    self.breakout_rule = str(breakout_rule or 'CLOSE_ABOVE_ZONE_BY_BUFFER').upper()
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
    self.neutral_short_min_penetration = max(0.0, min(1.0, float(neutral_short_min_penetration)))
    self.neutral_long_body_filter = bool(neutral_long_body_filter)
    self.neutral_long_weak_body_min = max(0.0, min(1.0, float(neutral_long_weak_body_min)))
    self.neutral_long_weak_body_max = max(self.neutral_long_weak_body_min, min(1.0, float(neutral_long_weak_body_max)))
    self.neutral_long_overextended_filter = bool(neutral_long_overextended_filter)
    self.neutral_long_min_overextended_wick = max(0.0, min(1.0, float(neutral_long_min_overextended_wick)))
    self.neutral_long_min_overextended_confirmation = max(0.0, float(neutral_long_min_overextended_confirmation))
    self.neutral_short_weak_confirmation_filter = bool(neutral_short_weak_confirmation_filter)
    self.neutral_short_max_weak_zone_strength = max(0.0, float(neutral_short_max_weak_zone_strength))
    self.neutral_short_max_weak_confirmation_displacement = max(0.0, float(neutral_short_max_weak_confirmation_displacement))
    self.neutral_short_ambiguous_wick_filter = bool(neutral_short_ambiguous_wick_filter)
    self.neutral_short_ambiguous_wick_min = max(0.0, min(1.0, float(neutral_short_ambiguous_wick_min)))
    self.neutral_short_ambiguous_wick_max = max(self.neutral_short_ambiguous_wick_min, min(1.0, float(neutral_short_ambiguous_wick_max)))
    self.neutral_long_moderate_strength_close_filter = bool(neutral_long_moderate_strength_close_filter)
    self.neutral_long_moderate_strength_min = max(0.0, float(neutral_long_moderate_strength_min))
    self.neutral_long_moderate_strength_max = max(self.neutral_long_moderate_strength_min, float(neutral_long_moderate_strength_max))
    self.neutral_long_max_close_position = max(0.0, min(1.0, float(neutral_long_max_close_position)))
    self.neutral_long_age_confirmation_filter = bool(neutral_long_age_confirmation_filter)
    self.neutral_long_age_confirmation_min_age = max(0, int(neutral_long_age_confirmation_min_age))
    self.neutral_long_age_confirmation_max_age = max(self.neutral_long_age_confirmation_min_age, int(neutral_long_age_confirmation_max_age))
    self.neutral_long_age_confirmation_min_displacement = max(0.0, float(neutral_long_age_confirmation_min_displacement))
    self.neutral_long_age_confirmation_max_displacement = max(self.neutral_long_age_confirmation_min_displacement, float(neutral_long_age_confirmation_max_displacement))
    self.neutral_long_ambiguous_moderate_filter = bool(neutral_long_ambiguous_moderate_filter)
    self.neutral_long_ambiguous_moderate_min_zone_strength = max(0.0, float(neutral_long_ambiguous_moderate_min_zone_strength))
    self.neutral_long_ambiguous_moderate_max_zone_strength = max(self.neutral_long_ambiguous_moderate_min_zone_strength, float(neutral_long_ambiguous_moderate_max_zone_strength))
    self.neutral_long_ambiguous_moderate_min_wick = max(0.0, min(1.0, float(neutral_long_ambiguous_moderate_min_wick)))
    self.neutral_long_ambiguous_moderate_max_wick = max(self.neutral_long_ambiguous_moderate_min_wick, min(1.0, float(neutral_long_ambiguous_moderate_max_wick)))
    self.neutral_long_low_strength_wick_filter = bool(neutral_long_low_strength_wick_filter)
    self.neutral_long_low_strength_min_zone_strength = max(0.0, float(neutral_long_low_strength_min_zone_strength))
    self.neutral_long_low_strength_max_zone_strength = max(self.neutral_long_low_strength_min_zone_strength, float(neutral_long_low_strength_max_zone_strength))
    self.neutral_long_low_strength_min_wick = max(0.0, min(1.0, float(neutral_long_low_strength_min_wick)))
    self.neutral_long_low_strength_max_wick = max(self.neutral_long_low_strength_min_wick, min(1.0, float(neutral_long_low_strength_max_wick)))
    self.neutral_long_shallow_wick_penetration_filter = bool(neutral_long_shallow_wick_penetration_filter)
    self.neutral_long_shallow_wick_min = max(0.0, min(1.0, float(neutral_long_shallow_wick_min)))
    self.neutral_long_shallow_wick_max = max(self.neutral_long_shallow_wick_min, min(1.0, float(neutral_long_shallow_wick_max)))
    self.neutral_long_shallow_max_penetration = max(0.0, min(1.0, float(neutral_long_shallow_max_penetration)))
    self.neutral_short_high_body_filter = bool(neutral_short_high_body_filter)
    self.neutral_short_high_body_min = max(0.0, min(1.0, float(neutral_short_high_body_min)))
    self.neutral_short_high_body_max = max(self.neutral_short_high_body_min, min(1.0, float(neutral_short_high_body_max)))
    self.neutral_long_midclose_penetration_filter = bool(neutral_long_midclose_penetration_filter)
    self.neutral_long_midclose_min_close = max(0.0, min(1.0, float(neutral_long_midclose_min_close)))
    self.neutral_long_midclose_max_close = max(self.neutral_long_midclose_min_close, min(1.0, float(neutral_long_midclose_max_close)))
    self.neutral_long_midclose_min_penetration = max(0.0, min(1.0, float(neutral_long_midclose_min_penetration)))
    self.neutral_long_midclose_max_penetration = max(self.neutral_long_midclose_min_penetration, min(1.0, float(neutral_long_midclose_max_penetration)))
    self.neutral_long_stale_weak_confirmation_filter = bool(neutral_long_stale_weak_confirmation_filter)
    self.neutral_long_stale_min_zone_age = max(0, int(neutral_long_stale_min_zone_age))
    self.neutral_long_stale_min_confirmation_displacement = max(0.0, float(neutral_long_stale_min_confirmation_displacement))
    self.neutral_long_stale_max_confirmation_displacement = max(self.neutral_long_stale_min_confirmation_displacement, float(neutral_long_stale_max_confirmation_displacement))
    self.neutral_long_medium_pen_weak_confirmation_filter = bool(neutral_long_medium_pen_weak_confirmation_filter)
    self.neutral_long_medium_pen_min_penetration = max(0.0, min(1.0, float(neutral_long_medium_pen_min_penetration)))
    self.neutral_long_medium_pen_max_penetration = max(self.neutral_long_medium_pen_min_penetration, min(1.0, float(neutral_long_medium_pen_max_penetration)))
    self.neutral_long_medium_pen_min_confirmation_displacement = max(0.0, float(neutral_long_medium_pen_min_confirmation_displacement))
    self.neutral_long_medium_pen_max_confirmation_displacement = max(self.neutral_long_medium_pen_min_confirmation_displacement, float(neutral_long_medium_pen_max_confirmation_displacement))
    self.neutral_short_weak_body_midclose_filter = bool(neutral_short_weak_body_midclose_filter)
    self.neutral_short_weak_body_midclose_min_body = max(0.0, min(1.0, float(neutral_short_weak_body_midclose_min_body)))
    self.neutral_short_weak_body_midclose_max_body = max(self.neutral_short_weak_body_midclose_min_body, min(1.0, float(neutral_short_weak_body_midclose_max_body)))
    self.neutral_short_weak_body_midclose_min_close = max(0.0, min(1.0, float(neutral_short_weak_body_midclose_min_close)))
    self.neutral_short_weak_body_midclose_max_close = max(self.neutral_short_weak_body_midclose_min_close, min(1.0, float(neutral_short_weak_body_midclose_max_close)))
    self.neutral_long_high_body_shallow_pen_filter = bool(neutral_long_high_body_shallow_pen_filter)
    self.neutral_long_high_body_shallow_pen_min_body = max(0.0, min(1.0, float(neutral_long_high_body_shallow_pen_min_body)))
    self.neutral_long_high_body_shallow_pen_max_body = max(self.neutral_long_high_body_shallow_pen_min_body, min(1.0, float(neutral_long_high_body_shallow_pen_max_body)))
    self.neutral_long_high_body_shallow_pen_min_penetration = max(0.0, min(1.0, float(neutral_long_high_body_shallow_pen_min_penetration)))
    self.neutral_long_high_body_shallow_pen_max_penetration = max(self.neutral_long_high_body_shallow_pen_min_penetration, min(1.0, float(neutral_long_high_body_shallow_pen_max_penetration)))
    self.neutral_long_medium_pen_midhigh_confirmation_filter = bool(neutral_long_medium_pen_midhigh_confirmation_filter)
    self.neutral_long_medium_pen_midhigh_min_penetration = max(0.0, min(1.0, float(neutral_long_medium_pen_midhigh_min_penetration)))
    self.neutral_long_medium_pen_midhigh_max_penetration = max(self.neutral_long_medium_pen_midhigh_min_penetration, min(1.0, float(neutral_long_medium_pen_midhigh_max_penetration)))
    self.neutral_long_medium_pen_midhigh_min_confirmation_displacement = max(0.0, float(neutral_long_medium_pen_midhigh_min_confirmation_displacement))
    self.neutral_long_medium_pen_midhigh_max_confirmation_displacement = max(self.neutral_long_medium_pen_midhigh_min_confirmation_displacement, float(neutral_long_medium_pen_midhigh_max_confirmation_displacement))
    self.bearish_short_sweep_weak_confirmation_filter = bool(bearish_short_sweep_weak_confirmation_filter)
    self.bearish_short_sweep_min_close = max(0.0, min(1.0, float(bearish_short_sweep_min_close)))
    self.bearish_short_sweep_max_close = max(self.bearish_short_sweep_min_close, min(1.0, float(bearish_short_sweep_max_close)))
    self.bearish_short_sweep_min_confirmation_displacement = max(0.0, float(bearish_short_sweep_min_confirmation_displacement))
    self.bearish_short_sweep_max_confirmation_displacement = max(self.bearish_short_sweep_min_confirmation_displacement, float(bearish_short_sweep_max_confirmation_displacement))
    self.bullish_long_sweep_mid_confirmation_filter = bool(bullish_long_sweep_mid_confirmation_filter)
    self.bullish_long_sweep_min_close = max(0.0, min(1.0, float(bullish_long_sweep_min_close)))
    self.bullish_long_sweep_max_close = max(self.bullish_long_sweep_min_close, min(1.0, float(bullish_long_sweep_max_close)))
    self.bullish_long_sweep_min_confirmation_displacement = max(0.0, float(bullish_long_sweep_min_confirmation_displacement))
    self.bullish_long_sweep_max_confirmation_displacement = max(self.bullish_long_sweep_min_confirmation_displacement, float(bullish_long_sweep_max_confirmation_displacement))
    self.neutral_long_deep_pen_mid_confirmation_filter = bool(neutral_long_deep_pen_mid_confirmation_filter)
    self.neutral_long_deep_pen_mid_confirmation_min_penetration = max(0.0, min(1.0, float(neutral_long_deep_pen_mid_confirmation_min_penetration)))
    self.neutral_long_deep_pen_mid_confirmation_max_penetration = max(self.neutral_long_deep_pen_mid_confirmation_min_penetration, min(1.0, float(neutral_long_deep_pen_mid_confirmation_max_penetration)))
    self.neutral_long_deep_pen_mid_confirmation_min_displacement = max(0.0, float(neutral_long_deep_pen_mid_confirmation_min_displacement))
    self.neutral_long_deep_pen_mid_confirmation_max_displacement = max(self.neutral_long_deep_pen_mid_confirmation_min_displacement, float(neutral_long_deep_pen_mid_confirmation_max_displacement))
    self.neutral_long_weak_body_mid_strength_filter = bool(neutral_long_weak_body_mid_strength_filter)
    self.neutral_long_weak_body_mid_strength_min_body = max(0.0, min(1.0, float(neutral_long_weak_body_mid_strength_min_body)))
    self.neutral_long_weak_body_mid_strength_max_body = max(self.neutral_long_weak_body_mid_strength_min_body, min(1.0, float(neutral_long_weak_body_mid_strength_max_body)))
    self.neutral_long_weak_body_mid_strength_min_zone_strength = max(0.0, float(neutral_long_weak_body_mid_strength_min_zone_strength))
    self.neutral_long_weak_body_mid_strength_max_zone_strength = max(self.neutral_long_weak_body_mid_strength_min_zone_strength, float(neutral_long_weak_body_mid_strength_max_zone_strength))
    self.neutral_long_mid_age_mid_strength_filter = bool(neutral_long_mid_age_mid_strength_filter)
    self.neutral_long_mid_age_mid_strength_min_age = max(0, int(neutral_long_mid_age_mid_strength_min_age))
    self.neutral_long_mid_age_mid_strength_max_age = max(self.neutral_long_mid_age_mid_strength_min_age, int(neutral_long_mid_age_mid_strength_max_age))
    self.neutral_long_mid_age_mid_strength_min_zone_strength = max(0.0, float(neutral_long_mid_age_mid_strength_min_zone_strength))
    self.neutral_long_mid_age_mid_strength_max_zone_strength = max(self.neutral_long_mid_age_mid_strength_min_zone_strength, float(neutral_long_mid_age_mid_strength_max_zone_strength))
    self.proposal_a_expansion_enabled = bool(proposal_a_expansion_enabled)
    self.proposal_a_min_body_ratio = max(0.0, min(1.0, float(proposal_a_min_body_ratio)))
    self.proposal_a_max_body_ratio = max(self.proposal_a_min_body_ratio, min(1.0, float(proposal_a_max_body_ratio)))
    self.proposal_b_expansion_enabled = bool(proposal_b_expansion_enabled)
    self.proposal_b_min_zone_age = max(0, int(proposal_b_min_zone_age))
    self.proposal_b_max_zone_age = max(self.proposal_b_min_zone_age, int(proposal_b_max_zone_age))
    self.proposal_c_expansion_enabled = bool(proposal_c_expansion_enabled)
    self.proposal_c_min_zone_age = max(0, int(proposal_c_min_zone_age))
    self.proposal_c_max_zone_age = max(self.proposal_c_min_zone_age, int(proposal_c_max_zone_age))
    self.proposal_d_expansion_enabled = bool(proposal_d_expansion_enabled)
    self.proposal_d_min_confirmation_displacement = max(0.0, float(proposal_d_min_confirmation_displacement))
    self.proposal_d_max_confirmation_displacement = max(self.proposal_d_min_confirmation_displacement, float(proposal_d_max_confirmation_displacement))
    self.v3_1_candidate_a_filter = bool(v3_1_candidate_a_filter)
    self.v3_1_candidate_a_min_rejection_wick = max(0.0, min(1.0, float(v3_1_candidate_a_min_rejection_wick)))
    self.v3_1_candidate_a_max_rejection_wick = max(self.v3_1_candidate_a_min_rejection_wick, min(1.0, float(v3_1_candidate_a_max_rejection_wick)))
    self.v3_1_candidate_a_min_confirmation_displacement = max(0.0, float(v3_1_candidate_a_min_confirmation_displacement))
    self.v3_1_candidate_a_max_confirmation_displacement = max(self.v3_1_candidate_a_min_confirmation_displacement, float(v3_1_candidate_a_max_confirmation_displacement))
    self.v3_2_candidate_a_filter = bool(v3_2_candidate_a_filter)
    self.v3_2_candidate_a_min_zone_age = max(0, int(v3_2_candidate_a_min_zone_age))
    self.v3_2_candidate_a_max_zone_age = max(self.v3_2_candidate_a_min_zone_age, int(v3_2_candidate_a_max_zone_age))
    self.v3_2_candidate_a_min_confirmation_displacement = max(0.0, float(v3_2_candidate_a_min_confirmation_displacement))
    self.v3_2_candidate_a_max_confirmation_displacement = max(self.v3_2_candidate_a_min_confirmation_displacement, float(v3_2_candidate_a_max_confirmation_displacement))
    self.v3_3_candidate_a_filter = bool(v3_3_candidate_a_filter)
    self.v3_3_candidate_a_min_zone_strength = max(0.0, float(v3_3_candidate_a_min_zone_strength))
    self.v3_3_candidate_a_max_zone_strength = max(self.v3_3_candidate_a_min_zone_strength, float(v3_3_candidate_a_max_zone_strength))
    self.v3_3_candidate_a_min_rejection_close = max(0.0, min(1.0, float(v3_3_candidate_a_min_rejection_close)))
    self.v3_3_candidate_a_max_rejection_close = max(self.v3_3_candidate_a_min_rejection_close, min(1.0, float(v3_3_candidate_a_max_rejection_close)))
    self.v3_4_candidate_a_filter = bool(v3_4_candidate_a_filter)
    self.v3_4_candidate_a_start_year = max(0, int(v3_4_candidate_a_start_year))
    self.v3_4_candidate_a_min_rejection_body = max(0.0, min(1.0, float(v3_4_candidate_a_min_rejection_body)))
    self.v3_4_candidate_a_max_rejection_body = max(self.v3_4_candidate_a_min_rejection_body, min(1.0, float(v3_4_candidate_a_max_rejection_body)))
    self.v3_4_candidate_a_min_rejection_close = max(0.0, min(1.0, float(v3_4_candidate_a_min_rejection_close)))
    self.v3_4_candidate_a_max_rejection_close = max(self.v3_4_candidate_a_min_rejection_close, min(1.0, float(v3_4_candidate_a_max_rejection_close)))
    self.v3_5_candidate_a_filter = bool(v3_5_candidate_a_filter)
    self.v3_5_candidate_a_min_zone_age = max(0, int(v3_5_candidate_a_min_zone_age))
    self.v3_5_candidate_a_max_zone_age = max(self.v3_5_candidate_a_min_zone_age, int(v3_5_candidate_a_max_zone_age))
    self.cooldown_enabled = bool(cooldown_enabled)
    self.cooldown_after_losses = max(1, int(cooldown_after_losses))
    self.cooldown_skip_setups = max(1, int(cooldown_skip_setups))
    self.intrabar_collision_policy = str(intrabar_collision_policy or 'STOP_FIRST').upper()
    if self.intrabar_collision_policy not in ('STOP_FIRST', 'TARGET_FIRST'):
      self.intrabar_collision_policy = 'STOP_FIRST'
    self.debug_mode = bool(debug_mode)
    self._diagnostic_rows = []
    self._rejection_reasons = {}
    self._counts = {'total_zones': 0, 'resistance_zones': 0, 'support_zones': 0, 'zone_interactions': 0, 'rejection_setups': 0, 'confirmed_setups': 0, 'executed_trades': 0, 'short_entries': 0, 'long_entries': 0, 'rejected_setups': 0, 'htf_bullish_short_rejections': 0, 'htf_bearish_long_rejections': 0, 'daily_cap_rejections': 0, 'monthly_cap_rejections': 0, 'spacing_rejections': 0, 'cooldown_rejections': 0, 'regime_interaction_rejections': 0, 'neutral_short_penetration_rejections': 0, 'neutral_long_weak_body_rejections': 0, 'neutral_long_overextended_rejections': 0, 'neutral_short_weak_confirmation_rejections': 0, 'neutral_short_ambiguous_wick_rejections': 0, 'neutral_long_moderate_strength_close_rejections': 0, 'neutral_long_age_confirmation_rejections': 0, 'neutral_long_ambiguous_moderate_rejections': 0, 'neutral_long_low_strength_wick_rejections': 0, 'neutral_long_shallow_wick_penetration_rejections': 0, 'neutral_short_high_body_rejections': 0, 'neutral_long_midclose_penetration_rejections': 0, 'neutral_long_stale_weak_confirmation_rejections': 0, 'neutral_long_medium_pen_weak_confirmation_rejections': 0, 'neutral_short_weak_body_midclose_rejections': 0, 'neutral_long_high_body_shallow_pen_rejections': 0, 'neutral_long_medium_pen_midhigh_confirmation_rejections': 0, 'bearish_short_sweep_weak_confirmation_rejections': 0, 'bullish_long_sweep_mid_confirmation_rejections': 0, 'neutral_long_deep_pen_mid_confirmation_rejections': 0, 'neutral_long_weak_body_mid_strength_rejections': 0, 'neutral_long_mid_age_mid_strength_rejections': 0, 'internal_trade_wins': 0, 'internal_trade_losses': 0, 'proposal_a_whitelisted': 0, 'proposal_a_executed': 0, 'proposal_b_whitelisted': 0, 'proposal_b_executed': 0, 'proposal_c_whitelisted': 0, 'proposal_c_executed': 0, 'proposal_d_whitelisted': 0, 'proposal_d_executed': 0, 'v3_1_candidate_a_rejections': 0, 'v3_2_candidate_a_rejections': 0, 'v3_3_candidate_a_rejections': 0, 'v3_4_candidate_a_rejections': 0, 'v3_5_candidate_a_rejections': 0}
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
    prev_close = df['Close'].shift(1)
    tr = pd.concat([df['High'] - df['Low'], (df['High'] - prev_close).abs(), (df['Low'] - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(self.atr_period, min_periods=1).mean()

  def _is_swing_high(self, df, pivot):
    if pivot < self.swing_left or pivot + self.swing_right >= len(df):
      return False
    value = float(df.iloc[pivot]['High'])
    left = df.iloc[pivot - self.swing_left:pivot]['High']
    right = df.iloc[pivot + 1:pivot + 1 + self.swing_right]['High']
    return value > float(left.max()) and value >= float(right.max())

  def _is_swing_low(self, df, pivot):
    if pivot < self.swing_left or pivot + self.swing_right >= len(df):
      return False
    value = float(df.iloc[pivot]['Low'])
    left = df.iloc[pivot - self.swing_left:pivot]['Low']
    right = df.iloc[pivot + 1:pivot + 1 + self.swing_right]['Low']
    return value < float(left.min()) and value <= float(right.min())

  def _candidate_zone(self, df, pivot, available, sequence, side):
    half = self.zone_width / 2.0
    follow_end = min(len(df), pivot + 1 + max(self.swing_right, 2))
    follow = df.iloc[pivot + 1:follow_end]
    if side == 'RESISTANCE':
      pivot_price = float(df.iloc[pivot]['High'])
      reaction = pivot_price - float(follow['Low'].min()) if not follow.empty else 0.0
      prefix = 'RRZ'
    else:
      pivot_price = float(df.iloc[pivot]['Low'])
      reaction = float(follow['High'].max()) - pivot_price if not follow.empty else 0.0
      prefix = 'SRZ'
    if reaction < self.minimum_reaction:
      return None
    strength = reaction / max(self.zone_width, 1e-09)
    if strength < self.minimum_strength:
      return None
    return SRZone(zone_id='%s-%05d' % (prefix, sequence), side=side, pivot_index=pivot, available_index=available, zone_low=pivot_price - half, zone_high=pivot_price + half, strength=float(strength))

  def _merge_or_add(self, zones, candidate):
    center = (candidate.zone_low + candidate.zone_high) / 2.0
    j = len(zones) - 1
    while j >= 0:
      zone = zones[j]
      if zone.side == candidate.side and (not zone.broken) and (not zone.consumed):
        zcenter = (zone.zone_low + zone.zone_high) / 2.0
        if abs(center - zcenter) <= self.merge_distance:
          zone.zone_low = min(zone.zone_low, candidate.zone_low)
          zone.zone_high = max(zone.zone_high, candidate.zone_high)
          zone.reactions += 1
          zone.strength = max(zone.strength, candidate.strength) + 0.25
          return False
      j -= 1
    zones.append(candidate)
    self._counts['total_zones'] += 1
    if candidate.side == 'RESISTANCE':
      self._counts['resistance_zones'] += 1
    else:
      self._counts['support_zones'] += 1
    return True

  def _zone_breakout(self, df, i, zone):
    close = float(df.iloc[i]['Close'])
    if zone.side == 'RESISTANCE':
      if self.breakout_rule == 'CLOSE_ABOVE_ZONE':
        return close > zone.zone_high
      if self.breakout_rule == 'CONSECUTIVE_CLOSES_ABOVE':
        n = self.breakout_consecutive_closes
        if i - n + 1 < 0:
          return False
        closes = df.iloc[i - n + 1:i + 1]['Close']
        return bool((closes > zone.zone_high).all())
      return close > zone.zone_high + self.breakout_buffer
    if self.breakout_rule == 'CONSECUTIVE_CLOSES_ABOVE':
      n = self.breakout_consecutive_closes
      if i - n + 1 < 0:
        return False
      closes = df.iloc[i - n + 1:i + 1]['Close']
      return bool((closes < zone.zone_low).all())
    if self.breakout_rule == 'CLOSE_ABOVE_ZONE':
      return close < zone.zone_low
    return close < zone.zone_low - self.breakout_buffer

  def _interaction(self, row, zone):
    high = float(row['High'])
    low = float(row['Low'])
    close = float(row['Close'])
    if zone.side == 'RESISTANCE':
      if high < zone.zone_low or low > zone.zone_high + self.breakout_buffer:
        return None
      if high > zone.zone_high and close < zone.zone_low:
        return 'SWEEP'
      if close < zone.zone_low and high >= zone.zone_low:
        return 'REJECTION'
      return 'TOUCH'
    if low > zone.zone_high or high < zone.zone_low - self.breakout_buffer:
      return None
    if low < zone.zone_low and close > zone.zone_high:
      return 'SWEEP'
    if close > zone.zone_high and low <= zone.zone_high:
      return 'REJECTION'
    return 'TOUCH'

  def _rejection(self, row, zone):
    high = float(row['High'])
    low = float(row['Low'])
    open_ = float(row['Open'])
    close = float(row['Close'])
    rng = max(high - low, 1e-09)
    body_ratio = abs(close - open_) / rng
    if zone.side == 'RESISTANCE':
      upper_wick_ratio = (high - max(open_, close)) / rng
      close_position = (close - low) / rng
      penetration = max(0.0, high - zone.zone_low) / max(zone.zone_high - zone.zone_low, 1e-09)
      failed_side = close < zone.zone_low
      candle_shape = body_ratio >= self.minimum_body_ratio or upper_wick_ratio >= self.minimum_upper_wick_ratio
      return bool(high >= zone.zone_low and failed_side and candle_shape and (penetration >= self.minimum_zone_penetration) and (close_position <= self.maximum_close_position))
    lower_wick_ratio = (min(open_, close) - low) / rng
    close_position_from_high = (high - close) / rng
    penetration = max(0.0, zone.zone_high - low) / max(zone.zone_high - zone.zone_low, 1e-09)
    failed_side = close > zone.zone_high
    candle_shape = body_ratio >= self.minimum_body_ratio or lower_wick_ratio >= self.minimum_lower_wick_ratio
    return bool(low <= zone.zone_high and failed_side and candle_shape and (penetration >= self.minimum_zone_penetration) and (close_position_from_high <= self.maximum_close_position))

  def _record_rejection(self, reason):
    key = str(reason)
    self._counts['rejected_setups'] += 1
    self._rejection_reasons[key] = self._rejection_reasons.get(key, 0) + 1

  def _sl(self, df, i, setup):
    entry = float(df.iloc[i]['Close'])
    if setup.direction == 'SHORT':
      if self.sl_mode == 'SWEEP_HIGH' and setup.sweep_extreme is not None:
        return float(setup.sweep_extreme) + self.sl_buffer
      if self.sl_mode == 'ZONE_HIGH':
        return float(setup.zone.zone_high) + self.sl_buffer
      if self.sl_mode == 'FIXED_DISTANCE':
        return entry + self.fixed_sl_distance
      if self.sl_mode == 'ATR_BUFFER':
        atr_value = df.iloc[i].get('_rr_atr', 0.0)
        atr = float(atr_value) if pd.notna(atr_value) else 0.0
        base = float(setup.rejection_high if setup.rejection_high is not None else setup.zone.zone_high)
        return base + atr * self.atr_buffer_multiplier + self.sl_buffer
      base = setup.rejection_high if setup.rejection_high is not None else setup.zone.zone_high
      return float(base) + self.sl_buffer
    if self.sl_mode == 'SWEEP_HIGH' and setup.sweep_extreme is not None:
      return float(setup.sweep_extreme) - self.sl_buffer
    if self.sl_mode == 'ZONE_HIGH':
      return float(setup.zone.zone_low) - self.sl_buffer
    if self.sl_mode == 'FIXED_DISTANCE':
      return entry - self.fixed_sl_distance
    if self.sl_mode == 'ATR_BUFFER':
      atr_value = df.iloc[i].get('_rr_atr', 0.0)
      atr = float(atr_value) if pd.notna(atr_value) else 0.0
      base = float(setup.rejection_low if setup.rejection_low is not None else setup.zone.zone_low)
      return base - atr * self.atr_buffer_multiplier - self.sl_buffer
    base = setup.rejection_low if setup.rejection_low is not None else setup.zone.zone_low
    return float(base) - self.sl_buffer

  def _tp(self, df, i, direction, entry, sl):
    risk = abs(entry - sl)
    if direction == 'SHORT':
      if self.tp_mode in ('PREVIOUS_SUPPORT', 'SWING_LOW', 'LIQUIDITY_TARGET'):
        lookback = df.iloc[max(0, i - 40):i]
        if not lookback.empty:
          structural = float(lookback['Low'].min())
          if structural < entry:
            return structural
      return entry - risk * self.target_rr
    if self.tp_mode in ('PREVIOUS_SUPPORT', 'SWING_LOW', 'LIQUIDITY_TARGET', 'PREVIOUS_RESISTANCE', 'SWING_HIGH'):
      lookback = df.iloc[max(0, i - 40):i]
      if not lookback.empty:
        structural = float(lookback['High'].max())
        if structural > entry:
          return structural
    return entry + risk * self.target_rr

  def _infer_source_timeframe_minutes(self, df):
    if self.source_timeframe_minutes > 0:
      minutes = self.source_timeframe_minutes
    else:
      diffs = df['Date'].diff().dropna()
      if diffs.empty:
        raise ValueError('Cannot infer source timeframe from fewer than 2 candles')
      minutes = int(round(float(diffs.median().total_seconds()) / 60.0))
    if minutes <= 0:
      raise ValueError('Invalid source timeframe')
    if self.htf_timeframe_minutes % minutes != 0:
      raise ValueError('Source timeframe must divide 15 minutes exactly; got %sM' % minutes)
    return minutes

  def _build_complete_15m(self, df, source_minutes):
    expected = int(self.htf_timeframe_minutes / source_minutes)
    work = df[['Date', 'Open', 'High', 'Low', 'Close']].copy().set_index('Date')
    rule = '%dmin' % self.htf_timeframe_minutes
    ohlc = work.resample(rule, label='left', closed='left').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    counts = work['Close'].resample(rule, label='left', closed='left').count()
    ohlc['_source_count'] = counts
    ohlc = ohlc.dropna(subset=['Open', 'High', 'Low', 'Close'])
    ohlc = ohlc[ohlc['_source_count'] == expected].reset_index()
    ohlc['_htf_close_time'] = ohlc['Date'] + pd.Timedelta(minutes=self.htf_timeframe_minutes)
    return ohlc

  def _is_htf_swing_high(self, htf, pivot):
    if pivot < self.htf_swing_left or pivot + self.htf_swing_right >= len(htf):
      return False
    value = float(htf.iloc[pivot]['High'])
    left = htf.iloc[pivot - self.htf_swing_left:pivot]['High']
    right = htf.iloc[pivot + 1:pivot + 1 + self.htf_swing_right]['High']
    return value > float(left.max()) and value >= float(right.max())

  def _is_htf_swing_low(self, htf, pivot):
    if pivot < self.htf_swing_left or pivot + self.htf_swing_right >= len(htf):
      return False
    value = float(htf.iloc[pivot]['Low'])
    left = htf.iloc[pivot - self.htf_swing_left:pivot]['Low']
    right = htf.iloc[pivot + 1:pivot + 1 + self.htf_swing_right]['Low']
    return value < float(left.min()) and value <= float(right.min())

  def _build_15m_structure_snapshots(self, htf):
    confirmed_highs = []
    confirmed_lows = []
    snapshots = []
    for j in range(len(htf)):
      pivot = j - self.htf_swing_right
      if self._is_htf_swing_high(htf, pivot):
        confirmed_highs.append(float(htf.iloc[pivot]['High']))
      if self._is_htf_swing_low(htf, pivot):
        confirmed_lows.append(float(htf.iloc[pivot]['Low']))
      previous_high = confirmed_highs[-2] if len(confirmed_highs) >= 2 else None
      last_high = confirmed_highs[-1] if len(confirmed_highs) >= 1 else None
      previous_low = confirmed_lows[-2] if len(confirmed_lows) >= 2 else None
      last_low = confirmed_lows[-1] if len(confirmed_lows) >= 1 else None
      bias = 'NEUTRAL'
      reason = 'INSUFFICIENT_CONFIRMED_SWINGS'
      if previous_high is not None and last_high is not None and (previous_low is not None) and (last_low is not None):
        if last_high > previous_high and last_low > previous_low:
          bias = 'BULLISH'
          reason = 'HH_AND_HL'
        elif last_high < previous_high and last_low < previous_low:
          bias = 'BEARISH'
          reason = 'LH_AND_LL'
        else:
          bias = 'NEUTRAL'
          reason = 'MIXED_STRUCTURE'
      snapshots.append({'available_time': pd.Timestamp(htf.iloc[j]['_htf_close_time']), 'bias': bias, 'reason': reason, 'last_swing_high': last_high, 'previous_swing_high': previous_high, 'last_swing_low': last_low, 'previous_swing_low': previous_low})
    return snapshots

  def _attach_15m_context(self, df, source_minutes):
    df['htf_15m_bias'] = 'NEUTRAL'
    df['htf_15m_structure_reason'] = 'INSUFFICIENT_CONFIRMED_SWINGS'
    df['htf_15m_last_swing_high'] = pd.NA
    df['htf_15m_previous_swing_high'] = pd.NA
    df['htf_15m_last_swing_low'] = pd.NA
    df['htf_15m_previous_swing_low'] = pd.NA
    if not self.htf_context_enabled:
      df['htf_15m_structure_reason'] = 'HTF_CONTEXT_DISABLED'
      return df
    htf = self._build_complete_15m(df, source_minutes)
    self._htf_bar_count = len(htf)
    if htf.empty:
      return df
    snapshots = self._build_15m_structure_snapshots(htf)
    pointer = -1
    for i in range(len(df)):
      decision_time = pd.Timestamp(df.iloc[i]['Date']) + pd.Timedelta(minutes=source_minutes)
      while pointer + 1 < len(snapshots) and snapshots[pointer + 1]['available_time'] <= decision_time:
        pointer += 1
      if pointer >= 0:
        snap = snapshots[pointer]
        idx = df.index[i]
        df.at[idx, 'htf_15m_bias'] = snap['bias']
        df.at[idx, 'htf_15m_structure_reason'] = snap['reason']
        if snap['last_swing_high'] is not None:
          df.at[idx, 'htf_15m_last_swing_high'] = snap['last_swing_high']
        if snap['previous_swing_high'] is not None:
          df.at[idx, 'htf_15m_previous_swing_high'] = snap['previous_swing_high']
        if snap['last_swing_low'] is not None:
          df.at[idx, 'htf_15m_last_swing_low'] = snap['last_swing_low']
        if snap['previous_swing_low'] is not None:
          df.at[idx, 'htf_15m_previous_swing_low'] = snap['previous_swing_low']
    return df

  def _update_internal_trade(self, df, i):
    if self._open_trade is None:
      return
    if i <= self._open_trade['entry_index']:
      return
    row = df.iloc[i]
    high = float(row['High'])
    low = float(row['Low'])
    direction = self._open_trade['direction']
    sl = float(self._open_trade['sl'])
    tp = float(self._open_trade['tp'])
    if direction == 'SHORT':
      hit_sl = high >= sl
      hit_tp = low <= tp
    else:
      hit_sl = low <= sl
      hit_tp = high >= tp
    if not hit_sl and (not hit_tp):
      return
    if hit_sl and hit_tp:
      result = 'LOSS' if self.intrabar_collision_policy == 'STOP_FIRST' else 'WIN'
    elif hit_sl:
      result = 'LOSS'
    else:
      result = 'WIN'
    entry_day = self._open_trade['entry_day']
    if result == 'LOSS':
      self._counts['internal_trade_losses'] += 1
      if self._loss_streak_day == entry_day:
        self._same_day_loss_streak += 1
      else:
        self._loss_streak_day = entry_day
        self._same_day_loss_streak = 1
      if self.cooldown_enabled and self._same_day_loss_streak >= self.cooldown_after_losses:
        self._cooldown_remaining = self.cooldown_skip_setups
    else:
      self._counts['internal_trade_wins'] += 1
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
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    if direction == 'SHORT' and bias == 'BULLISH':
      return '15M_BULLISH_CONTEXT'
    if direction == 'LONG' and bias == 'BEARISH':
      return '15M_BEARISH_CONTEXT'
    return None

  def _regime_interaction_rejection_reason(self, df, i, active):
    if not self.regime_interaction_filter:
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    direction = active.direction
    if bias == 'NEUTRAL' and interaction != 'REJECTION':
      return 'NEUTRAL_REQUIRES_REJECTION'
    if direction == 'LONG' and bias == 'BULLISH' and (interaction != 'SWEEP'):
      return 'BULLISH_LONG_REQUIRES_SWEEP'
    if direction == 'SHORT' and bias == 'BEARISH' and (interaction != 'SWEEP'):
      return 'BEARISH_SHORT_REQUIRES_SWEEP'
    return None

  def _proposal_a_whitelist_matches(self, df, i, active, reason):
    pass
    if not self.proposal_a_expansion_enabled:
      return False
    if str(reason) != 'BEARISH_SHORT_REQUIRES_SWEEP':
      return False
    if active.direction != 'SHORT':
      return False
    if str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL')) != 'BEARISH':
      return False
    if str(active.interaction_type or '').upper() != 'REJECTION':
      return False
    if active.rejection_index is None:
      return False
    rejection_row = df.iloc[int(active.rejection_index)]
    body_ratio = self._rejection_quality_metrics(rejection_row, active.zone)[0]
    return bool(float(body_ratio) >= self.proposal_a_min_body_ratio and float(body_ratio) < self.proposal_a_max_body_ratio)

  def _proposal_b_whitelist_matches(self, df, i, active, reason):
    pass
    if not self.proposal_b_expansion_enabled:
      return False
    if str(reason) != 'BULLISH_LONG_REQUIRES_SWEEP':
      return False
    if active.direction != 'LONG':
      return False
    if str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL')) != 'BULLISH':
      return False
    if str(active.interaction_type or '').upper() != 'REJECTION':
      return False
    zone_age = i - int(active.zone.available_index)
    return bool(int(zone_age) >= self.proposal_b_min_zone_age and int(zone_age) < self.proposal_b_max_zone_age)

  def _proposal_c_whitelist_matches(self, df, i, active, reason):
    pass
    if not self.proposal_c_expansion_enabled:
      return False
    if str(reason) != 'BEARISH_SHORT_REQUIRES_SWEEP':
      return False
    if active.direction != 'SHORT':
      return False
    if str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL')) != 'BEARISH':
      return False
    if str(active.interaction_type or '').upper() != 'REJECTION':
      return False
    zone_age = i - int(active.zone.available_index)
    return bool(int(zone_age) >= self.proposal_c_min_zone_age and int(zone_age) < self.proposal_c_max_zone_age)

  def _proposal_d_whitelist_matches(self, df, i, active, reason):
    pass
    if not self.proposal_d_expansion_enabled:
      return False
    if str(reason) != '15M_BEARISH_CONTEXT':
      return False
    if active.direction != 'LONG':
      return False
    if str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL')) != 'BEARISH':
      return False
    if str(active.interaction_type or '').upper() != 'REJECTION':
      return False
    displacement = self._confirmation_quality_tuple(df, i, active)[0]
    return bool(float(displacement) >= self.proposal_d_min_confirmation_displacement and float(displacement) < self.proposal_d_max_confirmation_displacement)

  def _v3_1_candidate_a_rejection_reason(self, df, i, active, proposal_a_whitelisted, proposal_b_whitelisted, proposal_c_whitelisted, proposal_d_whitelisted):
    pass
    if not self.v3_1_candidate_a_filter:
      return None
    if proposal_a_whitelisted or proposal_b_whitelisted or proposal_c_whitelisted or proposal_d_whitelisted:
      return None
    rejection_row = df.iloc[active.rejection_index]
    _body, wick, _close, _penetration = self._rejection_quality_metrics(rejection_row, active.zone)
    displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if float(wick) >= self.v3_1_candidate_a_min_rejection_wick and float(wick) < self.v3_1_candidate_a_max_rejection_wick and (float(displacement) >= self.v3_1_candidate_a_min_confirmation_displacement) and (float(displacement) < self.v3_1_candidate_a_max_confirmation_displacement):
      return 'V3_1_WEAK_ORIGINAL_MEDIUM_WICK_HIGH_CONFIRMATION'
    return None

  def _v3_2_candidate_a_rejection_reason(self, df, i, active):
    pass
    if not self.v3_2_candidate_a_filter:
      return None
    if active.direction != 'SHORT':
      return None
    zone_age = i - int(active.zone.available_index)
    displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if int(zone_age) >= self.v3_2_candidate_a_min_zone_age and int(zone_age) < self.v3_2_candidate_a_max_zone_age and (float(displacement) >= self.v3_2_candidate_a_min_confirmation_displacement) and (float(displacement) < self.v3_2_candidate_a_max_confirmation_displacement):
      return 'V3_2_WEAK_SHORT_MID_AGE_MID_CONFIRMATION'
    return None

  def _v3_3_candidate_a_rejection_reason(self, df, i, active):
    pass
    if not self.v3_3_candidate_a_filter:
      return None
    if str(active.interaction_type or '').upper() != 'REJECTION':
      return None
    rejection_row = df.iloc[active.rejection_index]
    _body, _wick, close_position, _penetration = self._rejection_quality_metrics(rejection_row, active.zone)
    strength = float(active.zone.strength)
    if strength >= self.v3_3_candidate_a_min_zone_strength and strength < self.v3_3_candidate_a_max_zone_strength and (float(close_position) >= self.v3_3_candidate_a_min_rejection_close) and (float(close_position) < self.v3_3_candidate_a_max_rejection_close):
      return 'V3_3_WEAK_REJECTION_MID_STRENGTH_MIDCLOSE'
    return None

  def _v3_4_candidate_a_rejection_reason(self, df, i, active):
    pass
    if not self.v3_4_candidate_a_filter:
      return None
    if active.direction != 'LONG':
      return None
    current_year = int(df.iloc[i]['Date'].year)
    if self.v3_4_candidate_a_start_year > 0 and current_year < self.v3_4_candidate_a_start_year:
      return None
    rejection_row = df.iloc[active.rejection_index]
    body, _wick, close_position, _penetration = self._rejection_quality_metrics(rejection_row, active.zone)
    if float(body) >= self.v3_4_candidate_a_min_rejection_body and float(body) < self.v3_4_candidate_a_max_rejection_body and (float(close_position) >= self.v3_4_candidate_a_min_rejection_close) and (float(close_position) < self.v3_4_candidate_a_max_rejection_close):
      return 'V3_4_WEAK_LONG_MIDHIGH_BODY_MIDCLOSE'
    return None

  def _v3_5_candidate_a_rejection_reason(self, df, i, active, proposal_a_whitelisted, proposal_b_whitelisted, proposal_c_whitelisted, proposal_d_whitelisted):
    pass
    if not self.v3_5_candidate_a_filter:
      return None
    if active.direction != 'SHORT':
      return None
    if proposal_a_whitelisted or proposal_b_whitelisted or proposal_c_whitelisted or proposal_d_whitelisted:
      return None
    zone_age = i - int(active.zone.available_index)
    if int(zone_age) >= self.v3_5_candidate_a_min_zone_age and int(zone_age) < self.v3_5_candidate_a_max_zone_age:
      return 'V3_5_WEAK_SHORT_BASE_YOUNG_ZONE'
    return None

  def _neutral_short_penetration_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_short_penetration_filter:
      return None
    if active.direction != 'SHORT':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, _, _, penetration = self._rejection_quality_metrics(rejection_row, active.zone)
    if float(penetration) < self.neutral_short_min_penetration:
      return 'INSUFFICIENT_RESISTANCE_PENETRATION'
    return None

  def _neutral_long_body_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_body_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    body_ratio, _, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    if float(body_ratio) >= self.neutral_long_weak_body_min and float(body_ratio) < self.neutral_long_weak_body_max:
      return 'WEAK_NEUTRAL_LONG_REJECTION_BODY'
    return None

  def _neutral_long_overextended_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_overextended_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, wick_ratio, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if float(wick_ratio) >= self.neutral_long_min_overextended_wick and float(confirmation_displacement) >= self.neutral_long_min_overextended_confirmation:
      return 'OVEREXTENDED_NEUTRAL_LONG_CONFIRMATION'
    return None

  def _neutral_short_weak_confirmation_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_short_weak_confirmation_filter:
      return None
    if active.direction != 'SHORT':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    zone_strength = float(active.zone.strength)
    confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if zone_strength < self.neutral_short_max_weak_zone_strength and float(confirmation_displacement) < self.neutral_short_max_weak_confirmation_displacement:
      return 'WEAK_NEUTRAL_SHORT_CONFIRMATION'
    return None

  def _neutral_short_ambiguous_wick_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_short_ambiguous_wick_filter:
      return None
    if active.direction != 'SHORT':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, wick_ratio, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    if float(wick_ratio) >= self.neutral_short_ambiguous_wick_min and float(wick_ratio) < self.neutral_short_ambiguous_wick_max:
      return 'AMBIGUOUS_NEUTRAL_SHORT_REJECTION_WICK'
    return None

  def _neutral_long_moderate_strength_close_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_moderate_strength_close_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, _, close_position, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    zone_strength = float(active.zone.strength)
    if zone_strength >= self.neutral_long_moderate_strength_min and zone_strength < self.neutral_long_moderate_strength_max and (float(close_position) < self.neutral_long_max_close_position):
      return 'WEAK_MODERATE_STRENGTH_NEUTRAL_LONG_REJECTION'
    return None

  def _neutral_long_age_confirmation_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_age_confirmation_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    zone_age = i - int(active.zone.available_index)
    confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if int(zone_age) >= self.neutral_long_age_confirmation_min_age and int(zone_age) < self.neutral_long_age_confirmation_max_age and (float(confirmation_displacement) >= self.neutral_long_age_confirmation_min_displacement) and (float(confirmation_displacement) < self.neutral_long_age_confirmation_max_displacement):
      return 'WEAK_YOUNG_NEUTRAL_LONG_CONFIRMATION'
    return None

  def _neutral_long_ambiguous_moderate_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_ambiguous_moderate_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, wick_ratio, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    zone_strength = float(active.zone.strength)
    if zone_strength >= self.neutral_long_ambiguous_moderate_min_zone_strength and zone_strength < self.neutral_long_ambiguous_moderate_max_zone_strength and (float(wick_ratio) >= self.neutral_long_ambiguous_moderate_min_wick) and (float(wick_ratio) < self.neutral_long_ambiguous_moderate_max_wick):
      return 'AMBIGUOUS_MODERATE_NEUTRAL_LONG_REJECTION'
    return None

  def _neutral_long_low_strength_wick_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_low_strength_wick_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, wick_ratio, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    zone_strength = float(active.zone.strength)
    if zone_strength >= self.neutral_long_low_strength_min_zone_strength and zone_strength < self.neutral_long_low_strength_max_zone_strength and (float(wick_ratio) >= self.neutral_long_low_strength_min_wick) and (float(wick_ratio) < self.neutral_long_low_strength_max_wick):
      return 'WEAK_LOW_STRENGTH_NEUTRAL_LONG_REJECTION'
    return None

  def _neutral_long_shallow_wick_penetration_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_shallow_wick_penetration_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, wick_ratio, _, penetration = self._rejection_quality_metrics(rejection_row, active.zone)
    if float(wick_ratio) >= self.neutral_long_shallow_wick_min and float(wick_ratio) < self.neutral_long_shallow_wick_max and (float(penetration) < self.neutral_long_shallow_max_penetration):
      return 'SHALLOW_WICK_NEUTRAL_LONG_REJECTION'
    return None

  def _neutral_short_high_body_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_short_high_body_filter:
      return None
    if active.direction != 'SHORT':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    body_ratio, _, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    if float(body_ratio) >= self.neutral_short_high_body_min and float(body_ratio) < self.neutral_short_high_body_max:
      return 'WEAK_HIGH_BODY_NEUTRAL_SHORT_REJECTION'
    return None

  def _neutral_long_midclose_penetration_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_midclose_penetration_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, _, close_position, penetration = self._rejection_quality_metrics(rejection_row, active.zone)
    if float(close_position) >= self.neutral_long_midclose_min_close and float(close_position) < self.neutral_long_midclose_max_close and (float(penetration) >= self.neutral_long_midclose_min_penetration) and (float(penetration) < self.neutral_long_midclose_max_penetration):
      return 'WEAK_MIDCLOSE_NEUTRAL_LONG_REJECTION'
    return None

  def _neutral_long_stale_weak_confirmation_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_stale_weak_confirmation_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    zone_age = i - int(active.zone.available_index)
    confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if int(zone_age) >= self.neutral_long_stale_min_zone_age and float(confirmation_displacement) >= self.neutral_long_stale_min_confirmation_displacement and (float(confirmation_displacement) < self.neutral_long_stale_max_confirmation_displacement):
      return 'STALE_WEAK_CONFIRMATION_NEUTRAL_LONG_REJECTION'
    return None

  def _neutral_long_medium_pen_weak_confirmation_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_medium_pen_weak_confirmation_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, _, _, penetration = self._rejection_quality_metrics(rejection_row, active.zone)
    confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if float(penetration) >= self.neutral_long_medium_pen_min_penetration and float(penetration) < self.neutral_long_medium_pen_max_penetration and (float(confirmation_displacement) >= self.neutral_long_medium_pen_min_confirmation_displacement) and (float(confirmation_displacement) < self.neutral_long_medium_pen_max_confirmation_displacement):
      return 'WEAK_MEDIUM_PENETRATION_NEUTRAL_LONG_CONFIRMATION'
    return None

  def _neutral_short_weak_body_midclose_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_short_weak_body_midclose_filter:
      return None
    if active.direction != 'SHORT':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    body_ratio, _, close_position, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    if float(body_ratio) >= self.neutral_short_weak_body_midclose_min_body and float(body_ratio) < self.neutral_short_weak_body_midclose_max_body and (float(close_position) >= self.neutral_short_weak_body_midclose_min_close) and (float(close_position) < self.neutral_short_weak_body_midclose_max_close):
      return 'WEAK_BODY_MIDCLOSE_NEUTRAL_SHORT_REJECTION'
    return None

  def _neutral_long_high_body_shallow_pen_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_high_body_shallow_pen_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    body_ratio, _, _, penetration = self._rejection_quality_metrics(rejection_row, active.zone)
    if float(body_ratio) >= self.neutral_long_high_body_shallow_pen_min_body and float(body_ratio) < self.neutral_long_high_body_shallow_pen_max_body and (float(penetration) >= self.neutral_long_high_body_shallow_pen_min_penetration) and (float(penetration) < self.neutral_long_high_body_shallow_pen_max_penetration):
      return 'WEAK_HIGH_BODY_SHALLOW_PEN_NEUTRAL_LONG_REJECTION'
    return None

  def _neutral_long_medium_pen_midhigh_confirmation_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_medium_pen_midhigh_confirmation_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, _, _, penetration = self._rejection_quality_metrics(rejection_row, active.zone)
    confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if float(penetration) >= self.neutral_long_medium_pen_midhigh_min_penetration and float(penetration) < self.neutral_long_medium_pen_midhigh_max_penetration and (float(confirmation_displacement) >= self.neutral_long_medium_pen_midhigh_min_confirmation_displacement) and (float(confirmation_displacement) < self.neutral_long_medium_pen_midhigh_max_confirmation_displacement):
      return 'WEAK_MEDIUM_PEN_MIDHIGH_CONFIRM_NEUTRAL_LONG_REJECTION'
    return None

  def _bearish_short_sweep_weak_confirmation_rejection_reason(self, df, i, active):
    pass
    if not self.bearish_short_sweep_weak_confirmation_filter:
      return None
    if active.direction != 'SHORT':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'BEARISH' or interaction != 'SWEEP':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, _, close_position, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if float(close_position) >= self.bearish_short_sweep_min_close and float(close_position) < self.bearish_short_sweep_max_close and (float(confirmation_displacement) >= self.bearish_short_sweep_min_confirmation_displacement) and (float(confirmation_displacement) < self.bearish_short_sweep_max_confirmation_displacement):
      return 'WEAK_BEARISH_SHORT_SWEEP_CONFIRMATION'
    return None

  def _bullish_long_sweep_mid_confirmation_rejection_reason(self, df, i, active):
    pass
    if not self.bullish_long_sweep_mid_confirmation_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'BULLISH' or interaction != 'SWEEP':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, _, close_position, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if float(close_position) >= self.bullish_long_sweep_min_close and float(close_position) < self.bullish_long_sweep_max_close and (float(confirmation_displacement) >= self.bullish_long_sweep_min_confirmation_displacement) and (float(confirmation_displacement) < self.bullish_long_sweep_max_confirmation_displacement):
      return 'WEAK_BULLISH_LONG_SWEEP_CONFIRMATION'
    return None

  def _neutral_long_deep_pen_mid_confirmation_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_deep_pen_mid_confirmation_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    _, _, _, penetration = self._rejection_quality_metrics(rejection_row, active.zone)
    confirmation_displacement = self._confirmation_quality_tuple(df, i, active)[0]
    if float(penetration) >= self.neutral_long_deep_pen_mid_confirmation_min_penetration and float(penetration) < self.neutral_long_deep_pen_mid_confirmation_max_penetration and (float(confirmation_displacement) >= self.neutral_long_deep_pen_mid_confirmation_min_displacement) and (float(confirmation_displacement) < self.neutral_long_deep_pen_mid_confirmation_max_displacement):
      return 'WEAK_DEEP_PEN_MID_CONFIRM_NEUTRAL_LONG_REJECTION'
    return None

  def _neutral_long_weak_body_mid_strength_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_weak_body_mid_strength_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    if active.rejection_index is None:
      return None
    rejection_row = df.iloc[int(active.rejection_index)]
    body_ratio, _, _, _ = self._rejection_quality_metrics(rejection_row, active.zone)
    zone_strength = float(active.zone.strength)
    if float(body_ratio) >= self.neutral_long_weak_body_mid_strength_min_body and float(body_ratio) < self.neutral_long_weak_body_mid_strength_max_body and (zone_strength >= self.neutral_long_weak_body_mid_strength_min_zone_strength) and (zone_strength < self.neutral_long_weak_body_mid_strength_max_zone_strength):
      return 'WEAK_BODY_MID_STRENGTH_NEUTRAL_LONG_REJECTION'
    return None

  def _neutral_long_mid_age_mid_strength_rejection_reason(self, df, i, active):
    pass
    if not self.neutral_long_mid_age_mid_strength_filter:
      return None
    if active.direction != 'LONG':
      return None
    bias = str(df.iloc[i].get('htf_15m_bias', 'NEUTRAL'))
    interaction = str(active.interaction_type or '').upper()
    if bias != 'NEUTRAL' or interaction != 'REJECTION':
      return None
    zone_age = i - int(active.zone.available_index)
    zone_strength = float(active.zone.strength)
    if int(zone_age) >= self.neutral_long_mid_age_mid_strength_min_age and int(zone_age) < self.neutral_long_mid_age_mid_strength_max_age and (zone_strength >= self.neutral_long_mid_age_mid_strength_min_zone_strength) and (zone_strength < self.neutral_long_mid_age_mid_strength_max_zone_strength):
      return 'WEAK_AGE_MID_STRENGTH_NEUTRAL_LONG_REJECTION'
    return None

  def _rejection_quality_metrics(self, row, zone):
    high = float(row['High'])
    low = float(row['Low'])
    open_ = float(row['Open'])
    close = float(row['Close'])
    rng = max(high - low, 1e-09)
    body_ratio = abs(close - open_) / rng
    zone_range = max(zone.zone_high - zone.zone_low, 1e-09)
    if zone.side == 'RESISTANCE':
      wick_ratio = (high - max(open_, close)) / rng
      close_position = (close - low) / rng
      penetration = max(0.0, high - zone.zone_low) / zone_range
    else:
      wick_ratio = (min(open_, close) - low) / rng
      close_position = (high - close) / rng
      penetration = max(0.0, zone.zone_high - low) / zone_range
    return (body_ratio, wick_ratio, close_position, penetration)

  def _confirmation_quality_tuple(self, df, i, active):
    row = df.iloc[i]
    close = float(row['Close'])
    rejection_range = max(float(active.rejection_high) - float(active.rejection_low), 1e-09)
    if active.direction == 'SHORT':
      displacement = max(0.0, float(active.rejection_low) - close) / rejection_range
    else:
      displacement = max(0.0, close - float(active.rejection_high)) / rejection_range
    return (float(displacement), float(active.zone.strength))

  def _frequency_rejection_reason(self, df, i):
    ts = pd.Timestamp(df.iloc[i]['Date'])
    day_key = self._day_key_from_timestamp(ts)
    month_key = self._month_key_from_timestamp(ts)
    if self.max_entries_per_month > 0 and self._entries_by_month.get(month_key, 0) >= self.max_entries_per_month:
      return 'MONTHLY_TRADE_CAP'
    if self.max_entries_per_day > 0 and self._entries_by_day.get(day_key, 0) >= self.max_entries_per_day:
      return 'DAILY_TRADE_CAP'
    if self.min_bars_between_entries > 0 and self._last_entry_index is not None:
      if i - self._last_entry_index < self.min_bars_between_entries:
        return 'ENTRY_SPACING'
    return None

  def _mark_entry_count(self, df, i):
    ts = pd.Timestamp(df.iloc[i]['Date'])
    day_key = self._day_key_from_timestamp(ts)
    month_key = self._month_key_from_timestamp(ts)
    self._entries_by_day[day_key] = self._entries_by_day.get(day_key, 0) + 1
    self._entries_by_month[month_key] = self._entries_by_month.get(month_key, 0) + 1
    self._last_entry_index = i

  def _emit_diag(self, df, i, setup, decision, reason, rr=None, entry=None, sl=None, tp=None):
    row = df.iloc[i]
    self._diagnostic_rows.append({'strategy_version': 'V1.22-LS', 'setup_id': setup.setup_id, 'zone_id': setup.zone.zone_id, 'timestamp': self._timestamp_text(pd.Timestamp(row['Date'])), 'direction': setup.direction, 'zone_side': setup.zone.side, 'state': setup.state, 'zone_low': float(setup.zone.zone_low), 'zone_high': float(setup.zone.zone_high), 'zone_strength': float(setup.zone.strength), 'interaction': setup.interaction_type, 'rejection_high': setup.rejection_high, 'rejection_low': setup.rejection_low, 'htf_15m_bias': str(row.get('htf_15m_bias', 'NEUTRAL')), 'htf_15m_structure_reason': str(row.get('htf_15m_structure_reason', '')), 'entry': entry, 'stop_loss': sl, 'take_profit': tp, 'rr': rr, 'same_day_loss_streak': self._same_day_loss_streak, 'cooldown_remaining': self._cooldown_remaining, 'final_decision': decision, 'rejection_reason': reason})

  def _reject_confirmed_setup(self, df, i, active, reason, rr=None, entry=None, sl=None, tp=None):
    active.state = 'REJECTED'
    self._record_rejection(reason)
    idx = df.index[i]
    df.at[idx, 'rr_state'] = 'REJECTED'
    df.at[idx, 'rejection_reason'] = reason
    df.at[idx, 'signal_reason'] = 'Blocked %s: %s' % (active.direction, reason)
    df.at[idx, 'rr_setup_id'] = active.setup_id
    df.at[idx, 'rr_zone_id'] = active.zone.zone_id
    df.at[idx, 'rr_zone_low'] = active.zone.zone_low
    df.at[idx, 'rr_zone_high'] = active.zone.zone_high
    df.at[idx, 'rr_interaction'] = active.interaction_type
    df.at[idx, 'rr_direction'] = active.direction
    if reason == '15M_BULLISH_CONTEXT':
      self._counts['htf_bullish_short_rejections'] += 1
    elif reason == '15M_BEARISH_CONTEXT':
      self._counts['htf_bearish_long_rejections'] += 1
    elif reason == 'DAILY_TRADE_CAP':
      self._counts['daily_cap_rejections'] += 1
    elif reason == 'MONTHLY_TRADE_CAP':
      self._counts['monthly_cap_rejections'] += 1
    elif reason == 'ENTRY_SPACING':
      self._counts['spacing_rejections'] += 1
    elif reason == 'TWO_LOSS_COOLDOWN':
      self._counts['cooldown_rejections'] += 1
    elif reason in ('NEUTRAL_REQUIRES_REJECTION', 'BULLISH_LONG_REQUIRES_SWEEP', 'BEARISH_SHORT_REQUIRES_SWEEP'):
      self._counts['regime_interaction_rejections'] += 1
    elif reason == 'INSUFFICIENT_RESISTANCE_PENETRATION':
      self._counts['neutral_short_penetration_rejections'] += 1
    elif reason == 'WEAK_NEUTRAL_LONG_REJECTION_BODY':
      self._counts['neutral_long_weak_body_rejections'] += 1
    elif reason == 'OVEREXTENDED_NEUTRAL_LONG_CONFIRMATION':
      self._counts['neutral_long_overextended_rejections'] += 1
    elif reason == 'WEAK_NEUTRAL_SHORT_CONFIRMATION':
      self._counts['neutral_short_weak_confirmation_rejections'] += 1
    elif reason == 'AMBIGUOUS_NEUTRAL_SHORT_REJECTION_WICK':
      self._counts['neutral_short_ambiguous_wick_rejections'] += 1
    elif reason == 'WEAK_MODERATE_STRENGTH_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_moderate_strength_close_rejections'] += 1
    elif reason == 'WEAK_YOUNG_NEUTRAL_LONG_CONFIRMATION':
      self._counts['neutral_long_age_confirmation_rejections'] += 1
    elif reason == 'AMBIGUOUS_MODERATE_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_ambiguous_moderate_rejections'] += 1
    elif reason == 'WEAK_LOW_STRENGTH_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_low_strength_wick_rejections'] += 1
    elif reason == 'SHALLOW_WICK_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_shallow_wick_penetration_rejections'] += 1
    elif reason == 'WEAK_HIGH_BODY_NEUTRAL_SHORT_REJECTION':
      self._counts['neutral_short_high_body_rejections'] += 1
    elif reason == 'WEAK_MIDCLOSE_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_midclose_penetration_rejections'] += 1
    elif reason == 'STALE_WEAK_CONFIRMATION_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_stale_weak_confirmation_rejections'] += 1
    elif reason == 'WEAK_MEDIUM_PENETRATION_NEUTRAL_LONG_CONFIRMATION':
      self._counts['neutral_long_medium_pen_weak_confirmation_rejections'] += 1
    elif reason == 'WEAK_BODY_MIDCLOSE_NEUTRAL_SHORT_REJECTION':
      self._counts['neutral_short_weak_body_midclose_rejections'] += 1
    elif reason == 'WEAK_HIGH_BODY_SHALLOW_PEN_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_high_body_shallow_pen_rejections'] += 1
    elif reason == 'WEAK_MEDIUM_PEN_MIDHIGH_CONFIRM_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_medium_pen_midhigh_confirmation_rejections'] += 1
    elif reason == 'WEAK_BEARISH_SHORT_SWEEP_CONFIRMATION':
      self._counts['bearish_short_sweep_weak_confirmation_rejections'] += 1
    elif reason == 'WEAK_BULLISH_LONG_SWEEP_CONFIRMATION':
      self._counts['bullish_long_sweep_mid_confirmation_rejections'] += 1
    elif reason == 'WEAK_DEEP_PEN_MID_CONFIRM_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_deep_pen_mid_confirmation_rejections'] += 1
    elif reason == 'WEAK_BODY_MID_STRENGTH_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_weak_body_mid_strength_rejections'] += 1
    elif reason == 'WEAK_AGE_MID_STRENGTH_NEUTRAL_LONG_REJECTION':
      self._counts['neutral_long_mid_age_mid_strength_rejections'] += 1
    elif reason == 'V3_1_WEAK_ORIGINAL_MEDIUM_WICK_HIGH_CONFIRMATION':
      self._counts['v3_1_candidate_a_rejections'] += 1
    elif reason == 'V3_2_WEAK_SHORT_MID_AGE_MID_CONFIRMATION':
      self._counts['v3_2_candidate_a_rejections'] += 1
    elif reason == 'V3_3_WEAK_REJECTION_MID_STRENGTH_MIDCLOSE':
      self._counts['v3_3_candidate_a_rejections'] += 1
    elif reason == 'V3_4_WEAK_LONG_MIDHIGH_BODY_MIDCLOSE':
      self._counts['v3_4_candidate_a_rejections'] += 1
    elif reason == 'V3_5_WEAK_SHORT_BASE_YOUNG_ZONE':
      self._counts['v3_5_candidate_a_rejections'] += 1
    self._emit_diag(df, i, active, 'NO_TRADE', reason, rr=rr, entry=entry, sl=sl, tp=tp)
    active.zone.consumed = True
    active.zone.lifecycle = 'FILTER_REJECTED'

  def _try_entry(self, df, i, active):
    self._counts['confirmed_setups'] += 1
    direction = active.direction
    proposal_a_whitelisted = False
    proposal_b_whitelisted = False
    proposal_c_whitelisted = False
    proposal_d_whitelisted = False
    reason = self._context_rejection_reason(df, i, direction)
    if reason is not None:
      if self._proposal_d_whitelist_matches(df, i, active, reason):
        proposal_d_whitelisted = True
        self._counts['proposal_d_whitelisted'] += 1
      else:
        self._reject_confirmed_setup(df, i, active, reason)
        return False
    reason = self._regime_interaction_rejection_reason(df, i, active)
    if reason is not None:
      if self._proposal_a_whitelist_matches(df, i, active, reason):
        proposal_a_whitelisted = True
        self._counts['proposal_a_whitelisted'] += 1
      elif self._proposal_b_whitelist_matches(df, i, active, reason):
        proposal_b_whitelisted = True
        self._counts['proposal_b_whitelisted'] += 1
      elif self._proposal_c_whitelist_matches(df, i, active, reason):
        proposal_c_whitelisted = True
        self._counts['proposal_c_whitelisted'] += 1
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
    reason = self._v3_1_candidate_a_rejection_reason(df, i, active, proposal_a_whitelisted, proposal_b_whitelisted, proposal_c_whitelisted, proposal_d_whitelisted)
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
    reason = self._v3_5_candidate_a_rejection_reason(df, i, active, proposal_a_whitelisted, proposal_b_whitelisted, proposal_c_whitelisted, proposal_d_whitelisted)
    if reason is not None:
      self._reject_confirmed_setup(df, i, active, reason)
      return False
    entry = float(df.iloc[i]['Close'])
    sl = self._sl(df, i, active)
    if direction == 'SHORT' and sl <= entry:
      self._reject_confirmed_setup(df, i, active, 'RR_TOO_LOW', entry=entry, sl=sl)
      return False
    if direction == 'LONG' and sl >= entry:
      self._reject_confirmed_setup(df, i, active, 'RR_TOO_LOW', entry=entry, sl=sl)
      return False
    tp = self._tp(df, i, direction, entry, sl)
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = reward / risk if risk > 0 else 0.0
    if rr < self.minimum_rr:
      self._reject_confirmed_setup(df, i, active, 'RR_TOO_LOW', rr=rr, entry=entry, sl=sl, tp=tp)
      return False
    if self._open_trade is not None:
      self._reject_confirmed_setup(df, i, active, 'TRADE_ALREADY_OPEN', rr=rr, entry=entry, sl=sl, tp=tp)
      return False
    freq_reason = self._frequency_rejection_reason(df, i)
    if freq_reason is not None:
      self._reject_confirmed_setup(df, i, active, freq_reason, rr=rr, entry=entry, sl=sl, tp=tp)
      return False
    if self.cooldown_enabled and self._cooldown_remaining > 0:
      self._cooldown_remaining -= 1
      self._same_day_loss_streak = 0
      self._reject_confirmed_setup(df, i, active, 'TWO_LOSS_COOLDOWN', rr=rr, entry=entry, sl=sl, tp=tp)
      return False
    idx = df.index[i]
    pos = -1 if direction == 'SHORT' else 1
    df.at[idx, 'Position'] = pos
    df.at[idx, 'strategy_stop_loss'] = sl
    df.at[idx, 'strategy_target'] = tp
    df.at[idx, 'rr_setup_id'] = active.setup_id
    df.at[idx, 'rr_zone_id'] = active.zone.zone_id
    df.at[idx, 'rr_state'] = '%s_ENTRY' % direction
    df.at[idx, 'rr_interaction'] = active.interaction_type
    df.at[idx, 'rr_zone_low'] = active.zone.zone_low
    df.at[idx, 'rr_zone_high'] = active.zone.zone_high
    df.at[idx, 'rr_direction'] = direction
    if proposal_a_whitelisted:
      df.at[idx, 'expansion_source'] = 'PROPOSAL_A'
    elif proposal_b_whitelisted:
      df.at[idx, 'expansion_source'] = 'PROPOSAL_B'
    elif proposal_c_whitelisted:
      df.at[idx, 'expansion_source'] = 'PROPOSAL_C'
    elif proposal_d_whitelisted:
      df.at[idx, 'expansion_source'] = 'PROPOSAL_D'
    rej_row = df.iloc[active.rejection_index]
    rq_body, rq_wick, rq_close, rq_pen = self._rejection_quality_metrics(rej_row, active.zone)
    cq = self._confirmation_quality_tuple(df, i, active)[0]
    zone_age = i - int(active.zone.available_index)
    df.at[idx, 'signal_reason'] = '%s rejection %s; confirmed; 15M=%s; zstr=%.3f; zage=%d; rbody=%.3f; rwick=%.3f; rclose=%.3f; pen=%.3f; cdisp=%.3f' % (active.zone.side, active.interaction_type, df.iloc[i]['htf_15m_bias'], float(active.zone.strength), int(zone_age), float(rq_body), float(rq_wick), float(rq_close), float(rq_pen), float(cq))
    if proposal_a_whitelisted:
      df.at[idx, 'signal_reason'] = '%s; expansion=PROPOSAL_A' % str(df.at[idx, 'signal_reason'])
    elif proposal_b_whitelisted:
      df.at[idx, 'signal_reason'] = '%s; expansion=PROPOSAL_B' % str(df.at[idx, 'signal_reason'])
    elif proposal_c_whitelisted:
      df.at[idx, 'signal_reason'] = '%s; expansion=PROPOSAL_C' % str(df.at[idx, 'signal_reason'])
    elif proposal_d_whitelisted:
      df.at[idx, 'signal_reason'] = '%s; expansion=PROPOSAL_D' % str(df.at[idx, 'signal_reason'])
    self._counts['executed_trades'] += 1
    if direction == 'SHORT':
      self._counts['short_entries'] += 1
    else:
      self._counts['long_entries'] += 1
    if proposal_a_whitelisted:
      self._counts['proposal_a_executed'] += 1
    elif proposal_b_whitelisted:
      self._counts['proposal_b_executed'] += 1
    elif proposal_c_whitelisted:
      self._counts['proposal_c_executed'] += 1
    elif proposal_d_whitelisted:
      self._counts['proposal_d_executed'] += 1
    self._mark_entry_count(df, i)
    ts = pd.Timestamp(df.iloc[i]['Date'])
    self._open_trade = {'direction': direction, 'entry_index': i, 'entry_day': self._day_key_from_timestamp(ts), 'entry': entry, 'sl': sl, 'tp': tp}
    active.state = '%s_ENTRY' % direction
    self._emit_diag(df, i, active, direction, None, rr=rr, entry=entry, sl=sl, tp=tp)
    active.zone.consumed = True
    active.zone.lifecycle = 'RETESTED'
    return True

  def _confirmation_passed(self, df, i, active):
    if active.rejection_index is None:
      return False
    if i <= active.rejection_index:
      return False
    if i > active.rejection_index + self.confirmation_bars:
      return False
    if active.direction == 'SHORT':
      return float(df.iloc[i]['Close']) < float(active.rejection_low)
    return float(df.iloc[i]['Close']) > float(active.rejection_high)

  def _find_candidate_zone(self, zones, df, i, required_side=None):
    close = float(df.iloc[i]['Close'])
    candidates = []
    for z in zones:
      if z.broken or z.consumed or z.lifecycle == 'EXPIRED' or (i < z.available_index):
        continue
      if required_side is not None and z.side != required_side:
        continue
      if z.side == 'RESISTANCE':
        if not self.enable_short:
          continue
        if close <= z.zone_high + self.breakout_buffer and z.zone_low - self.approach_distance <= close:
          candidates.append((abs(z.zone_low - close), -float(z.strength), z))
      else:
        if not self.enable_long:
          continue
        if close >= z.zone_low - self.breakout_buffer and close <= z.zone_high + self.approach_distance:
          candidates.append((abs(close - z.zone_high), -float(z.strength), z))
    candidates.sort(key=lambda item: (item[0], item[1]))
    for _, __, zone in candidates:
      interaction = self._interaction(df.iloc[i], zone)
      if interaction is not None:
        return (zone, interaction)
    return (None, None)

  def generate(self):
    df = self.df.copy()
    required = ['Date', 'Open', 'High', 'Low', 'Close']
    missing = [c for c in required if c not in df.columns]
    if missing:
      raise ValueError('Missing required columns: %s' % ', '.join(missing))
    df['Date'] = pd.to_datetime(df['Date'])
    for col in ['Open', 'High', 'Low', 'Close']:
      df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=required).sort_values('Date').reset_index(drop=True)
    source_minutes = self._infer_source_timeframe_minutes(df)
    self._detected_source_timeframe_minutes = source_minutes
    df['Position'] = 0
    df['strategy_stop_loss'] = pd.NA
    df['strategy_target'] = pd.NA
    df['signal_reason'] = pd.NA
    df['rejection_reason'] = pd.NA
    df['rr_setup_id'] = pd.NA
    df['rr_zone_id'] = pd.NA
    df['rr_state'] = 'WAITING'
    df['rr_interaction'] = pd.NA
    df['rr_direction'] = pd.NA
    df['rr_zone_low'] = pd.NA
    df['rr_zone_high'] = pd.NA
    df['expansion_source'] = pd.NA
    df['same_day_loss_streak'] = 0
    df['cooldown_remaining'] = 0
    df['monthly_entry_count'] = 0
    df['daily_entry_count'] = 0
    df['_rr_atr'] = self._atr(df)
    df = self._attach_15m_context(df, source_minutes)
    zones = []
    active_short = None
    active_long = None
    resistance_sequence = 0
    support_sequence = 0
    setup_sequence = 0
    for i in range(len(df)):
      ts = pd.Timestamp(df.iloc[i]['Date'])
      current_day = self._day_key_from_timestamp(ts)
      current_month = self._month_key_from_timestamp(ts)
      self._update_internal_trade(df, i)
      self._reset_day_state_if_needed(current_day)
      idx = df.index[i]
      df.at[idx, 'same_day_loss_streak'] = self._same_day_loss_streak
      df.at[idx, 'cooldown_remaining'] = self._cooldown_remaining
      df.at[idx, 'monthly_entry_count'] = self._entries_by_month.get(current_month, 0)
      df.at[idx, 'daily_entry_count'] = self._entries_by_day.get(current_day, 0)
      pivot = i - self.swing_right
      if self._is_swing_high(df, pivot):
        resistance_sequence += 1
        candidate = self._candidate_zone(df, pivot, i, resistance_sequence, 'RESISTANCE')
        if candidate is not None:
          self._merge_or_add(zones, candidate)
      if self._is_swing_low(df, pivot):
        support_sequence += 1
        candidate = self._candidate_zone(df, pivot, i, support_sequence, 'SUPPORT')
        if candidate is not None:
          self._merge_or_add(zones, candidate)
      for zone in zones:
        if zone.broken or zone.consumed:
          continue
        age = i - zone.available_index
        if age > self.max_zone_age:
          zone.lifecycle = 'EXPIRED'
          continue
        if self._zone_breakout(df, i, zone):
          zone.broken = True
          zone.lifecycle = 'BROKEN'
          if active_short is not None and active_short.zone.zone_id == zone.zone_id:
            active_short.state = 'ZONE_BROKEN'
            self._record_rejection('BREAKOUT')
            self._emit_diag(df, i, active_short, 'NO_TRADE', 'BREAKOUT')
            active_short = None
          if active_long is not None and active_long.zone.zone_id == zone.zone_id:
            active_long.state = 'ZONE_BROKEN'
            self._record_rejection('BREAKOUT')
            self._emit_diag(df, i, active_long, 'NO_TRADE', 'BREAKOUT')
            active_long = None
      confirmed = []
      if active_short is not None:
        a = active_short
        if a.zone.broken or a.zone.consumed:
          active_short = None
        elif a.expires_at is not None and i > a.expires_at:
          a.state = 'SETUP_EXPIRED'
          self._record_rejection('ZONE_EXPIRED')
          self._emit_diag(df, i, a, 'NO_TRADE', 'ZONE_EXPIRED')
          active_short = None
        elif a.state == 'REJECTION_DETECTED':
          if self._confirmation_passed(df, i, a):
            a.state = 'ENTRY_CONFIRMATION'
            confirmed.append(a)
          elif i >= a.rejection_index + self.confirmation_bars:
            a.state = 'REJECTION_FAILED'
            self._record_rejection('NO_ENTRY_CONFIRMATION')
            self._emit_diag(df, i, a, 'NO_TRADE', 'NO_ENTRY_CONFIRMATION')
            active_short = None
      if active_long is not None:
        a = active_long
        if a.zone.broken or a.zone.consumed:
          active_long = None
        elif a.expires_at is not None and i > a.expires_at:
          a.state = 'SETUP_EXPIRED'
          self._record_rejection('ZONE_EXPIRED')
          self._emit_diag(df, i, a, 'NO_TRADE', 'ZONE_EXPIRED')
          active_long = None
        elif a.state == 'REJECTION_DETECTED':
          if self._confirmation_passed(df, i, a):
            a.state = 'ENTRY_CONFIRMATION'
            confirmed.append(a)
          elif i >= a.rejection_index + self.confirmation_bars:
            a.state = 'REJECTION_FAILED'
            self._record_rejection('NO_ENTRY_CONFIRMATION')
            self._emit_diag(df, i, a, 'NO_TRADE', 'NO_ENTRY_CONFIRMATION')
            active_long = None
      if confirmed:
        confirmed.sort(key=lambda a: self._confirmation_quality_tuple(df, i, a), reverse=True)
        for a in confirmed:
          self._try_entry(df, i, a)
          if a.direction == 'SHORT':
            active_short = None
          else:
            active_long = None
      if self._open_trade is None and (not confirmed):
        if active_short is None and self.enable_short:
          zone, interaction = self._find_candidate_zone(zones, df, i, 'RESISTANCE')
          if zone is not None:
            self._counts['zone_interactions'] += 1
            zone.last_interaction_index = i
            zone.lifecycle = 'ACTIVE' if zone.reactions <= 1 else 'RETESTED'
            setup_sequence += 1
            setup_id = 'SD-%04d%02d%02d-%04d' % (ts.year, ts.month, ts.day, setup_sequence)
            active_short = ActiveSetup(setup_id=setup_id, zone=zone, direction='SHORT', state='ZONE_REACHED', interaction_type=interaction, expires_at=i + self.setup_expiry_bars)
            if interaction in ('REJECTION', 'SWEEP') and self._rejection(df.iloc[i], zone):
              active_short.state = 'REJECTION_DETECTED'
              active_short.rejection_index = i
              active_short.rejection_high = float(df.iloc[i]['High'])
              active_short.rejection_low = float(df.iloc[i]['Low'])
              if interaction == 'SWEEP':
                active_short.sweep_extreme = active_short.rejection_high
              self._counts['rejection_setups'] += 1
        if active_long is None and self.enable_long:
          zone, interaction = self._find_candidate_zone(zones, df, i, 'SUPPORT')
          if zone is not None:
            self._counts['zone_interactions'] += 1
            zone.last_interaction_index = i
            zone.lifecycle = 'ACTIVE' if zone.reactions <= 1 else 'RETESTED'
            setup_sequence += 1
            setup_id = 'SD-%04d%02d%02d-%04d' % (ts.year, ts.month, ts.day, setup_sequence)
            active_long = ActiveSetup(setup_id=setup_id, zone=zone, direction='LONG', state='ZONE_REACHED', interaction_type=interaction, expires_at=i + self.setup_expiry_bars)
            if interaction in ('REJECTION', 'SWEEP') and self._rejection(df.iloc[i], zone):
              active_long.state = 'REJECTION_DETECTED'
              active_long.rejection_index = i
              active_long.rejection_high = float(df.iloc[i]['High'])
              active_long.rejection_low = float(df.iloc[i]['Low'])
              if interaction == 'SWEEP':
                active_long.sweep_extreme = active_long.rejection_low
              self._counts['rejection_setups'] += 1
      if active_short is not None and active_short.state == 'ZONE_REACHED':
        interaction = self._interaction(df.iloc[i], active_short.zone)
        if interaction in ('REJECTION', 'SWEEP') and self._rejection(df.iloc[i], active_short.zone):
          active_short.interaction_type = interaction
          active_short.state = 'REJECTION_DETECTED'
          active_short.rejection_index = i
          active_short.rejection_high = float(df.iloc[i]['High'])
          active_short.rejection_low = float(df.iloc[i]['Low'])
          if interaction == 'SWEEP':
            active_short.sweep_extreme = active_short.rejection_high
          self._counts['rejection_setups'] += 1
      if active_long is not None and active_long.state == 'ZONE_REACHED':
        interaction = self._interaction(df.iloc[i], active_long.zone)
        if interaction in ('REJECTION', 'SWEEP') and self._rejection(df.iloc[i], active_long.zone):
          active_long.interaction_type = interaction
          active_long.state = 'REJECTION_DETECTED'
          active_long.rejection_index = i
          active_long.rejection_high = float(df.iloc[i]['High'])
          active_long.rejection_low = float(df.iloc[i]['Low'])
          if interaction == 'SWEEP':
            active_long.sweep_extreme = active_long.rejection_low
          self._counts['rejection_setups'] += 1
    diagnostics = {'strategy': 'XAUUSD 5M Resistance Rejection V3.5 CANDIDATE A', 'strategy_version': 'V3.5-CANDIDATE-A-RESEARCH', 'base_version': 'V3.4-CANDIDATE-A-RESEARCH-FROZEN', 'v1_3_included': False, 'v1_4_cooldown_included': False, 'direction_mode': 'LONG_AND_SHORT_INDEPENDENT_PENDING', 'total_zones': self._counts['total_zones'], 'resistance_zones': self._counts['resistance_zones'], 'support_zones': self._counts['support_zones'], 'zone_interactions': self._counts['zone_interactions'], 'rejection_setups': self._counts['rejection_setups'], 'confirmed_setups': self._counts['confirmed_setups'], 'executed_trades': self._counts['executed_trades'], 'short_entries': self._counts['short_entries'], 'long_entries': self._counts['long_entries'], 'rejected_setups': self._counts['rejected_setups'], 'htf_bullish_short_rejections': self._counts['htf_bullish_short_rejections'], 'htf_bearish_long_rejections': self._counts['htf_bearish_long_rejections'], 'regime_interaction_rejections': self._counts['regime_interaction_rejections'], 'neutral_short_penetration_rejections': self._counts['neutral_short_penetration_rejections'], 'neutral_long_weak_body_rejections': self._counts['neutral_long_weak_body_rejections'], 'neutral_long_overextended_rejections': self._counts['neutral_long_overextended_rejections'], 'neutral_short_weak_confirmation_rejections': self._counts['neutral_short_weak_confirmation_rejections'], 'neutral_short_ambiguous_wick_rejections': self._counts['neutral_short_ambiguous_wick_rejections'], 'neutral_long_moderate_strength_close_rejections': self._counts['neutral_long_moderate_strength_close_rejections'], 'neutral_long_age_confirmation_rejections': self._counts['neutral_long_age_confirmation_rejections'], 'neutral_long_ambiguous_moderate_rejections': self._counts['neutral_long_ambiguous_moderate_rejections'], 'neutral_long_low_strength_wick_rejections': self._counts['neutral_long_low_strength_wick_rejections'], 'neutral_long_shallow_wick_penetration_rejections': self._counts['neutral_long_shallow_wick_penetration_rejections'], 'neutral_short_high_body_rejections': self._counts['neutral_short_high_body_rejections'], 'neutral_long_midclose_penetration_rejections': self._counts['neutral_long_midclose_penetration_rejections'], 'neutral_long_stale_weak_confirmation_rejections': self._counts['neutral_long_stale_weak_confirmation_rejections'], 'neutral_long_medium_pen_weak_confirmation_rejections': self._counts['neutral_long_medium_pen_weak_confirmation_rejections'], 'neutral_short_weak_body_midclose_rejections': self._counts['neutral_short_weak_body_midclose_rejections'], 'neutral_long_high_body_shallow_pen_rejections': self._counts['neutral_long_high_body_shallow_pen_rejections'], 'neutral_long_medium_pen_midhigh_confirmation_rejections': self._counts['neutral_long_medium_pen_midhigh_confirmation_rejections'], 'bearish_short_sweep_weak_confirmation_rejections': self._counts['bearish_short_sweep_weak_confirmation_rejections'], 'bullish_long_sweep_mid_confirmation_rejections': self._counts['bullish_long_sweep_mid_confirmation_rejections'], 'neutral_long_deep_pen_mid_confirmation_rejections': self._counts['neutral_long_deep_pen_mid_confirmation_rejections'], 'neutral_long_weak_body_mid_strength_rejections': self._counts['neutral_long_weak_body_mid_strength_rejections'], 'neutral_long_mid_age_mid_strength_rejections': self._counts['neutral_long_mid_age_mid_strength_rejections'], 'v3_1_candidate_a_rejections': self._counts['v3_1_candidate_a_rejections'], 'v3_1_candidate_a': {'enabled': self.v3_1_candidate_a_filter, 'status': 'RESEARCH_ONLY_NOT_PROMOTED', 'applies_to': 'ORIGINAL_V1.22_SURVIVORS_ONLY; PROPOSALS_A_TO_D_UNCHANGED', 'minimum_rejection_wick_inclusive': self.v3_1_candidate_a_min_rejection_wick, 'maximum_rejection_wick_exclusive': self.v3_1_candidate_a_max_rejection_wick, 'minimum_confirmation_displacement_inclusive': self.v3_1_candidate_a_min_confirmation_displacement, 'maximum_confirmation_displacement_exclusive': self.v3_1_candidate_a_max_confirmation_displacement, 'rejection_reason': 'V3_1_WEAK_ORIGINAL_MEDIUM_WICK_HIGH_CONFIRMATION', 'disable_to_reproduce_v2_8': True}, 'v3_2_candidate_a_rejections': self._counts['v3_2_candidate_a_rejections'], 'v3_2_candidate_a': {'enabled': self.v3_2_candidate_a_filter, 'status': 'RESEARCH_ONLY_NOT_PROMOTED', 'applies_to': 'ALL_SHORT_ENTRIES_AFTER_COMPLETE_V3.1_LOGIC', 'minimum_zone_age_inclusive': self.v3_2_candidate_a_min_zone_age, 'maximum_zone_age_exclusive': self.v3_2_candidate_a_max_zone_age, 'minimum_confirmation_displacement_inclusive': self.v3_2_candidate_a_min_confirmation_displacement, 'maximum_confirmation_displacement_exclusive': self.v3_2_candidate_a_max_confirmation_displacement, 'rejection_reason': 'V3_2_WEAK_SHORT_MID_AGE_MID_CONFIRMATION', 'disable_to_reproduce_v3_1': True}, 'v3_3_candidate_a_rejections': self._counts['v3_3_candidate_a_rejections'], 'v3_3_candidate_a': {'enabled': self.v3_3_candidate_a_filter, 'status': 'RESEARCH_ONLY_NOT_PROMOTED', 'applies_to': 'REJECTION_INTERACTIONS_AFTER_COMPLETE_V3.2_LOGIC', 'minimum_zone_strength_inclusive': self.v3_3_candidate_a_min_zone_strength, 'maximum_zone_strength_exclusive': self.v3_3_candidate_a_max_zone_strength, 'minimum_rejection_close_inclusive': self.v3_3_candidate_a_min_rejection_close, 'maximum_rejection_close_exclusive': self.v3_3_candidate_a_max_rejection_close, 'rejection_reason': 'V3_3_WEAK_REJECTION_MID_STRENGTH_MIDCLOSE', 'disable_to_reproduce_v3_2': True}, 'v3_4_candidate_a_rejections': self._counts['v3_4_candidate_a_rejections'], 'v3_4_candidate_a': {'enabled': self.v3_4_candidate_a_filter, 'status': 'RESEARCH_ONLY_NOT_PROMOTED', 'applies_to': 'LONG_ENTRIES_AFTER_COMPLETE_V3.3_LOGIC', 'start_year_zero_means_global': self.v3_4_candidate_a_start_year, 'minimum_rejection_body_inclusive': self.v3_4_candidate_a_min_rejection_body, 'maximum_rejection_body_exclusive': self.v3_4_candidate_a_max_rejection_body, 'minimum_rejection_close_inclusive': self.v3_4_candidate_a_min_rejection_close, 'maximum_rejection_close_exclusive': self.v3_4_candidate_a_max_rejection_close, 'rejection_reason': 'V3_4_WEAK_LONG_MIDHIGH_BODY_MIDCLOSE', 'disable_to_reproduce_v3_3': True}, 'v3_5_candidate_a_rejections': self._counts['v3_5_candidate_a_rejections'], 'v3_5_candidate_a': {'enabled': self.v3_5_candidate_a_filter, 'status': 'RESEARCH_ONLY_NOT_PROMOTED', 'applies_to': 'SHORT_BASE_NON_EXPANSION_AFTER_COMPLETE_V3.4_LOGIC', 'interaction_scope': 'REJECTION_AND_SWEEP', 'minimum_zone_age_inclusive': self.v3_5_candidate_a_min_zone_age, 'maximum_zone_age_exclusive': self.v3_5_candidate_a_max_zone_age, 'proposal_a_d_whitelists_excluded': True, 'rejection_reason': 'V3_5_WEAK_SHORT_BASE_YOUNG_ZONE', 'disable_to_reproduce_v3_4': True}, 'internal_trade_wins': self._counts['internal_trade_wins'], 'internal_trade_losses': self._counts['internal_trade_losses'], 'proposal_a': {'enabled': self.proposal_a_expansion_enabled, 'applies_to': 'SHORT + 15M_BEARISH + REJECTION_ONLY', 'minimum_rejection_body_ratio_inclusive': self.proposal_a_min_body_ratio, 'maximum_rejection_body_ratio_exclusive': self.proposal_a_max_body_ratio, 'bypassed_rejection_reason': 'BEARISH_SHORT_REQUIRES_SWEEP', 'whitelisted_setups': self._counts['proposal_a_whitelisted'], 'executed_entries': self._counts['proposal_a_executed'], 'note': 'All other V1.22 filters and execution guards remain active.'}, 'proposal_b': {'enabled': self.proposal_b_expansion_enabled, 'applies_to': 'SHORT + 15M_BEARISH + REJECTION_ONLY', 'minimum_zone_age_inclusive': self.proposal_b_min_zone_age, 'maximum_zone_age_exclusive': self.proposal_b_max_zone_age, 'bypassed_rejection_reason': 'BEARISH_SHORT_REQUIRES_SWEEP', 'whitelisted_setups': self._counts['proposal_b_whitelisted'], 'executed_entries': self._counts['proposal_b_executed'], 'note': 'All other V1.22 filters and execution guards remain active.'}, 'proposal_c': {'enabled': self.proposal_c_expansion_enabled, 'applies_to': 'LONG + 15M_BULLISH + REJECTION_ONLY', 'minimum_zone_age_inclusive': self.proposal_c_min_zone_age, 'maximum_zone_age_exclusive': self.proposal_c_max_zone_age, 'bypassed_rejection_reason': 'BULLISH_LONG_REQUIRES_SWEEP', 'whitelisted_setups': self._counts['proposal_c_whitelisted'], 'executed_entries': self._counts['proposal_c_executed'], 'note': 'All other V1.22 filters and execution guards remain active.'}, 'proposal_d': {'enabled': self.proposal_d_expansion_enabled, 'applies_to': 'LONG + 15M_BEARISH + REJECTION_ONLY', 'minimum_confirmation_displacement_inclusive': self.proposal_d_min_confirmation_displacement, 'maximum_confirmation_displacement_exclusive': self.proposal_d_max_confirmation_displacement, 'bypassed_rejection_reason': '15M_BEARISH_CONTEXT', 'whitelisted_setups': self._counts['proposal_d_whitelisted'], 'executed_entries': self._counts['proposal_d_executed'], 'note': 'All V2.6 rules and execution guards remain active.'}, 'rejection_reasons': dict(self._rejection_reasons), 'frequency_guard': {'max_entries_per_month': self.max_entries_per_month, 'max_entries_per_day': self.max_entries_per_day, 'min_bars_between_entries': self.min_bars_between_entries, 'note': 'V2.8 preserves frozen V2.6 and adds Proposal D. Frequency remains uncapped by default (0).'}, 'quality_filter': {'enabled': self.regime_interaction_filter, 'neutral': 'REJECTION_ONLY', 'bullish_long': 'SWEEP_ONLY', 'bearish_short': 'SWEEP_ONLY', 'opposite_trend': 'BLOCKED_BY_V1.2_HTF_CONTEXT'}, 'v1_7_penetration_filter': {'enabled': self.neutral_short_penetration_filter, 'applies_to': 'SHORT + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_penetration': self.neutral_short_min_penetration, 'rejection_reason': 'INSUFFICIENT_RESISTANCE_PENETRATION'}, 'v1_8_neutral_long_body_filter': {'enabled': self.neutral_long_body_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'weak_body_min_inclusive': self.neutral_long_weak_body_min, 'weak_body_max_exclusive': self.neutral_long_weak_body_max, 'rejection_reason': 'WEAK_NEUTRAL_LONG_REJECTION_BODY'}, 'v1_9_neutral_long_overextended_filter': {'enabled': self.neutral_long_overextended_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_lower_wick_ratio': self.neutral_long_min_overextended_wick, 'minimum_confirmation_displacement': self.neutral_long_min_overextended_confirmation, 'rejection_reason': 'OVEREXTENDED_NEUTRAL_LONG_CONFIRMATION'}, 'v1_10_neutral_short_weak_confirmation_filter': {'enabled': self.neutral_short_weak_confirmation_filter, 'applies_to': 'SHORT + 15M_NEUTRAL + REJECTION_ONLY', 'maximum_zone_strength_exclusive': self.neutral_short_max_weak_zone_strength, 'maximum_confirmation_displacement_exclusive': self.neutral_short_max_weak_confirmation_displacement, 'rejection_reason': 'WEAK_NEUTRAL_SHORT_CONFIRMATION'}, 'v1_11_neutral_short_ambiguous_wick_filter': {'enabled': self.neutral_short_ambiguous_wick_filter, 'applies_to': 'SHORT + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_upper_wick_ratio_inclusive': self.neutral_short_ambiguous_wick_min, 'maximum_upper_wick_ratio_exclusive': self.neutral_short_ambiguous_wick_max, 'rejection_reason': 'AMBIGUOUS_NEUTRAL_SHORT_REJECTION_WICK'}, 'v1_12_neutral_long_moderate_strength_close_filter': {'enabled': self.neutral_long_moderate_strength_close_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_zone_strength_inclusive': self.neutral_long_moderate_strength_min, 'maximum_zone_strength_exclusive': self.neutral_long_moderate_strength_max, 'maximum_rejection_close_position_exclusive': self.neutral_long_max_close_position, 'rejection_reason': 'WEAK_MODERATE_STRENGTH_NEUTRAL_LONG_REJECTION'}, 'v1_14_neutral_long_age_confirmation_filter': {'enabled': self.neutral_long_age_confirmation_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_zone_age_inclusive': self.neutral_long_age_confirmation_min_age, 'maximum_zone_age_exclusive': self.neutral_long_age_confirmation_max_age, 'minimum_confirmation_displacement_inclusive': self.neutral_long_age_confirmation_min_displacement, 'maximum_confirmation_displacement_exclusive': self.neutral_long_age_confirmation_max_displacement, 'rejection_reason': 'WEAK_YOUNG_NEUTRAL_LONG_CONFIRMATION', 'built_from': 'V1.12-LS', 'v1_13_included': False}, 'v1_15_neutral_long_ambiguous_moderate_filter': {'enabled': self.neutral_long_ambiguous_moderate_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_zone_strength_inclusive': self.neutral_long_ambiguous_moderate_min_zone_strength, 'maximum_zone_strength_exclusive': self.neutral_long_ambiguous_moderate_max_zone_strength, 'minimum_lower_wick_ratio_inclusive': self.neutral_long_ambiguous_moderate_min_wick, 'maximum_lower_wick_ratio_exclusive': self.neutral_long_ambiguous_moderate_max_wick, 'rejection_reason': 'AMBIGUOUS_MODERATE_NEUTRAL_LONG_REJECTION', 'built_from': 'V1.14-LS'}, 'v1_16_neutral_long_low_strength_wick_filter': {'enabled': self.neutral_long_low_strength_wick_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_zone_strength_inclusive': self.neutral_long_low_strength_min_zone_strength, 'maximum_zone_strength_exclusive': self.neutral_long_low_strength_max_zone_strength, 'minimum_lower_wick_ratio_inclusive': self.neutral_long_low_strength_min_wick, 'maximum_lower_wick_ratio_exclusive': self.neutral_long_low_strength_max_wick, 'rejection_reason': 'WEAK_LOW_STRENGTH_NEUTRAL_LONG_REJECTION', 'built_from': 'V1.15-LS', 'final_planned_filter': False, 'superseded_by': 'V1.17-LS'}, 'v1_17_dual_refinement': {'built_from': 'V1.16-LS', 'filter_count': 2, 'filter_a_neutral_long_shallow_wick_penetration': {'enabled': self.neutral_long_shallow_wick_penetration_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_lower_wick_ratio_inclusive': self.neutral_long_shallow_wick_min, 'maximum_lower_wick_ratio_exclusive': self.neutral_long_shallow_wick_max, 'maximum_zone_penetration_exclusive': self.neutral_long_shallow_max_penetration, 'rejection_reason': 'SHALLOW_WICK_NEUTRAL_LONG_REJECTION', 'v1_16_research_sample': '38 trades; 7W/31L; WR~18.42%; total~-17R; PF~0.45'}, 'filter_b_neutral_short_high_body': {'enabled': self.neutral_short_high_body_filter, 'applies_to': 'SHORT + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_body_ratio_inclusive': self.neutral_short_high_body_min, 'maximum_body_ratio_exclusive': self.neutral_short_high_body_max, 'preserve_body_ratio_gte': self.neutral_short_high_body_max, 'rejection_reason': 'WEAK_HIGH_BODY_NEUTRAL_SHORT_REJECTION', 'v1_16_research_sample': '44 trades; 9W/35L; WR~20.45%; total~-17.09R; PF~0.51'}}, 'v1_18_dual_refinement': {'built_from': 'V1.17-LS', 'filter_count': 2, 'filter_a_neutral_long_midclose_penetration': {'enabled': self.neutral_long_midclose_penetration_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_rejection_close_position_inclusive': self.neutral_long_midclose_min_close, 'maximum_rejection_close_position_exclusive': self.neutral_long_midclose_max_close, 'minimum_zone_penetration_inclusive': self.neutral_long_midclose_min_penetration, 'maximum_zone_penetration_exclusive': self.neutral_long_midclose_max_penetration, 'rejection_reason': 'WEAK_MIDCLOSE_NEUTRAL_LONG_REJECTION', 'v1_17_research_sample': '37 trades; 4W/33L; WR~10.81%; total~-25.23R; R-PF~0.24; negative every tested year'}, 'filter_b_neutral_long_stale_weak_confirmation': {'enabled': self.neutral_long_stale_weak_confirmation_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_zone_age_inclusive': self.neutral_long_stale_min_zone_age, 'minimum_confirmation_displacement_inclusive': self.neutral_long_stale_min_confirmation_displacement, 'maximum_confirmation_displacement_exclusive': self.neutral_long_stale_max_confirmation_displacement, 'rejection_reason': 'STALE_WEAK_CONFIRMATION_NEUTRAL_LONG_REJECTION', 'v1_17_research_sample': '32 trades; 6W/26L; WR~18.75%; total~-14.15R; R-PF~0.46; negative every tested year'}, 'combined_unique_v1_17_sample': '63 trades; 10W/53L; winner:loser ~1:5.3; total~-33.38R'}, 'v1_19_dual_refinement': {'built_from': 'V1.18-LS', 'filter_count': 2, 'filter_a_neutral_long_medium_pen_weak_confirmation': {'enabled': self.neutral_long_medium_pen_weak_confirmation_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_zone_penetration_inclusive': self.neutral_long_medium_pen_min_penetration, 'maximum_zone_penetration_exclusive': self.neutral_long_medium_pen_max_penetration, 'minimum_confirmation_displacement_inclusive': self.neutral_long_medium_pen_min_confirmation_displacement, 'maximum_confirmation_displacement_exclusive': self.neutral_long_medium_pen_max_confirmation_displacement, 'rejection_reason': 'WEAK_MEDIUM_PENETRATION_NEUTRAL_LONG_CONFIRMATION', 'v1_18_research_sample': '24 trades; 4W/20L; WR~16.67%; total~-11.89R; R-PF~0.41; negative every tested year'}, 'filter_b_neutral_short_weak_body_midclose': {'enabled': self.neutral_short_weak_body_midclose_filter, 'applies_to': 'SHORT + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_body_ratio_inclusive': self.neutral_short_weak_body_midclose_min_body, 'maximum_body_ratio_exclusive': self.neutral_short_weak_body_midclose_max_body, 'minimum_rejection_close_position_inclusive': self.neutral_short_weak_body_midclose_min_close, 'maximum_rejection_close_position_exclusive': self.neutral_short_weak_body_midclose_max_close, 'rejection_reason': 'WEAK_BODY_MIDCLOSE_NEUTRAL_SHORT_REJECTION', 'v1_18_research_sample': '25 trades; 4W/21L; WR~16.00%; total~-13.02R; R-PF~0.38; negative every tested year'}, 'combined_unique_v1_18_sample': '49 trades; 8W/41L; winner:loser ~1:5.1; total~-24.90R'}, 'v1_20_dual_refinement': {'built_from': 'V1.19-LS', 'filter_count': 2, 'filter_a_neutral_long_high_body_shallow_pen': {'enabled': self.neutral_long_high_body_shallow_pen_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_body_ratio_inclusive': self.neutral_long_high_body_shallow_pen_min_body, 'maximum_body_ratio_exclusive': self.neutral_long_high_body_shallow_pen_max_body, 'minimum_zone_penetration_inclusive': self.neutral_long_high_body_shallow_pen_min_penetration, 'maximum_zone_penetration_exclusive': self.neutral_long_high_body_shallow_pen_max_penetration, 'rejection_reason': 'WEAK_HIGH_BODY_SHALLOW_PEN_NEUTRAL_LONG_REJECTION', 'v1_19_research_sample': '23 trades; 3W/20L; WR~13.04%; total~-13.98R; R-PF~0.30; negative every year present (2022-2025)'}, 'filter_b_neutral_long_medium_pen_midhigh_confirmation': {'enabled': self.neutral_long_medium_pen_midhigh_confirmation_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_zone_penetration_inclusive': self.neutral_long_medium_pen_midhigh_min_penetration, 'maximum_zone_penetration_exclusive': self.neutral_long_medium_pen_midhigh_max_penetration, 'minimum_confirmation_displacement_inclusive': self.neutral_long_medium_pen_midhigh_min_confirmation_displacement, 'maximum_confirmation_displacement_exclusive': self.neutral_long_medium_pen_midhigh_max_confirmation_displacement, 'rejection_reason': 'WEAK_MEDIUM_PEN_MIDHIGH_CONFIRM_NEUTRAL_LONG_REJECTION', 'v1_19_research_sample': '24 trades; 4W/20L; WR~16.67%; total~-11.99R; R-PF~0.40; negative every tested year'}, 'combined_unique_v1_19_sample': '47 trades; 7W/40L; winner:loser ~1:5.7; total~-25.97R'}, 'v1_21_dual_refinement': {'built_from': 'V1.20-LS', 'filter_count': 2, 'filter_a_bearish_short_sweep_weak_confirmation': {'enabled': self.bearish_short_sweep_weak_confirmation_filter, 'applies_to': 'SHORT + 15M_BEARISH + SWEEP_ONLY', 'minimum_rejection_close_position_inclusive': self.bearish_short_sweep_min_close, 'maximum_rejection_close_position_exclusive': self.bearish_short_sweep_max_close, 'minimum_confirmation_displacement_inclusive': self.bearish_short_sweep_min_confirmation_displacement, 'maximum_confirmation_displacement_exclusive': self.bearish_short_sweep_max_confirmation_displacement, 'rejection_reason': 'WEAK_BEARISH_SHORT_SWEEP_CONFIRMATION', 'v1_20_research_sample': '21 trades; 3W/18L; WR~14.29%; winner:loser=1:6.0; total~-12.02R'}, 'filter_b_bullish_long_sweep_mid_confirmation': {'enabled': self.bullish_long_sweep_mid_confirmation_filter, 'applies_to': 'LONG + 15M_BULLISH + SWEEP_ONLY', 'minimum_rejection_close_position_inclusive': self.bullish_long_sweep_min_close, 'maximum_rejection_close_position_exclusive': self.bullish_long_sweep_max_close, 'minimum_confirmation_displacement_inclusive': self.bullish_long_sweep_min_confirmation_displacement, 'maximum_confirmation_displacement_exclusive': self.bullish_long_sweep_max_confirmation_displacement, 'rejection_reason': 'WEAK_BULLISH_LONG_SWEEP_CONFIRMATION', 'v1_20_research_sample': '20 trades; 3W/17L; WR~15.00%; winner:loser~1:5.67; total~-11.06R'}, 'combined_unique_v1_20_sample': '41 trades; 6W/35L; winner:loser ~1:5.83; total~-23.08R'}, 'v1_22_triple_refinement': {'built_from': 'V1.21-LS', 'filter_count': 3, 'filter_a_neutral_long_deep_pen_mid_confirmation': {'enabled': self.neutral_long_deep_pen_mid_confirmation_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_zone_penetration_inclusive': self.neutral_long_deep_pen_mid_confirmation_min_penetration, 'maximum_zone_penetration_exclusive': self.neutral_long_deep_pen_mid_confirmation_max_penetration, 'minimum_confirmation_displacement_inclusive': self.neutral_long_deep_pen_mid_confirmation_min_displacement, 'maximum_confirmation_displacement_exclusive': self.neutral_long_deep_pen_mid_confirmation_max_displacement, 'rejection_reason': 'WEAK_DEEP_PEN_MID_CONFIRM_NEUTRAL_LONG_REJECTION', 'v1_21_research_sample': '15 trades; 2W/13L; WR~13.33%; winner:loser=1:6.5; total~-8.96R; negative every tested year'}, 'filter_b_neutral_long_weak_body_mid_strength': {'enabled': self.neutral_long_weak_body_mid_strength_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_rejection_body_ratio_inclusive': self.neutral_long_weak_body_mid_strength_min_body, 'maximum_rejection_body_ratio_exclusive': self.neutral_long_weak_body_mid_strength_max_body, 'minimum_zone_strength_inclusive': self.neutral_long_weak_body_mid_strength_min_zone_strength, 'maximum_zone_strength_exclusive': self.neutral_long_weak_body_mid_strength_max_zone_strength, 'rejection_reason': 'WEAK_BODY_MID_STRENGTH_NEUTRAL_LONG_REJECTION', 'v1_21_research_sample': '16 trades; 2W/14L; WR=12.50%; winner:loser=1:7.0; total~-10.18R'}, 'filter_c_neutral_long_mid_age_mid_strength': {'enabled': self.neutral_long_mid_age_mid_strength_filter, 'applies_to': 'LONG + 15M_NEUTRAL + REJECTION_ONLY', 'minimum_zone_age_inclusive': self.neutral_long_mid_age_mid_strength_min_age, 'maximum_zone_age_exclusive': self.neutral_long_mid_age_mid_strength_max_age, 'minimum_zone_strength_inclusive': self.neutral_long_mid_age_mid_strength_min_zone_strength, 'maximum_zone_strength_exclusive': self.neutral_long_mid_age_mid_strength_max_zone_strength, 'rejection_reason': 'WEAK_AGE_MID_STRENGTH_NEUTRAL_LONG_REJECTION', 'v1_21_research_sample': '20 trades; 3W/17L; WR=15.00%; winner:loser~1:5.67; total~-11.02R'}, 'combined_unique_v1_21_sample': '46 trades; 7W/39L; winner:loser ~1:5.57; total~-25.16R; B/C overlap=5 trades'}, 'htf_context': {'enabled': self.htf_context_enabled, 'timeframe_minutes': 15, 'source_timeframe_minutes': self._detected_source_timeframe_minutes, 'complete_15m_bars': self._htf_bar_count, 'short_block': 'BULLISH_HH_HL', 'long_block': 'BEARISH_LH_LL'}, 'setups': self._diagnostic_rows if self.debug_mode else [], 'debug_mode': self.debug_mode}
    df.attrs['strategy_diagnostics'] = diagnostics
    return df
Strategy = XAUUSD5MSupplyDemandRejectionV35CandidateA
import pandas as pd
import numpy as np
DEFAULTS = dict(left=3, right=3, atr_period=14, min_anchor_separation=6, max_anchor_separation=90, max_line_age=180, min_abs_slope_atr=0.025, touch_band_atr=0.25, reset_distance_atr=0.5, invalidate_close_atr=0.5, tick_size=0.001)

def rolling_atr(df, period):
  prior = df.Close.shift(1)
  tr = pd.concat([df.High - df.Low, (df.High - prior).abs(), (df.Low - prior).abs()], axis=1).max(axis=1)
  return tr.rolling(period, min_periods=period).mean().tolist()

def candle_features(open_, high, low, close, prev_open, prev_close, atr, tick):
  rng = max(high - low, tick)
  body = abs(close - open_)
  return {'body_to_range': body / rng, 'body_to_atr': body / max(atr, tick), 'upper_wick_to_range': (high - max(close, open_)) / rng, 'lower_wick_to_range': (min(close, open_) - low) / rng, 'close_from_low': (close - low) / rng, 'bearish_engulfing': bool(close < open_ and prev_close > prev_open and (open_ >= prev_close) and (close <= prev_open)), 'bullish_engulfing': bool(close > open_ and prev_close < prev_open and (open_ <= prev_close) and (close >= prev_open))}

def detect_trendline_events(df, params=None):
  pass
  p = {**DEFAULTS, **(params or {})}
  n = len(df)
  o, h, l, c = [df[k].to_numpy(dtype=float) for k in ('Open', 'High', 'Low', 'Close')]
  dates = df.Date.tolist()
  atr = rolling_atr(df, p['atr_period'])
  last = {'SHORT': None, 'LONG': None}
  lines = []
  events = []
  anchors = []
  for i in range(n):
    av = atr[i]
    if pd.notna(av) and av > 0 and (i > 0):
      retained = []
      for line in lines:
        if line['invalidated']:
          continue
        age = i - line['confirmed_index']
        if age > p['max_line_age']:
          continue
        side = line['direction']
        price = line['anchor2_price'] + line['slope'] * (i - line['anchor2_index'])
        band = p['touch_band_atr'] * av
        reset = p['reset_distance_atr'] * av
        if side == 'SHORT':
          away = h[i] < price - band - reset
          overlap = h[i] >= price - band and l[i] <= price + band
          broken = c[i] > price + p['invalidate_close_atr'] * av
          rejected = c[i] < price - band
        else:
          away = l[i] > price + band + reset
          overlap = l[i] <= price + band and h[i] >= price - band
          broken = c[i] < price - p['invalidate_close_atr'] * av
          rejected = c[i] > price + band
        if broken:
          line['invalidated'] = True
          line['invalidated_index'] = i
          continue
        if away:
          line['armed'] = True
        if overlap and line['armed']:
          line['touches'] += 1
          line['armed'] = False
          cf = candle_features(o[i], h[i], l[i], c[i], o[i - 1], c[i - 1], av, p['tick_size'])
          events.append(dict(event_id=f"{line['line_id']}:{i}", index=i, timestamp=str(dates[i]), direction=side, line_id=line['line_id'], anchor1_index=line['anchor1_index'], anchor2_index=line['anchor2_index'], anchor1_time=str(dates[line['anchor1_index']]), anchor2_time=str(dates[line['anchor2_index']]), anchor1_price=line['anchor1_price'], anchor2_price=line['anchor2_price'], anchor2_confirm_time=str(dates[line['confirmed_index']]), confirmed_index=line['confirmed_index'], slope_price_per_bar=line['slope'], slope_atr=line['slope_atr'], line_price=price, atr=av, touch_number=line['touches'], line_age_bars=age, distance_close_atr=(c[i] - price) / av, state='REJECTION' if rejected else 'TOUCH', **cf))
        retained.append(line)
      lines = retained
    j = i - p['right']
    if j < p['left'] or j < 0:
      continue
    for side, v, arr in [('SHORT', h[j], h), ('LONG', l[j], l)]:
      left = arr[j - p['left']:j]
      right = arr[j + 1:i + 1]
      yes = v > max(left) and v >= max(right) if side == 'SHORT' else v < min(left) and v <= min(right)
      if not yes:
        continue
      anchor = {'direction': side, 'index': j, 'time': str(dates[j]), 'price': float(v), 'confirmed_index': i, 'confirmed_time': str(dates[i])}
      anchors.append(anchor)
      a = last[side]
      last[side] = anchor
      if a is None or not pd.notna(atr[j]) or atr[j] <= 0:
        continue
      sep = j - a['index']
      if sep < p['min_anchor_separation'] or sep > p['max_anchor_separation']:
        continue
      slope = (float(v) - a['price']) / sep
      slope_atr = slope / atr[j]
      if side == 'SHORT' and slope_atr >= -p['min_abs_slope_atr']:
        continue
      if side == 'LONG' and slope_atr <= p['min_abs_slope_atr']:
        continue
      line_id = f"TL-{side}-{a['index']:07d}-{j:07d}"
      lines.append(dict(line_id=line_id, direction=side, anchor1_index=a['index'], anchor1_price=a['price'], anchor2_index=j, anchor2_price=float(v), confirmed_index=i, slope=slope, slope_atr=slope_atr, touches=2, armed=False, invalidated=False))
  return (pd.DataFrame(events), pd.DataFrame(anchors))

def htf_bias(raw):
  pass
  m5 = raw[['Date', 'Open', 'High', 'Low', 'Close']].copy()
  m5 = m5.set_index('Date')
  rule = '15min'
  oh = m5.resample(rule, closed='left', label='left').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
  count = m5.Close.resample(rule, closed='left', label='left').count()
  oh = oh[count.eq(3)].dropna(subset=['Open', 'High', 'Low', 'Close']).reset_index()
  highs = oh.High.to_numpy()
  lows = oh.Low.to_numpy()
  n = len(oh)
  values = np.zeros(n, dtype=np.int8)
  confirmed_high = []
  confirmed_low = []
  for j in range(n):
    k = j - 2
    if k >= 2:
      v = highs[k]
      if v > max(highs[k - 2:k]) and v >= max(highs[k + 1:j + 1]):
        confirmed_high.append(v)
      v = lows[k]
      if v < min(lows[k - 2:k]) and v <= min(lows[k + 1:j + 1]):
        confirmed_low.append(v)
    if len(confirmed_high) >= 2 and len(confirmed_low) >= 2:
      a, b = confirmed_high[-2:]
      c, d = confirmed_low[-2:]
      values[j] = 1 if b > a and d > c else -1 if b < a and d < c else 0
  available = (oh.Date + pd.Timedelta(minutes=15)).to_numpy(dtype='datetime64[ns]')
  dec = (raw.Date + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
  idx = np.searchsorted(available, dec, side='right') - 1
  res = np.zeros(len(raw), dtype=np.int8)
  valid = idx >= 0
  res[valid] = values[idx[valid]]
  return res

def generate_candidates(raw, events, bias, predeclared=None):
  pass
  n = len(raw)
  dt = pd.Index(raw.Date)
  o = raw.Open.to_numpy()
  h = raw.High.to_numpy()
  l = raw.Low.to_numpy()
  c = raw.Close.to_numpy()
  minutes = raw.Date.diff().dt.total_seconds().fillna(0).div(60).to_numpy()
  ev = events.loc[events.state.eq('REJECTION')].copy()
  times = pd.to_datetime(ev.timestamp)
  ix = dt.get_indexer(times)
  ev = ev.loc[ix >= 0].copy()
  ix = ix[ix >= 0]
  proposed = []
  statistics = {'events_total': len(events), 'rejection_events': len(ev), 'eligible_event_without_signal': 0, 'context_veto': 0, 'invalid_stop': 0, 'invalid_next_open': 0, 'same_bar_conflicts': 0, 'not_confirmed': 0, 'confirmed_proposals': 0}
  for k, (entry, i) in enumerate(zip(ev.itertuples(index=False), ix)):
    side = entry.direction
    sign = -1 if side == 'SHORT' else 1
    if i < 30 or i >= n - 1:
      continue
    if entry.touch_number < 3:
      continue
    if entry.confirmed_index >= entry.index:
      raise ValueError('Future-pivot leakage')
    found = False
    for j in range(int(i) + 1, min(int(i) + 5, n)):
      if minutes[j] != 5:
        break
      if sign == -1 and c[j] < l[i] or (sign == 1 and c[j] > h[i]):
        found = True
        statistics['confirmed_proposals'] += 1
        if sign == -1 and bias[j] == 1 or (sign == 1 and bias[j] == -1):
          statistics['context_veto'] += 1
          break
        stop = float(h[i] + 0.5) if sign == -1 else float(l[i] - 0.5)
        risk = abs(float(c[j]) - stop)
        target = float(c[j] - 2 * risk) if sign == -1 else float(c[j] + 2 * risk)
        if risk <= 0 or (sign == -1 and stop <= c[j]) or (sign == 1 and stop >= c[j]):
          statistics['invalid_stop'] += 1
          break
        proposed.append({'signal_index': int(j), 'signal_time': str(raw.Date.iloc[j]), 'entry_time': None, 'side': side, 'signal': sign, 'sl': stop, 'tp': target, 'indicative_entry': float(c[j]), 'expected_next_open': None, 'line_id': entry.line_id, 'event_id': entry.event_id, 'rejection_index': int(i), 'rejection_time': str(raw.Date.iloc[i]), 'anchor_confirm_time': entry.anchor2_confirm_time, 'touch_number': int(entry.touch_number), 'body_to_range': float(entry.body_to_range), 'body_to_atr': float(entry.body_to_atr), 'atr': float(entry.atr), 'slope_atr': float(entry.slope_atr), 'htf_bias_at_confirmation': int(bias[j]), 'event_bearish_engulfing': str(entry.bearish_engulfing), 'event_bullish_engulfing': str(entry.bullish_engulfing), 'confirmation_bars': int(j - i)})
        break
    if not found:
      statistics['not_confirmed'] += 1
  props = pd.DataFrame(proposed)
  if props.empty:
    return (props, statistics)
  props = props.sort_values(['signal_index', 'rejection_index', 'line_id']).drop_duplicates('signal_index', keep='first').reset_index(drop=True)
  statistics['unique_signal_bars'] = len(props)
  return (props, statistics)

def generate_confirmed_zone_retests(m5, events, bias, atr_period=14):
  pass
  n = len(m5)
  o, h, l, c = [m5[x].to_numpy(dtype=float) for x in ('Open', 'High', 'Low', 'Close')]
  dates = m5.Date.to_numpy()
  dt = pd.Index(m5.Date)
  gap = m5.Date.diff().dt.total_seconds().div(60).fillna(0).to_numpy()
  a = np.asarray(rolling_atr(m5, atr_period), dtype=float)
  proposed = []
  if events.empty:
    return pd.DataFrame()
  for r in events.itertuples(index=False):
    if int(r.touch_number) < 3:
      continue
    i = int(r.index)
    if i < 20 or i >= n - 1 or int(r.confirmed_index) >= i:
      continue
    side = 1 if str(r.direction) == 'SHORT' else -1
    for j in range(i + 1, min(i + 5, n)):
      if gap[j] != 5:
        break
      av = a[j]
      if not np.isfinite(av) or av <= 0:
        continue
      line = float(r.line_price) + float(r.slope_price_per_bar) * (j - i)
      if side == 1:
        crossed = c[j] > line + 0.5 * av
        already_outside = c[j - 1] > line + 0.5 * av
      else:
        crossed = c[j] < line - 0.5 * av
        already_outside = c[j - 1] < line - 0.5 * av
      if not crossed:
        continue
      if already_outside:
        break
      span = max(float(h[j] - l[j]), 0.001)
      body_atr = abs(float(c[j] - o[j])) / av
      proposed.append({'break_index': j, 'reference_index': i, 'line_id': str(r.line_id), 'event_id': str(r.event_id), 'slope': float(r.slope_price_per_bar), 'line_price': float(r.line_price), 'side': side, 'body_atr': body_atr, 'm15_at_break': int(bias[j]), 'source_touch': int(r.touch_number)})
      break
  if not proposed:
    return pd.DataFrame()
  breaks = pd.DataFrame(proposed)
  breaks = breaks.sort_values(['break_index', 'body_atr', 'event_id'], ascending=[True, False, True], kind='stable').drop_duplicates('break_index').reset_index(drop=True)
  ret = []
  for b in breaks.itertuples(index=False):
    j = int(b.break_index)
    i = int(b.reference_index)
    side = int(b.side)
    for k in range(j + 1, min(j + 13, n)):
      if gap[k] != 5:
        break
      av = a[k]
      if not np.isfinite(av) or av <= 0:
        continue
      line = float(b.line_price) + float(b.slope) * (k - i)
      band = 0.35 * av
      span = max(float(h[k] - l[k]), 0.001)
      if side == 1:
        contact = l[k] <= line + band and h[k] >= line - band
        good = c[k] > line + band * 0.25 and c[k] > o[k] and ((c[k] - l[k]) / span >= 0.6)
        stop = float(l[k] - 0.5)
      else:
        contact = h[k] >= line - band and l[k] <= line + band
        good = c[k] < line - band * 0.25 and c[k] < o[k] and ((h[k] - c[k]) / span >= 0.6)
        stop = float(h[k] + 0.5)
      if contact and good and (side * (c[k] - stop) > 0):
        body = abs(float(c[k] - o[k])) / av
        risk = abs(float(c[k] - stop))
        ret.append({'signal_index': k, 'signal_time': str(m5.Date.iloc[k]), 'signal': side, 'side': 'LONG' if side == 1 else 'SHORT', 'sl': stop, 'tp': float(c[k] + 2 * side * risk), 'body_atr_retest': body, 'aligned_break': bool(int(b.m15_at_break) == side), 'event_id': 'RETEST:' + str(b.event_id) + ':' + str(j) + ':' + str(k), 'line_id': b.line_id, 'rejection_index': int(b.reference_index)})
        break
  if not ret:
    return pd.DataFrame()
  tab = pd.DataFrame(ret).sort_values(['signal_index', 'body_atr_retest', 'event_id'], ascending=[True, False, True], kind='stable')
  return tab.drop_duplicates('signal_index').reset_index(drop=True)

class XAUUSD_M5_Trendline_V424_LongRetestOnly_EXPERIMENT:
  pass
  LIVE_HISTORY_BARS = 2000

  def __init__(self, df, **kwargs):
    self.df = df.copy()
    self.min_body_ratio = float(kwargs.get('min_body_ratio', 0.0))
    self.min_body_atr = float(kwargs.get('min_body_atr', 0.0))
    self.max_confirmation_bars = int(kwargs.get('max_confirmation_bars', 4))
    self.max_touch_number = int(kwargs.get('max_touch_number', 0))
    self.direction = str(kwargs.get('direction', 'BOTH')).upper()
    self.require_engulfing = bool(kwargs.get('require_engulfing', True))
    self.add_strong_non_engulf = bool(kwargs.get('add_strong_non_engulf', True))
    self.expansion_min_body_range = float(kwargs.get('expansion_min_body_range', 0.65))
    self.expansion_min_body_atr = float(kwargs.get('expansion_min_body_atr', 0.8))
    self.min_atr_regime = float(kwargs.get('min_atr_regime', 0.65))
    self.skip_prev_day_aligned_engulf = bool(kwargs.get('skip_prev_day_aligned_engulf', True))
    self.add_wick_counter_htf = bool(kwargs.get('add_wick_counter_htf', True))
    self.enable_v423_retest = bool(kwargs.get('enable_v423_retest', True))
    self.v423_min_retest_body_atr = float(kwargs.get('v423_min_retest_body_atr', 0.6))
    self.v423_require_m15_break_alignment = bool(kwargs.get('v423_require_m15_break_alignment', True))
    self.v424_retest_long_only = bool(kwargs.get('v424_retest_long_only', True))
    self.detector_params = kwargs.get('detector_params', {})
    self._diagnostics = {}

  def generate(self):
    df = self.df.copy().reset_index(drop=True)
    required = {'Date', 'Open', 'High', 'Low', 'Close'}
    if not required.issubset(df.columns):
      raise ValueError('Missing columns: ' + str(sorted(required - set(df.columns))))
    df['Date'] = pd.to_datetime(df.Date)
    if df.Date.duplicated().any() or not df.Date.is_monotonic_increasing:
      raise ValueError('Requires strictly increasing unique M5 timestamps')
    diffs = df.Date.diff().dt.total_seconds().div(60)
    start = int(np.flatnonzero(diffs.eq(5).to_numpy())[0]) - 1 if bool(diffs.eq(5).any()) else 0
    if start < 0:
      start = 0
    m5 = df.iloc[start:].copy().reset_index(drop=True)
    if len(m5) < 40:
      raise ValueError('At least 40 M5 candles required')
    if float(m5.Date.diff().dt.total_seconds().div(60).dropna().median()) != 5:
      raise ValueError('Source is not predominantly M5')
    events, pivots = detect_trendline_events(m5, self.detector_params)
    if not events.empty:
      bias = htf_bias(m5)
      candidate, stats = generate_candidates(m5, events, bias)
    else:
      candidate = pd.DataFrame()
      stats = {}
    if not candidate.empty:
      if self.direction in ('SHORT', 'LONG'):
        candidate = candidate[candidate.side.eq(self.direction)]
      if self.min_body_ratio > 0:
        candidate = candidate[candidate.body_to_range >= self.min_body_ratio]
      if self.min_body_atr > 0:
        candidate = candidate[candidate.body_to_atr >= self.min_body_atr]
      if self.max_confirmation_bars < 4:
        candidate = candidate[candidate.confirmation_bars <= self.max_confirmation_bars]
      if self.max_touch_number > 0:
        candidate = candidate[candidate.touch_number <= self.max_touch_number]
      if self.require_engulfing:
        engulf = candidate.side.eq('SHORT') & candidate.event_bearish_engulfing.astype(str).str.lower().eq('true') | candidate.side.eq('LONG') & candidate.event_bullish_engulfing.astype(str).str.lower().eq('true')
        if self.add_strong_non_engulf:
          extra = ~engulf & (candidate.body_to_range >= self.expansion_min_body_range) & (candidate.body_to_atr >= self.expansion_min_body_atr) & (candidate.htf_bias_at_confirmation == candidate.signal)
          wick_extra = pd.Series(False, index=candidate.index)
          if self.add_wick_counter_htf:
            ri = candidate.rejection_index.to_numpy(dtype=int)
            op = m5.Open.to_numpy(dtype=float)[ri]
            hi = m5.High.to_numpy(dtype=float)[ri]
            lo = m5.Low.to_numpy(dtype=float)[ri]
            cl = m5.Close.to_numpy(dtype=float)[ri]
            span = np.maximum(hi - lo, 0.001)
            upp = (hi - np.maximum(op, cl)) / span
            low = (np.minimum(op, cl) - lo) / span
            close_pos = (cl - lo) / span
            side = candidate.signal.to_numpy(dtype=int)
            rejecting_wick = np.where(side < 0, upp, low)
            close_quality = np.where(side < 0, 1.0 - close_pos, close_pos)
            counter_htf = candidate.htf_bias_at_confirmation.to_numpy(dtype=int) != side
            wick_extra = pd.Series(~engulf.to_numpy(dtype=bool) & ~extra.to_numpy(dtype=bool) & counter_htf & (rejecting_wick >= 0.45) & (close_quality >= 0.75) & (candidate.body_to_atr.to_numpy(dtype=float) >= 0.4), index=candidate.index)
          candidate = candidate[engulf | extra | wick_extra]
        else:
          candidate = candidate[engulf]
    if not candidate.empty and self.skip_prev_day_aligned_engulf:
      daily = m5.set_index('Date')[['Open', 'Close']].resample('1D', closed='left', label='left').agg({'Open': 'first', 'Close': 'last'})
      daily_count = m5.set_index('Date')['Close'].resample('1D', closed='left', label='left').count()
      daily.loc[daily_count.lt(30), ['Open', 'Close']] = float('nan')
      prev_dates = pd.to_datetime(candidate.signal_time).dt.normalize() - pd.Timedelta(days=1)
      d1 = daily.reindex(pd.DatetimeIndex(prev_dates))
      prev_direction = np.sign((d1.Close - d1.Open).to_numpy(dtype=float))
      engulf = candidate.side.eq('SHORT') & candidate.event_bearish_engulfing.astype(str).str.lower().eq('true') | candidate.side.eq('LONG') & candidate.event_bullish_engulfing.astype(str).str.lower().eq('true')
      skip = engulf.to_numpy(dtype=bool) & np.isfinite(prev_direction) & (prev_direction == candidate.signal.to_numpy(dtype=int))
      candidate = candidate.loc[~skip].copy()
    if not candidate.empty and self.min_atr_regime > 0:
      a14 = pd.Series(rolling_atr(m5, 14), dtype=float)
      previous_median = a14.shift(1).rolling(288, min_periods=144).median()
      loc = candidate.signal_index.to_numpy(dtype=int)
      reference = previous_median.iloc[loc].to_numpy(dtype=float)
      regime = candidate.atr.to_numpy(dtype=float) / reference
      candidate = candidate.loc[np.isfinite(regime) & (regime >= self.min_atr_regime)].copy()
    if self.enable_v423_retest and (not events.empty):
      retests = generate_confirmed_zone_retests(m5, events, bias)
      if not retests.empty:
        if self.v423_require_m15_break_alignment:
          retests = retests.loc[retests.aligned_break].copy()
        if self.v423_min_retest_body_atr > 0:
          retests = retests.loc[retests.body_atr_retest >= self.v423_min_retest_body_atr].copy()
        if self.v424_retest_long_only:
          retests = retests.loc[retests.signal == 1].copy()
        if not retests.empty:
          occupied = set(candidate.signal_index.to_list()) if not candidate.empty else set()
          retests = retests.loc[~retests.signal_index.isin(occupied)].copy()
          if not retests.empty:
            candidate = pd.concat([candidate, retests], ignore_index=True, sort=False)
            candidate = candidate.sort_values('signal_index', kind='stable')
    df['Position'] = 0
    df['strategy_stop_loss'] = float('nan')
    df['strategy_target'] = float('nan')
    df['signal_reason'] = ''
    if not candidate.empty:
      for r in candidate.itertuples(index=False):
        j = int(r.signal_index) + start
        df.at[j, 'Position'] = int(r.signal)
        df.at[j, 'strategy_stop_loss'] = float(r.sl)
        df.at[j, 'strategy_target'] = float(r.tp)
        df.at[j, 'signal_reason'] = 'TRENDLINE_V424_LONG_RETEST_RESEARCH|' + str(r.event_id)
    self._diagnostics = {'events': len(events), 'pivots': len(pivots), 'raw_candidates': stats.get('unique_signal_bars', 0), 'selected_signals': len(candidate), 'excluded_nonm5_prefix_rows': start, 'selection_params': {'min_body_ratio': self.min_body_ratio, 'min_body_atr': self.min_body_atr, 'max_confirmation_bars': self.max_confirmation_bars, 'max_touch_number': self.max_touch_number, 'direction': self.direction, 'require_engulfing': self.require_engulfing, 'add_strong_non_engulf': self.add_strong_non_engulf, 'min_atr_regime': self.min_atr_regime, 'skip_prev_day_aligned_engulf': self.skip_prev_day_aligned_engulf, 'add_wick_counter_htf': self.add_wick_counter_htf, 'expansion_min_body_range': self.expansion_min_body_range, 'expansion_min_body_atr': self.expansion_min_body_atr}}
    df.attrs['trendline_research_diagnostics'] = self._diagnostics
    return df
Strategy = XAUUSD_M5_Trendline_V424_LongRetestOnly_EXPERIMENT

def generate_event_signals(m5, events, bias, family='ZONE_WICK', params=None):
  p = {'min_touch': 3, 'min_wick': 0.45, 'min_close': 0.65, 'min_body_atr': 0.15, 'zone_atr': 0.2, 'confirmation': 1, 'risk_min': 0.6, 'risk_max': 25.0, 'bias_required': 0, 'min_slope': 0.025}
  p.update(params or {})
  n = len(m5)
  o, h, l, c = [m5[k].to_numpy(dtype=float) for k in ('Open', 'High', 'Low', 'Close')]
  dt = m5.Date
  minutes = dt.diff().dt.total_seconds().div(60).fillna(0).to_numpy()
  candidates = []
  for r in events.itertuples(index=False):
    i = int(r.index)
    side = 1 if str(r.direction) == 'LONG' else -1
    if i < 290 or i >= n - 1 or minutes[i + 1] != 5 or (int(r.touch_number) < p['min_touch']) or (abs(float(r.slope_atr)) < p['min_slope']):
      continue
    av = float(r.atr)
    if not np.isfinite(av) or av <= 0:
      continue
    span = max(h[i] - l[i], 0.001)
    wick = (min(o[i], c[i]) - l[i]) / span if side == 1 else (h[i] - max(o[i], c[i])) / span
    close = (c[i] - l[i]) / span if side == 1 else (h[i] - c[i]) / span
    line = float(r.line_price)
    penetration = (line - l[i]) / av if side == 1 else (h[i] - line) / av
    if family == 'ZONE_WICK':
      if str(r.state) != 'REJECTION' or wick < p['min_wick'] or close < p['min_close'] or (abs(c[i] - o[i]) / av < p['min_body_atr']):
        continue
    elif family == 'SWEEP_RECLAIM':
      if wick < p['min_wick'] or close < p['min_close'] or penetration < p['zone_atr']:
        continue
      if not side * (c[i] - line) > 0:
        continue
    elif family == 'COUNTER_SLOPE':
      if str(r.state) != 'REJECTION' or wick < p['min_wick'] or close < p['min_close']:
        continue
    else:
      raise ValueError(family)
    j = i + int(p['confirmation'])
    if j >= n or np.any(minutes[i + 1:j + 1] != 5):
      continue
    if p['confirmation'] == 1:
      directional = side * (c[j] - o[j]) > 0 and side * (c[j] - c[i]) > 0
    else:
      directional = side * (c[j] - o[j]) > 0 and side * (c[j] - c[i]) > 0 and (side * (c[j] - c[j - 1]) > 0)
    if not directional:
      continue
    if p['bias_required'] == 1 and int(bias[j]) != side:
      continue
    if p['bias_required'] == -1 and int(bias[j]) == -side:
      continue
    sl = float(l[i] - 0.5) if side == 1 else float(h[i] + 0.5)
    risk = side * (c[j] - sl)
    if risk < p['risk_min'] or risk > p['risk_max']:
      continue
    tp = float(c[j] + 2 * side * risk)
    candidates.append({'signal_index': j, 'Date': dt.iloc[j], 'Position': side, 'strategy_stop_loss': sl, 'strategy_target': tp, 'signal_reason': f'{family}|{r.line_id}|{i}|{j}', 'family': family, 'touch': int(r.touch_number), 'atr': av, 'wick': float(wick), 'close_pos': float(close), 'body_atr': float(abs(c[i] - o[i]) / av), 'slope_atr': float(r.slope_atr), 'confirmation': j - i, 'bias': int(bias[j]), 'risk': float(risk), 'hour_utc': int(dt.iloc[j].hour), 'year': int(dt.iloc[j].year), 'source_index': i, 'line_id': str(r.line_id)})
  if not candidates:
    return pd.DataFrame(columns=['signal_index', 'Date', 'Position', 'strategy_stop_loss', 'strategy_target', 'signal_reason', 'family'])
  t = pd.DataFrame(candidates).sort_values(['signal_index', 'wick', 'source_index', 'line_id'], ascending=[True, False, True, True], kind='stable').drop_duplicates('signal_index').reset_index(drop=True)
  return t

class XAUUSD_Trendline_V427_TwoBarZone_RESEARCH_ONLY(XAUUSD_M5_Trendline_V424_LongRetestOnly_EXPERIMENT):
  pass

  def generate(self):
    base = super().generate()
    m5 = base[['Date', 'Open', 'High', 'Low', 'Close']].copy().reset_index(drop=True)
    diffs = m5.Date.diff().dt.total_seconds().div(60)
    ix = int(np.flatnonzero(diffs.eq(5).to_numpy())[0]) - 1 if bool(diffs.eq(5).any()) else 0
    ix = max(0, ix)
    genuine = m5.iloc[ix:].reset_index(drop=True)
    ev, _ = detect_trendline_events(genuine, self.detector_params)
    if ev.empty:
      return base
    bias = htf_bias(genuine)
    new = generate_event_signals(genuine, ev, bias, 'ZONE_WICK', {'confirmation': 2, 'min_wick': 0.35, 'min_close': 0.6})
    if new.empty:
      return base
    new = new.loc[(new.wick >= 0.35) & (new.close_pos >= 0.55) & (new.body_atr >= 0.1) & (new.touch >= 3) & (new.slope_atr.abs() >= 0.1) & (new.risk <= 10.0)].copy()
    new = new.loc[new.bias != -new.Position].copy()
    new = new.loc[new.Date.dt.hour.between(0, 7)].copy()
    for r in new.itertuples(index=False):
      j = int(r.signal_index) + ix
      if j < 0 or j >= len(base) or int(base.at[j, 'Position']) != 0:
        continue
      base.at[j, 'Position'] = int(r.Position)
      base.at[j, 'strategy_stop_loss'] = float(r.strategy_stop_loss)
      base.at[j, 'strategy_target'] = float(r.strategy_target)
      base.at[j, 'signal_reason'] = 'TRENDLINE_V427_RESEARCH_ONLY|' + str(r.signal_reason)
    return base
Strategy = XAUUSD_Trendline_V427_TwoBarZone_RESEARCH_ONLY

class V428_FilteredZone_RESEARCH_ONLY(XAUUSD_Trendline_V427_TwoBarZone_RESEARCH_ONLY):

  def generate(self):
    df = super().generate()
    date = pd.to_datetime(df['Date'])
    prev = df['Close'].shift(1)
    tr = pd.concat([df.High - df.Low, (df.High - prev).abs(), (df.Low - prev).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=14).mean()
    historical_med = atr.shift(1).rolling(288, min_periods=144).median()
    atr_ratio = atr / historical_med
    span = (df.High - df.Low).clip(lower=0.001)
    pos = df['Position'].to_numpy(dtype=int)
    long_quality = ((df.Close - df.Low) / span).to_numpy(dtype=float)
    short_quality = ((df.High - df.Close) / span).to_numpy(dtype=float)
    quality = np.where(pos == 1, long_quality, short_quality)
    stop_distance = (df.Close - df.strategy_stop_loss).abs()
    tag = df['signal_reason'].astype(str).str.startswith('TRENDLINE_V427_RESEARCH_ONLY|')
    valid = atr_ratio.ge(0.6) & (quality >= 0.65) & stop_distance.ge(1.0) & stop_distance.le(15.0)
    drop = tag & ~valid
    df.loc[drop, 'Position'] = 0
    df.loc[drop, 'strategy_stop_loss'] = float('nan')
    df.loc[drop, 'strategy_target'] = float('nan')
    df.loc[drop, 'signal_reason'] = ''
    df.attrs['v428_research'] = {'rule': 'ATR regime >=.60 AND last-confirmation close position >=.65 AND indicative stop risk >=1 USD/oz; inspected-stress exploratory', 'rejected_new_signals': int(drop.sum()), 'retained_new_signals': int((tag & valid).sum())}
    return df
Strategy = V428_FilteredZone_RESEARCH_ONLY

class V429_TrainSelectedATRSession_RESEARCH_ONLY(V428_FilteredZone_RESEARCH_ONLY):

  def generate(self):
    frame = super().generate()
    ts = pd.to_datetime(frame['Date'])
    prev = frame['Close'].shift(1)
    tr = pd.concat([frame.High - frame.Low, (frame.High - prev).abs(), (frame.Low - prev).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=14).mean()
    med = atr.shift(1).rolling(288, min_periods=144).median()
    regime = atr / med
    stop_distance = (frame.Close - frame.strategy_stop_loss).abs()
    allow = (regime >= 0.65) & (regime <= 20) & (stop_distance <= 25) & (ts.dt.hour < 8)
    new_zone = frame.signal_reason.astype(str).str.startswith('TRENDLINE_V427_RESEARCH_ONLY|')
    veto = new_zone & ~allow
    frame.loc[veto, 'Position'] = 0
    frame.loc[veto, 'strategy_stop_loss'] = float('nan')
    frame.loc[veto, 'strategy_target'] = float('nan')
    frame.loc[veto, 'signal_reason'] = ''
    frame.attrs['V429_SANDBOX_FILTERS'] = {'veto_new_zone': int(veto.sum()), 'filter_source': '2022-2023, historically inspected', 'activation': 'RESEARCH_ONLY'}
    return frame
Strategy = V429_TrainSelectedATRSession_RESEARCH_ONLY

def _v430_completed_bar_direction(candles, rule, count_required, duration_min):
  d = candles.set_index('Date')
  bars = d[['Open', 'Close']].resample(rule, closed='left', label='left').agg({'Open': 'first', 'Close': 'last'})
  count = d.Close.resample(rule, closed='left', label='left').count()
  completed = bars[count.eq(count_required)].dropna()
  available = (completed.index + pd.Timedelta(minutes=duration_min)).to_numpy(dtype='datetime64[ns]')
  candle_closes = (candles.Date + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
  idx = np.searchsorted(available, candle_closes, side='right') - 1
  out = np.zeros(len(candles), dtype=np.int8)
  valid = idx >= 0
  if valid.any():
    out[valid] = np.sign((completed.Close - completed.Open).to_numpy(dtype=float))[idx[valid]].astype(np.int8)
  return out

def _v430_add_new_entries(owner, frozen_frame, variant):
  out = frozen_frame.copy()
  d = out.Date.diff().dt.total_seconds().div(60)
  first = int(np.flatnonzero(d.eq(5).to_numpy())[0]) - 1 if bool(d.eq(5).any()) else 0
  first = max(first, 0)
  m5 = out.iloc[first:][['Date', 'Open', 'High', 'Low', 'Close']].copy().reset_index(drop=True)
  if len(m5) < 300:
    return out
  events, _ = detect_trendline_events(m5, owner.detector_params)
  if events.empty:
    return out
  bias = htf_bias(m5)
  if variant == 'A':
    conf, min_quality, min_ratio, risk_max, min_wick, htf = (2, 0.8, 0.6, 10.0, 0.3, 'BOTH')
  elif variant == 'B':
    conf, min_quality, min_ratio, risk_max, min_wick, htf = (1, 0.55, 1.0, 20.0, 0.3, 'H1')
  else:
    raise ValueError('Unknown V430 research variant')
  proposed = generate_event_signals(m5, events, bias, 'SWEEP_RECLAIM', {'confirmation': conf, 'min_touch': 3, 'min_wick': 0.3, 'min_close': 0.55, 'min_body_atr': 0.0, 'zone_atr': 0.05, 'risk_min': 0.5, 'risk_max': 30.0, 'min_slope': 0.025})
  if proposed.empty:
    return out
  ix = proposed.signal_index.to_numpy(dtype=int)
  preceding = m5.Close.shift(1)
  tr = pd.concat([m5.High - m5.Low, (m5.High - preceding).abs(), (m5.Low - preceding).abs()], axis=1).max(axis=1)
  atr = tr.rolling(14, min_periods=14).mean()
  atr_regime = (atr / atr.shift(1).rolling(288, min_periods=144).median()).iloc[ix].to_numpy()
  span = np.maximum((m5.High - m5.Low).iloc[ix].to_numpy(dtype=float), 0.001)
  closeq = np.where(proposed.Position.to_numpy(dtype=int) == 1, (m5.Close - m5.Low).iloc[ix].to_numpy(dtype=float) / span, (m5.High - m5.Close).iloc[ix].to_numpy(dtype=float) / span)
  direction = proposed.Position.to_numpy(dtype=int)
  h1 = _v430_completed_bar_direction(m5, '1h', 12, 60)[ix]
  h4 = _v430_completed_bar_direction(m5, '4h', 48, 240)[ix]
  aligned = h1 == direction if htf == 'H1' else (h1 == direction) & (h4 == direction)
  selected = (direction == -1) & (closeq >= min_quality) & (atr_regime >= min_ratio) & (proposed.risk.to_numpy(dtype=float) <= risk_max) & (proposed.risk.to_numpy(dtype=float) >= 0.5) & (proposed.wick.to_numpy(dtype=float) >= min_wick) & (proposed.touch.to_numpy(dtype=int) >= 3) & aligned
  new = proposed.loc[selected].copy()
  count_added = 0
  for r in new.itertuples(index=False):
    global_index = int(r.signal_index) + first
    if global_index >= len(out) or int(out.at[global_index, 'Position']) != 0:
      continue
    out.at[global_index, 'Position'] = int(r.Position)
    out.at[global_index, 'strategy_stop_loss'] = float(r.strategy_stop_loss)
    out.at[global_index, 'strategy_target'] = float(r.strategy_target)
    out.at[global_index, 'signal_reason'] = 'TRENDLINE_V430' + variant + '_RESEARCH_ONLY|' + str(r.signal_reason)
    count_added += 1
  out.attrs['v430_research'] = {'variant': variant, 'new_selected': int(len(new)), 'added_signal_bars': count_added, 'historical_inspected_data': True, 'deploy_to_live': False}
  return out

class V430A_Sweep2_RESEARCH_ONLY(V429_TrainSelectedATRSession_RESEARCH_ONLY):

  def generate(self):
    return _v430_add_new_entries(self, super().generate(), 'A')

class V430B_Sweep1_RESEARCH_ONLY(V429_TrainSelectedATRSession_RESEARCH_ONLY):

  def generate(self):
    return _v430_add_new_entries(self, super().generate(), 'B')
Strategy = V430B_Sweep1_RESEARCH_ONLY

def _v431_add_entries(owner, frozen_frame, mode):
  out = frozen_frame.copy()
  gaps = out.Date.diff().dt.total_seconds().div(60)
  start = int(np.flatnonzero(gaps.eq(5).to_numpy())[0]) - 1 if bool(gaps.eq(5).any()) else 0
  start = max(0, start)
  m5 = out.iloc[start:][['Date', 'Open', 'High', 'Low', 'Close']].copy().reset_index(drop=True)
  if len(m5) < 300:
    return out
  events, _ = detect_trendline_events(m5, owner.detector_params)
  if events.empty:
    return out
  bias = htf_bias(m5)
  if mode == 'A':
    family = 'ZONE_WICK'
    confirmation = 3
    min_close, min_ratio, min_wick, max_risk, min_touch, bodymin = (0.85, 1.1, 0.6, 10.0, 4, 0.0)
    htf = 'NONE'
  elif mode == 'B':
    family = 'SWEEP_RECLAIM'
    confirmation = 2
    min_close, min_ratio, min_wick, max_risk, min_touch, bodymin = (0.55, 0.8, 0.45, 20.0, 3, 0.4)
    htf = 'H1'
  else:
    raise ValueError('Invalid research mode')
  proposals = generate_event_signals(m5, events, bias, family, {'confirmation': confirmation, 'min_touch': 3, 'min_wick': 0.3, 'min_close': 0.55, 'min_body_atr': 0.0, 'zone_atr': 0.05, 'risk_min': 0.5, 'risk_max': 30.0, 'min_slope': 0.025})
  if proposals.empty:
    return out
  ix = proposals.signal_index.to_numpy(dtype=int)
  previous = m5.Close.shift(1)
  true_range = pd.concat([m5.High - m5.Low, (m5.High - previous).abs(), (m5.Low - previous).abs()], axis=1).max(axis=1)
  atr = true_range.rolling(14, min_periods=14).mean()
  regime = (atr / atr.shift(1).rolling(288, min_periods=144).median()).iloc[ix].to_numpy(dtype=float)
  span = np.maximum((m5.High - m5.Low).iloc[ix].to_numpy(dtype=float), 0.001)
  side = proposals.Position.to_numpy(dtype=int)
  closeq = np.where(side > 0, (m5.Close - m5.Low).iloc[ix].to_numpy(dtype=float) / span, (m5.High - m5.Close).iloc[ix].to_numpy(dtype=float) / span)
  same_h1 = _v430_completed_bar_direction(m5, '1h', 12, 60)[ix] == side
  keep = (closeq >= min_close) & (regime >= min_ratio) & (proposals.wick.to_numpy(dtype=float) >= min_wick) & (proposals.risk.to_numpy(dtype=float) >= 0.5) & (proposals.risk.to_numpy(dtype=float) <= max_risk) & (proposals.touch.to_numpy(dtype=int) >= min_touch) & (proposals.body_atr.to_numpy(dtype=float) >= bodymin)
  if htf == 'H1':
    keep &= same_h1
  selected = proposals.loc[keep]
  added = 0
  for r in selected.itertuples(index=False):
    gi = int(r.signal_index) + start
    if gi >= len(out) or int(out.at[gi, 'Position']) != 0:
      continue
    out.at[gi, 'Position'] = int(r.Position)
    out.at[gi, 'strategy_stop_loss'] = float(r.strategy_stop_loss)
    out.at[gi, 'strategy_target'] = float(r.strategy_target)
    out.at[gi, 'signal_reason'] = 'TRENDLINE_V431' + mode + '_RESEARCH_ONLY|' + str(r.signal_reason)
    added += 1
  out.attrs['v431_research'] = {'variant': mode, 'selected_intents': int(len(selected)), 'new_signal_bars': int(added), 'historical_research_only': True, 'live_approved': False}
  return out

class V431_RESEARCH_ONLY(V430B_Sweep1_RESEARCH_ONLY):
  pass

  def generate(self):
    return _v431_add_entries(self, super().generate(), RESEARCH_MODE)
RESEARCH_MODE = 'B'
Strategy = V431_RESEARCH_ONLY

def _v8_completed_htf_features(raw):
  import pandas as pd
  import numpy as np
  work = raw[['Date', 'Open', 'High', 'Low', 'Close']].copy()
  work['Date'] = pd.to_datetime(work['Date'])
  work = work.set_index('Date')
  decision = pd.DatetimeIndex(raw['Date']) + pd.Timedelta(minutes=5)
  out = {}
  for minutes in (10, 45):
    key = str(minutes)
    group = work.resample(f'{minutes}min', label='left', closed='left')
    x = group.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    counts = group['Close'].count()
    x = x.loc[counts.eq(minutes // 5)].copy()
    x['available'] = x.index + pd.Timedelta(minutes=minutes)
    x['body'] = (x.Close - x.Open).abs() / (x.High - x.Low).clip(lower=1e-09)
    x['opp_long'] = (x.High - np.maximum(x.Open, x.Close)) / (x.High - x.Low).clip(lower=1e-09)
    x['opp_short'] = (np.minimum(x.Open, x.Close) - x.Low) / (x.High - x.Low).clip(lower=1e-09)
    x['dirpos_long'] = (x.Close - x.Low) / (x.High - x.Low).clip(lower=1e-09)
    x['dirpos_short'] = (x.High - x.Close) / (x.High - x.Low).clip(lower=1e-09)
    x['prevhi24'] = x.High.rolling(24, min_periods=24).max().shift(1)
    x['prevlo24'] = x.Low.rolling(24, min_periods=24).min().shift(1)
    x['fav_long'] = (x.Low < x.prevlo24) & (x.Close > x.prevlo24)
    x['fav_short'] = (x.High > x.prevhi24) & (x.Close < x.prevhi24)
    idx = np.searchsorted(x['available'].to_numpy(dtype='datetime64[ns]'), decision.to_numpy(dtype='datetime64[ns]'), side='right') - 1
    valid = idx >= 0
    safe = np.maximum(idx, 0)
    for col in ['body', 'opp_long', 'opp_short', 'dirpos_long', 'dirpos_short', 'fav_long', 'fav_short']:
      arr = x[col].to_numpy()[safe]
      if col.startswith('fav'):
        out[key + '_' + col] = arr & valid
      else:
        out[key + '_' + col] = np.where(valid, arr, np.nan)
    out[key + '_has'] = valid
  return out

def _v86_highvol_short_sweep(raw):
  import pandas as pd
  import numpy as np
  n = len(raw)
  a = raw[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
  a['Date'] = pd.to_datetime(a['Date'])
  t = a['Date'].to_numpy(dtype='datetime64[ns]')
  o = a.Open.to_numpy(dtype=float)
  h = a.High.to_numpy(dtype=float)
  l = a.Low.to_numpy(dtype=float)
  c = a.Close.to_numpy(dtype=float)
  vol = a.Volume.to_numpy(dtype=float)
  tr = np.maximum.reduce([h - l, abs(h - np.r_[c[0], c[:-1]]), abs(l - np.r_[c[0], c[:-1]])])
  atr = pd.Series(tr).ewm(alpha=1.0 / 14.0, adjust=False, min_periods=14).mean().to_numpy()
  med = pd.Series(atr).shift(1).rolling(288, min_periods=144).median().to_numpy()
  prev_high = pd.Series(h).shift(1).rolling(24, min_periods=24).max().to_numpy()
  vavg = pd.Series(vol).shift(1).rolling(48, min_periods=48).mean().to_numpy()
  closepos = (h - c) / np.maximum(h - l, 1e-08)
  f = a.set_index('Date')
  gr = f.resample('60min', label='left', closed='left')
  hourly = gr.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
  hourly = hourly.loc[gr.Close.count() == 12].copy()
  hourly['available'] = hourly.index + pd.Timedelta(hours=1)
  hourly['ema20'] = hourly.Close.ewm(span=20, adjust=False).mean()
  hourly['momentum4'] = hourly.Close - hourly.Close.shift(4)
  ht = hourly.available.to_numpy(dtype='datetime64[ns]')
  ix = np.searchsorted(ht, t + np.timedelta64(5, 'm'), side='right') - 1
  valid = ix >= 0
  ix = np.maximum(ix, 0)
  hc = hourly.Close.to_numpy(dtype=float)[ix]
  he = hourly.ema20.to_numpy(dtype=float)[ix]
  hm = hourly.momentum4.to_numpy(dtype=float)[ix]
  hr = np.asarray(a.Date.dt.hour, dtype=int)
  nextbar = np.r_[np.diff(t) == np.timedelta64(5, 'm'), False]
  gate = nextbar & valid & (h > prev_high) & (c < prev_high) & (vol / np.maximum(vavg, 1.0) >= 1.1) & (atr / np.maximum(med, 1e-09) >= 1.2) & (closepos >= 0.65) & (hc - he <= -0.35 * atr) & (-hm >= 1.0 * atr) & (hr >= 7) & (hr < 20) & np.isfinite(atr) & (atr > 0) & np.isfinite(prev_high)
  stop = np.maximum(h + 0.12 * atr, c + 1.0 * atr)
  risk = (stop - c) / np.maximum(atr, 1e-08)
  gate &= np.isfinite(risk) & (risk >= 0.3) & (risk <= 4.5)
  return (gate, stop)

def _v89_htf_break_retest_long(raw):
  import numpy as np, pandas as pd
  h = raw.High.to_numpy(float)
  l = raw.Low.to_numpy(float)
  o = raw.Open.to_numpy(float)
  c = raw.Close.to_numpy(float)
  v = raw.Volume.to_numpy(float)
  t = pd.to_datetime(raw.Date).to_numpy(dtype='datetime64[ns]')
  tr = np.maximum.reduce([h - l, abs(h - np.r_[c[0], c[:-1]]), abs(l - np.r_[c[0], c[:-1]])])
  atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().to_numpy()
  rsi_d = pd.Series(c).diff()
  up = rsi_d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
  down = (-rsi_d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
  rsi = (100 - 100 / (1 + up / np.maximum(down, 1e-09))).to_numpy()
  volmean = pd.Series(v).shift(1).rolling(48, min_periods=48).mean().to_numpy()
  level = pd.Series(h).shift(2).rolling(12, min_periods=12).max().to_numpy()
  previous_break = np.r_[False, c[:-1] > level[:-1]]
  body = np.abs(c - o) / np.maximum(h - l, 1e-08)

  def confirmed(minutes):
    f = raw[['Date', 'Open', 'High', 'Low', 'Close']].copy()
    f.Date = pd.to_datetime(f.Date)
    grp = f.set_index('Date').resample(f'{minutes}min', closed='left', label='left')
    z = grp.agg({'Close': 'last'}).loc[grp.Close.count() == minutes // 5].copy()
    z['available'] = z.index + pd.Timedelta(minutes=minutes)
    z['ema20'] = z.Close.ewm(span=20, adjust=False).mean()
    available = z.available.to_numpy(dtype='datetime64[ns]')
    ix = np.searchsorted(available, t + np.timedelta64(5, 'm'), side='right') - 1
    valid = ix >= 0
    ix = np.maximum(ix, 0)
    gap = z.Close.to_numpy(float)[ix] - z.ema20.to_numpy(float)[ix]
    return (valid, gap)
  valid15, gap15 = confirmed(15)
  valid60, gap60 = confirmed(60)
  nextbar = np.r_[np.diff(t) == np.timedelta64(5, 'm'), False]
  stop = pd.Series(l).rolling(6, min_periods=6).min().to_numpy() - 0.12 * atr
  risk = (c - stop) / np.maximum(atr, 1e-09)
  gate = nextbar & valid15 & valid60 & previous_break & (l <= level) & (c > level) & (c > o) & (body >= 0.65) & (v / np.maximum(volmean, 1.0) >= 1.6) & (rsi >= 65) & (gap15 >= 0.3 * atr) & (gap60 >= 0.35 * atr) & (risk >= 0.3) & (risk <= 4.5) & np.isfinite(atr)
  return (gate, stop)

def _v9_completed_htf_veto_features(raw):
  pass
  import numpy as np
  import pandas as pd
  n = len(raw)
  idx = (pd.DatetimeIndex(pd.to_datetime(raw.Date)) + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
  oo = raw.Open.to_numpy(dtype=float)
  hh = raw.High.to_numpy(dtype=float)
  ll = raw.Low.to_numpy(dtype=float)
  cc = raw.Close.to_numpy(dtype=float)
  spread = np.maximum(hh - ll, 1e-12)
  m5_long = (cc - ll) / spread
  m5_short = (hh - cc) / spread
  h15long = np.full(n, np.nan)
  h15short = np.full(n, np.nan)
  h30volume = np.full(n, np.nan)
  h240body = np.full(n, np.nan)
  work = raw.set_index(pd.DatetimeIndex(raw.Date))
  for minutes in (15, 30, 240):
    gr = work.resample(f'{minutes}min', label='left', closed='left')
    a = gr.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
    full = gr.Close.count().eq(minutes // 5)
    a = a.loc[full].copy()
    if a.empty:
      continue
    end = (a.index + pd.Timedelta(minutes=minutes)).to_numpy(dtype='datetime64[ns]')
    k = np.searchsorted(end, idx, side='right') - 1
    valid = k >= 0
    k = np.maximum(k, 0)
    A = a.Open.to_numpy(dtype=float)
    H = a.High.to_numpy(dtype=float)
    L = a.Low.to_numpy(dtype=float)
    C = a.Close.to_numpy(dtype=float)
    V = a.Volume.to_numpy(dtype=float)
    span = np.maximum(H[k] - L[k], 1e-12)
    if minutes == 15:
      h15long = np.where(valid, (C[k] - L[k]) / span, np.nan)
      h15short = np.where(valid, (H[k] - C[k]) / span, np.nan)
    elif minutes == 30:
      prior = pd.Series(V).shift(1).rolling(12, min_periods=12).mean().to_numpy(dtype=float)
      ratio = V[k] / np.maximum(prior[k], 1.0)
      h30volume = np.where(valid & np.isfinite(prior[k]), ratio, np.nan)
    else:
      h240body = np.where(valid, np.abs(C[k] - A[k]) / span, np.nan)
  v91L = (m5_long >= 0.7) & (h15long < 0.25) & (h240body < 0.22)
  v91S = (m5_short >= 0.7) & (h15short < 0.25) & (h240body < 0.22)
  v92L = (h15long < 0.4) & (h30volume < 1.45) & (h240body < 0.22)
  v92S = (h15short < 0.4) & (h30volume < 1.45) & (h240body < 0.22)
  return {'v91long': v91L, 'v91short': v91S, 'v92long': v92L, 'v92short': v92S}

def _v96_v97_mtf_veto_features(raw):
  import numpy as np, pandas as pd
  n = len(raw)
  dt = pd.DatetimeIndex(pd.to_datetime(raw.Date))
  decision = (dt + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
  hi = raw.High.to_numpy(dtype=float)
  lo = raw.Low.to_numpy(dtype=float)
  cl = raw.Close.to_numpy(dtype=float)
  tr = np.maximum.reduce((hi - lo, abs(hi - np.r_[cl[0], cl[:-1]]), abs(lo - np.r_[cl[0], cl[:-1]])))
  atr = pd.Series(tr).ewm(alpha=1.0 / 14.0, adjust=False).mean().to_numpy(dtype=float)
  features = {}
  w = raw.set_index(dt)
  for mins in (15, 30, 60, 240):
    g = w.resample(f'{mins}min', label='left', closed='left')
    z = g.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
    z = z.loc[g.Close.count().eq(mins // 5)].copy()
    if len(z) < 30:
      continue
    ends = (z.index + pd.Timedelta(minutes=mins)).to_numpy(dtype='datetime64[ns]')
    j = np.searchsorted(ends, decision, side='right') - 1
    valid = j >= 0
    j = np.maximum(j, 0)
    O = z.Open.to_numpy(dtype=float)
    H = z.High.to_numpy(dtype=float)
    L = z.Low.to_numpy(dtype=float)
    C = z.Close.to_numpy(dtype=float)
    V = z.Volume.to_numpy(dtype=float)
    if mins == 15:
      prhi = pd.Series(H).shift(1).rolling(8, min_periods=8).max().to_numpy(float)
      prlo = pd.Series(L).shift(1).rolling(8, min_periods=8).min().to_numpy(float)
      features['h15_range8_pos'] = np.where(valid, (C[j] - prlo[j]) / np.maximum(prhi[j] - prlo[j], 1e-10), np.nan)
    if mins == 30:
      m = pd.Series(V).shift(1).rolling(12, min_periods=12).mean().to_numpy(float)
      features['h30_volume_ratio'] = np.where(valid, V[j] / np.maximum(m[j], 1.0), np.nan)
    if mins == 60:
      p3 = np.r_[np.full(3, np.nan), C[:-3]]
      d = (C[j] - p3[j]) / np.maximum(atr, 1e-10)
      features['h60_trend3_long'] = np.where(valid, d, np.nan)
      features['h60_trend3_short'] = np.where(valid, -d, np.nan)
      features['h60_body'] = np.where(valid, np.abs(C[j] - O[j]) / np.maximum(H[j] - L[j], 1e-10), np.nan)
    if mins == 240:
      prhi = pd.Series(H).shift(1).rolling(8, min_periods=8).max().to_numpy(float)
      prlo = pd.Series(L).shift(1).rolling(8, min_periods=8).min().to_numpy(float)
      features['h240_break8_long'] = np.where(valid, (C[j] - prhi[j]) / np.maximum(atr, 1e-10), np.nan)
      features['h240_break8_short'] = np.where(valid, (prlo[j] - C[j]) / np.maximum(atr, 1e-10), np.nan)
      m = pd.Series(V).shift(1).rolling(12, min_periods=12).mean().to_numpy(float)
      features['h240_volume_ratio'] = np.where(valid, V[j] / np.maximum(m[j], 1.0), np.nan)
  required = ('h30_volume_ratio', 'h60_trend3_long', 'h240_break8_long', 'h60_trend3_short', 'h240_break8_short', 'h15_range8_pos', 'h60_body', 'h240_volume_ratio')
  if any((k not in features for k in required)):
    return {'v96long': np.zeros(n, dtype=bool), 'v96short': np.zeros(n, dtype=bool), 'v97long': np.zeros(n, dtype=bool), 'v97short': np.zeros(n, dtype=bool)}
  c96 = features['h30_volume_ratio'] >= 1.64008
  long96 = c96 & (features['h60_trend3_long'] >= 2.44989) & (features['h240_break8_long'] < -3.03884)
  short96 = c96 & (features['h60_trend3_short'] >= 2.44989) & (features['h240_break8_short'] < -3.03884)
  c97 = (features['h15_range8_pos'] >= 1.07726) & (features['h60_body'] >= 0.58985) & (features['h240_volume_ratio'] < 0.78074)
  return {'v96long': long96, 'v96short': short96, 'v97long': c97, 'v97short': c97}

def _research_v98_v99_candidates(raw, variant):
  import numpy as np, pandas as pd
  oo = raw.Open.to_numpy(float)
  hh = raw.High.to_numpy(float)
  ll = raw.Low.to_numpy(float)
  cc = raw.Close.to_numpy(float)
  vv = raw.Volume.to_numpy(float)
  dates = pd.DatetimeIndex(pd.to_datetime(raw.Date))
  t = dates.to_numpy(dtype='datetime64[ns]')
  decision = t + np.timedelta64(5, 'm')
  last = np.r_[cc[0], cc[:-1]]
  tr = np.maximum.reduce([hh - ll, np.abs(hh - last), np.abs(ll - last)])
  atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().to_numpy()
  atrmed = pd.Series(atr).shift(1).rolling(288, min_periods=144).median().to_numpy()
  volume_baseline = pd.Series(vv).shift(1).rolling(48, min_periods=48).mean().to_numpy()
  vrel = vv / np.maximum(volume_baseline, 1.0)
  valid_next = np.r_[np.diff(t) == np.timedelta64(5, 'm'), False]
  span = np.maximum(hh - ll, 1e-10)

  def completed(minutes):
    temp = raw.set_index(dates)
    g = temp.resample(f'{minutes}min', label='left', closed='left')
    z = g.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
    z = z.loc[g.Close.count().eq(minutes // 5)].copy()
    ends = (z.index + pd.Timedelta(minutes=minutes)).to_numpy(dtype='datetime64[ns]')
    j = np.searchsorted(ends, decision, side='right') - 1
    ok = j >= 0
    j = np.maximum(j, 0)
    z['ema20'] = z.Close.ewm(span=20, adjust=False).mean()
    z['priorhi16'] = z.High.shift(1).rolling(16, min_periods=16).max()
    return (z, ends, j, ok)
  if variant == 'V98':
    m15, e15, j15, ok15 = completed(15)
    h1, e1, j1, ok1 = completed(60)
    mlow = m15.Low.to_numpy(float)[j15]
    mclose = m15.Close.to_numpy(float)[j15]
    mema = m15.ema20.to_numpy(float)[j15]
    hc = h1.Close.to_numpy(float)[j1]
    hema = h1.ema20.to_numpy(float)[j1]
    signal = ok15 & ok1 & (e15[j15] == decision) & valid_next & (mlow < mema) & (mclose > mema) & (cc > oo) & ((cc - ll) / span >= 0.62) & ((hc - hema) / np.maximum(atr, 0.01) >= 0.25) & (vrel >= 1.8) & (dates.hour >= 12) & (dates.hour < 21)
    sig = 1
  elif variant == 'V99':
    m10, e10, j10, ok10 = completed(10)
    m45, e45, j45, ok45 = completed(45)
    lo = m10.Low.to_numpy(float)[j10]
    hi = m10.High.to_numpy(float)[j10]
    close = m10.Close.to_numpy(float)[j10]
    level = m10.priorhi16.to_numpy(float)[j10]
    gap = m45.ema20.to_numpy(float)[j45] - m45.Close.to_numpy(float)[j45]
    signal = ok10 & ok45 & (e10[j10] == decision) & valid_next & (hi > level) & (close < level) & (cc < oo) & ((hh - cc) / span >= 0.62) & (gap / np.maximum(atr, 0.01) >= 0.2) & (atr / np.maximum(atrmed, 0.01) >= 1.15) & (vrel >= 1.25)
    sig = -1
  else:
    raise ValueError(variant)
  stop = pd.Series(ll).rolling(7, min_periods=7).min().to_numpy() - 0.18 * atr if sig > 0 else pd.Series(hh).rolling(7, min_periods=7).max().to_numpy() + 0.18 * atr
  rr = sig * (cc - stop) / np.maximum(atr, 1e-10)
  signal &= np.isfinite(atr) & np.isfinite(stop) & (rr >= 0.4) & (rr <= 5)
  return (signal, stop)

def _v912_m15_bos_new_long(raw):
  import numpy as np
  import pandas as pd
  d = pd.to_datetime(raw['Date'])
  o = raw.Open.to_numpy(float)
  h = raw.High.to_numpy(float)
  l = raw.Low.to_numpy(float)
  c = raw.Close.to_numpy(float)
  v = raw.Volume.to_numpy(float)
  prev = np.r_[c[0], c[:-1]]
  tr = np.maximum.reduce([h - l, abs(h - prev), abs(l - prev)])
  atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().to_numpy(float)
  atrmed = pd.Series(atr).shift(1).rolling(288, min_periods=144).median().to_numpy(float)
  vrel = v / np.maximum(pd.Series(v).shift(1).rolling(48, min_periods=48).mean().to_numpy(float), 1)
  span = np.maximum(h - l, 1e-06)
  body = np.abs(c - o) / span
  t = d.to_numpy(dtype='datetime64[ns]')
  decision = t + np.timedelta64(5, 'm')
  next_exact = np.r_[t[1:] - t[:-1] == np.timedelta64(5, 'm'), False]
  data = raw.set_index(d)

  def completed(minutes):
    g = data.resample(f'{minutes}min', label='left', closed='left')
    z = g.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
    z = z.loc[g.Close.count().eq(minutes // 5)].copy()
    z['ema20'] = z.Close.ewm(span=20, adjust=False).mean()
    z['priorhi8'] = z.High.shift(1).rolling(8, min_periods=8).max()
    ends = (z.index + pd.Timedelta(minutes=minutes)).to_numpy(dtype='datetime64[ns]')
    ix = np.searchsorted(ends, decision, side='right') - 1
    ok = ix >= 0
    ix = np.maximum(ix, 0)
    return (z, ends, ix, ok)
  m, me, mi, mok = completed(15)
  h4, he, hi, hok = completed(240)
  mclose = m.Close.to_numpy(float)[mi]
  breakout = m.priorhi8.to_numpy(float)[mi]
  ht = (h4.Close.to_numpy(float)[hi] - h4.ema20.to_numpy(float)[hi]) / np.maximum(atr, 0.01)
  stop = pd.Series(l).rolling(5, min_periods=5).min().to_numpy(float) - 0.15 * atr
  risk = (c - stop) / np.maximum(atr, 1e-10)
  signal = mok & hok & (me[mi] == decision) & next_exact & (mclose > breakout) & (c > o) & (ht >= 0.25) & (atr / np.maximum(atrmed, 1e-06) >= 1.15) & (vrel >= 1.8) & (body >= 0.6) & np.isfinite(atr) & np.isfinite(stop) & (risk >= 0.4) & (risk <= 5.0)
  return (signal, stop)

class AlgoAgentX_V62_NewEntries_RESEARCH_ONLY:
  pass
  LIVE_HISTORY_BARS = 24000

  def __init__(self, df, same_bar_priority='V35', conflict_policy='SKIP', v5_filter_enabled=True, v5_filter_rule='RECENT_EXTREME_CLOSE', v52_filter_enabled=True, v52_filter_rule='MOMENTUM_WICK_SESSION', v54_filter_enabled=True, v55_filter_enabled=True, v56_filter_enabled=True, v57_filter_enabled=True, v57_filter_rule='CHOP_EXPANSION', v58_new_entries_enabled=True, v58_rule='STRICT_EARLY_ATR3', v59_new_entries_enabled=True, v61_fvg_new_entries_enabled=True, v62_failed_break_new_entries_enabled=False, v62_compression_long_enabled=True, v63_resist96_enabled=True, v64_gate_enabled=True, v8_filter_enabled=True, v86_new_entries_enabled=True, v89_new_entries_enabled=True, v9_filter_enabled=True, v96_filter_enabled=True, v97_filter_enabled=False, v99_new_entries_enabled=True, v912_new_entries_enabled=True, **kwargs):
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
    self.v8_filter_enabled = bool(v8_filter_enabled)
    self.v86_new_entries_enabled = bool(v86_new_entries_enabled)
    self.v89_new_entries_enabled = bool(v89_new_entries_enabled)
    self.v9_filter_enabled = bool(v9_filter_enabled)
    self.v96_filter_enabled = bool(v96_filter_enabled)
    self.v97_filter_enabled = bool(v97_filter_enabled)
    self.v99_new_entries_enabled = bool(v99_new_entries_enabled)
    self.v912_new_entries_enabled = bool(v912_new_entries_enabled)
    if self.v58_rule not in ('ATR_MOM48', 'STRICT_EARLY', 'STRICT_EARLY_ATR3'):
      raise ValueError('Invalid V5.8 rule')
    self.v57_filter_rule = str(v57_filter_rule).upper()
    if self.v57_filter_rule not in ('FLAT_TREND', 'CHOP_EXPANSION'):
      raise ValueError('Unsupported v57 filter')
    self.v52_filter_enabled = bool(v52_filter_enabled)
    self.v52_filter_rule = str(v52_filter_rule).upper()
    if self.v52_filter_rule not in ('MOMENTUM_WICK_SESSION', 'LOW_ATR_CLOSE', 'OFF'):
      raise ValueError('Invalid v52_filter_rule')
    if self.v5_filter_rule not in ('RECENT_EXTREME_CLOSE', 'TRAIN_COUNTERTREND_BODY'):
      raise ValueError('v5_filter_rule must be RECENT_EXTREME_CLOSE or TRAIN_COUNTERTREND_BODY')
    if self.same_bar_priority not in ('V35', 'V431B'):
      raise ValueError('same_bar_priority must be V35 or V431B')
    if self.conflict_policy not in ('SKIP', 'PRIORITY'):
      raise ValueError('conflict_policy must be SKIP or PRIORITY')
    self._stats = {}

  def generate(self):
    raw = self.df.copy().reset_index(drop=True)
    need = ['Date', 'Open', 'High', 'Low', 'Close']
    if any((k not in raw.columns for k in need)):
      raise ValueError('Requires Date Open High Low Close columns')
    raw['Date'] = pd.to_datetime(raw.Date)
    if raw.Date.isna().any() or raw.Date.duplicated().any() or (not raw.Date.is_monotonic_increasing):
      raise ValueError('Input timestamps must be increasing, non-null and unique')
    for k in ('Open', 'High', 'Low', 'Close'):
      raw[k] = pd.to_numeric(raw[k], errors='raise')
      if not np.isfinite(raw[k].to_numpy(dtype=float)).all():
        raise ValueError('Nonfinite OHLC candle')
    # Authorized live hybrid may inject the exact V3.5 signal ledger already
    # advanced by the retained V3.5 state machine. Standalone/replay calls
    # with no cache use the unmodified original calculation.
    hor = getattr(self, "_v932_cached_hor_history", None)
    if hor is None:
      hor = XAUUSD5MSupplyDemandRejectionV35CandidateA(raw).generate()
    elif len(hor) != len(raw) or not pd.DatetimeIndex(hor['Date']).equals(pd.DatetimeIndex(raw['Date'])):
      raise RuntimeError("V932_PRECOMPUTED_SOURCE_CANDLE_MISMATCH")
    if not hasattr(self, "_v932_original_hor_history"):
      self._v932_original_hor_history = hor
    tr = V431_RESEARCH_ONLY(raw).generate()

    def align(f):
      k = f[['Date', 'Position', 'strategy_stop_loss', 'strategy_target', 'signal_reason']].copy()
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
    _span = np.maximum(_h - _l, 1e-09)
    _body_ratio = np.abs(_c - _o) / _span
    _prev = raw['Close'].shift(1)
    _tr = pd.concat([raw.High - raw.Low, (raw.High - _prev).abs(), (raw.Low - _prev).abs()], axis=1).max(axis=1)
    _atr14 = _tr.rolling(14, min_periods=14).mean().to_numpy(dtype=float)
    _ma20 = raw['Close'].rolling(20, min_periods=20).mean().to_numpy(dtype=float)
    _momentum20 = raw['Close'].shift(19).to_numpy(dtype=float)
    _momentum12 = raw['Close'].shift(12).to_numpy(dtype=float)
    _median_prior_atr = pd.Series(_atr14).shift(1).rolling(144, min_periods=72).median().to_numpy(dtype=float)
    _ist_entry_hour = (pd.DatetimeIndex(raw.Date) + pd.Timedelta(minutes=335)).hour.to_numpy()
    _utc_entry_hour = (pd.DatetimeIndex(raw.Date) + pd.Timedelta(minutes=5)).hour.to_numpy()
    _delta = raw.Close.diff().abs()
    _er48 = ((raw.Close - raw.Close.shift(48)).abs() / (_delta.rolling(48, min_periods=48).sum() + 1e-07)).to_numpy()
    _er20 = ((raw.Close - raw.Close.shift(20)).abs() / (_delta.rolling(20, min_periods=20).sum() + 1e-07)).to_numpy()
    _ma120 = raw.Close.rolling(120, min_periods=120).mean()
    _ma_slope = ((_ma120 - _ma120.shift(24)) / (_atr14 + 1e-07)).to_numpy()
    _atr_acc = _atr14 / (pd.Series(_atr14).shift(48).to_numpy() + 1e-07)
    _tr_expand = _tr.to_numpy() / (_tr.shift(1).rolling(48, min_periods=48).median().to_numpy() + 1e-07)
    _flip = (raw.Close.diff().apply(lambda v: 1 if v > 0 else -1 if v < 0 else 0).diff().ne(0).rolling(9).sum() / 9).to_numpy()
    _lvl = raw.High.shift(1).rolling(24, min_periods=24).max().to_numpy(dtype=float)
    _median_atr = pd.Series(_atr14).shift(1).rolling(144, min_periods=60).median().to_numpy(dtype=float)
    _sw_ok = np.zeros(N, dtype=bool)
    _sw_stop = np.full(N, np.nan)
    if N > 200:
      s = np.arange(N - 1)
      i1 = s + 1
      span_s = np.maximum(_h[s] - _l[s], 1e-09)
      wick_s = (_h[s] - np.maximum(_o[s], _c[s])) / span_s
      reg_s = _atr14[s] / np.maximum(_median_atr[s], 1e-09)
      mom_s = (_c[s] - pd.Series(_c).shift(48).to_numpy(dtype=float)[s]) / np.maximum(_atr14[s], 1e-09)
      ok = (_h[s] > _lvl[s] + 0.025 * _atr14[s]) & (_c[s] < _lvl[s]) & (_c[s] < _o[s]) & (wick_s > 0.15)
      ok &= (_c[i1] < _o[i1]) & (_c[i1] < _lvl[s]) & (_c[i1] < _l[s] + 0.6 * span_s)
      gap = raw.Date.iloc[1:].to_numpy() - raw.Date.iloc[:-1].to_numpy() == np.timedelta64(5, 'm')
      ok &= gap & np.isfinite(_lvl[s]) & np.isfinite(_atr14[s])
      if self.v58_rule == 'ATR_MOM48':
        ok &= (reg_s >= 1.05) & (mom_s <= 0)
      else:
        hour = (pd.DatetimeIndex(raw.Date) + pd.Timedelta(hours=5, minutes=30)).hour.to_numpy()[i1]
        ok &= (hour <= 8) & (reg_s >= 1.05) & ((_c[s] - _ma20[s]) / np.maximum(_atr14[s], 1e-09) <= 2.0)
        if self.v58_rule == 'STRICT_EARLY_ATR3':
          ok &= _atr14[s] >= 3.0
      sl = _h[s] + 0.1 * _atr14[s]
      r = sl - _c[i1]
      ok &= (r > 0.35 * _atr14[s]) & (r < 5.0 * _atr14[s])
      _sw_ok[i1] = ok
      _sw_stop[i1] = sl
    _eng_ok = np.zeros(N, dtype=bool)
    _eng_stop = np.full(N, np.nan)
    if self.v59_new_entries_enabled and N > 250:
      _res48 = raw.High.shift(2).rolling(48, min_periods=48).max().to_numpy(dtype=float)
      _ma240 = raw.Close.rolling(240, min_periods=240).mean().to_numpy(dtype=float)
      j = np.arange(240, N, dtype=int)
      prior = j - 1
      prior_body = np.maximum(_c[prior] - _o[prior], 1e-08)
      body = _o[j] - _c[j]
      contiguous = raw.Date.iloc[1:].to_numpy() - raw.Date.iloc[:-1].to_numpy() == np.timedelta64(5, 'm')
      valid = (_c[prior] > _o[prior]) & (body > 0) & (_o[j] >= _c[prior] - 0.35 * _atr14[j])
      valid &= (_c[j] <= _o[prior] + 0.05 * _atr14[j]) & (body / prior_body >= 0.6)
      valid &= body / np.maximum(_atr14[j], 1e-08) >= 0.15
      valid &= np.maximum(_h[j], _h[prior]) >= _res48[j] - 0.8 * _atr14[j]
      valid &= _atr14[j] / np.maximum(_median_atr[j], 1e-08) >= 1.25
      valid &= -(_c[j] - _momentum12[j]) / np.maximum(_atr14[j], 1e-08) <= -2.0
      valid &= -(_c[j] - _ma240[j]) / np.maximum(_atr14[j], 1e-08) >= 0.0
      valid &= contiguous[j - 1] & np.isfinite(_res48[j]) & np.isfinite(_ma240[j])
      stopv = np.maximum(_h[j], _h[prior]) + 0.1 * _atr14[j]
      riskv = stopv - _c[j]
      valid &= (riskv > 0.3 * _atr14[j]) & (riskv < 5.0 * _atr14[j])
      _eng_ok[j] = valid
      _eng_stop[j] = stopv
    _fvg_ok = np.zeros(N, dtype=bool)
    _fvg_stop = np.full(N, np.nan, dtype=float)
    if self.v61_fvg_new_entries_enabled and N > 200:
      _fvg_reg = _atr14 / (_tr.shift(1).rolling(72, min_periods=72).median().to_numpy(dtype=float) + 1e-09)
      _fvg_mom48 = (raw.Close - raw.Close.shift(48)).to_numpy(dtype=float) / np.maximum(_atr14, 1e-09)
      _fvg_hi24 = raw.High.shift(1).rolling(24, min_periods=24).max().to_numpy(dtype=float)
      _fvg_idx = np.arange(150, N - 1, dtype=int)
      _fvg_gap_ok = raw.Date.iloc[1:].to_numpy() - raw.Date.iloc[:-1].to_numpy() == np.timedelta64(5, 'm')
      _fvg_body = _c[_fvg_idx] - _o[_fvg_idx]
      _fvg_cond = _l[_fvg_idx] > _h[_fvg_idx - 2] + 0.02 * _atr14[_fvg_idx]
      _fvg_cond &= _fvg_body > 0.6 * _atr14[_fvg_idx]
      _fvg_cond &= (_c[_fvg_idx] > _fvg_hi24[_fvg_idx]) & (_c[_fvg_idx] > _ma20[_fvg_idx])
      _fvg_cond &= _c[_fvg_idx] - _momentum12[_fvg_idx] > 0.5 * _atr14[_fvg_idx]
      _fvg_cond &= (_fvg_mom48[_fvg_idx] < -1.0) & (_fvg_reg[_fvg_idx] >= 1.1)
      _fvg_cond &= _ist_entry_hour[_fvg_idx] < 12
      _fvg_cond &= _fvg_gap_ok[_fvg_idx - 1]
      _fvg_cond &= np.isfinite(_atr14[_fvg_idx]) & np.isfinite(_fvg_reg[_fvg_idx])
      _fvg_sl = np.minimum(np.minimum(_l[_fvg_idx], _l[_fvg_idx - 1]), _l[_fvg_idx - 2]) - 0.1 * _atr14[_fvg_idx]
      _fvg_risk = _c[_fvg_idx] - _fvg_sl
      _fvg_cond &= (_fvg_risk > 0.25 * _atr14[_fvg_idx]) & (_fvg_risk < 5.0 * _atr14[_fvg_idx])
      _fvg_ok[_fvg_idx] = _fvg_cond
      _fvg_stop[_fvg_idx] = _fvg_sl
    _fb_ok = np.zeros(N, dtype=bool)
    _fb_stop = np.full(N, np.nan, dtype=float)
    if self.v62_failed_break_new_entries_enabled and N > 200:
      _fb_res48 = raw.High.shift(1).rolling(48, min_periods=48).max().to_numpy(dtype=float)
      _fb_med = _tr.shift(1).rolling(72, min_periods=72).median().to_numpy(dtype=float)
      _fb_idx = np.arange(200, N - 1, dtype=int)
      _fb_prev = _fb_idx - 1
      _fb_upwick = (_h[_fb_idx] - np.maximum(_o[_fb_idx], _c[_fb_idx])) / _span[_fb_idx]
      _fb_reg = _atr14[_fb_idx] / np.maximum(_fb_med[_fb_idx], 1e-09)
      _fb_ma_dist = (_c[_fb_idx] - _ma20[_fb_idx]) / np.maximum(_atr14[_fb_idx], 1e-09)
      _fb_contiguous = raw.Date.iloc[1:].to_numpy() - raw.Date.iloc[:-1].to_numpy() == np.timedelta64(5, 'm')
      _fb_cond = _h[_fb_prev] > _fb_res48[_fb_prev] + 0.05 * _atr14[_fb_prev]
      _fb_cond &= _c[_fb_prev] < _fb_res48[_fb_prev]
      _fb_cond &= _c[_fb_idx] - _o[_fb_idx] < -0.35 * _atr14[_fb_idx]
      _fb_cond &= (_c[_fb_idx] < _l[_fb_prev]) & (_fb_upwick > 0.08)
      _fb_cond &= (_fb_ma_dist >= 2.0) & (_fb_reg >= 1.4) & (_ist_entry_hour[_fb_idx] < 8)
      _fb_cond &= _fb_contiguous[_fb_idx - 1] & _fb_contiguous[_fb_idx - 2]
      _fb_cond &= np.isfinite(_fb_res48[_fb_prev]) & np.isfinite(_fb_reg)
      _fb_sl = np.maximum(np.maximum(_h[_fb_idx], _h[_fb_prev]), _h[_fb_idx - 2]) + 0.1 * _atr14[_fb_idx]
      _fb_risk = _fb_sl - _c[_fb_idx]
      _fb_cond &= (_fb_risk > 0.25 * _atr14[_fb_idx]) & (_fb_risk < 5.0 * _atr14[_fb_idx])
      _fb_ok[_fb_idx] = _fb_cond
      _fb_stop[_fb_idx] = _fb_sl
    _cb_ok = np.zeros(N, dtype=bool)
    _cb_stop = np.full(N, np.nan, dtype=float)
    if self.v62_compression_long_enabled and N > 200:
      _cb_idx = np.arange(200, N - 1, dtype=int)
      _cb_prevhi48 = raw.High.shift(1).rolling(48, min_periods=48).max().to_numpy(dtype=float)
      _cb_comp = _tr.shift(1).rolling(5, min_periods=5).mean().to_numpy(dtype=float) / np.maximum(_atr14, 1e-09)
      _cb_mom = (_c - raw.Close.shift(12).to_numpy(dtype=float)) / np.maximum(_atr14, 1e-09)
      _cb_cond = (_cb_comp[_cb_idx] < 0.85) & (_c[_cb_idx] - _o[_cb_idx] > 0.55 * _atr14[_cb_idx])
      _cb_cond &= (_c[_cb_idx] > _cb_prevhi48[_cb_idx]) & (_c[_cb_idx] > _ma20[_cb_idx])
      _cb_cond &= _span[_cb_idx] / np.maximum(_atr14[_cb_idx], 1e-09) < 1.0
      _cb_cond &= (_cb_mom[_cb_idx] >= 2.0) & (_ist_entry_hour[_cb_idx] >= 20)
      _cb_cond &= np.isfinite(_cb_comp[_cb_idx]) & np.isfinite(_cb_prevhi48[_cb_idx])
      _cb_sl = np.minimum(np.minimum(_l[_cb_idx], _l[_cb_idx - 1]), _l[_cb_idx - 2]) - 0.1 * _atr14[_cb_idx]
      _cb_risk = _c[_cb_idx] - _cb_sl
      _cb_cond &= (_cb_risk > 0.25 * _atr14[_cb_idx]) & (_cb_risk < 5.0 * _atr14[_cb_idx])
      _cb_ok[_cb_idx] = _cb_cond
      _cb_stop[_cb_idx] = _cb_sl
    _v63_ok = np.zeros(N, dtype=bool)
    _v63_stop = np.full(N, np.nan, dtype=float)
    if self.v63_resist96_enabled and N > 220:
      _v63_i = np.arange(200, N - 1, dtype=int)
      _v63_p = _v63_i - 1
      _v63_res = raw.High.shift(2).rolling(96, min_periods=96).max().to_numpy(dtype=float)
      _v63_upwick = (_h[_v63_i] - np.maximum(_o[_v63_i], _c[_v63_i])) / _span[_v63_i]
      _v63_range = _span[_v63_i] / np.maximum(_atr14[_v63_i], 1e-09)
      _v63_ok_i = _h[_v63_p] > _v63_res[_v63_p] + 0.02 * _atr14[_v63_i]
      _v63_ok_i &= (_c[_v63_p] < _v63_res[_v63_p]) & (_c[_v63_i] < _o[_v63_i])
      _v63_ok_i &= (_c[_v63_i] < _l[_v63_p]) & (_v63_upwick >= 0.5)
      _v63_ok_i &= (_body_ratio[_v63_i] <= 0.63) & (_v63_range <= 1.0)
      _v63_contiguous = raw.Date.iloc[1:].to_numpy() - raw.Date.iloc[:-1].to_numpy() == np.timedelta64(5, 'm')
      _v63_ok_i &= _v63_contiguous[_v63_i - 1] & _v63_contiguous[_v63_i - 2]
      _v63_sl = np.maximum(_h[_v63_i], _h[_v63_p]) + 0.12 * _atr14[_v63_i]
      _v63_r = _v63_sl - _c[_v63_i]
      _v63_ok_i &= (_v63_r > 0.2 * _atr14[_v63_i]) & (_v63_r < 5 * _atr14[_v63_i])
      _v63_ok_i &= np.isfinite(_v63_res[_v63_p]) & np.isfinite(_atr14[_v63_i])
      _v63_ok[_v63_i] = _v63_ok_i
      _v63_stop[_v63_i] = _v63_sl
    oh = raw[['Open', 'High', 'Low', 'Close']].to_numpy(dtype=float)
    hs = pd.to_numeric(h.Position, errors='coerce').fillna(0).to_numpy(dtype=int)
    ts = pd.to_numeric(t.Position, errors='coerce').fillna(0).to_numpy(dtype=int)
    hsl = pd.to_numeric(h.strategy_stop_loss, errors='coerce').to_numpy(dtype=float)
    htp = pd.to_numeric(h.strategy_target, errors='coerce').to_numpy(dtype=float)
    tsl = pd.to_numeric(t.strategy_stop_loss, errors='coerce').to_numpy(dtype=float)
    ttp = pd.to_numeric(t.strategy_target, errors='coerce').to_numpy(dtype=float)
    hwhy = h.signal_reason.fillna('').astype(str).tolist()
    twhy = t.signal_reason.fillna('').astype(str).tolist()
    _v64_tr_ewm14 = _tr.ewm(alpha=1.0 / 14.0, adjust=False, min_periods=14).mean().to_numpy(dtype=float)
    _v64_prior288hi = raw['High'].shift(1).rolling(288, min_periods=288).max().to_numpy(dtype=float)
    _v64_prior288lo = raw['Low'].shift(1).rolling(288, min_periods=288).min().to_numpy(dtype=float)
    _v64_prev48_medtr = _tr.shift(1).rolling(48, min_periods=48).median().to_numpy(dtype=float)
    _v8_features = _v8_completed_htf_features(raw) if self.v8_filter_enabled else None
    _v86_ok, _v86_stop = _v86_highvol_short_sweep(raw) if self.v86_new_entries_enabled else (None, None)
    _v89_ok, _v89_stop = _v89_htf_break_retest_long(raw) if self.v89_new_entries_enabled else (None, None)
    _v9_features = _v9_completed_htf_veto_features(raw) if self.v9_filter_enabled else None
    _v96_features = _v96_v97_mtf_veto_features(raw) if self.v96_filter_enabled or self.v97_filter_enabled else None
    _extra99_ok, _extra99_stop = _research_v98_v99_candidates(raw, 'V99') if self.v99_new_entries_enabled else (None, None)
    _extra911_ok, _extra911_stop = _v912_m15_bos_new_long(raw) if self.v912_new_entries_enabled else (None, None)
    filled_dir = 0
    stop = 0.0
    target = 0.0
    entered_bar = -1
    pending = None
    counts = dict(v35_signals=int((hs != 0).sum()), v431b_signals=int((ts != 0).sum()), accepted=0, blocked_while_open=0, same_direction=0, opposite_conflicts=0, bad_stop_target=0, invalid_next_open=0, simulated_stop_exits=0, simulated_target_exits=0, v5_quality_vetoes=0, v52_quality_vetoes=0, v54_quality_vetoes=0, v55_quality_vetoes=0, v56_quality_vetoes=0, v57_quality_vetoes=0, v58_candidates=int(_sw_ok.sum()), v58_accepted=0, v59_candidates=int(_eng_ok.sum()), v59_accepted=0, v61_candidates=int(_fvg_ok.sum()), v61_accepted=0, v62_candidates=int(_fb_ok.sum()), v62_accepted=0, v62_compression_candidates=int(_cb_ok.sum()), v62_compression_accepted=0, v63_resist96_candidates=int(_v63_ok.sum()), v63_resist96_accepted=0, v64_weakgroup_vetoes=0, v8_candidate_vetoes=0, v86_candidates=0, v86_accepted=0, v89_candidates=0, v89_accepted=0, v9_vetoes=0, v96_vetoes=0, v97_vetoes=0, extra99_candidates=0, extra99_accepted=0, extra911_candidates=0, extra911_accepted=0)
    for i in range(N):
      open_i, high_i, low_i, close_i = oh[i]
      if pending is not None:
        sig, sl, tp = pending
        if sig * (open_i - sl) <= 0 or sig * (tp - open_i) <= 0:
          counts['invalid_next_open'] += 1
        else:
          filled_dir = sig
          stop, target = (sl, tp)
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
      a, b = (int(hs[i]), int(ts[i]))
      liq = bool(self.v58_new_entries_enabled and _sw_ok[i] and (a == 0) and (b == 0))
      engulf = bool(self.v59_new_entries_enabled and _eng_ok[i] and (a == 0) and (b == 0) and (not liq))
      fvg = bool(self.v61_fvg_new_entries_enabled and _fvg_ok[i] and (a == 0) and (b == 0) and (not liq) and (not engulf))
      fb = bool(self.v62_failed_break_new_entries_enabled and _fb_ok[i] and (a == 0) and (b == 0) and (not liq) and (not engulf) and (not fvg))
      cb = bool(self.v62_compression_long_enabled and _cb_ok[i] and (a == 0) and (b == 0) and (not liq) and (not engulf) and (not fvg) and (not fb))
      rs = bool(self.v63_resist96_enabled and _v63_ok[i] and (a == 0) and (b == 0) and (not liq) and (not engulf) and (not fvg) and (not fb) and (not cb))
      extra = bool(self.v86_new_entries_enabled and _v86_ok is not None and _v86_ok[i] and (a == 0) and (b == 0) and (not liq) and (not engulf) and (not fvg) and (not fb) and (not cb) and (not rs))
      if extra:
        counts['v86_candidates'] += 1
      extra88 = bool(self.v89_new_entries_enabled and _v89_ok is not None and _v89_ok[i] and (a == 0) and (b == 0) and (not liq) and (not engulf) and (not fvg) and (not fb) and (not cb) and (not rs) and (not extra))
      if extra88:
        counts['v89_candidates'] += 1
      extra99 = bool(self.v99_new_entries_enabled and _extra99_ok is not None and _extra99_ok[i] and (a == 0) and (b == 0) and (not liq) and (not engulf) and (not fvg) and (not fb) and (not cb) and (not rs) and (not extra) and (not extra88))
      if extra99:
        counts['extra99_candidates'] += 1
      extra911 = bool(self.v912_new_entries_enabled and _extra911_ok is not None and _extra911_ok[i] and (a == 0) and (b == 0) and (not liq) and (not engulf) and (not fvg) and (not fb) and (not cb) and (not rs) and (not extra) and (not extra88) and (not extra99))
      if extra911:
        counts['extra911_candidates'] += 1
      if a == 0 and b == 0 and (not liq) and (not engulf) and (not fvg) and (not fb) and (not cb) and (not rs) and (not extra) and (not extra88) and (not extra99) and (not extra911):
        continue
      if filled_dir != 0:
        counts['blocked_while_open'] += 1
        continue
      if a and b and (a != b):
        counts['opposite_conflicts'] += 1
        if self.conflict_policy == 'SKIP':
          continue
      confluent = a != 0 and a == b
      if confluent:
        counts['same_direction'] += 1
      if extra911:
        source = 'V912_CANDIDATE'
        sig = 1
        sl = float(_extra911_stop[i])
        tp = float(close_i + 2.0 * (close_i - sl))
      elif extra99:
        source = 'V99_CANDIDATE'
        sig = -1
        sl = float(_extra99_stop[i])
        tp = float(close_i + -1 * 2.0 * (-1 * (close_i - sl)))
      elif extra88:
        source = 'V89_HTF_BREAK_RETEST_LONG'
        sig = 1
        sl = float(_v89_stop[i])
        tp = float(close_i + 2.0 * (close_i - sl))
      elif extra:
        source = 'V86_H1VOL_SWEEP_SHORT'
        sig = -1
        sl = float(_v86_stop[i])
        tp = float(close_i - 2.0 * (sl - close_i))
      elif rs:
        source = 'RESIST96'
        sig = -1
        sl = float(_v63_stop[i])
        tp = float(close_i - 2.0 * (sl - close_i))
      elif cb:
        source = 'COMPRESS_LONG'
        sig = 1
        sl = float(_cb_stop[i])
        tp = float(close_i + 2.0 * (close_i - sl))
      elif fb:
        source = 'FAILED_BREAK48'
        sig = -1
        sl = float(_fb_stop[i])
        tp = float(close_i - 2.0 * (sl - close_i))
      elif fvg:
        source = 'BULL_FVG'
        sig = 1
        sl = float(_fvg_stop[i])
        tp = float(close_i + 2.0 * (close_i - sl))
      elif liq:
        source = 'LIQ_SWEEP'
        sig = -1
        sl = float(_sw_stop[i])
        tp = float(close_i - 2.0 * (sl - close_i))
      elif engulf:
        source = 'ENGULF_RESIST'
        sig = -1
        sl = float(_eng_stop[i])
        tp = float(close_i - 2.0 * (sl - close_i))
      else:
        if a and b:
          source = self.same_bar_priority
        elif a:
          source = 'V35'
        else:
          source = 'V431B'
        sig = a if source == 'V35' else b
        sl = float(hsl[i] if source == 'V35' else tsl[i])
        tp = float(htp[i] if source == 'V35' else ttp[i])
      if not np.isfinite(sl) or not np.isfinite(tp) or sig * (close_i - sl) <= 0 or (sig * (tp - close_i) <= 0):
        counts['bad_stop_target'] += 1
        continue
      if self.v5_filter_enabled and (not (liq or engulf or fvg or fb or cb or extra or extra88 or extra99 or extra911)) and (i >= 20) and np.isfinite(_atr14[i]) and (_atr14[i] > 0):
        _quality = (close_i - low_i) / _span[i] if sig > 0 else (high_i - close_i) / _span[i]
        _aligned_ma = sig * (close_i - _ma20[i]) / _atr14[i]
        if self.v5_filter_rule == 'RECENT_EXTREME_CLOSE':
          _veto = _quality >= 0.9 and _aligned_ma >= 0.5 and (16 <= int(_ist_entry_hour[i]) < 20)
        else:
          _flat20 = abs(close_i - _momentum20[i]) / _atr14[i]
          _veto = _body_ratio[i] >= 0.4 and _aligned_ma < 0 and (_flat20 < 1.0)
        if _veto:
          counts['v5_quality_vetoes'] += 1
          continue
      if self.v52_filter_enabled and (not (liq or engulf or fvg or fb or cb or extra or extra88 or extra99 or extra911)) and (self.v52_filter_rule != 'OFF') and (i >= 160) and np.isfinite(_atr14[i]) and (_atr14[i] > 0):
        _dir_wick = (min(open_i, close_i) - low_i if sig > 0 else high_i - max(open_i, close_i)) / _span[i]
        if self.v52_filter_rule == 'MOMENTUM_WICK_SESSION':
          _mom12 = sig * (close_i - _momentum12[i]) / _atr14[i]
          _veto52 = _dir_wick >= 0.1 and _mom12 < -1.0 and (8 <= int(_ist_entry_hour[i]) < 16)
        else:
          _reg = _atr14[i] / max(_median_prior_atr[i], 1e-09)
          _dir_close = (close_i - low_i) / _span[i] if sig > 0 else (high_i - close_i) / _span[i]
          _veto52 = _reg < 0.65 and _body_ratio[i] < 0.8 and (_dir_close >= 0.7)
        if _veto52:
          counts['v52_quality_vetoes'] += 1
          continue
      if self.v54_filter_enabled and source == 'V431B' and (i >= 160) and np.isfinite(_atr14[i]) and (_atr14[i] > 0):
        _m12_v54 = sig * (close_i - _momentum12[i]) / _atr14[i]
        if 8 <= int(_utc_entry_hour[i]) < 12 and _m12_v54 <= 0.6:
          counts['v54_quality_vetoes'] += 1
          continue
      if self.v54_filter_enabled and source == 'V35' and (i >= 160) and np.isfinite(_atr14[i]) and (_atr14[i] > 0):
        _wick54 = (min(open_i, close_i) - low_i if sig > 0 else high_i - max(open_i, close_i)) / _span[i]
        _ma54 = sig * (close_i - _ma20[i]) / _atr14[i]
        if _wick54 >= 0.33526 and _ma54 >= 0.39731:
          counts['v54_quality_vetoes'] += 1
          continue
      if self.v55_filter_enabled and source == 'V35':
        _details = str(hwhy[i])
        try:
          _age = float(_details.split('zage=')[1].split(';')[0].strip())
          _wick = float(_details.split('rwick=')[1].split(';')[0].strip())
          _disp = float(_details.split('cdisp=')[1].split(';')[0].strip())
          if _age <= 10.0 and _wick <= 0.15 and (_disp <= 0.1):
            counts['v55_quality_vetoes'] += 1
            continue
        except Exception:
          pass
      if self.v56_filter_enabled and source == 'V35':
        try:
          _disp56 = float(str(hwhy[i]).split('cdisp=')[1].split(';')[0])
          _wick56 = (min(open_i, close_i) - low_i if sig > 0 else high_i - max(open_i, close_i)) / _span[i]
          if 0.1 < _disp56 <= 0.2 and _wick56 > 0.2:
            counts['v56_quality_vetoes'] += 1
            continue
        except Exception:
          pass
      if self.v57_filter_enabled and (not (liq or engulf or fvg or fb or cb or extra or extra88 or extra99 or extra911)) and (i >= 170):
        if self.v57_filter_rule == 'FLAT_TREND':
          _v57 = _ma_slope[i] <= -1.0 and _atr_acc[i] > 0.9 and (_er48[i] <= 0.1)
        else:
          _v57 = _flip[i] > 0.67 and _er20[i] > 0.1 and (_tr_expand[i] > 1.5)
        if _v57:
          counts['v57_quality_vetoes'] += 1
          continue
      if self.v64_gate_enabled and source == 'V431B' and (i >= 301) and np.isfinite(_v64_tr_ewm14[i]) and (_v64_tr_ewm14[i] > 0) and np.isfinite(_v64_prev48_medtr[i]) and (_v64_prev48_medtr[i] > 0):
        _v64_signed36 = sig * (close_i - _c[i - 36]) / _v64_tr_ewm14[i]
        _v64_edge = (close_i - _v64_prior288lo[i] if sig > 0 else _v64_prior288hi[i] - close_i) / _v64_tr_ewm14[i]
        _v64_range = float(_tr.iat[i]) / _v64_prev48_medtr[i]
        if _v64_signed36 < 3.7492 and _v64_edge >= 11.7751 and (_v64_range < 1.2224):
          counts['v64_weakgroup_vetoes'] += 1
          continue
      if not extra and (not extra88) and (not extra911) and self.v8_filter_enabled and (_v8_features is not None) and _v8_features['10_has'][i] and _v8_features['45_has'][i]:
        if (_v8_features['10_dirpos_long'][i] if sig > 0 else _v8_features['10_dirpos_short'][i]) < 0.7403 and _v8_features['45_body'][i] < 0.14284 and ((_v8_features['10_opp_long'][i] if sig > 0 else _v8_features['10_opp_short'][i]) >= 0.19892):
          counts['v8_candidate_vetoes'] += 1
          continue
      if not extra911 and self.v9_filter_enabled and (_v9_features is not None) and (_v9_features['v91long'][i] if sig > 0 else _v9_features['v91short'][i]):
        counts['v9_vetoes'] += 1
        continue
      if not extra911 and self.v96_filter_enabled and (_v96_features is not None) and (_v96_features['v96long'][i] if sig > 0 else _v96_features['v96short'][i]):
        counts['v96_vetoes'] += 1
        continue
      if not extra911 and self.v97_filter_enabled and (_v96_features is not None) and (_v96_features['v97long'][i] if sig > 0 else _v96_features['v97short'][i]):
        counts['v97_vetoes'] += 1
        continue
      out.at[i, 'Position'] = sig
      out.at[i, 'strategy_stop_loss'] = sl
      out.at[i, 'strategy_target'] = tp
      out.at[i, 'v432_source'] = source
      out.at[i, 'v432_confluence'] = bool(confluent)
      reason = 'V63_RESIST96_REJECT_CONFIRM' if rs else 'V62_COMPRESSION_BREAK_LONG' if cb else 'V62_FAILED_BREAK48_BEAR_CONFIRM' if fb else 'V61_BULL_FVG_DISPLACEMENT_PULLBACK' if fvg else 'BEARISH_ENGULFING_RESIST48_PULLBACK' if engulf else 'RESISTANCE_LIQUIDITY_SWEEP_24_CONFIRM' if liq else hwhy[i] if source == 'V35' else twhy[i]
      if extra:
        reason = 'V86_H1_HIGH_VOLUME_RESISTANCE_SWEEP_CONFIRMED'
      if extra88:
        reason = 'V89_M5_2BAR_BREAK_RETEST_M15_H1_BULLISH_HIGH_VOLUME'
      if extra99:
        reason = 'V99_ADD_ONLY_NEW_FAMILY'
      if extra911:
        reason = 'V912_M15_BOS8_LONG_H4_ATR_VOL_BODY_RESEARCH'
      if extra:
        counts['v86_accepted'] += 1
      if extra88:
        counts['v89_accepted'] += 1
      if extra99:
        counts['extra99_accepted'] += 1
      if extra911:
        counts['extra911_accepted'] += 1
      if rs:
        counts['v63_resist96_accepted'] += 1
      if cb:
        counts['v62_compression_accepted'] += 1
      if fb:
        counts['v62_accepted'] += 1
      if fvg:
        counts['v61_accepted'] += 1
      if engulf:
        counts['v59_accepted'] += 1
      if liq:
        counts['v58_accepted'] += 1
      out.at[i, 'signal_reason'] = 'V432A_' + source + ('_CONFLUENCE' if confluent else '') + '|' + reason
      counts['accepted'] += 1
      pending = (sig, sl, tp)
    self._stats = counts
    out.attrs['strategy_diagnostics'] = dict(version='V9_11_ADD_ONLY_RESEARCH_ONLY', frozen_sources=['V3.5', 'V4.31B'], one_position=True, live_approved=False, arbitration=counts, v5_filter_rule=self.v5_filter_rule, v5_filter_enabled=self.v5_filter_enabled, v52_filter_rule=self.v52_filter_rule, v52_filter_enabled=self.v52_filter_enabled, v54_filter_enabled=self.v54_filter_enabled, v55_filter_enabled=self.v55_filter_enabled, v56_filter_enabled=self.v56_filter_enabled, v57_filter_enabled=self.v57_filter_enabled, v57_filter_rule=self.v57_filter_rule, v58_new_entries_enabled=self.v58_new_entries_enabled, v58_rule=self.v58_rule, v59_new_entries_enabled=self.v59_new_entries_enabled, v61_fvg_new_entries_enabled=self.v61_fvg_new_entries_enabled, v62_failed_break_new_entries_enabled=self.v62_failed_break_new_entries_enabled, v62_compression_long_enabled=self.v62_compression_long_enabled, v63_resist96_enabled=self.v63_resist96_enabled, v64_gate_enabled=self.v64_gate_enabled, v8_filter_enabled=self.v8_filter_enabled, v86_new_entries_enabled=self.v86_new_entries_enabled, v89_new_entries_enabled=self.v89_new_entries_enabled, v9_filter_enabled=self.v9_filter_enabled, v96_filter_enabled=self.v96_filter_enabled, v97_filter_enabled=self.v97_filter_enabled, v99_new_entries_enabled=self.v99_new_entries_enabled, v912_new_entries_enabled=self.v912_new_entries_enabled, caution='Both source engines run standalone; source self-suppression and execution differences need full replay parity')
    return out
Strategy = AlgoAgentX_V62_NewEntries_RESEARCH_ONLY
_VETO_VERSION = 'v914'

def _v913_v914_causal_masks(raw):
  import numpy as _np, pandas as _pd
  dates = _pd.DatetimeIndex(_pd.to_datetime(raw['Date']))
  decision = (dates + _pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
  oo = raw['Open'].to_numpy(dtype=float)
  hh = raw['High'].to_numpy(dtype=float)
  ll = raw['Low'].to_numpy(dtype=float)
  cc = raw['Close'].to_numpy(dtype=float)
  previous = _np.r_[cc[0], cc[:-1]]
  tr = _np.maximum.reduce([hh - ll, _np.abs(hh - previous), _np.abs(ll - previous)])
  atr = _pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(dtype=float)
  n = len(raw)
  out = {key: _np.full(n, _np.nan) for key in ('m10_trend', 'm15_break_long', 'm15_break_short', 'm30_rangepos', 'h1_body', 'h4_close_long', 'h4_close_short', 'h4_trend')}
  work = raw[['Date', 'Open', 'High', 'Low', 'Close']].copy()
  work['Date'] = dates
  work = work.set_index('Date')
  for minutes in (10, 15, 30, 60, 240):
    group = work.resample(str(minutes) + 'min', closed='left', label='left')
    frame = group.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    frame = frame.loc[group['Close'].count() == minutes // 5]
    if frame.empty:
      continue
    end = (frame.index + _pd.Timedelta(minutes=minutes)).to_numpy(dtype='datetime64[ns]')
    ix = _np.searchsorted(end, decision, side='right') - 1
    valid = ix >= 0
    ix = _np.maximum(ix, 0)
    h = frame['High'].to_numpy(float)
    l = frame['Low'].to_numpy(float)
    c = frame['Close'].to_numpy(float)
    o = frame['Open'].to_numpy(float)
    span = _np.maximum(h[ix] - l[ix], 1e-10)
    if minutes == 10:
      d = c - _pd.Series(c).shift(3).to_numpy(float)
      out['m10_trend'] = _np.where(valid, d[ix] / _np.maximum(atr, 1e-10), _np.nan)
    if minutes == 15:
      priorhi = _pd.Series(h).shift(1).rolling(8, min_periods=8).max().to_numpy(float)
      priorlo = _pd.Series(l).shift(1).rolling(8, min_periods=8).min().to_numpy(float)
      out['m15_break_long'] = _np.where(valid, (c[ix] - priorhi[ix]) / _np.maximum(atr, 1e-10), _np.nan)
      out['m15_break_short'] = _np.where(valid, (priorlo[ix] - c[ix]) / _np.maximum(atr, 1e-10), _np.nan)
    if minutes == 30:
      priorhi = _pd.Series(h).shift(1).rolling(8, min_periods=8).max().to_numpy(float)
      priorlo = _pd.Series(l).shift(1).rolling(8, min_periods=8).min().to_numpy(float)
      out['m30_rangepos'] = _np.where(valid, (c[ix] - priorlo[ix]) / _np.maximum(priorhi[ix] - priorlo[ix], 1e-10), _np.nan)
    if minutes == 60:
      out['h1_body'] = _np.where(valid, _np.abs(c[ix] - o[ix]) / span, _np.nan)
    if minutes == 240:
      out['h4_close_long'] = _np.where(valid, (c[ix] - l[ix]) / span, _np.nan)
      out['h4_close_short'] = _np.where(valid, (h[ix] - c[ix]) / span, _np.nan)
      d = c - _pd.Series(c).shift(3).to_numpy(float)
      out['h4_trend'] = _np.where(valid, d[ix] / _np.maximum(atr, 1e-10), _np.nan)
  mask13_long = (out['m10_trend'] < -1.73436) & (out['m15_break_long'] >= -4.42234) & (out['m30_rangepos'] >= 0.69293)
  mask13_short = (-out['m10_trend'] < -1.73436) & (out['m15_break_short'] >= -4.42234) & (out['m30_rangepos'] >= 0.69293)
  mask14_long = (out['h1_body'] < 0.45312) & (out['h4_close_long'] < 0.29714) & (out['h4_trend'] >= 2.5995)
  mask14_short = (out['h1_body'] < 0.45312) & (out['h4_close_short'] < 0.29714) & (-out['h4_trend'] >= 2.5995)
  return {'v913_long': mask13_long, 'v913_short': mask13_short, 'v914_long': mask14_long, 'v914_short': mask14_short}

class AlgoAgentX_Filter_Research_ONLY(AlgoAgentX_V62_NewEntries_RESEARCH_ONLY):

  def __init__(self, df, filter_enabled=True, **kwargs):
    self._research_filter_enabled = bool(filter_enabled)
    super().__init__(df, **kwargs)

  def generate(self):
    result = super().generate()
    if not self._research_filter_enabled:
      return result
    gates = _v913_v914_causal_masks(self.df.copy().reset_index(drop=True))
    positions = result['Position'].to_numpy(dtype=int)
    long_mask = gates[_VETO_VERSION + '_long']
    short_mask = gates[_VETO_VERSION + '_short']
    veto = (positions == 1) & long_mask | (positions == -1) & short_mask
    if veto.any():
      result.loc[veto, 'Position'] = 0
      result.loc[veto, 'strategy_stop_loss'] = float('nan')
      result.loc[veto, 'strategy_target'] = float('nan')
      result.loc[veto, 'signal_reason'] = ''
      if 'v432_source' in result.columns:
        result.loc[veto, 'v432_source'] = ''
      if 'v432_confluence' in result.columns:
        result.loc[veto, 'v432_confluence'] = False
    diag = dict(result.attrs.get('strategy_diagnostics', {}))
    diag.update(research_filter=_VETO_VERSION, filter_only=True, filter_vetoed_signal_rows=int(veto.sum()), live_approved=False)
    result.attrs['strategy_diagnostics'] = diag
    return result
Strategy = AlgoAgentX_Filter_Research_ONLY

def _new_v915_16(raw, version):
  import numpy as np, pandas as pd
  d = pd.DatetimeIndex(pd.to_datetime(raw.Date))
  t = d.to_numpy('datetime64[ns]')
  dec = t + np.timedelta64(5, 'm')
  o = raw.Open.to_numpy(float)
  h = raw.High.to_numpy(float)
  l = raw.Low.to_numpy(float)
  c = raw.Close.to_numpy(float)
  v = raw.Volume.to_numpy(float)
  pr = np.r_[c[0], c[:-1]]
  tr = np.maximum.reduce([h - l, abs(h - pr), abs(l - pr)])
  atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().to_numpy(float)
  vol = v / np.maximum(pd.Series(v).shift(1).rolling(48, min_periods=48).mean().to_numpy(float), 1.0)
  reg = atr / np.maximum(pd.Series(atr).shift(1).rolling(288, min_periods=144).median().to_numpy(float), 0.001)
  span = np.maximum(h - l, 1e-06)
  valid = np.r_[np.diff(t) == np.timedelta64(5, 'm'), False]
  tab = raw.set_index(d)

  def htf(mins):
    g = tab.resample(str(mins) + 'min', label='left', closed='left')
    x = g.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    x = x.loc[g.Close.count().eq(mins // 5)]
    end = (x.index + pd.Timedelta(minutes=mins)).to_numpy('datetime64[ns]')
    j = np.searchsorted(end, dec, side='right') - 1
    ok = j >= 0
    j = np.maximum(j, 0)
    return (x, j, ok, end[j] == dec)
  if version == 15:
    x, j, ok, fresh = htf(45)
    change = x.Close.diff()
    up = change.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-change.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    hrsi = (100 - 100 / (1 + up / np.maximum(dn, 1e-07))).to_numpy(float)[j]
    delta = pd.Series(c).diff()
    u = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    n = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = (100 - 100 / (1 + u / np.maximum(n, 1e-07))).to_numpy(float)
    good = ok & fresh & (hrsi >= 30) & (hrsi <= 45) & (c > o) & ((c - l) / span > 0.6) & (reg >= 0.8) & (reg <= 1.25) & (vol >= 1.25) & (rsi >= 52)
    side = 1
    stop = pd.Series(l).rolling(7, min_periods=7).min().to_numpy(float) - 0.2 * atr
  else:
    x, j, ok, fresh = htf(15)
    mid = x.Close.shift(1).rolling(20, min_periods=20).mean().to_numpy(float)[j]
    std = x.Close.shift(1).rolling(20, min_periods=20).std().to_numpy(float)[j]
    top = x.High.to_numpy(float)[j]
    cl = x.Close.to_numpy(float)[j]
    y, k, kok, _ = htf(240)
    ema = y.Close.ewm(span=20, adjust=False).mean().to_numpy(float)[k]
    hc = y.Close.to_numpy(float)[k]
    good = ok & fresh & kok & (top > mid + 2 * std) & (cl < mid + std) & (c < o) & ((h - c) / span > 0.6) & ((ema - hc) / np.maximum(atr, 0.01) >= 0.25) & (reg >= 1.1) & (abs(c - o) / span >= 0.7)
    side = -1
    stop = pd.Series(h).rolling(7, min_periods=7).max().to_numpy(float) + 0.2 * atr
  risk = side * (c - stop) / np.maximum(atr, 1e-09)
  good &= valid & np.isfinite(atr) & np.isfinite(stop) & (risk >= 0.4) & (risk <= 5)
  return (good, stop, side)

class V917_AddOnly_RESEARCH(AlgoAgentX_Filter_Research_ONLY):

  def __init__(self, df, new_entries_enabled=True, **kw):
    self._new_enabled = bool(new_entries_enabled)
    super().__init__(df, **kw)

  def generate(self):
    f = super().generate()
    if not self._new_enabled:
      return f
    raw = self.df
    c = raw.Close.to_numpy(float)
    for v in (15, 16):
      mask, sl, side = _new_v915_16(raw, v)
      a = mask & (f.Position.to_numpy(dtype=int) == 0)
      f.loc[a, 'Position'] = side
      f.loc[a, 'strategy_stop_loss'] = sl[a]
      f.loc[a, 'strategy_target'] = c[a] + side * 2 * abs(c[a] - sl[a])
      f.loc[a, 'signal_reason'] = 'V9.' + str(v) + '_NEW_' + ('LONG' if side == 1 else 'SHORT')
    return f
Strategy = V917_AddOnly_RESEARCH

def _v918_veto(raw, position):
  import numpy as np, pandas as pd
  ts = pd.DatetimeIndex(pd.to_datetime(raw['Date']))
  decision = (ts + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
  tab = raw.set_index(ts)
  p = np.asarray(position, dtype=int)

  def completed(mins):
    g = tab.resample(str(mins) + 'min', closed='left', label='left')
    x = g.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    x = x.loc[g['Close'].count().eq(mins // 5)]
    finish = (x.index + pd.Timedelta(minutes=mins)).to_numpy(dtype='datetime64[ns]')
    ix = np.searchsorted(finish, decision, side='right') - 1
    valid = ix >= 0
    ix = np.maximum(ix, 0)
    return (x, ix, valid)
  a, i, va = completed(10)
  b, j, vb = completed(240)
  ac = a.Close.to_numpy(float)[i]
  ah = a.High.to_numpy(float)[i]
  al = a.Low.to_numpy(float)[i]
  ao = a.Open.to_numpy(float)[i]
  bh = b.High.to_numpy(float)[j]
  bl = b.Low.to_numpy(float)[j]
  bc = b.Close.to_numpy(float)[j]
  span = np.maximum(ah - al, 0.001)
  hspan = np.maximum(bh - bl, 0.001)
  m10dir = np.where(p == 1, (ac - al) / span, (ah - ac) / span)
  h4dir = np.where(p == 1, (bc - bl) / hspan, (bh - bc) / hspan)
  body = np.abs(ac - ao) / span
  return va & vb & (p != 0) & (m10dir >= 0.971919) & (h4dir < 0.19731) & (body >= 0.44843)

class V918_FilterOnly_RESEARCH(V917_AddOnly_RESEARCH):

  def __init__(self, df, filter_enabled=True, **kwargs):
    self._v918_filter_enabled = bool(filter_enabled)
    super().__init__(df, **kwargs)

  def generate(self):
    out = super().generate()
    if not self._v918_filter_enabled:
      return out
    mask = _v918_veto(self.df, out['Position'].to_numpy())
    if mask.any():
      out.loc[mask, 'Position'] = 0
      out.loc[mask, 'strategy_stop_loss'] = float('nan')
      out.loc[mask, 'strategy_target'] = float('nan')
      out.loc[mask, 'signal_reason'] = ''
    return out
Strategy = V918_FilterOnly_RESEARCH

def _weak_mtf_ema_veto(df, pos, variant):
  import numpy as np, pandas as pd
  ts = pd.DatetimeIndex(pd.to_datetime(df['Date']))
  decision = (ts + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
  tab = df.set_index(ts)
  p = np.asarray(pos, dtype=int)
  result = {}
  for minutes, name, n in ((45, 'm45', 26), (60, 'h1', 12), (240, 'h4', 12)):
    g = tab.resample(str(minutes) + 'min', closed='left', label='left')
    a = g.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    a = a.loc[g['Close'].count().eq(minutes // 5)]
    finish = (a.index + pd.Timedelta(minutes=minutes)).to_numpy(dtype='datetime64[ns]')
    ids = np.searchsorted(finish, decision, side='right') - 1
    valid = ids >= 0
    ids = np.maximum(ids, 0)
    close = a.Close.to_numpy(dtype=float)
    ran = np.maximum((a.High - a.Low).to_numpy(dtype=float), 0.001)
    avg = pd.Series(ran).rolling(14, min_periods=14).mean().to_numpy(dtype=float)
    ema = pd.Series(close).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy(dtype=float)
    dist = ((close - ema) / np.maximum(avg, 0.01))[ids] * p
    dist[~valid] = np.nan
    result[name] = dist
  if variant == 919:
    return (p != 0) & (result['m45'] >= 0.2687062011639503) & (result['h1'] < -0.1356366079397278) & (result['h4'] < 1.2377361540875762)
  g = tab.resample('240min', closed='left', label='left')
  h = g.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
  h = h.loc[g['Close'].count().eq(48)]
  finish = (h.index + pd.Timedelta(minutes=240)).to_numpy(dtype='datetime64[ns]')
  ix = np.searchsorted(finish, decision, side='right') - 1
  valid = ix >= 0
  ix = np.maximum(ix, 0)
  hi = pd.Series(h.High.to_numpy(float)).shift(1).rolling(12, min_periods=12).max().to_numpy(float)[ix]
  lo = pd.Series(h.Low.to_numpy(float)).shift(1).rolling(12, min_periods=12).min().to_numpy(float)[ix]
  cl = h.Close.to_numpy(float)[ix]
  dir_range = np.where(p == 1, (cl - lo) / np.maximum(hi - lo, 0.001), (hi - cl) / np.maximum(hi - lo, 0.001))
  return (p != 0) & valid & (result['m45'] >= 0.2687062011639503) & (result['h1'] < -0.1356366079397278) & (dir_range < 0.9562515275304656)

class V920_FilterOnly_RESEARCH(V918_FilterOnly_RESEARCH):

  def __init__(self, df, new_filter_enabled=True, **kwargs):
    self._new_filter_enabled = bool(new_filter_enabled)
    super().__init__(df, **kwargs)

  def generate(self):
    out = super().generate()
    if not self._new_filter_enabled:
      return out
    mask = _weak_mtf_ema_veto(self.df, out['Position'].to_numpy(), 920)
    if mask.any():
      out.loc[mask, 'Position'] = 0
      out.loc[mask, 'strategy_stop_loss'] = float('nan')
      out.loc[mask, 'strategy_target'] = float('nan')
      out.loc[mask, 'signal_reason'] = ''
    return out
Strategy = V920_FilterOnly_RESEARCH

def _v92122_weak_trade_veto(raw, position, variant):
  import numpy as np, pandas as pd
  p = np.asarray(position, dtype=int)
  ok = p != 0
  c = raw['Close'].astype(float)
  h = raw['High'].astype(float)
  l = raw['Low'].astype(float)
  if variant == 921:
    ma = c.rolling(20, min_periods=20).mean()
    sd = c.rolling(20, min_periods=20).std()
    bb = (c - ma).to_numpy(float) / np.maximum(sd.to_numpy(float), 0.01) * p
    ts = pd.DatetimeIndex(pd.to_datetime(raw['Date']))
    decision = (ts + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
    g = raw.set_index(ts).resample('60min', closed='left', label='left')
    b = g.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    b = b.loc[g['Close'].count().eq(12)]
    ends = (b.index + pd.Timedelta(minutes=60)).to_numpy(dtype='datetime64[ns]')
    i = np.searchsorted(ends, decision, side='right') - 1
    valid = i >= 0
    i = np.maximum(i, 0)
    cc = b.Close.to_numpy(float)
    hh = b.High.to_numpy(float)
    ll = b.Low.to_numpy(float)
    ran = np.maximum(hh - ll, 0.001)
    close_dir = np.where(p == 1, (cc[i] - ll[i]) / ran[i], (hh[i] - cc[i]) / ran[i])
    prior_hi = pd.Series(hh).shift(1).rolling(12, min_periods=12).max().to_numpy(float)
    prior_lo = pd.Series(ll).shift(1).rolling(12, min_periods=12).min().to_numpy(float)
    avg = pd.Series(ran).rolling(14, min_periods=14).mean().to_numpy(float)
    break_dir = np.where(p == 1, (cc[i] - prior_hi[i]) / np.maximum(avg[i], 0.01), (prior_lo[i] - cc[i]) / np.maximum(avg[i], 0.01))
    return ok & valid & np.isfinite(bb) & np.isfinite(break_dir) & (close_dir >= 0.8453302373580913) & (bb >= 2.504870877012801) & (break_dir < 0.2731052126638597)
  o = raw['Open'].astype(float)
  pr = c.shift(1)
  tr = np.maximum.reduce(((h - l).to_numpy(float), (h - pr).abs().to_numpy(float), (l - pr).abs().to_numpy(float)))
  atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
  den = np.maximum(atr.to_numpy(float), 0.01)
  moment = (c - c.shift(36)).to_numpy(float) / den * p
  up = h - h.shift(1)
  down = l.shift(1) - l
  pos = up.where((up > down) & (up > 0), 0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
  neg = down.where((down > up) & (down > 0), 0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
  di_direction = 100 * (pos - neg).to_numpy(float) / den * p
  prior_hi = h.shift(1).rolling(48, min_periods=48).max()
  sweep = (h - prior_hi).to_numpy(float) / den
  return ok & np.isfinite(moment) & np.isfinite(di_direction) & np.isfinite(sweep) & (moment < 3.3321563344075407) & (di_direction >= 18.554843223869128 - 1e-12) & (sweep >= -1.3029653957006957)

class V921_FilterOnly_RESEARCH(V920_FilterOnly_RESEARCH):

  def __init__(self, df, new_filter_enabled=True, **kwargs):
    self._v921_new_filter_enabled = bool(new_filter_enabled)
    super().__init__(df, **kwargs)

  def generate(self):
    out = super().generate()
    if not self._v921_new_filter_enabled:
      return out
    mask = _v92122_weak_trade_veto(self.df, out['Position'].to_numpy(dtype=int), 921)
    if mask.any():
      out.loc[mask, 'Position'] = 0
      out.loc[mask, 'strategy_stop_loss'] = float('nan')
      out.loc[mask, 'strategy_target'] = float('nan')
      out.loc[mask, 'signal_reason'] = ''
    return out
Strategy = V921_FilterOnly_RESEARCH

class V923_FilterOnly_RESEARCH(V920_FilterOnly_RESEARCH):

  def __init__(self, df, new_filter_enabled=True, **kwargs):
    self._v923_enabled = bool(new_filter_enabled)
    super().__init__(df, **kwargs)

  def generate(self):
    f = super().generate()
    if not self._v923_enabled:
      return f
    p = f['Position'].to_numpy(dtype=int)
    veto = _v92122_weak_trade_veto(self.df, p, 921) | _v92122_weak_trade_veto(self.df, p, 922)
    if veto.any():
      f.loc[veto, 'Position'] = 0
      f.loc[veto, 'strategy_stop_loss'] = float('nan')
      f.loc[veto, 'strategy_target'] = float('nan')
      f.loc[veto, 'signal_reason'] = ''
    return f
Strategy = V923_FilterOnly_RESEARCH
RESEARCH_VERSION = 924

def _v92425_new(raw, variant):
  import numpy as np, pandas as pd
  o = raw['Open'].to_numpy(float)
  h = raw['High'].to_numpy(float)
  l = raw['Low'].to_numpy(float)
  c = raw['Close'].to_numpy(float)
  v = raw['Volume'].to_numpy(float)
  C = pd.Series(c)
  H = pd.Series(h)
  ts = pd.DatetimeIndex(pd.to_datetime(raw['Date']))
  tr = np.maximum.reduce((h - l, np.abs(h - np.r_[np.nan, c[:-1]]), np.abs(l - np.r_[np.nan, c[:-1]])))
  atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().to_numpy(float)
  reg = atr / np.maximum(pd.Series(atr).shift(1).rolling(288, min_periods=100).median().to_numpy(float), 0.01)
  vol = v / np.maximum(pd.Series(v).shift(1).rolling(24, min_periods=18).mean().to_numpy(float), 1.0)
  d = C.diff()
  u = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
  dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
  rsi = (100 - 100 / (1 + u / np.maximum(dn, 1e-05))).to_numpy(float)
  body = np.abs(c - o) / np.maximum(h - l, 0.001)
  dec = (ts + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')

  def closed(minutes):
    g = raw.set_index(ts).resample(str(minutes) + 'min', closed='left', label='left')
    x = g.agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    x = x.loc[g['Close'].count().eq(minutes // 5)]
    idx = np.searchsorted((x.index + pd.Timedelta(minutes=minutes)).to_numpy(dtype='datetime64[ns]'), dec, side='right') - 1
    valid = idx >= 0
    idx = np.maximum(idx, 0)
    cl = x.Close.to_numpy(float)
    ema20 = pd.Series(cl).ewm(span=20, adjust=False, min_periods=20).mean().to_numpy(float)
    ema50 = pd.Series(cl).ewm(span=50, adjust=False, min_periods=50).mean().to_numpy(float)
    return {'trend': np.sign(ema20[idx] - ema50[idx]), 'last': cl[idx], 'ema20': ema20[idx], 'previous': np.r_[np.nan, cl[:-1]][idx], 'prevema': np.r_[np.nan, ema20[:-1]][idx], 'fresh': valid & np.r_[False, idx[1:] != idx[:-1]]}
  m15 = closed(15)
  pos = np.zeros(len(c), dtype=np.int8)
  if variant in (924, 926):
    priorhi = H.shift(1).rolling(48, min_periods=48).max().to_numpy(float)
    mask = (h > priorhi) & (c < priorhi) & (c < o) & (body >= 0.15) & (vol >= 1.0) & (reg >= 1.15) & (m15['trend'] == -1) & (ts.hour >= 12) & (ts.hour < 17) & (rsi <= 65)
    pos[mask] = -1
  if variant in (925, 926):
    h1 = closed(60)
    mask = m15['fresh'] & (m15['last'] > m15['ema20']) & (m15['previous'] <= m15['prevema']) & (c > o) & (body >= 0.15) & (vol >= 1.0) & (reg >= 0.9) & (h1['trend'] == 1) & (ts.hour >= 0) & (ts.hour < 8) & (rsi >= 55)
    pos[mask & (pos == 0)] = 1
  pos[~np.isfinite(atr)] = 0
  return (pos, atr)

class V92425_AddOnly_RESEARCH(V923_FilterOnly_RESEARCH):

  def __init__(self, df, new_entries_enabled=True, **kwargs):
    self._v92425_enabled = bool(new_entries_enabled)
    super().__init__(df, **kwargs)

  def generate(self):
    frame = super().generate()
    if not self._v92425_enabled:
      return frame
    new, atr = _v92425_new(self.df, RESEARCH_VERSION)
    c = self.df['Close'].to_numpy(float)
    old = frame['Position'].to_numpy(dtype=int)
    import numpy as np
    for i in np.flatnonzero((new != 0) & (old == 0)):
      sig = int(new[i])
      sl = c[i] - sig * 1.4 * atr[i]
      tp = c[i] + sig * 2.8 * atr[i]
      if not np.isfinite(sl) or not np.isfinite(tp) or sig * (c[i] - sl) <= 0.1:
        continue
      frame.at[i, 'Position'] = sig
      frame.at[i, 'strategy_stop_loss'] = sl
      frame.at[i, 'strategy_target'] = tp
      frame.at[i, 'signal_reason'] = 'V924_NEW_M5_SWEEP48_SHORT' if sig < 0 else 'V925_NEW_M15_EMA_RECLAIM_LONG'
    return frame
Strategy = V92425_AddOnly_RESEARCH

# FILTER_EXISTING_LOSING_TRADES_ONLY. Original V9.24 strategy above has identical Python AST.
def _v92728_weak_veto(df, position, variant):
 import numpy as np, pandas as pd
 p=np.asarray(position,dtype=int)
 ts=pd.DatetimeIndex(pd.to_datetime(df['Date']))
 dec=(ts+pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
 h=df['High'].to_numpy(float);l=df['Low'].to_numpy(float);c=df['Close'].to_numpy(float)
 def closed(minutes):
  g=df.set_index(ts).resample(str(minutes)+'min',closed='left',label='left')
  b=g.agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
  b=b.loc[g['Close'].count().eq(minutes//5)]
  ix=np.searchsorted((b.index+pd.Timedelta(minutes=minutes)).to_numpy(dtype='datetime64[ns]'),dec,side='right')-1
  valid=ix>=0;ix=np.maximum(ix,0)
  cc=b.Close.to_numpy(float);hh=b.High.to_numpy(float);ll=b.Low.to_numpy(float)
  high=pd.Series(hh).shift(1).rolling(12,min_periods=12).max().to_numpy(float)
  low=pd.Series(ll).shift(1).rolling(12,min_periods=12).min().to_numpy(float)
  ran=np.maximum(high[ix]-low[ix],.001)
  range_dir=np.where(p==1,(cc[ix]-low[ix])/ran,(high[ix]-cc[ix])/ran)
  return b,ix,valid,cc,high,low,range_dir
 b10,i10,valid10,cl10,hi10,lo10,r10=closed(10)
 if variant==927:
  v=b10.Volume.to_numpy(float)
  vol=(v/np.maximum(pd.Series(v).shift(1).rolling(12,min_periods=12).mean().to_numpy(float),1.))[i10]
  b30,i30,valid30,cl30,hi30,lo30,r30=closed(30)
  return (p!=0)&valid10&valid30&(vol<1.6178046020369672)&(r10< -0.0910240202275834)&(r30>=0.1862780593772995)
 b15,i15,valid15,cl15,hi15,lo15,r15=closed(15)
 tr=np.maximum.reduce((h-l,np.abs(h-np.r_[c[0],c[:-1]]),np.abs(l-np.r_[c[0],c[:-1]])))
 atr=pd.Series(tr).ewm(alpha=1/14,adjust=False,min_periods=14).mean().to_numpy(float)
 scale=np.maximum(pd.Series((b10.High-b10.Low).to_numpy(float)).rolling(14,min_periods=14).mean().to_numpy(float)[i10],.01)
 br=np.where(p==1,(cl10[i10]-hi10[i10])/scale,(lo10[i10]-cl10[i10])/scale)
 m8=(cl15[i15]-pd.Series(cl15).shift(8).to_numpy(float)[i15])/np.maximum(atr,.01)*p
 m20=(cl15[i15]-pd.Series(cl15).shift(20).to_numpy(float)[i15])/np.maximum(atr,.01)*p
 return (p!=0)&valid10&valid15&(br < -4.23762827822119)&(m8>= -2.777986641574124)&(m20>= -2.4493372036456)

class V927_FilterOnly_Research(V92425_AddOnly_RESEARCH):
 def __init__(self,df,new_filter_enabled=True,**kwargs):
  self._v927_filter_enabled=bool(new_filter_enabled)
  super().__init__(df,**kwargs)
 def generate(self):
  frame=super().generate()
  if not self._v927_filter_enabled:return frame
  mask=_v92728_weak_veto(self.df,frame['Position'].to_numpy(dtype=int),927)
  if mask.any():
   frame.loc[mask,'Position']=0
   frame.loc[mask,'strategy_stop_loss']=float('nan')
   frame.loc[mask,'strategy_target']=float('nan')
   frame.loc[mask,'signal_reason']=''
  return frame
Strategy=V927_FilterOnly_Research

class V929_Combined_Filter_Research(V92425_AddOnly_RESEARCH):
 def __init__(self,df,new_filter_enabled=True,**kwargs):
  self._v929_filter_enabled=bool(new_filter_enabled)
  super().__init__(df,**kwargs)
 def generate(self):
  frame=super().generate()
  if not self._v929_filter_enabled:return frame
  import numpy as np
  p=frame['Position'].to_numpy(dtype=int)
  mask=_v92728_weak_veto(self.df,p,927)|_v92728_weak_veto(self.df,p,928)
  if mask.any():
   frame.loc[mask,'Position']=0
   frame.loc[mask,'strategy_stop_loss']=float('nan')
   frame.loc[mask,'strategy_target']=float('nan')
   frame.loc[mask,'signal_reason']=''
  return frame
Strategy=V929_Combined_Filter_Research

# Filter-only addition to frozen V9.29. No baseline entry or execution rules modified.
def _v93031_filter(df, position, version):
 import numpy as np, pandas as pd
 p=np.asarray(position,dtype=int)
 ts=pd.DatetimeIndex(pd.to_datetime(df['Date']))
 decision=(ts+pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
 o=df['Open'].to_numpy(float);h=df['High'].to_numpy(float);l=df['Low'].to_numpy(float);c=df['Close'].to_numpy(float)
 prev=np.r_[c[0],c[:-1]]
 tr=np.maximum.reduce((h-l,np.abs(h-prev),np.abs(l-prev)))
 atr=pd.Series(tr).ewm(alpha=1/14,adjust=False,min_periods=14).mean().to_numpy(float)
 d=df.set_index(ts)
 def closed(minutes):
  g=d.resample(str(minutes)+'min',closed='left',label='left')
  b=g.agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
  b=b.loc[g['Close'].count().eq(minutes//5)]
  last=np.searchsorted((b.index+pd.Timedelta(minutes=minutes)).to_numpy(dtype='datetime64[ns]'),decision,side='right')-1
  ok=last>=0
  return b,np.maximum(last,0),ok
 b45,i45,ok45=closed(45)
 v45=b45.Volume.to_numpy(float)
 avg45=pd.Series(v45).shift(1).rolling(12,min_periods=12).mean().to_numpy(float)
 vol45=v45[i45]/np.maximum(avg45[i45],1.)
 b4,i4,ok4=closed(240)
 c4=b4.Close.to_numpy(float)
 mom4=(c4-pd.Series(c4).shift(3).to_numpy(float))[i4]/np.maximum(atr,.01)*p
 b10,i10,ok10=closed(10)
 c10=b10.Close.to_numpy(float);h10=b10.High.to_numpy(float);l10=b10.Low.to_numpy(float)
 high=pd.Series(h10).shift(1).rolling(12,min_periods=12).max().to_numpy(float)
 low=pd.Series(l10).shift(1).rolling(12,min_periods=12).min().to_numpy(float)
 if version==930:
  rng=np.maximum(high[i10]-low[i10],.001)
  third=np.where(p==1,(c10[i10]-low[i10])/rng,(high[i10]-c10[i10])/rng)<0.9000625726289727
 else:
  denom=pd.Series(np.maximum(h10-l10,.001)).rolling(14,min_periods=14).mean().to_numpy(float)[i10]
  third=np.where(p==1,(c10[i10]-high[i10])/np.maximum(denom,.01),(low[i10]-c10[i10])/np.maximum(denom,.01))< -0.33337296536807404
 return (p!=0)&ok45&ok4&ok10&(vol45>=1.2251503717131889)&(mom4< -13.038226831175798)&third

class V930_FilterOnly_Research(V929_Combined_Filter_Research):
 def __init__(self,df,additional_filter_enabled=True,**kwargs):
  self._v930_enabled=bool(additional_filter_enabled)
  super().__init__(df,**kwargs)
 def generate(self):
  frame=super().generate()
  if not self._v930_enabled:return frame
  mask=_v93031_filter(self.df,frame['Position'].to_numpy(dtype=int),930)
  if mask.any():
   frame.loc[mask,'Position']=0
   frame.loc[mask,'strategy_stop_loss']=float('nan')
   frame.loc[mask,'strategy_target']=float('nan')
   frame.loc[mask,'signal_reason']=''
  return frame
Strategy=V930_FilterOnly_Research

# ADDITIONAL RESEARCH VETO ONLY. Frozen V9.30 definitions above are unmodified.
def _v932_candidate_filter(df, baseline_positions, version):
 import numpy as np
 import pandas as pd
 p=np.asarray(baseline_positions,dtype=int)
 dates=pd.DatetimeIndex(pd.to_datetime(df['Date']))
 decision=(dates+pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
 d=df.set_index(dates)
 def closed(minutes):
  g=d.resample(str(minutes)+'min',closed='left',label='left')
  b=g.agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
  b=b.loc[g['Close'].count().eq(minutes//5)]
  idx=np.searchsorted((b.index+pd.Timedelta(minutes=minutes)).to_numpy(dtype='datetime64[ns]'),decision,side='right')-1
  ok=idx>=0
  return b,np.maximum(idx,0),ok
 b15,i15,ok15=closed(15);b45,i45,ok45=closed(45)
 v15=b15.Volume.to_numpy(float);v45=b45.Volume.to_numpy(float)
 av15=pd.Series(v15).shift(1).rolling(12,min_periods=12).mean().to_numpy(float)
 av45=pd.Series(v45).shift(1).rolling(12,min_periods=12).mean().to_numpy(float)
 vol15=v15[i15]/np.maximum(av15[i15],1.)
 vol45=v45[i45]/np.maximum(av45[i45],1.)
 if version==932:
  cl45=b45.Close.to_numpy(float)
  oo=cl45-pd.Series(cl45).shift(8).to_numpy(float)
  h=df['High'].to_numpy(float);l=df['Low'].to_numpy(float);c=df['Close'].to_numpy(float)
  prev=np.r_[c[0],c[:-1]]
  tr=np.maximum.reduce((h-l,np.abs(h-prev),np.abs(l-prev)))
  atr=pd.Series(tr).ewm(alpha=1/14,adjust=False,min_periods=14).mean().to_numpy(float)
  third=(oo[i45]*p/np.maximum(atr,.01))>=-0.3269843529569886
 else:
  c=df['Close'].to_numpy(float);h=df['High'].to_numpy(float);l=df['Low'].to_numpy(float)
  prev=np.r_[c[0],c[:-1]]
  tr=np.maximum.reduce((h-l,np.abs(h-prev),np.abs(l-prev)))
  atr=pd.Series(tr).ewm(alpha=1/14,adjust=False,min_periods=14).mean().to_numpy(float)
  m36=(c-pd.Series(c).shift(36).to_numpy(float))*p/np.maximum(atr,.01)
  third=m36>=-3.5274670175769964
 return (p!=0)&ok15&ok45&(vol15>=2.377603288295051)&(vol45<1.3142245960273808)&third

class V932_FilterOnly_Research(V930_FilterOnly_Research):
 def __init__(self,df,additional_filter_enabled=True,**kwargs):
  self._v932_enabled=bool(additional_filter_enabled)
  super().__init__(df,**kwargs)
 def generate(self):
  frame=super().generate()
  if not self._v932_enabled:return frame
  mask=_v932_candidate_filter(self.df,frame['Position'].to_numpy(dtype=int),932)
  if mask.any():
   frame.loc[mask,'Position']=0
   frame.loc[mask,'strategy_stop_loss']=float('nan')
   frame.loc[mask,'strategy_target']=float('nan')
   frame.loc[mask,'signal_reason']=''
  return frame
Strategy=V932_FilterOnly_Research
