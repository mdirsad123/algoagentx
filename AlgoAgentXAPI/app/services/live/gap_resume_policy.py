"""Pure operator opt-in policy for long broker-observed DEMO M5 discontinuities.

It is *not* a broker-session calendar and cannot prove whether a historical
bar should have existed. A recovered gap always requires full cold re-seeding
and a broker-order-suppressed baseline evaluation before trading resumes.
"""
from __future__ import annotations


def eligible_for_demo_cold_reseed(*, mode: str, enabled: bool, timeframe_seconds: int,
                                  missing_slots: int, min_missing_slots: int,
                                  attempts: int, successful_refetches: int,
                                  broker_source_verified: bool,
                                  last_two_broker_bars_consecutive: bool) -> bool:
    return (
        mode.upper() == 'DEMO'
        and enabled is True
        and timeframe_seconds == 300
        and missing_slots >= max(1, min_missing_slots)
        and attempts >= 3
        and successful_refetches >= 2
        and broker_source_verified
        and last_two_broker_bars_consecutive
    )
