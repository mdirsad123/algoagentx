"""Pure, time-aligned TradeLocker polling policy.

No guessed market session hours. Broker history remains the authority for OHLCV.
For M5 a prolonged no-data period is probed at the NEXT 5-minute candle
boundary instead of hammering the REST API every few seconds.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from .runner_scheduler import parse_timeframe_to_seconds, ensure_utc, latest_expected_closed_candle_open


def next_candle_probe(now: datetime, timeframe: str, grace_seconds: int = 2) -> datetime:
    """Next aligned candle-close+grace instant, strictly after now."""
    now = ensure_utc(now)
    if now is None:
        raise ValueError('now is required')
    sec = parse_timeframe_to_seconds(timeframe)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    offset = (now - start).total_seconds()
    boundary = ((int(offset // sec) + 1) * sec)
    candidate = start + timedelta(seconds=boundary + max(0, grace_seconds))
    if offset < max(0, grace_seconds):
        # e.g. 02:05:01 before the first eligible +2s poll.
        # This is also correct for earlier aligned intraday boundaries.
        pass
    previous = candidate - timedelta(seconds=sec)
    if previous > now:
        return previous
    return candidate


def next_poll_delay(
    now: datetime, timeframe: str, *, ready: bool = False,
    empty_streak: int = 0, fast_retries: int = 2,
    fast_retry_seconds: float = 8.0, grace_seconds: int = 2,
    skip_reason: str | None = None, idle_grace_seconds: int = 2,
    retry_at: datetime | None = None,
) -> float:
    """Return seconds to next poll (no blocking sleep or network work)."""
    now = ensure_utc(now)
    if now is None:
        raise ValueError('now is required')
    if skip_reason == 'grace':
        # A grace skip belongs to the boundary already attempted, not the next
        # boundary. DB/event-loop waits may have crossed its exact deadline.
        deadline = ensure_utc(retry_at)
        if deadline is None:
            deadline = latest_expected_closed_candle_open(now, timeframe) + timedelta(
                seconds=parse_timeframe_to_seconds(timeframe) + max(0, grace_seconds))
        return max(0.1, (deadline - now).total_seconds())
    aligned = max(0.1, (next_candle_probe(now, timeframe, grace_seconds) - now).total_seconds())
    if not ready and skip_reason != 'already_stored' and empty_streak <= max(0, fast_retries):
        # Do not allow a short retry to drift past the next M5 close.
        return max(0.1, min(float(max(1, fast_retry_seconds)), aligned))
    if not ready and empty_streak > max(0, fast_retries):
        # During an extended no-data session, a single poll at CLOSE+2s can
        # miss a broker candle published at +6..10s, then defer five minutes.
        # Keep ONE poll per M5 but align it to CLOSE+10s after prolonged idle.
        next_close = next_candle_probe(now, timeframe, grace_seconds=grace_seconds)
        extra = max(0, idle_grace_seconds - grace_seconds)
        return max(0.1, (next_close + timedelta(seconds=extra) - now).total_seconds())
    return aligned


def runner_no_data_probe_time(now: datetime, timeframe: str, misses: int, *,
                              fast_probes: int = 3, probe_seconds: int = 5,
                              run_delay_seconds: int = 2, max_idle_probe_seconds: int = 30) -> datetime:
    """DB-only runner wait; broker polling remains in the separate worker."""
    now = ensure_utc(now)
    if now is None:
        raise ValueError('now is required')
    if misses < max(0, fast_probes):
        return now + timedelta(seconds=max(1, probe_seconds))
    return min(now + timedelta(seconds=max(5, max_idle_probe_seconds)),
               next_candle_probe(now, timeframe, grace_seconds=max(2, run_delay_seconds)))
